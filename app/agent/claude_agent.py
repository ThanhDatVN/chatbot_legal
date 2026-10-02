"""Claude-driven agent: a manual tool-use loop over the two business tools.

The model searches and reads sources itself, then returns a JSON object (enforced
with output_config.format) listing claims, each with the chunk IDs it relies on
and a verbatim quote. Citation numbers, URLs and pages are attached later by
code from the snapshot, never taken from model text.
"""

from __future__ import annotations

from app.agent.draft import Draft, Usage
from app.agent.llm_common import FINAL_SCHEMA, SYSTEM_PROMPT, parse_final, question_message, wrap_tool_result
from app.agent.tools import TOOL_DEFINITIONS, ToolBox
from app.config import Settings
from app.errors import LLMUnavailable
from app.schemas import Decision, RefusalReason

# USD per million tokens: (input, output, cache read, cache write)
PRICES = {
    "claude-opus-5-5": (4.00, 20.00, 0.20, 5.00),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20, 2.50),
    "claude-haiku-4-5": (1.00, 5.00, 0.10, 1.25),
}



def _cost(model: str, usage: Usage) -> float:
    p_in, p_out, p_read, p_write = PRICES.get(model, PRICES["claude-opus-5-5"])
    return (usage.input_tokens * p_in + usage.output_tokens * p_out + usage.cache_read_tokens * p_read
            + usage.cache_write_tokens * p_write) / 1_000_000


class ClaudeAgent:
    def __init__(self, toolbox: ToolBox, settings: Settings, client=None) -> None:
        self.toolbox = toolbox
        self.settings = settings
        if client is None:
            import anthropic

            client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=settings.llm_timeout_s)
        self.client = client

    def _request(self, messages: list) -> object:
        import anthropic

        kwargs = dict(model=self.settings.llm_model, max_tokens=16000, system=SYSTEM_PROMPT, tools=TOOL_DEFINITIONS,
                      messages=messages, cache_control={"type": "ephemeral"},
                      output_config={"effort": self.settings.llm_effort,
                                     "format": {"type": "json_schema", "schema": FINAL_SCHEMA}})
        if self.settings.llm_server_fallback:
            kwargs.update(betas=["server-side-fallback-2026-07-01"], fallbacks="default")
        try:
            return self.client.beta.messages.create(**kwargs)
        except anthropic.AuthenticationError as exc:
            raise LLMUnavailable() from exc
        except anthropic.RateLimitError as exc:
            raise LLMUnavailable() from exc
        except anthropic.APIStatusError as exc:
            raise LLMUnavailable() from exc
        except anthropic.APIConnectionError as exc:
            raise LLMUnavailable() from exc

    def run(self, question: str, as_of_date: str) -> Draft:
        usage = Usage(model=self.settings.llm_model)
        messages: list = [{"role": "user", "content": question_message(question, as_of_date)}]
        max_turns = self.settings.max_search_calls + self.settings.max_source_calls + 2
        for _ in range(max_turns):
            response = self._request(messages)
            usage.requests += 1
            u = response.usage
            usage.input_tokens += getattr(u, "input_tokens", 0) or 0
            usage.output_tokens += getattr(u, "output_tokens", 0) or 0
            usage.cache_read_tokens += getattr(u, "cache_read_input_tokens", 0) or 0
            usage.cache_write_tokens += getattr(u, "cache_creation_input_tokens", 0) or 0
            usage.model = getattr(response, "model", usage.model)
            usage.cost_usd = _cost(self.settings.llm_model, usage)

            if response.stop_reason == "refusal":
                return Draft(Decision.REFUSE, RefusalReason.OUT_OF_SCOPE, usage=usage, layout="prose",
                             notes=["model_refusal"])
            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})  # keep thinking blocks
                results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    text, is_error = self.toolbox.call(block.name, dict(block.input))
                    results.append({"type": "tool_result", "tool_use_id": block.id, "is_error": is_error,
                                    "content": wrap_tool_result(text)})
                messages.append({"role": "user", "content": results})  # all results in one message
                continue
            if response.stop_reason == "max_tokens":
                raise LLMUnavailable()
            text = "".join(b.text for b in response.content if b.type == "text")
            return parse_final(text, usage)
        return Draft(Decision.REFUSE, RefusalReason.INSUFFICIENT_EVIDENCE, usage=usage, layout="prose",
                     notes=["tool_loop_limit"])

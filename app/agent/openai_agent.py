"""OpenAI-driven agent (default model gpt-4o-mini): the same tool loop, prompt and JSON contract as the Claude agent.

Chat Completions with strict function calling for search_evidence/get_source and a strict JSON-schema
response format for the final answer. Tool results are wrapped as untrusted data; citation numbers, URLs and
pages are attached later by code, and every claim still goes through app/generation/validator.py.
"""

from __future__ import annotations

import json

from app.agent.draft import Draft, Usage
from app.agent.llm_common import FINAL_SCHEMA, SYSTEM_PROMPT, parse_final, question_message, wrap_tool_result
from app.agent.tools import TOOL_DEFINITIONS, ToolBox
from app.config import Settings
from app.errors import LLMUnavailable
from app.schemas import Decision, RefusalReason

# USD per million tokens: (input, output, cached input). List prices when this was written; check before budgeting.
PRICES = {
    "gpt-4o-mini": (0.15, 0.60, 0.075),
    "gpt-4o": (2.50, 10.00, 1.25),
}

OPENAI_TOOLS = [{"type": "function",
                 "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"],
                              "strict": True}}
                for t in TOOL_DEFINITIONS]
RESPONSE_FORMAT = {"type": "json_schema", "json_schema": {"name": "citeagent_answer", "schema": FINAL_SCHEMA,
                                                          "strict": True}}


def _cost(model: str, usage: Usage) -> float:
    p_in, p_out, p_cached = PRICES.get(model, PRICES["gpt-4o-mini"])
    uncached = max(0, usage.input_tokens - usage.cache_read_tokens)
    return (uncached * p_in + usage.cache_read_tokens * p_cached + usage.output_tokens * p_out) / 1_000_000


class OpenAIAgent:
    def __init__(self, toolbox: ToolBox, settings: Settings, client=None) -> None:
        self.toolbox = toolbox
        self.settings = settings
        if client is None:
            if not settings.openai_api_key:
                raise LLMUnavailable()  # OPENAI_API_KEY is not set in .env
            import openai

            client = openai.OpenAI(api_key=settings.openai_api_key, timeout=settings.llm_timeout_s, max_retries=2)
        self.client = client

    def _request(self, messages: list) -> object:
        import openai

        try:
            return self.client.chat.completions.create(
                model=self.settings.openai_model, messages=messages, tools=OPENAI_TOOLS,
                parallel_tool_calls=False,  # strict schemas are guaranteed for one call at a time
                response_format=RESPONSE_FORMAT, temperature=0, max_completion_tokens=4000)
        except (openai.AuthenticationError, openai.PermissionDeniedError, openai.RateLimitError,
                openai.NotFoundError, openai.BadRequestError, openai.APIStatusError, openai.APIConnectionError) as exc:
            raise LLMUnavailable() from exc

    def run(self, question: str, as_of_date: str) -> Draft:
        usage = Usage(model=self.settings.openai_model)
        messages: list = [{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": question_message(question, as_of_date)}]
        max_turns = self.settings.max_search_calls + self.settings.max_source_calls + 2
        for _ in range(max_turns):
            response = self._request(messages)
            usage.requests += 1
            u = response.usage
            usage.input_tokens += getattr(u, "prompt_tokens", 0) or 0
            usage.output_tokens += getattr(u, "completion_tokens", 0) or 0
            details = getattr(u, "prompt_tokens_details", None)
            usage.cache_read_tokens += getattr(details, "cached_tokens", 0) or 0
            usage.model = getattr(response, "model", usage.model)
            usage.cost_usd = _cost(self.settings.openai_model, usage)

            choice = response.choices[0]
            message = choice.message
            if getattr(message, "refusal", None):
                return Draft(Decision.REFUSE, RefusalReason.OUT_OF_SCOPE, usage=usage, layout="prose",
                             notes=["model_refusal"])
            if message.tool_calls:
                messages.append({"role": "assistant", "content": message.content,
                                 "tool_calls": [{"id": c.id, "type": "function",
                                                 "function": {"name": c.function.name,
                                                              "arguments": c.function.arguments}}
                                                for c in message.tool_calls]})
                for call in message.tool_calls:
                    try:
                        args = json.loads(call.function.arguments or "{}")
                    except json.JSONDecodeError:
                        text, is_error = "Tham số tool không phải JSON hợp lệ.", True
                    else:
                        text, is_error = self.toolbox.call(call.function.name, args)
                    content = wrap_tool_result(text)
                    messages.append({"role": "tool", "tool_call_id": call.id,
                                     "content": f"[error] {content}" if is_error else content})
                continue
            if choice.finish_reason == "length":
                raise LLMUnavailable()
            return parse_final(message.content or "", usage)
        return Draft(Decision.REFUSE, RefusalReason.INSUFFICIENT_EVIDENCE, usage=usage, layout="prose",
                     notes=["tool_loop_limit"])

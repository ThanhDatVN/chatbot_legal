"""Local agent on Ollama (default qwen3:4b): no API cost, same tools, prompt, JSON contract and validator.

Small local models do not reliably combine tool calls with a forced JSON format: given both, qwen3:4b skips the
tools and invents chunk ids. So the agent works in two phases over the native /api/chat endpoint (which also
lets us set num_ctx and turn thinking off):

1. tool loop, no format constraint. The first search_evidence call is made by the agent itself with the
   question (plus the statutory query expansion), because small models often answer without searching; the
   model can then open sources with get_source or search again.
2. one final request without tools and with the final-answer JSON schema as `format`.

The citation validator then drops every claim whose chunk was not fetched or whose quote is not verbatim.
"""

from __future__ import annotations

import json

import httpx

from app.agent.draft import Draft, Usage
from app.agent.lexicon import expand_query
from app.agent.llm_common import FINAL_SCHEMA, SYSTEM_PROMPT, parse_final, question_message, wrap_tool_result
from app.agent.tools import TOOL_DEFINITIONS, ToolBox
from app.config import Settings
from app.errors import LLMUnavailable
from app.schemas import Decision, RefusalReason

OLLAMA_TOOLS = [{"type": "function",
                 "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}}
                for t in TOOL_DEFINITIONS]
FINAL_INSTRUCTION = (
    "Bây giờ trả về câu trả lời cuối cùng dưới dạng JSON theo schema. Chỉ dùng chunk_id của các nguồn đã mở bằng "
    "get_source; mỗi quote phải chép nguyên văn từ nguồn đó. Nếu các nguồn đã mở không đủ để trả lời, chọn "
    "decision REFUSE với reason phù hợp và để claims rỗng.")


class OllamaAgent:
    def __init__(self, toolbox: ToolBox, settings: Settings, client: httpx.Client | None = None) -> None:
        self.toolbox = toolbox
        self.settings = settings
        self.client = client or httpx.Client(base_url=settings.ollama_url, timeout=settings.ollama_timeout_s)

    def _chat(self, messages: list, *, tools: bool, usage: Usage) -> dict:
        body = {"model": self.settings.ollama_model, "messages": messages, "stream": False,
                "think": self.settings.ollama_think,
                "options": {"temperature": 0, "num_ctx": self.settings.ollama_num_ctx}}
        if tools:
            body["tools"] = OLLAMA_TOOLS
        else:
            body["format"] = FINAL_SCHEMA
        try:
            response = self.client.post("/api/chat", json=body)
            response.raise_for_status()
        except httpx.HTTPError as exc:  # Ollama not running, model not pulled, timeout
            raise LLMUnavailable() from exc
        data = response.json()
        usage.requests += 1
        usage.input_tokens += data.get("prompt_eval_count", 0) or 0
        usage.output_tokens += data.get("eval_count", 0) or 0
        return data.get("message") or {}

    def _run_tool(self, messages: list, name: str, args: dict, call_id: str) -> None:
        text, is_error = self.toolbox.call(name, args)
        content = wrap_tool_result(text)
        messages.append({"role": "tool", "tool_name": name, "tool_call_id": call_id,
                         "content": f"[error] {content}" if is_error else content})

    def run(self, question: str, as_of_date: str) -> Draft:
        usage = Usage(model=self.settings.ollama_model)
        messages: list = [{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": question_message(question, as_of_date)}]
        seed = {"query": expand_query(question)[:1000], "top_k": 5, "document_ids": None}
        messages.append({"role": "assistant", "content": "",
                         "tool_calls": [{"id": "seed", "function": {"name": "search_evidence", "arguments": seed}}]})
        self._run_tool(messages, "search_evidence", seed, "seed")

        max_turns = self.settings.max_search_calls + self.settings.max_source_calls
        for turn in range(max_turns):
            message = self._chat(messages, tools=True, usage=usage)
            calls = message.get("tool_calls") or []
            if not calls:
                break
            messages.append({"role": "assistant", "content": message.get("content") or "", "tool_calls": calls})
            for i, call in enumerate(calls):
                fn = call.get("function") or {}
                args = fn.get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                self._run_tool(messages, fn.get("name", ""), args, call.get("id") or f"t{turn}-{i}")
        else:
            return Draft(Decision.REFUSE, RefusalReason.INSUFFICIENT_EVIDENCE, usage=usage, layout="prose",
                         notes=["tool_loop_limit"])

        messages.append({"role": "user", "content": FINAL_INSTRUCTION})
        final = self._chat(messages, tools=False, usage=usage)
        return parse_final(final.get("content") or "", usage)

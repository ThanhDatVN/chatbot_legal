"""Step 1: write everyday-wording questions for every in-scope article chunk with a local LLM (or gpt-4o-mini).

    python -m training.generate_queries --backend ollama --model qwen3:8b [--limit 20] [--no-check]

For each chunk the model writes three questions the chunk answers directly, in the words people use ("sếp",
"nghỉ ngang", "bị đuổi việc"), and one near-miss question on the same topic that the chunk does not answer.
With the self-check on (default), the gray-zone verifier prompt (app/agent/verifier.py) is asked about each
question against its own chunk: answerable questions it rejects and near-misses it accepts are dropped.

Output: data/training/queries.jsonl, one line per chunk; the run resumes where it stopped. Nothing here reads
the evaluation sets; near-duplicates of evaluation questions are removed in step 2.
"""

from __future__ import annotations

import argparse
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from app.agent.extractive import ExtractiveAgent
from app.agent.verifier import make_verifier
from app.config import Settings, get_settings
from app.storage.corpus import CorpusCatalog
from training.common import DATA, Corpus, read_jsonl

OUT = DATA / "queries.jsonl"
GEN_SCHEMA = {
    "type": "object",
    "properties": {"questions": {"type": "array", "items": {"type": "string"}},
                   "near_miss": {"type": "array", "items": {"type": "string"}}},
    "required": ["questions", "near_miss"],
    "additionalProperties": False,
}
PROMPT = """Bạn tạo dữ liệu huấn luyện cho hệ thống hỏi đáp pháp luật lao động Việt Nam.

Đoạn văn bản pháp luật:
{header}
{text}

Hãy viết:
1. "questions": {n} câu hỏi khác nhau mà người lao động hoặc chủ doanh nghiệp bình thường hay hỏi, và đoạn văn bản
   trên trả lời TRỰC TIẾP được.
   - Mỗi câu hỏi về một nội dung cụ thể có trong đoạn (một quyền, nghĩa vụ, con số, thời hạn hoặc điều kiện).
   - Diễn đạt bằng từ ngữ thông thường của người không học luật; tránh lặp lại nguyên văn cụm từ chuyên môn của đoạn.
   - Câu hỏi tự đứng được: không chào hỏi, không xưng hô, không nhắc số điều, khoản hay tên văn bản.
   - Đa dạng: một câu hỏi có/không; một câu hỏi về con số, thời hạn hoặc điều kiện nếu đoạn có; một câu kể ngắn
     tình huống của người hỏi rồi hỏi.
   - Mỗi câu dưới 35 từ.
2. "near_miss": 1 câu hỏi cùng chủ đề nhưng đoạn văn bản trên KHÔNG trả lời được (hỏi một chi tiết, con số hoặc
   thủ tục không có trong đoạn).

Chỉ trả về JSON: {{"questions": [...], "near_miss": [...]}}"""
MAX_TEXT_CHARS = 3500
REF_IN_QUESTION_RE = re.compile(r"\b(điều|khoản|điểm)\s+\d+|bộ luật|nghị định|thông tư", re.IGNORECASE)
VIETNAMESE_RE = re.compile(r"[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]", re.IGNORECASE)
# gpt-4o-mini, USD per million tokens (input, output)
OPENAI_PRICES = {"gpt-4o-mini": (0.15, 0.60)}


def clean(questions: list, limit: int) -> list[str]:
    out = []
    for q in questions:
        q = " ".join(str(q).split()).strip(" -•*\"'")
        words = len(q.split())
        if 5 <= words <= 45 and VIETNAMESE_RE.search(q) and not REF_IN_QUESTION_RE.search(q) and q not in out:
            out.append(q)
    return out[:limit]


class Generator:
    def __init__(self, backend: str, model: str, settings: Settings, temperature: float, seed: int) -> None:
        self.backend, self.model, self.temperature, self.seed = backend, model, temperature, seed
        self.calls = self.input_tokens = self.output_tokens = 0
        self.seconds = 0.0
        self.lock = threading.Lock()
        if backend == "ollama":
            self.client = httpx.Client(base_url=settings.ollama_url, timeout=settings.ollama_timeout_s)
        else:
            import openai

            if not settings.openai_api_key:
                raise SystemExit("OPENAI_API_KEY is not set")
            self.client = openai.OpenAI(api_key=settings.openai_api_key, timeout=120, max_retries=3)

    def __call__(self, prompt: str) -> dict | None:
        started = time.perf_counter()
        tokens_in = tokens_out = 0
        try:
            if self.backend == "ollama":
                body = {"model": self.model, "stream": False, "think": False, "format": GEN_SCHEMA,
                        "keep_alive": "60m", "messages": [{"role": "user", "content": prompt}],
                        "options": {"temperature": self.temperature, "seed": self.seed, "num_ctx": 4096,
                                    "num_predict": 400}}
                response = self.client.post("/api/chat", json=body)
                response.raise_for_status()
                data = response.json()
                tokens_in, tokens_out = data.get("prompt_eval_count", 0) or 0, data.get("eval_count", 0) or 0
                text = (data.get("message") or {}).get("content") or ""
            else:
                response = self.client.chat.completions.create(
                    model=self.model, temperature=self.temperature, seed=self.seed, max_completion_tokens=400,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_schema",
                                     "json_schema": {"name": "questions", "schema": GEN_SCHEMA, "strict": True}})
                tokens_in, tokens_out = response.usage.prompt_tokens, response.usage.completion_tokens
                text = response.choices[0].message.content or ""
            return json.loads(text)
        except Exception as exc:  # noqa: BLE001 - one bad chunk must not stop a long run
            print(f"  generation failed: {type(exc).__name__}: {exc}"[:200], flush=True)
            return None
        finally:
            with self.lock:
                self.calls += 1
                self.seconds += time.perf_counter() - started
                self.input_tokens += tokens_in
                self.output_tokens += tokens_out

    def cost_usd(self) -> float:
        price_in, price_out = OPENAI_PRICES.get(self.model, (0.0, 0.0)) if self.backend == "openai" else (0.0, 0.0)
        return (self.input_tokens * price_in + self.output_tokens * price_out) / 1e6


def checker(backend: str, model: str, settings: Settings):
    s = settings.model_copy(update={"llm_verifier": backend, "verifier_model": model})
    verifier = make_verifier(s)
    if verifier is None:
        raise SystemExit(f"self-check backend {backend} unavailable")
    return verifier


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["ollama", "openai"], default="ollama")
    parser.add_argument("--model", default=None, help="default: OLLAMA_MODEL or OPENAI_MODEL")
    parser.add_argument("--per-chunk", type=int, default=3)
    parser.add_argument("--subset", choices=["eligible", "in_scope"], default="in_scope")
    parser.add_argument("--limit", type=int, default=None, help="only N chunks (smoke test)")
    parser.add_argument("--offset", type=int, default=0, help="skip the first N chunks (smoke test)")
    parser.add_argument("--workers", type=int, default=1, help="parallel requests (set OLLAMA_NUM_PARALLEL to match)")
    parser.add_argument("--no-check", action="store_true", help="skip the verifier self-check")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args()
    settings = get_settings()
    model = args.model or (settings.ollama_model if args.backend == "ollama" else settings.openai_model)
    catalog = CorpusCatalog(settings.snapshot_dir, settings.currency_policy)
    corpus = Corpus(catalog)
    chunks = corpus.generation_chunks(args.subset)[args.offset:]
    chunks = chunks[: args.limit] if args.limit else chunks
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {r["chunk_id"] for r in read_jsonl(out)}
    todo = [c for c in chunks if c.chunk_id not in done]
    if args.backend == "openai":
        est_in, est_out = len(todo) * (900 + args.per_chunk * 450), len(todo) * (250 + args.per_chunk * 10)
        price_in, price_out = OPENAI_PRICES.get(model, (0.15, 0.60))
        print(f"estimated OpenAI cost for {len(todo)} chunks: ${(est_in * price_in + est_out * price_out) / 1e6:.2f}")
    print(f"{len(chunks)} chunks, {len(done)} already done, {len(todo)} to generate with {args.backend}/{model}")
    generate = Generator(args.backend, model, settings, args.temperature, args.seed)
    verify = None if args.no_check else checker(args.backend, model, settings)

    def process(chunk) -> dict:
        prompt = PROMPT.format(header=chunk.context_header, text=chunk.text[:MAX_TEXT_CHARS], n=args.per_chunk)
        data = generate(prompt) or {}
        questions = clean(data.get("questions", []), args.per_chunk)
        near = clean(data.get("near_miss", []), 1)
        rejected = []
        if verify is not None and (questions or near):
            units = ExtractiveAgent._body(chunk.text, chunk.section_label)
            title = f"{chunk.section_label}. {chunk.section_title or ''} — {chunk.document_number}"
            answers = {q: verify.check(q, title, units) is not None for q in questions + near}
            rejected = [q for q in questions if not answers[q]] + [q for q in near if answers[q]]
            questions = [q for q in questions if answers[q]]
            near = [q for q in near if not answers[q]]
        return {"chunk_id": chunk.chunk_id, "document_id": chunk.document_id, "section": chunk.section_label,
                "questions": questions, "near_miss": near, "rejected": rejected, "raw": data,
                "checked": verify is not None, "generator": f"{args.backend}/{model}"}

    started = time.perf_counter()
    kept = dropped = 0
    with out.open("a", encoding="utf-8", newline="\n") as fh, ThreadPoolExecutor(args.workers) as pool:
        for i, record in enumerate(pool.map(process, todo), 1):
            kept += len(record["questions"]) + len(record["near_miss"])
            dropped += len(record["rejected"])
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            fh.flush()
            if i % 10 == 0 or i == len(todo):
                rate = (time.perf_counter() - started) / i
                print(f"[{i}/{len(todo)}] kept {kept}, dropped by self-check {dropped}, "
                      f"{rate:.1f}s/chunk, ~{rate * (len(todo) - i) / 60:.0f} min left", flush=True)
    summary = {"generator": f"{args.backend}/{model}", "calls": generate.calls, "seconds": round(generate.seconds),
               "tokens": {"input": generate.input_tokens, "output": generate.output_tokens},
               "cost_usd": round(generate.cost_usd(), 4), "kept": kept, "dropped_by_check": dropped,
               "check_calls": verify.stats.calls if verify else 0}
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()

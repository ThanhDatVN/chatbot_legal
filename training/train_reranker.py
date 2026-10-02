"""Step 3: fine-tune the cross-encoder (BAAI/bge-reranker-v2-m3) on the mined question groups.

    python -m training.train_reranker [--epochs 1] [--lr 1e-5] [--max-length 1024] [--out models/reranker-ft]

Needs a CUDA GPU with about 12 GB (Kaggle T4 16 GB); a 4 GB laptop GPU only runs the smoke test
(--freeze-layers 22 --max-length 128 --max-steps 2).

Loss per group = binary cross-entropy on every (question, chunk) pair, which keeps the sigmoid score calibrated
for the absolute answer threshold, + softmax cross-entropy of the positive against its negatives (ranking).
Near-miss groups (one chunk that does not answer) add only the BCE term. The word-embedding matrix (250k
tokens) is frozen: it holds most of the parameters and the corpus uses a small part of the vocabulary.
fp16 autocast, gradient checkpointing, AdamW with linear warm-up and decay.

The synthetic validation split (about one article in ten, by hash) is scored before training and after every
epoch; the best epoch is saved in fp16 with its tokenizer and training_meta.json. Point RERANKER_MODEL at the
output directory to use it. The evaluation sets are not read here.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from datetime import UTC, datetime
from pathlib import Path

from app.config import get_settings
from app.storage.corpus import CorpusCatalog
from evaluation.common import git_commit
from training.common import DATA, MODELS, read_jsonl

THRESHOLD = 0.8


def build_pairs(group: dict, texts: dict[str, str]) -> tuple[list[tuple[str, str]], list[float]]:
    ids = group["pos"] + group["neg"]
    return [(group["query"], texts[cid]) for cid in ids], [1.0] * len(group["pos"]) + [0.0] * len(group["neg"])


def score_group(model, tok, pairs, max_length, device, torch):
    batch = tok([q for q, _ in pairs], [p for _, p in pairs], padding=True, truncation="only_second",
                max_length=max_length, return_tensors="pt").to(device)
    with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type == "cuda"):
        return model(**batch).logits.float().view(-1)


def evaluate(model, tok, groups, texts, max_length, device, torch) -> dict:
    model.eval()
    top1 = rr = pos_high = 0
    pos_scores, neg_high, near_high, n_neg = [], 0, 0, 0
    answerable = [g for g in groups if g["pos"]]
    near = [g for g in groups if not g["pos"]]
    with torch.inference_mode():
        for g in groups:
            pairs, _ = build_pairs(g, texts)
            probs = torch.sigmoid(score_group(model, tok, pairs, max_length, device, torch)).cpu().tolist()
            if g["pos"]:
                pos, negs = probs[0], probs[1:]
                rank = 1 + sum(n >= pos for n in negs)
                top1 += rank == 1
                rr += 1 / rank
                pos_scores.append(pos)
                pos_high += pos >= THRESHOLD
                neg_high += sum(n >= THRESHOLD for n in negs)
                n_neg += len(negs)
            else:
                near_high += max(probs) >= THRESHOLD
    model.train()
    a, m = max(1, len(answerable)), max(1, len(near))
    out = {"answerable_groups": len(answerable), "near_miss_groups": len(near),
           "acc_at_1": round(top1 / a, 4), "mrr": round(rr / a, 4),
           "positive_mean": round(sum(pos_scores) / a, 4), "positive_at_threshold": round(pos_high / a, 4),
           "negative_at_threshold": round(neg_high / max(1, n_neg), 4), "near_miss_at_threshold": round(near_high / m, 4)}
    # what the answer policy cares about: the right chunk clears the threshold, near-misses do not
    out["objective"] = round(out["acc_at_1"] * 0.5 + out["positive_at_threshold"] * 0.5
                             - out["near_miss_at_threshold"] - out["negative_at_threshold"], 4)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", default=str(DATA / "pairs.jsonl"))
    parser.add_argument("--base", default="BAAI/bge-reranker-v2-m3")
    parser.add_argument("--out", default=str(MODELS / "reranker-ft"))
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--lr", type=float, default=1e-5)
    parser.add_argument("--warmup", type=float, default=0.1)
    parser.add_argument("--accum", type=int, default=8, help="question groups per optimizer step")
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--ce-weight", type=float, default=1.0)
    parser.add_argument("--freeze-layers", type=int, default=0, help="also freeze the first N encoder layers")
    parser.add_argument("--max-steps", type=int, default=None, help="stop after N optimizer steps (smoke test)")
    parser.add_argument("--limit-groups", type=int, default=None)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device(args.device if torch.cuda.is_available() or args.device == "cpu" else "cpu")
    settings = get_settings()
    catalog = CorpusCatalog(settings.snapshot_dir, settings.currency_policy)
    texts = {cid: c.embedding_text for cid, c in catalog.chunks.items()}
    groups = [g for g in read_jsonl(Path(args.pairs)) if all(cid in texts for cid in g["pos"] + g["neg"])]
    train = [g for g in groups if g["split"] == "train"][: args.limit_groups]
    val = [g for g in groups if g["split"] == "val"][: args.limit_groups]
    print(f"{len(train)} training groups, {len(val)} validation groups, device {device}", flush=True)

    tok = AutoTokenizer.from_pretrained(args.base)
    model = AutoModelForSequenceClassification.from_pretrained(args.base, dtype=torch.float32).to(device)
    model.gradient_checkpointing_enable()
    encoder = model.roberta if hasattr(model, "roberta") else model.base_model
    encoder.embeddings.word_embeddings.weight.requires_grad_(False)
    for layer in encoder.encoder.layer[: args.freeze_layers]:
        layer.requires_grad_(False)
    trainable = [p for p in model.parameters() if p.requires_grad]
    print(f"trainable parameters: {sum(p.numel() for p in trainable) / 1e6:.0f}M of "
          f"{sum(p.numel() for p in model.parameters()) / 1e6:.0f}M", flush=True)

    steps_per_epoch = math.ceil(len(train) / args.accum)
    total = min(steps_per_epoch * args.epochs, args.max_steps or 10**9)
    optimizer = torch.optim.AdamW(trainable, lr=args.lr, weight_decay=0.01)
    scheduler = get_linear_schedule_with_warmup(optimizer, int(total * args.warmup), total)
    scaler = torch.amp.GradScaler(enabled=device.type == "cuda")
    bce = torch.nn.BCEWithLogitsLoss()
    ce = torch.nn.CrossEntropyLoss()

    started = time.perf_counter()
    history = [{"epoch": 0, "val": evaluate(model, tok, val, texts, args.max_length, device, torch)}]
    print("before training:", history[0]["val"], flush=True)
    best = history[0]["val"]["objective"]
    out = Path(args.out)
    saved_epoch = None
    step = 0
    model.train()
    for epoch in range(1, args.epochs + 1):
        random.shuffle(train)
        running = 0.0
        for i, g in enumerate(train, 1):
            pairs, labels = build_pairs(g, texts)
            logits = score_group(model, tok, pairs, args.max_length, device, torch)
            target = torch.tensor(labels, device=device)
            loss = bce(logits, target)
            if g["pos"]:
                loss = loss + args.ce_weight * ce(logits.unsqueeze(0), torch.zeros(1, dtype=torch.long, device=device))
            scaler.scale(loss / args.accum).backward()
            running += loss.item()
            if i % args.accum == 0 or i == len(train):
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(trainable, 1.0)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
                scheduler.step()
                step += 1
                if step % 25 == 0:
                    rate = (time.perf_counter() - started) / i
                    print(f"epoch {epoch} step {step}/{total} loss {running / i:.4f} "
                          f"~{rate * (len(train) - i) / 60:.0f} min left in epoch", flush=True)
                if args.max_steps and step >= args.max_steps:
                    break
        result = evaluate(model, tok, val, texts, args.max_length, device, torch)
        history.append({"epoch": epoch, "steps": step, "train_loss": round(running / max(1, i), 4), "val": result})
        print(f"after epoch {epoch}:", result, flush=True)
        if result["objective"] > best or saved_epoch is None:
            best, saved_epoch = max(best, result["objective"]), epoch
            out.mkdir(parents=True, exist_ok=True)
            fp16 = {k: v.detach().to("cpu", torch.float16) for k, v in model.state_dict().items()}
            model.save_pretrained(out, state_dict=fp16, safe_serialization=True)
            tok.save_pretrained(out)
        if args.max_steps and step >= args.max_steps:
            break

    meta = {"date": datetime.now(UTC).isoformat(timespec="seconds"), "git_commit": git_commit(),
            "base_model": args.base, "snapshot": catalog.snapshot_id, "args": vars(args),
            "groups": {"train": len(train), "val": len(val)}, "saved_epoch": saved_epoch,
            "improved_over_base": best > history[0]["val"]["objective"], "history": history,
            "seconds": round(time.perf_counter() - started),
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}
    summary = Path(args.pairs).with_name(Path(args.pairs).stem + "_summary.json")
    if summary.exists():
        meta["data"] = json.loads(summary.read_text(encoding="utf-8"))
    out.mkdir(parents=True, exist_ok=True)
    (out / "training_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved epoch {saved_epoch} to {out} (validation objective {best}, before training "
          f"{history[0]['val']['objective']})")


if __name__ == "__main__":
    main()

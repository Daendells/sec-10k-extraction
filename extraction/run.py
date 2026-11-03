"""Extract the six figures from every filing and score them against the XBRL answer key.

    OPENROUTER_API_KEY=... python -m extraction.run --k 16 --k 8
    python -m extraction.run --k 16 --k 8 --score-only     # re-score cached replies without calling the LLM

Replies are cached in results/raw/k<k>/<ticker>.json, so an interrupted run resumes where it stopped.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from extraction.chunks import chunk, top_chunks
from extraction.llm import FIELD_HELP, OpenRouter, build_messages, parse_json
from extraction.score import is_correct, summarize
from extraction.values import appears_in, evidence_supports, parse_number, to_full_units

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"


def excerpts_for(filing: dict, k: int) -> list[str]:
    text = (ROOT / "data" / "text" / f"{filing['ticker']}.txt").read_text(encoding="utf-8")
    return top_chunks(chunk(text), k=k)


def ask(client: OpenRouter, filing: dict, excerpts: list[str], path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    messages = build_messages(filing["ticker"], filing["report_date"], excerpts)
    for attempt in range(4):
        try:
            start = time.perf_counter()
            reply, model = client.complete(messages)
            record = {"reply": reply, "model": model, "seconds": round(time.perf_counter() - start, 1)}
            parse_json(reply)  # retry malformed replies too
            break
        except Exception as error:  # rate limits, timeouts, malformed JSON
            record = {"reply": "", "model": "", "error": f"{type(error).__name__}: {error}"[:300]}
            time.sleep(15 * (attempt + 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    return record


def score_filing(filing: dict, record: dict, excerpts: list[str]) -> list[dict]:
    try:
        answer = parse_json(record["reply"])
    except ValueError:
        answer = {}
    source = "\n".join(excerpts)
    rows = []
    for field, truth in filing["truth"].items():
        item = answer.get(field) or {}
        raw, pred, verified = item.get("value"), None, False
        if raw not in (None, ""):
            try:
                written = parse_number(raw)
                pred = to_full_units(written, str(item.get("scale", "units")).lower(), field)
                verified = evidence_supports(str(item.get("evidence") or ""), written, source)
            except ValueError:
                pred = None
        rows.append({"ticker": filing["ticker"], "field": field, "truth": truth, "pred": pred, "verified": verified,
                     "correct": is_correct(pred, truth), "in_excerpts": appears_in(truth, field, source),
                     "evidence": item.get("evidence")})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, action="append", required=True)
    parser.add_argument("--score-only", action="store_true")
    args = parser.parse_args()

    filings = json.loads((ROOT / "data" / "filings.json").read_text(encoding="utf-8"))["filings"]
    client = None if args.score_only else OpenRouter()
    metrics = {}
    for k in args.k:
        rows, models, seconds, failures = [], {}, [], 0
        for filing in filings:
            excerpts = excerpts_for(filing, k)
            path = RESULTS / "raw" / f"k{k}" / f"{filing['ticker']}.json"
            record = json.loads(path.read_text(encoding="utf-8")) if args.score_only else ask(client, filing, excerpts, path)
            failures += bool(record.get("error"))
            models[record.get("model") or "none"] = models.get(record.get("model") or "none", 0) + 1
            seconds += [record["seconds"]] if "seconds" in record else []
            rows += score_filing(filing, record, excerpts)
            print(f"k={k} {filing['ticker']}: {sum(r['correct'] for r in rows[-len(filing['truth']):])}/{len(filing['truth'])}")
        summary = summarize(rows)
        in_text = [r for r in rows if r["in_excerpts"]]
        summary["accuracy_when_value_was_retrieved"] = round(sum(r["correct"] for r in in_text) / len(in_text), 4)
        summary["retrieval_recall"] = round(len(in_text) / len(rows), 4)
        summary["models_that_answered"] = models
        summary["failed_requests"] = failures
        summary["median_seconds"] = sorted(seconds)[len(seconds) // 2] if seconds else None
        metrics[f"k{k}"] = summary
        with open(RESULTS / f"predictions_k{k}.jsonl", "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
    (RESULTS / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v["overall"] for k, v in metrics.items()}, indent=1))


if __name__ == "__main__":
    main()

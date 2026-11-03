# Reading 10-K filings with an LLM, checked against XBRL

[![CI](https://github.com/Daendells/sec-10k-extraction/actions/workflows/ci.yml/badge.svg)](https://github.com/Daendells/sec-10k-extraction/actions/workflows/ci.yml)

Can a free LLM read six headline figures out of a US annual report (Form 10-K) correctly? This project measures that
instead of eyeballing it. Every answer is compared with the figure the company itself tagged in XBRL, the
machine-readable data the SEC publishes next to each filing.

**Result:** with 16 retrieved excerpts per filing, 211 of 220 values were correct (95.9%). No answer was off by a factor
of a thousand or a million, the usual failure when a table says "in millions".

## What it reads

- 39 companies across 11 sectors, one 10-K each, with fiscal years ending between September 2025 and August 2026.
- Six figures per filing: revenue, net income, diluted EPS, total assets, cash and cash equivalents, and shareholders'
  equity. That makes 220 values, because a few companies do not tag every one of the six.
- ExxonMobil was dropped: its ticker now maps to a CIK with no 10-K on file.

## How it works

1. `download.py` fetches each filing from SEC EDGAR, plus the answer key from the `companyfacts` API. A fact counts
   only when its accession number matches the filing and its period ends on the report date. That way the key is
   the exact number the filing reports, not a later restatement.
2. `text.py` turns the HTML into plain text and keeps table rows as `label | value | value` lines.
3. `chunks.py` cuts the text into 2,000-character chunks, ranks them with BM25 for five statement-style queries, and
   fuses the rankings (reciprocal rank fusion). The top k chunks go to the model in document order.
4. `llm.py` asks for JSON: each figure's value as printed, the unit the table states, and a short quote as evidence.
   The model is told to return null rather than guess.
5. `values.py` converts the value to full units and checks that the quoted evidence really appears in the
   excerpts and contains that number. `score.py` marks an answer correct when it is within 0.5% of the key, which
   allows for rounding such as EPS printed to two decimals.

The model was `nvidia/nemotron-3-ultra-550b-a55b:free` through OpenRouter, with Gemma 4 31B as a fallback. The
fallback was never needed in the final run.

## Results

| Excerpts per filing | Correct | Answered | True value was in the excerpts | Correct when it was |
| ---: | ---: | ---: | ---: | ---: |
| 16 | 211 / 220 (95.9%) | 98.2% | 97.3% | 98.6% |
| 8 | 186 / 220 (84.5%) | 87.3% | 90.0% | 93.4% |

Most of the gap between k=8 and k=16 is retrieval, not reading. With 8 chunks, the income statement or balance sheet
was sometimes not retrieved at all, and the model correctly returned null.

By field, at k=16:

| Field | Correct |
| --- | ---: |
| Net income | 35 / 35 |
| Total assets | 38 / 39 |
| Diluted EPS | 37 / 38 |
| Cash and cash equivalents | 34 / 35 |
| Shareholders' equity | 33 / 34 |
| Revenue | 34 / 39 |

## Where it went wrong

All nine misses at k=16 are listed in `results/predictions_k16.jsonl`. They fall into three groups.

- **Revenue means different things (4).** For Chevron, ConocoPhillips, NextEra Energy and Duke Energy, the model
  quoted a real revenue line from the income statement, and the quote checks out. The XBRL key uses a different
  line:
  - Chevron's key is "Total revenues and other income", while the model took "Sales and other operating revenues".
    ConocoPhillips is the reverse.
  - Duke's key is "Total revenue from contracts with customers".
  - NextEra's key (25,800 million) is not printed anywhere in the filing, so the key itself may be the problem there.
    It still counts as wrong.

  None of these are invented numbers. Still, a pipeline that needs "revenue" for energy and utility companies has
  to say which line it means.
- **Wrong row (1).** For NVIDIA, the model took the "Cost of revenue" row and shortened the label to "Revenue" in its
  quote. The evidence check caught it: that shortened quote is not in the text.
- **No answer (4).** Abbott's diluted EPS, JPMorgan's total assets, ConocoPhillips' equity and UPS's cash came back
  null. For the first two, the true value was not in the retrieved excerpts.

The evidence check is useful but not enough by itself. It flagged the NVIDIA mistake, but it passes the four revenue
mismatches, because those quotes are real.

## Limits

- 39 filings is a small sample. One more mistake moves accuracy by about half a percentage point.
- All companies are large US firms with clean, standard statements. Smaller filers and other formats will be harder.
- Free models on OpenRouter change and get rate-limited. Re-running with live calls may give different replies. The
  cached replies in `results/raw/` reproduce the numbers above exactly.

## Running it

```bash
python -m venv .venv && .venv/Scripts/activate      # source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env                                # SEC_USER_AGENT and OPENROUTER_API_KEY

python -m extraction.download                       # filings and answer key into data/
python -m extraction.run --k 16 --k 8               # calls the LLM, caches replies, writes results/
python -m extraction.run --k 16 --k 8 --score-only  # re-score the cached replies, no API calls
pytest -q
```

The SEC asks every client to identify itself, so `SEC_USER_AGENT` must hold a name and contact email.

## License

MIT

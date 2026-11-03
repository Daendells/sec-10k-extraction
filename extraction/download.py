"""Fetch the latest 10-K of each company, convert it to text, and record the XBRL answer key.

    SEC_USER_AGENT="Your Name your@email" python -m extraction.download
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from extraction.sec import Sec, ground_truth
from extraction.text import html_to_text

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def main() -> None:
    sec = Sec()
    ciks = {row["ticker"]: row["cik_str"] for row in sec.get("https://www.sec.gov/files/company_tickers.json").json().values()}
    companies = list(csv.DictReader(open(DATA / "companies.csv", encoding="utf-8")))
    (DATA / "text").mkdir(exist_ok=True)
    filings, skipped = [], []
    for company in companies:
        ticker = company["ticker"]
        cik = int(ciks[ticker])
        try:
            filing = sec.latest_10k(cik)
        except LookupError as error:  # e.g. a ticker that now maps to a new holding company with no 10-K yet
            skipped.append({"ticker": ticker, "cik": cik, "reason": str(error)})
            print(f"{ticker}: skipped, {error}")
            continue
        text_path = DATA / "text" / f"{ticker}.txt"
        if not text_path.exists():
            text_path.write_text(html_to_text(sec.document(cik, filing["accn"], filing["document"])), encoding="utf-8")
        truth = ground_truth(sec.companyfacts(cik), filing["accn"], filing["report_date"])
        filings.append({"ticker": ticker, "sector": company["sector"], "cik": cik, **filing, "truth": truth})
        print(f"{ticker}: {filing['report_date']} {len(truth)} fields, {text_path.stat().st_size // 1024} KB text")
    out = {"filings": filings, "skipped": skipped}
    (DATA / "filings.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

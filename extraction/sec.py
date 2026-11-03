"""SEC EDGAR access and the XBRL answer key.

Every request carries the contact SEC requires, read from the SEC_USER_AGENT environment variable
("Name email@example.com"), so no contact is hard-coded.
"""

from __future__ import annotations

import datetime as dt
import itertools
import os
import time

import httpx

# Field -> (XBRL tags tried in order, unit, is it a flow over the year?)
FIELDS = {
    "revenue": (["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "RevenuesNetOfInterestExpense",
                 "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax"], "USD", True),
    "net_income": (["NetIncomeLoss"], "USD", True),
    "diluted_eps": (["EarningsPerShareDiluted"], "USD/shares", True),
    "total_assets": (["Assets"], "USD", False),
    "cash": (["CashAndCashEquivalentsAtCarryingValue"], "USD", False),
    "equity": (["StockholdersEquity"], "USD", False),
}


def _full_year(fact: dict) -> bool:
    days = (dt.date.fromisoformat(fact["end"]) - dt.date.fromisoformat(fact["start"])).days
    return 340 <= days <= 380  # 52- and 53-week fiscal years


def ground_truth(companyfacts: dict, accn: str, report_date: str) -> dict[str, float]:
    """The value each field has in this filing for the fiscal year ending on report_date."""
    gaap = companyfacts["facts"].get("us-gaap", {})
    truth = {}
    for field, (tags, unit, flow) in FIELDS.items():
        for tag in tags:
            for fact in gaap.get(tag, {}).get("units", {}).get(unit, []):
                if fact.get("accn") != accn or fact.get("end") != report_date or fact.get("form") != "10-K":
                    continue
                if flow and not ("start" in fact and _full_year(fact)):
                    continue
                truth[field] = float(fact["val"])
                break
            if field in truth:
                break
    return truth


class Sec:
    """Polite client: SEC allows 10 requests a second; this stays well under it."""

    def __init__(self, user_agent: str | None = None):
        agent = user_agent or os.environ.get("SEC_USER_AGENT")
        if not agent:
            raise RuntimeError("Set SEC_USER_AGENT to 'Your Name your@email' (SEC requires a contact).")
        self.http = httpx.Client(headers={"User-Agent": agent}, timeout=60, follow_redirects=True)

    def get(self, url: str) -> httpx.Response:
        time.sleep(0.2)
        response = self.http.get(url)
        response.raise_for_status()
        return response

    def latest_10k(self, cik: int) -> dict:
        """Newest 10-K. "recent" holds only the last ~1,000 filings, so frequent filers need the older pages too."""
        filings = self.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json").json()["filings"]
        older = (self.get(f"https://data.sec.gov/submissions/{f['name']}").json() for f in filings.get("files", []))
        pages = itertools.chain([filings["recent"]], older)  # older pages are fetched only if needed
        for page in pages:
            if "10-K" in page["form"]:
                i = page["form"].index("10-K")
                return {"accn": page["accessionNumber"][i], "document": page["primaryDocument"][i],
                        "report_date": page["reportDate"][i], "filed": page["filingDate"][i]}
        raise LookupError(f"no 10-K found for CIK {cik}")

    def document(self, cik: int, accn: str, name: str) -> str:
        return self.get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{accn.replace('-', '')}/{name}").text

    def companyfacts(self, cik: int) -> dict:
        return self.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json").json()

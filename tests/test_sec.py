from extraction.sec import ground_truth

ACCN, END = "0000320193-25-000079", "2025-09-27"


def fact(val, end=END, start=None, accn=ACCN, form="10-K"):
    f = {"val": val, "end": end, "accn": accn, "form": form, "fp": "FY"}
    if start:
        f["start"] = start
    return f


FACTS = {"facts": {"us-gaap": {
    "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
        fact(391035e6, end="2024-09-28", start="2023-10-01"),       # prior year, same filing
        fact(102466e6, start="2025-06-29"),                          # one quarter: wrong duration
        fact(416161e6, start="2024-09-29"),                          # the answer
    ]}},
    "NetIncomeLoss": {"units": {"USD": [fact(112010e6, start="2024-09-29", accn="0000320193-24-000123")]}},
    "Assets": {"units": {"USD": [fact(359241e6)]}},
    "EarningsPerShareDiluted": {"units": {"USD/shares": [fact(7.46, start="2024-09-29")]}},
}}}


def test_ground_truth_picks_the_full_year_from_this_filing():
    truth = ground_truth(FACTS, ACCN, END)
    assert truth["revenue"] == 416161e6
    assert truth["total_assets"] == 359241e6
    assert truth["diluted_eps"] == 7.46


def test_ground_truth_skips_facts_from_other_filings_and_missing_tags():
    truth = ground_truth(FACTS, ACCN, END)
    assert "net_income" not in truth          # only reported under another accession
    assert "cash" not in truth                 # tag absent


def test_latest_10k_looks_in_older_pages_when_recent_has_none():
    from extraction.sec import Sec

    pages = {
        "https://data.sec.gov/submissions/CIK0000034088.json": {"filings": {
            "recent": {"form": ["8-K", "424B2"], "accessionNumber": ["a", "b"], "primaryDocument": ["x", "y"],
                       "reportDate": ["", ""], "filingDate": ["2026-01-02", "2026-01-01"]},
            "files": [{"name": "CIK0000034088-submissions-001.json"}]}},
        "https://data.sec.gov/submissions/CIK0000034088-submissions-001.json": {
            "form": ["10-K"], "accessionNumber": ["c"], "primaryDocument": ["xom-10k.htm"],
            "reportDate": ["2025-12-31"], "filingDate": ["2026-02-20"]},
    }

    class Fake(Sec):
        def __init__(self):
            pass

        def get(self, url):
            class R:
                def json(_self):
                    return pages[url]
            return R()

    assert Fake().latest_10k(34088) == {"accn": "c", "document": "xom-10k.htm", "report_date": "2025-12-31",
                                        "filed": "2026-02-20"}

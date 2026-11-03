from extraction.chunks import chunk, top_chunks
from extraction.text import html_to_text

HTML = """<html><head><style>.x{}</style><script>var a=1;</script></head><body>
<div style="display:none"><ix:header>hidden facts 999</ix:header></div>
<p>CONSOLIDATED BALANCE SHEETS</p>
<table><tr><td>Total assets</td><td>$</td><td>359,241</td></tr><tr><td>Total liabilities</td><td>285,508</td></tr></table>
</body></html>"""


def test_html_to_text_keeps_tables_as_rows_and_drops_hidden_parts():
    text = html_to_text(HTML)
    assert "Total assets | $ | 359,241" in text
    assert "Total liabilities | 285,508" in text
    assert "hidden facts" not in text and "var a" not in text


def test_chunk_overlaps_and_covers_the_text():
    text = "".join(chr(65 + i % 26) for i in range(5000))
    parts = chunk(text, size=2000, overlap=200)
    assert parts[0] == text[:2000] and parts[1].startswith(text[1800:1810])
    assert parts[-1].endswith(text[-50:])


def test_top_chunks_finds_the_statement_and_keeps_document_order():
    chunks = ["risk factors weather supply", "consolidated balance sheets total assets 359,241",
              "legal proceedings", "consolidated statements of operations net income revenue"]
    picked = top_chunks(chunks, ["total assets balance sheet", "net income revenue operations"], k=2)
    assert picked == [chunks[1], chunks[3]]

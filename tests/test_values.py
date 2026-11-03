import pytest

from extraction.values import evidence_supports, parse_number, to_full_units


@pytest.mark.parametrize("raw, expected", [("391,035", 391035), ("(1,234)", -1234), ("$ 6.08", 6.08), ("-0.5", -0.5), (7, 7)])
def test_parse_number(raw, expected):
    assert parse_number(raw) == expected


def test_to_full_units_scales_money_but_never_eps():
    assert to_full_units(416161, "millions", "revenue") == 416161e6
    assert to_full_units(7.46, "millions", "diluted_eps") == 7.46
    assert to_full_units(5, "thousands", "cash") == 5000


def test_evidence_must_contain_the_number_and_appear_in_the_text():
    source = "Total net sales | $ | 416,161 | $ | 391,035"
    assert evidence_supports("Total net sales | $ | 416,161", 416161, source)
    assert not evidence_supports("Total net sales | $ | 416,161", 400000, source)   # number not in quote
    assert not evidence_supports("Net sales were 416,161", 416161, source)          # quote not in document
    assert evidence_supports("Diluted | $ | 7.46", 7.46, "Earnings per share: Diluted | $ | 7.46")


def test_appears_in_finds_the_value_in_any_common_scale():
    from extraction.values import appears_in

    text = "Total net sales | $ | 416,161 | ... Diluted | $ | 7.46 | Cash 35,934 ... Total assets 1,234,567"
    assert appears_in(416161e6, "revenue", text)          # in millions
    assert appears_in(7.46, "diluted_eps", text)
    assert appears_in(1234567e3, "total_assets", text)    # in thousands
    assert not appears_in(999e6, "revenue", text)


def test_evidence_ignores_curly_versus_straight_quotes():
    source = "Total shareholders’ equity | 73,733 | 56,950"
    assert evidence_supports("Total shareholders' equity | 73,733", 73733, source)

"""Unit tests for normalizers."""
from __future__ import annotations

from candidate_transformer.normalizers.phone_normalizer import normalize_phone
from candidate_transformer.normalizers.date_normalizer import normalize_date_to_yyyy_mm
from candidate_transformer.normalizers.skill_normalizer import normalize_skill
from candidate_transformer.normalizers.country_normalizer import normalize_country


def test_normalize_phone_valid_us():
    assert normalize_phone("(415) 555-2671", default_region="US") == "+14155552671"


def test_normalize_phone_strict_e164():
    assert normalize_phone("+1 555 123456", default_region="US") == "+1555123456"
    assert normalize_phone("(+44) 20 7946 0958", default_region="GB") == "+442079460958"


def test_normalize_phone_invalid():
    assert normalize_phone("not a phone", default_region="US") is None


def test_normalize_date_with_month_name():
    assert normalize_date_to_yyyy_mm("March 2020") == "2020-03"


def test_normalize_date_month_slash_year():
    assert normalize_date_to_yyyy_mm("03/2020") == "2020-03"


def test_normalize_date_year_only_returns_none():
    assert normalize_date_to_yyyy_mm("2020") is None


def test_skill_normalization_variants():
    assert normalize_skill("py") == "Python"
    assert normalize_skill("python programming") == "Python"
    assert normalize_skill("JS") == "JavaScript"
    assert normalize_skill("c plus plus") == "C++"
    assert normalize_skill("some new skill") == "Some New Skill"


def test_country_normalizer():
    assert normalize_country("United States") == "US"
    assert normalize_country("usa") == "US"
    assert normalize_country("UK") == "GB"
    assert normalize_country("unknownland") is None

import pytest

from candidate_transformer.parsers.resume_parser import parse_resume_text


def test_btech_degree_and_field_split():
    text = """
    Education:
    B.Tech Computer Science
    """

    pr = parse_resume_text(text)
    edu = pr.raw.get("education", [])
    assert isinstance(edu, list)
    assert len(edu) == 1
    entry = edu[0]
    assert entry["degree"] == "B.Tech"
    assert entry["field"] == "Computer Science"
    assert entry["institution"] is None
    assert entry["end_year"] is None

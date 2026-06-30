import pytest

from candidate_transformer.projection import PathResolver, Projector


@pytest.fixture
def sample_candidate():
    return {
        "full_name": "Jane Doe",
        "emails": ["jane@example.com"],
        "skills": [{"name": "Python"}, {"name": "AWS"}],
        "experience": [{"company": "Acme Corp"}],
    }


def test_path_resolver_supports_requested_paths(sample_candidate):
    assert PathResolver("full_name").resolve(sample_candidate) == "Jane Doe"
    assert PathResolver("emails[0]").resolve(sample_candidate) == "jane@example.com"
    assert PathResolver("skills[].name").resolve(sample_candidate) == ["Python", "AWS"]
    assert PathResolver("experience[0].company").resolve(sample_candidate) == "Acme Corp"


def test_projector_handles_missing_policies(sample_candidate):
    projector = Projector(
        {
            "name": "full_name",
            "primary_email": {"path": "emails[0]"},
            "missing_as_none": {"path": "missing_field", "on_missing": "null"},
            "missing_as_omit": {"path": "missing_field", "on_missing": "omit"},
        }
    )

    result = projector.project(sample_candidate)

    assert result == {
        "name": "Jane Doe",
        "primary_email": "jane@example.com",
        "missing_as_none": None,
    }


def test_path_resolver_raises_for_error_policy(sample_candidate):
    with pytest.raises(KeyError):
        PathResolver("missing_field").resolve(sample_candidate, on_missing="error")

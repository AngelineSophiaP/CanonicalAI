import json
from pathlib import Path

from candidate_transformer.main import main


def test_main_writes_final_profile_json(tmp_path):
    csv_path = tmp_path / "candidates.csv"
    csv_path.write_text("name,email\nJane Doe,jane@example.com\n", encoding="utf-8")

    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Jane Doe\nPython\n", encoding="utf-8")

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "projection": {
                    "fields": ["candidate_id", "full_name", "emails", "skills", "provenance"],
                    "include_confidence": True,
                    "include_provenance": True,
                    "on_missing": "null",
                },
                "confidence": {"csv": 0.95, "resume": 0.8},
            }
        ),
        encoding="utf-8",
    )

    output_path = tmp_path / "final_profile.json"

    exit_code = main(
        [
            "--csv",
            str(csv_path),
            "--resume",
            str(resume_path),
            "--config",
            str(config_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["full_name"] == "Jane Doe"
    assert payload["emails"] == ["jane@example.com"]
    assert payload["provenance"][0]["field"] == "full_name"


def test_missing_fields_use_default_schema_values(tmp_path):
    csv_path = tmp_path / "candidates.csv"
    csv_path.write_text("name,email\nJane Doe,\n", encoding="utf-8")

    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Jane Doe\n", encoding="utf-8")

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "projection": {
                    "fields": [
                        "candidate_id",
                        "full_name",
                        "emails",
                        "phones",
                        "location",
                        "links",
                        "headline",
                        "years_experience",
                        "skills",
                        "experience",
                        "education",
                        "provenance",
                        "overall_confidence",
                    ],
                    "include_confidence": True,
                    "include_provenance": True,
                    "on_missing": "null",
                },
                "confidence": {"csv": 0.95, "resume": 0.8},
            }
        ),
        encoding="utf-8",
    )

    output_path = tmp_path / "final_profile.json"

    exit_code = main(
        [
            "--csv",
            str(csv_path),
            "--resume",
            str(resume_path),
            "--config",
            str(config_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["candidate_id"] == "candidates"
    assert payload["full_name"] == "Jane Doe"
    assert payload["emails"] == []
    assert payload["phones"] == []
    assert payload["location"] == {"city": None, "region": None, "country": None}
    assert payload["links"] == {
        "linkedin": None,
        "github": None,
        "portfolio": None,
        "other": [],
    }
    assert payload["headline"] is None
    assert payload["years_experience"] is None
    assert payload["skills"] == []
    assert payload["experience"] == []
    assert payload["education"] == []
    assert isinstance(payload["provenance"], list)
    assert any(record["field"] == "full_name" for record in payload["provenance"])
    assert isinstance(payload["overall_confidence"], float)
    assert set(payload.keys()) == {
        "candidate_id",
        "full_name",
        "emails",
        "phones",
        "location",
        "links",
        "headline",
        "years_experience",
        "skills",
        "experience",
        "education",
        "provenance",
        "overall_confidence",
    }


def test_main_reports_missing_config_file(tmp_path, capsys):
    csv_path = tmp_path / "candidates.csv"
    csv_path.write_text("name,email\nJane Doe,jane@example.com\n", encoding="utf-8")

    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Jane Doe\nPython\n", encoding="utf-8")

    missing_config_path = tmp_path / "missing-config.json"
    output_path = tmp_path / "final_profile.json"

    exit_code = main(
        [
            "--csv",
            str(csv_path),
            "--resume",
            str(resume_path),
            "--config",
            str(missing_config_path),
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "config file" in captured.err.lower()
    assert "not found" in captured.err.lower()


def test_assignment_config_full_name_only(tmp_path):
    csv_path = tmp_path / "candidates.csv"
    csv_path.write_text("name,email\nJohn Doe,john.doe@gmail.com\n", encoding="utf-8")

    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("John Doe\n", encoding="utf-8")

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "fields": [
                    {"path": "full_name"}
                ],
                "include_confidence": False,
                "include_provenance": False,
                "on_missing": "null",
            }
        ),
        encoding="utf-8",
    )

    output_path = tmp_path / "final_profile.json"

    exit_code = main(
        [
            "--csv",
            str(csv_path),
            "--resume",
            str(resume_path),
            "--config",
            str(config_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {"full_name": "John Doe"}


def test_assignment_config_map_name_and_primary_email(tmp_path):
    csv_path = tmp_path / "candidates.csv"
    csv_path.write_text("name,email\nJohn Doe,john.doe@gmail.com\n", encoding="utf-8")

    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("John Doe\n", encoding="utf-8")

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "fields": [
                    {"path": "name", "from": "full_name"},
                    {"path": "primary_email", "from": "emails[0]"},
                ],
                "include_confidence": False,
                "include_provenance": False,
                "on_missing": "null",
            }
        ),
        encoding="utf-8",
    )

    output_path = tmp_path / "final_profile.json"

    exit_code = main(
        [
            "--csv",
            str(csv_path),
            "--resume",
            str(resume_path),
            "--config",
            str(config_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {"name": "John Doe", "primary_email": "john.doe@gmail.com"}


def test_assignment_config_phone_e164_normalization(tmp_path):
    csv_path = tmp_path / "candidates.csv"
    csv_path.write_text("name,email,phone\nJohn Doe,john.doe@gmail.com,(415) 555-2671\n", encoding="utf-8")

    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("John Doe\n", encoding="utf-8")

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "fields": [
                    {"path": "phone", "from": "phones[0]", "normalize": "E164"}
                ],
                "include_confidence": False,
                "include_provenance": False,
                "on_missing": "null",
            }
        ),
        encoding="utf-8",
    )

    output_path = tmp_path / "final_profile.json"

    exit_code = main(
        [
            "--csv",
            str(csv_path),
            "--resume",
            str(resume_path),
            "--config",
            str(config_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {"phone": "+14155552671"}
    csv_path = tmp_path / "candidates.csv"
    csv_path.write_text("name,email\nJane Doe,jane@example.com\n", encoding="utf-8")

    resume_path = tmp_path / "resume.txt"
    resume_path.write_text(
        "Jane Doe\n\nSkills:\nPython\nSQL\nMachine Learning\n", encoding="utf-8"
    )

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "projection": {
                    "fields": ["candidate_id", "full_name", "emails", "skills", "overall_confidence"],
                    "include_confidence": True,
                    "include_provenance": False,
                    "on_missing": "null",
                },
                "confidence": {"csv": 0.95, "resume": 0.8},
            }
        ),
        encoding="utf-8",
    )

    output_path = tmp_path / "final_profile.json"

    exit_code = main(
        [
            "--csv",
            str(csv_path),
            "--resume",
            str(resume_path),
            "--config",
            str(config_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert isinstance(payload["skills"], list)
    assert [skill["name"] for skill in payload["skills"]] == ["Python", "SQL", "Machine Learning"]


def test_assignment_config_links_and_skill_list_resolution(tmp_path):
    csv_path = tmp_path / "candidates.csv"
    csv_path.write_text("name,email\nJohn Doe,john.doe@gmail.com\n", encoding="utf-8")

    resume_path = tmp_path / "resume.txt"
    resume_path.write_text(
        "John Doe\n\nSkills:\nPython\nSQL\n\nLinks:\nlinkedin: https://linkedin.com/in/johndoe\n",
        encoding="utf-8",
    )

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "fields": [
                    {"path": "linkedin", "from": "links.linkedin", "type": "string"},
                    {"path": "skills", "from": "skills[].name", "type": "string[]"},
                ],
                "include_confidence": False,
                "include_provenance": False,
                "on_missing": "null",
            }
        ),
        encoding="utf-8",
    )

    output_path = tmp_path / "final_profile.json"

    exit_code = main(
        [
            "--csv",
            str(csv_path),
            "--resume",
            str(resume_path),
            "--config",
            str(config_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["linkedin"] == "https://linkedin.com/in/johndoe"
    assert payload["skills"] == ["Python", "SQL"]


def test_resume_experience_and_education_parsing(tmp_path):
    csv_path = tmp_path / "candidates.csv"
    csv_path.write_text("name,email\nJane Doe,jane@example.com\n", encoding="utf-8")

    resume_path = tmp_path / "resume.txt"
    resume_path.write_text(
        "Jane Doe\n\nExperience:\nGoogle - Software Engineer (2020-Present)\n\nEducation:\nB.Tech Computer Science, Stanford University (2020)\n",
        encoding="utf-8",
    )

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "projection": {
                    "fields": [
                        "candidate_id",
                        "full_name",
                        "emails",
                        "experience",
                        "education",
                        "overall_confidence",
                    ],
                    "include_confidence": True,
                    "include_provenance": False,
                    "on_missing": "null",
                },
                "confidence": {"csv": 0.95, "resume": 0.8},
            }
        ),
        encoding="utf-8",
    )

    output_path = tmp_path / "final_profile.json"

    exit_code = main(
        [
            "--csv",
            str(csv_path),
            "--resume",
            str(resume_path),
            "--config",
            str(config_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["experience"][0]["company"] == "Google"
    assert payload["experience"][0]["title"] == "Software Engineer"
    assert payload["experience"][0]["start"] == "2020-01"
    assert payload["experience"][0]["end"] is None
    assert payload["education"][0]["institution"] == "Stanford University"
    assert payload["education"][0]["degree"] == "B.Tech"
    assert payload["education"][0]["field"] == "Computer Science"
    assert payload["education"][0]["end_year"] == 2020

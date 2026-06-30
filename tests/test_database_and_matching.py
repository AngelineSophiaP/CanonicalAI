import pytest
import sqlite3
import json
from candidate_transformer.db import init_db, save_candidate_profile, get_all_candidates, get_candidate, clear_db, DB_PATH
from candidate_transformer.models.candidate import ParseResult
from candidate_transformer.app import find_matching_candidate, find_matching_candidate_for_github

def test_sqlite_operations():
    # Make sure DB is initialized and clean
    init_db()
    clear_db()
    
    # Check that it's empty
    candidates = get_all_candidates()
    assert len(candidates) == 0
    
    # Save a profile
    profile_data = {
        "candidate_id": "test_candidate",
        "full_name": "Test User",
        "emails": ["test@example.com"],
        "phones": ["+1 555 123 4567"],
        "skills": [{"name": "python", "confidence": 0.95, "sources": ["csv"]}],
        "overall_confidence": 0.95
    }
    
    save_candidate_profile(
        candidate_id="test_candidate",
        full_name="Test User",
        email="test@example.com",
        phone="+1 555 123 4567",
        github_username="test_github",
        profile_dict=profile_data,
        raw_results=[]
    )
    
    # Retrieve it
    candidates = get_all_candidates()
    assert len(candidates) == 1
    assert candidates[0]["candidate_id"] == "test_candidate"
    assert candidates[0]["full_name"] == "Test User"
    assert candidates[0]["email"] == "test@example.com"
    assert candidates[0]["phone"] == "+1 555 123 4567"
    assert candidates[0]["github_username"] == "test_github"
    
    loaded_profile = json.loads(candidates[0]["profile_json"])
    assert loaded_profile["candidate_id"] == "test_candidate"
    assert loaded_profile["overall_confidence"] == 0.95
    
    # Fetch specific candidate
    c = get_candidate("test_candidate")
    assert c is not None
    assert c["full_name"] == "Test User"
    
    # Clear DB and check again
    clear_db()
    candidates = get_all_candidates()
    assert len(candidates) == 0

def test_resume_matching_logic():
    csv_candidates = [
        {
            "candidate_id": "madhu_id",
            "name": "Madhu Rithika",
            "email": "madhurithika22@gmail.com",
            "phone": "+91 99999 88888",
            "github_url": "https://github.com/madhurithika22"
        },
        {
            "candidate_id": "jane_id",
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
            "phone": "555-123-4567",
            "github_url": ""
        }
    ]
    
    # Exact email match
    res_pr1 = ParseResult(
        source="resume",
        raw={
            "email": "madhurithika22@gmail.com",
            "full_name": "Madhu Rithika",
            "phones": [],
            "links": {}
        }
    )
    assert find_matching_candidate(res_pr1, csv_candidates) == "madhu_id"
    
    # Fuzzy name match
    res_pr2 = ParseResult(
        source="resume",
        raw={
            "email": "",
            "full_name": "Jane D.", # close to Jane Doe
            "phones": [],
            "links": {}
        }
    )
    assert find_matching_candidate(res_pr2, csv_candidates) == "jane_id"
    
    # Github username match
    res_pr3 = ParseResult(
        source="resume",
        raw={
            "email": "",
            "full_name": "",
            "phones": [],
            "links": {"github": "https://github.com/madhurithika22"}
        }
    )
    assert find_matching_candidate(res_pr3, csv_candidates) == "madhu_id"
    
    # Unmatched
    res_pr_unmatched = ParseResult(
        source="resume",
        raw={
            "email": "unknown@example.com",
            "full_name": "Unknown Candidate",
            "phones": [],
            "links": {}
        }
    )
    assert find_matching_candidate(res_pr_unmatched, csv_candidates) is None

def test_github_matching_logic():
    csv_candidates = [
        {
            "candidate_id": "madhu_id",
            "name": "Madhu Rithika",
            "email": "madhurithika22@gmail.com",
            "phone": "+91 99999 88888",
            "github_url": "https://github.com/madhurithika22"
        }
    ]
    
    # Matching by Github URL
    gh_pr1 = ParseResult(
        source="github",
        raw={
            "name": "Madhu Rithika",
            "email": "",
            "links": {"github": "https://github.com/madhurithika22"}
        }
    )
    assert find_matching_candidate_for_github(gh_pr1, csv_candidates) == "madhu_id"

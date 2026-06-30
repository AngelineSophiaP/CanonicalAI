import sqlite3
import json
import os
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "pipeline.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            candidate_id TEXT PRIMARY KEY,
            full_name TEXT,
            email TEXT,
            phone TEXT,
            github_username TEXT,
            profile_json TEXT,
            raw_results_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_candidate_profile(
    candidate_id: str, 
    full_name: Optional[str], 
    email: Optional[str], 
    phone: Optional[str], 
    github_username: Optional[str], 
    profile_dict: dict, 
    raw_results: list
):
    init_db()  # Ensure tables exist
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO candidates (
            candidate_id, 
            full_name, 
            email, 
            phone, 
            github_username, 
            profile_json, 
            raw_results_json, 
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(candidate_id) DO UPDATE SET
            full_name=excluded.full_name,
            email=excluded.email,
            phone=excluded.phone,
            github_username=excluded.github_username,
            profile_json=excluded.profile_json,
            raw_results_json=excluded.raw_results_json,
            updated_at=CURRENT_TIMESTAMP
    """, (
        candidate_id.strip(),
        full_name.strip() if full_name else None,
        email.strip() if email else None,
        phone.strip() if phone else None,
        github_username.strip() if github_username else None,
        json.dumps(profile_dict),
        json.dumps(raw_results)
    ))
    conn.commit()
    conn.close()

def get_all_candidates() -> List[Dict[str, Any]]:
    init_db()  # Ensure DB is created
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candidates ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_candidate(candidate_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def clear_db():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM candidates")
    conn.commit()
    conn.close()

def delete_candidate(candidate_id: str):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM candidates WHERE candidate_id = ?", (candidate_id,))
    conn.commit()
    conn.close()

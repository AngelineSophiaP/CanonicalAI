import os
import re
import tempfile
import json
import logging
from pathlib import Path
from thefuzz import fuzz

# Starlette imports for ASGI web application
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse, FileResponse
from starlette.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

# Import pipeline backend components
from inputs.csv_source_adapter import CSVSourceAdapter
from inputs.resume_source_adapter import ResumeSourceAdapter
from inputs.github_adapter import GitHubSourceAdapter, resolve_github_handle
from merger.merge_engine import MergeEngine
from models.candidate import ParseResult
from validators import validate_canonical_profile
from db import init_db, save_candidate_profile, get_all_candidates, get_candidate, clear_db, delete_candidate
from projection.projector import Projector

# Initialize database
init_db()

# Logger setup
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("app")

# --- Matching Algorithm Helper Functions ---
def are_names_similar(name1: str, name2: str) -> bool:
    # 1. Clean names by removing spaces, numbers, and punctuation
    c1 = re.sub(r'[^a-zA-Z]', '', name1).lower()
    c2 = re.sub(r'[^a-zA-Z]', '', name2).lower()
    if not c1 or not c2:
        return False
        
    # Check if one contains the other and they share the same starting characters (at least 4)
    if (c1 in c2 or c2 in c1) and c1[:4] == c2[:4]:
        return True
        
    # 2. Split camel case just in case
    n1_split = re.sub(r'([a-z])([A-Z])', r'\1 \2', name1.strip())
    n2_split = re.sub(r'([a-z])([A-Z])', r'\1 \2', name2.strip())
    
    n1 = n1_split.lower().strip()
    n2 = n2_split.lower().strip()
    
    w1 = [w.strip(".,") for w in n1.split() if w.strip(".,")]
    w2 = [w.strip(".,") for w in n2.split() if w.strip(".,")]
    
    # Avoid matching if either name is single word/first name only
    if len(w1) <= 1 or len(w2) <= 1:
        return False
        
    # Check strict character edit distance ratio
    clean_n1 = " ".join(w1)
    clean_n2 = " ".join(w2)
    ratio = fuzz.ratio(clean_n1, clean_n2)
    if ratio >= 85:
        return True
        
    # Check if first and last name initials match, e.g. "Jane Doe" vs "Jane D."
    if w1[0] == w2[0] and (w1[-1].startswith(w2[-1]) or w2[-1].startswith(w1[-1])):
        return True
        
    return False

def find_matching_candidate(resume_pr: ParseResult, csv_candidates: list) -> str | None:
    raw = resume_pr.raw
    resume_email = (raw.get("emails") or [None])[0] if isinstance(raw.get("emails"), list) else (raw.get("email") or "")
    resume_phones = raw.get("phones") or []
    resume_name = raw.get("full_name") or ""
    resume_links = raw.get("links") or {}
    
    # Try email match
    if resume_email:
        for cc in csv_candidates:
            cc_email = cc.get("email") or ""
            if cc_email.lower() == resume_email.lower():
                return cc["candidate_id"]
                
    # Try phone match
    if resume_phones:
        for cc in csv_candidates:
            cc_phone = cc.get("phone") or ""
            if cc_phone:
                cc_digits = "".join(filter(str.isdigit, cc_phone))
                if len(cc_digits) >= 7:
                    for p in resume_phones:
                        p_digits = "".join(filter(str.isdigit, p))
                        if len(p_digits) >= 7 and (p_digits in cc_digits or cc_digits in p_digits):
                            return cc["candidate_id"]
                        
    # Try name fuzzy match
    if resume_name:
        for cc in csv_candidates:
            cc_name = cc.get("name") or cc.get("full_name") or ""
            if cc_name and are_names_similar(cc_name, resume_name):
                return cc["candidate_id"]
                    
    # Try github link match
    resume_github = resume_links.get("github") or ""
    if resume_github:
        for cc in csv_candidates:
            cc_gh = cc.get("github_url") or cc.get("github_username") or ""
            if cc_gh and (cc_gh.lower() in resume_github.lower() or resume_github.lower() in cc_gh.lower()):
                return cc["candidate_id"]
                
    return None

def find_matching_candidate_for_github(gh_pr: ParseResult, csv_candidates: list) -> str | None:
    raw = gh_pr.raw
    gh_name = raw.get("name") or ""
    gh_email = raw.get("email") or ""
    gh_links = raw.get("links") or {}
    gh_url = gh_links.get("github") or ""
    
    # Try github URL/username match
    if gh_url:
        for cc in csv_candidates:
            cc_gh = cc.get("github_url") or cc.get("github_username") or ""
            if cc_gh and (cc_gh.lower() in gh_url.lower() or gh_url.lower() in cc_gh.lower()):
                return cc["candidate_id"]
                
    # Try email match
    if gh_email:
        for cc in csv_candidates:
            cc_email = cc.get("email") or ""
            if cc_email.lower() == gh_email.lower():
                return cc["candidate_id"]
                
    # Try name fuzzy match
    if gh_name:
        for cc in csv_candidates:
            cc_name = cc.get("name") or cc.get("full_name") or ""
            if cc_name and are_names_similar(cc_name, gh_name):
                return cc["candidate_id"]
                    
    return None

# --- Results Deduplication Helper ---
def deduplicate_results(results: list) -> list:
    seen = set()
    unique = []
    for pr in results:
        meta_str = str(pr.metadata.get("path") or pr.metadata.get("filename") or pr.metadata.get("username") or pr.metadata.get("row") or "")
        try:
            raw_str = json.dumps(pr.raw, sort_keys=True)
        except Exception:
            raw_str = str(pr.raw)
        key = (pr.source, meta_str, raw_str)
        if key not in seen:
            seen.add(key)
            unique.append(pr)
    return unique


# --- Web Handlers ---
async def serve_home(request):
    """Serve index.html dashboard home page."""
    return FileResponse("static/index.html")

async def get_candidates(request):
    """Get summarized candidate listing."""
    db_cands = get_all_candidates()
    res = []
    for c in db_cands:
        try:
            profile = json.loads(c["profile_json"])
            overall_confidence = profile.get("overall_confidence", 0.8)
        except Exception:
            overall_confidence = 0.8
        res.append({
            "candidate_id": c["candidate_id"],
            "full_name": c["full_name"],
            "email": c["email"],
            "github_username": c["github_username"],
            "overall_confidence": overall_confidence
        })
    return JSONResponse(res)

async def get_candidate_details(request):
    """Get single candidate detail profile."""
    cid = request.path_params["cid"]
    candidate = get_candidate(cid)
    if not candidate:
        return JSONResponse({"error": "Candidate not found"}, status_code=404)
    return JSONResponse({
        "candidate_id": candidate["candidate_id"],
        "full_name": candidate["full_name"],
        "email": candidate["email"],
        "phone": candidate["phone"],
        "github_username": candidate["github_username"],
        "merged": json.loads(candidate["profile_json"]),
        "raw_results": json.loads(candidate["raw_results_json"])
    })

async def project_candidate(request):
    """Dynamically project selected candidate fields."""
    cid = request.path_params["cid"]
    candidate = get_candidate(cid)
    if not candidate:
        return JSONResponse({"error": "Candidate not found"}, status_code=404)
    
    try:
        body = await request.json()
    except Exception:
        body = {}
        
    fields = body.get("fields", [])
    merged_profile = json.loads(candidate["profile_json"])
    
    # Build specifications based on active switches
    specs = [{"path": f, "from": f} for f in fields]
    projector = Projector(specs, default_on_missing="null")
    projected = projector.project(merged_profile)
    
    return JSONResponse(projected)

async def wipe_database(request):
    """Clear all records from DB."""
    clear_db()
    return JSONResponse({"status": "success"})

async def process_pipeline(request):
    """Execute ingestion pipeline for incoming CSV/Resumes/GitHub parameters."""
    try:
        form = await request.form()
    except Exception:
        return JSONResponse({"error": "Failed to parse form upload"}, status_code=400)
    
    csv_upload = form.get("csv_file")
    resumes_upload = form.getlist("resumes")
    github_usernames_input = form.get("github_usernames", "")
    
    # 1. Seed candidate records from database (with duplicate self-healing)
    db_candidates = get_all_candidates()
    csv_candidates_info = []
    grouped_results = {}
    duplicates_to_delete = set()
    
    for c in db_candidates:
        cid = c["candidate_id"]
        c_name = c["full_name"] or ""
        c_email = c["email"] or ""
        c_phone = c["phone"] or ""
        c_gh = c["github_username"] or ""
        c_gh_url = f"https://github.com/{c_gh}" if c_gh else ""
        
        matched_cid = None
        for cc in csv_candidates_info:
            if c_email and cc["email"] and c_email.lower() == cc["email"].lower():
                matched_cid = cc["candidate_id"]
                break
            if c_gh and cc["github_url"] and c_gh.lower() in cc["github_url"].lower():
                matched_cid = cc["candidate_id"]
                break
            if c_name and cc["name"] and are_names_similar(c_name, cc["name"]):
                matched_cid = cc["candidate_id"]
                break
            if c_phone and cc["phone"]:
                cc_dig = "".join(filter(str.isdigit, cc["phone"]))
                c_dig = "".join(filter(str.isdigit, c_phone))
                if len(cc_dig) >= 7 and len(c_dig) >= 7 and (cc_dig in c_dig or c_dig in cc_dig):
                    matched_cid = cc["candidate_id"]
                    break
                    
        try:
            db_results = [ParseResult(**r) for r in json.loads(c["raw_results_json"])]
        except Exception:
            db_results = []
            
        if matched_cid:
            grouped_results.setdefault(matched_cid, []).extend(db_results)
            duplicates_to_delete.add(cid)
        else:
            csv_candidates_info.append({
                "candidate_id": cid,
                "name": c_name,
                "email": c_email,
                "phone": c_phone,
                "github_url": c_gh_url
            })
            grouped_results[cid] = db_results

    # 2. Ingest CSV upload
    csv_records = []
    if csv_upload and csv_upload.filename:
        # Save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(await csv_upload.read())
            tmp_path = tmp.name
        
        csv_adapter = CSVSourceAdapter(tmp_path)
        csv_records = csv_adapter.read()
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
            
        for pr in csv_records:
            raw = pr.raw
            first = raw.get("first_name") or ""
            last = raw.get("last_name") or ""
            name = raw.get("name") or f"{first} {last}".strip()
            if name:
                pr.raw["name"] = name
            email = raw.get("email") or ""
            phone = raw.get("phone") or ""
            github_url = raw.get("github_url") or ""
            
            matched_cid = None
            for cc in csv_candidates_info:
                if email and cc["email"] and email.lower() == cc["email"].lower():
                    matched_cid = cc["candidate_id"]
                    break
                if github_url and cc["github_url"] and github_url.lower() in cc["github_url"].lower():
                    matched_cid = cc["candidate_id"]
                    break
                if name and cc["name"] and are_names_similar(name, cc["name"]):
                    matched_cid = cc["candidate_id"]
                    break
                    
            if matched_cid:
                grouped_results.setdefault(matched_cid, []).append(pr)
            else:
                candidate_id = email or github_url or name.lower().replace(" ", "_") or f"cand_{len(csv_candidates_info)}"
                csv_candidates_info.append({
                    "candidate_id": candidate_id,
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "github_url": github_url
                })
                grouped_results[candidate_id] = [pr]

    # 3. Fetch GitHub profiles
    github_records = []
    if github_usernames_input:
        usernames = [u.strip() for u in github_usernames_input.split(",") if u.strip()]
        for username in usernames:
            gh_adapter = GitHubSourceAdapter(username)
            gh_prs = gh_adapter.read()
            github_records.extend(gh_prs)

    # 4. Ingest Resume uploads
    resume_records = []
    for res_file in resumes_upload:
        if not res_file.filename:
            continue
        suffix = Path(res_file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await res_file.read())
            tmp_path = tmp.name
        
        resume_adapter = ResumeSourceAdapter(tmp_path)
        res_prs = resume_adapter.read()
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
            
        for pr in res_prs:
            pr.metadata["filename"] = res_file.filename
            resume_records.append(pr)

    # Match GitHub profiles to CSV list
    for gh_pr in github_records:
        matching_cid = find_matching_candidate_for_github(gh_pr, csv_candidates_info)
        if matching_cid:
            grouped_results.setdefault(matching_cid, []).append(gh_pr)
        else:
            username = gh_pr.metadata.get("username") or ""
            name = gh_pr.raw.get("name") or ""
            email = gh_pr.raw.get("email") or ""
            cid = username or name.lower().replace(" ", "_") or f"unmatched_github_{len(grouped_results)}"
            grouped_results[cid] = [gh_pr]
            csv_candidates_info.append({
                "candidate_id": cid,
                "name": name,
                "email": email,
                "phone": "",
                "github_url": f"https://github.com/{username}" if username else ""
            })

    # Match Resume profiles to CSV list
    for r_pr in resume_records:
        matching_cid = find_matching_candidate(r_pr, csv_candidates_info)
        if matching_cid:
            grouped_results.setdefault(matching_cid, []).append(r_pr)
        else:
            email = (r_pr.raw.get("emails") or [None])[0] if isinstance(r_pr.raw.get("emails"), list) else (r_pr.raw.get("email") or "")
            name = r_pr.raw.get("full_name") or ""
            cid = email or name.lower().replace(" ", "_") or f"unmatched_resume_{len(grouped_results)}"
            grouped_results[cid] = [r_pr]
            csv_candidates_info.append({
                "candidate_id": cid,
                "name": name,
                "email": email,
                "phone": (r_pr.raw.get("phones") or [None])[0] if isinstance(r_pr.raw.get("phones"), list) else "",
                "github_url": ""
            })

    # 5. Merge and Save unified records
    merge_engine = MergeEngine()
    processed_count = 0
    
    for cid, results in grouped_results.items():
        results = deduplicate_results(results)
        if not results:
            continue
            
        profile = merge_engine.merge(results, candidate_id=cid)
        validated_profile = validate_canonical_profile(profile)
        
        emails_str = validated_profile.emails[0] if validated_profile.emails else None
        phones_str = validated_profile.phones[0] if validated_profile.phones else None
        gh_link = validated_profile.links.get("github") or ""
        gh_username = resolve_github_handle(gh_link) if gh_link else None
        
        raw_ser = [pr.dict() for pr in results]
        
        save_candidate_profile(
            candidate_id=cid,
            full_name=validated_profile.full_name,
            email=emails_str,
            phone=phones_str,
            github_username=gh_username,
            profile_dict=validated_profile.dict(),
            raw_results=raw_ser
        )
        processed_count += 1
        
    # Delete obsolete database matches
    for dup_cid in duplicates_to_delete:
        delete_candidate(dup_cid)
        
    return JSONResponse({"status": "success", "processed_count": processed_count})


# --- Routing Specification ---
app = Starlette(
    routes=[
        Route("/", serve_home),
        Route("/api/candidates", get_candidates),
        Route("/api/candidates/{cid}", get_candidate_details),
        Route("/api/candidates/{cid}/project", project_candidate, methods=["POST"]),
        Route("/api/pipeline/clear", wipe_database, methods=["POST"]),
        Route("/api/pipeline/process", process_pipeline, methods=["POST"]),
        Mount("/static", app=StaticFiles(directory="static")),
    ],
    middleware=[
        Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    ]
)

if __name__ == "__main__":
    import uvicorn
    LOGGER.info("Starting candidate pipeline dashboard on http://localhost:8501")
    uvicorn.run("app:app", host="localhost", port=8501, log_level="info")
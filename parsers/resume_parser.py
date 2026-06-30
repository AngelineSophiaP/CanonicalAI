"""Resume parser using simple regex/heuristics.

Extracts: full_name, skills, experience, education.
Returns a `ParseResult` with those fields in `raw`.
"""
from __future__ import annotations

from typing import List, Dict, Optional, Tuple, Any
import re
import logging
from pathlib import Path

from models.candidate import ParseResult
from normalizers.date_normalizer import normalize_date_to_yyyy_mm


LOGGER = logging.getLogger("candidate_transformer.parsers.resume_parser")


_HEADER_RE = re.compile(
    r"^\s*(?:[•·*§■\-–—]|\d+\.?\s+)?(?P<header>skills|skillset|technical skills|experience|work experience|education|education and qualifications|professional experience|links|link|projects|key projects|academic projects|personal projects|certifications|credentials|achievements|accomplishments|awards|publications|research|summary|profile|objective|about me)s?\s*:?$",
    re.I,
)

_HEADER_MAPPING = {
    "skills": "skills",
    "skillset": "skills",
    "technical skills": "skills",
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "education": "education",
    "education and qualifications": "education",
    "links": "links",
    "link": "links",
    "projects": "projects",
    "key projects": "projects",
    "academic projects": "projects",
    "personal projects": "projects",
    "certifications": "certifications",
    "credentials": "certifications",
    "licenses": "certifications",
    "achievements": "achievements",
    "accomplishments": "achievements",
    "awards": "achievements",
    "activities": "achievements",
    "publications": "publications",
    "research": "publications",
    "summary": "summary",
    "profile": "summary",
    "objective": "summary",
    "about me": "summary",
}


def _split_sections(text: str) -> Dict[str, str]:
    lines = text.splitlines()
    sections: Dict[str, List[str]] = {}
    current: Optional[str] = None
    buffer: List[str] = []

    for ln in lines:
        ln_strip = ln.strip()
        m = _HEADER_RE.match(ln_strip)
        if m:
            header_matched = m.group("header").lower()
            canonical_header = _HEADER_MAPPING.get(header_matched, header_matched)
            # commit previous
            if current and buffer:
                existing = sections.get(current, [])
                sections[current] = existing + buffer
            current = canonical_header
            buffer = []
            continue

        if current:
            buffer.append(ln)

    if current and buffer:
        existing = sections.get(current, [])
        sections[current] = existing + buffer

    # convert lists to strings
    result: Dict[str, str] = {}
    for k, v in sections.items():
        result[k] = "\n".join(v).strip()
    return result


def _extract_skills(section_text: str) -> List[str]:
    # Split by commas, semicolons, bullets
    parts = re.split(r"[,;·•\n]+", section_text)
    skills = []
    
    # Action verbs and common words in project descriptions that indicate a text/sentence block
    action_verbs = {
        "built", "developed", "implemented", "created", "engineered", 
        "designed", "architected", "managed", "led", "worked", 
        "assisted", "optimized", "integrated", "automated", "achieved",
        "scanned", "detected", "scam", "scams", "enabled", "shortlisted",
        "form", "filling", "banking", "removing"
    }
    
    for p in parts:
        p_clean = p.strip()
        if not p_clean:
            continue
            
        words = p_clean.split()
        if len(words) > 4:
            # Too long for a single skill name (likely a sentence or description)
            continue
            
        first_word = words[0].lower().strip("-,.")
        if first_word in action_verbs:
            # Exclude lines starting with action verbs (projects)
            continue
            
        if not re.search(r"[a-zA-Z0-9]", p_clean):
            continue
            
        skills.append(p_clean)
        
    return skills


def _extract_phones(text: str) -> List[str]:
    phones = []
    try:
        import phonenumbers
        # Find all valid international phone numbers
        for match in phonenumbers.PhoneNumberMatcher(text, "IN"):
            formatted = phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164)
            if formatted not in phones:
                phones.append(formatted)
        for match in phonenumbers.PhoneNumberMatcher(text, "US"):
            formatted = phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164)
            # Avoid adding US duplicates of already matched IN phone digits
            digits = re.sub(r"\D+", "", formatted)
            last_10 = digits[-10:] if len(digits) >= 10 else digits
            
            already_exists = False
            for p in phones:
                p_digits = re.sub(r"\D+", "", p)
                p_last_10 = p_digits[-10:] if len(p_digits) >= 10 else p_digits
                if p_last_10 == last_10:
                    already_exists = True
                    break
            if not already_exists:
                phones.append(formatted)
    except Exception:
        # Robust regex fallback avoiding common year ranges
        phone_re = re.compile(r"\b(?:\+?\d{1,3}[\s\-\.]*)?\(?\d{2,5}\)?[\s\-\.]*\d{3,5}[\s\-\.]*\d{3,5}\b")
        for m in phone_re.finditer(text):
            raw = m.group(0).strip()
            if re.search(r'\b(19|20)\d{2}\s*[-–—]\s*(19|20)\d{2}\b', raw):
                continue
            digits = re.sub(r"\D+", "", raw)
            if len(digits) >= 10:
                phones.append(raw)
    return phones


def _extract_links(section_text: str) -> Dict[str, Any]:
    links: Dict[str, Any] = {}
    for ln in section_text.splitlines():
        raw = ln.strip()
        if not raw:
            continue

        if ":" in raw:
            key, value = [part.strip() for part in raw.split(":", 1)]
            if key and value:
                links[key.lower()] = value
                continue

        if raw.startswith("http"):
            links.setdefault("other", []).append(raw)

    # normalize common link keys
    normalized: Dict[str, Any] = {"other": links.get("other", [])}
    for k, v in list(links.items()):
        lk = k.lower()
        if "linkedin" in lk:
            normalized["linkedin"] = v
        elif "github" in lk:
            normalized["github"] = v
        elif "portfolio" in lk or "website" in lk or "site" in lk:
            normalized["portfolio"] = v
        elif lk == "other":
            continue
        else:
            normalized.setdefault("other", []).append(v)

    # if any URLs present directly in section lines, attempt to classify
    for v in normalized.get("other", [])[:]:
        url = v
        if "github.com" in url and "github" not in normalized:
            normalized["github"] = url
            normalized["other"].remove(v)
        elif "linkedin.com" in url and "linkedin" not in normalized:
            normalized["linkedin"] = url
            normalized["other"].remove(v)
        elif re.search(r"\.(io|me|dev|app|com)(/|$)", url) and "portfolio" not in normalized:
            normalized.setdefault("portfolio", url)
            normalized["other"].remove(v)

    return normalized


def _looks_like_title(text: str) -> bool:
    return bool(re.search(r"\b(engineer|developer|manager|director|analyst|consultant|architect|specialist|administrator|officer|scientist|designer|coordinator|executive|lead|principal)\b", text, re.I))


def _normalize_date_token(value: str, is_start: bool = False) -> Optional[str]:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None

    if cleaned.lower() in {"present", "current", "now", "ongoing"}:
        return None

    normalized = normalize_date_to_yyyy_mm(cleaned)
    if normalized:
        return normalized

    year_match = re.fullmatch(r"(19|20)\d{2}", cleaned)
    if year_match:
        year = year_match.group(0)
        return f"{year}-01" if is_start else f"{year}-12"

    return None


def _parse_date_range(value: str) -> tuple[Optional[str], Optional[str]]:
    parts = re.split(r"\s*(?:-|–|—|\bto\b|\buntil\b)\s*", value, flags=re.I)
    if not parts:
        return None, None
    start = _normalize_date_token(parts[0], is_start=True)
    end = None
    if len(parts) > 1:
        end = _normalize_date_token(parts[1], is_start=False)
    else:
        if not re.search(r"\b(present|current|now|ongoing)\b", value, re.I):
            end = start
    return start, end


def _extract_education(section_text: str) -> List[Dict[str, Optional[str]]]:
    # First split by double newlines to get initial blocks
    raw_blocks = [b.strip() for b in re.split(r"\n\s*\n", section_text) if b.strip()]
    
    # We will refine blocks: split consecutive lines in a block if a line clearly starts a new degree/school entry.
    refined_blocks: List[List[str]] = []
    
    edu_keywords = {
        "bachelor", "master", "b.tech", "btech", "m.tech", "mtech", "b.sc", "bsc",
        "m.sc", "msc", "ph.d", "phd", "hsc", "sslc", "12th", "10th", "diploma", 
        "certificate"
    }
    inst_keywords = {"school", "college", "university", "institute", "academy", "mhss", "cbse", "icse"}
    
    for rb in raw_blocks:
        lines = [l.strip() for l in rb.splitlines() if l.strip()]
        current_sub: List[str] = []
        for ln in lines:
            is_new_edu = False
            ln_words = [w.strip(".,()").lower() for w in ln.split()]
            
            if current_sub:
                # Check if current_sub already has a degree and an institution
                has_degree = False
                has_inst = False
                for prev in current_sub:
                    prev_words = [w.strip(".,()").lower() for w in prev.split()]
                    if any(kw in prev_words for kw in edu_keywords):
                        has_degree = True
                    if any(kw in prev_words for kw in inst_keywords):
                        has_inst = True
                
                # Check if new line has degree or institution
                new_has_degree = any(kw in ln_words for kw in edu_keywords)
                new_has_inst = any(kw in ln_words for kw in inst_keywords)
                
                # If block already has degree and line starts with a new degree
                if has_degree and new_has_degree:
                    is_new_edu = True
                # If block already has institution and line starts with a new institution
                elif has_inst and new_has_inst:
                    is_new_edu = True
                    
            if is_new_edu and current_sub:
                refined_blocks.append(current_sub)
                current_sub = []
            current_sub.append(ln)
        if current_sub:
            refined_blocks.append(current_sub)

    # Now parse each block using the existing logic
    entries: List[Dict[str, Optional[str]]] = []
    for lines in refined_blocks:
        institution = None
        degree = None
        field = None
        end_year = None

        def _split_degree_token(val: str) -> tuple[Optional[str], Optional[str]]:
            if not val:
                return None, None
            m = re.match(r"^(?P<tok>(?:B\.?Tech|BTech|B\.?Sc|BSc|Bachelor|M\.?S|MS|MSc|MBA|Ph\.?D|Phd|Master|Doctor|Associate|Diploma|Certificate))\b", val, re.I)
            if m:
                tok = m.group("tok").strip()
                rest = val[m.end():].strip()
                if rest:
                    return tok, rest
                return tok, None
            m2 = re.search(r"(?P<tok>(?:B\.?Tech|BTech|B\.?Sc|BSc|Bachelor|M\.?S|MS|MSc|MBA|Ph\.?D|Phd|Master|Doctor|Associate|Diploma|Certificate))\b", val, re.I)
            if m2 and m2.start() < 8:
                tok = m2.group("tok").strip()
                rest = m2.group("tok").strip() # default
                rest = val[m2.end():].strip()
                if rest:
                    return tok, rest
                return tok, None
            return None, None

        # Extract date or year from any line, and clean it in place
        for idx, ln in enumerate(lines):
            # 1. Check for range, e.g. "September 2023 - Present"
            range_match = re.search(
                r"\b((?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*)?(?:19|20)\d{2}\s*[-–—]\s*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*)?(?:(?:19|20)\d{2}|present|current|ongoing|now)\b)",
                ln,
                re.I
            )
            if range_match:
                date_str = range_match.group(1).strip()
                start_dt, end_dt = _parse_date_range(date_str)
                year_part = None
                if end_dt:
                    year_part = end_dt.split("-")[0]
                elif start_dt:
                    year_part = start_dt.split("-")[0]
                if year_part:
                    try:
                        end_year = int(year_part)
                    except Exception:
                        pass
                lines[idx] = ln.replace(date_str, "").strip(" ,;()-–—")
                continue

            # 2. Check for single month + year, e.g. "May 2022"
            month_year_match = re.search(
                r"\b((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(?:19|20)\d{2})\b",
                ln,
                re.I
            )
            if month_year_match:
                date_str = month_year_match.group(1).strip()
                try:
                    yr = re.search(r"\b(19|20)\d{2}\b", date_str).group(0)
                    end_year = int(yr)
                except Exception:
                    pass
                lines[idx] = ln.replace(date_str, "").strip(" ,;()-–—")
                continue

            # 3. Check for single year, e.g. "(2022)" or "2022"
            year_match = re.search(r"\b(19|20)\d{2}\b", ln)
            if year_match:
                yr_str = year_match.group(0)
                try:
                    end_year = int(yr_str)
                except Exception:
                    pass
                lines[idx] = re.sub(r"\(?\b" + yr_str + r"\b\)?", "", ln).strip(" ,;()-–—")

        # Try to find institution-looking line
        for ln in lines:
            subparts = [p.strip() for p in ln.split(",") if p.strip()] if "," in ln else [ln]
            for sub in subparts:
                # Skip if the part contains grades or degree keywords instead of an institution
                invalid_inst_keywords = r"\b(cgpa|gpa|percentage|marks|grade|score|class|division|rank|c\.g\.p\.a|bachelor|master|b\.?tech|btech|m\.?tech|mtech|hsc|sslc|diploma|certificate)\b"
                if re.search(invalid_inst_keywords, sub, re.I):
                    continue
                if re.search(r"(University|College|Institute|School|University of|School of|Stanford|MIT|Harvard|MHSS)", sub, re.I):
                    institution = sub
                    break
            if institution:
                break

        if not institution:
            invalid_inst_keywords = r"\b(cgpa|gpa|percentage|marks|grade|score|class|division|rank|c\.g\.p\.a|bachelor|master|b\.?tech|btech|m\.?tech|mtech|hsc|sslc|diploma|certificate)\b"
            candidate_lines = []
            for ln in lines:
                subparts = [p.strip() for p in ln.split(",") if p.strip()] if "," in ln else [ln]
                for sub in subparts:
                    if not re.search(invalid_inst_keywords, sub, re.I):
                        candidate_lines.append(sub)
            if candidate_lines:
                institution = candidate_lines[-1]

        # Degree and field detection
        for ln in lines:
            if re.search(r"\b(Bachelor|Master|B\.?Tech|BTech|M\.?S|MBA|Phd|Doctor|Associate|Diploma|Certificate|HSC|SSLC)\b", ln, re.I):
                deg = ln
                if "," in ln:
                    parts = [p.strip() for p in ln.split(",") if p.strip()]
                    if institution and parts[-1].lower() == institution.lower():
                        degree_part = ", ".join(parts[:-1])
                        degree = degree_part
                        tok, rest = _split_degree_token(degree_part)
                        if tok:
                            degree = tok
                            field = rest
                    else:
                        degree = parts[0]
                        if len(parts) > 1:
                            field = parts[1]
                else:
                    m = re.match(r"^(?P<deg>.+?)\s+in\s+(?P<fld>.+)$", ln, re.I)
                    if m:
                        degree = m.group("deg").strip()
                        field = m.group("fld").strip()
                    else:
                        degree = deg
                        m2 = re.match(
                            r"^(?P<deg_token>(?:B\.?Tech|BTech|B\.?Sc|BSc|Bachelor|M\.?S|MS|MSc|MBA|Ph\.?D|Phd|Master|Doctor|Associate|Diploma|Certificate|HSC|SSLC))\b[\s\.:\-]+(?P<rest>.+)$",
                            deg,
                            re.I,
                        )
                        if m2:
                            degree = m2.group("deg_token").strip()
                            field = m2.group("rest").strip()

        if not degree and lines:
            for ln in lines:
                # Skip if it looks like an institution
                if re.search(r"\b(university|college|institute|school|academy|mhss|engineering)\b", ln, re.I):
                    continue
                m = re.match(r"^(?P<deg>.+?)\s+(?P<fld>[A-Z][a-zA-Z ].+)$", ln)
                if m and len(m.group("fld")) > 2:
                    degree = m.group("deg").strip()
                    field = m.group("fld").strip()
                    break


        entries.append({
            "institution": institution,
            "degree": degree,
            "field": field,
            "end_year": end_year,
        })
    return entries


def _extract_links(section_text: str) -> Dict[str, Any]:
    links: Dict[str, Any] = {}
    for ln in section_text.splitlines():
        raw = ln.strip()
        if not raw:
            continue

        if ":" in raw:
            key, value = [part.strip() for part in raw.split(":", 1)]
            if key and value:
                links[key.lower()] = value
                continue

        if raw.startswith("http"):
            links.setdefault("other", []).append(raw)

    return links


def _parse_experience_header(header: str) -> tuple[Optional[str], Optional[str]]:
    header = header.strip()
    if not header:
        return None, None

    header = re.sub(r"\s*\([^)]*\)$", "", header).strip()

    dash_match = re.match(r"^(?P<left>.+?)\s*[-–—]\s*(?P<right>.+)$", header)
    if dash_match:
        left = dash_match.group("left").strip()
        right = dash_match.group("right").strip()
        if _looks_like_title(right) and not _looks_like_title(left):
            return left, right
        if _looks_like_title(left) and not _looks_like_title(right):
            return right, left
        return left, right

    at_match = re.match(r"^(?P<title>.+?)\s+at\s+(?P<company>.+)$", header, re.I)
    if at_match:
        return at_match.group("company").strip(), at_match.group("title").strip()

    comma_match = re.match(r"^(?P<company>.+?),\s*(?P<title>.+)$", header)
    if comma_match and _looks_like_title(comma_match.group("title")):
        return comma_match.group("company").strip(), comma_match.group("title").strip()

    return None, header


def _extract_experience(section_text: str) -> List[Dict[str, Optional[str]]]:
    entries: List[Dict[str, Optional[str]]] = []
    lines = [l.strip() for l in section_text.splitlines() if l.strip()]
    if not lines:
        return []

    # Group lines into blocks
    blocks: List[List[str]] = []
    current_block: List[str] = []

    # Regex for a date range/token pattern, e.g. "June 2024", "September 2024 - October 2024"
    date_pattern = re.compile(
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*\d{4}"
        r"|\b(?:19|20)\d{2}\s*[-–—]\s*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*\d{4}|present|current|ongoing|\b(?:19|20)\d{2})\b",
        re.I
    )

    for ln in lines:
        is_header = False
        has_date = bool(date_pattern.search(ln))
        has_role_keyword = bool(re.search(r"\b(intern|developer|engineer|analyst|manager|specialist|lead|consultant|technocrates|byts)\b", ln, re.I))
        
        if current_block:
            if has_date and (has_role_keyword or " at " in ln or " - " in ln or len(ln.split()) < 8):
                is_header = True
            elif has_role_keyword and (" at " in ln or " - " in ln) and len(ln.split()) < 8:
                is_header = True

        if is_header and current_block:
            blocks.append(current_block)
            current_block = []

        current_block.append(ln)

    if current_block:
        blocks.append(current_block)

    # Parse each block
    for b in blocks:
        first = b[0]
        start, end = None, None
        
        # 1. Try parenthesized dates at the end of the line (e.g. "(2020-Present)")
        date_match = re.search(r"\(([^)]+)\)$", first)
        if date_match:
            date_range = date_match.group(1).strip()
            first = first[: date_match.start()].strip()
            start, end = _parse_date_range(date_range)
        else:
            # 2. Look for date range pattern in the first line
            m = re.search(
                r"\b((?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*)?(?:19|20)\d{2}\s*[-–—]\s*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*)?(?:(?:19|20)\d{2}|present|current|ongoing|now)\b)",
                first,
                re.I
            )
            if m:
                date_range = m.group(1).strip()
                start, end = _parse_date_range(date_range)
                first = first.replace(date_range, "").strip(" ,;()-–—")
            else:
                # Try single month + year range, e.g. "June 2024"
                m2 = re.search(
                    r"\b((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(?:19|20)\d{2})\b",
                    first,
                    re.I
                )
                if m2:
                    date_range = m2.group(1).strip()
                    start, end = _parse_date_range(date_range)
                    first = first.replace(date_range, "").strip(" ,;()-–—")
                else:
                    # 3. Fallback: find any year or present token
                    date_parts = re.findall(r"\b(?:19|20)\d{2}\b|present|current|now|ongoing", first, re.I)
                    if date_parts:
                        start = _normalize_date_token(date_parts[0], is_start=True)
                        if len(date_parts) > 1:
                            end = _normalize_date_token(date_parts[1], is_start=False)
                        for dp in date_parts:
                            first = re.sub(r"\b" + re.escape(dp) + r"\b", "", first, flags=re.I).strip(" ,;()-–—")

        header_line = first.strip()
        company, title = _parse_experience_header(header_line)
        if not company and not title:
            title = header_line

        # Ignore entry if it looks like a certification/license/credential
        is_certification = False
        for field_val in [company, title]:
            if field_val and re.search(r"\b(certified|certification|certificate|credential|license|award|achievement)\b", field_val, re.I):
                is_certification = True
                break
        if is_certification:
            continue

        summary_lines = []
        for ln in b[1:]:
            summary_lines.append(ln)
            
        summary = "\n".join(summary_lines).strip() if summary_lines else None
        entries.append({"company": company, "title": title, "start": start, "end": end, "summary": summary})

    return entries


def parse_resume_text(text: str, source_path: Optional[str] = None) -> ParseResult:
    """Parse resume text and extract fields.

    Uses simple heuristics. Missing values are returned as None.
    """
    warnings: List[str] = []
    full_name: Optional[str] = None
    skills: List[str] = []
    education = []
    experience = []
    links: Dict[str, Any] = {}
    phones: List[str] = []

    try:
        # name: first non-empty line, prefer lines of 2-4 words
        for ln in text.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            if 1 <= len(ln.split()) <= 4 and re.match(r"^[A-Za-z\-\.' ]+$", ln):
                full_name = ln.strip()
                break

        sections = _split_sections(text)
        if "skills" in sections:
            skills = _extract_skills(sections["skills"])
        if "education" in sections:
            education = _extract_education(sections["education"])
        if "experience" in sections or "work experience" in sections or "professional experience" in sections:
            key = "experience" if "experience" in sections else ("work experience" if "work experience" in sections else "professional experience")
            experience = _extract_experience(sections.get(key, sections.get("experience", "")))
        if "links" in sections or "link" in sections:
            key = "links" if "links" in sections else "link"
            links = _extract_links(sections[key])
        # phones: search entire text
        phones = _extract_phones(text)

        # location heuristics
        location: Dict[str, Optional[str]] = {"city": None, "region": None, "country": None}
        # Look for explicit Location: lines
        for ln in text.splitlines():
            m = re.match(r"^Location:\s*(.+)$", ln.strip(), re.I)
            if m:
                loc = m.group(1).strip()
                parts = [p.strip() for p in re.split(r",|\\-|/", loc) if p.strip()]
                if parts:
                    location["city"] = parts[0]
                if len(parts) > 1:
                    location["region"] = parts[1]
                if len(parts) > 2:
                    location["country"] = parts[-1]
                break
        # fallback: find a short line with comma-separated place
        if not any(location.values()):
            invalid_location_keywords = {
                "school", "college", "university", "institute", "b.tech", "btech", 
                "b.sc", "bsc", "bachelor", "master", "ph.d", "phd", "diploma", 
                "certificate", "intern", "developer", "engineer", "manager", "analyst", 
                "specialist", "mhss", "hsc", "sslc", "cgpa", "gpa", "percentage", "marks"
            }
            for ln in text.splitlines():
                s = ln.strip()
                if not s or len(s) > 60:
                    continue
                s_lower = s.lower()
                if any(kw in s_lower for kw in invalid_location_keywords):
                    continue
                if "," in s:
                    parts = [p.strip() for p in s.split(",") if p.strip()]
                    if 1 < len(parts) <= 3 and all(len(p) > 1 for p in parts):
                        location["city"] = parts[0]
                        if len(parts) > 1:
                            location["region"] = parts[1]
                        if len(parts) > 2:
                            location["country"] = parts[2]
                        break
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.exception("resume parsing failed: %s", exc)
        warnings.append(str(exc))

    raw = {
        "full_name": full_name,
        "skills": skills,
        "education": education,
        "experience": experience,
        "links": links,
        "phones": phones,
        "location": location,
    }

    pr = ParseResult(source="resume", raw=raw, warnings=warnings, metadata={"path": source_path} if source_path else {})
    return pr


def parse_resume_file(path: str) -> ParseResult:
    p = Path(path)
    text = ""
    warnings: List[str] = []
    if not p.exists():
        LOGGER.warning("Resume file not found: %s", p)
        warnings.append("file_not_found")
        return ParseResult(source="resume", raw={}, warnings=warnings, metadata={"path": str(p)})

    try:
        if p.suffix.lower() == ".pdf":
            try:
                import pdfplumber

                with pdfplumber.open(p) as pdf:
                    pages = [page.extract_text() or "" for page in pdf.pages]
                    text = "\n\n".join(pages)
            except Exception as e:  # pragma: no cover - pdf extraction
                LOGGER.exception("pdfplumber failed to extract text: %s", e)
                warnings.append(f"pdf_extraction_failed: {e}")
        else:
            text = p.read_text(encoding='utf-8')
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.exception("Failed to read resume %s: %s", p, exc)
        warnings.append(str(exc))

    return parse_resume_text(text, source_path=str(p))

"""Merge engine for combining parsed candidate data from multiple sources."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple
import json

from models.candidate import CandidateProfile, ExperienceEntry, EducationEntry, ParseResult, ProvenanceRecord, Skill
from normalizers.phone_normalizer import normalize_phone
from normalizers.date_normalizer import normalize_date_to_yyyy_mm
from normalizers.skill_normalizer import normalize_skill
from normalizers.country_normalizer import normalize_country
from merger.confidence_engine import ConfidenceEngine


class MergeEngine:
    """Merge normalized fields from multiple sources into a canonical profile."""

    def __init__(self, confidence_engine: Optional[ConfidenceEngine] = None) -> None:
        self.confidence_engine = confidence_engine or ConfidenceEngine()

    def merge(self, parse_results: Sequence[ParseResult], candidate_id: str) -> CandidateProfile:
        """Merge ordered ParseResults into a CandidateProfile."""
        if not parse_results:
            return CandidateProfile(candidate_id=candidate_id, overall_confidence=0.0)

        profile = CandidateProfile(candidate_id=candidate_id)
        profile.provenance = []

        # Merge scalar fields in priority order: csv first, then resume
        ordered = sorted(parse_results, key=lambda item: self._priority(item.source))

        # Full name
        full_name = self._select_scalar(ordered, ["name", "full_name"], field_name="full_name")
        if full_name:
            profile.full_name = full_name
            profile.provenance.append(ProvenanceRecord(field="full_name", source=self._source_for_value(ordered, ["name", "full_name"], full_name), method="direct", value=full_name))

        # Email
        emails_found = []
        for result in ordered:
            val = result.raw.get("email")
            if isinstance(val, str) and val.strip():
                emails_found.append(val.strip())
            vals = result.raw.get("emails")
            if isinstance(vals, list):
                for v in vals:
                    if isinstance(v, str) and v.strip():
                        emails_found.append(v.strip())
                        
        # Filter dummy emails if we have real ones
        real_emails = [e for e in emails_found if not e.endswith("@github.example.com") and not e.endswith("@example.com")]
        if real_emails:
            final_email = real_emails[0]
        elif emails_found:
            final_email = emails_found[0]
        else:
            final_email = None
            
        if final_email:
            profile.emails = [final_email]
            profile.provenance.append(ProvenanceRecord(
                field="emails",
                source=self._source_for_value(ordered, ["email", "emails"], final_email) or "github",
                method="direct",
                value=final_email,
                index=0
            ))

        # Phone: preserve raw if normalization fails; always keep phone data
        phone_value = self._select_scalar(ordered, ["phone", "phones"], field_name="phone")
        phones_list: List[str] = []
        if phone_value:
            import re
            if len(re.sub(r"[^0-9]", "", phone_value)) >= 7:
                npv = None
                try:
                    npv = normalize_phone(phone_value)
                except Exception:
                    npv = None
                if npv:
                    phones_list.append(npv)
                    profile.provenance.append(ProvenanceRecord(field="phones", source=self._source_for_value(ordered, ["phone", "phones"], phone_value), method="normalized", value=npv, index=0))
                else:
                    # fallback: keep raw phone string
                    phones_list.append(phone_value.strip())
                    profile.provenance.append(ProvenanceRecord(field="phones", source=self._source_for_value(ordered, ["phone", "phones"], phone_value), method="raw", value=phone_value.strip(), index=0))

        # Company/title/headline (simple)
        company = self._select_scalar(ordered, ["current_company", "company"], field_name="company")
        title = self._select_scalar(ordered, ["title", "job_title"], field_name="title")
        if company or title:
            profile.headline = f"{title or ''} at {company or ''}".strip(" at")
            if company:
                profile.provenance.append(ProvenanceRecord(field="headline", source=self._source_for_value(ordered, ["current_company", "company"], company), method="direct", value=profile.headline))

        # Skills from resume raw list or CSV entry if present
        skills_found: List[Tuple[str, str, float]] = []
        for result in ordered:
            raw_skills = result.raw.get("skills")
            if isinstance(raw_skills, list):
                for skill_name in raw_skills:
                    normalized = normalize_skill(skill_name)
                    if normalized:
                        skills_found.append((normalized, result.source, self.confidence_engine.get_base_confidence(result.source)))

        if skills_found:
            deduped: Dict[str, Skill] = {}
            for name, source, _confidence in skills_found:
                if name not in deduped:
                    deduped[name] = Skill(name=name, confidence=0.0, sources=[source])
                else:
                    existing = deduped[name]
                    if source not in existing.sources:
                        existing.sources.append(source)

            # compute confidence per skill using confidence engine
            for skill_name, skill_obj in deduped.items():
                conf = self.confidence_engine.compute_skill_confidence(skill_name, skill_obj.sources, list(parse_results))
                skill_obj.confidence = conf

            profile.skills = list(deduped.values())
            # add provenance per skill value
            for idx, s in enumerate(profile.skills):
                profile.provenance.append(ProvenanceRecord(field="skills", source=",".join(s.sources), method="extracted", value=s.name, index=idx))

        # Experience & education from resume raw lists
        experience_entries: List[ExperienceEntry] = []
        for result in ordered:
            raw_experience = result.raw.get("experience")
            if isinstance(raw_experience, list):
                for item in raw_experience:
                    if isinstance(item, dict):
                        experience_entries.append(
                            ExperienceEntry(
                                company=item.get("company"),
                                title=item.get("title"),
                                start=normalize_date_to_yyyy_mm(item.get("start")),
                                end=normalize_date_to_yyyy_mm(item.get("end")),
                                summary=item.get("summary"),
                            )
                        )
        if experience_entries:
            profile.experience = experience_entries
            # add provenance per experience entry
            for idx, e in enumerate(profile.experience):
                profile.provenance.append(ProvenanceRecord(field="experience", source="resume", method="regex_extraction", value={"company": e.company, "title": e.title}, index=idx))

        # Compute years_experience from experience entries
        def _compute_years(exp_entries: List[ExperienceEntry]) -> Optional[float]:
            from datetime import date

            total_months = 0
            for e in exp_entries:
                if not e.start:
                    continue
                # parse YYYY-MM or YYYY
                try:
                    parts = e.start.split("-")
                    y = int(parts[0])
                    m = int(parts[1]) if len(parts) > 1 else 1
                    start_date = date(y, m, 1)
                except Exception:
                    continue

                if e.end:
                    try:
                        parts = e.end.split("-")
                        ey = int(parts[0])
                        em = int(parts[1]) if len(parts) > 1 else 1
                        end_date = date(ey, em, 1)
                    except Exception:
                        end_date = date.today()
                else:
                    end_date = date.today()

                months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                if months > 0:
                    total_months += months

            if total_months <= 0:
                return None
            years = round(total_months / 12.0, 1)
            return years

        computed_years = _compute_years(profile.experience or [])
        if computed_years is not None:
            profile.years_experience = computed_years
            profile.provenance.append(ProvenanceRecord(field="years_experience", source="resume", method="computed", value=computed_years))

        education_entries: List[EducationEntry] = []
        for result in ordered:
            raw_education = result.raw.get("education")
            if isinstance(raw_education, list):
                for item in raw_education:
                    if isinstance(item, dict):
                        education_entries.append(
                            EducationEntry(
                                institution=item.get("institution"),
                                degree=item.get("degree"),
                                field=item.get("field"),
                                end_year=item.get("end_year"),
                            )
                        )
        if education_entries:
            profile.education = education_entries
            for idx, ed in enumerate(profile.education):
                profile.provenance.append(ProvenanceRecord(field="education", source="resume", method="regex_extraction", value={"institution": ed.institution, "degree": ed.degree, "field": ed.field}, index=idx))

        # Phones: merge phones from parse results and any scalar phone fields
        phones_found: List[str] = []
        for result in ordered:
            raw_phones = result.raw.get("phones")
            if isinstance(raw_phones, list):
                phones_found.extend(raw_phones)
            scalar_phone = result.raw.get("phone")
            if isinstance(scalar_phone, str):
                phones_found.append(scalar_phone)
        # Normalize and dedupe phones but preserve raw values when normalization fails
        normalized_phones: List[str] = []
        for p in phones_found:
            if not p:
                continue
            import re
            if len(re.sub(r"[^0-9]", "", p)) < 7:
                continue
            try:
                np = normalize_phone(p)
            except Exception:
                np = None
            chosen = np if np else p.strip()
            if chosen and chosen not in normalized_phones:
                normalized_phones.append(chosen)
                # append per-value provenance
                src = self._source_for_value(ordered, ["phone", "phones"], p) or "resume"
                method = "normalized" if np else "raw"
                profile.provenance.append(ProvenanceRecord(field="phones", source=src, method=method, value=chosen, index=len(normalized_phones)-1))

        if normalized_phones:
            # merge phones from earlier scalar handling (phones_list) and normalized_phones
            final_phones = []
            for ph in (phones_list + normalized_phones):
                if ph and ph not in final_phones:
                    final_phones.append(ph)
            profile.phones = final_phones

        # Location selection: prefer highest-confidence source
        location_from_results: List[Tuple[Dict[str, Optional[str]], float, str]] = []
        for result in parse_results:
            loc = result.raw.get("location")
            if isinstance(loc, dict):
                score = self.confidence_engine.get_base_confidence(result.source)
                location_from_results.append((loc, score, result.source))

        if location_from_results:
            location_from_results.sort(key=lambda x: x[1], reverse=True)
            chosen_loc, _, chosen_source = location_from_results[0]
            # normalize country code when present
            if chosen_loc.get("country"):
                chosen_loc["country"] = normalize_country(chosen_loc.get("country"))
            profile.location = {"city": chosen_loc.get("city"), "region": chosen_loc.get("region"), "country": chosen_loc.get("country")}
            profile.provenance.append(ProvenanceRecord(field="location", source=chosen_source, method="extracted", value=profile.location))

        links_found: Dict[str, Any] = {}
        for result in ordered:
            raw_links = result.raw.get("links")
            if isinstance(raw_links, dict):
                for key, value in raw_links.items():
                    normalized_key = key.lower()
                    if normalized_key == "other":
                        if value is None:
                            continue
                        if isinstance(value, list):
                            links_found.setdefault("other", []).extend(value)
                        else:
                            links_found.setdefault("other", []).append(value)
                    elif value is not None:
                        links_found[normalized_key] = value
        if links_found:
            merged_links = {**profile.links}
            for key, value in links_found.items():
                if key == "other":
                    existing_other = merged_links.get("other")
                    if isinstance(existing_other, list):
                        merged_links["other"] = existing_other + (value if isinstance(value, list) else [value])
                    else:
                        merged_links["other"] = value if isinstance(value, list) else [value]
                else:
                    merged_links[key] = value
            profile.links = merged_links
            profile.provenance.append(ProvenanceRecord(field="links", source="resume", method="regex_extraction", value=merged_links))

        profile.provenance = self._dedupe_provenance(profile.provenance)
        profile.overall_confidence = self.confidence_engine.compute_overall_confidence(profile)
        return profile

    def _dedupe_provenance(self, records: List[ProvenanceRecord]) -> List[ProvenanceRecord]:
        seen = set()
        deduped: List[ProvenanceRecord] = []
        def _value_key(v: Any) -> Any:
            if v is None:
                return None
            # For dict/list, produce a stable JSON string; fallback to repr
            try:
                if isinstance(v, (dict, list)):
                    return json.dumps(v, sort_keys=True, default=str)
                # simple scalars are fine
                return v
            except Exception:
                return repr(v)

        for record in records:
            val_key = _value_key(getattr(record, "value", None))
            idx_key = getattr(record, "index", None)
            key = (record.field, record.source, record.method, val_key, idx_key)
            if key not in seen:
                seen.add(key)
                deduped.append(record)
        return deduped

    def _select_scalar(self, parse_results: Sequence[ParseResult], keys: Sequence[str], field_name: str) -> Optional[str]:
        for result in parse_results:
            for key in keys:
                value = result.raw.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return None

    def _source_for_value(self, parse_results: Sequence[ParseResult], keys: Sequence[str], value: Optional[str]) -> str:
        for result in parse_results:
            for key in keys:
                candidate = result.raw.get(key)
                if isinstance(candidate, str) and candidate.strip() and candidate.strip() == value:
                    return result.source
        return "unknown"

    def _priority(self, source: str) -> int:
        priority_map = {"csv": 0, "resume": 1}
        return priority_map.get(source.lower(), 99)

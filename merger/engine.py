from models.canonical import CanonicalCandidate
from models.source_models import ParsedCSVRecord, ParsedResumeData, ParsedGitHubData

class CandidateMergeEngine:
    """Stateful upsert engine. Modifies existing profile based on weight rules."""
    
    def upsert_csv(self, profile: CanonicalCandidate, data: ParsedCSVRecord):
        self._set_field(profile, "first_name", data.first_name, data)
        self._set_field(profile, "last_name", data.last_name, data)
        self._set_field(profile.contact, "email", data.email, data, "contact.email")
        self._set_field(profile.contact, "phone", data.phone, data, "contact.phone")
        self._set_field(profile.contact, "github_url", data.github_url, data, "contact.github_url")
        if data.skills:
            from src.utils.skill_engine import extract_canonical_skills
            csv_skills = extract_canonical_skills(data.skills)
            self._merge_skills(profile, csv_skills, data)
        
    def upsert_resume(self, profile: CanonicalCandidate, data: ParsedResumeData):
        self._set_field(profile.contact, "email", data.email, data, "contact.email")
        self._set_field(profile.contact, "phone", data.phone, data, "contact.phone")
        self._merge_skills(profile, data.extracted_skills, data)
        
    def upsert_github(self, profile: CanonicalCandidate, data: ParsedGitHubData):
        self._set_field(profile.contact, "github_url", data.profile_url, data, "contact.github_url")
        self._merge_skills(profile, data.repo_languages + data.bio_skills, data)

    def _set_field(self, target_obj, attr_name: str, new_value, source_data, metadata_key: str = None):
        if not new_value:
            return
            
        key = metadata_key or attr_name
        current_weight = target_obj._weights.get(key, 0) if hasattr(target_obj, '_weights') else 0
        
        # Overwrite if new data comes from a more trusted source
        if source_data.source_weight > current_weight:
            setattr(target_obj, attr_name, new_value)
            
            # Update provenance
            if isinstance(target_obj, CanonicalCandidate):
                target_obj.provenance_metadata[key] = source_data.source_name
                target_obj._weights[key] = source_data.source_weight

    def _merge_skills(self, profile: CanonicalCandidate, canonical_new: list, source_data):
        """
        Stateful skill merge:
        1. Performs a set-union to merge canonical skills and deduplicate.
        2. Updates provenance metadata to track source contribution.
        """
        # 1. Merge Canonical Skills (Taxonomy-backed)
        # We use set union (|) for clean deduplication
        combined_canonical = set(profile.skills) | set(canonical_new)
        profile.skills = sorted(list(combined_canonical))
        
        # 2. Update Provenance Metadata
        # We append the source name to the metadata key, creating a trace of 
        # which sources contributed to the skills list
        existing_sources = profile.provenance_metadata.get("skills", "")
        new_source = source_data.source_name
        
        if new_source not in existing_sources:
            profile.provenance_metadata["skills"] = f"{existing_sources} + {new_source}".strip(" + ")
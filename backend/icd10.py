"""ICD-10 lookup and red flag detection."""
import httpx
from typing import Optional
from config import WHO_CLIENT_ID, WHO_CLIENT_SECRET

# Cache for WHO API token
_who_token_cache: Optional[str] = None


async def get_who_token() -> str:
    """Get access token for WHO ICD API."""
    global _who_token_cache

    if _who_token_cache:
        return _who_token_cache

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://icdaccessmanagement.who.int/connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": WHO_CLIENT_ID,
                "client_secret": WHO_CLIENT_SECRET,
                "scope": "icdapi_access"
            }
        )

        if response.status_code == 200:
            _who_token_cache = response.json()["access_token"]
            return _who_token_cache
        else:
            # Fallback to NLM API if WHO auth fails
            return None


async def lookup_icd10(symptom: str) -> dict:
    """Look up ICD-10 code for a symptom or condition.

    Priority: Local cache → WHO ICD API → NLM Clinical Tables → Fallback
    """
    # Try local cache first for common symptoms (fastest)
    local_result = quick_icd10_lookup(symptom)
    if local_result:
        local_result["source"] = "Daktari Common Symptoms Database"
        local_result["source_url"] = "Local cache based on WHO ICD-10 standards"
        return local_result

    # Try WHO ICD API
    try:
        token = await get_who_token()
        if token:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://id.who.int/icd/release/10/2019/search",
                    params={"q": symptom, "flatResults": "true"},
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                        "Accept-Language": "en",
                        "API-Version": "v2"
                    }
                )

                if resp.status_code == 200:
                    results = resp.json()
                    codes = []
                    for entity in results.get("destinationEntities", [])[:3]:
                        codes.append({
                            "code": entity.get("theCode", "Unknown"),
                            "title": entity.get("title", symptom)
                        })

                    if codes:
                        return {
                            "codes": codes,
                            "source": "WHO ICD-10 International Classification",
                            "source_url": "https://icd.who.int/browse10/2019/en"
                        }
    except Exception:
        pass

    # Fallback: NLM Clinical Tables API (no auth required)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search",
                params={"sf": "code,name", "terms": symptom, "maxList": 3}
            )

            if resp.status_code == 200:
                data = resp.json()
                # Response format: [total, codes, extra_data, display_strings]
                if len(data) >= 4 and data[3]:
                    codes = []
                    for item in data[3][:3]:
                        codes.append({
                            "code": item[0] if len(item) > 0 else "Unknown",
                            "title": item[1] if len(item) > 1 else symptom
                        })
                    return {
                        "codes": codes,
                        "source": "U.S. National Library of Medicine ICD-10-CM",
                        "source_url": "https://clinicaltables.nlm.nih.gov/"
                    }
    except Exception:
        pass

    # Final fallback: return placeholder
    return {
        "codes": [{"code": "R69", "title": "Illness, unspecified"}],
        "source": "ICD-10 Fallback (unspecified illness)",
        "source_url": "https://icd.who.int/browse10/2019/en#/R69"
    }


# Red flag combinations that indicate emergencies
RED_FLAG_COMBOS = {
    frozenset(["chest pain", "shortness of breath"]): "Possible cardiac emergency",
    frozenset(["chest pain", "difficulty breathing"]): "Possible cardiac emergency",
    frozenset(["headache", "stiff neck", "fever"]): "Possible meningitis",
    frozenset(["severe headache", "neck stiffness"]): "Possible meningitis",
    frozenset(["bleeding", "pregnancy"]): "Obstetric emergency",
    frozenset(["bleeding", "pregnant"]): "Obstetric emergency",
    frozenset(["confusion", "fever"]): "Possible cerebral malaria or meningitis",
    frozenset(["altered consciousness", "fever"]): "Possible cerebral malaria or meningitis",
    frozenset(["severe abdominal pain", "fever"]): "Possible acute abdomen",
    frozenset(["stomach pain", "vomiting", "fever"]): "Possible acute abdomen",
    frozenset(["face drooping", "arm weakness"]): "Possible stroke",
    frozenset(["slurred speech", "weakness"]): "Possible stroke",
    frozenset(["severe diarrhea", "blood"]): "Possible dysentery",
    frozenset(["cough", "blood", "weight loss"]): "Possible tuberculosis",
    frozenset(["high fever", "chills", "sweating"]): "Possible severe malaria",
}

# Individual red flag symptoms
SINGLE_RED_FLAGS = {
    "unconscious": "Loss of consciousness - emergency",
    "unresponsive": "Unresponsive patient - emergency",
    "seizure": "Seizure activity - urgent",
    "convulsion": "Convulsion - urgent",
    "severe bleeding": "Severe hemorrhage - emergency",
    "difficulty breathing": "Respiratory distress",
    "cannot breathe": "Respiratory failure - emergency",
    "suicidal": "Mental health crisis - urgent",
    "poisoning": "Possible poisoning - emergency",
    "snake bite": "Envenomation - emergency",
    "severe burn": "Severe burn injury - emergency",
}


def check_red_flags(symptoms: list[str]) -> dict:
    """Check if combination of symptoms indicates emergency.

    Uses keyword matching - no ML needed.
    """
    flags = []
    symptom_lower = [s.lower().strip() for s in symptoms]
    symptom_set = set(symptom_lower)

    # Check single red flags
    for symptom in symptom_lower:
        for keyword, alert in SINGLE_RED_FLAGS.items():
            if keyword in symptom:
                flags.append(alert)
                break

    # Check combination red flags
    for combo, alert in RED_FLAG_COMBOS.items():
        # Check if all keywords in combo are present in any symptom
        combo_found = True
        for keyword in combo:
            keyword_found = False
            for symptom in symptom_lower:
                if keyword in symptom:
                    keyword_found = True
                    break
            if not keyword_found:
                combo_found = False
                break

        if combo_found:
            flags.append(alert)

    # Remove duplicates
    flags = list(set(flags))

    return {
        "red_flags": flags,
        "is_emergency": len(flags) > 0,
        "urgency": "emergency" if len(flags) > 0 else "routine",
        "source": "Daktari Clinical Decision Support",
        "methodology": "Keyword-based symptom pattern matching against known emergency presentations"
    }


# Common symptom to ICD-10 mapping for quick lookup
COMMON_SYMPTOMS = {
    "headache": {"code": "R51", "title": "Headache"},
    "fever": {"code": "R50.9", "title": "Fever, unspecified"},
    "cough": {"code": "R05", "title": "Cough"},
    "abdominal pain": {"code": "R10.9", "title": "Unspecified abdominal pain"},
    "stomach pain": {"code": "R10.9", "title": "Unspecified abdominal pain"},
    "diarrhea": {"code": "R19.7", "title": "Diarrhea, unspecified"},
    "vomiting": {"code": "R11.10", "title": "Vomiting, unspecified"},
    "nausea": {"code": "R11.0", "title": "Nausea"},
    "chest pain": {"code": "R07.9", "title": "Chest pain, unspecified"},
    "back pain": {"code": "M54.9", "title": "Dorsalgia, unspecified"},
    "fatigue": {"code": "R53.83", "title": "Other fatigue"},
    "dizziness": {"code": "R42", "title": "Dizziness and giddiness"},
    "shortness of breath": {"code": "R06.02", "title": "Shortness of breath"},
    "sore throat": {"code": "J02.9", "title": "Acute pharyngitis, unspecified"},
    "runny nose": {"code": "J00", "title": "Acute nasopharyngitis"},
    "body aches": {"code": "M79.1", "title": "Myalgia"},
    "joint pain": {"code": "M25.50", "title": "Pain in unspecified joint"},
    "rash": {"code": "R21", "title": "Rash and other nonspecific skin eruption"},
    "swelling": {"code": "R60.9", "title": "Edema, unspecified"},
    "bleeding": {"code": "R58", "title": "Hemorrhage, not elsewhere classified"},
}


def quick_icd10_lookup(symptom: str) -> Optional[dict]:
    """Quick local lookup for common symptoms."""
    symptom_lower = symptom.lower().strip()
    for key, value in COMMON_SYMPTOMS.items():
        if key in symptom_lower or symptom_lower in key:
            return {"codes": [value], "source": "local"}
    return None

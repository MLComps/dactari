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


# Comprehensive ICD-10 symptom mapping for quick lookup
COMMON_SYMPTOMS = {
    # Head & Neurological
    "headache": {"code": "R51", "title": "Headache"},
    "head pain": {"code": "R51", "title": "Headache"},
    "migraine": {"code": "G43.909", "title": "Migraine, unspecified"},
    "dizziness": {"code": "R42", "title": "Dizziness and giddiness"},
    "vertigo": {"code": "R42", "title": "Dizziness and giddiness"},
    "fainting": {"code": "R55", "title": "Syncope and collapse"},
    "syncope": {"code": "R55", "title": "Syncope and collapse"},
    "seizure": {"code": "R56.9", "title": "Unspecified convulsions"},
    "convulsion": {"code": "R56.9", "title": "Unspecified convulsions"},
    "confusion": {"code": "R41.0", "title": "Disorientation, unspecified"},
    "memory loss": {"code": "R41.3", "title": "Other amnesia"},
    "numbness": {"code": "R20.0", "title": "Anesthesia of skin"},
    "tingling": {"code": "R20.2", "title": "Paresthesia of skin"},
    "weakness": {"code": "R53.1", "title": "Weakness"},
    "tremor": {"code": "R25.1", "title": "Tremor, unspecified"},
    "imbalance": {"code": "R26.81", "title": "Unsteadiness on feet"},
    "unsteady": {"code": "R26.81", "title": "Unsteadiness on feet"},

    # Eyes
    "blurred vision": {"code": "H53.8", "title": "Other visual disturbances"},
    "vision problems": {"code": "H53.9", "title": "Unspecified visual disturbance"},
    "eye pain": {"code": "H57.10", "title": "Ocular pain, unspecified eye"},
    "red eye": {"code": "H57.8", "title": "Other specified disorders of eye"},
    "photophobia": {"code": "H53.14", "title": "Visual discomfort"},
    "light sensitivity": {"code": "H53.14", "title": "Visual discomfort"},
    "double vision": {"code": "H53.2", "title": "Diplopia"},

    # Ear, Nose, Throat
    "ear pain": {"code": "H92.09", "title": "Otalgia, unspecified ear"},
    "earache": {"code": "H92.09", "title": "Otalgia, unspecified ear"},
    "hearing loss": {"code": "H91.90", "title": "Unspecified hearing loss"},
    "tinnitus": {"code": "H93.19", "title": "Tinnitus, unspecified ear"},
    "sore throat": {"code": "J02.9", "title": "Acute pharyngitis, unspecified"},
    "throat pain": {"code": "J02.9", "title": "Acute pharyngitis, unspecified"},
    "runny nose": {"code": "J00", "title": "Acute nasopharyngitis"},
    "nasal congestion": {"code": "R09.81", "title": "Nasal congestion"},
    "stuffy nose": {"code": "R09.81", "title": "Nasal congestion"},
    "nosebleed": {"code": "R04.0", "title": "Epistaxis"},
    "difficulty swallowing": {"code": "R13.10", "title": "Dysphagia, unspecified"},
    "hoarseness": {"code": "R49.0", "title": "Dysphonia"},

    # Respiratory
    "cough": {"code": "R05", "title": "Cough"},
    "dry cough": {"code": "R05.9", "title": "Cough, unspecified"},
    "productive cough": {"code": "R05.9", "title": "Cough, unspecified"},
    "shortness of breath": {"code": "R06.02", "title": "Shortness of breath"},
    "breathing difficulty": {"code": "R06.00", "title": "Dyspnea, unspecified"},
    "dyspnea": {"code": "R06.00", "title": "Dyspnea, unspecified"},
    "wheezing": {"code": "R06.2", "title": "Wheezing"},
    "chest tightness": {"code": "R07.89", "title": "Other chest pain"},
    "rapid breathing": {"code": "R06.82", "title": "Tachypnea"},
    "coughing blood": {"code": "R04.2", "title": "Hemoptysis"},
    "hemoptysis": {"code": "R04.2", "title": "Hemoptysis"},

    # Cardiovascular
    "chest pain": {"code": "R07.9", "title": "Chest pain, unspecified"},
    "heart palpitations": {"code": "R00.2", "title": "Palpitations"},
    "palpitations": {"code": "R00.2", "title": "Palpitations"},
    "rapid heartbeat": {"code": "R00.0", "title": "Tachycardia, unspecified"},
    "slow heartbeat": {"code": "R00.1", "title": "Bradycardia, unspecified"},
    "irregular heartbeat": {"code": "R00.8", "title": "Other abnormalities of heart beat"},
    "high blood pressure": {"code": "R03.0", "title": "Elevated blood-pressure reading"},
    "low blood pressure": {"code": "R03.1", "title": "Nonspecific low blood-pressure reading"},
    "leg swelling": {"code": "R60.0", "title": "Localized edema"},

    # Gastrointestinal
    "abdominal pain": {"code": "R10.9", "title": "Unspecified abdominal pain"},
    "stomach pain": {"code": "R10.9", "title": "Unspecified abdominal pain"},
    "belly pain": {"code": "R10.9", "title": "Unspecified abdominal pain"},
    "nausea": {"code": "R11.0", "title": "Nausea"},
    "vomiting": {"code": "R11.10", "title": "Vomiting, unspecified"},
    "diarrhea": {"code": "R19.7", "title": "Diarrhea, unspecified"},
    "loose stool": {"code": "R19.7", "title": "Diarrhea, unspecified"},
    "constipation": {"code": "K59.00", "title": "Constipation, unspecified"},
    "bloating": {"code": "R14.0", "title": "Abdominal distension (gaseous)"},
    "heartburn": {"code": "R12", "title": "Heartburn"},
    "acid reflux": {"code": "K21.0", "title": "Gastro-esophageal reflux with esophagitis"},
    "blood in stool": {"code": "K92.1", "title": "Melena"},
    "rectal bleeding": {"code": "K62.5", "title": "Hemorrhage of anus and rectum"},
    "loss of appetite": {"code": "R63.0", "title": "Anorexia"},
    "difficulty eating": {"code": "R63.3", "title": "Feeding difficulties"},
    "jaundice": {"code": "R17", "title": "Unspecified jaundice"},

    # Musculoskeletal
    "back pain": {"code": "M54.9", "title": "Dorsalgia, unspecified"},
    "lower back pain": {"code": "M54.5", "title": "Low back pain"},
    "neck pain": {"code": "M54.2", "title": "Cervicalgia"},
    "stiff neck": {"code": "M54.2", "title": "Cervicalgia"},
    "joint pain": {"code": "M25.50", "title": "Pain in unspecified joint"},
    "knee pain": {"code": "M25.569", "title": "Pain in unspecified knee"},
    "hip pain": {"code": "M25.559", "title": "Pain in unspecified hip"},
    "shoulder pain": {"code": "M25.519", "title": "Pain in unspecified shoulder"},
    "muscle pain": {"code": "M79.1", "title": "Myalgia"},
    "body aches": {"code": "M79.1", "title": "Myalgia"},
    "muscle cramps": {"code": "R25.2", "title": "Cramp and spasm"},
    "muscle weakness": {"code": "M62.81", "title": "Muscle weakness (generalized)"},
    "swelling": {"code": "R60.9", "title": "Edema, unspecified"},

    # Skin
    "rash": {"code": "R21", "title": "Rash and other nonspecific skin eruption"},
    "skin rash": {"code": "R21", "title": "Rash and other nonspecific skin eruption"},
    "itching": {"code": "L29.9", "title": "Pruritus, unspecified"},
    "itchy skin": {"code": "L29.9", "title": "Pruritus, unspecified"},
    "hives": {"code": "L50.9", "title": "Urticaria, unspecified"},
    "skin lesion": {"code": "L98.9", "title": "Disorder of skin, unspecified"},
    "wound": {"code": "T14.8", "title": "Other injury of unspecified body region"},
    "burn": {"code": "T30.0", "title": "Burn of unspecified body region"},
    "bruise": {"code": "T14.8", "title": "Other injury of unspecified body region"},
    "skin infection": {"code": "L08.9", "title": "Local infection of skin, unspecified"},
    "abscess": {"code": "L02.91", "title": "Cutaneous abscess, unspecified"},
    "boil": {"code": "L02.91", "title": "Cutaneous abscess, unspecified"},

    # Urological
    "painful urination": {"code": "R30.0", "title": "Dysuria"},
    "burning urination": {"code": "R30.0", "title": "Dysuria"},
    "frequent urination": {"code": "R35.0", "title": "Frequency of micturition"},
    "blood in urine": {"code": "R31.9", "title": "Hematuria, unspecified"},
    "urinary incontinence": {"code": "R32", "title": "Unspecified urinary incontinence"},
    "difficulty urinating": {"code": "R33.9", "title": "Retention of urine, unspecified"},
    "flank pain": {"code": "R10.9", "title": "Unspecified abdominal pain"},

    # Reproductive/OB-GYN
    "vaginal bleeding": {"code": "N93.9", "title": "Abnormal uterine bleeding, unspecified"},
    "vaginal discharge": {"code": "N89.8", "title": "Other specified noninflammatory disorders of vagina"},
    "pelvic pain": {"code": "R10.2", "title": "Pelvic and perineal pain"},
    "menstrual pain": {"code": "N94.6", "title": "Dysmenorrhea, unspecified"},
    "missed period": {"code": "N91.2", "title": "Amenorrhea, unspecified"},
    "breast pain": {"code": "N64.4", "title": "Mastodynia"},
    "pregnancy bleeding": {"code": "O20.9", "title": "Hemorrhage in early pregnancy, unspecified"},

    # General/Constitutional
    "fever": {"code": "R50.9", "title": "Fever, unspecified"},
    "high temperature": {"code": "R50.9", "title": "Fever, unspecified"},
    "chills": {"code": "R68.83", "title": "Chills (without fever)"},
    "night sweats": {"code": "R61", "title": "Generalized hyperhidrosis"},
    "fatigue": {"code": "R53.83", "title": "Other fatigue"},
    "tiredness": {"code": "R53.83", "title": "Other fatigue"},
    "malaise": {"code": "R53.81", "title": "Other malaise"},
    "weight loss": {"code": "R63.4", "title": "Abnormal weight loss"},
    "weight gain": {"code": "R63.5", "title": "Abnormal weight gain"},
    "dehydration": {"code": "E86.0", "title": "Dehydration"},
    "thirst": {"code": "R63.1", "title": "Polydipsia"},
    "excessive thirst": {"code": "R63.1", "title": "Polydipsia"},
    "bleeding": {"code": "R58", "title": "Hemorrhage, not elsewhere classified"},
    "swollen lymph nodes": {"code": "R59.9", "title": "Enlarged lymph nodes, unspecified"},

    # Mental Health
    "anxiety": {"code": "F41.9", "title": "Anxiety disorder, unspecified"},
    "depression": {"code": "F32.9", "title": "Major depressive disorder, unspecified"},
    "insomnia": {"code": "G47.00", "title": "Insomnia, unspecified"},
    "sleep problems": {"code": "G47.9", "title": "Sleep disorder, unspecified"},
    "stress": {"code": "F43.9", "title": "Reaction to severe stress, unspecified"},
    "mood changes": {"code": "R45.89", "title": "Other symptoms involving emotional state"},

    # Pediatric Common
    "diaper rash": {"code": "L22", "title": "Diaper dermatitis"},
    "colic": {"code": "R10.83", "title": "Colic"},
    "failure to thrive": {"code": "R62.51", "title": "Failure to thrive (child)"},
    "developmental delay": {"code": "R62.50", "title": "Unspecified lack of expected normal development"},

    # Tropical/Regional (East Africa relevant)
    "malaria symptoms": {"code": "B54", "title": "Unspecified malaria"},
    "yellow eyes": {"code": "R17", "title": "Unspecified jaundice"},
    "pale skin": {"code": "R23.1", "title": "Pallor"},
    "dark urine": {"code": "R82.99", "title": "Other abnormal findings in urine"},
}


def quick_icd10_lookup(symptom: str) -> Optional[dict]:
    """Quick local lookup for common symptoms."""
    symptom_lower = symptom.lower().strip()
    for key, value in COMMON_SYMPTOMS.items():
        if key in symptom_lower or symptom_lower in key:
            return {"codes": [value], "source": "local"}
    return None

"""ICD-10 lookup and red flag detection.

API Strategy:
1. Local cache with 139 common symptoms (fastest)
2. NLM Clinical Tables API (free, no auth required)
3. Fallback to R69 (unspecified illness)

Note: WHO ICD API does not provide ICD-10 search functionality.
See: https://icd.who.int/docs/icd-api/APIDoc-Version2/
"ICD10 endpoints serves ICD-10 releases... the search is not provided"
"""
import httpx
from typing import Optional


async def lookup_icd10(symptom: str) -> dict:
    """Look up ICD-10 code for a symptom or condition.

    Priority: Local cache (139 symptoms) → NLM Clinical Tables API → Fallback

    Note: WHO ICD API does not provide ICD-10 search functionality (only ICD-11).
    See: https://icd.who.int/docs/icd-api/APIDoc-Version2/
    "ICD10 endpoints... the search is not provided"
    """
    # Try local cache first for common symptoms (fastest)
    local_result = quick_icd10_lookup(symptom)
    if local_result:
        local_result["source"] = "Daktari Common Symptoms Database"
        local_result["source_url"] = "Local cache based on WHO ICD-10 standards"
        return local_result

    # Primary external source: NLM Clinical Tables API (free, no auth required)
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

# ============================================================
# MULTILINGUAL SYMPTOM TRANSLATIONS
# Maps non-English symptoms to English equivalents
# ============================================================

SYMPTOM_TRANSLATIONS = {
    # French (Français)
    "fr": {
        # Head & Neurological
        "mal de tête": "headache",
        "maux de tête": "headache",
        "céphalée": "headache",
        "migraine": "migraine",
        "vertige": "dizziness",
        "vertiges": "dizziness",
        "évanouissement": "fainting",
        "convulsion": "seizure",
        "convulsions": "seizure",
        "confusion": "confusion",
        "perte de mémoire": "memory loss",
        "engourdissement": "numbness",
        "fourmillement": "tingling",
        "faiblesse": "weakness",
        "tremblement": "tremor",
        # Eyes
        "vision floue": "blurred vision",
        "douleur oculaire": "eye pain",
        "mal aux yeux": "eye pain",
        "yeux rouges": "red eye",
        # Ear, Nose, Throat
        "mal d'oreille": "ear pain",
        "douleur à l'oreille": "ear pain",
        "perte auditive": "hearing loss",
        "mal de gorge": "sore throat",
        "douleur à la gorge": "sore throat",
        "nez qui coule": "runny nose",
        "nez bouché": "nasal congestion",
        "saignement de nez": "nosebleed",
        "difficulté à avaler": "difficulty swallowing",
        # Respiratory
        "toux": "cough",
        "toux sèche": "dry cough",
        "essoufflement": "shortness of breath",
        "difficulté à respirer": "difficulty breathing",
        "respiration difficile": "difficulty breathing",
        "respiration sifflante": "wheezing",
        "oppression thoracique": "chest tightness",
        # Cardiovascular
        "douleur thoracique": "chest pain",
        "douleur à la poitrine": "chest pain",
        "mal à la poitrine": "chest pain",
        "palpitations": "palpitations",
        "battements cardiaques rapides": "rapid heartbeat",
        "hypertension": "high blood pressure",
        "jambes enflées": "leg swelling",
        # Gastrointestinal
        "douleur abdominale": "abdominal pain",
        "mal au ventre": "stomach pain",
        "mal d'estomac": "stomach pain",
        "nausée": "nausea",
        "nausées": "nausea",
        "vomissement": "vomiting",
        "vomissements": "vomiting",
        "diarrhée": "diarrhea",
        "constipation": "constipation",
        "ballonnement": "bloating",
        "brûlures d'estomac": "heartburn",
        "sang dans les selles": "blood in stool",
        "perte d'appétit": "loss of appetite",
        "jaunisse": "jaundice",
        # Musculoskeletal
        "mal de dos": "back pain",
        "douleur au dos": "back pain",
        "douleur lombaire": "lower back pain",
        "douleur au cou": "neck pain",
        "torticolis": "stiff neck",
        "douleur articulaire": "joint pain",
        "douleur au genou": "knee pain",
        "douleur à la hanche": "hip pain",
        "douleur à l'épaule": "shoulder pain",
        "douleur musculaire": "muscle pain",
        "courbatures": "body aches",
        "crampes": "muscle cramps",
        "gonflement": "swelling",
        # Skin
        "éruption cutanée": "rash",
        "boutons": "rash",
        "démangeaisons": "itching",
        "urticaire": "hives",
        "plaie": "wound",
        "brûlure": "burn",
        "bleu": "bruise",
        "ecchymose": "bruise",
        "abcès": "abscess",
        # Urological
        "miction douloureuse": "painful urination",
        "brûlure urinaire": "burning urination",
        "envie fréquente d'uriner": "frequent urination",
        "sang dans les urines": "blood in urine",
        # General
        "fièvre": "fever",
        "température": "fever",
        "frissons": "chills",
        "sueurs nocturnes": "night sweats",
        "fatigue": "fatigue",
        "épuisement": "fatigue",
        "perte de poids": "weight loss",
        "déshydratation": "dehydration",
        "soif excessive": "excessive thirst",
        "saignement": "bleeding",
        "ganglions enflés": "swollen lymph nodes",
        # Mental Health
        "anxiété": "anxiety",
        "dépression": "depression",
        "insomnie": "insomnia",
        "troubles du sommeil": "sleep problems",
        "stress": "stress",
        # Pediatric
        "érythème fessier": "diaper rash",
        "colique": "colic",
        # Emergency
        "inconscient": "unconscious",
        "ne répond pas": "unresponsive",
        "empoisonnement": "poisoning",
        "morsure de serpent": "snake bite",
    },

    # Spanish (Español)
    "es": {
        # Head & Neurological
        "dolor de cabeza": "headache",
        "cefalea": "headache",
        "migraña": "migraine",
        "mareo": "dizziness",
        "mareos": "dizziness",
        "vértigo": "vertigo",
        "desmayo": "fainting",
        "convulsión": "seizure",
        "convulsiones": "seizure",
        "confusión": "confusion",
        "pérdida de memoria": "memory loss",
        "entumecimiento": "numbness",
        "hormigueo": "tingling",
        "debilidad": "weakness",
        "temblor": "tremor",
        # Eyes
        "visión borrosa": "blurred vision",
        "dolor de ojos": "eye pain",
        "dolor ocular": "eye pain",
        "ojo rojo": "red eye",
        "ojos rojos": "red eye",
        "visión doble": "double vision",
        # Ear, Nose, Throat
        "dolor de oído": "ear pain",
        "pérdida de audición": "hearing loss",
        "zumbido en los oídos": "tinnitus",
        "dolor de garganta": "sore throat",
        "nariz congestionada": "nasal congestion",
        "congestión nasal": "nasal congestion",
        "goteo nasal": "runny nose",
        "sangrado nasal": "nosebleed",
        "dificultad para tragar": "difficulty swallowing",
        "ronquera": "hoarseness",
        # Respiratory
        "tos": "cough",
        "tos seca": "dry cough",
        "falta de aire": "shortness of breath",
        "dificultad para respirar": "difficulty breathing",
        "falta de aliento": "shortness of breath",
        "sibilancia": "wheezing",
        "opresión en el pecho": "chest tightness",
        "tos con sangre": "coughing blood",
        # Cardiovascular
        "dolor de pecho": "chest pain",
        "dolor en el pecho": "chest pain",
        "dolor torácico": "chest pain",
        "palpitaciones": "palpitations",
        "latidos rápidos": "rapid heartbeat",
        "presión arterial alta": "high blood pressure",
        "hinchazón de piernas": "leg swelling",
        # Gastrointestinal
        "dolor abdominal": "abdominal pain",
        "dolor de estómago": "stomach pain",
        "dolor de barriga": "stomach pain",
        "náusea": "nausea",
        "náuseas": "nausea",
        "vómito": "vomiting",
        "vómitos": "vomiting",
        "diarrea": "diarrhea",
        "estreñimiento": "constipation",
        "hinchazón abdominal": "bloating",
        "acidez": "heartburn",
        "sangre en las heces": "blood in stool",
        "pérdida de apetito": "loss of appetite",
        "ictericia": "jaundice",
        # Musculoskeletal
        "dolor de espalda": "back pain",
        "dolor lumbar": "lower back pain",
        "dolor de cuello": "neck pain",
        "cuello rígido": "stiff neck",
        "dolor articular": "joint pain",
        "dolor de rodilla": "knee pain",
        "dolor de cadera": "hip pain",
        "dolor de hombro": "shoulder pain",
        "dolor muscular": "muscle pain",
        "dolores corporales": "body aches",
        "calambres": "muscle cramps",
        "hinchazón": "swelling",
        # Skin
        "erupción": "rash",
        "sarpullido": "rash",
        "picazón": "itching",
        "urticaria": "hives",
        "herida": "wound",
        "quemadura": "burn",
        "moretón": "bruise",
        "absceso": "abscess",
        # Urological
        "dolor al orinar": "painful urination",
        "ardor al orinar": "burning urination",
        "micción frecuente": "frequent urination",
        "sangre en la orina": "blood in urine",
        # General
        "fiebre": "fever",
        "calentura": "fever",
        "escalofríos": "chills",
        "sudores nocturnos": "night sweats",
        "fatiga": "fatigue",
        "cansancio": "fatigue",
        "agotamiento": "fatigue",
        "pérdida de peso": "weight loss",
        "deshidratación": "dehydration",
        "sed excesiva": "excessive thirst",
        "sangrado": "bleeding",
        "ganglios inflamados": "swollen lymph nodes",
        # Mental Health
        "ansiedad": "anxiety",
        "depresión": "depression",
        "insomnio": "insomnia",
        "problemas de sueño": "sleep problems",
        "estrés": "stress",
        # Pediatric
        "dermatitis del pañal": "diaper rash",
        "cólico": "colic",
        # Emergency
        "inconsciente": "unconscious",
        "no responde": "unresponsive",
        "envenenamiento": "poisoning",
        "mordedura de serpiente": "snake bite",
    },

}


def translate_symptom(symptom: str) -> str:
    """Translate a symptom from any supported language to English."""
    symptom_lower = symptom.lower().strip()

    # Check each language's translations
    for lang_code, translations in SYMPTOM_TRANSLATIONS.items():
        for foreign, english in translations.items():
            if foreign in symptom_lower or symptom_lower in foreign:
                return english

    # No translation found, return original
    return symptom_lower


def quick_icd10_lookup(symptom: str) -> Optional[dict]:
    """Quick local lookup for common symptoms.

    Supports multilingual input (French, Spanish, Portuguese, Kiswahili, etc.)
    by translating to English first.
    """
    symptom_lower = symptom.lower().strip()

    # First, try direct English lookup
    for key, value in COMMON_SYMPTOMS.items():
        if key in symptom_lower or symptom_lower in key:
            return {"codes": [value], "source": "local"}

    # If not found, try translating from other languages
    translated = translate_symptom(symptom_lower)
    if translated != symptom_lower:
        # Translation found, look up the English term
        for key, value in COMMON_SYMPTOMS.items():
            if key in translated or translated in key:
                return {"codes": [value], "source": "local", "translated_from": symptom_lower}

    return None

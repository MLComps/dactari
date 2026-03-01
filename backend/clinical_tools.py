"""Clinical decision support tools using Mistral Small for fast inference."""
import json
import logging
import time
import traceback
from mistralai import Mistral
from config import MISTRAL_API_KEY
from icd10 import check_red_flags, COMMON_SYMPTOMS

# Get logger
logger = logging.getLogger("daktari")

# Initialize Mistral client for clinical tools (uses Small model for speed/cost)
logger.info("Initializing Mistral client for clinical tools...")
client = Mistral(api_key=MISTRAL_API_KEY)
logger.info("✓ Clinical tools Mistral client ready")

# Prompt for differential diagnosis suggestion
DIFFERENTIAL_PROMPT = """You are a clinical decision support system. Given the following symptom profile, suggest 3-5 possible differential diagnoses ranked by likelihood.

For each differential:
1. Name the condition
2. Provide the ICD-10 code
3. Explain which symptoms support this differential
4. Flag if this differential warrants urgent investigation (e.g., imaging, labs)
5. Mark confidence: HIGH / MEDIUM / LOW

IMPORTANT: Flag dangerous differentials even if they're low probability.

For headache with progressive neurological symptoms, ALWAYS consider:
- Space-occupying lesion (requires imaging)
- Raised intracranial pressure
- Temporal arteritis (if age >50)

For chest pain, ALWAYS consider:
- Acute coronary syndrome
- Pulmonary embolism
- Aortic dissection

Return your response as valid JSON with this structure:
{
  "differentials": [
    {
      "rank": 1,
      "condition": "Condition name",
      "icd10_code": "X00.0",
      "confidence": "HIGH|MEDIUM|LOW",
      "supporting_symptoms": ["symptom1", "symptom2"],
      "urgent_workup": true|false,
      "reasoning": "Brief clinical reasoning"
    }
  ],
  "red_flag_conditions": ["List any dangerous conditions to rule out"],
  "recommended_investigations": ["List of suggested tests/imaging"]
}

SYMPTOM PROFILE:
"""

# Prompt for SATS triage assessment
SATS_TRIAGE_PROMPT = """You are a triage nurse using the South African Triage Scale (SATS). Assess the following patient and assign a triage category.

TRIAGE CATEGORIES:
- RED (Emergency): Immediate treatment needed. Life-threatening conditions.
  Examples: Airway compromise, severe respiratory distress, shock, unconsciousness, active seizure

- ORANGE (Very Urgent): Treatment within 10 minutes.
  Examples: Severe pain (8-10), high fever with confusion, significant bleeding, chest pain with cardiac features

- YELLOW (Urgent): Treatment within 60 minutes.
  Examples: Moderate pain (5-7), progressive symptoms, neurological changes without immediate threat

- GREEN (Routine): Treatment within 240 minutes.
  Examples: Minor injuries, chronic stable symptoms, mild illness

CLINICAL RULES:
- Progressive neurological symptoms = at minimum YELLOW, often ORANGE
- Severity 8-10 with neurological signs = ORANGE
- Any airway/breathing/circulation compromise = RED
- Altered consciousness = RED
- Chest pain + shortness of breath = minimum ORANGE
- Fever + neck stiffness = RED (possible meningitis)
- Headache + worst ever + sudden onset = RED (possible SAH)

Return your response as valid JSON:
{
  "color": "red|orange|yellow|green",
  "emoji": "emoji for color",
  "label": "EMERGENCY|VERY URGENT|URGENT|ROUTINE",
  "time_target": "Immediate|Within 10 minutes|Within 60 minutes|Within 240 minutes",
  "reasoning": "Clinical reasoning for this triage level",
  "key_findings": ["Finding 1", "Finding 2"],
  "recommended_actions": ["Action 1", "Action 2", "Action 3"]
}

PATIENT PRESENTATION:
"""

# Prompt for generating clinical recommendations
RECOMMENDATIONS_PROMPT = """Based on the following clinical presentation, generate a focused list of recommended actions for the clinician.

Include:
1. Physical examination components specific to the presentation
2. Basic bedside assessments
3. Laboratory investigations if indicated
4. Imaging if indicated
5. Specialist referral if needed

Format as a checklist. Be specific to the symptoms presented.

Return as JSON:
{
  "immediate_actions": ["Action 1", "Action 2"],
  "physical_exam": ["Exam component 1", "Exam component 2"],
  "investigations": ["Test 1", "Test 2"],
  "referrals": ["Referral if needed"],
  "patient_education": ["Key point for patient"]
}

CLINICAL PRESENTATION:
"""


async def suggest_differentials(
    symptoms: list[str],
    duration: str = None,
    severity: str = None,
    medical_history: str = None,
    age_sex: str = None,
    triggers: str = None
) -> dict:
    """Generate differential diagnoses using Mistral Small.

    This is a CLINICAL DECISION SUPPORT tool - outputs are for clinicians only,
    NOT for patient-facing communication.
    """
    logger.info("🧠 SUGGEST_DIFFERENTIALS called")
    logger.info(f"   Symptoms: {symptoms}")
    logger.info(f"   Duration: {duration}, Severity: {severity}")
    logger.info(f"   Patient: {age_sex}, History: {medical_history}")

    # Build the symptom profile
    profile_parts = [f"Symptoms: {', '.join(symptoms)}"]

    if duration:
        profile_parts.append(f"Duration: {duration}")
    if severity:
        profile_parts.append(f"Severity: {severity}")
    if medical_history:
        profile_parts.append(f"Medical History: {medical_history}")
    if age_sex:
        profile_parts.append(f"Patient: {age_sex}")
    if triggers:
        profile_parts.append(f"Triggers/Exacerbating factors: {triggers}")

    profile = "\n".join(profile_parts)
    logger.debug(f"   Profile:\n{profile}")

    try:
        logger.info("   Calling Mistral Small for differentials...")
        start_time = time.time()
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {"role": "user", "content": DIFFERENTIAL_PROMPT + profile}
            ],
            response_format={"type": "json_object"}
        )
        elapsed = time.time() - start_time
        logger.info(f"   ✅ Mistral Small responded in {elapsed:.2f}s")

        result = json.loads(response.choices[0].message.content)
        result["source"] = "Daktari Clinical Decision Support (AI-assisted)"
        result["disclaimer"] = "AI-generated suggestions require clinical validation"

        # Log the differentials found
        if result.get("differentials"):
            logger.info(f"   📋 Found {len(result['differentials'])} differentials:")
            for d in result["differentials"][:3]:
                logger.info(f"      - {d.get('condition', 'N/A')} ({d.get('confidence', 'N/A')})")

        return result

    except Exception as e:
        logger.error(f"   ❌ SUGGEST_DIFFERENTIALS failed: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "error": str(e),
            "differentials": [],
            "source": "Error in differential generation"
        }


async def assess_urgency(
    symptoms: list[str],
    severity_score: int,
    duration: str = None,
    vital_signs: str = None,
    red_flags_detected: list[str] = None
) -> dict:
    """Assess clinical urgency using South African Triage Scale (SATS).

    Uses LLM-based clinical reasoning, with keyword-based red flag detection as backup.
    """
    logger.info("🚨 ASSESS_URGENCY called (SATS)")
    logger.info(f"   Symptoms: {symptoms}")
    logger.info(f"   Severity Score: {severity_score}/10")
    logger.info(f"   Duration: {duration}")

    # First, run keyword-based red flag check as safety net
    keyword_flags = check_red_flags(symptoms)
    if keyword_flags.get("red_flags"):
        logger.warning(f"   ⚠️ Keyword red flags detected: {keyword_flags['red_flags']}")
    if keyword_flags.get("is_emergency"):
        logger.warning(f"   🔴 KEYWORD EMERGENCY FLAG SET")

    # Build presentation for LLM
    presentation_parts = [
        f"Symptoms: {', '.join(symptoms)}",
        f"Severity score: {severity_score}/10"
    ]

    if duration:
        presentation_parts.append(f"Duration: {duration}")
    if vital_signs:
        presentation_parts.append(f"Vital signs: {vital_signs}")
    if red_flags_detected:
        presentation_parts.append(f"Pre-identified red flags: {', '.join(red_flags_detected)}")
    if keyword_flags.get("red_flags"):
        presentation_parts.append(f"Keyword-detected concerns: {', '.join(keyword_flags['red_flags'])}")

    presentation = "\n".join(presentation_parts)
    logger.debug(f"   Presentation:\n{presentation}")

    try:
        logger.info("   Calling Mistral Small for SATS assessment...")
        start_time = time.time()
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {"role": "user", "content": SATS_TRIAGE_PROMPT + presentation}
            ],
            response_format={"type": "json_object"}
        )
        elapsed = time.time() - start_time
        logger.info(f"   ✅ Mistral Small responded in {elapsed:.2f}s")

        llm_result = json.loads(response.choices[0].message.content)
        logger.info(f"   🏥 LLM Triage: {llm_result.get('color', 'N/A').upper()} - {llm_result.get('label', 'N/A')}")

        # Safety net: If keyword matcher found emergency but LLM didn't, escalate
        if keyword_flags.get("is_emergency") and llm_result.get("color") not in ["red", "orange"]:
            logger.warning(f"   ⬆️ ESCALATING from {llm_result.get('color')} to ORANGE (keyword safety)")
            llm_result["color"] = "orange"
            llm_result["emoji"] = "🟠"
            llm_result["label"] = "VERY URGENT"
            llm_result["time_target"] = "Within 10 minutes"
            llm_result["reasoning"] += f" [ESCALATED: Keyword safety check detected: {', '.join(keyword_flags['red_flags'])}]"
            llm_result["escalated_by_safety_check"] = True

        llm_result["source"] = "South African Triage Scale (SATS) - AI-assisted"
        llm_result["keyword_backup_flags"] = keyword_flags.get("red_flags", [])

        logger.info(f"   ✅ Final Triage: {llm_result.get('emoji', '')} {llm_result.get('color', '').upper()}")
        return llm_result

    except Exception as e:
        logger.error(f"   ❌ ASSESS_URGENCY failed: {str(e)}")
        logger.error(traceback.format_exc())
        # Fallback to keyword-based assessment
        fallback_color = "red" if keyword_flags.get("is_emergency") else "green"
        logger.warning(f"   ⚠️ Using keyword fallback: {fallback_color.upper()}")
        return {
            "color": fallback_color,
            "emoji": "🔴" if fallback_color == "red" else "🟢",
            "label": "EMERGENCY" if fallback_color == "red" else "ROUTINE",
            "time_target": "Immediate" if fallback_color == "red" else "Within 240 minutes",
            "reasoning": f"Fallback assessment due to error. Keyword flags: {keyword_flags.get('red_flags', [])}",
            "error": str(e),
            "source": "Keyword-based fallback"
        }


async def generate_recommendations(
    symptoms: list[str],
    chief_complaint: str,
    severity: str = None,
    triage_color: str = None
) -> dict:
    """Generate clinical recommendations checklist."""

    presentation = f"""
Chief Complaint: {chief_complaint}
Symptoms: {', '.join(symptoms)}
Severity: {severity or 'Not specified'}
Triage Level: {triage_color or 'Not assessed'}
"""

    try:
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {"role": "user", "content": RECOMMENDATIONS_PROMPT + presentation}
            ],
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as e:
        # Provide generic recommendations on error
        return {
            "immediate_actions": ["Complete vital signs assessment"],
            "physical_exam": ["General examination", "System-specific examination based on chief complaint"],
            "investigations": ["Consider basic labs based on clinical presentation"],
            "referrals": ["Specialist referral if indicated"],
            "error": str(e)
        }


def build_symptom_timeline(symptoms_with_timing: list[dict]) -> dict:
    """Build a simple text-based symptom timeline.

    Args:
        symptoms_with_timing: List of {"symptom": str, "day": int, "severity": int}

    Returns:
        Timeline data structure for rendering
    """
    if not symptoms_with_timing:
        return {"timeline": [], "text_representation": "No timeline data available"}

    # Sort by day
    sorted_symptoms = sorted(symptoms_with_timing, key=lambda x: x.get("day", 0))

    # Group by day
    days = {}
    for s in sorted_symptoms:
        day = s.get("day", 0)
        if day not in days:
            days[day] = []
        days[day].append(s.get("symptom", "Unknown"))

    # Build timeline
    timeline = []
    for day in sorted(days.keys()):
        timeline.append({
            "day": day,
            "label": f"Day {day}" if day > 0 else "Day 1",
            "symptoms": days[day]
        })

    # Text representation
    lines = []
    for entry in timeline:
        symptoms_str = ", ".join(entry["symptoms"])
        lines.append(f"{entry['label']}: {symptoms_str}")

    return {
        "timeline": timeline,
        "text_representation": "\n".join(lines),
        "total_days": max(days.keys()) if days else 0
    }


# ============================================================
# IMAGE ANALYSIS (Pixtral)
# ============================================================

IMAGE_ANALYSIS_PROMPT = """You are a medical triage assistant analyzing an image for clinical assessment purposes.

IMPORTANT DISCLAIMERS:
- This is NOT a diagnosis - only observations for triage
- Always recommend professional medical evaluation
- Note any limitations in image quality

Analyze this image and provide:

1. **Visual Observations**: Describe what you see objectively
   - Location, size, shape, color
   - Pattern (localized, diffuse, clustered)
   - Any notable characteristics

2. **Clinical Descriptors**: Use appropriate medical terminology
   - For skin: erythema, papule, vesicle, pustule, macule, plaque, etc.
   - For wounds: laceration, abrasion, contusion, etc.
   - For swelling: edema, inflammation, etc.

3. **Relevant Considerations**: What conditions might present this way?
   - List 2-3 possibilities (NOT diagnoses)
   - Note any concerning features that warrant urgent evaluation

4. **Triage Implications**: Does this visual finding affect urgency?
   - Signs of infection (spreading redness, pus, streaking)
   - Signs of severe reaction (extensive involvement, systemic appearance)
   - Signs requiring immediate care

5. **Image Quality Note**: Comment on any limitations

Return your response as JSON:
{{
  "observations": "Objective description of what is visible",
  "clinical_descriptors": ["descriptor1", "descriptor2"],
  "possible_conditions": [
    {{"condition": "Condition name", "icd10_hint": "Code", "likelihood": "HIGH/MEDIUM/LOW"}}
  ],
  "concerning_features": ["feature1", "feature2"],
  "urgency_impact": "none|increases|significantly_increases",
  "recommended_action": "What should happen next",
  "image_quality": "good|adequate|poor",
  "limitations": "Any limitations in assessment"
}}

Body area being examined: {body_area}
Condition type reported: {condition_type}
Patient-reported context: {context}
"""


async def analyze_medical_image(
    image_base64: str,
    body_area: str = "unspecified",
    condition_type: str = "other",
    context: str = "No additional context provided"
) -> dict:
    """Analyze a medical image using Pixtral for visual assessment.

    Args:
        image_base64: Base64-encoded image data
        body_area: Which body part (e.g., 'arm', 'face', 'throat')
        condition_type: Type of condition (skin, eye, wound, etc.)
        context: Patient-reported symptoms or context

    Returns:
        dict with visual observations and clinical considerations
    """
    logger.info("🖼️ ANALYZE_MEDICAL_IMAGE called")
    logger.info(f"   Body area: {body_area}")
    logger.info(f"   Condition type: {condition_type}")
    logger.info(f"   Image size: {len(image_base64)} chars (base64)")

    # Prepare the prompt with context
    prompt = IMAGE_ANALYSIS_PROMPT.format(
        body_area=body_area,
        condition_type=condition_type,
        context=context
    )

    try:
        logger.info("   Calling Pixtral Large for image analysis...")
        start_time = time.time()

        # Determine image type from base64 header or default to jpeg
        if image_base64.startswith("/9j/"):
            mime_type = "image/jpeg"
            logger.info("   Detected JPEG image")
        elif image_base64.startswith("iVBOR"):
            mime_type = "image/png"
            logger.info("   Detected PNG image")
        elif image_base64.startswith("R0lGOD"):
            mime_type = "image/gif"
            logger.info("   Detected GIF image")
        else:
            mime_type = "image/jpeg"  # Default
            logger.info(f"   Unknown format, defaulting to JPEG. First chars: {image_base64[:20]}")

        logger.info(f"   Building Pixtral request with {len(image_base64)} chars of base64 data")
        logger.info(f"   MIME type: {mime_type}")

        response = client.chat.complete(
            model="pixtral-large-latest",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )

        elapsed = time.time() - start_time
        logger.info(f"   ✅ Pixtral responded in {elapsed:.2f}s")

        result = json.loads(response.choices[0].message.content)
        result["source"] = "Pixtral Large - Visual Analysis"
        result["analyzed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        result["body_area"] = body_area
        result["condition_type"] = condition_type

        logger.info(f"   📋 Observations: {result.get('observations', 'N/A')[:100]}...")
        logger.info(f"   ⚠️ Urgency impact: {result.get('urgency_impact', 'none')}")

        return result

    except Exception as e:
        error_msg = str(e)
        logger.error(f"   ❌ Image analysis failed: {error_msg}")
        logger.error(traceback.format_exc())

        # Check for common error types
        if "401" in error_msg or "unauthorized" in error_msg.lower():
            user_error = "API authentication failed. Please check your Mistral API key."
        elif "404" in error_msg or "not found" in error_msg.lower():
            user_error = "Pixtral model not found. The model may not be available for your API tier."
        elif "429" in error_msg or "rate limit" in error_msg.lower():
            user_error = "Rate limit exceeded. Please wait a moment and try again."
        elif "image" in error_msg.lower() and ("size" in error_msg.lower() or "large" in error_msg.lower()):
            user_error = "Image too large. Please try a smaller or compressed image."
        elif "format" in error_msg.lower() or "invalid" in error_msg.lower():
            user_error = "Invalid image format. Please try a different image."
        else:
            user_error = f"Image analysis unavailable: {error_msg[:100]}"

        return {
            "error": error_msg,
            "observations": user_error,
            "clinical_descriptors": [],
            "possible_conditions": [],
            "concerning_features": [],
            "urgency_impact": "none",
            "recommended_action": "Continue with verbal assessment - describe what you see",
            "image_quality": "unknown",
            "limitations": user_error,
            "source": "Error fallback"
        }

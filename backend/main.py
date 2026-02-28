"""Daktari - Medical Intake Assistant Backend."""
from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from mistralai import Mistral
import httpx
import json
import io
import base64
import asyncio
import logging
import traceback
import time
from typing import Optional, AsyncGenerator
from datetime import datetime

from config import MISTRAL_API_KEY, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID
from icd10 import lookup_icd10, check_red_flags
from handoff import generate_handoff_pdf
from clinical_tools import suggest_differentials, assess_urgency, generate_recommendations, build_symptom_timeline

# ============================================
# LOGGING CONFIGURATION
# ============================================

# Create custom formatter with colors
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'

    def format(self, record):
        # Add color based on level
        color = self.COLORS.get(record.levelname, self.RESET)

        # Format timestamp
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]

        # Create the log message
        level_name = f"{color}{self.BOLD}[{record.levelname:^8}]{self.RESET}"
        message = f"{timestamp} {level_name} {record.getMessage()}"

        # Add exception info if present
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"

        return message

# Configure root logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("daktari")
logger.setLevel(logging.DEBUG)

# Remove default handlers and add our custom one
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(ColoredFormatter())
logger.addHandler(console_handler)

# Also set uvicorn loggers to use our format
logging.getLogger("uvicorn").handlers = []
logging.getLogger("uvicorn.access").handlers = []

logger.info("=" * 60)
logger.info("🏥 DAKTARI MEDICAL ASSISTANT - BACKEND STARTING")
logger.info("=" * 60)

app = FastAPI(title="Daktari API", version="1.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Mistral client
logger.info("Initializing Mistral client...")
client = Mistral(api_key=MISTRAL_API_KEY)
logger.info(f"✓ Mistral client initialized (API key: {MISTRAL_API_KEY[:8]}...)")
logger.info(f"✓ ElevenLabs configured: {'Yes' if ELEVENLABS_API_KEY and ELEVENLABS_API_KEY != 'your-elevenlabs-api-key-here' else 'No'}")

# System prompt for medical triage
TRIAGE_SYSTEM_PROMPT = """You are Daktari, a warm and professional medical intake assistant for community health workers.

LANGUAGE: Respond in English. Be warm, patient, and reassuring.

## INTAKE PROTOCOL (follow this order):

### Phase 1: Symptom Collection
1. Greet warmly, ask chief complaint: "Hello! I'm Daktari. What brings you in today?"
2. Ask onset/duration: "When did this start? Has it been getting better or worse?"
3. Ask severity: "On a scale of 1-10, how severe is it right now?"
4. Ask about triggers: "Does anything make it better or worse?"
5. Ask 2-3 associated symptoms relevant to the chief complaint
6. Ask medical history: chronic conditions, current medications, allergies

### Phase 2: Clinical Assessment (AUTOMATIC - do this after collecting symptoms)
7. Call `assess_urgency` tool with all symptoms and severity score - this uses the South African Triage Scale
8. Call `lookup_icd10` for each significant symptom to get medical codes
9. Call `suggest_differentials` tool with the complete symptom profile - this generates differential diagnoses for the clinician

### Phase 3: Handoff Generation
10. Call `generate_handoff` with ALL data including:
    - urgency assessment results
    - differential diagnoses
    - ICD-10 codes
    - symptoms with timeline
    - recommended clinical actions

## PATIENT COMMUNICATION:
- When presenting results to the patient, use SIMPLE, REASSURING language
- Tell them their triage level and what it means for next steps
- DO NOT share differential diagnoses with the patient - those are for clinician handoff only
- Example: "Based on your symptoms, I recommend you see a clinician within the next hour. I've prepared a detailed note for them."

## TRIAGE COMMUNICATION:
- 🔴 RED: "This needs immediate attention. Please go to the emergency department right away."
- 🟠 ORANGE: "This is quite urgent. Please see a clinician within 10 minutes."
- 🟡 YELLOW: "This should be seen soon. Please see a clinician within the next hour."
- 🟢 GREEN: "This can be seen during normal clinic hours."

## WHEN CITING MEDICAL DATA:
- Include ICD-10 codes: "headache (ICD-10: R51)"
- Mention data source when relevant

## RULES:
- NEVER diagnose - only document and triage
- NEVER prescribe medications
- Be warm and professional
- Ask one question at a time
- Always complete the full assessment before generating handoff
- Include disclaimer: "AI-assisted triage — clinical judgment required"
"""

# Tool definitions for Mistral function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_icd10",
            "description": "Look up ICD-10 code for a symptom or condition",
            "parameters": {
                "type": "object",
                "properties": {
                    "symptom": {"type": "string", "description": "Symptom in English"},
                },
                "required": ["symptom"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_red_flags",
            "description": "Quick keyword-based check for emergency symptoms (backup safety net)",
            "parameters": {
                "type": "object",
                "properties": {
                    "symptoms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of reported symptoms in English"
                    }
                },
                "required": ["symptoms"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "assess_urgency",
            "description": "Assess clinical urgency using South African Triage Scale (SATS). Returns triage color, time-to-treatment target, and reasoning. Call this AFTER collecting all symptoms.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symptoms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of all reported symptoms"
                    },
                    "severity_score": {
                        "type": "integer",
                        "description": "Pain/severity score from 1-10"
                    },
                    "duration": {"type": "string", "description": "How long symptoms have been present"},
                    "vital_signs": {"type": "string", "description": "Vital signs if available"},
                    "red_flags_detected": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Any red flags already identified"
                    }
                },
                "required": ["symptoms", "severity_score"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_differentials",
            "description": "After symptom intake is complete, suggest possible differential diagnoses for the CLINICIAN to consider. This is clinical decision support, NOT a patient-facing diagnosis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symptoms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of all reported symptoms in English"
                    },
                    "duration": {"type": "string"},
                    "severity": {"type": "string"},
                    "medical_history": {"type": "string"},
                    "age_sex": {"type": "string", "description": "Patient age and sex if known"},
                    "triggers": {"type": "string", "description": "What makes symptoms worse"}
                },
                "required": ["symptoms"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_handoff",
            "description": "Generate structured clinical handoff note with SBAR format. Call when intake AND assessments are complete.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chief_complaint": {"type": "string"},
                    "symptoms": {"type": "array", "items": {"type": "string"}},
                    "duration": {"type": "string"},
                    "severity": {"type": "string"},
                    "triggers": {"type": "string", "description": "What makes symptoms worse"},
                    "red_flags": {"type": "array", "items": {"type": "string"}},
                    "medical_history": {"type": "string"},
                    "patient_language": {"type": "string"},
                    "urgency_assessment": {
                        "type": "object",
                        "description": "Results from assess_urgency tool",
                        "properties": {
                            "color": {"type": "string"},
                            "label": {"type": "string"},
                            "time_target": {"type": "string"},
                            "reasoning": {"type": "string"}
                        }
                    },
                    "differentials": {
                        "type": "array",
                        "description": "Results from suggest_differentials tool",
                        "items": {
                            "type": "object",
                            "properties": {
                                "condition": {"type": "string"},
                                "icd10_code": {"type": "string"},
                                "confidence": {"type": "string"}
                            }
                        }
                    },
                    "recommended_actions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Checklist of recommended clinical actions"
                    },
                    "symptom_timeline": {
                        "type": "string",
                        "description": "Text description of symptom progression"
                    }
                },
                "required": ["chief_complaint", "symptoms"]
            }
        }
    }
]


class ChatRequest(BaseModel):
    messages: list[dict]


class ChatResponse(BaseModel):
    response: str
    tool_calls: Optional[list] = None
    handoff_ready: bool = False
    handoff_data: Optional[dict] = None


class HandoffRequest(BaseModel):
    chief_complaint: str
    symptoms: list[str]
    duration: Optional[str] = None
    severity: Optional[str] = None
    triggers: Optional[str] = None
    red_flags: Optional[list[str]] = None
    medical_history: Optional[str] = None
    patient_language: Optional[str] = None
    patient: Optional[dict] = None
    urgency: str = "routine"
    urgency_assessment: Optional[dict] = None
    differentials: Optional[list[dict]] = None
    recommended_actions: Optional[list[str]] = None
    symptom_timeline: Optional[str] = None
    icd_codes: Optional[list[str]] = None


class TTSRequest(BaseModel):
    text: str
    language: str = "en"


@app.get("/")
async def root():
    return {"message": "Daktari API is running", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


async def execute_tool_call(tool_name: str, arguments: dict) -> dict:
    """Execute a tool call and return the result."""
    start_time = time.time()
    logger.info(f"🔧 TOOL CALL: {tool_name}")
    logger.debug(f"   Arguments: {json.dumps(arguments, indent=2)[:500]}")

    try:
        if tool_name == "lookup_icd10":
            result = await lookup_icd10(arguments["symptom"])
        elif tool_name == "check_red_flags":
            result = check_red_flags(arguments["symptoms"])
        elif tool_name == "assess_urgency":
            logger.info(f"   📊 Assessing urgency for {len(arguments.get('symptoms', []))} symptoms")
            logger.info(f"   📊 Severity score: {arguments.get('severity_score', 'N/A')}")
            result = await assess_urgency(
                symptoms=arguments["symptoms"],
                severity_score=arguments.get("severity_score", 5),
                duration=arguments.get("duration"),
                vital_signs=arguments.get("vital_signs"),
                red_flags_detected=arguments.get("red_flags_detected")
            )
            logger.info(f"   🚨 TRIAGE RESULT: {result.get('color', 'unknown').upper()} - {result.get('label', 'N/A')}")
        elif tool_name == "suggest_differentials":
            logger.info(f"   🧠 Generating differentials for: {', '.join(arguments.get('symptoms', []))[:100]}")
            result = await suggest_differentials(
                symptoms=arguments["symptoms"],
                duration=arguments.get("duration"),
                severity=arguments.get("severity"),
                medical_history=arguments.get("medical_history"),
                age_sex=arguments.get("age_sex"),
                triggers=arguments.get("triggers")
            )
            if result.get("differentials"):
                logger.info(f"   🧠 Top differential: {result['differentials'][0].get('condition', 'N/A')}")
        elif tool_name == "generate_handoff":
            logger.info(f"   📋 Generating handoff document")
            result = {"status": "handoff_ready", "data": arguments}
        else:
            logger.warning(f"   ⚠️ Unknown tool: {tool_name}")
            result = {"error": f"Unknown tool: {tool_name}"}

        elapsed = time.time() - start_time
        logger.info(f"   ✅ {tool_name} completed in {elapsed:.2f}s")
        return result

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"   ❌ {tool_name} FAILED after {elapsed:.2f}s: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e), "tool": tool_name}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint - handles conversation with Mistral."""
    logger.info("=" * 50)
    logger.info("📨 POST /chat - New chat request")
    logger.info(f"   Messages in conversation: {len(request.messages)}")
    if request.messages:
        last_msg = request.messages[-1]
        logger.info(f"   Last message ({last_msg.get('role', 'unknown')}): {last_msg.get('content', '')[:100]}...")

    try:
        messages = [{"role": "system", "content": TRIAGE_SYSTEM_PROMPT}] + request.messages

        logger.info("   🤖 Calling Mistral Large...")
        start_time = time.time()
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"
        )
        elapsed = time.time() - start_time
        logger.info(f"   ✅ Mistral responded in {elapsed:.2f}s")

        assistant_message = response.choices[0].message
        logger.debug(f"   Response preview: {(assistant_message.content or '')[:150]}...")

        # Check if there are tool calls
        if assistant_message.tool_calls:
            logger.info(f"   🔧 {len(assistant_message.tool_calls)} tool call(s) requested")
            tool_results = []
            handoff_data = None

            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                result = await execute_tool_call(tool_name, arguments)

                if tool_name == "generate_handoff":
                    handoff_data = result.get("data")

                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "result": result
                })

            # If handoff was generated, return it
            if handoff_data:
                return ChatResponse(
                    response=assistant_message.content or "Intake complete. Generating handoff note...",
                    tool_calls=tool_results,
                    handoff_ready=True,
                    handoff_data=handoff_data
                )

            # Otherwise, continue conversation with tool results
            messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })

            for result in tool_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": result["tool_call_id"],
                    "content": json.dumps(result["result"])
                })

            # Get follow-up response
            follow_up = client.chat.complete(
                model="mistral-large-latest",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto"
            )

            return ChatResponse(
                response=follow_up.choices[0].message.content,
                tool_calls=tool_results
            )

        return ChatResponse(response=assistant_message.content)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice")
async def voice_to_text(audio: UploadFile = File(...)):
    """Convert voice to text using ElevenLabs Speech-to-Text API."""
    try:
        audio_content = await audio.read()

        async with httpx.AsyncClient() as http_client:
            # ElevenLabs Speech-to-Text endpoint
            response = await http_client.post(
                "https://api.elevenlabs.io/v1/speech-to-text",
                headers={
                    "xi-api-key": ELEVENLABS_API_KEY,
                },
                files={
                    "file": ("audio.webm", audio_content, audio.content_type or "audio/webm"),
                },
                data={
                    "model_id": "scribe_v1",  # ElevenLabs Scribe model
                },
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                return {"text": data.get("text", ""), "language": data.get("language_code", "auto")}
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Transcription failed: {response.text}"
                )

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Transcription timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice transcription failed: {str(e)}")


@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    """Convert text to speech using ElevenLabs."""
    # Check if API key is configured
    if not ELEVENLABS_API_KEY or ELEVENLABS_API_KEY == "your-elevenlabs-api-key-here":
        raise HTTPException(status_code=503, detail="TTS not configured - ElevenLabs API key missing")

    try:
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
                headers={
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "text": request.text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    }
                }
            )

            if response.status_code != 200:
                error_detail = response.text[:200] if response.text else "Unknown error"
                print(f"TTS Error: {response.status_code} - {error_detail}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"TTS failed: {error_detail}"
                )

            return StreamingResponse(
                io.BytesIO(response.content),
                media_type="audio/mpeg"
            )

    except httpx.RequestError as e:
        print(f"TTS Request Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TTS request failed: {str(e)}")
    except Exception as e:
        print(f"TTS Unexpected Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")


@app.post("/handoff")
async def create_handoff(request: HandoffRequest):
    """Generate PDF handoff note."""
    logger.info("=" * 50)
    logger.info("📄 POST /handoff - Generating PDF")
    try:
        data = request.model_dump()
        logger.info(f"   Chief complaint: {data.get('chief_complaint', 'N/A')}")
        logger.info(f"   Symptoms: {data.get('symptoms', [])}")
        logger.info(f"   Urgency: {data.get('urgency_assessment', {}).get('color', 'N/A')}")
        logger.info(f"   Differentials: {len(data.get('differentials', []))} items")
        logger.info(f"   Patient: {data.get('patient', {}).get('name', 'N/A')}")

        # Look up ICD codes for symptoms if not provided
        if not data.get("icd_codes"):
            logger.info("   🔍 Looking up ICD-10 codes...")
            icd_codes = []
            for symptom in data["symptoms"][:3]:  # Limit to 3 lookups
                result = await lookup_icd10(symptom)
                if result.get("codes"):
                    icd_codes.append(result["codes"][0]["code"])
            data["icd_codes"] = icd_codes if icd_codes else ["Pending"]
            logger.info(f"   ✅ ICD codes: {data['icd_codes']}")

        logger.info("   📋 Generating PDF...")
        filename = generate_handoff_pdf(data)
        logger.info(f"   ✅ PDF generated: {filename}")

        return FileResponse(
            filename,
            media_type="application/pdf",
            filename=filename
        )

    except Exception as e:
        logger.error(f"   ❌ Handoff generation failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# ============== REAL-TIME STREAMING ENDPOINTS ==============

class StreamingChatRequest(BaseModel):
    messages: list[dict]
    voice_response: bool = False  # If true, also stream TTS


@app.post("/chat/stream")
async def chat_stream(request: StreamingChatRequest):
    """Streaming chat endpoint - returns Server-Sent Events with tool support."""
    logger.info("=" * 50)
    logger.info("📨 POST /chat/stream - Streaming chat request")
    logger.info(f"   Messages: {len(request.messages)}")

    async def generate() -> AsyncGenerator[str, None]:
        try:
            messages = [{"role": "system", "content": TRIAGE_SYSTEM_PROMPT}] + request.messages

            # First, get response with tool support (non-streaming for tool handling)
            logger.info("   🤖 Calling Mistral Large with tools...")
            start_time = time.time()

            response = client.chat.complete(
                model="mistral-large-latest",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto"
            )

            elapsed = time.time() - start_time
            logger.info(f"   ✅ Mistral responded in {elapsed:.2f}s")

            assistant_message = response.choices[0].message
            full_response = assistant_message.content or ""

            # Handle tool calls if present
            if assistant_message.tool_calls:
                logger.info(f"   🔧 {len(assistant_message.tool_calls)} tool call(s) detected")

                # Send initial response if any
                if full_response:
                    for i in range(0, len(full_response), 20):
                        chunk = full_response[i:i + 20]
                        yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
                        await asyncio.sleep(0.02)

                tool_results = []
                handoff_data = None
                triage_data = None
                differentials_data = None
                icd10_codes = []
                tool_arguments = {}  # Store arguments from tool calls

                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    logger.info(f"   🔧 Executing: {tool_name}")

                    # Notify frontend about tool execution
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool_name})}\n\n"

                    try:
                        arguments = json.loads(tool_call.function.arguments)
                        tool_arguments[tool_name] = arguments  # Store for later use
                        result = await execute_tool_call(tool_name, arguments)
                        logger.info(f"   ✅ {tool_name} completed")

                        # Send tool result to frontend
                        yield f"data: {json.dumps({'type': 'tool_result', 'tool': tool_name, 'result': result})}\n\n"

                        if tool_name == "generate_handoff":
                            handoff_data = result.get("data")

                        if tool_name == "assess_urgency" and "error" not in result:
                            triage_data = result
                            yield f"data: {json.dumps({'type': 'triage', 'data': result})}\n\n"

                        if tool_name == "suggest_differentials" and "error" not in result:
                            differentials_data = result.get("differentials", [])

                        if tool_name == "lookup_icd10" and "error" not in result:
                            if result.get("icd10_code"):
                                icd10_codes.append({
                                    "symptom": arguments.get("symptom"),
                                    "code": result.get("icd10_code"),
                                    "description": result.get("description")
                                })

                    except Exception as tool_error:
                        logger.error(f"   ❌ {tool_name} failed: {str(tool_error)}")
                        result = {"error": str(tool_error)}
                        yield f"data: {json.dumps({'type': 'tool_error', 'tool': tool_name, 'error': str(tool_error)})}\n\n"

                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "result": result
                    })

                # Build messages with tool results for follow-up
                messages.append({
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in assistant_message.tool_calls
                    ]
                })

                for result in tool_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": result["tool_call_id"],
                        "content": json.dumps(result["result"])
                    })

                # Get follow-up response after tool execution
                logger.info("   🤖 Getting follow-up response...")
                follow_up_start = time.time()
                follow_up = client.chat.complete(
                    model="mistral-large-latest",
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto"
                )
                follow_up_elapsed = time.time() - follow_up_start
                full_response = follow_up.choices[0].message.content or ""
                logger.info(f"   ✅ Follow-up: {len(full_response)} chars in {follow_up_elapsed:.2f}s")

                # Auto-construct handoff data if we have triage results (even if generate_handoff wasn't called)
                if not handoff_data and triage_data:
                    logger.info("   📋 Auto-constructing handoff data from tool results")
                    # Extract symptoms from tool arguments
                    symptoms = []
                    if "assess_urgency" in tool_arguments:
                        symptoms = tool_arguments["assess_urgency"].get("symptoms", [])
                    elif "suggest_differentials" in tool_arguments:
                        symptoms = tool_arguments["suggest_differentials"].get("symptoms", [])

                    handoff_data = {
                        "chief_complaint": ", ".join(symptoms[:3]) if symptoms else "Symptoms assessed",
                        "symptoms": symptoms,
                        "urgency_assessment": triage_data,
                        "differentials": differentials_data or [],
                        "icd10_codes": icd10_codes,
                        "recommended_actions": triage_data.get("recommended_actions", []),
                        "auto_generated": True
                    }

                # Send handoff data if available
                if handoff_data:
                    logger.info(f"   📋 Sending handoff data (differentials: {len(handoff_data.get('differentials', []))})")
                    yield f"data: {json.dumps({'type': 'handoff', 'data': handoff_data})}\n\n"

            # Stream the final response
            logger.info(f"   📤 Streaming response ({len(full_response)} chars)")
            for i in range(0, len(full_response), 20):
                chunk = full_response[i:i + 20]
                yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
                await asyncio.sleep(0.02)

            # Signal completion
            yield f"data: {json.dumps({'type': 'done', 'full_response': full_response})}\n\n"
            logger.info("   ✅ Stream complete")

        except Exception as e:
            logger.error(f"   ❌ Stream error: {str(e)}")
            logger.error(traceback.format_exc())
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.websocket("/ws/voice")
async def websocket_voice(websocket: WebSocket):
    """WebSocket endpoint for real-time voice transcription and response."""
    ws_id = id(websocket)
    logger.info("=" * 50)
    logger.info(f"🔌 WEBSOCKET CONNECTED (ID: {ws_id})")

    await websocket.accept()
    logger.info(f"   ✅ Connection accepted")

    audio_buffer = bytearray()
    conversation_messages = []
    chunk_count = 0

    try:
        while True:
            message = await websocket.receive()

            # Handle binary audio data - just collect, transcribe at the end
            if "bytes" in message:
                chunk_count += 1
                audio_buffer.extend(message["bytes"])
                if chunk_count % 10 == 0:  # Log every 10 chunks
                    logger.debug(f"   🎤 Received {chunk_count} audio chunks ({len(audio_buffer)} bytes total)")

            # Handle JSON messages
            elif "text" in message:
                try:
                    data = json.loads(message["text"])
                    logger.debug(f"   📩 Received JSON message: {data.get('type', 'unknown')}")

                    if data.get("type") == "stop":
                        logger.info(f"   🛑 STOP received - Processing {len(audio_buffer)} bytes of audio")
                        logger.info(f"   📊 Total chunks received: {chunk_count}")

                        # Final transcription
                        if audio_buffer:
                            logger.info("   🎙 Sending audio to ElevenLabs Scribe...")
                            transcription_start = time.time()

                            async with httpx.AsyncClient() as http_client:
                                response = await http_client.post(
                                    "https://api.elevenlabs.io/v1/speech-to-text",
                                    headers={"xi-api-key": ELEVENLABS_API_KEY},
                                    files={"file": ("audio.webm", bytes(audio_buffer), "audio/webm")},
                                    data={"model_id": "scribe_v1"},
                                    timeout=30.0
                                )

                                transcription_elapsed = time.time() - transcription_start
                                logger.info(f"   📝 ElevenLabs response: {response.status_code} in {transcription_elapsed:.2f}s")

                                if response.status_code == 200:
                                    transcription = response.json().get("text", "")
                                    logger.info(f"   ✅ TRANSCRIPTION: \"{transcription[:100]}...\"")

                                    # Send final transcription to frontend
                                    await websocket.send_json({
                                        "type": "transcription",
                                        "text": transcription
                                    })
                                    logger.debug("   📤 Sent transcription to frontend")

                                    # Add to conversation and get AI response
                                    conversation_messages.append({
                                        "role": "user",
                                        "content": transcription
                                    })

                                    # Get AI response with tool support
                                    messages = [{"role": "system", "content": TRIAGE_SYSTEM_PROMPT}] + conversation_messages

                                    logger.info("   🤖 Calling Mistral Large for response...")
                                    mistral_start = time.time()

                                    # Use SDK with tools for proper tool handling
                                    response = client.chat.complete(
                                        model="mistral-large-latest",
                                        messages=messages,
                                        tools=TOOLS,
                                        tool_choice="auto"
                                    )

                                    mistral_elapsed = time.time() - mistral_start
                                    logger.info(f"   ✅ Mistral responded in {mistral_elapsed:.2f}s")

                                    assistant_message = response.choices[0].message
                                    full_response = assistant_message.content or ""
                                    logger.debug(f"   Response preview: {full_response[:150]}...")

                                    # Handle tool calls if present
                                    if assistant_message.tool_calls:
                                        logger.info(f"   🔧 {len(assistant_message.tool_calls)} TOOL CALLS requested:")
                                        for tc in assistant_message.tool_calls:
                                            logger.info(f"      - {tc.function.name}")

                                        try:
                                            tool_results = []
                                            handoff_data = None
                                            triage_data = None
                                            differentials_data = None
                                            tool_arguments = {}

                                            for tool_call in assistant_message.tool_calls:
                                                tool_name = tool_call.function.name
                                                logger.info(f"   🔧 Executing: {tool_name}")
                                                try:
                                                    arguments = json.loads(tool_call.function.arguments)
                                                    tool_arguments[tool_name] = arguments
                                                    result = await execute_tool_call(tool_name, arguments)
                                                    logger.info(f"   ✅ {tool_name} completed")
                                                except Exception as tool_error:
                                                    logger.error(f"   ❌ {tool_name} FAILED: {str(tool_error)}")
                                                    logger.error(traceback.format_exc())
                                                    result = {"error": str(tool_error), "tool": tool_name}

                                                if tool_name == "generate_handoff":
                                                    handoff_data = result.get("data")

                                                # Send triage data immediately when assess_urgency is called
                                                if tool_name == "assess_urgency" and "error" not in result:
                                                    triage_data = result
                                                    await websocket.send_json({
                                                        "type": "triage",
                                                        "data": result
                                                    })

                                                if tool_name == "suggest_differentials" and "error" not in result:
                                                    differentials_data = result.get("differentials", [])

                                                tool_results.append({
                                                    "tool_call_id": tool_call.id,
                                                    "name": tool_name,
                                                    "result": result
                                                })

                                            # Add tool messages to conversation
                                            logger.debug("   Adding tool results to conversation context")
                                            messages.append({
                                                "role": "assistant",
                                                "content": assistant_message.content,
                                                "tool_calls": [
                                                    {
                                                        "id": tc.id,
                                                        "type": "function",
                                                        "function": {
                                                            "name": tc.function.name,
                                                            "arguments": tc.function.arguments
                                                        }
                                                    }
                                                    for tc in assistant_message.tool_calls
                                                ]
                                            })

                                            for result in tool_results:
                                                messages.append({
                                                    "role": "tool",
                                                    "tool_call_id": result["tool_call_id"],
                                                    "content": json.dumps(result["result"])
                                                })

                                            # Get follow-up response after tool execution
                                            logger.info("   🤖 Getting follow-up response from Mistral...")
                                            follow_up_start = time.time()
                                            follow_up = client.chat.complete(
                                                model="mistral-large-latest",
                                                messages=messages,
                                                tools=TOOLS,
                                                tool_choice="auto"
                                            )
                                            follow_up_elapsed = time.time() - follow_up_start
                                            full_response = follow_up.choices[0].message.content or full_response
                                            logger.info(f"   ✅ Follow-up response: {len(full_response)} chars in {follow_up_elapsed:.2f}s")
                                            logger.debug(f"   Follow-up preview: {full_response[:150]}...")

                                            # Auto-construct handoff data if we have triage results
                                            if not handoff_data and triage_data:
                                                logger.info("   📋 Auto-constructing handoff data from tool results")
                                                symptoms = []
                                                if "assess_urgency" in tool_arguments:
                                                    symptoms = tool_arguments["assess_urgency"].get("symptoms", [])
                                                elif "suggest_differentials" in tool_arguments:
                                                    symptoms = tool_arguments["suggest_differentials"].get("symptoms", [])

                                                handoff_data = {
                                                    "chief_complaint": ", ".join(symptoms[:3]) if symptoms else "Symptoms assessed",
                                                    "symptoms": symptoms,
                                                    "urgency_assessment": triage_data,
                                                    "differentials": differentials_data or [],
                                                    "recommended_actions": triage_data.get("recommended_actions", []),
                                                    "auto_generated": True
                                                }

                                            # Send handoff data if available
                                            if handoff_data:
                                                logger.info(f"   📋 Sending handoff data to frontend (differentials: {len(handoff_data.get('differentials', []))})")
                                                await websocket.send_json({
                                                    "type": "handoff",
                                                    "data": handoff_data
                                                })

                                        except Exception as tool_block_error:
                                            logger.error(f"   ❌ TOOL EXECUTION BLOCK FAILED: {str(tool_block_error)}")
                                            logger.error(traceback.format_exc())
                                            # Continue with whatever response we have
                                            if not full_response:
                                                full_response = "I apologize, but I encountered an issue processing the clinical assessment. Please try again or consult a healthcare provider directly given the symptoms you've described."
                                                logger.warning("   ⚠️ Using fallback error response")

                                    # Send response in chunks for streaming effect
                                    logger.info(f"   📤 Streaming response to frontend ({len(full_response)} chars)")
                                    chunk_size = 20
                                    for i in range(0, len(full_response), chunk_size):
                                        chunk = full_response[i:i + chunk_size]
                                        await websocket.send_json({
                                            "type": "response",
                                            "text": chunk,
                                            "streaming": True
                                        })
                                        await asyncio.sleep(0.02)  # Small delay for streaming effect

                                    # Add assistant response to conversation
                                    conversation_messages.append({
                                        "role": "assistant",
                                        "content": full_response
                                    })

                                    # Signal response complete
                                    await websocket.send_json({
                                        "type": "response_complete",
                                        "full_text": full_response
                                    })
                                    logger.info("   ✅ Response complete - sent to frontend")

                                    # Generate TTS for the response
                                    if data.get("voice_response", True):
                                        logger.info("   🔊 Generating TTS audio...")
                                        tts_start = time.time()
                                        try:
                                            async with httpx.AsyncClient() as tts_client:
                                                tts_response = await tts_client.post(
                                                    f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream",
                                                    headers={
                                                        "xi-api-key": ELEVENLABS_API_KEY,
                                                        "Content-Type": "application/json"
                                                    },
                                                    json={
                                                        "text": full_response,
                                                        "model_id": "eleven_multilingual_v2",
                                                        "voice_settings": {
                                                            "stability": 0.5,
                                                            "similarity_boost": 0.75
                                                        }
                                                    },
                                                    timeout=60.0
                                                )

                                                tts_elapsed = time.time() - tts_start
                                                if tts_response.status_code == 200:
                                                    audio_data = base64.b64encode(tts_response.content).decode()
                                                    await websocket.send_json({
                                                        "type": "audio",
                                                        "data": audio_data,
                                                        "format": "mp3"
                                                    })
                                                    logger.info(f"   ✅ TTS audio sent ({len(tts_response.content)} bytes) in {tts_elapsed:.2f}s")
                                                else:
                                                    logger.warning(f"   ⚠️ TTS failed: {tts_response.status_code} - {tts_response.text[:100]}")
                                        except Exception as e:
                                            logger.error(f"   ❌ TTS error: {str(e)}")
                                            await websocket.send_json({
                                                "type": "error",
                                                "message": f"TTS failed: {str(e)}"
                                            })

                                else:
                                    logger.error(f"   ❌ Transcription failed: {response.status_code}")
                                    logger.error(f"   Response: {response.text[:200]}")
                                    await websocket.send_json({
                                        "type": "error",
                                        "message": f"Transcription failed: {response.status_code}"
                                    })

                        # Clear buffer for next recording
                        audio_buffer = bytearray()
                        chunk_count = 0
                        logger.info("   🔄 Buffer cleared - ready for next recording")

                    elif data.get("type") == "clear":
                        # Clear conversation history
                        logger.info("   🗑️ Clearing conversation history")
                        conversation_messages = []
                        audio_buffer = bytearray()
                        chunk_count = 0
                        await websocket.send_json({"type": "cleared"})

                except json.JSONDecodeError as e:
                    logger.warning(f"   ⚠️ Invalid JSON received: {str(e)}")

    except WebSocketDisconnect:
        logger.info(f"🔌 WEBSOCKET DISCONNECTED (ID: {ws_id})")
    except Exception as e:
        logger.error(f"❌ WEBSOCKET ERROR (ID: {ws_id}): {str(e)}")
        logger.error(traceback.format_exc())
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass


@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("🏥 DAKTARI BACKEND READY")
    logger.info(f"   Endpoints: http://localhost:8000")
    logger.info(f"   WebSocket: ws://localhost:8000/ws/voice")
    logger.info(f"   Docs: http://localhost:8000/docs")
    logger.info("=" * 60)


if __name__ == "__main__":
    import uvicorn
    from config import HOST, PORT, DEBUG
    logger.info(f"Starting server on {HOST}:{PORT} (debug={DEBUG})")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=DEBUG)

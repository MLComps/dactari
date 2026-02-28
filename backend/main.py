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
from typing import Optional, AsyncGenerator

from config import MISTRAL_API_KEY, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID
from icd10 import lookup_icd10, check_red_flags
from handoff import generate_handoff_pdf
from clinical_tools import suggest_differentials, assess_urgency, generate_recommendations, build_symptom_timeline

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
client = Mistral(api_key=MISTRAL_API_KEY)

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
    if tool_name == "lookup_icd10":
        return await lookup_icd10(arguments["symptom"])
    elif tool_name == "check_red_flags":
        return check_red_flags(arguments["symptoms"])
    elif tool_name == "assess_urgency":
        return await assess_urgency(
            symptoms=arguments["symptoms"],
            severity_score=arguments.get("severity_score", 5),
            duration=arguments.get("duration"),
            vital_signs=arguments.get("vital_signs"),
            red_flags_detected=arguments.get("red_flags_detected")
        )
    elif tool_name == "suggest_differentials":
        return await suggest_differentials(
            symptoms=arguments["symptoms"],
            duration=arguments.get("duration"),
            severity=arguments.get("severity"),
            medical_history=arguments.get("medical_history"),
            age_sex=arguments.get("age_sex"),
            triggers=arguments.get("triggers")
        )
    elif tool_name == "generate_handoff":
        return {"status": "handoff_ready", "data": arguments}
    else:
        return {"error": f"Unknown tool: {tool_name}"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint - handles conversation with Mistral."""
    try:
        messages = [{"role": "system", "content": TRIAGE_SYSTEM_PROMPT}] + request.messages

        response = client.chat.complete(
            model="mistral-large-latest",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"
        )

        assistant_message = response.choices[0].message

        # Check if there are tool calls
        if assistant_message.tool_calls:
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
    try:
        async with httpx.AsyncClient() as http_client:
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
                raise HTTPException(status_code=response.status_code, detail="TTS failed")

            return StreamingResponse(
                io.BytesIO(response.content),
                media_type="audio/mpeg"
            )

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"TTS request failed: {str(e)}")


@app.post("/handoff")
async def create_handoff(request: HandoffRequest):
    """Generate PDF handoff note."""
    try:
        data = request.model_dump()

        # Look up ICD codes for symptoms if not provided
        if not data.get("icd_codes"):
            icd_codes = []
            for symptom in data["symptoms"][:3]:  # Limit to 3 lookups
                result = await lookup_icd10(symptom)
                if result.get("codes"):
                    icd_codes.append(result["codes"][0]["code"])
            data["icd_codes"] = icd_codes if icd_codes else ["Pending"]

        filename = generate_handoff_pdf(data)
        return FileResponse(
            filename,
            media_type="application/pdf",
            filename=filename
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== REAL-TIME STREAMING ENDPOINTS ==============

class StreamingChatRequest(BaseModel):
    messages: list[dict]
    voice_response: bool = False  # If true, also stream TTS


@app.post("/chat/stream")
async def chat_stream(request: StreamingChatRequest):
    """Streaming chat endpoint - returns Server-Sent Events."""

    async def generate() -> AsyncGenerator[str, None]:
        try:
            messages = [{"role": "system", "content": TRIAGE_SYSTEM_PROMPT}] + request.messages

            # Use streaming response from Mistral
            full_response = ""
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {MISTRAL_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "mistral-large-latest",
                        "messages": messages,
                        "stream": True
                    },
                    timeout=60.0
                )

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            if chunk.get("choices") and chunk["choices"][0].get("delta", {}).get("content"):
                                text = chunk["choices"][0]["delta"]["content"]
                                full_response += text
                                yield f"data: {json.dumps({'type': 'text', 'content': text})}\n\n"
                        except json.JSONDecodeError:
                            continue

            # Signal completion
            yield f"data: {json.dumps({'type': 'done', 'full_response': full_response})}\n\n"

        except Exception as e:
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
    """WebSocket endpoint for real-time voice transcription and response.

    Protocol:
    1. Client sends audio chunks as binary data
    2. Server sends back transcription updates as JSON: {"type": "transcription", "text": "..."}
    3. When client sends {"type": "done"}, server processes and responds
    4. Server streams response as JSON: {"type": "response", "text": "..."}
    5. If voice_response enabled, server also sends: {"type": "audio", "data": "base64..."}
    """
    await websocket.accept()

    audio_buffer = bytearray()
    conversation_messages = []

    try:
        while True:
            message = await websocket.receive()

            # Handle binary audio data - just collect, transcribe at the end
            if "bytes" in message:
                audio_buffer.extend(message["bytes"])

            # Handle JSON messages
            elif "text" in message:
                try:
                    data = json.loads(message["text"])

                    if data.get("type") == "stop":
                        # Final transcription
                        if audio_buffer:
                            async with httpx.AsyncClient() as http_client:
                                response = await http_client.post(
                                    "https://api.elevenlabs.io/v1/speech-to-text",
                                    headers={"xi-api-key": ELEVENLABS_API_KEY},
                                    files={"file": ("audio.webm", bytes(audio_buffer), "audio/webm")},
                                    data={"model_id": "scribe_v1"},
                                    timeout=30.0
                                )

                                if response.status_code == 200:
                                    transcription = response.json().get("text", "")
                                    # Send final transcription to frontend
                                    await websocket.send_json({
                                        "type": "transcription",
                                        "text": transcription
                                    })

                                    # Add to conversation and get AI response
                                    conversation_messages.append({
                                        "role": "user",
                                        "content": transcription
                                    })

                                    # Get AI response with tool support
                                    messages = [{"role": "system", "content": TRIAGE_SYSTEM_PROMPT}] + conversation_messages

                                    # Use SDK with tools for proper tool handling
                                    response = client.chat.complete(
                                        model="mistral-large-latest",
                                        messages=messages,
                                        tools=TOOLS,
                                        tool_choice="auto"
                                    )

                                    assistant_message = response.choices[0].message
                                    full_response = assistant_message.content or ""

                                    # Handle tool calls if present
                                    if assistant_message.tool_calls:
                                        tool_results = []
                                        handoff_data = None

                                        for tool_call in assistant_message.tool_calls:
                                            tool_name = tool_call.function.name
                                            arguments = json.loads(tool_call.function.arguments)
                                            result = await execute_tool_call(tool_name, arguments)

                                            if tool_name == "generate_handoff":
                                                handoff_data = result.get("data")

                                            # Send triage data immediately when assess_urgency is called
                                            if tool_name == "assess_urgency":
                                                await websocket.send_json({
                                                    "type": "triage",
                                                    "data": result
                                                })

                                            tool_results.append({
                                                "tool_call_id": tool_call.id,
                                                "name": tool_name,
                                                "result": result
                                            })

                                        # Add tool messages to conversation
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
                                        follow_up = client.chat.complete(
                                            model="mistral-large-latest",
                                            messages=messages,
                                            tools=TOOLS,
                                            tool_choice="auto"
                                        )
                                        full_response = follow_up.choices[0].message.content or full_response

                                        # Send handoff data if available
                                        if handoff_data:
                                            await websocket.send_json({
                                                "type": "handoff",
                                                "data": handoff_data
                                            })

                                    # Send response in chunks for streaming effect
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

                                    # Generate TTS for the response
                                    if data.get("voice_response", True):
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

                                                if tts_response.status_code == 200:
                                                    audio_data = base64.b64encode(tts_response.content).decode()
                                                    await websocket.send_json({
                                                        "type": "audio",
                                                        "data": audio_data,
                                                        "format": "mp3"
                                                    })
                                        except Exception as e:
                                            await websocket.send_json({
                                                "type": "error",
                                                "message": f"TTS failed: {str(e)}"
                                            })

                        # Clear buffer for next recording
                        audio_buffer = bytearray()

                    elif data.get("type") == "clear":
                        # Clear conversation history
                        conversation_messages = []
                        audio_buffer = bytearray()
                        await websocket.send_json({"type": "cleared"})

                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass


if __name__ == "__main__":
    import uvicorn
    from config import HOST, PORT, DEBUG
    uvicorn.run("main:app", host=HOST, port=PORT, reload=DEBUG)

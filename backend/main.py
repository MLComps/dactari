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
TRIAGE_SYSTEM_PROMPT = """You are Daktari, a medical intake assistant for community health workers.

LANGUAGE: Always respond in English. Assume all input is in English.

INTAKE PROTOCOL (follow this order):
1. Greet warmly, ask about chief complaint: "What brings you in today?"
2. Ask onset/duration: "When did this start?"
3. Ask severity: "On a scale of 1-10, how severe is it?"
4. Use the check_red_flags tool to check for emergency symptoms
5. Ask about 2-3 associated symptoms relevant to the chief complaint
6. Ask relevant medical history (chronic conditions, medications, allergies)
7. For each significant symptom, use lookup_icd10 tool to get the medical code
8. Summarize findings back to patient and confirm accuracy
9. Call generate_handoff tool when intake is complete

WHEN CITING MEDICAL DATA:
- When you receive ICD-10 codes from tools, include them in your response like: "headache (ICD-10: R51, Source: WHO ICD-10)"
- Always mention the data source when referencing medical codes or classifications
- Format: "Symptom (ICD-10: CODE, Source: SOURCE_NAME)"

RED FLAGS (escalate immediately):
- Chest pain + shortness of breath → Possible cardiac event
- Severe headache + stiff neck + fever → Possible meningitis
- Bleeding in pregnancy → Obstetric emergency
- Altered consciousness → Neurological emergency
- Face drooping + arm weakness + speech difficulty → Possible stroke

If ANY red flag detected:
1. Say: "⚠️ URGENT: This requires immediate medical attention. Please go to the nearest health facility NOW."
2. Still complete the handoff note for the receiving clinician

RULES:
- NEVER diagnose conditions - only document symptoms
- NEVER prescribe medications or treatments
- You are doing STRUCTURED INTAKE only
- Be warm, patient, and professional
- Ask one question at a time for clarity"""

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
            "description": "Check if combination of symptoms indicates emergency",
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
            "name": "generate_handoff",
            "description": "Generate structured clinical handoff note. Call when intake is complete.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chief_complaint": {"type": "string"},
                    "symptoms": {"type": "array", "items": {"type": "string"}},
                    "duration": {"type": "string"},
                    "severity": {"type": "string"},
                    "red_flags": {"type": "array", "items": {"type": "string"}},
                    "medical_history": {"type": "string"},
                    "patient_language": {"type": "string"},
                    "urgency": {"type": "string", "enum": ["emergency", "urgent", "routine"]}
                },
                "required": ["chief_complaint", "symptoms", "urgency"]
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
    red_flags: Optional[list[str]] = None
    medical_history: Optional[str] = None
    patient_language: Optional[str] = None
    urgency: str = "routine"
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

            # Handle binary audio data
            if "bytes" in message:
                audio_buffer.extend(message["bytes"])

                # If buffer is large enough, do interim transcription
                if len(audio_buffer) > 16000:  # ~1 second of audio
                    try:
                        async with httpx.AsyncClient() as http_client:
                            response = await http_client.post(
                                "https://api.elevenlabs.io/v1/speech-to-text",
                                headers={"xi-api-key": ELEVENLABS_API_KEY},
                                files={"file": ("audio.webm", bytes(audio_buffer), "audio/webm")},
                                data={"model_id": "scribe_v1"},
                                timeout=10.0
                            )
                            if response.status_code == 200:
                                data = response.json()
                                await websocket.send_json({
                                    "type": "transcription",
                                    "text": data.get("text", ""),
                                    "interim": True
                                })
                    except Exception:
                        pass  # Interim transcription failed, continue collecting

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
                                    await websocket.send_json({
                                        "type": "transcription",
                                        "text": transcription,
                                        "interim": False
                                    })

                                    # Add to conversation and get AI response
                                    conversation_messages.append({
                                        "role": "user",
                                        "content": transcription
                                    })

                                    # Stream AI response
                                    messages = [{"role": "system", "content": TRIAGE_SYSTEM_PROMPT}] + conversation_messages

                                    full_response = ""
                                    async with httpx.AsyncClient() as ai_client:
                                        ai_response = await ai_client.post(
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

                                        async for line in ai_response.aiter_lines():
                                            if line.startswith("data: "):
                                                line_data = line[6:]
                                                if line_data == "[DONE]":
                                                    break
                                                try:
                                                    chunk = json.loads(line_data)
                                                    if chunk.get("choices") and chunk["choices"][0].get("delta", {}).get("content"):
                                                        text = chunk["choices"][0]["delta"]["content"]
                                                        full_response += text
                                                        await websocket.send_json({
                                                            "type": "response",
                                                            "text": text,
                                                            "streaming": True
                                                        })
                                                except json.JSONDecodeError:
                                                    continue

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

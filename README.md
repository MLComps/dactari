# Daktari - AI Medical Triage Assistant

<div align="center">

![Daktari Logo](https://img.shields.io/badge/Daktari-Medical_AI-2DD4A8?style=for-the-badge&logo=heart&logoColor=white)

**Multilingual voice-first medical triage assistant powered by Mistral AI**

[Features](#features) • [Quick Start](#quick-start) • [Configuration](#configuration) • [Usage](#usage) • [API](#api-documentation)

</div>

---

## Overview

Daktari is an AI-powered medical triage assistant designed for healthcare workers in multilingual African contexts. It collects patient symptoms via voice or text, conducts structured clinical intake, assesses urgency using the South African Triage Scale (SATS), suggests differential diagnoses with ICD-10 codes, and generates clinical handoff PDFs in SBAR format.

**Built for the Mistral AI Worldwide Hackathon 2026**

### Key Capabilities

- **Voice-First Interface** - Record symptoms in English, French, or Spanish
- **Clinical Triage** - Automated urgency assessment using SATS (South African Triage Scale)
- **ICD-10 Mapping** - Symptoms mapped to standardized medical codes with multilingual support
- **Differential Diagnosis** - AI-suggested conditions ranked by likelihood
- **SBAR Handoff** - Professional clinical handoff PDFs for healthcare providers
- **Red Flag Detection** - Automatic identification of emergency symptoms
- **Medical Image Analysis** - AI-powered visual assessment of visible conditions using Pixtral Large
- **Emergency Helplines** - Geolocation-based emergency numbers for 50+ countries

---

## Features

| Feature | Description |
|---------|-------------|
| **Multilingual Voice Input** | Speech-to-text in 3 languages (English, French, Spanish) via ElevenLabs Scribe |
| **Real-time Transcription** | WebSocket-based streaming for instant feedback |
| **SATS Triage** | 4-level urgency classification (Red/Orange/Yellow/Green) |
| **ICD-10 Codes** | 150+ symptom mappings with multilingual translation support |
| **Differential Suggestions** | AI-generated differentials with confidence levels |
| **Clinical Handoff PDF** | SBAR format with triage banner, differentials, recommendations |
| **Text-to-Speech** | AI voice responses for accessibility |
| **Symptom Timeline** | Visual progression of symptoms over time |
| **Red Flag Alerts** | Keyword + AI-based emergency detection |
| **Medical Image Analysis** | Agentic photo requests for visible conditions (rashes, burns, wounds) via Pixtral Large |
| **Emergency Helplines** | Auto-detected emergency numbers based on user geolocation (50+ countries) |

---

## Tech Stack

### Backend
- **FastAPI** - High-performance Python web framework
- **Mistral AI** - Large (conversation) + Small (clinical tools) + Pixtral Large (image analysis)
- **ElevenLabs** - Speech-to-text (Scribe) and text-to-speech
- **NLM Clinical Tables API** - ICD-10 code lookups
- **ReportLab** - PDF generation
- **WebSockets** - Real-time voice streaming

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool
- **Web Audio API** - Real-time waveform visualization
- **Geolocation API** - Emergency helpline detection
- **BigDataCloud API** - Reverse geocoding for country detection

---

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **npm** or **yarn**

### API Keys Required

| Service | Purpose | Get it at |
|---------|---------|-----------|
| Mistral AI | LLM for conversation, clinical tools & image analysis | [console.mistral.ai](https://console.mistral.ai) |
| ElevenLabs | Speech-to-text & text-to-speech | [elevenlabs.io](https://elevenlabs.io) |

**Note:** ICD-10 lookups use the free NLM Clinical Tables API (no key required). Emergency number geolocation uses the free BigDataCloud API.

### Installation

#### 1. Clone the repository

```bash
git clone https://github.com/yourusername/darktari-mixtral.git
cd darktari-mixtral
```

#### 2. Set up the backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
```

#### 3. Configure API keys

Edit `backend/.env`:

```env
# Required
MISTRAL_API_KEY=your-mistral-api-key-here

# Required for voice features
ELEVENLABS_API_KEY=your-elevenlabs-api-key-here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# Server config
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

#### 4. Set up the frontend

```bash
cd ../frontend

# Install dependencies
npm install
```

#### 5. Configure Vite proxy

The frontend proxies API requests to the backend. This is pre-configured in `vite.config.js`:

```javascript
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
        ws: true,
      },
    },
  },
})
```

---

## Running the Application

### Development Mode

You need **two terminal windows**:

#### Terminal 1 - Backend

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python main.py
```

The backend will start at `http://localhost:8000`

#### Terminal 2 - Frontend

```bash
cd frontend
npm run dev
```

The frontend will start at `http://localhost:5173`

### Production Mode

#### Backend

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend
npm run build
npm run preview
```

### Docker (Recommended)

Run the entire application with a single command using Docker Compose.

#### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed
- [Docker Compose](https://docs.docker.com/compose/install/) installed

#### Quick Start

1. **Create environment file** in the project root:

```bash
cp .env.example .env
```

2. **Edit `.env`** with your API keys:

```env
MISTRAL_API_KEY=your-mistral-api-key-here
ELEVENLABS_API_KEY=your-elevenlabs-api-key-here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
```

3. **Start the application**:

```bash
docker-compose up -d
```

4. **Access the app** at http://localhost:5173

#### Docker Commands

| Command | Description |
|---------|-------------|
| `docker-compose up -d` | Start services in background |
| `docker-compose down` | Stop all services |
| `docker-compose logs -f` | View live logs |
| `docker-compose logs backend` | View backend logs only |
| `docker-compose up -d --build` | Rebuild and restart |
| `docker-compose ps` | Check service status |

#### Services

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:5173 | React application |
| Backend | http://localhost:8000 | FastAPI server |
| API Docs | http://localhost:8000/docs | Swagger documentation |

#### Troubleshooting Docker

**Container not starting?**
```bash
docker-compose logs backend  # Check for errors
```

**Port already in use?**
```bash
docker-compose down
lsof -i :8000  # Find process using port
lsof -i :5173
```

**Rebuild after code changes?**
```bash
docker-compose up -d --build
```

---

## Usage

### 1. Patient Registration

When you open the app, you'll see the **Patient Intake Modal**:

- Enter patient name, age, gender
- Select preferred language (English, Français, Español)
- Optionally add contact number
- View auto-detected emergency helpline based on your location
- Click "Start Triage"

### 2. Describe Symptoms

Choose your input method:

**Voice Input (Recommended)**
1. Click the microphone button or "Start Speaking"
2. Describe symptoms naturally in any supported language
3. Click stop when finished
4. Wait for transcription

**Text Input**
1. Type symptoms in the text field
2. Press Enter or click send

**Quick Start Cards**
- Click a pre-defined symptom card for common presentations

### 3. Clinical Assessment

Daktari will:

1. Ask clarifying questions (duration, severity, history)
2. Map symptoms to ICD-10 codes (multilingual input supported)
3. Check for red flags
4. **Request photos** for visible conditions (rashes, burns, wounds, swelling)
5. Analyze images using Pixtral Large for visual assessment
6. Assess urgency using SATS
7. Generate differential diagnoses

### 4. Triage Result

You'll see:

- **Triage Banner** - Color-coded urgency level
- **Tool Call Cards** - ICD-10 codes, urgency assessment, differentials
- **Progress Stepper** - Intake phase tracking

### 5. Clinical Handoff

When assessment is complete:

- **Handoff Card** appears with summary
- Click **Download PDF** for SBAR clinical note
- Click **Copy Summary** for clipboard text

---

## Project Structure

```
darktari-mixtral/
├── backend/
│   ├── main.py              # FastAPI app, WebSocket handlers, image analysis
│   ├── clinical_tools.py    # Differential, urgency assessment, Pixtral image analysis
│   ├── handoff.py           # PDF generation (SBAR format)
│   ├── icd10.py             # ICD-10 mappings with multilingual symptom translations
│   ├── config.py            # Environment configuration
│   ├── requirements.txt     # Python dependencies
│   ├── .env                 # API keys (create from .env.example)
│   └── .env.example         # Template for environment variables
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main React component
│   │   ├── emergencyNumbers.js  # Emergency helplines database (50+ countries)
│   │   ├── main.jsx         # React entry point
│   │   └── index.css        # Global styles
│   ├── index.html           # HTML template
│   ├── vite.config.js       # Vite configuration
│   └── package.json         # Node dependencies
│
└── README.md                # This file
```

---

## API Documentation

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | Send message, get response |
| POST | `/chat/stream` | Streaming chat response |
| POST | `/tts` | Text-to-speech conversion |
| POST | `/handoff` | Generate PDF handoff |
| POST | `/analyze-image` | Analyze medical image with Pixtral Large |
| GET | `/health` | Health check |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `ws://localhost:8000/ws/voice` | Real-time voice streaming |

#### WebSocket Message Types

**Client → Server:**
```json
// Binary: Audio chunks (WebM/Opus)
// JSON: Stop recording
{ "type": "stop", "voice_response": true, "patient": {...} }
```

**Server → Client:**
```json
{ "type": "transcription", "text": "..." }
{ "type": "response", "text": "..." }
{ "type": "response_complete", "full_text": "..." }
{ "type": "triage", "data": { "color": "yellow", ... } }
{ "type": "handoff", "data": { "differentials": [...], ... } }
{ "type": "image_request", "data": { "reason": "...", "body_area": "...", "condition_type": "..." } }
{ "type": "audio", "data": "<base64>" }
{ "type": "error", "message": "..." }
```

### Clinical Tools (Internal)

| Tool | Purpose |
|------|---------|
| `check_red_flags` | Keyword-based emergency detection |
| `lookup_icd10` | Map symptoms to ICD-10 codes (multilingual) |
| `assess_urgency` | SATS triage assessment |
| `suggest_differentials` | Generate differential diagnoses |
| `request_image` | Agentic photo request for visible conditions |

---

## South African Triage Scale (SATS)

| Color | Level | Time Target | Examples |
|-------|-------|-------------|----------|
| 🔴 Red | Emergency | Immediate | Airway compromise, unconscious, shock |
| 🟠 Orange | Very Urgent | 10 minutes | Severe pain 8-10, chest pain + SOB |
| 🟡 Yellow | Urgent | 60 minutes | Moderate pain 5-7, progressive symptoms |
| 🟢 Green | Routine | 4 hours | Minor injuries, stable chronic symptoms |

---

## Recent Updates

### Medical Image Analysis (Pixtral Large)
The AI can now request photos for visible conditions and analyze them:
- **Agentic requests** - AI determines when a photo would help diagnosis
- **Supported conditions** - Rashes, burns, wounds, swelling, skin conditions, eye issues
- **Visual assessment** - Pixtral Large provides structured analysis including appearance, severity estimate, and recommendations
- **Optional** - Patients can skip image upload if uncomfortable

### Emergency Helplines
Auto-detected emergency numbers based on geolocation:
- **50+ countries** supported with ambulance, police, and fire numbers
- **Africa-focused** - Comprehensive coverage for African nations
- **Geolocation** - Uses browser location + BigDataCloud for country detection
- **One-tap call** - Emergency numbers displayed in patient modal

### Multilingual ICD-10 Support
Symptom recognition now works in multiple languages:
- **French** - 100+ symptom translations (mal de tête → headache)
- **Spanish** - 100+ symptom translations (dolor de cabeza → headache)
- **English** - Primary language with 150+ symptom mappings
- **NLM API** - Clinical Tables API for extended ICD-10 lookups

### Language Support
Interface and conversation available in:
- **English** - Default
- **Français** - French (formal "vous" form)
- **Español** - Spanish (formal "usted" form)

---

## Troubleshooting

### Common Issues

**"WebSocket connection failed"**
- Ensure backend is running on port 8000
- Check that Vite proxy is configured correctly

**"401 Unauthorized" on TTS**
- Verify ELEVENLABS_API_KEY in .env
- Check ElevenLabs account has available credits
- Ensure no extra spaces/quotes in the key

**"Transcription stuck"**
- Check microphone permissions in browser
- Verify ElevenLabs API key is valid
- Check browser console for errors

**"Tool calls showing in response"**
- This indicates the streaming endpoint isn't handling tools
- Ensure you're using the latest backend code

### Debug Mode

Enable debug logging:

```env
DEBUG=true
```

Check backend logs for detailed error messages.

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MISTRAL_API_KEY` | Yes | - | Mistral AI API key (includes Pixtral Large access) |
| `ELEVENLABS_API_KEY` | Yes* | - | ElevenLabs API key (*for voice features) |
| `ELEVENLABS_VOICE_ID` | No | 21m00Tcm4TlvDq8ikWAM | Voice ID for TTS |
| `HOST` | No | 0.0.0.0 | Server host |
| `PORT` | No | 8000 | Server port |
| `DEBUG` | No | true | Enable debug mode |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **Mistral AI** - For the powerful LLM capabilities
- **ElevenLabs** - For multilingual speech recognition
- **South African Triage Group** - For the SATS methodology
- **WHO** - For the ICD-10 classification system

---

<div align="center">

**Built with ♡ for the Mistral AI Worldwide Hackathon 2026**

[Report Bug](https://github.com/yourusername/darktari-mixtral/issues) • [Request Feature](https://github.com/yourusername/darktari-mixtral/issues)

</div>

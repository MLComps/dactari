import { useState, useRef, useEffect, useCallback, useMemo } from 'react'

// ============================================
// DESIGN TOKENS
// ============================================

const tokens = {
  bg: "#0F1419",
  bgSurface: "#1A2332",
  bgCard: "#1E2A3A",
  bgCardHover: "#243447",
  accent: "#2DD4A8",
  accentDim: "rgba(45,212,168,0.15)",
  accentGlow: "rgba(45,212,168,0.25)",
  amber: "#F59E0B",
  red: "#EF4444",
  orange: "#EA580C",
  green: "#16A34A",
  textPrimary: "#F1F5F9",
  textSecondary: "#94A3B8",
  textMuted: "#64748B",
  border: "#2A3A4E",
  userBubble: "#1D4ED8",
}

const triageColors = {
  red: { bg: "rgba(239,68,68,0.15)", border: "#EF4444", text: "#FCA5A5", label: "EMERGENCY", emoji: "🔴", time: "Immediate" },
  orange: { bg: "rgba(234,88,12,0.15)", border: "#EA580C", text: "#FDBA74", label: "VERY URGENT", emoji: "🟠", time: "Within 10 min" },
  yellow: { bg: "rgba(202,138,4,0.15)", border: "#CA8A04", text: "#FDE047", label: "URGENT", emoji: "🟡", time: "Within 60 min" },
  green: { bg: "rgba(22,163,74,0.15)", border: "#16A34A", text: "#86EFAC", label: "ROUTINE", emoji: "🟢", time: "Within 4 hours" },
}

const INTAKE_STEPS = [
  { id: 'complaint', label: 'Chief Complaint' },
  { id: 'severity', label: 'Severity' },
  { id: 'history', label: 'History' },
  { id: 'flags', label: 'Red Flags' },
  { id: 'assessment', label: 'Assessment' },
  { id: 'handoff', label: 'Handoff' },
]

// ============================================
// GLOBAL STYLES
// ============================================

const GlobalStyles = () => (
  <style>{`
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'DM Sans', -apple-system, sans-serif; background: ${tokens.bg}; }
    @keyframes modalIn { from { opacity: 0; transform: scale(0.95) translateY(10px); } to { opacity: 1; transform: scale(1) translateY(0); } }
    @keyframes slideUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes slideDown { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes pulse { 0% { opacity: 0.6; transform: scale(1); } 100% { opacity: 0; transform: scale(1.5); } }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    @keyframes breathe { 0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(239,68,68,0.4); } 50% { transform: scale(1.05); box-shadow: 0 0 0 12px rgba(239,68,68,0); } }
    @keyframes waveform { 0%, 100% { transform: scaleY(0.3); } 50% { transform: scaleY(1); } }
    input:focus, select:focus { border-color: ${tokens.accent} !important; box-shadow: 0 0 0 3px ${tokens.accentDim} !important; outline: none; }
    button:active { transform: scale(0.98); }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: ${tokens.border}; border-radius: 3px; }
  `}</style>
)

// ============================================
// FORM FIELD COMPONENT
// ============================================

function FormField({ label, required, optional, children }) {
  return (
    <div>
      <div style={{
        fontSize: 11, fontWeight: 600, textTransform: "uppercase",
        letterSpacing: "0.08em", color: tokens.textMuted, marginBottom: 8,
        display: "flex", alignItems: "center", gap: 4,
      }}>
        {label}
        {required && <span style={{ color: tokens.accent }}>*</span>}
        {optional && <span style={{ fontWeight: 400, textTransform: "none", letterSpacing: 0 }}>(optional)</span>}
      </div>
      {children}
    </div>
  )
}

const inputStyle = {
  width: "100%", padding: "12px 16px", borderRadius: 12,
  border: `1px solid ${tokens.border}`, background: tokens.bgCard,
  color: tokens.textPrimary, fontSize: 15, outline: "none",
  transition: "border-color 0.2s, box-shadow 0.2s",
  boxSizing: "border-box", fontFamily: "inherit",
}

// ============================================
// PATIENT MODAL
// ============================================

function PatientModal({ isOpen, onSubmit }) {
  const [name, setName] = useState("")
  const [age, setAge] = useState("")
  const [gender, setGender] = useState("")
  const [lang, setLang] = useState("sw")
  const [phone, setPhone] = useState("")

  if (!isOpen) return null

  const canSubmit = name.trim() && age && gender

  const handleSubmit = (e) => {
    e.preventDefault()
    if (canSubmit) {
      onSubmit({ name, age, gender, lang, phone })
    }
  }

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 50,
      display: "flex", alignItems: "center", justifyContent: "center",
      background: "rgba(0,0,0,0.7)", backdropFilter: "blur(16px)",
    }}>
      <div style={{
        width: "100%", maxWidth: 440, margin: "0 16px",
        background: tokens.bgSurface,
        border: `1px solid ${tokens.border}`,
        borderRadius: 20,
        boxShadow: `0 0 60px rgba(45,212,168,0.08), 0 24px 48px rgba(0,0,0,0.4)`,
        overflow: "hidden",
        animation: "modalIn 0.35s ease-out",
      }}>
        {/* Header */}
        <div style={{
          padding: "28px 32px 20px",
          background: `linear-gradient(135deg, ${tokens.bgCard}, ${tokens.bgSurface})`,
          borderBottom: `1px solid ${tokens.border}`,
          display: "flex", alignItems: "center", gap: 16,
        }}>
          <div style={{
            width: 48, height: 48, borderRadius: 14,
            background: `linear-gradient(135deg, ${tokens.accent}, #06B6D4)`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 22,
          }}>
            ♡
          </div>
          <div>
            <div style={{ fontSize: 20, fontWeight: 700, color: tokens.textPrimary }}>
              New Patient Intake
            </div>
            <div style={{ fontSize: 13, color: tokens.textMuted, marginTop: 2 }}>
              Enter details to begin triage assessment
            </div>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ padding: "24px 32px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
          <FormField label="Full Name" required>
            <input
              value={name} onChange={e => setName(e.target.value)}
              placeholder="Patient's full name"
              style={inputStyle}
              autoFocus
            />
          </FormField>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <FormField label="Age" required>
              <input
                value={age} onChange={e => setAge(e.target.value)}
                placeholder="Years" type="number" min="0" max="120"
                style={inputStyle}
              />
            </FormField>
            <FormField label="Gender" required>
              <select value={gender} onChange={e => setGender(e.target.value)} style={{ ...inputStyle, cursor: "pointer" }}>
                <option value="">Select</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </FormField>
          </div>

          <FormField label="Language">
            <div style={{ display: "flex", gap: 8 }}>
              {[
                { code: "sw", name: "Kiswahili" },
                { code: "rw", name: "Kinyarwanda" },
                { code: "en", name: "English" },
                { code: "fr", name: "Français" },
              ].map(l => (
                <button key={l.code} type="button" onClick={() => setLang(l.code)} style={{
                  flex: 1, padding: "10px 0", borderRadius: 10, border: "1px solid",
                  borderColor: lang === l.code ? tokens.accent : tokens.border,
                  background: lang === l.code ? tokens.accentDim : tokens.bgCard,
                  color: lang === l.code ? tokens.accent : tokens.textSecondary,
                  fontSize: 13, fontWeight: 600, cursor: "pointer",
                  transition: "all 0.2s",
                }}>
                  {l.name}
                </button>
              ))}
            </div>
          </FormField>

          <FormField label="Contact" optional>
            <input
              value={phone} onChange={e => setPhone(e.target.value)}
              placeholder="+250 7XX XXX XXX"
              style={inputStyle}
            />
          </FormField>

          <button
            type="submit"
            disabled={!canSubmit}
            style={{
              marginTop: 4, padding: "14px 0", borderRadius: 14, border: "none",
              background: canSubmit
                ? `linear-gradient(135deg, ${tokens.accent}, #06B6D4)`
                : tokens.bgCard,
              color: canSubmit ? "#0F1419" : tokens.textMuted,
              fontSize: 15, fontWeight: 700, cursor: canSubmit ? "pointer" : "not-allowed",
              transition: "all 0.2s",
              letterSpacing: "0.02em",
            }}
          >
            Start Triage →
          </button>
        </form>
      </div>
    </div>
  )
}

// ============================================
// WELCOME SCREEN
// ============================================

function WelcomeScreen({ patient, onStartRecording, onSendMessage }) {
  const quickStarts = [
    { emoji: "🤒", title: "Headache & Fever", desc: "Common symptoms needing assessment", prompt: "I have a headache and fever" },
    { emoji: "🫁", title: "Persistent Cough", desc: "Coughing for 3+ days", prompt: "I've been coughing for several days" },
    { emoji: "💔", title: "Chest Pain", desc: "Requires urgent triage", prompt: "I have chest pain" },
    { emoji: "🧒", title: "Child Symptoms", desc: "Rash, fever, or unusual behavior", prompt: "My child has a fever and rash" },
  ]

  return (
    <div style={{
      flex: 1, display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      padding: "40px 24px", gap: 32,
    }}>
      {/* Hero */}
      <div style={{ textAlign: "center" }}>
        <div style={{
          width: 72, height: 72, borderRadius: 20, margin: "0 auto 16px",
          background: `linear-gradient(135deg, ${tokens.accent}, #06B6D4)`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 32, boxShadow: `0 0 40px ${tokens.accentGlow}`,
        }}>
          ♡
        </div>
        {patient && (
          <div style={{
            display: "inline-flex", padding: "6px 14px", borderRadius: 20,
            background: tokens.bgCard, border: `1px solid ${tokens.border}`,
            fontSize: 13, color: tokens.textSecondary, marginBottom: 16,
            fontWeight: 500,
          }}>
            {patient.name} · {patient.age}y · {patient.gender}
          </div>
        )}
        <h1 style={{
          fontSize: 28, fontWeight: 700, color: tokens.textPrimary, margin: "0 0 8px",
        }}>
          How can I help you today?
        </h1>
        <p style={{ fontSize: 15, color: tokens.textSecondary, margin: 0, lineHeight: 1.5 }}>
          Describe your symptoms. I'll prepare a clinical handoff note.
        </p>
      </div>

      {/* Voice CTA */}
      <button
        onClick={onStartRecording}
        style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "14px 28px", borderRadius: 50,
          background: `linear-gradient(135deg, ${tokens.accent}, #06B6D4)`,
          border: "none", color: "#0F1419", fontSize: 15, fontWeight: 700,
          cursor: "pointer", position: "relative",
          boxShadow: `0 0 30px ${tokens.accentGlow}`,
        }}
      >
        <span style={{ fontSize: 18 }}>🎙</span>
        Start Speaking
        <div style={{
          position: "absolute", inset: -4, borderRadius: 54,
          border: `2px solid ${tokens.accent}`, opacity: 0.4,
          animation: "pulse 2s ease-in-out infinite",
        }} />
      </button>
      <span style={{ fontSize: 13, color: tokens.textMuted, marginTop: -20 }}>or choose below</span>

      {/* Quick start cards */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, width: "100%", maxWidth: 480 }}>
        {quickStarts.map((q, i) => (
          <button
            key={i}
            onClick={() => onSendMessage(q.prompt)}
            style={{
              padding: "20px 18px", borderRadius: 16, border: `1px solid ${tokens.border}`,
              background: tokens.bgCard, cursor: "pointer", textAlign: "left",
              transition: "all 0.2s", display: "flex", flexDirection: "column", gap: 6,
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = tokens.accent
              e.currentTarget.style.background = tokens.bgCardHover
              e.currentTarget.style.transform = "translateY(-2px)"
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = tokens.border
              e.currentTarget.style.background = tokens.bgCard
              e.currentTarget.style.transform = "translateY(0)"
            }}
          >
            <span style={{ fontSize: 24 }}>{q.emoji}</span>
            <span style={{ fontSize: 14, fontWeight: 600, color: tokens.textPrimary }}>{q.title}</span>
            <span style={{ fontSize: 12, color: tokens.textMuted, lineHeight: 1.4 }}>{q.desc}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

// ============================================
// INTAKE STEPPER
// ============================================

function IntakeStepper({ currentStep }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 0,
      padding: "12px 20px",
      background: tokens.bgSurface,
      borderBottom: `1px solid ${tokens.border}`,
      overflowX: "auto",
    }}>
      {INTAKE_STEPS.map((s, i) => (
        <div key={s.id} style={{ display: "flex", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, whiteSpace: "nowrap" }}>
            <div style={{
              width: 22, height: 22, borderRadius: "50%",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 11, fontWeight: 700,
              background: i < currentStep ? tokens.accent
                : i === currentStep ? tokens.accentDim
                : "transparent",
              color: i < currentStep ? "#0F1419"
                : i === currentStep ? tokens.accent
                : tokens.textMuted,
              border: `2px solid ${i <= currentStep ? tokens.accent : tokens.border}`,
              transition: "all 0.3s",
            }}>
              {i < currentStep ? "✓" : i + 1}
            </div>
            <span style={{
              fontSize: 12, fontWeight: i === currentStep ? 600 : 400,
              color: i <= currentStep ? tokens.textPrimary : tokens.textMuted,
            }}>
              {s.label}
            </span>
          </div>
          {i < INTAKE_STEPS.length - 1 && (
            <div style={{
              width: 24, height: 2, margin: "0 6px",
              background: i < currentStep ? tokens.accent : tokens.border,
              borderRadius: 1, transition: "background 0.3s",
            }} />
          )}
        </div>
      ))}
    </div>
  )
}

// ============================================
// TRIAGE BANNER
// ============================================

function TriageBanner({ triageData }) {
  if (!triageData?.color) return null

  const t = triageColors[triageData.color] || triageColors.green

  return (
    <div style={{
      padding: "12px 20px",
      background: t.bg, borderBottom: `1px solid ${t.border}`,
      display: "flex", alignItems: "center", gap: 12,
      animation: "slideDown 0.4s ease-out",
    }}>
      <span style={{ fontSize: 18 }}>{t.emoji}</span>
      <div style={{ flex: 1 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: t.text }}>
          {t.label}
        </span>
        <span style={{ fontSize: 13, color: tokens.textSecondary, marginLeft: 8 }}>
          — Recommend evaluation {t.time.toLowerCase()}
        </span>
      </div>
      <span style={{ fontSize: 12, color: tokens.textMuted }}>SATS</span>
    </div>
  )
}

// ============================================
// TOOL CALL CARD
// ============================================

function ToolCallCard({ tool, status, children }) {
  const config = {
    icd10: { icon: "🔍", label: "ICD-10 Lookup" },
    urgency: { icon: "🚨", label: "Urgency Assessment (SATS)" },
    differentials: { icon: "🧠", label: "Differential Suggestions" },
    handoff: { icon: "📋", label: "Generating Handoff" },
    red_flags: { icon: "⚠️", label: "Red Flag Check" },
  }

  const c = config[tool] || { icon: "⚙️", label: tool }

  return (
    <div style={{
      margin: "8px 0 8px 44px", borderRadius: 12,
      border: `1px solid ${tokens.border}`,
      background: tokens.bgCard, overflow: "hidden",
      animation: "slideUp 0.3s ease-out",
    }}>
      <div style={{
        padding: "10px 16px", display: "flex", alignItems: "center", gap: 8,
        borderBottom: children ? `1px solid ${tokens.border}` : "none",
        fontSize: 13, color: tokens.textSecondary,
      }}>
        <span>{c.icon}</span>
        <span style={{ fontWeight: 600 }}>{c.label}</span>
        {status === "loading" && (
          <span style={{ marginLeft: "auto", animation: "spin 1s linear infinite", display: "inline-block" }}>⟳</span>
        )}
        {status === "done" && (
          <span style={{ marginLeft: "auto", color: tokens.accent }}>✓</span>
        )}
      </div>
      {children && (
        <div style={{ padding: "12px 16px", fontSize: 13, lineHeight: 1.6 }}>
          {children}
        </div>
      )}
    </div>
  )
}

// ============================================
// HANDOFF CARD
// ============================================

function HandoffCard({ handoffData, triageData, patient, onDownload, onCopy }) {
  if (!handoffData) return null

  const t = triageColors[triageData?.color] || triageColors.green
  const differentials = handoffData.differentials || []

  return (
    <div style={{
      margin: "16px 0 16px 44px", borderRadius: 16,
      border: `1px solid ${tokens.accent}`,
      background: tokens.bgCard, overflow: "hidden",
      boxShadow: `0 0 40px ${tokens.accentDim}`,
      animation: "slideUp 0.4s ease-out",
    }}>
      <div style={{
        padding: "20px 24px", borderBottom: `1px solid ${tokens.border}`,
        display: "flex", alignItems: "center", gap: 12,
      }}>
        <div style={{
          width: 40, height: 40, borderRadius: 12,
          background: tokens.accentDim, display: "flex",
          alignItems: "center", justifyContent: "center", fontSize: 20,
        }}>📋</div>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, color: tokens.textPrimary }}>
            Clinical Handoff Ready
          </div>
          <div style={{ fontSize: 12, color: tokens.textMuted, marginTop: 2 }}>
            SBAR format with ICD-10 codes
          </div>
        </div>
      </div>

      <div style={{ padding: "16px 24px" }}>
        {/* Triage mini banner */}
        <div style={{
          padding: "10px 14px", borderRadius: 10, marginBottom: 16,
          background: t.bg, border: `1px solid ${t.border}`,
          fontSize: 13, fontWeight: 600, color: t.text,
        }}>
          {t.emoji} {t.label} — {handoffData.chief_complaint || 'Symptom assessment complete'}
        </div>

        {/* Differentials */}
        {differentials.length > 0 && (
          <>
            <div style={{ fontSize: 12, fontWeight: 600, color: tokens.textMuted, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>
              Top Differentials
            </div>
            {differentials.slice(0, 3).map((d, i) => (
              <div key={i} style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "8px 0", borderBottom: i < Math.min(differentials.length, 3) - 1 ? `1px solid ${tokens.border}` : "none",
              }}>
                <span style={{
                  fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 6,
                  background: d.confidence === "HIGH" ? tokens.accentDim : d.confidence === "MEDIUM" ? "rgba(245,158,11,0.15)" : "rgba(239,68,68,0.15)",
                  color: d.confidence === "HIGH" ? tokens.accent : d.confidence === "MEDIUM" ? tokens.amber : tokens.red,
                }}>
                  {d.confidence}
                </span>
                <span style={{ fontSize: 13, color: tokens.textPrimary, flex: 1 }}>{d.condition}</span>
                <span style={{ fontSize: 12, color: tokens.textMuted, fontFamily: "monospace" }}>{d.icd10_code}</span>
              </div>
            ))}
          </>
        )}
      </div>

      {/* Actions */}
      <div style={{
        padding: "16px 24px", borderTop: `1px solid ${tokens.border}`,
        display: "flex", gap: 12,
      }}>
        <button
          onClick={onDownload}
          style={{
            flex: 1, padding: "12px 0", borderRadius: 10, border: "none",
            background: `linear-gradient(135deg, ${tokens.accent}, #06B6D4)`,
            color: "#0F1419", fontSize: 14, fontWeight: 700, cursor: "pointer",
          }}
        >
          📄 Download PDF
        </button>
        <button
          onClick={onCopy}
          style={{
            flex: 1, padding: "12px 0", borderRadius: 10,
            border: `1px solid ${tokens.border}`, background: tokens.bgSurface,
            color: tokens.textSecondary, fontSize: 14, fontWeight: 600, cursor: "pointer",
          }}
        >
          📋 Copy Summary
        </button>
      </div>

      <div style={{
        padding: "10px 24px 14px", textAlign: "center",
        fontSize: 11, color: tokens.textMuted, fontStyle: "italic",
      }}>
        ⚕️ AI-assisted triage — clinical judgment required
      </div>
    </div>
  )
}

// ============================================
// CHAT BUBBLE
// ============================================

function ChatBubble({ message, onPlayTTS, isPlaying, isVoice }) {
  const isUser = message.role === 'user'
  const isError = message.error

  const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  return (
    <div style={{
      display: "flex", justifyContent: isUser ? "flex-end" : "flex-start",
      gap: 8, animation: "slideUp 0.3s ease-out",
      padding: "4px 0",
    }}>
      {!isUser && (
        <div style={{
          width: 32, height: 32, borderRadius: 10, flexShrink: 0,
          background: `linear-gradient(135deg, ${tokens.accent}, #06B6D4)`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 14, marginTop: 4,
        }}>♡</div>
      )}
      <div style={{
        maxWidth: "75%", padding: "14px 18px", borderRadius: 16,
        borderTopLeftRadius: isUser ? 16 : 4,
        borderTopRightRadius: isUser ? 4 : 16,
        background: isError ? "rgba(239,68,68,0.15)" : isUser ? tokens.userBubble : tokens.bgCard,
        border: isUser ? "none" : `1px solid ${isError ? tokens.red : tokens.border}`,
        color: isError ? "#FCA5A5" : tokens.textPrimary,
        fontSize: 14, lineHeight: 1.65,
      }}>
        <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{message.content}</p>
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          marginTop: 8, gap: 12,
        }}>
          {!isUser && !isError && (
            <button
              onClick={() => onPlayTTS(message.id, message.content)}
              style={{
                display: "flex", alignItems: "center", gap: 4,
                background: "none", border: `1px solid ${tokens.border}`,
                borderRadius: 8, padding: "5px 12px", cursor: "pointer",
                color: isPlaying ? tokens.accent : tokens.textMuted,
                fontSize: 12, transition: "all 0.2s",
              }}
            >
              🔊 {isPlaying ? 'Playing...' : 'Listen'}
            </button>
          )}
          <span style={{ fontSize: 11, color: tokens.textMuted, marginLeft: "auto" }}>
            {isVoice && "🎙 "}
            {timestamp}
          </span>
        </div>
      </div>
    </div>
  )
}

// ============================================
// THINKING INDICATOR
// ============================================

function ThinkingIndicator() {
  return (
    <div style={{
      display: "flex", gap: 8, padding: "4px 0",
      animation: "slideUp 0.3s ease-out",
    }}>
      <div style={{
        width: 32, height: 32, borderRadius: 10,
        background: `linear-gradient(135deg, ${tokens.accent}, #06B6D4)`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 14,
      }}>♡</div>
      <div style={{
        padding: "14px 18px", borderRadius: 16, borderTopLeftRadius: 4,
        background: tokens.bgCard, border: `1px solid ${tokens.border}`,
        display: "flex", alignItems: "center", gap: 8,
      }}>
        <div style={{ display: "flex", gap: 4 }}>
          {[0, 1, 2].map(i => (
            <span key={i} style={{
              width: 8, height: 8, borderRadius: "50%",
              background: tokens.accent,
              animation: `pulse 1.4s ease-in-out ${i * 0.16}s infinite`,
            }} />
          ))}
        </div>
        <span style={{ fontSize: 13, color: tokens.textMuted }}>Thinking...</span>
      </div>
    </div>
  )
}

// ============================================
// TRANSCRIBING INDICATOR
// ============================================

function TranscribingIndicator() {
  return (
    <div style={{
      display: "flex", justifyContent: "center",
      padding: "8px 0", animation: "slideUp 0.3s ease-out",
    }}>
      <div style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "10px 20px", borderRadius: 20,
        background: "rgba(29,78,216,0.15)", border: "1px solid rgba(29,78,216,0.3)",
      }}>
        <div style={{ display: "flex", gap: 4 }}>
          {[0, 1, 2].map(i => (
            <span key={i} style={{
              width: 6, height: 6, borderRadius: "50%",
              background: "#60A5FA",
              animation: `pulse 1.4s ease-in-out ${i * 0.16}s infinite`,
            }} />
          ))}
        </div>
        <span style={{ fontSize: 13, color: "#93C5FD", fontWeight: 500 }}>Transcribing audio...</span>
      </div>
    </div>
  )
}

// ============================================
// STREAMING MESSAGE
// ============================================

function StreamingMessage({ content }) {
  return (
    <div style={{
      display: "flex", gap: 8, padding: "4px 0",
      animation: "slideUp 0.3s ease-out",
    }}>
      <div style={{
        width: 32, height: 32, borderRadius: 10,
        background: `linear-gradient(135deg, ${tokens.accent}, #06B6D4)`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 14,
      }}>♡</div>
      <div style={{
        maxWidth: "75%", padding: "14px 18px", borderRadius: 16, borderTopLeftRadius: 4,
        background: tokens.bgCard, border: `1px solid ${tokens.border}`,
        color: tokens.textPrimary, fontSize: 14, lineHeight: 1.65,
      }}>
        <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>
          {content}
          <span style={{
            display: "inline-block", width: 2, height: 16,
            marginLeft: 2, background: tokens.accent,
            animation: "pulse 1s ease-in-out infinite",
          }} />
        </p>
      </div>
    </div>
  )
}

// ============================================
// AUDIO WAVEFORM
// ============================================

function AudioWaveform({ analyser, isActive }) {
  const canvasRef = useRef(null)
  const animationRef = useRef(null)

  useEffect(() => {
    if (!isActive || !analyser || !canvasRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    const bufferLength = analyser.frequencyBinCount
    const dataArray = new Uint8Array(bufferLength)

    const draw = () => {
      animationRef.current = requestAnimationFrame(draw)
      analyser.getByteFrequencyData(dataArray)

      ctx.clearRect(0, 0, canvas.width, canvas.height)

      const barCount = 24
      const barWidth = (canvas.width / barCount) * 0.7
      const gap = (canvas.width / barCount) * 0.3
      let x = gap / 2

      for (let i = 0; i < barCount; i++) {
        const idx = Math.floor(i * bufferLength / barCount)
        const barHeight = Math.max(4, (dataArray[idx] / 255) * canvas.height * 0.85)

        const gradient = ctx.createLinearGradient(0, canvas.height - barHeight, 0, canvas.height)
        gradient.addColorStop(0, tokens.accent)
        gradient.addColorStop(1, '#06B6D4')

        ctx.fillStyle = gradient
        ctx.beginPath()
        ctx.roundRect(x, canvas.height - barHeight, barWidth, barHeight, 2)
        ctx.fill()

        x += barWidth + gap
      }
    }

    draw()

    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current)
    }
  }, [analyser, isActive])

  if (!isActive) return null

  return (
    <div style={{ display: "flex", justifyContent: "center", padding: "8px 0" }}>
      <canvas ref={canvasRef} width={240} height={48} style={{ borderRadius: 8 }} />
    </div>
  )
}

// ============================================
// STATIC WAVEFORM
// ============================================

function StaticWaveform() {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 3, height: 40, padding: "8px 0" }}>
      {[...Array(9)].map((_, i) => (
        <div
          key={i}
          style={{
            width: 6, height: "100%", borderRadius: 3,
            background: `linear-gradient(to top, ${tokens.accent}, #06B6D4)`,
            animation: `waveform 0.5s ease-in-out ${i * 0.05}s infinite`,
            transformOrigin: "center bottom",
          }}
        />
      ))}
    </div>
  )
}

// ============================================
// MAIN APP COMPONENT
// ============================================

function App() {
  // State
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [streamingResponse, setStreamingResponse] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [playingId, setPlayingId] = useState(null)
  const [handoffData, setHandoffData] = useState(null)
  const [showPatientModal, setShowPatientModal] = useState(true)
  const [patient, setPatient] = useState(null)
  const [triageData, setTriageData] = useState(null)
  const [analyser, setAnalyser] = useState(null)
  const [toolCalls, setToolCalls] = useState([])

  // Refs
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const mediaRecorder = useRef(null)
  const audioChunks = useRef([])
  const wsRef = useRef(null)
  const audioContextRef = useRef(null)
  const audioPlayerRef = useRef(null)

  // Calculate current step
  const currentStep = useMemo(() => {
    if (handoffData) return 5
    if (triageData) return 4
    if (toolCalls.includes('differentials')) return 3
    if (toolCalls.includes('urgency')) return 2
    if (messages.length > 2) return 1
    return 0
  }, [messages, triageData, handoffData, toolCalls])

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingResponse])

  // WebSocket initialization
  const initWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/ws/voice`
    wsRef.current = new WebSocket(wsUrl)

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'transcription':
          setIsTranscribing(false)
          if (data.text.trim()) {
            setMessages(prev => [...prev, { id: Date.now(), role: 'user', content: data.text, isVoice: true }])
            setIsLoading(true)
          } else {
            setIsLoading(false)
          }
          break
        case 'response':
          setIsStreaming(true)
          setStreamingResponse(prev => prev + data.text)
          break
        case 'response_complete':
          setIsStreaming(false)
          setMessages(prev => [...prev, { id: Date.now(), role: 'assistant', content: data.full_text }])
          setStreamingResponse('')
          setIsLoading(false)
          break
        case 'tool_call':
          setToolCalls(prev => [...prev, data.tool])
          break
        case 'audio':
          playAudioFromBase64(data.data)
          break
        case 'handoff':
          setHandoffData(data.data)
          if (data.data?.urgency_assessment) {
            setTriageData(data.data.urgency_assessment)
          }
          break
        case 'triage':
          setTriageData(data.data)
          break
        case 'error':
          console.error('WebSocket error:', data.message)
          setIsTranscribing(false)
          setIsLoading(false)
          setIsStreaming(false)
          break
      }
    }

    wsRef.current.onerror = (error) => console.error('WebSocket error:', error)
    wsRef.current.onclose = () => setTimeout(initWebSocket, 2000)
  }, [])

  useEffect(() => {
    initWebSocket()
    return () => wsRef.current?.close()
  }, [initWebSocket])

  // Audio playback
  const playAudioFromBase64 = (base64Data) => {
    const audioData = atob(base64Data)
    const arrayBuffer = new ArrayBuffer(audioData.length)
    const view = new Uint8Array(arrayBuffer)
    for (let i = 0; i < audioData.length; i++) view[i] = audioData.charCodeAt(i)

    const blob = new Blob([arrayBuffer], { type: 'audio/mpeg' })
    const url = URL.createObjectURL(blob)

    if (audioPlayerRef.current) audioPlayerRef.current.pause()
    audioPlayerRef.current = new Audio(url)
    audioPlayerRef.current.play()
  }

  // Send text message
  const sendMessage = async (text) => {
    if (!text.trim() || isLoading) return

    const userMsg = { id: Date.now(), role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setIsLoading(true)
    setStreamingResponse('')
    setIsStreaming(true)

    try {
      const allMessages = [...messages, userMsg].map(m => ({ role: m.role, content: m.content }))
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: allMessages, voice_response: false, patient })
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let fullResponse = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value)
        const lines = text.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'text') {
                fullResponse += data.content
                setStreamingResponse(fullResponse)
              } else if (data.type === 'done') {
                setMessages(prev => [...prev, { id: Date.now(), role: 'assistant', content: data.full_response }])
              } else if (data.type === 'tool_call') {
                setToolCalls(prev => [...prev, data.tool])
              } else if (data.type === 'triage') {
                setTriageData(data.data)
              } else if (data.type === 'handoff') {
                setHandoffData(data.data)
              }
            } catch (e) {}
          }
        }
      }
    } catch (error) {
      setMessages(prev => [...prev, { id: Date.now(), role: 'assistant', content: 'Sorry, something went wrong.', error: true }])
    } finally {
      setIsLoading(false)
      setIsStreaming(false)
      setStreamingResponse('')
    }
  }

  // Start recording
  const startRecording = async () => {
    try {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        initWebSocket()
        await new Promise(resolve => setTimeout(resolve, 500))
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)()
      const source = audioContextRef.current.createMediaStreamSource(stream)
      const analyserNode = audioContextRef.current.createAnalyser()
      analyserNode.fftSize = 256
      source.connect(analyserNode)
      setAnalyser(analyserNode)

      mediaRecorder.current = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
      audioChunks.current = []

      mediaRecorder.current.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunks.current.push(e.data)
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            e.data.arrayBuffer().then(buffer => wsRef.current.send(buffer))
          }
        }
      }

      mediaRecorder.current.onstop = () => {
        stream.getTracks().forEach(t => t.stop())
        if (audioContextRef.current) {
          audioContextRef.current.close()
          setAnalyser(null)
        }
        setTimeout(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'stop', voice_response: true, patient }))
          }
        }, 100)
      }

      mediaRecorder.current.start(500)
      setIsRecording(true)
    } catch (err) {
      console.error('Mic error:', err)
    }
  }

  // Stop recording
  const stopRecording = () => {
    if (mediaRecorder.current && isRecording) {
      setIsRecording(false)
      setIsTranscribing(true)
      mediaRecorder.current.stop()
    }
  }

  // Play TTS
  const playTTS = async (id, text) => {
    if (playingId === id) {
      audioPlayerRef.current?.pause()
      setPlayingId(null)
      return
    }

    setPlayingId(id)
    try {
      const res = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      })
      if (!res.ok) {
        console.warn('TTS not available')
        setPlayingId(null)
        return
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)

      audioPlayerRef.current = new Audio(url)
      audioPlayerRef.current.onended = () => setPlayingId(null)
      audioPlayerRef.current.play()
    } catch {
      setPlayingId(null)
    }
  }

  // Download handoff
  const downloadHandoff = async () => {
    try {
      const res = await fetch('/api/handoff', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...handoffData, patient })
      })
      const blob = await res.blob()
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `daktari-handoff-${patient?.name || 'patient'}.pdf`
      a.click()
    } catch (err) {
      console.error('Download failed:', err)
    }
  }

  // Copy summary
  const copySummary = async () => {
    const summary = `
DAKTARI CLINICAL HANDOFF
========================
Patient: ${patient?.name || 'Unknown'}, ${patient?.age}y, ${patient?.gender}
Triage: ${triageData?.label || 'Not assessed'}
Chief Complaint: ${handoffData?.chief_complaint || 'N/A'}

Differentials:
${(handoffData?.differentials || []).map(d => `- ${d.condition} (${d.icd10_code}) - ${d.confidence}`).join('\n')}

Generated by Daktari AI Triage Assistant
    `.trim()

    await navigator.clipboard.writeText(summary)
    alert('Summary copied to clipboard!')
  }

  // Handlers
  const handlePatientSubmit = (data) => {
    setPatient(data)
    setShowPatientModal(false)
  }

  const startNewChat = () => {
    setMessages([])
    setHandoffData(null)
    setTriageData(null)
    setToolCalls([])
    setShowPatientModal(true)
    setPatient(null)
  }

  const showWelcome = messages.length === 0 && !streamingResponse && !isTranscribing
  const showChat = !showWelcome

  return (
    <div style={{
      width: "100%", height: "100vh", background: tokens.bg,
      fontFamily: "'DM Sans', -apple-system, sans-serif",
      color: tokens.textPrimary, display: "flex", flexDirection: "column",
      overflow: "hidden", position: "relative",
    }}>
      <GlobalStyles />

      {/* Patient Modal */}
      <PatientModal isOpen={showPatientModal} onSubmit={handlePatientSubmit} />

      {/* Header */}
      {!showPatientModal && (
        <div style={{
          padding: "12px 20px", display: "flex", alignItems: "center", gap: 12,
          background: tokens.bgSurface, borderBottom: `1px solid ${tokens.border}`,
          flexShrink: 0,
        }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: `linear-gradient(135deg, ${tokens.accent}, #06B6D4)`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 16,
          }}>♡</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 16, fontWeight: 700 }}>Daktari</div>
            {patient && (
              <div style={{ fontSize: 12, color: tokens.textSecondary }}>
                {patient.name} · {patient.age}y · {patient.gender}
              </div>
            )}
          </div>
          {handoffData && (
            <button
              onClick={downloadHandoff}
              style={{
                padding: "8px 16px", borderRadius: 10, border: "none",
                background: `linear-gradient(135deg, ${tokens.accent}, #06B6D4)`,
                color: "#0F1419", fontSize: 13, fontWeight: 600, cursor: "pointer",
                marginRight: 8,
              }}
            >
              📄 PDF
            </button>
          )}
          <button
            onClick={startNewChat}
            style={{
              padding: "8px 16px", borderRadius: 10, border: `1px solid ${tokens.border}`,
              background: tokens.bgCard, color: tokens.textSecondary, fontSize: 13,
              fontWeight: 600, cursor: "pointer",
            }}
          >
            + New
          </button>
        </div>
      )}

      {/* Intake Stepper */}
      {showChat && !showPatientModal && (
        <IntakeStepper currentStep={currentStep} />
      )}

      {/* Triage Banner */}
      {triageData && <TriageBanner triageData={triageData} />}

      {/* Main Content */}
      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column" }}>
        {showWelcome && !showPatientModal ? (
          <WelcomeScreen
            patient={patient}
            onStartRecording={startRecording}
            onSendMessage={sendMessage}
          />
        ) : (
          <div style={{ padding: "16px 20px", display: "flex", flexDirection: "column", gap: 8 }}>
            {messages.map((msg) => (
              <ChatBubble
                key={msg.id}
                message={msg}
                onPlayTTS={playTTS}
                isPlaying={playingId === msg.id}
                isVoice={msg.isVoice}
              />
            ))}

            {isTranscribing && <TranscribingIndicator />}
            {isStreaming && streamingResponse && <StreamingMessage content={streamingResponse} />}
            {isLoading && !isStreaming && !streamingResponse && <ThinkingIndicator />}

            {/* Tool call visualizations */}
            {toolCalls.includes('icd10') && (
              <ToolCallCard tool="icd10" status="done" />
            )}
            {toolCalls.includes('urgency') && triageData && (
              <ToolCallCard tool="urgency" status="done">
                <div style={{
                  padding: "8px 12px", borderRadius: 8,
                  background: triageColors[triageData.color]?.bg,
                  border: `1px solid ${triageColors[triageData.color]?.border}`,
                }}>
                  <span style={{ fontWeight: 700, color: triageColors[triageData.color]?.text }}>
                    {triageColors[triageData.color]?.emoji} {triageColors[triageData.color]?.label} — Evaluation {triageColors[triageData.color]?.time.toLowerCase()}
                  </span>
                </div>
              </ToolCallCard>
            )}
            {toolCalls.includes('differentials') && handoffData?.differentials && (
              <ToolCallCard tool="differentials" status="done">
                {handoffData.differentials.slice(0, 3).map((d, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 0" }}>
                    <span style={{
                      fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 4,
                      background: d.confidence === "HIGH" ? tokens.accentDim : d.confidence === "MEDIUM" ? "rgba(245,158,11,0.15)" : "rgba(239,68,68,0.15)",
                      color: d.confidence === "HIGH" ? tokens.accent : d.confidence === "MEDIUM" ? tokens.amber : tokens.red,
                    }}>{d.confidence}</span>
                    <span style={{ fontSize: 13, color: tokens.textPrimary }}>{d.condition}</span>
                    <code style={{ marginLeft: "auto", fontSize: 11, color: tokens.textMuted }}>{d.icd10_code}</code>
                  </div>
                ))}
              </ToolCallCard>
            )}

            {handoffData && (
              <HandoffCard
                handoffData={handoffData}
                triageData={triageData}
                patient={patient}
                onDownload={downloadHandoff}
                onCopy={copySummary}
              />
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      {!showPatientModal && (
        <div style={{
          padding: "12px 16px", background: tokens.bgSurface,
          borderTop: `1px solid ${tokens.border}`,
          flexShrink: 0,
        }}>
          {/* Waveform */}
          {isRecording && (
            analyser ? <AudioWaveform analyser={analyser} isActive={isRecording} /> : <StaticWaveform />
          )}

          {/* Input row */}
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button
              onClick={isRecording ? stopRecording : startRecording}
              disabled={(isLoading || isTranscribing) && !isRecording}
              style={{
                width: 44, height: 44, borderRadius: "50%",
                border: isRecording ? "none" : `1px solid ${tokens.border}`,
                background: isRecording ? tokens.red : tokens.bgCard,
                color: isRecording ? "white" : tokens.textMuted,
                fontSize: 18, cursor: "pointer", flexShrink: 0,
                display: "flex", alignItems: "center", justifyContent: "center",
                animation: isRecording ? "breathe 2s ease-in-out infinite" : "none",
                opacity: (isLoading || isTranscribing) && !isRecording ? 0.5 : 1,
              }}
            >
              {isRecording ? "⏹" : "🎙"}
            </button>

            <input
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), sendMessage(input))}
              placeholder={isRecording ? "Listening..." : isTranscribing ? "Transcribing..." : "Describe your symptoms..."}
              disabled={isLoading || isRecording || isTranscribing}
              style={{
                flex: 1, padding: "12px 20px", borderRadius: 24,
                border: `1px solid ${tokens.border}`, background: tokens.bgCard,
                color: tokens.textPrimary, fontSize: 14, outline: "none",
                opacity: (isLoading || isRecording || isTranscribing) ? 0.5 : 1,
              }}
            />

            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || isLoading}
              style={{
                width: 44, height: 44, borderRadius: "50%", border: "none",
                background: input.trim() && !isLoading
                  ? `linear-gradient(135deg, ${tokens.accent}, #06B6D4)`
                  : tokens.bgCard,
                color: input.trim() && !isLoading ? "#0F1419" : tokens.textMuted,
                fontSize: 16, cursor: input.trim() && !isLoading ? "pointer" : "not-allowed",
                flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center",
              }}
            >
              ➤
            </button>
          </div>

          {/* Recording indicator */}
          {isRecording && (
            <div style={{
              display: "flex", alignItems: "center", justifyContent: "center",
              gap: 8, marginTop: 10, color: tokens.red, fontSize: 13,
            }}>
              <span style={{
                width: 8, height: 8, borderRadius: "50%",
                background: tokens.red, animation: "pulse 1s ease-in-out infinite",
              }} />
              Recording... tap stop when finished
            </div>
          )}

          {/* Disclaimer */}
          <div style={{
            textAlign: "center", padding: "8px 0 4px",
            fontSize: 11, color: tokens.textMuted,
          }}>
            AI-assisted triage — always consult a healthcare provider
          </div>
        </div>
      )}
    </div>
  )
}

export default App

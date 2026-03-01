import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import { detectEmergencyNumbers, getEmergencyNumbers, DEFAULT_EMERGENCY } from './emergencyNumbers'

// ============================================
// DESIGN TOKENS
// ============================================

const tokens = {
  // Background layers
  bg: "#F8FAFB",
  bgSurface: "#FFFFFF",
  bgCard: "#FFFFFF",
  bgRecessed: "#F1F5F9",
  bgCardHover: "#E8EDF2",

  // Accent (teal)
  accent: "#0D9B7A",
  accentLight: "#2DD4A8",
  accentDim: "rgba(13, 155, 122, 0.08)",
  accentDimBorder: "rgba(13, 155, 122, 0.25)",

  // Text hierarchy
  textPrimary: "#111827",
  textSecondary: "#4B5563",
  textMuted: "#9CA3AF",
  textPlaceholder: "#CBD5E1",

  // Borders & shadows
  border: "#E5E7EB",
  shadow: "0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)",
  shadowMd: "0 4px 12px rgba(0,0,0,0.08)",
  shadowLg: "0 8px 24px rgba(0,0,0,0.12)",

  // User bubble
  userBubbleBg: "#0D9B7A",
  userBubbleText: "#FFFFFF",

  // Semantic
  red: "#DC2626",
  orange: "#EA580C",
  amber: "#A16207",
  green: "#15803D",
}

const triageColors = {
  red: { bg: "#FEF2F2", border: "#FECACA", text: "#DC2626", label: "EMERGENCY", time: "Immediate" },
  orange: { bg: "#FFF7ED", border: "#FED7AA", text: "#EA580C", label: "VERY URGENT", time: "Within 10 min" },
  yellow: { bg: "#FEFCE8", border: "#FDE68A", text: "#A16207", label: "URGENT", time: "Within 60 min" },
  green: { bg: "#F0FDF4", border: "#BBF7D0", text: "#15803D", label: "ROUTINE", time: "Within 4 hours" },
}

// ============================================
// DUAL-TONE ICON COMPONENTS
// ============================================

const Icon = {
  // Heart/Medical icon
  Heart: ({ size = 24, primary = tokens.accent, secondary = "#06B6D4" }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" fill={primary} fillOpacity="0.2"/>
      <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" stroke={secondary} strokeWidth="1.5" fill="none"/>
    </svg>
  ),

  // Microphone icon
  Mic: ({ size = 24, primary = tokens.accent, secondary = "#06B6D4" }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <rect x="9" y="2" width="6" height="11" rx="3" fill={primary} fillOpacity="0.2" stroke={secondary} strokeWidth="1.5"/>
      <path d="M5 10v1a7 7 0 0014 0v-1" stroke={primary} strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M12 19v3m-3 0h6" stroke={secondary} strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  ),

  // Stop icon
  Stop: ({ size = 24, primary = tokens.red, secondary = "#FCA5A5" }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <rect x="6" y="6" width="12" height="12" rx="2" fill={primary} fillOpacity="0.3" stroke={secondary} strokeWidth="1.5"/>
    </svg>
  ),

  // Send icon
  Send: ({ size = 24, primary = tokens.accent, secondary = "#06B6D4" }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M22 2L11 13" stroke={secondary} strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M22 2L15 22L11 13L2 9L22 2Z" fill={primary} fillOpacity="0.2" stroke={primary} strokeWidth="1.5" strokeLinejoin="round"/>
    </svg>
  ),

  // Speaker icon
  Speaker: ({ size = 20, primary = tokens.accent, secondary = "#06B6D4", playing = false }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M11 5L6 9H2v6h4l5 4V5z" fill={playing ? primary : "none"} fillOpacity="0.2" stroke={playing ? primary : secondary} strokeWidth="1.5"/>
      {playing && (
        <>
          <path d="M15.54 8.46a5 5 0 010 7.07" stroke={primary} strokeWidth="1.5" strokeLinecap="round"/>
          <path d="M19.07 4.93a10 10 0 010 14.14" stroke={secondary} strokeWidth="1.5" strokeLinecap="round"/>
        </>
      )}
      {!playing && (
        <path d="M15.54 8.46a5 5 0 010 7.07M19.07 4.93a10 10 0 010 14.14" stroke={secondary} strokeWidth="1.5" strokeLinecap="round" opacity="0.5"/>
      )}
    </svg>
  ),

  // Document icon
  Document: ({ size = 24, primary = tokens.accent, secondary = "#06B6D4" }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" fill={primary} fillOpacity="0.15" stroke={secondary} strokeWidth="1.5"/>
      <path d="M14 2v6h6" stroke={primary} strokeWidth="1.5"/>
      <path d="M8 13h8M8 17h5" stroke={secondary} strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  ),

  // Copy icon
  Copy: ({ size = 24, primary = tokens.accent, secondary = "#06B6D4" }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <rect x="9" y="9" width="10" height="10" rx="2" fill={primary} fillOpacity="0.15" stroke={secondary} strokeWidth="1.5"/>
      <path d="M5 15V5a2 2 0 012-2h10" stroke={primary} strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  ),

  // Plus icon
  Plus: ({ size = 20, primary = tokens.accent, secondary = "#06B6D4" }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" fill={primary} fillOpacity="0.1" stroke={secondary} strokeWidth="1.5"/>
      <path d="M12 8v8M8 12h8" stroke={primary} strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  ),

  // Search/Lookup icon
  Search: ({ size = 20, primary = tokens.accent, secondary = "#06B6D4" }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="11" cy="11" r="7" fill={primary} fillOpacity="0.15" stroke={secondary} strokeWidth="1.5"/>
      <path d="M21 21l-4.35-4.35" stroke={primary} strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  ),

  // Alert/Warning icon
  Alert: ({ size = 20, primary = tokens.amber, secondary = "#FDE047" }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M12 2L2 20h20L12 2z" fill={primary} fillOpacity="0.15" stroke={secondary} strokeWidth="1.5" strokeLinejoin="round"/>
      <path d="M12 9v4M12 17h.01" stroke={primary} strokeWidth="2" strokeLinecap="round"/>
    </svg>
  ),

  // Brain/Differentials icon
  Brain: ({ size = 20, primary = tokens.accent, secondary = "#06B6D4" }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M12 2a7 7 0 00-7 7c0 2.38 1.19 4.47 3 5.74V17a2 2 0 002 2h4a2 2 0 002-2v-2.26c1.81-1.27 3-3.36 3-5.74a7 7 0 00-7-7z" fill={primary} fillOpacity="0.15" stroke={secondary} strokeWidth="1.5"/>
      <path d="M9 21h6" stroke={primary} strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M9 9a3 3 0 013-3m3 3a3 3 0 00-3-3" stroke={secondary} strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  ),

  // Urgency/Clock icon
  Urgency: ({ size = 20, primary = tokens.red, secondary = "#FCA5A5" }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" fill={primary} fillOpacity="0.15" stroke={secondary} strokeWidth="1.5"/>
      <path d="M12 7v5l3 3" stroke={primary} strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  ),

  // Gear/Settings icon
  Gear: ({ size = 20, primary = tokens.textSecondary, secondary = tokens.textMuted }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="3" fill={primary} fillOpacity="0.2" stroke={secondary} strokeWidth="1.5"/>
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" stroke={primary} strokeWidth="1.5"/>
    </svg>
  ),

  // Checkmark icon
  Check: ({ size = 16, primary = tokens.accent }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M20 6L9 17l-5-5" stroke={primary} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),

  // Spinner icon
  Spinner: ({ size = 16, primary = tokens.accent }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ animation: "spin 1s linear infinite" }}>
      <circle cx="12" cy="12" r="9" stroke={primary} strokeWidth="2" strokeOpacity="0.25"/>
      <path d="M12 3a9 9 0 019 9" stroke={primary} strokeWidth="2" strokeLinecap="round"/>
    </svg>
  ),

  // Triage indicator dot
  TriageDot: ({ color = "green", size = 18 }) => {
    const c = triageColors[color] || triageColors.green
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="8" fill={c.bg} stroke={c.border} strokeWidth="2"/>
        <circle cx="12" cy="12" r="4" fill={c.border}/>
      </svg>
    )
  },

  // Medical cross icon
  Medical: ({ size = 24, primary = tokens.accent, secondary = "#06B6D4" }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <rect x="3" y="3" width="18" height="18" rx="3" fill={primary} fillOpacity="0.15" stroke={secondary} strokeWidth="1.5"/>
      <path d="M12 7v10M7 12h10" stroke={primary} strokeWidth="2" strokeLinecap="round"/>
    </svg>
  ),

  // Phone icon for emergency calls
  Phone: ({ size = 24, primary = tokens.red, secondary = "#FCA5A5" }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 16.92z" fill={primary} fillOpacity="0.2" stroke={secondary} strokeWidth="1.5"/>
    </svg>
  ),

  // Location pin icon
  Location: ({ size = 20, primary = tokens.accent, secondary = "#06B6D4" }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" fill={primary} fillOpacity="0.2" stroke={secondary} strokeWidth="1.5"/>
      <circle cx="12" cy="9" r="2.5" fill={primary} stroke={secondary} strokeWidth="1"/>
    </svg>
  ),

  // Fever icon
  Fever: ({ size = 28 }) => (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <circle cx="16" cy="16" r="12" fill="rgba(239,68,68,0.15)" stroke="#EF4444" strokeWidth="1.5"/>
      <path d="M16 10v8M16 22v.01" stroke="#FCA5A5" strokeWidth="2" strokeLinecap="round"/>
      <circle cx="10" cy="12" r="1.5" fill="#EF4444"/>
      <circle cx="22" cy="12" r="1.5" fill="#EF4444"/>
    </svg>
  ),

  // Cough icon
  Cough: ({ size = 28 }) => (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <ellipse cx="16" cy="18" rx="8" ry="6" fill="rgba(59,130,246,0.15)" stroke="#3B82F6" strokeWidth="1.5"/>
      <path d="M8 14c0-4 4-8 8-8s8 4 8 8" stroke="#93C5FD" strokeWidth="1.5" strokeLinecap="round"/>
      <circle cx="24" cy="10" r="2" fill="#3B82F6" fillOpacity="0.4" stroke="#93C5FD"/>
      <circle cx="27" cy="8" r="1.5" fill="#3B82F6" fillOpacity="0.3"/>
    </svg>
  ),

  // Chest pain icon
  ChestPain: ({ size = 28 }) => (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <path d="M16 28l-1.5-1.4C8.5 21 5 17.8 5 13.5 5 10 8 7 11.5 7c2 0 3.9.9 4.5 2.3C16.6 7.9 18.5 7 20.5 7 24 7 27 10 27 13.5c0 4.3-3.5 7.5-9.5 13.1L16 28z" fill="rgba(239,68,68,0.2)" stroke="#EF4444" strokeWidth="1.5"/>
      <path d="M10 15l3 3 5-6" stroke="#FCA5A5" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),

  // Child icon
  Child: ({ size = 28 }) => (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <circle cx="16" cy="10" r="5" fill="rgba(168,85,247,0.15)" stroke="#A855F7" strokeWidth="1.5"/>
      <path d="M10 28v-5a6 6 0 0112 0v5" fill="rgba(168,85,247,0.1)" stroke="#C084FC" strokeWidth="1.5"/>
      <circle cx="14" cy="9" r="1" fill="#A855F7"/>
      <circle cx="18" cy="9" r="1" fill="#A855F7"/>
      <path d="M14 12c.5.5 1.5.5 2 0" stroke="#A855F7" strokeWidth="1" strokeLinecap="round"/>
    </svg>
  ),
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
    body { font-family: 'DM Sans', -apple-system, sans-serif; background: ${tokens.bg}; color: ${tokens.textPrimary}; }
    @keyframes modalIn { from { opacity: 0; transform: scale(0.95) translateY(10px); } to { opacity: 1; transform: scale(1) translateY(0); } }
    @keyframes slideUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes slideDown { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes pulse { 0% { opacity: 0.6; transform: scale(1); } 100% { opacity: 0; transform: scale(1.5); } }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    @keyframes breathe { 0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(220,38,38,0.4); } 50% { transform: scale(1.05); box-shadow: 0 0 0 12px rgba(220,38,38,0); } }
    @keyframes waveform { 0%, 100% { transform: scaleY(0.3); } 50% { transform: scaleY(1); } }
    input:focus, select:focus, textarea:focus { border-color: ${tokens.accent} !important; box-shadow: 0 0 0 3px ${tokens.accentDim}, 0 0 0 1px ${tokens.accentDimBorder} !important; outline: none; }
    button:active { transform: scale(0.98); }
    ::placeholder { color: ${tokens.textPlaceholder}; }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #D1D5DB; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #9CA3AF; }

    /* Markdown content styles */
    .markdown-content { line-height: 1.65; color: ${tokens.textSecondary}; }
    .markdown-content > *:last-child { margin-bottom: 0 !important; }
    .markdown-content p { margin-bottom: 8px; }
    .markdown-content ul, .markdown-content ol { margin: 8px 0; padding-left: 20px; }
    .markdown-content li { margin-bottom: 4px; }
    .markdown-content li::marker { color: ${tokens.accentLight}; }
    .markdown-content strong { font-weight: 600; color: ${tokens.textPrimary}; }
    .markdown-content em { font-style: italic; }
    .markdown-content code {
      background: ${tokens.accentDim};
      border: 1px solid ${tokens.accentDimBorder};
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 13px;
      font-family: 'SF Mono', Monaco, monospace;
      color: ${tokens.accent};
    }
    .markdown-content blockquote {
      border-left: 3px solid ${tokens.accentLight};
      margin: 8px 0;
      padding-left: 12px;
      color: ${tokens.textSecondary};
      font-style: italic;
    }
    .markdown-content h1, .markdown-content h2, .markdown-content h3 {
      font-weight: 600;
      margin-top: 12px;
      margin-bottom: 6px;
      color: ${tokens.textPrimary};
    }
    .markdown-content h1 { font-size: 18px; }
    .markdown-content h2 { font-size: 16px; }
    .markdown-content h3 { font-size: 15px; }
    .markdown-content hr {
      border: none;
      border-top: 1px solid ${tokens.border};
      margin: 12px 0;
    }
    .markdown-content a {
      color: ${tokens.accent};
      text-decoration: underline;
    }
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
  border: `1px solid ${tokens.border}`, background: tokens.bgRecessed,
  color: tokens.textPrimary, fontSize: 15, outline: "none",
  transition: "border-color 0.2s, box-shadow 0.2s",
  boxSizing: "border-box", fontFamily: "inherit",
}

// ============================================
// PATIENT MODAL
// ============================================

function PatientModal({ isOpen, onSubmit, emergencyData, userLocation, locationLoading }) {
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
      background: "rgba(17,24,39,0.3)", backdropFilter: "blur(8px)",
    }}>
      <div style={{
        width: "100%", maxWidth: 440, margin: "0 16px",
        background: tokens.bgSurface,
        borderRadius: 20,
        boxShadow: tokens.shadowLg,
        overflow: "hidden",
        animation: "modalIn 0.35s ease-out",
      }}>
        {/* Header */}
        <div style={{
          padding: "28px 32px 20px",
          background: tokens.bgSurface,
          borderBottom: `1px solid ${tokens.border}`,
          display: "flex", alignItems: "center", gap: 16,
        }}>
          <div style={{
            width: 48, height: 48, borderRadius: 14,
            background: `linear-gradient(135deg, #0D9B7A, #0891B2)`,
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: tokens.shadow,
          }}>
            <Icon.Heart size={26} primary="#FFFFFF" secondary="#FFFFFF" />
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
                  flex: 1, padding: "10px 0", borderRadius: 10,
                  border: lang === l.code ? `1px solid ${tokens.accentDimBorder}` : `1px solid ${tokens.border}`,
                  background: lang === l.code ? tokens.accentDim : tokens.bgRecessed,
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

          {/* Emergency info section */}
          <div style={{
            padding: "14px 16px", borderRadius: 12,
            background: "rgba(220,38,38,0.06)",
            border: "1px solid rgba(220,38,38,0.15)",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
              <Icon.Phone size={18} primary={tokens.red} secondary="#FCA5A5" />
              <span style={{ fontSize: 13, fontWeight: 600, color: tokens.red }}>
                Emergency Services
              </span>
              {locationLoading && (
                <span style={{ marginLeft: "auto" }}>
                  <Icon.Spinner size={14} primary={tokens.textMuted} />
                </span>
              )}
            </div>
            {emergencyData ? (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <div style={{ fontSize: 12, color: tokens.textMuted, display: "flex", alignItems: "center", gap: 4 }}>
                    <Icon.Location size={12} primary={tokens.textMuted} secondary={tokens.textMuted} />
                    {userLocation?.city ? `${userLocation.city}, ` : ''}{emergencyData.country}
                  </div>
                  <div style={{ fontSize: 11, color: tokens.textMuted, marginTop: 2 }}>
                    Ambulance: {emergencyData.ambulance} | Police: {emergencyData.police}
                  </div>
                </div>
                <a
                  href={`tel:${emergencyData.ambulance}`}
                  style={{
                    padding: "8px 14px", borderRadius: 8,
                    background: tokens.red, color: "#FFFFFF",
                    fontSize: 13, fontWeight: 700, textDecoration: "none",
                    display: "flex", alignItems: "center", gap: 6,
                  }}
                >
                  <Icon.Phone size={14} primary="#FFFFFF" secondary="#FCA5A5" />
                  {emergencyData.display}
                </a>
              </div>
            ) : (
              <div style={{ fontSize: 12, color: tokens.textMuted }}>
                {locationLoading ? "Detecting your location..." : "Emergency: 112 (International)"}
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={!canSubmit}
            style={{
              marginTop: 4, padding: "14px 0", borderRadius: 14, border: "none",
              background: canSubmit
                ? `linear-gradient(135deg, #0D9B7A, #0891B2)`
                : tokens.border,
              color: canSubmit ? "#FFFFFF" : tokens.textMuted,
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

function WelcomeScreen({ patient, onStartRecording, onSendMessage, emergencyData, userLocation }) {
  const quickStarts = [
    { icon: "fever", title: "Headache & Fever", desc: "Common symptoms needing assessment", prompt: "I have a headache and fever" },
    { icon: "cough", title: "Persistent Cough", desc: "Coughing for 3+ days", prompt: "I've been coughing for several days" },
    { icon: "chest", title: "Chest Pain", desc: "Requires urgent triage", prompt: "I have chest pain" },
    { icon: "child", title: "Child Symptoms", desc: "Rash, fever, or unusual behavior", prompt: "My child has a fever and rash" },
  ]

  const QuickStartIcon = ({ type }) => {
    switch (type) {
      case "fever": return <Icon.Fever size={28} />
      case "cough": return <Icon.Cough size={28} />
      case "chest": return <Icon.ChestPain size={28} />
      case "child": return <Icon.Child size={28} />
      default: return <Icon.Medical size={28} />
    }
  }

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
          background: `linear-gradient(135deg, #0D9B7A, #0891B2)`,
          display: "flex", alignItems: "center", justifyContent: "center",
          boxShadow: tokens.shadowLg,
        }}>
          <Icon.Heart size={36} primary="#FFFFFF" secondary="#FFFFFF" />
        </div>
        {patient && (
          <div style={{
            display: "inline-flex", padding: "6px 14px", borderRadius: 20,
            background: tokens.accentDim, border: `1px solid ${tokens.accentDimBorder}`,
            fontSize: 13, color: tokens.accent, marginBottom: 16,
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
          background: `linear-gradient(135deg, #0D9B7A, #0891B2)`,
          border: "none", color: "#FFFFFF", fontSize: 15, fontWeight: 700,
          cursor: "pointer", position: "relative",
          boxShadow: tokens.shadowMd,
        }}
      >
        <Icon.Mic size={20} primary="#FFFFFF" secondary="#FFFFFF" />
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
              padding: "20px 18px", borderRadius: 16, border: "none",
              background: tokens.bgSurface, cursor: "pointer", textAlign: "left",
              transition: "all 0.2s", display: "flex", flexDirection: "column", gap: 8,
              boxShadow: tokens.shadow,
            }}
            onMouseEnter={e => {
              e.currentTarget.style.boxShadow = tokens.shadowMd
              e.currentTarget.style.background = tokens.bgCardHover
              e.currentTarget.style.transform = "translateY(-2px)"
            }}
            onMouseLeave={e => {
              e.currentTarget.style.boxShadow = tokens.shadow
              e.currentTarget.style.background = tokens.bgSurface
              e.currentTarget.style.transform = "translateY(0)"
            }}
          >
            <QuickStartIcon type={q.icon} />
            <span style={{ fontSize: 14, fontWeight: 600, color: tokens.textPrimary }}>{q.title}</span>
            <span style={{ fontSize: 12, color: tokens.textMuted, lineHeight: 1.4 }}>{q.desc}</span>
          </button>
        ))}
      </div>

      {/* Emergency info footer */}
      {emergencyData && (
        <a
          href={`tel:${emergencyData.ambulance || emergencyData.display}`}
          style={{
            marginTop: 8, padding: "10px 20px", borderRadius: 12,
            background: "rgba(220,38,38,0.06)", border: "1px solid rgba(220,38,38,0.12)",
            display: "flex", alignItems: "center", gap: 10,
            textDecoration: "none", color: tokens.textSecondary,
            maxWidth: 480, width: "100%",
          }}
        >
          <Icon.Phone size={18} primary={tokens.red} secondary="#FCA5A5" />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: tokens.red }}>
              Emergency: {emergencyData.display}
            </div>
            <div style={{ fontSize: 11, color: tokens.textMuted, display: "flex", alignItems: "center", gap: 4 }}>
              <Icon.Location size={10} primary={tokens.textMuted} secondary={tokens.textMuted} />
              {userLocation?.city ? `${userLocation.city}, ` : ''}{emergencyData.country}
            </div>
          </div>
          <span style={{ fontSize: 11, color: tokens.textMuted }}>Tap to call</span>
        </a>
      )}
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
      boxShadow: tokens.shadow,
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
              color: i < currentStep ? "#FFFFFF"
                : i === currentStep ? tokens.accent
                : tokens.textMuted,
              border: `2px solid ${i <= currentStep ? tokens.accent : tokens.border}`,
              transition: "all 0.3s",
            }}>
              {i < currentStep ? <Icon.Check size={12} primary="#FFFFFF" /> : i + 1}
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
      background: t.bg,
      borderLeft: `4px solid ${t.text}`,
      display: "flex", alignItems: "center", gap: 12,
      animation: "slideDown 0.4s ease-out",
    }}>
      <Icon.TriageDot color={triageData.color} size={20} />
      <div style={{ flex: 1 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: t.text }}>
          {t.label}
        </span>
        <span style={{ fontSize: 13, color: tokens.textSecondary, marginLeft: 8 }}>
          — Recommend evaluation {t.time.toLowerCase()}
        </span>
      </div>
      <span style={{
        fontSize: 11, color: t.text, fontWeight: 600,
        padding: "3px 10px", borderRadius: 6,
        background: tokens.bgSurface,
        boxShadow: tokens.shadow,
      }}>SATS</span>
    </div>
  )
}

// ============================================
// TOOL CALL CARD
// ============================================

function ToolCallCard({ tool, status, children }) {
  const getIcon = () => {
    switch (tool) {
      case 'icd10': return <Icon.Search size={18} />
      case 'urgency': return <Icon.Urgency size={18} />
      case 'differentials': return <Icon.Brain size={18} />
      case 'handoff': return <Icon.Document size={18} />
      case 'red_flags': return <Icon.Alert size={18} />
      default: return <Icon.Gear size={18} />
    }
  }

  const labels = {
    icd10: "ICD-10 Lookup",
    urgency: "Urgency Assessment (SATS)",
    differentials: "Differential Suggestions",
    handoff: "Generating Handoff",
    red_flags: "Red Flag Check",
  }

  return (
    <div style={{
      margin: "8px 0 8px 44px", borderRadius: 12,
      background: tokens.bgSurface, overflow: "hidden",
      animation: "slideUp 0.3s ease-out",
      boxShadow: tokens.shadow,
    }}>
      <div style={{
        padding: "10px 16px", display: "flex", alignItems: "center", gap: 10,
        borderBottom: children ? `1px solid ${tokens.border}` : "none",
        fontSize: 13, color: tokens.textSecondary,
        background: tokens.bgRecessed,
      }}>
        {getIcon()}
        <span style={{ fontWeight: 600 }}>{labels[tool] || tool}</span>
        {status === "loading" && (
          <span style={{ marginLeft: "auto" }}><Icon.Spinner size={16} /></span>
        )}
        {status === "done" && (
          <span style={{ marginLeft: "auto" }}><Icon.Check size={16} /></span>
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
      borderLeft: `4px solid ${tokens.accent}`,
      background: tokens.bgSurface, overflow: "hidden",
      boxShadow: tokens.shadowMd,
      animation: "slideUp 0.4s ease-out",
    }}>
      <div style={{
        padding: "20px 24px", borderBottom: `1px solid ${tokens.border}`,
        display: "flex", alignItems: "center", gap: 12,
      }}>
        <div style={{
          width: 40, height: 40, borderRadius: 12,
          background: tokens.accentDim,
          border: `1px solid ${tokens.accentDimBorder}`,
          display: "flex",
          alignItems: "center", justifyContent: "center",
        }}>
          <Icon.Document size={22} />
        </div>
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
          display: "flex", alignItems: "center", gap: 8,
        }}>
          <Icon.TriageDot color={triageData?.color || "green"} size={16} />
          {t.label} — {handoffData.chief_complaint || 'Symptom assessment complete'}
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
            background: `linear-gradient(135deg, #0D9B7A, #0891B2)`,
            color: "#FFFFFF", fontSize: 14, fontWeight: 700, cursor: "pointer",
            display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
          }}
        >
          <Icon.Document size={18} primary="#FFFFFF" secondary="#FFFFFF" />
          Download PDF
        </button>
        <button
          onClick={onCopy}
          style={{
            flex: 1, padding: "12px 0", borderRadius: 10,
            border: "none", background: tokens.bgRecessed,
            color: tokens.textSecondary, fontSize: 14, fontWeight: 600, cursor: "pointer",
            display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
            boxShadow: "inset 0 1px 2px rgba(0,0,0,0.05)",
          }}
        >
          <Icon.Copy size={18} />
          Copy Summary
        </button>
      </div>

      <div style={{
        padding: "10px 24px 14px", textAlign: "center",
        fontSize: 11, color: tokens.textMuted, fontStyle: "italic",
        display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
      }}>
        <Icon.Medical size={14} primary={tokens.textMuted} secondary={tokens.textMuted} />
        AI-assisted triage — clinical judgment required
      </div>
    </div>
  )
}

// ============================================
// EMERGENCY CALL BUTTON
// ============================================

function EmergencyCallButton({ emergency, location, isUrgent, compact = false }) {
  const [expanded, setExpanded] = useState(false)

  if (!emergency) return null

  const handleCall = (number) => {
    // Clean the number for tel: link
    const cleanNumber = number.replace(/\s+/g, '').replace(/[()-]/g, '')
    window.location.href = `tel:${cleanNumber}`
  }

  if (compact) {
    return (
      <button
        onClick={() => handleCall(emergency.display)}
        style={{
          display: "flex", alignItems: "center", gap: 6,
          padding: "6px 12px", borderRadius: 8,
          background: isUrgent ? tokens.red : "transparent",
          border: isUrgent ? "none" : `1px solid ${tokens.border}`,
          color: isUrgent ? "#FFFFFF" : tokens.textSecondary,
          fontSize: 12, fontWeight: 600, cursor: "pointer",
          animation: isUrgent ? "breathe 2s ease-in-out infinite" : "none",
        }}
        title={`Call ${emergency.country} Emergency: ${emergency.display}`}
      >
        <Icon.Phone size={14} primary={isUrgent ? "#FFFFFF" : tokens.red} secondary={isUrgent ? "#FCA5A5" : "#FCA5A5"} />
        {emergency.display}
      </button>
    )
  }

  return (
    <div style={{
      margin: "12px 0", borderRadius: 16,
      background: isUrgent ? "#FEF2F2" : tokens.bgSurface,
      border: `2px solid ${isUrgent ? tokens.red : tokens.border}`,
      overflow: "hidden",
      animation: isUrgent ? "slideUp 0.4s ease-out" : "none",
      boxShadow: isUrgent ? "0 4px 20px rgba(220,38,38,0.15)" : tokens.shadow,
    }}>
      {/* Header */}
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          padding: "14px 18px",
          display: "flex", alignItems: "center", gap: 12,
          cursor: "pointer",
          background: isUrgent ? "rgba(220,38,38,0.08)" : "transparent",
        }}
      >
        <div style={{
          width: 40, height: 40, borderRadius: 12,
          background: isUrgent ? tokens.red : "rgba(220,38,38,0.1)",
          display: "flex", alignItems: "center", justifyContent: "center",
          animation: isUrgent ? "breathe 2s ease-in-out infinite" : "none",
        }}>
          <Icon.Phone size={22} primary={isUrgent ? "#FFFFFF" : tokens.red} secondary={isUrgent ? "#FCA5A5" : "#FCA5A5"} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: isUrgent ? tokens.red : tokens.textPrimary }}>
            Emergency Services
          </div>
          <div style={{ fontSize: 12, color: tokens.textMuted, display: "flex", alignItems: "center", gap: 4 }}>
            <Icon.Location size={12} primary={tokens.textMuted} secondary={tokens.textMuted} />
            {location?.city ? `${location.city}, ` : ''}{emergency.country}
          </div>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation()
            handleCall(emergency.ambulance || emergency.display)
          }}
          style={{
            padding: "10px 20px", borderRadius: 10, border: "none",
            background: tokens.red,
            color: "#FFFFFF", fontSize: 14, fontWeight: 700, cursor: "pointer",
            display: "flex", alignItems: "center", gap: 6,
            boxShadow: "0 2px 8px rgba(220,38,38,0.3)",
          }}
        >
          <Icon.Phone size={16} primary="#FFFFFF" secondary="#FCA5A5" />
          Call {emergency.ambulance || emergency.display}
        </button>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div style={{
          padding: "0 18px 16px",
          borderTop: `1px solid ${tokens.border}`,
          marginTop: 0,
          paddingTop: 14,
        }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginBottom: 12 }}>
            {[
              { label: "Ambulance", number: emergency.ambulance, icon: "ambulance" },
              { label: "Police", number: emergency.police, icon: "police" },
              { label: "Fire", number: emergency.fire, icon: "fire" },
            ].map((service) => (
              <button
                key={service.label}
                onClick={() => handleCall(service.number)}
                style={{
                  padding: "10px 8px", borderRadius: 10,
                  border: `1px solid ${tokens.border}`,
                  background: tokens.bgRecessed,
                  cursor: "pointer",
                  display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
                }}
              >
                <span style={{ fontSize: 11, color: tokens.textMuted, textTransform: "uppercase", fontWeight: 600 }}>
                  {service.label}
                </span>
                <span style={{ fontSize: 16, fontWeight: 700, color: tokens.textPrimary }}>
                  {service.number}
                </span>
              </button>
            ))}
          </div>

          {/* Specialized numbers */}
          {emergency.specialized && emergency.specialized.length > 0 && (
            <>
              <div style={{ fontSize: 11, color: tokens.textMuted, fontWeight: 600, textTransform: "uppercase", marginBottom: 8 }}>
                Specialized Services
              </div>
              {emergency.specialized.map((service, i) => (
                <button
                  key={i}
                  onClick={() => handleCall(service.number)}
                  style={{
                    width: "100%", padding: "10px 14px", marginBottom: 6,
                    borderRadius: 8, border: `1px solid ${tokens.border}`,
                    background: tokens.bgSurface, cursor: "pointer",
                    display: "flex", justifyContent: "space-between", alignItems: "center",
                  }}
                >
                  <span style={{ fontSize: 13, color: tokens.textSecondary }}>{service.name}</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: tokens.accent }}>{service.number}</span>
                </button>
              ))}
            </>
          )}

          <div style={{
            marginTop: 12, padding: "8px 12px", borderRadius: 8,
            background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.3)",
            fontSize: 11, color: tokens.amber, textAlign: "center",
          }}>
            In life-threatening emergencies, call immediately. Daktari is not a substitute for emergency services.
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================
// CHAT BUBBLE
// ============================================

// Markdown component styles
const markdownComponents = {
  p: ({ children }) => <p style={{ margin: "0 0 8px 0" }}>{children}</p>,
  strong: ({ children }) => <strong style={{ fontWeight: 600, color: tokens.textPrimary }}>{children}</strong>,
  em: ({ children }) => <em style={{ fontStyle: "italic" }}>{children}</em>,
  ul: ({ children }) => <ul style={{ margin: "8px 0", paddingLeft: 20 }}>{children}</ul>,
  ol: ({ children }) => <ol style={{ margin: "8px 0", paddingLeft: 20 }}>{children}</ol>,
  li: ({ children }) => <li style={{ marginBottom: 4 }}>{children}</li>,
  h1: ({ children }) => <h1 style={{ fontSize: 18, fontWeight: 700, margin: "12px 0 8px" }}>{children}</h1>,
  h2: ({ children }) => <h2 style={{ fontSize: 16, fontWeight: 600, margin: "10px 0 6px" }}>{children}</h2>,
  h3: ({ children }) => <h3 style={{ fontSize: 15, fontWeight: 600, margin: "8px 0 4px" }}>{children}</h3>,
  code: ({ children }) => (
    <code style={{
      background: "rgba(45,212,168,0.15)",
      padding: "2px 6px",
      borderRadius: 4,
      fontSize: 13,
      fontFamily: "monospace",
      color: tokens.accent,
    }}>{children}</code>
  ),
  blockquote: ({ children }) => (
    <blockquote style={{
      borderLeft: `3px solid ${tokens.accent}`,
      margin: "8px 0",
      paddingLeft: 12,
      color: tokens.textSecondary,
      fontStyle: "italic",
    }}>{children}</blockquote>
  ),
  hr: () => <hr style={{ border: "none", borderTop: `1px solid ${tokens.border}`, margin: "12px 0" }} />,
}

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
          background: `linear-gradient(135deg, #0D9B7A, #0891B2)`,
          display: "flex", alignItems: "center", justifyContent: "center",
          marginTop: 4,
        }}>
          <Icon.Heart size={18} primary="#FFFFFF" secondary="#FFFFFF" />
        </div>
      )}
      <div style={{
        maxWidth: "75%", padding: "14px 18px", borderRadius: 16,
        borderTopLeftRadius: isUser ? 16 : 4,
        borderTopRightRadius: isUser ? 4 : 16,
        background: isError ? "#FEF2F2" : isUser ? tokens.userBubbleBg : tokens.bgSurface,
        border: isError ? `1px solid #FECACA` : "none",
        color: isError ? tokens.red : isUser ? tokens.userBubbleText : tokens.textSecondary,
        fontSize: 14, lineHeight: 1.65,
        boxShadow: tokens.shadow,
      }}>
        <div className="markdown-content">
          {isUser ? (
            <p style={{ margin: 0 }}>{message.content}</p>
          ) : (
            <ReactMarkdown components={markdownComponents}>
              {message.content}
            </ReactMarkdown>
          )}
        </div>
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          marginTop: 8, gap: 12,
        }}>
          {!isUser && !isError && (
            <button
              onClick={() => onPlayTTS(message.id, message.content)}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                background: "none", border: `1px solid ${isPlaying ? tokens.accent : tokens.border}`,
                borderRadius: 8, padding: "5px 12px", cursor: "pointer",
                color: isPlaying ? tokens.accent : tokens.textMuted,
                fontSize: 12, transition: "all 0.2s",
              }}
            >
              <Icon.Speaker size={16} playing={isPlaying} />
              {isPlaying ? 'Playing...' : 'Listen'}
            </button>
          )}
          <span style={{ fontSize: 11, color: tokens.textMuted, marginLeft: "auto", display: "flex", alignItems: "center", gap: 4 }}>
            {isVoice && <Icon.Mic size={12} primary={tokens.textMuted} secondary={tokens.textMuted} />}
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
        background: `linear-gradient(135deg, #0D9B7A, #0891B2)`,
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        <Icon.Heart size={18} primary="#FFFFFF" secondary="#FFFFFF" />
      </div>
      <div style={{
        padding: "14px 18px", borderRadius: 16, borderTopLeftRadius: 4,
        background: tokens.bgSurface,
        display: "flex", alignItems: "center", gap: 8,
        boxShadow: tokens.shadow,
      }}>
        <div style={{ display: "flex", gap: 4 }}>
          {[0, 1, 2].map(i => (
            <span key={i} style={{
              width: 8, height: 8, borderRadius: "50%",
              background: tokens.accentLight,
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
        background: `linear-gradient(135deg, #0D9B7A, #0891B2)`,
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        <Icon.Heart size={18} primary="#FFFFFF" secondary="#FFFFFF" />
      </div>
      <div style={{
        maxWidth: "75%", padding: "14px 18px", borderRadius: 16, borderTopLeftRadius: 4,
        background: tokens.bgSurface,
        color: tokens.textSecondary, fontSize: 14, lineHeight: 1.65,
        boxShadow: tokens.shadow,
      }}>
        <div className="markdown-content">
          <ReactMarkdown components={markdownComponents}>
            {content}
          </ReactMarkdown>
          <span style={{
            display: "inline-block", width: 2, height: 16,
            marginLeft: 2, background: tokens.accentLight,
            animation: "pulse 1s ease-in-out infinite",
          }} />
        </div>
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
        gradient.addColorStop(0, '#0D9B7A')
        gradient.addColorStop(1, '#0891B2')

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
            background: `linear-gradient(to top, #0D9B7A, #0891B2)`,
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
  const [emergencyData, setEmergencyData] = useState(null)
  const [userLocation, setUserLocation] = useState(null)
  const [locationLoading, setLocationLoading] = useState(false)

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

  // Auto-scroll to bottom when new messages arrive or streaming content updates
  useEffect(() => {
    const scrollToBottom = () => {
      if (messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' })
      }
    }
    // Use requestAnimationFrame for smoother scrolling
    requestAnimationFrame(scrollToBottom)
  }, [messages, streamingResponse, toolCalls, triageData, handoffData, isTranscribing])

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

  // Detect location and emergency numbers on mount
  useEffect(() => {
    const detectLocation = async () => {
      setLocationLoading(true)
      try {
        const result = await detectEmergencyNumbers()
        if (result.success) {
          setEmergencyData(result.emergency)
          setUserLocation(result.location)
        } else {
          // Use default international emergency number
          setEmergencyData(DEFAULT_EMERGENCY)
        }
      } catch (error) {
        console.error('Location detection failed:', error)
        setEmergencyData(DEFAULT_EMERGENCY)
      } finally {
        setLocationLoading(false)
      }
    }

    detectLocation()
  }, [])

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

              switch (data.type) {
                case 'text':
                  fullResponse += data.content
                  setStreamingResponse(fullResponse)
                  break

                case 'done':
                  setMessages(prev => [...prev, {
                    id: Date.now(),
                    role: 'assistant',
                    content: data.full_response
                  }])
                  break

                case 'tool_start':
                  console.log(`🔧 Tool started: ${data.tool}`)
                  setToolCalls(prev => [...new Set([...prev, data.tool])])
                  break

                case 'tool_result':
                  console.log(`✅ Tool result: ${data.tool}`, data.result)
                  // Handle specific tool results
                  if (data.tool === 'suggest_differentials' && data.result?.differentials) {
                    setHandoffData(prev => ({
                      ...prev,
                      differentials: data.result.differentials
                    }))
                  }
                  break

                case 'triage':
                  console.log('🚨 Triage data received:', data.data)
                  setTriageData(data.data)
                  break

                case 'handoff':
                  console.log('📋 Handoff data received:', data.data)
                  setHandoffData(prev => ({ ...prev, ...data.data }))
                  break

                case 'tool_error':
                  console.error(`❌ Tool error: ${data.tool}`, data.error)
                  break

                case 'error':
                  console.error('Stream error:', data.message)
                  setMessages(prev => [...prev, {
                    id: Date.now(),
                    role: 'assistant',
                    content: `Error: ${data.message}`,
                    error: true
                  }])
                  break
              }
            } catch (e) {
              console.error('Parse error:', e)
            }
          }
        }
      }
    } catch (error) {
      console.error('Fetch error:', error)
      setMessages(prev => [...prev, {
        id: Date.now(),
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
        error: true
      }])
    } finally {
      setIsLoading(false)
      setIsStreaming(false)
      setStreamingResponse('')
    }
  }

  // Start recording
  const startRecording = async () => {
    try {
      // Stop any currently playing audio before recording
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause()
        audioPlayerRef.current.currentTime = 0
        setPlayingId(null)
      }

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
    // Include location and emergency data with patient
    setPatient({
      ...data,
      location: userLocation,
      emergencyNumber: emergencyData?.display || "112"
    })
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
      <PatientModal
        isOpen={showPatientModal}
        onSubmit={handlePatientSubmit}
        emergencyData={emergencyData}
        userLocation={userLocation}
        locationLoading={locationLoading}
      />

      {/* Header */}
      {!showPatientModal && (
        <div style={{
          padding: "12px 20px", display: "flex", alignItems: "center", gap: 12,
          background: tokens.bgSurface,
          flexShrink: 0,
          boxShadow: tokens.shadow,
        }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: `linear-gradient(135deg, #0D9B7A, #0891B2)`,
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: tokens.shadow,
          }}>
            <Icon.Heart size={20} primary="#FFFFFF" secondary="#FFFFFF" />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: tokens.textPrimary }}>Daktari</div>
            {patient && (
              <div style={{ fontSize: 12, color: tokens.textMuted }}>
                {patient.name} · {patient.age}y · {patient.gender}
              </div>
            )}
          </div>
          {/* Emergency button in header */}
          {emergencyData && (
            <EmergencyCallButton
              emergency={emergencyData}
              location={userLocation}
              isUrgent={triageData?.color === 'red' || triageData?.color === 'orange'}
              compact={true}
            />
          )}
          {handoffData && (
            <button
              onClick={downloadHandoff}
              style={{
                padding: "8px 16px", borderRadius: 10, border: "none",
                background: `linear-gradient(135deg, #0D9B7A, #0891B2)`,
                color: "#FFFFFF", fontSize: 13, fontWeight: 600, cursor: "pointer",
                marginRight: 8, display: "flex", alignItems: "center", gap: 6,
              }}
            >
              <Icon.Document size={16} primary="#FFFFFF" secondary="#FFFFFF" />
              PDF
            </button>
          )}
          <button
            onClick={startNewChat}
            style={{
              padding: "8px 16px", borderRadius: 10, border: "none",
              background: tokens.bgRecessed, color: tokens.textSecondary, fontSize: 13,
              fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", gap: 6,
            }}
          >
            <Icon.Plus size={16} />
            New
          </button>
        </div>
      )}

      {/* Intake Stepper */}
      {showChat && !showPatientModal && (
        <IntakeStepper currentStep={currentStep} />
      )}

      {/* Triage Banner */}
      {triageData && <TriageBanner triageData={triageData} />}

      {/* Prominent Emergency Call for RED/ORANGE triage */}
      {triageData && (triageData.color === 'red' || triageData.color === 'orange') && emergencyData && (
        <div style={{ padding: "0 20px", marginTop: 8 }}>
          <EmergencyCallButton
            emergency={emergencyData}
            location={userLocation}
            isUrgent={true}
          />
        </div>
      )}

      {/* Main Content */}
      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column" }}>
        {showWelcome && !showPatientModal ? (
          <WelcomeScreen
            patient={patient}
            onStartRecording={startRecording}
            onSendMessage={sendMessage}
            emergencyData={emergencyData}
            userLocation={userLocation}
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
                  display: "flex", alignItems: "center", gap: 8,
                }}>
                  <Icon.TriageDot color={triageData.color} size={16} />
                  <span style={{ fontWeight: 700, color: triageColors[triageData.color]?.text }}>
                    {triageColors[triageData.color]?.label} — Evaluation {triageColors[triageData.color]?.time.toLowerCase()}
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
          flexShrink: 0,
          boxShadow: "0 -2px 10px rgba(0,0,0,0.04)",
        }}>
          {/* Waveform */}
          {isRecording && (
            analyser ? <AudioWaveform analyser={analyser} isActive={isRecording} /> : <StaticWaveform />
          )}

          {/* Input row */}
          <div style={{ display: "flex", gap: 10, alignItems: "flex-end" }}>
            <button
              onClick={isRecording ? stopRecording : startRecording}
              disabled={(isLoading || isTranscribing) && !isRecording}
              style={{
                width: 44, height: 44, borderRadius: "50%",
                border: "none",
                background: isRecording ? tokens.red : tokens.bgRecessed,
                cursor: "pointer", flexShrink: 0,
                display: "flex", alignItems: "center", justifyContent: "center",
                animation: isRecording ? "breathe 2s ease-in-out infinite" : "none",
                opacity: (isLoading || isTranscribing) && !isRecording ? 0.5 : 1,
                marginBottom: 2,
                boxShadow: isRecording ? "none" : "inset 0 1px 2px rgba(0,0,0,0.05)",
              }}
            >
              {isRecording
                ? <Icon.Stop size={20} primary="#fff" secondary="#FCA5A5" />
                : <Icon.Mic size={22} primary={tokens.textMuted} secondary={tokens.accent} />
              }
            </button>

            <div style={{ flex: 1, position: "relative" }}>
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    if (e.metaKey || e.ctrlKey) {
                      // Cmd+Enter or Ctrl+Enter: insert newline
                      e.preventDefault()
                      const target = e.target
                      const start = target.selectionStart
                      const end = target.selectionEnd
                      const newValue = input.substring(0, start) + '\n' + input.substring(end)
                      setInput(newValue)
                      // Set cursor position after the newline
                      requestAnimationFrame(() => {
                        target.selectionStart = target.selectionEnd = start + 1
                        // Trigger resize
                        target.style.height = 'auto'
                        target.style.height = Math.min(target.scrollHeight, 120) + 'px'
                      })
                    } else {
                      // Just Enter: send message
                      e.preventDefault()
                      sendMessage(input)
                    }
                  }
                }}
                placeholder={isRecording ? "Listening..." : isTranscribing ? "Transcribing..." : "Describe your symptoms..."}
                disabled={isLoading || isRecording || isTranscribing}
                rows={1}
                style={{
                  width: "100%",
                  minHeight: 44,
                  maxHeight: 120,
                  padding: "12px 20px",
                  borderRadius: 22,
                  border: "none",
                  background: tokens.bgRecessed,
                  color: tokens.textPrimary,
                  fontSize: 14,
                  outline: "none",
                  resize: "none",
                  fontFamily: "inherit",
                  lineHeight: 1.4,
                  opacity: (isLoading || isRecording || isTranscribing) ? 0.5 : 1,
                  overflow: "hidden",
                  boxShadow: "inset 0 1px 3px rgba(0,0,0,0.06)",
                }}
                onInput={e => {
                  // Auto-resize textarea
                  e.target.style.height = 'auto'
                  e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
                }}
              />
              {/* Markdown hint */}
              {input.length > 0 && (
                <div style={{
                  position: "absolute", right: 12, bottom: -18,
                  fontSize: 10, color: tokens.textMuted,
                }}>
                  <span style={{ opacity: 0.6 }}>Markdown supported</span>
                  <span style={{ margin: "0 4px", opacity: 0.3 }}>·</span>
                  <span style={{ opacity: 0.4 }}>⌘↵ new line</span>
                </div>
              )}
            </div>

            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || isLoading}
              style={{
                width: 44, height: 44, borderRadius: "50%", border: "none",
                background: input.trim() && !isLoading
                  ? `linear-gradient(135deg, #0D9B7A, #0891B2)`
                  : tokens.bgRecessed,
                cursor: input.trim() && !isLoading ? "pointer" : "not-allowed",
                flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center",
                marginBottom: 2,
                boxShadow: input.trim() && !isLoading ? tokens.shadow : "inset 0 1px 2px rgba(0,0,0,0.05)",
              }}
            >
              <Icon.Send
                size={20}
                primary={input.trim() && !isLoading ? "#FFFFFF" : tokens.textPlaceholder}
                secondary={input.trim() && !isLoading ? "#FFFFFF" : tokens.textPlaceholder}
              />
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
            textAlign: "center", padding: input.length > 0 ? "16px 0 4px" : "8px 0 4px",
            fontSize: 11, color: tokens.textMuted,
            display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
          }}>
            <Icon.Medical size={12} primary={tokens.textMuted} secondary={tokens.textMuted} />
            AI-assisted triage — always consult a healthcare provider
          </div>
        </div>
      )}
    </div>
  )
}

export default App

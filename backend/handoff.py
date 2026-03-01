"""
Daktari Clinical Handoff PDF Generator — Redesigned
Clean, professional SBAR medical handoff document using reportlab.
Matches the Clinical Day theme with teal accent.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from datetime import datetime
import os
import logging

logger = logging.getLogger("daktari")

# Ensure output directory exists
OUTPUT_DIR = "handoffs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# DESIGN TOKENS (Clinical Day Theme)
# ============================================================
COLORS = {
    "bg":           HexColor("#FFFFFF"),
    "surface":      HexColor("#F8FAFB"),
    "border":       HexColor("#E5E7EB"),
    "border_light": HexColor("#F1F5F9"),
    "text":         HexColor("#111827"),
    "text_sec":     HexColor("#4B5563"),
    "text_muted":   HexColor("#9CA3AF"),
    "accent":       HexColor("#0D9B7A"),
    "accent_light": HexColor("#ECFDF5"),
    # Triage colors
    "red":          HexColor("#DC2626"),
    "red_bg":       HexColor("#FEF2F2"),
    "red_border":   HexColor("#FECACA"),
    "orange":       HexColor("#EA580C"),
    "orange_bg":    HexColor("#FFF7ED"),
    "orange_border":HexColor("#FED7AA"),
    "yellow":       HexColor("#A16207"),
    "yellow_bg":    HexColor("#FEFCE8"),
    "yellow_border":HexColor("#FDE68A"),
    "green":        HexColor("#15803D"),
    "green_bg":     HexColor("#F0FDF4"),
    "green_border": HexColor("#BBF7D0"),
}

TRIAGE = {
    "red":    {"color": COLORS["red"],    "bg": COLORS["red_bg"],    "border": COLORS["red_border"],    "label": "EMERGENCY",    "time": "Immediate"},
    "orange": {"color": COLORS["orange"], "bg": COLORS["orange_bg"], "border": COLORS["orange_border"], "label": "VERY URGENT", "time": "Within 10 minutes"},
    "yellow": {"color": COLORS["yellow"], "bg": COLORS["yellow_bg"], "border": COLORS["yellow_border"], "label": "URGENT",      "time": "Within 60 minutes"},
    "green":  {"color": COLORS["green"],  "bg": COLORS["green_bg"],  "border": COLORS["green_border"],  "label": "ROUTINE",     "time": "Within 4 hours"},
}


# ============================================================
# STYLES
# ============================================================
def get_styles():
    return {
        "title": ParagraphStyle(
            "title", fontName="Helvetica-Bold", fontSize=18,
            textColor=COLORS["text"], spaceAfter=2, leading=22
        ),
        "subtitle": ParagraphStyle(
            "subtitle", fontName="Helvetica", fontSize=9,
            textColor=COLORS["text_muted"], spaceAfter=0
        ),
        "section_header": ParagraphStyle(
            "section_header", fontName="Helvetica-Bold", fontSize=11,
            textColor=COLORS["accent"], spaceBefore=14, spaceAfter=6,
            leading=14
        ),
        "section_label": ParagraphStyle(
            "section_label", fontName="Helvetica", fontSize=7,
            textColor=COLORS["text_muted"], spaceBefore=0, spaceAfter=2,
            leading=9
        ),
        "body": ParagraphStyle(
            "body", fontName="Helvetica", fontSize=9.5,
            textColor=COLORS["text"], leading=14, spaceAfter=3
        ),
        "body_bold": ParagraphStyle(
            "body_bold", fontName="Helvetica-Bold", fontSize=9.5,
            textColor=COLORS["text"], leading=14, spaceAfter=3
        ),
        "body_sec": ParagraphStyle(
            "body_sec", fontName="Helvetica", fontSize=9,
            textColor=COLORS["text_sec"], leading=13, spaceAfter=2
        ),
        "small": ParagraphStyle(
            "small", fontName="Helvetica", fontSize=7.5,
            textColor=COLORS["text_muted"], leading=10
        ),
        "small_italic": ParagraphStyle(
            "small_italic", fontName="Helvetica-Oblique", fontSize=7.5,
            textColor=COLORS["text_muted"], leading=10
        ),
        "checklist": ParagraphStyle(
            "checklist", fontName="Helvetica", fontSize=9.5,
            textColor=COLORS["text"], leading=16, leftIndent=8
        ),
        "icd_code": ParagraphStyle(
            "icd_code", fontName="Courier", fontSize=8.5,
            textColor=COLORS["accent"], leading=12
        ),
        "triage_label": ParagraphStyle(
            "triage_label", fontName="Helvetica-Bold", fontSize=11,
            leading=14, spaceAfter=0
        ),
        "triage_detail": ParagraphStyle(
            "triage_detail", fontName="Helvetica", fontSize=9,
            leading=12, spaceAfter=0
        ),
        "diff_name": ParagraphStyle(
            "diff_name", fontName="Helvetica", fontSize=9.5,
            textColor=COLORS["text"], leading=13
        ),
        "diff_reason": ParagraphStyle(
            "diff_reason", fontName="Helvetica", fontSize=8,
            textColor=COLORS["text_sec"], leading=11
        ),
        "footer": ParagraphStyle(
            "footer", fontName="Helvetica", fontSize=6.5,
            textColor=COLORS["text_muted"], leading=9, alignment=TA_CENTER
        ),
    }


# ============================================================
# HELPER FUNCTIONS
# ============================================================
def section_header(styles, letter, title):
    """Creates a section header like: [S] — SITUATION"""
    return Paragraph(
        f'<font color="{COLORS["accent"].hexval()}" name="Helvetica-Bold" size="12">{letter}</font>'
        f'<font color="{COLORS["text_muted"].hexval()}" size="9">  —  </font>'
        f'<font color="{COLORS["text"].hexval()}" name="Helvetica-Bold" size="11">{title}</font>',
        styles["section_header"]
    )


def kv_row(styles, label, value, W):
    """Creates a key-value row"""
    t = Table(
        [[
            Paragraph(f'<font color="{COLORS["text_muted"].hexval()}" size="8">{label}</font>', styles["small"]),
            Paragraph(str(value), styles["body"]),
        ]],
        colWidths=[W*0.25, W*0.75]
    )
    t.setStyle(TableStyle([
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
        ("TOPPADDING",   (0,0), (-1,-1), 3),
        ("BOTTOMPADDING",(0,0), (-1,-1), 3),
        ("VALIGN",       (0,0), (-1,-1), "TOP"),
    ]))
    return t


# ============================================================
# MAIN PDF GENERATOR
# ============================================================
def generate_handoff_pdf(data: dict) -> str:
    """
    Generate a clinical handoff PDF from the provided data.

    Args:
        data: Dictionary containing handoff information:
            - chief_complaint: str
            - symptoms: list[str] or list[dict]
            - duration: str
            - severity: int/str
            - medical_history: str
            - triggers: str
            - patient: dict {name, age, gender, contact, lang}
            - urgency_assessment: dict {color, label, reasoning, time_target}
            - differentials: list[dict] {condition, icd10_code, confidence, reasoning, urgent_workup}
            - recommended_actions: list[str]
            - icd_codes: list[str]
            - symptom_timeline: str

    Returns:
        Path to the generated PDF file
    """
    logger.info("📄 Generating clinical handoff PDF...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    patient = data.get('patient', {})
    patient_name = patient.get('name', 'patient').replace(' ', '_') if patient else 'patient'
    filename = os.path.join(OUTPUT_DIR, f"handoff_{patient_name}_{timestamp}.pdf")

    styles = get_styles()
    story = []
    W = A4[0] - 30*mm  # usable width

    # Get triage info
    urgency_assessment = data.get('urgency_assessment', {})
    triage_color = urgency_assessment.get('color', 'green').lower()
    triage = TRIAGE.get(triage_color, TRIAGE['green'])

    # Prepare data with defaults
    chief_complaint = data.get('chief_complaint', 'Not specified')
    duration = data.get('duration', 'Not reported')
    severity = data.get('severity', 'N/A')
    if isinstance(severity, str) and severity.endswith('/10'):
        severity = severity.replace('/10', '')

    # ── TRIAGE BANNER ──────────────────────────────────────────
    cc_short = chief_complaint[:77] + "..." if len(chief_complaint) > 80 else chief_complaint

    banner_table = Table(
        [
            # Row 1: Triage label + time target
            [
                Paragraph(f'<font color="{triage["color"].hexval()}">■ {triage["label"]}</font>', styles["triage_label"]),
                Paragraph(f'<font color="{triage["color"].hexval()}">{triage["time"]}</font>',
                          ParagraphStyle("rt", parent=styles["triage_detail"], alignment=TA_RIGHT, textColor=triage["color"])),
            ],
            # Row 2: Chief complaint summary
            [
                Paragraph(f'<font color="{COLORS["text_sec"].hexval()}">{cc_short}</font>', styles["triage_detail"]),
                None,
            ],
            # Row 3: Severity + Duration
            [
                Paragraph(f'<font color="{COLORS["text_muted"].hexval()}" size="8">Severity: {severity}/10  |  Duration: {duration}</font>', styles["small"]),
                None,
            ],
        ],
        colWidths=[W*0.7, W*0.3],
    )
    banner_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), triage["bg"]),
        ("BOX",         (0,0), (-1,-1), 1, triage["border"]),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("RIGHTPADDING",(0,0), (-1,-1), 12),
        ("TOPPADDING",  (0,0), (-1,0), 10),
        ("TOPPADDING",  (0,1), (-1,1), 2),
        ("TOPPADDING",  (0,2), (-1,2), 2),
        ("BOTTOMPADDING",(0,-1),(-1,-1), 10),
        ("BOTTOMPADDING",(0,0), (-1,1), 2),
        ("SPAN",        (0,1), (1,1)),
        ("SPAN",        (0,2), (1,2)),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 12))

    # ── HEADER ─────────────────────────────────────────────────
    generated_at = datetime.now()
    header_table = Table(
        [[
            Paragraph("DAKTARI", ParagraphStyle("logo", fontName="Helvetica-Bold", fontSize=22, textColor=COLORS["accent"])),
            Paragraph(
                f'<font color="{COLORS["text_muted"].hexval()}">Clinical Handoff Note<br/>'
                f'{generated_at.strftime("%B %d, %Y at %H:%M")}</font>',
                ParagraphStyle("hdr_r", parent=styles["small"], alignment=TA_RIGHT, leading=10)
            ),
        ]],
        colWidths=[W*0.5, W*0.5],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "BOTTOM"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(header_table)

    # Thin accent line
    story.append(HRFlowable(width="100%", thickness=2, color=COLORS["accent"], spaceAfter=10))

    # ── PATIENT INFO BAR ───────────────────────────────────────
    p_name = patient.get('name', 'Unknown')
    p_age = patient.get('age', 'Unknown')
    p_sex = patient.get('gender', patient.get('sex', 'Unknown'))
    if isinstance(p_sex, str):
        p_sex = p_sex.capitalize()
    p_lang = patient.get('lang', patient.get('language', 'Not specified'))
    p_contact = patient.get('contact', patient.get('phone', '—')) or '—'
    p_emergency = patient.get('emergencyNumber', '112')
    p_location = patient.get('location', {})
    p_location_str = ''
    if p_location:
        city = p_location.get('city', '')
        country = p_location.get('country', '')
        if city and country:
            p_location_str = f"{city}, {country}"
        elif country:
            p_location_str = country

    # Map language codes to names
    lang_map = {'sw': 'Kiswahili', 'rw': 'Kinyarwanda', 'en': 'English', 'fr': 'Français'}
    if p_lang in lang_map:
        p_lang = lang_map[p_lang]

    patient_cells = [
        [
            Paragraph(f'<b>{p_name}</b>', ParagraphStyle("pn", fontName="Helvetica-Bold", fontSize=13, textColor=COLORS["text"])),
            Paragraph(f'{p_age} years', styles["body"]),
            Paragraph(f'{p_sex}', styles["body"]),
            Paragraph(f'Language: {p_lang}', styles["body_sec"]),
            Paragraph(f'<font color="#DC2626"><b>Emergency: {p_emergency}</b></font>', styles["body_sec"]) if p_emergency else Paragraph(f'{p_contact}', styles["body_sec"]),
        ]
    ]
    patient_table = Table(patient_cells, colWidths=[W*0.25, W*0.15, W*0.15, W*0.22, W*0.23])
    patient_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), COLORS["surface"]),
        ("BOX",          (0,0), (-1,-1), 0.5, COLORS["border"]),
        ("LEFTPADDING",  (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING",   (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 14))

    # ── S: SITUATION ───────────────────────────────────────────
    story.append(section_header(styles, "S", "SITUATION"))

    sit_data = [
        ["Chief Complaint", chief_complaint],
        ["Duration", duration],
        ["Severity", f'{severity}/10'],
        ["Triage Level", f'{triage["label"]} — {triage["time"]}'],
    ]
    for label, value in sit_data:
        story.append(kv_row(styles, label, value, W))

    story.append(Spacer(1, 6))

    # ── B: BACKGROUND ──────────────────────────────────────────
    story.append(section_header(styles, "B", "BACKGROUND"))

    # Symptoms table with ICD-10
    story.append(Paragraph("PRESENTING SYMPTOMS", styles["section_label"]))

    symptoms = data.get('symptoms', [])
    icd_codes = data.get('icd_codes', [])

    sym_header = [
        Paragraph('<b>Symptom</b>', styles["small"]),
        Paragraph('<b>ICD-10</b>', styles["small"]),
    ]
    sym_rows = [sym_header]

    for i, s in enumerate(symptoms):
        if isinstance(s, dict):
            sym_name = s.get('name', s.get('symptom', str(s)))
            sym_code = s.get('icd10', s.get('icd10_code', ''))
        else:
            sym_name = str(s)
            sym_code = icd_codes[i] if i < len(icd_codes) else ''

        sym_rows.append([
            Paragraph(sym_name, styles["body"]),
            Paragraph(f'<font name="Courier" color="{COLORS["accent"].hexval()}">{sym_code}</font>', styles["body"]),
        ])

    if len(sym_rows) > 1:  # Has symptoms beyond header
        sym_table = Table(sym_rows, colWidths=[W*0.7, W*0.3])
        sym_table.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), COLORS["surface"]),
            ("LINEBELOW",     (0,0), (-1,0), 0.5, COLORS["border"]),
            ("LINEBELOW",     (0,1), (-1,-1), 0.25, COLORS["border_light"]),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
            ("RIGHTPADDING",  (0,0), (-1,-1), 8),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("BOX",           (0,0), (-1,-1), 0.5, COLORS["border"]),
        ]))
        story.append(sym_table)
        story.append(Spacer(1, 8))

    # Medical history & triggers
    story.append(kv_row(styles, "Medical History", data.get('medical_history', 'None reported'), W))
    if data.get('triggers'):
        story.append(kv_row(styles, "Aggravating Factors", data['triggers'], W))

    story.append(Spacer(1, 4))

    # ── SYMPTOM TIMELINE ───────────────────────────────────────
    timeline = data.get('symptom_timeline') or data.get('timeline')
    if timeline:
        story.append(Paragraph("SYMPTOM PROGRESSION", styles["section_label"]))

        if isinstance(timeline, str):
            # Simple text timeline
            timeline_table = Table([[Paragraph(timeline, styles["body"])]], colWidths=[W])
            timeline_table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,-1), COLORS["surface"]),
                ("BOX", (0,0), (-1,-1), 0.5, COLORS["border"]),
                ("LEFTPADDING", (0,0), (-1,-1), 10),
                ("RIGHTPADDING", (0,0), (-1,-1), 10),
                ("TOPPADDING", (0,0), (-1,-1), 8),
                ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ]))
            story.append(timeline_table)
        elif isinstance(timeline, list):
            # Structured timeline
            tl_rows = []
            for t in timeline:
                day = t.get('day', t.get('label', ''))
                events = t.get('events', t.get('symptoms', []))
                if isinstance(events, list):
                    events_str = " · ".join(events)
                else:
                    events_str = str(events)
                tl_rows.append([
                    Paragraph(f'<b>{day}</b>', styles["body_sec"]),
                    Paragraph(events_str, styles["body"]),
                ])

            if tl_rows:
                tl_table = Table(tl_rows, colWidths=[W*0.2, W*0.8])
                tl_table.setStyle(TableStyle([
                    ("LEFTPADDING",   (0,0), (-1,-1), 8),
                    ("RIGHTPADDING",  (0,0), (-1,-1), 8),
                    ("TOPPADDING",    (0,0), (-1,-1), 4),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                    ("LINEBELOW",     (0,0), (-1,-2), 0.25, COLORS["border_light"]),
                    ("VALIGN",        (0,0), (-1,-1), "TOP"),
                    ("BACKGROUND",    (0,0), (-1,-1), COLORS["surface"]),
                    ("BOX",           (0,0), (-1,-1), 0.5, COLORS["border"]),
                ]))
                story.append(tl_table)

        story.append(Spacer(1, 6))

    # ── A: ASSESSMENT ──────────────────────────────────────────
    story.append(section_header(styles, "A", "ASSESSMENT"))

    # Triage reasoning
    triage_reasoning = urgency_assessment.get('reasoning', '')
    if triage_reasoning:
        story.append(Paragraph("TRIAGE REASONING", styles["section_label"]))
        story.append(Paragraph(triage_reasoning, styles["body"]))
        story.append(Spacer(1, 8))

    # Red flags
    red_flags = data.get('red_flags', [])
    if red_flags:
        flags_text = f'<font color="{COLORS["red"].hexval()}"><b>RED FLAGS IDENTIFIED:</b></font><br/>'
        for flag in red_flags:
            flags_text += f'<font color="{COLORS["red"].hexval()}">• {flag}</font><br/>'
        story.append(Paragraph(flags_text, styles["body"]))
        story.append(Spacer(1, 8))

    # Differentials
    differentials = data.get('differentials', [])
    if differentials:
        story.append(Paragraph("DIFFERENTIAL DIAGNOSES (for clinical consideration)", styles["section_label"]))

        conf_colors = {
            "HIGH": COLORS["accent"],
            "MED":  HexColor("#D97706"),
            "MEDIUM": HexColor("#D97706"),
            "LOW":  HexColor("#DC2626"),
        }

        diff_header = [
            Paragraph('<b>#</b>', styles["small"]),
            Paragraph('<b>Condition</b>', styles["small"]),
            Paragraph('<b>ICD-10</b>', styles["small"]),
            Paragraph('<b>Confidence</b>', styles["small"]),
        ]
        diff_rows = [diff_header]

        for i, d in enumerate(differentials[:5], 1):
            condition = d.get('condition', d.get('name', 'Unknown'))
            icd10 = d.get('icd10_code', d.get('icd10', '-'))
            confidence = d.get('confidence', 'N/A').upper()
            reasoning = d.get('reasoning', '')
            urgent = d.get('urgent_workup', d.get('urgent', False))

            prefix = "⚠ " if urgent else ""
            c = conf_colors.get(confidence, COLORS["text_muted"])

            condition_text = f'{prefix}<b>{condition}</b>'
            if reasoning:
                condition_text += f'<br/><font size="7.5" color="{COLORS["text_sec"].hexval()}">{reasoning[:80]}{"..." if len(reasoning) > 80 else ""}</font>'

            diff_rows.append([
                Paragraph(str(i), styles["body_sec"]),
                Paragraph(condition_text, styles["body"]),
                Paragraph(f'<font name="Courier">{icd10}</font>', styles["icd_code"]),
                Paragraph(f'<font color="{c.hexval()}"><b>{confidence}</b></font>', styles["body"]),
            ])

        diff_table = Table(diff_rows, colWidths=[W*0.06, W*0.54, W*0.18, W*0.22])
        diff_table.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), COLORS["surface"]),
            ("LINEBELOW",     (0,0), (-1,0), 0.5, COLORS["border"]),
            ("LINEBELOW",     (0,1), (-1,-1), 0.25, COLORS["border_light"]),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
            ("RIGHTPADDING",  (0,0), (-1,-1), 8),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("BOX",           (0,0), (-1,-1), 0.5, COLORS["border"]),
        ]))

        # Highlight urgent rows
        for i, d in enumerate(differentials[:5], 1):
            if d.get('urgent_workup', d.get('urgent', False)):
                diff_table.setStyle(TableStyle([
                    ("BACKGROUND", (0,i), (-1,i), HexColor("#FEF2F2")),
                ]))

        story.append(diff_table)

    story.append(Spacer(1, 6))

    # ── R: RECOMMENDATION ──────────────────────────────────────
    story.append(section_header(styles, "R", "RECOMMENDATION"))

    story.append(Paragraph("CLINICAL ACTION CHECKLIST", styles["section_label"]))

    recommendations = data.get('recommended_actions', data.get('recommendations', []))
    if not recommendations:
        # Default recommendations based on triage level
        recommendations = [
            "Complete vital signs assessment (BP, HR, RR, Temp, SpO2)",
            "Focused physical examination",
            "Review and confirm ICD-10 codes",
            "Consider appropriate investigations",
        ]
        if triage_color in ['red', 'orange']:
            recommendations.insert(0, "IMMEDIATE: Stabilize patient and establish IV access")
            recommendations.append("Urgent specialist review if indicated")

    for rec in recommendations:
        story.append(Paragraph(f'<font name="Courier" size="10">☐</font>  {rec}', styles["checklist"]))

    story.append(Spacer(1, 10))

    # ── BILINGUAL NOTE ─────────────────────────────────────────
    original_complaint = data.get('chief_complaint_original')
    if original_complaint and p_lang.lower() not in ['english', 'en']:
        story.append(Paragraph("PATIENT'S WORDS", styles["section_label"]))

        bil_data = [
            [
                Paragraph(f'<b>{p_lang}</b>', styles["small"]),
                Paragraph('<b>English (clinical)</b>', styles["small"]),
            ],
            [
                Paragraph(f'<i>"{original_complaint}"</i>', styles["body"]),
                Paragraph(chief_complaint, styles["body"]),
            ],
        ]
        bil_table = Table(bil_data, colWidths=[W*0.5, W*0.5])
        bil_table.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), COLORS["surface"]),
            ("BOX",           (0,0), (-1,-1), 0.5, COLORS["border"]),
            ("LINEAFTER",     (0,0), (0,-1), 0.5, COLORS["border"]),
            ("LINEBELOW",     (0,0), (-1,0), 0.5, COLORS["border"]),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
            ("RIGHTPADDING",  (0,0), (-1,-1), 10),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ]))
        story.append(bil_table)

    story.append(Spacer(1, 16))

    # ── DISCLAIMER ─────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=COLORS["border"], spaceAfter=6))

    disclaimer = (
        '<font size="6.5" color="#9CA3AF">'
        '<b>DISCLAIMER:</b> This note was generated by Daktari AI Medical Intake Assistant using '
        'AI-assisted clinical decision support. It is intended as a triage and handoff tool and '
        'does NOT constitute a diagnosis. Differential diagnoses are suggestions for clinical '
        'consideration only. Always apply clinical judgment and conduct appropriate examination '
        'before making treatment decisions.<br/><br/>'
        '<b>Data Sources:</b> ICD-10 codes from WHO ICD-10 / NLM Clinical Tables  |  '
        'Triage: South African Triage Scale (SATS)  |  '
        'Clinical reasoning: Mistral AI'
        '</font>'
    )
    story.append(Paragraph(disclaimer, styles["footer"]))

    # ── BUILD PDF ──────────────────────────────────────────────
    doc = SimpleDocTemplate(
        filename, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )
    doc.build(story)

    logger.info(f"✅ Generated PDF: {filename}")
    return filename


# Alias for backwards compatibility
def generate_simple_handoff_pdf(data: dict) -> str:
    """Alias for generate_handoff_pdf for backwards compatibility."""
    return generate_handoff_pdf(data)

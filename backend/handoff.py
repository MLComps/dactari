"""Generate enhanced SBAR clinical handoff PDF with differentials and SATS triage."""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem
from reportlab.pdfgen import canvas
from datetime import datetime
import os

# Ensure output directory exists
OUTPUT_DIR = "handoffs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Triage colors mapping
TRIAGE_COLORS = {
    'red': {'bg': '#DC2626', 'label': 'EMERGENCY', 'emoji': '🔴'},
    'orange': {'bg': '#EA580C', 'label': 'VERY URGENT', 'emoji': '🟠'},
    'yellow': {'bg': '#CA8A04', 'label': 'URGENT', 'emoji': '🟡'},
    'green': {'bg': '#16A34A', 'label': 'ROUTINE', 'emoji': '🟢'},
}


def generate_handoff_pdf(data: dict) -> str:
    """Generate enhanced SBAR clinical handoff note as PDF.

    Args:
        data: Dictionary containing:
            - chief_complaint: str
            - symptoms: list[str]
            - duration: str (optional)
            - severity: str (optional)
            - triggers: str (optional)
            - red_flags: list[str] (optional)
            - medical_history: str (optional)
            - patient_language: str (optional)
            - patient: dict (optional) - {name, age, gender, contact}
            - urgency_assessment: dict (optional) - {color, label, time_target, reasoning}
            - differentials: list[dict] (optional) - [{condition, icd10_code, confidence}]
            - recommended_actions: list[str] (optional)
            - symptom_timeline: str (optional)
            - icd_codes: list[str] (optional)

    Returns:
        Path to generated PDF file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    patient = data.get('patient', {})
    patient_name = patient.get('name', 'patient').replace(' ', '_') if patient else 'patient'
    filename = os.path.join(OUTPUT_DIR, f"handoff_{patient_name}_{timestamp}.pdf")

    # Create PDF document
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )

    # Styles
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=8,
        textColor=colors.HexColor('#1a5f7a')
    )

    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor('#1f2937'),
        fontName='Helvetica-Bold'
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=10,
        spaceBefore=2,
        spaceAfter=2,
        leading=13
    )

    small_style = ParagraphStyle(
        'Small',
        parent=body_style,
        fontSize=9,
        textColor=colors.HexColor('#6b7280')
    )

    checklist_style = ParagraphStyle(
        'Checklist',
        parent=body_style,
        fontSize=10,
        leftIndent=15,
        bulletIndent=5
    )

    # Build content
    story = []

    # === HEADER BANNER ===
    urgency_assessment = data.get('urgency_assessment', {})
    triage_color = urgency_assessment.get('color', 'green').lower()
    triage_info = TRIAGE_COLORS.get(triage_color, TRIAGE_COLORS['green'])

    # One-line triage summary banner
    chief = data.get('chief_complaint', 'Not specified')[:50]
    severity = data.get('severity', 'N/A')
    duration = data.get('duration', '')
    time_target = urgency_assessment.get('time_target', '')

    banner_text = f"{triage_info['emoji']} {triage_info['label']} | {chief}"
    if duration:
        banner_text += f" ({duration})"
    if severity and severity != 'N/A':
        banner_text += f" | Severity: {severity}/10"

    banner_table = Table(
        [[banner_text]],
        colWidths=[7*inch]
    )
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(triage_info['bg'])),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 0.15*inch))

    # Title and metadata
    story.append(Paragraph("CLINICAL HANDOFF NOTE", title_style))
    story.append(Paragraph(
        f"<b>Daktari AI Medical Intake</b> | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        f"<font color='gray'>AI-assisted triage — clinical judgment required</font>",
        small_style
    ))
    story.append(Spacer(1, 0.1*inch))

    # === PATIENT INFORMATION ===
    if patient:
        patient_info = f"<b>{patient.get('name', 'Unknown')}</b> | "
        patient_info += f"Age: {patient.get('age', 'Unknown')} | "
        patient_info += f"Sex: {patient.get('gender', 'Unknown').capitalize()}"
        if patient.get('contact'):
            patient_info += f" | Contact: {patient.get('contact')}"

        patient_table = Table([[patient_info]], colWidths=[7*inch])
        patient_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f3f4f6')),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(patient_table)
        story.append(Spacer(1, 0.1*inch))

    # === S - SITUATION ===
    story.append(Paragraph("S — SITUATION", section_style))

    situation_content = f"<b>Chief Complaint:</b> {data.get('chief_complaint', 'Not specified')}<br/>"
    situation_content += f"<b>Triage Level:</b> {triage_info['emoji']} {triage_info['label']}"
    if time_target:
        situation_content += f" — {time_target}"
    situation_content += f"<br/><b>Duration:</b> {data.get('duration', 'Not reported')}"
    situation_content += f"<br/><b>Severity:</b> {data.get('severity', 'Not reported')}/10"

    story.append(Paragraph(situation_content, body_style))

    # === B - BACKGROUND ===
    story.append(Paragraph("B — BACKGROUND", section_style))

    # Symptoms with ICD-10 codes
    symptoms = data.get('symptoms', [])
    icd_codes = data.get('icd_codes', [])

    if symptoms:
        symptoms_text = "<b>Symptoms:</b><br/>"
        for i, symptom in enumerate(symptoms):
            code = icd_codes[i] if i < len(icd_codes) else ""
            if code:
                symptoms_text += f"• {symptom} <font color='#6b7280'>(ICD-10: {code})</font><br/>"
            else:
                symptoms_text += f"• {symptom}<br/>"
        story.append(Paragraph(symptoms_text, body_style))

    # Triggers
    if data.get('triggers'):
        story.append(Paragraph(f"<b>Triggers/Aggravating factors:</b> {data.get('triggers')}", body_style))

    # Medical history
    story.append(Paragraph(f"<b>Medical History:</b> {data.get('medical_history', 'None reported')}", body_style))

    # Symptom Timeline
    timeline = data.get('symptom_timeline')
    if timeline:
        story.append(Spacer(1, 0.08*inch))
        story.append(Paragraph("<b>Symptom Timeline:</b>", body_style))

        # Create a simple timeline box
        timeline_table = Table([[timeline]], colWidths=[6.5*inch])
        timeline_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fef3c7')),
            ('FONTNAME', (0, 0), (-1, -1), 'Courier'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#d97706')),
        ]))
        story.append(timeline_table)

    # === A - ASSESSMENT ===
    story.append(Paragraph("A — ASSESSMENT", section_style))

    # Triage reasoning
    if urgency_assessment.get('reasoning'):
        reasoning_table = Table(
            [[f"<b>Triage Reasoning:</b> {urgency_assessment.get('reasoning')}"]],
            colWidths=[7*inch]
        )
        reasoning_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fef2f2') if triage_color in ['red', 'orange'] else colors.HexColor('#f0fdf4')),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(reasoning_table)
        story.append(Spacer(1, 0.08*inch))

    # Red flags
    red_flags = data.get('red_flags', [])
    if red_flags:
        flags_text = "<font color='red'><b>⚠️ RED FLAGS IDENTIFIED:</b></font><br/>"
        for flag in red_flags:
            flags_text += f"<font color='red'>• {flag}</font><br/>"
        story.append(Paragraph(flags_text, body_style))
        story.append(Spacer(1, 0.05*inch))

    # Differential Diagnoses (for clinician)
    differentials = data.get('differentials', [])
    if differentials:
        story.append(Paragraph("<b>Differential Diagnoses (Clinical Decision Support):</b>", body_style))

        diff_data = [["#", "Condition", "ICD-10", "Confidence", "Urgent W/U"]]
        for i, diff in enumerate(differentials[:5], 1):
            urgent = "⚠️" if diff.get('urgent_workup') else ""
            diff_data.append([
                str(i),
                diff.get('condition', 'Unknown')[:35],
                diff.get('icd10_code', '-'),
                diff.get('confidence', 'N/A'),
                urgent
            ])

        diff_table = Table(diff_data, colWidths=[0.3*inch, 2.8*inch, 0.8*inch, 0.8*inch, 0.5*inch])
        diff_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (4, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(diff_table)
        story.append(Spacer(1, 0.05*inch))
        story.append(Paragraph(
            "<font color='gray' size='8'>⚠️ = Urgent workup recommended even if low probability</font>",
            small_style
        ))

    # === R - RECOMMENDATION ===
    story.append(Paragraph("R — RECOMMENDATION", section_style))

    # Recommended actions as checklist
    recommended_actions = data.get('recommended_actions', [])
    if recommended_actions:
        story.append(Paragraph("<b>Clinical Action Checklist:</b>", body_style))
        for action in recommended_actions:
            story.append(Paragraph(f"☐ {action}", checklist_style))
    else:
        # Default recommendations based on triage level
        default_actions = [
            "Complete vital signs assessment",
            "Focused physical examination",
            "Review and confirm ICD-10 codes",
        ]
        if triage_color in ['red', 'orange']:
            default_actions.insert(0, "IMMEDIATE: Stabilize patient")
            default_actions.append("Consider urgent investigations")

        story.append(Paragraph("<b>Clinical Action Checklist:</b>", body_style))
        for action in default_actions:
            story.append(Paragraph(f"☐ {action}", checklist_style))

    story.append(Spacer(1, 0.2*inch))

    # === BILINGUAL SECTION ===
    original_language = data.get('patient_language', '')
    if original_language and original_language.lower() not in ['english', 'en', '']:
        story.append(Paragraph("BILINGUAL NOTES", section_style))
        bilingual_text = f"<b>Patient's Language:</b> {original_language}<br/>"
        bilingual_text += f"<b>Chief Complaint (Original):</b> <i>[Record patient's exact words]</i><br/>"
        bilingual_text += f"<b>Chief Complaint (English):</b> {data.get('chief_complaint', 'N/A')}"
        story.append(Paragraph(bilingual_text, body_style))
        story.append(Spacer(1, 0.1*inch))

    # === FOOTER ===
    story.append(Spacer(1, 0.2*inch))
    footer_text = """<font size='8' color='gray'>
    <b>DISCLAIMER:</b> This note was generated by Daktari AI Medical Intake Assistant using
    AI-assisted clinical decision support. It is intended as a triage and handoff tool and does NOT
    constitute a diagnosis. Differential diagnoses are suggestions for clinical consideration only.
    Always apply clinical judgment and conduct appropriate examination before treatment decisions.
    <br/><br/>
    <b>Data Sources:</b> ICD-10 codes from WHO ICD-10 / NLM Clinical Tables | Triage: South African Triage Scale (SATS)
    </font>"""
    story.append(Paragraph(footer_text, small_style))

    # Build PDF
    doc.build(story)
    return filename


def generate_simple_handoff_pdf(data: dict) -> str:
    """Generate a simple PDF without reportlab styling (fallback)."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(OUTPUT_DIR, f"handoff_{timestamp}.pdf")

    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "CLINICAL HANDOFF NOTE - Daktari")

    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, f"Generated: {datetime.now().isoformat()}")

    # Urgency
    urgency_assessment = data.get('urgency_assessment', {})
    triage_color = urgency_assessment.get('color', 'green').lower()
    triage_label = urgency_assessment.get('label', 'ROUTINE')

    c.setFont("Helvetica-Bold", 14)
    if triage_color == 'red':
        c.setFillColorRGB(0.86, 0.15, 0.15)
    elif triage_color == 'orange':
        c.setFillColorRGB(0.92, 0.35, 0.05)
    elif triage_color == 'yellow':
        c.setFillColorRGB(0.79, 0.54, 0.02)
    else:
        c.setFillColorRGB(0.09, 0.64, 0.29)
    c.drawString(50, height - 100, f"TRIAGE: {triage_label}")
    c.setFillColorRGB(0, 0, 0)

    y = height - 140

    # Patient info
    patient = data.get('patient', {})
    if patient:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "PATIENT INFORMATION")
        y -= 18
        c.setFont("Helvetica", 10)
        c.drawString(70, y, f"Name: {patient.get('name', 'Not provided')}")
        y -= 14
        c.drawString(70, y, f"Age: {patient.get('age', 'Unknown')} years | Gender: {patient.get('gender', 'Unknown')}")
        y -= 14
        c.drawString(70, y, f"Contact: {patient.get('contact', 'Not provided') or 'Not provided'}")
        y -= 24

    # Sections
    sections = {
        "SITUATION": [
            f"Chief Complaint: {data.get('chief_complaint', 'Not specified')}",
            f"Severity: {data.get('severity', 'Not reported')}/10",
            f"Duration: {data.get('duration', 'Not reported')}"
        ],
        "BACKGROUND": [
            f"Symptoms: {', '.join(data.get('symptoms', ['Not specified']))}",
            f"Medical History: {data.get('medical_history', 'None reported')}"
        ],
        "ASSESSMENT": [
            f"ICD-10 Codes: {', '.join(data.get('icd_codes', ['Pending']))}",
            f"Red Flags: {', '.join(data.get('red_flags', ['None']))}",
            f"Triage Reasoning: {urgency_assessment.get('reasoning', 'N/A')[:80]}..."
        ],
        "RECOMMENDATION": data.get('recommended_actions', [
            "Complete physical examination",
            "Review ICD-10 codes",
            "Consider appropriate investigations"
        ])[:4]
    }

    for title, lines in sections.items():
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, title)
        y -= 18

        c.setFont("Helvetica", 10)
        for line in lines:
            # Wrap long lines
            if len(line) > 80:
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line + word) < 80:
                        current_line += word + " "
                    else:
                        c.drawString(70, y, current_line.strip())
                        y -= 14
                        current_line = word + " "
                if current_line:
                    c.drawString(70, y, current_line.strip())
                    y -= 14
            else:
                c.drawString(70, y, line)
                y -= 14
        y -= 10

    # Differentials
    differentials = data.get('differentials', [])
    if differentials and y > 150:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "DIFFERENTIAL DIAGNOSES")
        y -= 18
        c.setFont("Helvetica", 10)
        for i, diff in enumerate(differentials[:3], 1):
            c.drawString(70, y, f"{i}. {diff.get('condition', 'Unknown')} ({diff.get('confidence', 'N/A')})")
            y -= 14

    # Footer
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(50, 30, "AI-assisted triage - Clinical judgment required | Daktari Medical Intake Assistant")

    c.save()
    return filename

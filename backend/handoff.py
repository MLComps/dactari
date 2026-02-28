"""Generate SBAR clinical handoff PDF."""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfgen import canvas
from datetime import datetime
import os

# Ensure output directory exists
OUTPUT_DIR = "handoffs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_handoff_pdf(data: dict) -> str:
    """Generate SBAR clinical handoff note as PDF.

    Args:
        data: Dictionary containing:
            - chief_complaint: str
            - symptoms: list[str]
            - duration: str (optional)
            - severity: str (optional)
            - red_flags: list[str] (optional)
            - medical_history: str (optional)
            - patient_language: str (optional)
            - urgency: str (emergency/urgent/routine)
            - icd_codes: list[str] (optional)

    Returns:
        Path to generated PDF file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(OUTPUT_DIR, f"handoff_{timestamp}.pdf")

    # Create PDF document
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12,
        textColor=colors.HexColor('#1a5f7a')
    )
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=16,
        spaceAfter=8,
        textColor=colors.HexColor('#2d3436')
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=11,
        spaceBefore=4,
        spaceAfter=4,
        leading=14
    )
    urgent_style = ParagraphStyle(
        'Urgent',
        parent=body_style,
        textColor=colors.red,
        fontName='Helvetica-Bold'
    )

    # Build content
    story = []

    # Header
    story.append(Paragraph("CLINICAL HANDOFF NOTE", title_style))
    story.append(Paragraph(
        f"<b>Daktari Medical Intake Assistant</b><br/>"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        body_style
    ))
    story.append(Spacer(1, 0.25*inch))

    # Urgency banner
    urgency = data.get('urgency', 'routine').upper()
    urgency_colors = {
        'EMERGENCY': colors.HexColor('#e74c3c'),
        'URGENT': colors.HexColor('#e67e22'),
        'ROUTINE': colors.HexColor('#27ae60')
    }
    urgency_color = urgency_colors.get(urgency, colors.gray)

    urgency_table = Table(
        [[f"URGENCY: {urgency}"]],
        colWidths=[6*inch]
    )
    urgency_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), urgency_color),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(urgency_table)
    story.append(Spacer(1, 0.25*inch))

    # SBAR Format
    # S - Situation
    story.append(Paragraph("S - SITUATION", section_style))
    situation_data = [
        ["Chief Complaint:", data.get('chief_complaint', 'Not specified')],
        ["Patient Language:", data.get('patient_language', 'Not recorded')],
    ]
    situation_table = Table(situation_data, colWidths=[1.5*inch, 4.5*inch])
    situation_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(situation_table)

    # B - Background
    story.append(Paragraph("B - BACKGROUND", section_style))
    symptoms_text = ", ".join(data.get('symptoms', ['Not specified']))
    background_data = [
        ["Symptoms:", symptoms_text],
        ["Duration:", data.get('duration', 'Not reported')],
        ["Severity:", data.get('severity', 'Not reported')],
        ["Medical History:", data.get('medical_history', 'None reported')],
    ]
    background_table = Table(background_data, colWidths=[1.5*inch, 4.5*inch])
    background_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(background_table)

    # A - Assessment
    story.append(Paragraph("A - ASSESSMENT", section_style))

    icd_codes = data.get('icd_codes', ['Pending review'])
    icd_text = ", ".join(icd_codes) if isinstance(icd_codes, list) else str(icd_codes)

    red_flags = data.get('red_flags', [])
    if red_flags:
        red_flags_text = "<font color='red'><b>" + ", ".join(red_flags) + "</b></font>"
    else:
        red_flags_text = "None identified"

    assessment_data = [
        ["ICD-10 Codes:", icd_text],
        ["Red Flags:", ""],
    ]
    assessment_table = Table(assessment_data, colWidths=[1.5*inch, 4.5*inch])
    assessment_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(assessment_table)

    # Red flags as separate paragraph for formatting
    if red_flags:
        story.append(Paragraph(
            f"<font color='red'><b>WARNING: {', '.join(red_flags)}</b></font>",
            urgent_style
        ))
    else:
        story.append(Paragraph("No red flags identified.", body_style))

    # R - Recommendation
    story.append(Paragraph("R - RECOMMENDATION", section_style))
    recommendations = [
        "1. Conduct physical examination to confirm preliminary assessment",
        "2. Consider diagnostic tests based on clinical presentation",
        "3. Review ICD-10 codes and adjust as needed after examination",
    ]
    if urgency == 'EMERGENCY':
        recommendations.insert(0, "<b>IMMEDIATE ACTION REQUIRED - Prioritize this patient</b>")
    elif urgency == 'URGENT':
        recommendations.insert(0, "<b>Expedited review recommended</b>")

    for rec in recommendations:
        story.append(Paragraph(rec, body_style))

    story.append(Spacer(1, 0.5*inch))

    # Footer
    story.append(Paragraph(
        "<i>This note was generated by Daktari AI Medical Intake Assistant. "
        "It is intended as a clinical handoff tool and does not constitute a diagnosis. "
        "Always apply clinical judgment.</i>",
        ParagraphStyle('Footer', parent=body_style, fontSize=9, textColor=colors.gray)
    ))

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
    urgency = data.get('urgency', 'routine').upper()
    c.setFont("Helvetica-Bold", 14)
    if urgency == 'EMERGENCY':
        c.setFillColorRGB(0.9, 0.1, 0.1)
    elif urgency == 'URGENT':
        c.setFillColorRGB(0.9, 0.5, 0.1)
    else:
        c.setFillColorRGB(0.1, 0.7, 0.3)
    c.drawString(50, height - 100, f"URGENCY: {urgency}")
    c.setFillColorRGB(0, 0, 0)

    y = height - 140

    # Sections
    sections = {
        "SITUATION": [
            f"Chief Complaint: {data.get('chief_complaint', 'Not specified')}",
            f"Patient Language: {data.get('patient_language', 'Unknown')}"
        ],
        "BACKGROUND": [
            f"Symptoms: {', '.join(data.get('symptoms', ['Not specified']))}",
            f"Duration: {data.get('duration', 'Not reported')}",
            f"Severity: {data.get('severity', 'Not reported')}",
            f"Medical History: {data.get('medical_history', 'None reported')}"
        ],
        "ASSESSMENT": [
            f"ICD-10 Codes: {', '.join(data.get('icd_codes', ['Pending']))}",
            f"Red Flags: {', '.join(data.get('red_flags', ['None']))}"
        ],
        "RECOMMENDATION": [
            "Please conduct physical examination and confirm assessment.",
            "Consider diagnostic tests based on clinical presentation."
        ]
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

    c.save()
    return filename

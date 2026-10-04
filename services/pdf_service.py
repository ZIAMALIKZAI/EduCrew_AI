import io
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

class PDFReportService:
    @classmethod
    def generate_lesson_pdf(cls, topic: str, grade_level: str, markdown_content: str, school_name: str = "GOVERNMENT HIGH SCHOOL") -> bytes:
        """
        Converts the Multi-Agent Crew's generated markdown lesson pack
        into a formatted, official printable institutional PDF.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )

        styles = getSampleStyleSheet()

        # Custom Typographic Hierarchy
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            textColor=colors.HexColor('#065F46'),
            alignment=1, # Center
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'DocSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=14,
            textColor=colors.HexColor('#475569'),
            alignment=1,
            spaceAfter=15
        )
        h1_style = ParagraphStyle(
            'Heading1_Custom',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=colors.HexColor('#065F46'),
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True
        )
        h2_style = ParagraphStyle(
            'Heading2_Custom',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=14,
            textColor=colors.HexColor('#1E3A8A'),
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True
        )
        body_style = ParagraphStyle(
            'Body_Custom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor('#1E293B'),
            spaceAfter=4
        )
        bullet_style = ParagraphStyle(
            'Bullet_Custom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor('#1E293B'),
            leftIndent=15,
            spaceAfter=3
        )

        story = []

        # Document Header
        story.append(Paragraph(school_name.upper(), title_style))
        story.append(Paragraph(f"OFFICIAL LESSON & ASSESSMENT PACK • {grade_level.upper()}", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#065F46'), spaceAfter=10))

        # Metadata Table
        meta_data = [
            [
                Paragraph(f"<b>Topic:</b> {topic}", body_style),
                Paragraph(f"<b>Class Level:</b> {grade_level}", body_style),
                Paragraph("<b>Session:</b> 2026-2027", body_style)
            ]
        ]
        meta_table = Table(meta_data, colWidths=[240, 160, 130])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 14))

        # Markdown Parser into Flowable PDF Elements
        lines = markdown_content.split('\n')
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                story.append(Spacer(1, 4))
                continue

            # Section Headers
            if line.startswith('# '):
                text = line.replace('# ', '').strip()
                story.append(Paragraph(text, h1_style))
                story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceAfter=4))
            elif line.startswith('## '):
                text = line.replace('## ', '').strip()
                story.append(Paragraph(text, h1_style))
            elif line.startswith('### '):
                text = line.replace('### ', '').strip()
                story.append(Paragraph(text, h2_style))
            elif line.startswith('#### '):
                text = line.replace('#### ', '').strip()
                story.append(Paragraph(f"<b>{text}</b>", h2_style))
            # Bullets
            elif line.startswith('- ') or line.startswith('* '):
                text = line[2:].strip()
                clean_text = cls._format_inline_markdown(text)
                story.append(Paragraph(f"&bull; {clean_text}", bullet_style))
            elif re.match(r'^\d+\.\s', line):
                clean_text = cls._format_inline_markdown(line)
                story.append(Paragraph(clean_text, bullet_style))
            # Standard Paragraphs
            else:
                clean_text = cls._format_inline_markdown(line)
                story.append(Paragraph(clean_text, body_style))

        # Document Footer & Build
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def _format_inline_markdown(text: str) -> str:
        """Converts bold and italic markdown tags to safe ReportLab XML tags."""
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        # Bold: **word** -> <b>word</b>
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        # Italic: *word* -> <i>\1</i>
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        # Code backticks: `word` -> <font name="Courier">word</font>
        text = re.sub(r'`(.*?)`', r'<font name="Courier" color="#065F46"><b>\1</b></font>', text)
        return text

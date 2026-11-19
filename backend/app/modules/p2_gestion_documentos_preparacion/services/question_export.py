"""Student question handout: no internal answers or retrieval evidence."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether


def export_questions(bank, document_name: str) -> bytes:
    output = BytesIO()
    styles = getSampleStyleSheet()
    styles["BodyText"].leading = 16
    story = [
        Paragraph("Socratia · Banco de preguntas", styles["Title"]),
        Spacer(1, 0.4 * cm),
        Paragraph(escape(document_name), styles["Heading2"]),
        Paragraph(
            "Practica tus argumentos y contrástalos con tu investigación.", styles["BodyText"]
        ),
        Spacer(1, 0.5 * cm),
    ]
    categories = {
        "CONCEPTUAL": "Conceptual",
        "METHODOLOGICAL": "Metodología",
        "TECHNICAL": "Técnica",
        "RESULTS": "Resultados",
        "CRITICAL": "Análisis crítico",
    }
    for index, question in enumerate(bank.questions, 1):
        category = getattr(question.category, "value", str(question.category))
        story.append(
            KeepTogether(
                [
                    Paragraph(f"Pregunta {index}", styles["Heading3"]),
                    Paragraph(
                        escape(categories.get(category, "Defensa académica")), styles["Italic"]
                    ),
                    Paragraph(escape(question.question).replace("\n", "<br/>"), styles["BodyText"]),
                    Spacer(1, 0.45 * cm),
                ]
            )
        )

    def footer(canvas, doc):
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#405b60"))
        canvas.drawString(2 * cm, 1.2 * cm, "Socratia · Preparación de defensa")
        canvas.drawRightString(19 * cm, 1.2 * cm, str(doc.page))

    SimpleDocTemplate(
        output,
        pagesize=(21 * cm, 29.7 * cm),
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Banco de preguntas · Socratia",
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()

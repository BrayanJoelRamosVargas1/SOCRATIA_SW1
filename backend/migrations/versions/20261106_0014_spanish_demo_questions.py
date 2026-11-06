"""Repair the known English bank from the fictional tutoring demo, preserving IDs.

No API calls. Original generated text is retained for an exact, conditional rollback.
Student responses, evidence, scores and source documents are never modified.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261106_0014"
down_revision = "20261018_0013"
branch_labels = None
depends_on = None

TRANSLATIONS = {
    "What is the primary problem the project aims to solve, and why is it significant for university tutoring coordination?": "¿Cuál es el problema principal que busca resolver el proyecto y por qué es importante para la coordinación de tutorías universitarias?",
    "How does the project define and differentiate between 'student' and 'administrator' roles within the system?": "¿Cómo define y diferencia el proyecto los roles de estudiante y administrador dentro del sistema?",
    "In what ways does the project acknowledge limitations of its evaluation, and what implications do these limitations have for generalizing results?": "¿De qué manera reconoce el proyecto las limitaciones de su evaluación y qué implicaciones tienen para generalizar los resultados?",
    "Describe the iterative development process used for the prototype, including the number of iterations and types of tests performed.": "Describa el proceso de desarrollo iterativo utilizado para el prototipo, incluido el número de iteraciones y los tipos de pruebas realizados.",
    "What criteria were used to select the sample of participants for the evaluation, and how does this choice affect the validity of the findings?": "¿Qué criterios se utilizaron para seleccionar a los participantes de la evaluación y cómo afecta esa elección a la validez de los hallazgos?",
    "Explain the approach taken to validate the uniqueness of reservation identifiers and how this mitigates duplicate bookings.": "Explique cómo se validó la unicidad de los identificadores de reserva y cómo esto reduce las reservas duplicadas.",
    "Outline the architectural components of the prototype and explain how they interact to support tutoring requests.": "Describa los componentes de la arquitectura del prototipo y explique cómo interactúan para gestionar las solicitudes de tutoría.",
    "Discuss the security measures implemented for credential storage and why storing keys outside the codebase is important.": "Analice las medidas de seguridad implementadas para almacenar las credenciales y explique por qué es importante guardar las claves fuera del código.",
    "What performance metrics were collected during functional testing, and what were the observed results?": "¿Qué métricas de rendimiento se recopilaron durante las pruebas funcionales y cuáles fueron los resultados observados?",
    "Identify the main risk associated with the current prototype's handling of calendar conflicts and propose a mitigation strategy.": "Identifique el principal riesgo del manejo de conflictos de agenda en el prototipo actual y proponga una estrategia para mitigarlo.",
    "Evaluate the potential impact of not measuring concurrent user load on the system's scalability.": "Evalúe el posible efecto de no haber medido la carga de usuarios concurrentes sobre la escalabilidad del sistema.",
    "Critique the decision to use a fictitious dataset for evaluation, considering the trade-offs between controlled testing and realistic user behavior.": "Analice críticamente el uso de datos ficticios en la evaluación y el equilibrio entre pruebas controladas y el comportamiento real de los usuarios."
}
FIELDS = {"questions":"question", "simulation_questions":"prompt_text", "simulation_turns":"content"}


def upgrade():
    op.create_table("spanish_question_repairs",
        sa.Column("table_name",sa.String(50),primary_key=True),
        sa.Column("row_id",sa.String(36),primary_key=True),
        sa.Column("original_text",sa.Text(),nullable=False),
        sa.Column("translated_text",sa.Text(),nullable=False))
    db=op.get_bind()
    audit=sa.table("spanish_question_repairs",sa.column("table_name"),sa.column("row_id"),sa.column("original_text"),sa.column("translated_text"))
    for name,field in FIELDS.items():
        table=sa.table(name,sa.column("id"),sa.column(field),sa.column("speaker"))
        column=table.c[field]
        where=sa.or_(*(column.contains(text) for text in TRANSLATIONS))
        if name=="simulation_turns":where=sa.and_(where,table.c.speaker=="JURY")
        for row in db.execute(sa.select(table.c.id,column).where(where)).mappings():
            before=row[field];after=before
            for old,new in TRANSLATIONS.items():after=after.replace(old,new)
            if before==after:continue
            db.execute(audit.insert().values(table_name=name,row_id=row["id"],original_text=before,translated_text=after))
            db.execute(table.update().where(table.c.id==row["id"],column==before).values({field:after}))


def downgrade():
    db=op.get_bind()
    audit=sa.table("spanish_question_repairs",sa.column("table_name"),sa.column("row_id"),sa.column("original_text"),sa.column("translated_text"))
    for row in db.execute(sa.select(audit)).mappings():
        field=FIELDS[row["table_name"]]
        table=sa.table(row["table_name"],sa.column("id"),sa.column(field))
        db.execute(table.update().where(table.c.id==row["row_id"] ,table.c[field]==row["translated_text"]).values({field:row["original_text"]}))
    op.drop_table("spanish_question_repairs")

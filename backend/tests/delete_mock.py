from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
db.execute(text("DELETE FROM document_chunks WHERE document_id = 'd5dd4fb7-0a32-418a-bdb5-10c1caedaafa'"))
db.execute(text("DELETE FROM embedding_profiles WHERE document_id = 'd5dd4fb7-0a32-418a-bdb5-10c1caedaafa'"))
db.execute(text("DELETE FROM documents WHERE id = 'd5dd4fb7-0a32-418a-bdb5-10c1caedaafa'"))
db.commit()

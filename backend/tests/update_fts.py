from sqlalchemy import text
from app.core.database import SessionLocal

db = SessionLocal()
db.execute(text("UPDATE document_chunks SET search_vector = to_tsvector('spanish', coalesce(content, '')) WHERE content LIKE '%Mock content%'"))
db.commit()
print("Updated search_vector")

from sqlalchemy import text
from app.core.database import SessionLocal

db = SessionLocal()
res = db.execute(text("SELECT id, content, fts_vector FROM document_chunks WHERE content LIKE '%Mock%'")).fetchone()
if res:
    print('Vector:', res[2])
else:
    print('No match')

from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
db.execute(text("DELETE FROM vector_embeddings_768"))
db.execute(text("DELETE FROM document_chunks"))
db.execute(text("DELETE FROM chunk_sets"))
db.execute(text("DELETE FROM embedding_profiles"))
db.execute(text("DELETE FROM presentation_materials"))
db.execute(text("DELETE FROM question_banks"))
db.execute(text("DELETE FROM documents"))
db.commit()
print("done")

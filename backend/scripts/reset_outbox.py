import os
import sys
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.database import SessionLocal
from app.modules.p2_gestion_documentos_preparacion.models.vector_store import VectorSyncOutbox

def reset_outbox():
    db = SessionLocal()
    try:
        # Find the outbox item we created in the smoke test
        # and reset it to PENDING
        stmt = text("""
            UPDATE vector_sync_outbox 
            SET status = 'PENDING', attempts = 0, next_retry_at = NULL, locked_by = NULL, locked_at = NULL, lease_expires_at = NULL
            WHERE operation = 'UPSERT' 
            RETURNING id
        """)
        result = db.execute(stmt)
        updated = result.fetchall()
        db.commit()
        print(f"Reset {len(updated)} outbox items to PENDING")
        for u in updated:
            print(f" - {u[0]}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_outbox()

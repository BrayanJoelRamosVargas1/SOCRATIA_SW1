"""Scenario arithmetic, not a bill or usage meter. Official rates checked 2026-10-15."""
import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument("--sessions", type=int, default=100)
parser.add_argument("--new-documents", type=int, default=100)
parser.add_argument("--answers", type=int, default=12)
parser.add_argument("--audio-minutes", type=float, default=20)
parser.add_argument("--clothing-checks", type=int, default=3)
parser.add_argument("--aws-monthly", type=float, default=24)
args = parser.parse_args()
if any(value < 0 for value in vars(args).values()):
    parser.error("Values must be non-negative.")
# Paid standard rates, USD. Do not assume free-tier quotas or cache discounts.
# Token sizes below are workload assumptions, not observed provider usage.
cost_per_bank = (4000*.75 + 4000*3.75)/1_000_000
cost_per_document_embedding = 75000*.20/1_000_000
per_session = {
    "evaluation_groq": args.answers*(4500*.075+500*.30)/1_000_000,
    "jury_groq": args.answers*(1200*.075+200*.30)/1_000_000,
    "transcription_groq": args.audio_minutes/60*.04,
    "clothing_gemini": args.clothing_checks*(1500*.25+300*1.50)/1_000_000,
}
new_document_cost = args.new_documents*(cost_per_bank+cost_per_document_embedding)
ai_total = args.sessions*sum(per_session.values())+new_document_cost
print(json.dumps({
    "rate_date": "2026-10-15", "currency": "USD", "assumptions": vars(args),
    "per_session_without_new_document": per_session,
    "new_documents_embeddings_and_question_banks": new_document_cost,
    "ai_monthly": ai_total, "aws_monthly_assumption": args.aws_monthly,
    "combined_before_extras": ai_total+args.aws_monthly,
    "excluded": ["backups", "domain", "taxes", "egress overages", "extra context/output/thinking tokens", "retries/fallbacks", "paid TTS", "presentation generation", "old project resources", "capacity scaling"],
    "sources": ["https://ai.google.dev/gemini-api/docs/pricing", "https://console.groq.com/docs/models", "https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-bundles.html"],
}, indent=2))

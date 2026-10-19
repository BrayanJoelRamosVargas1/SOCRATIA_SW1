"""Create unique staging secrets without printing them or copying development keys."""
import argparse
from pathlib import Path
import re
import secrets

parser = argparse.ArgumentParser()
parser.add_argument("--domain", required=True)
parser.add_argument("--output", type=Path, default=Path(".env.staging"))
args = parser.parse_args()
if not re.fullmatch(r"(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}", args.domain):
    parser.error("Use a DNS hostname, without a scheme, path, port or wildcard.")
template = Path(__file__).resolve().parents[1] / "staging" / "staging.env.example"
text = template.read_text(encoding="utf-8").replace("staging.example.com", args.domain)
text = text.replace("POSTGRES_PASSWORD=\n", f"POSTGRES_PASSWORD={secrets.token_hex(24)}\n")
text = text.replace("JWT_SECRET=\n", f"JWT_SECRET={secrets.token_hex(32)}\n")
with args.output.open("x", encoding="utf-8") as destination:
    destination.write(text)
args.output.chmod(0o600)
print(f"Created {args.output}. Secrets were not printed; existing files are never overwritten.")

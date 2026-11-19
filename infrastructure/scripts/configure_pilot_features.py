"""Configure pilot limits and create VAPID keys on the server without printing secrets.
Run with the backend Python environment, against the private .env.staging file.
"""

import argparse
import base64
from pathlib import Path
import re
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

parser = argparse.ArgumentParser()
parser.add_argument("--env", type=Path, required=True)
args = parser.parse_args()
p = args.env.resolve()
assert p.is_file(), "Existing private environment required"
s = p.read_text(encoding="utf-8")


def value(key):
    match = re.search(r"^" + key + r"=(.*)$", s, re.M)
    return match.group(1).strip() if match else ""


def put(key, value):
    global s
    if re.search(r"^" + key + r"=", s, re.M):
        s = re.sub(r"^" + key + r"=.*$", lambda _: key + "=" + value, s, flags=re.M)
    else:
        s = s.rstrip() + "\n" + key + "=" + value + "\n"


for key, val in {
    "MAX_DOCUMENT_SIZE_MB": "50",
    "DOCUMENT_MAX_CHUNKS": "500",
    "QUESTION_GENERATION_TIMEOUT_SECONDS": "30",
    "QUESTION_GENERATION_MAX_ATTEMPTS": "1",
    "PREPARATION_PRIMARY_PROVIDER": "groq",
}.items():
    put(key, val)
if not value("PUSH_PRIVATE_KEY") and not value("PUSH_PUBLIC_KEY"):
    key = ec.generate_private_key(ec.SECP256R1())
    enc = lambda data: base64.urlsafe_b64encode(data).decode().rstrip("=")
    put(
        "PUSH_PRIVATE_KEY", enc(key.private_numbers().private_value.to_bytes(32, "big"))
    )
    put(
        "PUSH_PUBLIC_KEY",
        enc(
            key.public_key().public_bytes(
                serialization.Encoding.X962,
                serialization.PublicFormat.UncompressedPoint,
            )
        ),
    )
assert value("PUSH_PRIVATE_KEY") and value("PUSH_PUBLIC_KEY"), (
    "Incomplete VAPID pair: fix before continuing"
)
if not value("PUSH_CONTACT"):
    put("PUSH_CONTACT", "mailto:joelramostrbj@gmail.com")
p.write_text(s, encoding="utf-8")
p.chmod(0o600)
print("Pilot limits and push keys configured; secrets were not printed.")

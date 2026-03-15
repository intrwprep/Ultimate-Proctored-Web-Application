import base64
import hashlib
import hmac
import json
import os

from cryptography.fernet import Fernet


def get_fernet() -> Fernet:
    key = os.getenv("ANSWER_ENCRYPTION_KEY")
    if not key:
        key = Fernet.generate_key().decode()
        os.environ["ANSWER_ENCRYPTION_KEY"] = key
    return Fernet(key.encode())


def sha256_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sign_exam_payload(payload: dict, secret: str) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    sig = hmac.new(secret.encode(), canonical, hashlib.sha256).digest()
    return base64.b64encode(sig).decode()


def verify_exam_signature(payload: dict, signature: str | None, secret: str) -> bool:
    if not signature:
        return False
    expected = sign_exam_payload(payload, secret)
    return hmac.compare_digest(expected, signature)

import base64
import hashlib
from cryptography.fernet import Fernet
from .config import KEY_ENCRYPTION_SECRET


def _fernet() -> Fernet:
    if not KEY_ENCRYPTION_SECRET or len(KEY_ENCRYPTION_SECRET) < 16:
        raise RuntimeError(
            "KEY_ENCRYPTION_SECRET is missing/too short. Set it in .env (16+ chars, ideally 32+)."
        )
    digest = hashlib.sha256(KEY_ENCRYPTION_SECRET.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(digest)
    return Fernet(fernet_key)


def encrypt_api_key(api_key: str) -> bytes:
    return _fernet().encrypt(api_key.encode("utf-8"))


def decrypt_api_key(ciphertext: bytes) -> str:
    return _fernet().decrypt(ciphertext).decode("utf-8")

from functools import lru_cache

from cryptography.fernet import Fernet

from backend.config.security import get_fernet_key


@lru_cache(maxsize=1)
def get_fernet() -> Fernet:
    return Fernet(get_fernet_key().encode("utf-8"))


def encrypt_bytes(plaintext: bytes) -> bytes:
    return get_fernet().encrypt(plaintext)


def decrypt_bytes(ciphertext: bytes) -> bytes:
    return get_fernet().decrypt(ciphertext)

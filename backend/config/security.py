import os

from dotenv import load_dotenv


load_dotenv()


def get_fernet_key() -> str:
    fernet_key = os.getenv("FERNET_KEY")

    if not fernet_key:
        raise ValueError("FERNET_KEY is not configured.")

    return fernet_key

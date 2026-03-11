import os


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing env var {name}.")
    return value


S3_BUCKET = _required("S3_BUCKET")
GOOGLE_SHEET_ID = _required("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS_S3_BUCKET = os.environ.get("GOOGLE_CREDENTIALS_S3_BUCKET")
GOOGLE_CREDENTIALS_S3_KEY = os.environ.get("GOOGLE_CREDENTIALS_S3_KEY")
GOOGLE_SHEET_NAME = os.environ.get("GOOGLE_SHEET_NAME")

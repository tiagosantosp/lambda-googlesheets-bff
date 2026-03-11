import json
from typing import Dict, List

import boto3
import gspread
from google.oauth2.service_account import Credentials

from config.config import (
    GOOGLE_CREDENTIALS_S3_BUCKET,
    GOOGLE_CREDENTIALS_S3_KEY,
    GOOGLE_SHEET_ID,
    GOOGLE_SHEET_NAME,
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_DOCUMENTS_CACHE: List[Dict[str, str]] | None = None
_CACHE_SHEET_ID: str | None = None


def _load_credentials_info() -> Dict:
    if GOOGLE_CREDENTIALS_S3_BUCKET and GOOGLE_CREDENTIALS_S3_KEY:
        s3 = boto3.client("s3")
        obj = s3.get_object(
            Bucket=GOOGLE_CREDENTIALS_S3_BUCKET,
            Key=GOOGLE_CREDENTIALS_S3_KEY,
        )
        content = obj["Body"].read().decode("utf-8")
        return json.loads(content)

    if GOOGLE_CREDENTIALS_S3_KEY:
        return json.loads(GOOGLE_CREDENTIALS_S3_KEY)

    raise RuntimeError(
        "Missing Google credentials. Set GOOGLE_CREDENTIALS_S3_BUCKET + "
        "GOOGLE_CREDENTIALS_S3_KEY or provide JSON in GOOGLE_CREDENTIALS_S3_KEY."
    )


def _get_sheet():
    credentials_info = _load_credentials_info()
    credentials = Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
    client = gspread.authorize(credentials)
    return client.open_by_key(GOOGLE_SHEET_ID)


def _normalize_record(record: Dict[str, str]) -> Dict[str, str]:
    lowered = {str(k).strip().lower(): v for k, v in record.items()}

    return {
        "empresa": lowered.get("empresa", ""),
        "valor": lowered.get("valor", ""),
        "categoria": lowered.get("categoria", ""),
        "data": lowered.get("data", ""),
        "arquivo": lowered.get("nomearquivo")
        or lowered.get("arquivo")
        or lowered.get("filename")
        or "",
        "link": lowered.get("links3") or lowered.get("link") or lowered.get("s3") or "",
    }


def get_documents() -> List[Dict[str, str]]:
    global _DOCUMENTS_CACHE, _CACHE_SHEET_ID

    if _DOCUMENTS_CACHE is not None and _CACHE_SHEET_ID == GOOGLE_SHEET_ID:
        return _DOCUMENTS_CACHE

    sheet = _get_sheet()
    worksheet = sheet.worksheet(GOOGLE_SHEET_NAME) if GOOGLE_SHEET_NAME else sheet.sheet1

    records = worksheet.get_all_records()
    documents = [_normalize_record(record) for record in records]

    _DOCUMENTS_CACHE = documents
    _CACHE_SHEET_ID = GOOGLE_SHEET_ID
    return documents

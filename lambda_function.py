import json
from typing import Any, Dict

from services.s3_service import create_presigned_url
from services.sheets_service import get_documents
from utils.filters import apply_filters, build_stats

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
}


def _response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", **CORS_HEADERS},
        "body": json.dumps(body),
    }


def handler(event, context):  # noqa: ARG001 - AWS Lambda signature
    method = (
        event.get("requestContext", {})
        .get("http", {})
        .get("method", event.get("httpMethod", "GET"))
    )

    if method == "OPTIONS":
        return {
            "statusCode": 204,
            "headers": CORS_HEADERS,
            "body": "",
        }

    path = event.get("rawPath") or event.get("path") or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    params = event.get("queryStringParameters") or {}

    try:
        force_refresh = params.get("refresh") == "1"

        if path == "/documents":
            documents = get_documents(force_refresh=force_refresh)
            documents = apply_filters(documents, params)
            return _response(200, {"documents": documents})

        if path == "/stats":
            documents = get_documents(force_refresh=force_refresh)
            stats = build_stats(documents)
            return _response(200, stats)

        if path == "/download":
            file_key = params.get("file") or params.get("key")
            if not file_key:
                return _response(400, {"error": "Missing required query param: file"})

            url = create_presigned_url(file_key)
            return _response(200, {"url": url, "expiresIn": 300})

        return _response(404, {"error": "Not found"})
    except Exception as exc:  # noqa: BLE001 - return controlled error
        return _response(500, {"error": "Internal server error", "details": str(exc)})

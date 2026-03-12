import json
from typing import Any, Dict

from services.s3_service import create_presigned_url
from services.sheets_service import get_documents
from utils.dashboard import (
    build_breakdowns,
    build_filter_options,
    build_indicators,
    parse_reference_date,
    resolve_period_range,
)
from utils.filters import apply_filters, build_stats, parse_amount

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

        if path == "/dashboard/indicators":
            reference_date = parse_reference_date(params.get("referenceDate"))
            if not reference_date:
                return _response(400, {"error": "Missing or invalid query param: referenceDate (DD-MM-AAAA)"})

            documents = get_documents(force_refresh=force_refresh)
            indicators = build_indicators(
                documents,
                reference_date=reference_date,
                empresa=params.get("empresa"),
                categoria=params.get("categoria"),
                texto=params.get("texto"),
                valor_min=parse_amount(params.get("valorMin")) if params.get("valorMin") else None,
                valor_max=parse_amount(params.get("valorMax")) if params.get("valorMax") else None,
            )
            return _response(200, {"referenceDate": reference_date.strftime("%d-%m-%Y"), **indicators})

        if path == "/dashboard/breakdowns":
            reference_date = parse_reference_date(params.get("referenceDate"))
            if not reference_date:
                return _response(400, {"error": "Missing or invalid query param: referenceDate (DD-MM-AAAA)"})

            date_from, date_to = resolve_period_range(
                reference_date=reference_date,
                from_param=params.get("from"),
                to_param=params.get("to"),
                month_param=params.get("month") or params.get("mes"),
                period_param=params.get("period"),
            )

            if (params.get("from") and not date_from) or (params.get("to") and not date_to):
                return _response(400, {"error": "Invalid date format for from/to (use DD-MM-AAAA)"})

            if params.get("month") and not date_from:
                return _response(400, {"error": "Invalid month format (use YYYY-MM)"})

            if params.get("period") and not date_from:
                return _response(400, {"error": "Invalid period (use month|quarter|year)"})

            months = 12
            if params.get("months"):
                try:
                    months = max(1, min(36, int(params.get("months"))))
                except ValueError:
                    return _response(400, {"error": "Invalid months param (use integer 1-36)"})

            documents = get_documents(force_refresh=force_refresh)
            breakdowns = build_breakdowns(
                documents,
                reference_date=reference_date,
                date_from=date_from,
                date_to=date_to,
                empresa=params.get("empresa"),
                categoria=params.get("categoria"),
                texto=params.get("texto"),
                valor_min=parse_amount(params.get("valorMin")) if params.get("valorMin") else None,
                valor_max=parse_amount(params.get("valorMax")) if params.get("valorMax") else None,
                months=months,
            )
            return _response(200, {"referenceDate": reference_date.strftime("%d-%m-%Y"), **breakdowns})

        if path == "/filters/options":
            reference_date = parse_reference_date(params.get("referenceDate"))
            date_from, date_to = resolve_period_range(
                reference_date=reference_date,
                from_param=params.get("from"),
                to_param=params.get("to"),
                month_param=params.get("month") or params.get("mes"),
                period_param=params.get("period"),
            )
            if (params.get("from") and not date_from) or (params.get("to") and not date_to):
                return _response(400, {"error": "Invalid date format for from/to (use DD-MM-AAAA)"})

            if params.get("month") and not date_from:
                return _response(400, {"error": "Invalid month format (use YYYY-MM)"})

            if params.get("period") and not date_from:
                return _response(400, {"error": "Invalid period (use month|quarter|year)"})

            documents = get_documents(force_refresh=force_refresh)
            options = build_filter_options(documents, date_from=date_from, date_to=date_to)
            return _response(200, options)

        if path == "/download":
            file_key = params.get("file") or params.get("key")
            if not file_key:
                return _response(400, {"error": "Missing required query param: file"})

            url = create_presigned_url(file_key)
            return _response(200, {"url": url, "expiresIn": 300})

        return _response(404, {"error": "Not found"})
    except Exception as exc:  # noqa: BLE001 - return controlled error
        return _response(500, {"error": "Internal server error", "details": str(exc)})

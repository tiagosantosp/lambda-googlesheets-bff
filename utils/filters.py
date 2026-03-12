import re
from datetime import date, datetime
from typing import Dict, List, Optional


def _normalize_str(value: str) -> str:
    return str(value).strip().lower()


def parse_amount(value) -> float:
    if value is None:
        return 0.0
    text = str(value).strip()
    if not text:
        return 0.0

    cleaned = re.sub(r"[^0-9,.\-]", "", text)
    if re.search(r",\d{1,2}$", cleaned):
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif re.search(r"\.\d{1,2}$", cleaned):
        cleaned = cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(".", "").replace(",", "")

    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_amount(value) -> float:
    # Backwards-compatible alias
    return parse_amount(value)


def parse_date(value: str) -> Optional[date]:
    if not value:
        return None

    text = str(value).strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def month_key(value: str) -> str | None:
    parsed = parse_date(value)
    if parsed:
        return f"{parsed.year:04d}-{parsed.month:02d}"

    text = str(value).strip() if value else ""
    if len(text) >= 7:
        return text[:7]
    return None


def _month_key(value: str) -> str | None:
    if not value:
        return None

    return month_key(value)


def apply_filters(documents: List[Dict[str, str]], params: Dict[str, str]) -> List[Dict[str, str]]:
    empresa = _normalize_str(params.get("empresa", "")) if params else ""
    categoria = _normalize_str(params.get("categoria", "")) if params else ""
    mes = _normalize_str(params.get("mes", "")) if params else ""
    month_param = _normalize_str(params.get("month", "")) if params else ""
    texto = _normalize_str(params.get("texto", "")) if params else ""

    valor_min = parse_amount(params.get("valorMin")) if params and params.get("valorMin") else None
    valor_max = parse_amount(params.get("valorMax")) if params and params.get("valorMax") else None

    from_date = parse_date(params.get("from")) if params and params.get("from") else None
    to_date = parse_date(params.get("to")) if params and params.get("to") else None

    filtered = []
    for doc in documents:
        if empresa and _normalize_str(doc.get("empresa", "")) != empresa:
            continue
        if categoria and _normalize_str(doc.get("categoria", "")) != categoria:
            continue
        if texto and texto not in _normalize_str(doc.get("arquivo", "")):
            continue

        if valor_min is not None or valor_max is not None:
            valor = parse_amount(doc.get("valor", ""))
            if valor_min is not None and valor < valor_min:
                continue
            if valor_max is not None and valor > valor_max:
                continue

        if mes or month_param:
            month_key = _month_key(doc.get("data", ""))
            if not month_key:
                continue
            if mes and _normalize_str(month_key) != mes:
                continue
            if month_param and _normalize_str(month_key) != month_param:
                continue

        if from_date or to_date:
            doc_date = parse_date(doc.get("data", ""))
            if not doc_date:
                continue
            if from_date and doc_date < from_date:
                continue
            if to_date and doc_date > to_date:
                continue

        filtered.append(doc)

    return filtered


def build_stats(documents: List[Dict[str, str]]) -> Dict[str, object]:
    total_documentos = len(documents)
    valor_total_empresas: Dict[str, float] = {}
    valor_documentos_por_categoria: Dict[str, float] = {}
    valor_total_documentos_por_mes: Dict[str, float] = {}

    for doc in documents:
        empresa = doc.get("empresa", "") or "N/A"
        categoria = doc.get("categoria", "") or "N/A"
        month_key = _month_key(doc.get("data", "")) or "N/A"
        valor = _parse_amount(doc.get("valor", ""))

        valor_total_empresas[empresa] = valor_total_empresas.get(empresa, 0.0) + valor
        valor_documentos_por_categoria[categoria] = (
            valor_documentos_por_categoria.get(categoria, 0.0) + valor
        )
        valor_total_documentos_por_mes[month_key] = (
            valor_total_documentos_por_mes.get(month_key, 0.0) + valor
        )

    return {
        "totalDocumentos": total_documentos,
        "valortotalEmpresas": valor_total_empresas,
        "valordocumentosPorCategoria": valor_documentos_por_categoria,
        "valorTotaldocumentosPorMes": valor_total_documentos_por_mes,
    }

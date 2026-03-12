import re
from datetime import datetime
from typing import Dict, List


def _normalize_str(value: str) -> str:
    return str(value).strip().lower()


def _parse_amount(value) -> float:
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


def _month_key(value: str) -> str | None:
    if not value:
        return None

    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m")
        except ValueError:
            continue

    if len(text) >= 7:
        return text[:7]
    return None


def apply_filters(documents: List[Dict[str, str]], params: Dict[str, str]) -> List[Dict[str, str]]:
    empresa = _normalize_str(params.get("empresa", "")) if params else ""
    categoria = _normalize_str(params.get("categoria", "")) if params else ""
    mes = _normalize_str(params.get("mes", "")) if params else ""

    filtered = []
    for doc in documents:
        if empresa and _normalize_str(doc.get("empresa", "")) != empresa:
            continue
        if categoria and _normalize_str(doc.get("categoria", "")) != categoria:
            continue
        if mes:
            month_key = _month_key(doc.get("data", ""))
            if not month_key or _normalize_str(month_key) != mes:
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

from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, Iterable, List, Optional, Tuple

from utils.filters import parse_amount, parse_date


def _month_start(ref_date: date) -> date:
    return ref_date.replace(day=1)


def _month_end(ref_date: date) -> date:
    start = _month_start(ref_date)
    if start.month == 12:
        next_month = date(start.year + 1, 1, 1)
    else:
        next_month = date(start.year, start.month + 1, 1)
    return next_month - timedelta(days=1)


def _month_key_from_date(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def _month_index(value: date) -> int:
    return value.year * 12 + (value.month - 1)


def _year_month_from_index(index: int) -> Tuple[int, int]:
    year = index // 12
    month = (index % 12) + 1
    return year, month


def _months_back(reference: date, months: int) -> List[str]:
    end_index = _month_index(reference)
    start_index = end_index - (months - 1)
    result = []
    for idx in range(start_index, end_index + 1):
        year, month = _year_month_from_index(idx)
        result.append(f"{year:04d}-{month:02d}")
    return result


def _months_between(start: date, end: date) -> List[str]:
    start_index = _month_index(start)
    end_index = _month_index(end)
    result = []
    for idx in range(start_index, end_index + 1):
        year, month = _year_month_from_index(idx)
        result.append(f"{year:04d}-{month:02d}")
    return result


def _round_money(value: float) -> float:
    return round(value, 2)


def _round_pct(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value, 2)


def _filter_documents(
    documents: List[Dict[str, str]],
    *,
    empresa: Optional[str] = None,
    categoria: Optional[str] = None,
    texto: Optional[str] = None,
    valor_min: Optional[float] = None,
    valor_max: Optional[float] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> List[Dict[str, str]]:
    def _norm(text: Optional[str]) -> str:
        return str(text or "").strip().lower()

    empresa = _norm(empresa) if empresa else ""
    categoria = _norm(categoria) if categoria else ""
    texto = _norm(texto) if texto else ""

    filtered: List[Dict[str, str]] = []
    for doc in documents:
        if empresa and _norm(doc.get("empresa", "")) != empresa:
            continue
        if categoria and _norm(doc.get("categoria", "")) != categoria:
            continue
        if texto and texto not in _norm(doc.get("arquivo", "")):
            continue

        valor = parse_amount(doc.get("valor", ""))
        if valor_min is not None and valor < valor_min:
            continue
        if valor_max is not None and valor > valor_max:
            continue

        if date_from or date_to:
            doc_date = parse_date(doc.get("data", ""))
            if not doc_date:
                continue
            if date_from and doc_date < date_from:
                continue
            if date_to and doc_date > date_to:
                continue

        filtered.append(doc)

    return filtered


def parse_reference_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return parse_date(value)


def resolve_period_range(
    *,
    reference_date: Optional[date],
    from_param: Optional[str],
    to_param: Optional[str],
    month_param: Optional[str],
    period_param: Optional[str],
) -> Tuple[Optional[date], Optional[date]]:
    if from_param or to_param:
        return parse_date(from_param), parse_date(to_param)

    if month_param:
        parts = month_param.split("-")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            year = int(parts[0])
            month = int(parts[1])
            if 1 <= month <= 12:
                start = date(year, month, 1)
                return start, _month_end(start)

    if period_param and reference_date:
        period = period_param.strip().lower()
        if period == "month":
            start = _month_start(reference_date)
            return start, _month_end(reference_date)
        if period == "quarter":
            start_month = ((reference_date.month - 1) // 3) * 3 + 1
            start = date(reference_date.year, start_month, 1)
            end_month = start_month + 2
            end = _month_end(date(reference_date.year, end_month, 1))
            return start, end
        if period == "year":
            start = date(reference_date.year, 1, 1)
            end = date(reference_date.year, 12, 31)
            return start, end

    return None, None


def build_indicators(
    documents: List[Dict[str, str]],
    *,
    reference_date: date,
    empresa: Optional[str],
    categoria: Optional[str],
    texto: Optional[str],
    valor_min: Optional[float],
    valor_max: Optional[float],
) -> Dict[str, object]:
    filtered = _filter_documents(
        documents,
        empresa=empresa,
        categoria=categoria,
        texto=texto,
        valor_min=valor_min,
        valor_max=valor_max,
    )

    current_start = _month_start(reference_date)
    current_end = _month_end(reference_date)
    prev_end = current_start - timedelta(days=1)
    prev_start = _month_start(prev_end)

    total_current = 0.0
    total_prev = 0.0
    max_current = 0.0
    count_current = 0
    totals_by_month: Dict[str, float] = {}

    for doc in filtered:
        doc_date = parse_date(doc.get("data", ""))
        if not doc_date:
            continue
        valor = parse_amount(doc.get("valor", ""))
        month_key = _month_key_from_date(doc_date)
        totals_by_month[month_key] = totals_by_month.get(month_key, 0.0) + valor

        if current_start <= doc_date <= current_end:
            total_current += valor
            max_current = max(max_current, valor)
            count_current += 1
        elif prev_start <= doc_date <= prev_end:
            total_prev += valor

    def _average_for(months: int) -> float:
        keys = _months_back(reference_date, months)
        total = sum(totals_by_month.get(key, 0.0) for key in keys)
        return total / months if months else 0.0

    variation = None if total_prev == 0 else ((total_current - total_prev) / total_prev) * 100

    return {
        "period": {
            "from": current_start.strftime("%d-%m-%Y"),
            "to": current_end.strftime("%d-%m-%Y"),
        },
        "indicators": {
            "totalMesAtual": _round_money(total_current),
            "totalMesAnterior": _round_money(total_prev),
            "variacaoMesAnteriorPct": _round_pct(variation),
            "media3Meses": _round_money(_average_for(3)),
            "media6Meses": _round_money(_average_for(6)),
            "media12Meses": _round_money(_average_for(12)),
            "maiorGastoMes": _round_money(max_current),
            "quantidadeComprovantesMes": count_current,
        },
    }


def build_breakdowns(
    documents: List[Dict[str, str]],
    *,
    reference_date: date,
    date_from: Optional[date],
    date_to: Optional[date],
    empresa: Optional[str],
    categoria: Optional[str],
    texto: Optional[str],
    valor_min: Optional[float],
    valor_max: Optional[float],
    months: int = 12,
) -> Dict[str, object]:
    filtered = _filter_documents(
        documents,
        empresa=empresa,
        categoria=categoria,
        texto=texto,
        valor_min=valor_min,
        valor_max=valor_max,
        date_from=date_from,
        date_to=date_to,
    )

    totals_by_categoria: Dict[str, float] = {}
    totals_by_empresa: Dict[str, float] = {}
    total_period = 0.0
    monthly_by_categoria: Dict[str, Dict[str, float]] = {}

    for doc in filtered:
        categoria_nome = doc.get("categoria", "") or "OUTROS"
        empresa_nome = doc.get("empresa", "") or "N/A"
        doc_date = parse_date(doc.get("data", ""))
        if not doc_date:
            continue
        valor = parse_amount(doc.get("valor", ""))
        total_period += valor
        totals_by_categoria[categoria_nome] = totals_by_categoria.get(categoria_nome, 0.0) + valor
        totals_by_empresa[empresa_nome] = totals_by_empresa.get(empresa_nome, 0.0) + valor

        month_key = _month_key_from_date(doc_date)
        monthly_by_categoria.setdefault(categoria_nome, {})
        monthly_by_categoria[categoria_nome][month_key] = (
            monthly_by_categoria[categoria_nome].get(month_key, 0.0) + valor
        )

    por_categoria = [
        {"categoria": key, "valor": _round_money(value)}
        for key, value in sorted(
            totals_by_categoria.items(), key=lambda item: item[1], reverse=True
        )
    ]

    top_empresas = [
        {"empresa": key, "valor": _round_money(value)}
        for key, value in sorted(
            totals_by_empresa.items(), key=lambda item: item[1], reverse=True
        )[:5]
    ]

    participacao_categoria = []
    for key, value in sorted(
        totals_by_categoria.items(), key=lambda item: item[1], reverse=True
    ):
        pct = 0.0 if total_period == 0 else (value / total_period) * 100
        participacao_categoria.append({"categoria": key, "pct": _round_pct(pct)})

    if date_from and date_to:
        months_range = _months_between(date_from, date_to)
    else:
        months_range = _months_back(reference_date, months)

    evolucao_mensal = []
    for categoria_nome, month_map in monthly_by_categoria.items():
        series = [{"mes": key, "valor": _round_money(month_map.get(key, 0.0))} for key in months_range]
        total_cat = sum(month_map.get(key, 0.0) for key in months_range)
        evolucao_mensal.append((total_cat, {"categoria": categoria_nome, "series": series}))

    evolucao_mensal_sorted = [item[1] for item in sorted(evolucao_mensal, key=lambda x: x[0], reverse=True)]

    current_start = _month_start(reference_date)
    current_end = _month_end(reference_date)
    prev_end = current_start - timedelta(days=1)
    prev_start = _month_start(prev_end)

    current_totals: Dict[str, float] = {}
    prev_totals: Dict[str, float] = {}

    for doc in _filter_documents(
        documents,
        empresa=empresa,
        categoria=categoria,
        texto=texto,
        valor_min=valor_min,
        valor_max=valor_max,
        date_from=prev_start,
        date_to=current_end,
    ):
        doc_date = parse_date(doc.get("data", ""))
        if not doc_date:
            continue
        valor = parse_amount(doc.get("valor", ""))
        categoria_nome = doc.get("categoria", "") or "OUTROS"
        if current_start <= doc_date <= current_end:
            current_totals[categoria_nome] = current_totals.get(categoria_nome, 0.0) + valor
        elif prev_start <= doc_date <= prev_end:
            prev_totals[categoria_nome] = prev_totals.get(categoria_nome, 0.0) + valor

    comparativo = []
    categorias = set(current_totals.keys()) | set(prev_totals.keys())
    for cat in sorted(categorias):
        valor_atual = current_totals.get(cat, 0.0)
        valor_anterior = prev_totals.get(cat, 0.0)
        variacao = None if valor_anterior == 0 else ((valor_atual - valor_anterior) / valor_anterior) * 100
        comparativo.append(
            {
                "categoria": cat,
                "valorMesAtual": _round_money(valor_atual),
                "valorMesAnterior": _round_money(valor_anterior),
                "variacaoPct": _round_pct(variacao),
            }
        )

    return {
        "period": {
            "from": date_from.strftime("%d-%m-%Y") if date_from else None,
            "to": date_to.strftime("%d-%m-%Y") if date_to else None,
        },
        "breakdowns": {
            "porCategoria": por_categoria,
            "evolucaoMensalPorCategoria": evolucao_mensal_sorted,
            "topEmpresas": top_empresas,
            "participacaoCategoriaPct": participacao_categoria,
            "comparativoMesAtualVsAnteriorPorCategoria": comparativo,
        },
    }


def build_filter_options(
    documents: List[Dict[str, str]],
    *,
    date_from: Optional[date],
    date_to: Optional[date],
) -> Dict[str, object]:
    filtered = _filter_documents(documents, date_from=date_from, date_to=date_to)

    categorias = sorted({(doc.get("categoria", "") or "OUTROS") for doc in filtered})
    empresas = sorted({(doc.get("empresa", "") or "N/A") for doc in filtered})

    meses = set()
    valores: List[float] = []
    for doc in filtered:
        doc_date = parse_date(doc.get("data", ""))
        if doc_date:
            meses.add(_month_key_from_date(doc_date))
        valores.append(parse_amount(doc.get("valor", "")))

    valor_min = min(valores) if valores else 0.0
    valor_max = max(valores) if valores else 0.0

    return {
        "categorias": categorias,
        "empresas": empresas,
        "mesesDisponiveis": sorted(meses),
        "valorMin": _round_money(valor_min),
        "valorMax": _round_money(valor_max),
    }

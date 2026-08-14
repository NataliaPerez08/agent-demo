import re

import sqlglot
from sqlglot import exp


def extract_tables(sql: str) -> set[str]:
    """Tablas referenciadas en el SQL (sin esquema, sin CTEs internos)."""

    try:
        parsed = sqlglot.parse_one(sql, read="postgres")
    except Exception:
        return set()

    cte_names = {c.alias_or_name for c in parsed.find_all(exp.CTE)}

    tables = set()
    for node in parsed.find_all(exp.Table):
        name = node.name
        if name and name not in cte_names:
            tables.add(name)

    return tables


def check_metric(sql: str, expected_metric: str) -> bool:
    """True si el SQL contiene la metrica esperada (normalizada)."""

    if not expected_metric:
        return True

    norm_sql = re.sub(r"\s+", "", sql.lower())
    norm_metric = re.sub(r"\s+", "", expected_metric.lower())
    return norm_metric in norm_sql


def check_filters(sql: str, expected_filters: dict) -> tuple[bool, list[str]]:
    """True si todos los filtros esperados estan presentes en el SQL.

    Para cada clave se busca el valor en el SQL. status se busca como
    literal de string (p. ej. 'completed'); meses como numero o palabra.
    """

    if not expected_filters:
        return True, []

    lowered = sql.lower()
    missing = []

    for key, value in expected_filters.items():

        if key == "status":
            ok = str(value).lower() in lowered
        elif key == "month":
            value_str = str(value).lower()
            ok = value_str in lowered or (
                {
                    "1": ["enero", "jan", "january"],
                    "2": ["febrero", "feb", "february"],
                    "3": ["marzo", "mar", "march"],
                    "4": ["abril", "apr", "april"],
                    "5": ["mayo", "may"],
                    "6": ["junio", "jun", "june"],
                    "7": ["julio", "jul", "july"],
                    "8": ["agosto", "aug", "august"],
                    "9": ["septiembre", "sep", "september"],
                    "10": ["octubre", "oct", "october"],
                    "11": ["noviembre", "nov", "november"],
                    "12": ["diciembre", "dec", "december"],
                }
                .get(value_str, [])
                and any(
                    alias in lowered
                    for alias in {
                        "1": ["enero", "jan", "january"],
                        "2": ["febrero", "feb", "february"],
                        "3": ["marzo", "mar", "march"],
                        "4": ["abril", "apr", "april"],
                        "5": ["mayo", "may"],
                        "6": ["junio", "jun", "june"],
                        "7": ["julio", "jul", "july"],
                        "8": ["agosto", "aug", "august"],
                        "9": ["septiembre", "sep", "september"],
                        "10": ["octubre", "oct", "october"],
                        "11": ["noviembre", "nov", "november"],
                        "12": ["diciembre", "dec", "december"],
                    }.get(value_str, [])
                )
            )
        else:
            ok = str(value).lower() in lowered

        if not ok:
            missing.append(f"{key}={value}")

    return not missing, missing


def compare_result(query_result: list, expected_result) -> tuple[bool, float | None]:
    """Compara el resultado numerico esperado con el primer escalar devuelto.

    Tolerancia 1% o 0.01. expected_result None -> siempre True (skip).
    """

    if expected_result is None:
        return True, None

    if not query_result:
        return False, None

    first = query_result[0]
    value = None
    if isinstance(first, dict):
        value = next(iter(first.values()))
    else:
        value = first

    if value is None:
        return False, None

    try:
        actual = float(value)
    except (TypeError, ValueError):
        return False, None

    expected = float(expected_result)
    tol = max(abs(expected) * 0.01, 0.01)
    return abs(actual - expected) <= tol, actual


def check_answer(answer: str, expected_contains: str) -> bool:
    """True si el texto esperado aparece en la respuesta final."""

    if not expected_contains:
        return True
    return expected_contains.lower() in (answer or "").lower()
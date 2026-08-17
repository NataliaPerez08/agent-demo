import datetime


def _is_numeric(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_temporal(value) -> bool:
    return isinstance(value, (datetime.date, datetime.datetime))


def _classify_columns(rows: list[dict]) -> tuple[list[str], list[str], list[str]]:
    """Devuelve (numeric_cols, temporal_cols, categorical_cols)."""

    if not rows:
        return [], [], []

    columns = list(rows[0].keys())
    numeric = []
    temporal = []
    categorical = []

    for col in columns:

        values = [r.get(col) for r in rows if r.get(col) is not None]

        if not values:
            categorical.append(col)
            continue

        if all(_is_numeric(v) for v in values):
            numeric.append(col)
        elif all(_is_temporal(v) for v in values):
            temporal.append(col)
        else:
            categorical.append(col)

    return numeric, temporal, categorical


def _looks_like_id(col: str) -> bool:
    """True si el nombre de columna sugiere un identificador (no metrica)."""

    name = col.lower()
    return name == "id" or name.endswith("_id")


def suggest_chart(rows: list[dict], question: str = "") -> dict | None:
    """Sugiere una configuracion de grafica a partir de los resultados.

    Heuristica:
      - 0 filas               -> None
      - eje temporal + 1 num  -> line
      - 1 categoria + 1 num   -> bar (top 8) o pie si pocas filas
      - 1 categoria + N nums  -> bar agrupado
      - 1 num                 -> bar
      - resto                 -> None (tabla)
    """

    if not rows:
        return None

    numeric, temporal, categorical = _classify_columns(rows)
    numeric = [c for c in numeric if not _looks_like_id(c)]
    columns = list(rows[0].keys())
    n = len(rows)

    title = (question or "Resultados").strip()
    if len(title) > 80:
        title = title[:77] + "..."

    if temporal and numeric:
        x = temporal[0]
        y = numeric[0]
        series = categorical[0] if categorical else None
        return {
            "type": "line",
            "title": title,
            "x": x,
            "y": y,
            "series": [series] if series else None,
            "columns": columns,
        }

    if categorical and numeric:
        x = categorical[0]
        y = numeric[0]
        if n <= 6 and len(numeric) == 1:
            return {
                "type": "pie",
                "title": title,
                "x": x,
                "y": y,
                "series": None,
                "columns": columns,
            }
        return {
            "type": "bar",
            "title": title,
            "x": x,
            "y": y,
            "series": numeric[1:] if len(numeric) > 1 else None,
            "columns": columns,
        }

    if numeric and len(columns) == 1:
        return {
            "type": "bar",
            "title": title,
            "x": None,
            "y": numeric[0],
            "series": None,
            "columns": columns,
        }

    if numeric and categorical:
        return {
            "type": "bar",
            "title": title,
            "x": categorical[0],
            "y": numeric[0],
            "series": None,
            "columns": columns,
        }

    return None
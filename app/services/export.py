import csv
import io

import pandas as pd


def rows_to_csv(rows: list[dict]) -> str:
    """Convierte una lista de dicts (filas) en CSV como string."""

    if not rows:
        return ""

    buffer = io.StringIO()

    fieldnames = list(rows[0].keys())

    writer = csv.DictWriter(buffer, fieldnames=fieldnames)

    writer.writeheader()

    for row in rows:
        writer.writerow(row)

    return buffer.getvalue()


def rows_to_excel(rows: list[dict]) -> bytes:
    """Convierte una lista de dicts (filas) en un XLSX como bytes."""

    df = pd.DataFrame(rows)

    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="results")

    return buffer.getvalue()
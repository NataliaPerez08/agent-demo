import datetime
import io

import pandas as pd

from app.services.charts import suggest_chart
from app.services.export import rows_to_csv, rows_to_excel


def test_csv_empty():
    assert rows_to_csv([]) == ""


def test_csv_basic():
    rows = [
        {"name": "Acme", "revenue": 6000},
        {"name": "Globex", "revenue": 3000},
    ]
    csv = rows_to_csv(rows)
    assert "name,revenue" in csv
    assert "Acme,6000" in csv
    assert "Globex,3000" in csv


def test_csv_all_columns_present():
    rows = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    csv = rows_to_csv(rows)
    assert csv.startswith("a,b")


def test_xlsx_basic():
    rows = [{"name": "Acme", "revenue": 6000}, {"name": "Globex", "revenue": 3000}]
    data = rows_to_excel(rows)
    assert isinstance(data, bytes) and len(data) > 0
    df = pd.read_excel(io.BytesIO(data), sheet_name="results")
    assert list(df.columns) == ["name", "revenue"]
    assert len(df) == 2
    assert df.iloc[0]["name"] == "Acme"
    assert int(df.iloc[0]["revenue"]) == 6000


def test_xlsx_empty_rows():
    data = rows_to_excel([])
    assert isinstance(data, bytes)


def test_chart_none_empty():
    assert suggest_chart([], "x") is None


def test_chart_bar_category_numeric():
    rows = [
        {"name": "Acme", "revenue": 6000},
        {"name": "Globex", "revenue": 3000},
        {"name": "Initech", "revenue": 1800},
        {"name": "Umbrella", "revenue": 8800},
        {"name": "Stark", "revenue": 12000},
        {"name": "Wayne", "revenue": 5000},
        {"name": "Soylent", "revenue": 1300},
        {"name": "Hooli", "revenue": 2800},
    ]
    chart = suggest_chart(rows, "Top clientes")
    assert chart["type"] == "bar"
    assert chart["x"] == "name"
    assert chart["y"] == "revenue"
    assert chart["title"] == "Top clientes"


def test_chart_pie_few_rows():
    rows = [
        {"country": "Mexico", "revenue": 30000},
        {"country": "USA", "revenue": 20000},
        {"country": "Colombia", "revenue": 10000},
    ]
    chart = suggest_chart(rows, "revenue por pais")
    assert chart["type"] == "pie"
    assert chart["x"] == "country"
    assert chart["y"] == "revenue"


def test_chart_line_temporal():
    rows = [
        {"month": datetime.date(2026, 6, 1), "revenue": 30000},
        {"month": datetime.date(2026, 7, 1), "revenue": 52500},
    ]
    chart = suggest_chart(rows, "revenue por mes")
    assert chart["type"] == "line"
    assert chart["x"] == "month"
    assert chart["y"] == "revenue"


def test_chart_long_title_truncated():
    long_q = "¿Cual fue el revenue total consolidado considerando todos los paises y segmentos durante el ultimo trimestre?"
    rows = [{"name": "A", "revenue": 1}]
    chart = suggest_chart(rows, long_q)
    assert len(chart["title"]) <= 80
    assert chart["title"].endswith("...")


def test_chart_none_when_no_pattern():
    rows = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
    chart = suggest_chart(rows, "x")
    assert chart is None
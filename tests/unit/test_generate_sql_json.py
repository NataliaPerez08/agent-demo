"""Tests del parser JSON estructurado de generate_sql y fix_sql.

Probado sin LLM: se mockea ainvoke_with_usage.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest


def test_parse_json_pure():
    from app.nodes.generate_sql import _parse_json_response

    raw = '{"can_answer": true, "sql": "SELECT 1", "reason": null}'
    result = _parse_json_response(raw)

    assert result["can_answer"] is True
    assert result["sql"] == "SELECT 1"
    assert result["reason"] is None


def test_parse_json_markdown_wrapped():
    from app.nodes.generate_sql import _parse_json_response

    raw = '```json\n{"can_answer": true, "sql": "SELECT 1", "reason": null}\n```'
    result = _parse_json_response(raw)

    assert result["can_answer"] is True
    assert result["sql"] == "SELECT 1"


def test_parse_json_with_surrounding_text():
    from app.nodes.generate_sql import _parse_json_response

    raw = 'Aqui esta el resultado:\n{"can_answer": false, "sql": null, "reason": "No hay datos"}\nEspero que sirva.'
    result = _parse_json_response(raw)

    assert result["can_answer"] is False
    assert result["sql"] is None
    assert "No hay datos" in result["reason"]


def test_parse_json_fallback_to_raw_sql():
    from app.nodes.generate_sql import _parse_json_response

    raw = "SELECT 1 FROM customers"
    result = _parse_json_response(raw)

    assert result["can_answer"] is True
    assert "SELECT 1" in result["sql"]


def test_parse_json_empty():
    from app.nodes.generate_sql import _parse_json_response

    result = _parse_json_response("")

    assert result["can_answer"] is True
    assert result["sql"] == ""


@pytest.mark.asyncio
async def test_generate_sql_can_answer():
    from app.nodes.generate_sql import generate_sql

    fake_response = json.dumps({
        "can_answer": True,
        "sql": "SELECT SUM(total) FROM orders WHERE status = 'completed'",
        "reason": None,
    })

    with patch("app.nodes.generate_sql.ainvoke_with_usage", new_callable=AsyncMock) as mock:
        mock.return_value = fake_response
        result = await generate_sql({"schema_context": "TABLE orders", "question": "revenue?"})

    assert "SELECT SUM(total)" in result["generated_sql"]
    assert result["generated_sql"] != "CANNOT_ANSWER"


@pytest.mark.asyncio
async def test_generate_sql_cannot_answer():
    from app.nodes.generate_sql import generate_sql

    fake_response = json.dumps({
        "can_answer": False,
        "sql": None,
        "reason": "El esquema no contiene datos de RRHH",
    })

    with patch("app.nodes.generate_sql.ainvoke_with_usage", new_callable=AsyncMock) as mock:
        mock.return_value = fake_response
        result = await generate_sql({"schema_context": "", "question": "salarios?"})

    assert result["generated_sql"] == "CANNOT_ANSWER"


@pytest.mark.asyncio
async def test_generate_sql_markdown_sql_in_json():
    from app.nodes.generate_sql import generate_sql

    fake_response = json.dumps({
        "can_answer": True,
        "sql": "```sql\nSELECT 1\n```",
        "reason": None,
    })

    with patch("app.nodes.generate_sql.ainvoke_with_usage", new_callable=AsyncMock) as mock:
        mock.return_value = fake_response
        result = await generate_sql({"schema_context": "", "question": "x"})

    assert "```" not in result["generated_sql"]
    assert "SELECT 1" in result["generated_sql"]


@pytest.mark.asyncio
async def test_fix_sql_can_answer():
    from app.nodes.fix_sql import fix_sql

    fake_response = json.dumps({
        "can_answer": True,
        "sql": "SELECT corrected FROM customers",
        "reason": None,
    })

    with patch("app.nodes.fix_sql.ainvoke_with_usage", new_callable=AsyncMock) as mock:
        mock.return_value = fake_response
        result = await fix_sql({
            "question": "x",
            "schema_context": "",
            "generated_sql": "SELECT bad FROM customers",
            "validation_error": "column bad does not exist",
            "retry_count": 0,
        })

    assert "SELECT corrected" in result["generated_sql"]
    assert result["retry_count"] == 1


@pytest.mark.asyncio
async def test_fix_sql_cannot_answer():
    from app.nodes.fix_sql import fix_sql

    fake_response = json.dumps({
        "can_answer": False,
        "sql": None,
        "reason": "Imposible corregir",
    })

    with patch("app.nodes.fix_sql.ainvoke_with_usage", new_callable=AsyncMock) as mock:
        mock.return_value = fake_response
        result = await fix_sql({
            "question": "x",
            "schema_context": "",
            "generated_sql": "SELECT bad",
            "validation_error": "error",
            "retry_count": 1,
        })

    assert result["generated_sql"] == "CANNOT_ANSWER"
    assert result["retry_count"] == 2
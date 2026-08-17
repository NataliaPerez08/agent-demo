"""Tests del data_dictionary.yaml: metricas y estructura."""

import pytest
import yaml
from pathlib import Path


DICT_PATH = (
    Path(__file__).resolve().parents[2]
    / "database"
    / "analytics"
    / "model"
    / "data_dictionary.yaml"
)


@pytest.fixture
def dictionary():
    with open(DICT_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_dictionary_loads(dictionary):
    assert "business_rules" in dictionary
    assert "tables" in dictionary


def test_required_metrics_present(dictionary):
    rules = dictionary["business_rules"]

    required = ["revenue", "average_order_value", "active_customer", "new_customers", "units_sold", "product_revenue"]

    for name in required:
        assert name in rules, f"Metrica faltante: {name}"
        assert "description" in rules[name], f"Metrica {name} sin descripcion"


def test_revenue_filter_completed(dictionary):
    rules = dictionary["business_rules"]
    assert rules["revenue"].get("filter", {}).get("status") == "completed"


def test_units_sold_mentions_completed(dictionary):
    desc = dictionary["business_rules"]["units_sold"]["description"]
    assert "completed" in desc.lower()


def test_product_revenue_mentions_completed(dictionary):
    desc = dictionary["business_rules"]["product_revenue"]["description"]
    assert "completed" in desc.lower()


def test_new_customers_based_on_created_at(dictionary):
    desc = dictionary["business_rules"]["new_customers"]["description"]
    assert "created_at" in desc.lower()


def test_tables_have_primary_keys(dictionary):
    tables = dictionary["tables"]

    for tname, spec in tables.items():
        pk = spec.get("primary_key")
        assert pk is not None, f"Tabla {tname} sin primary_key"
        assert len(pk) > 0, f"Tabla {tname} con primary_key vacio"


def test_expected_tables_present(dictionary):
    tables = dictionary["tables"]
    expected = {"customers", "orders", "products", "order_items"}

    assert expected.issubset(set(tables.keys()))


def test_orders_has_relationships(dictionary):
    orders = dictionary["tables"]["orders"]
    assert "relationships" in orders
    assert "customer_id" in orders["relationships"]
    assert orders["relationships"]["customer_id"]["references"] == "customers.id"


def test_order_items_has_relationships(dictionary):
    items = dictionary["tables"]["order_items"]
    assert "relationships" in items
    assert "order_id" in items["relationships"]
    assert "product_id" in items["relationships"]
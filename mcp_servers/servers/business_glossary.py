"""Servidor MCP que expone el data_dictionary.yaml y las business rules
como recursos MCP (streamable HTTP en /mcp).

Recursos expuestos:
  glossary://database            -> descripcion general de la base
  glossary://metrics/{name}      -> definicion de una metrica/business rule
  glossary://tables/{name}       -> descripcion semantica de una tabla
  glossary://tables              -> listado de tablas con su descripcion

El cliente (agente LangGraph) puede leer estos recursos para enriquecer
el schema_context con significado empresarial versionado y separable
del codigo del agente.
"""

from pathlib import Path

import yaml
from mcp.server.fastmcp import FastMCP

DICT_PATH = (
    Path(__file__).resolve().parents[2]
    / "database"
    / "analytics"
    / "model"
    / "data_dictionary.yaml"
)


def _load_dictionary() -> dict:
    with open(DICT_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def create_server() -> FastMCP:
    """Construye el FastMCP server con los recursos del glossary."""

    mcp = FastMCP(
        "business-glossary",
        instructions=(
            "Servidor MCP con el glosario semantico del data analyst agent. "
            "Expone metricas (business rules) y descripciones de tablas "
            "como recursos MCP. Pensado para enriquecer el contexto del "
            "agente con significado empresarial."
        ),
        host="0.0.0.0",
        port=8100,
    )

    @mcp.resource("glossary://database")
    def database_overview() -> str:
        """Descripcion general de la base analitica."""

        data = _load_dictionary()
        db = data.get("database", {})
        name = db.get("name", "analytics")
        desc = db.get("description", "").strip()
        return f"Base: {name}\nDescripcion: {desc}"

    @mcp.resource("glossary://metrics")
    def list_metrics() -> str:
        """Lista todas las metricas/business rules disponibles."""

        data = _load_dictionary()
        rules = data.get("business_rules", {})
        lines = ["Metricas disponibles:"]
        for name, spec in rules.items():
            desc = str(spec.get("description", "")).strip().replace("\n", " ")
            lines.append(f"- {name}: {desc}")
        return "\n".join(lines)

    @mcp.resource("glossary://metrics/{name}")
    def get_metric(name: str) -> str:
        """Definicion completa de una metrica/business rule por nombre."""

        data = _load_dictionary()
        rules = data.get("business_rules", {})
        if name not in rules:
            return f"Metrica '{name}' no encontrada."
        return yaml.safe_dump({name: rules[name]}, allow_unicode=True, sort_keys=False)

    @mcp.resource("glossary://tables")
    def list_tables() -> str:
        """Lista todas las tablas con su descripcion semantica."""

        data = _load_dictionary()
        tables = data.get("tables", {})
        lines = ["Tablas disponibles:"]
        for tname, spec in tables.items():
            desc = str(spec.get("description", "")).strip().replace("\n", " ")
            lines.append(f"- {tname}: {desc}")
        return "\n".join(lines)

    @mcp.resource("glossary://tables/{name}")
    def get_table(name: str) -> str:
        """Descripcion semantica completa de una tabla: columnas, PK, relaciones."""

        data = _load_dictionary()
        tables = data.get("tables", {})
        if name not in tables:
            return f"Tabla '{name}' no encontrada en el glosario."
        return yaml.safe_dump(
            {name: tables[name]}, allow_unicode=True, sort_keys=False
        )

    return mcp


# Instancia lista para `mcp run` o montar como ASGI.
mcp = create_server()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
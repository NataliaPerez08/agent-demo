"""Servidor MCP con tools para explorar la analytics DB read-only.

Tools expuestos:
  list_tables()              -> lista de tablas y views del schema public
  describe_table(table)      -> columnas, tipos y nullability de una tabla
  sample_table(table, n)     -> n filas de muestra de una tabla

Conecta a la analytics DB con el rol read-only analyst_agent y aplica
LIMIT + statement_timeout defensivos. Pensado para ser consumido por
el agente LangGraph (y otros clientes MCP) como complemento al
retrieval de schema.
"""

from mcp.server.fastmcp import FastMCP
from psycopg_pool import AsyncConnectionPool

from app.config import settings

SAMPLE_LIMIT = 20
STATEMENT_TIMEOUT_MS = 5000


def _pool() -> AsyncConnectionPool:
    """Pool read-only contra la analytics DB (creado bajo demanda)."""
    return AsyncConnectionPool(
        conninfo=settings.analytics_database_url,
        open=False,
        min_size=1,
        max_size=3,
    )


def create_server() -> FastMCP:
    """Construye el FastMCP server con tools de exploracion."""

    mcp = FastMCP(
        "analytics-explorer",
        instructions=(
            "Servidor MCP con tools para explorar la base analitica "
            "read-only (rol analyst_agent). Permite listar tablas, "
            "describir su estructura y muestrear filas. Pensado para "
            "clientes MCP (incluido el agente LangGraph)."
        ),
        host="0.0.0.0",
        port=8101,
    )

    @mcp.tool()
    async def list_tables() -> str:
        """Lista las tablas y views del schema public de la analytics DB."""

        pool = _pool()
        await pool.open()
        try:
            async with pool.connection() as conn, conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT table_name, table_type
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                    """
                )
                rows = await cur.fetchall()
        finally:
            await pool.close()

        if not rows:
            return "No se encontraron tablas."
        lines = ["Tablas (nombre, tipo):"]
        for name, ttype in rows:
            lines.append(f"- {name} ({ttype})")
        return "\n".join(lines)

    @mcp.tool()
    async def describe_table(table: str) -> str:
        """Describe columnas, tipos y nullability de una tabla o view."""

        pool = _pool()
        await pool.open()
        try:
            async with pool.connection() as conn, conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (table,),
                )
                rows = await cur.fetchall()
        finally:
            await pool.close()

        if not rows:
            return f"Tabla '{table}' no encontrada."
        lines = [f"Tabla {table} (columna, tipo, nullable):"]
        for col, dtype, nullable in rows:
            lines.append(f"- {col} {dtype} nullable={nullable}")
        return "\n".join(lines)

    @mcp.tool()
    async def sample_table(table: str, n: int = 5) -> str:
        """Devuelve hasta n filas (max 20) de muestreo de una tabla.

        Aplica LIMIT defensivo y statement_timeout.
        """

        n = max(1, min(int(n), SAMPLE_LIMIT))
        pool = _pool()
        await pool.open()
        try:
            async with pool.connection() as conn, conn.cursor() as cur:
                await cur.execute(
                    f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}"
                )
                await cur.execute(
                    'SELECT * FROM "{}" LIMIT {}'.format(table.replace('"', ""), n)
                )
                cols = [d[0] for d in cur.description]
                rows = await cur.fetchall()
        finally:
            await pool.close()

        if not rows:
            return f"Tabla '{table}' sin filas o no accesible."
        lines = ["\t".join(cols)]
        for row in rows:
            lines.append("\t".join(str(v) for v in row))
        return "\n".join(lines)

    return mcp


mcp = create_server()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
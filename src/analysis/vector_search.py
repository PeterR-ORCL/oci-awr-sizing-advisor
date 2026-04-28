from __future__ import annotations

from typing import Any


def execute_query(
    connection: Any,
    sql: str,
    **bindings: Any,
) -> list[dict[str, Any]]:
    """Execute a SQL query and return rows as dictionaries."""

    with connection.cursor() as cursor:
        cursor.execute(sql, bindings)
        rows = cursor.fetchall()
        description = getattr(cursor, "description", None) or []
        column_names = [column[0].lower() for column in description]
    return [dict(zip(column_names, row, strict=True)) for row in rows]


def find_similar_awrs_exact(
    connection: Any,
    query_vector: list[float],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Exact similarity search using VECTOR_DISTANCE.
    """

    sql = """
        SELECT
            awr_id,
            VECTOR_DISTANCE(FEATURE_VECTOR, :query_vector, COSINE) AS distance
        FROM AWR_FEATURE_VECTOR
        ORDER BY distance
        FETCH FIRST :top_k ROWS ONLY
    """

    return execute_query(
        connection,
        sql,
        query_vector=query_vector,
        top_k=top_k,
    )


def find_similar_awrs_approx(
    connection: Any,
    query_vector: list[float],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Fast similarity search using HNSW index.
    """

    sql = """
        SELECT
            awr_id,
            VECTOR_DISTANCE(FEATURE_VECTOR, :query_vector, COSINE) AS distance
        FROM AWR_FEATURE_VECTOR
        ORDER BY distance
        FETCH APPROXIMATE FIRST :top_k ROWS ONLY
    """

    return execute_query(
        connection,
        sql,
        query_vector=query_vector,
        top_k=top_k,
    )

from __future__ import annotations

from urllib.parse import quote

import httpx

from app.core.config import get_settings


class OpenMetadataClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _base_url(self) -> str:
        if not self.settings.openmetadata_url:
            raise ValueError("OPENMETADATA_URL is required")
        return self.settings.openmetadata_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.settings.openmetadata_token:
            headers["Authorization"] = f"Bearer {self.settings.openmetadata_token}"
        return headers

    async def fetch_tables(self) -> list[dict]:
        base = self._base_url()
        headers = self._headers()
        tables: list[dict] = []
        after: str | None = None

        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                params = {"limit": 100}
                if after:
                    params["after"] = after
                resp = await client.get(f"{base}/api/v1/tables", headers=headers, params=params)
                resp.raise_for_status()
                payload = resp.json()
                data = payload.get("data", [])
                tables.extend(data)
                after = (payload.get("paging") or {}).get("after")
                if not after:
                    break

        return tables

    async def fetch_lineage_for_table(self, table_id: str) -> list[dict]:
        base = self._base_url()
        headers = self._headers()
        url = f"{base}/api/v1/lineage/table/{quote(table_id, safe='')}"
        params = {"upstreamDepth": 1, "downstreamDepth": 1, "includeDeleted": "false"}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            payload = resp.json()

        edges = []
        for edge in payload.get("upstreamEdges", []) + payload.get("downstreamEdges", []):
            source_ref = edge.get("fromEntity") or {}
            target_ref = edge.get("toEntity") or {}
            source = source_ref.get("fullyQualifiedName") or source_ref.get("name")
            target = target_ref.get("fullyQualifiedName") or target_ref.get("name")
            if not source or not target:
                continue
            deleted = bool(source_ref.get("deleted") or target_ref.get("deleted"))
            edges.append(
                {
                    "source": source,
                    "target": target,
                    "is_active": not deleted,
                    "broken_reason": edge.get("description"),
                }
            )
        return edges

    async def fetch_schemas(self, tables: list[dict]) -> dict[str, list[dict]]:
        schemas: dict[str, list[dict]] = {}
        for table in tables:
            fqn = table.get("fullyQualifiedName")
            if not fqn:
                continue
            columns = table.get("columns") or []
            schemas[fqn] = [
                {
                    "name": col.get("name"),
                    "type": col.get("dataType") or col.get("dataTypeDisplay"),
                    "nullable": bool(col.get("constraint") != "NOT_NULL"),
                    "description": col.get("description"),
                }
                for col in columns
                if col.get("name")
            ]
        return schemas

    async def fetch_usage_stats(self, tables: list[dict]) -> dict[str, dict]:
        usage: dict[str, dict] = {}
        for table in tables:
            fqn = table.get("fullyQualifiedName")
            if not fqn:
                continue
            usage_summary = table.get("usageSummary") or {}
            usage[fqn] = {
                "weekly_queries": usage_summary.get("weeklyStats", {}).get("count") or 0,
                "daily_queries": usage_summary.get("dailyStats", {}).get("count") or 0,
                "last_accessed": usage_summary.get("date"),
                "percentile_rank": usage_summary.get("percentileRank"),
            }
        return usage

    async def fetch_normalized_metadata(self) -> list[dict]:
        tables = await self.fetch_tables()
        schemas = await self.fetch_schemas(tables)
        usage = await self.fetch_usage_stats(tables)

        normalized = []
        for table in tables:
            fqn = table.get("fullyQualifiedName")
            if not fqn:
                continue

            table_id = table.get("id")
            lineage = await self.fetch_lineage_for_table(str(table_id)) if table_id else []
            owners = table.get("owners") or []
            owner_name = owners[0].get("name") if owners else "unknown"

            normalized.append(
                {
                    "dataset": fqn,
                    "owner": owner_name,
                    "description": table.get("description", ""),
                    "schema": schemas.get(fqn, []),
                    "lineage": lineage,
                    "usage": usage.get(fqn, {}),
                }
            )
        return normalized

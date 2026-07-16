"""
WebSearchConnector — implements the Connector protocol over the Tavily
search API.

Unlike the two local connectors, this one talks to a paid, rate-limited,
external HTTP API — so a few things are handled differently on purpose:

  - The Tavily client is injectable (`client=`), same dependency-injection
    pattern used for manifest and for ChromaDB's client elsewhere. Tests
    inject a fake client with a canned .search() response rather than
    hitting the real API: it costs API credits, and the real Tavily
    endpoint isn't reachable from every sandbox/CI network (it wasn't
    reachable from the one this connector was built in).

  - health() only validates configuration (an api_key or injected client
    is present) rather than making a real search call on every health
    check — burning API quota on liveness checks is wasteful for a paid
    external service. Genuine reachability failures surface naturally
    through retrieve() and are handled by Phase 6's re-planning logic.

  - retrieve() lets network/auth errors from the Tavily SDK propagate
    rather than swallowing them. Phase 6 (per-connector timeouts, re-plan
    on failure) is where failure handling for external sources belongs;
    Phase 2's job is just a correct, honest wrapper.

This connector's manifest declares query_leaks_externally: true — the raw
query text is sent to Tavily's servers on every retrieve() call. That
fact is what S1 (privacy hard-block) depends on later.
"""

from __future__ import annotations

from datetime import datetime, timezone

from tavily import TavilyClient

from capretrieve.contracts.health import HealthState, HealthStatus
from capretrieve.contracts.request import RetrievalRequest
from capretrieve.contracts.result import Evidence, RetrievalResult
from capretrieve.manifest.models import CapabilityManifest


class WebSearchConnector:
    """
    manifest is injected (same pattern as the other connectors) so it's
    guaranteed identical to whatever registry/static.py loaded from
    configs/connectors/web_search.yaml.

    Either api_key or client may be provided. If client is given, api_key
    is ignored. If neither is given, the underlying Tavily SDK runs in
    keyless mode (heavily rate-limited, search-only per Tavily's docs) —
    usable for casual local testing, not intended for real deployment.
    Real wiring should read the key from WEB_SEARCH_API_KEY (see
    .env.example) and pass it in explicitly; this connector doesn't read
    environment variables itself, to keep it testable via plain
    constructor arguments.
    """

    def __init__(
        self,
        manifest: CapabilityManifest,
        api_key: str | None = None,
        client: TavilyClient | None = None,
    ) -> None:
        self._manifest = manifest
        self._client = client if client is not None else TavilyClient(api_key=api_key)
        self._configured = client is not None or bool(api_key)

    def manifest(self) -> CapabilityManifest:
        return self._manifest

    async def retrieve(self, req: RetrievalRequest) -> RetrievalResult:
        search_kwargs: dict = {"max_results": req.top_k}
        if req.deadline_ms is not None:
            # Tavily's timeout is in seconds; give it at least 1s even for
            # a very tight deadline_ms rather than passing something that
            # would reject the request outright.
            search_kwargs["timeout"] = max(req.deadline_ms / 1000, 1.0)

        response = self._client.search(req.query, **search_kwargs)
        results = response.get("results", [])

        evidence = [
            Evidence(
                source_id=self._manifest.connector_id,
                content=result.get("content", ""),
                score=float(result.get("score", 0.0)),
                uri=result.get("url"),
                retrieved_at=datetime.now(timezone.utc),
            )
            for result in results[: req.top_k]
        ]
        return RetrievalResult(evidence=evidence)

    async def health(self) -> HealthStatus:
        if not self._configured:
            return HealthStatus(
                state=HealthState.DEGRADED,
                detail=(
                    "no api_key or client configured; running in Tavily "
                    "keyless mode with heavy rate limits"
                ),
            )
        return HealthStatus(state=HealthState.OK)
# 0002: An explicit registry, not a plugin framework

**Status:** accepted

## Context

Sources need to be added over time. A common approach is automatic
discovery: entry points, scanning a package, or registering by decorator.
In this system a source's manifest decides where queries go, including
whether private queries can reach it, so adding a source changes the
system's privacy behaviour.

## Decision

`registry/static.py` is an explicit `{connector_id: Connector}` map. Adding
a source means writing a YAML manifest, implementing a `Connector`, and
calling `register()` once at startup in `bootstrap.py`. Nothing is
auto-detected.

`register()` checks that the connector's `manifest()` equals the manifest
loaded from YAML, and rejects unknown ids.

## Consequences

- Every new source arrives through a reviewed code change, with its
  capabilities visible in one YAML file.
- A connector can't declare different capabilities in code than in its
  manifest.
- Adding a source touches a few places (manifest, class, bootstrap, tests);
  [adding-a-connector.md](../adding-a-connector.md) lists them.
- The planner never imports the registry or connectors. It receives
  manifests as plain data from the graph's plan node (enforced by
  `tests/architecture/test_planner_imports.py`).

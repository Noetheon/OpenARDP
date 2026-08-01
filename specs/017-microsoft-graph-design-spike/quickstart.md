# Quickstart: Microsoft Graph Design Spike

The spike is deliberately offline. It requires no tenant, credentials, Graph SDK or network.

```bash
uv run pytest \
  tests/domain/test_graph.py \
  tests/contract/test_graph_ports.py \
  tests/integration/test_graph_sync.py \
  tests/security/test_graph_boundaries.py -q
```

Expected result: all focused tests pass with sockets disabled. The suite proves mock contract and
orchestration behavior only; it does not validate Microsoft tenant behavior or production readiness.

Then run the full repository gates:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

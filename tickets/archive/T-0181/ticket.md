---
id: T-0181
title: survey-prioritized third-party python/npm/cargo dangerous-surface registry
  entries (T-0158 addendum 2 remainder)
state: done
kind: security
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability_registry.py
- tests/**
- docs/modules/vet.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_every_operation_kind_and_language_registered
- tests/test_capability_registry.py::TestPerOperationFireFixtures::test_entry_fires_scan_file_operations
- tests/test_capability_registry.py::TestPerOperationFireFixtures::test_entry_absent_from_benign_source
designated_repro_test: null
threat: null
component: null
---
T-0158 shipped python stdlib coverage (subprocess/os/pickle/marshal/shelve/ctypes/importlib/eval+compile/socket+http+urllib+requests/httpx/aiohttp/sqlite3/asyncio/pty/multiprocessing) plus the common third-party python net clients (requests/aiohttp/httpx) already folded into the base table. NOT shipped: the addendum 2 (3) REAL-WORLD PRIORITY list's remaining survey items -- pydantic, fastapi, numpy, cryptography, jinja2, python-dotenv, uvicorn, sqlalchemy, asyncpg, alembic, redis, boto3, stripe, anthropic, argon2-cffi, aiosmtpd, playwright, Pillow (python); react/react-dom, vite/vitest, playwright, openapi-typescript, eslint tooling (npm); pyo3, serde/serde_json, tracing, libloading, wasm-bindgen, crossbeam, thiserror (cargo). Each needs its own DangerousOperation entries (or an explicit 'no dangerous surface, pure library' NO_CAPABILITY-style entry) surveyed against its actual API surface, not guessed. Left for a dedicated per-library-survey pass; T-0158's Done report has the full reasoning for why this was cut, not silently dropped.
---
id: T-4773
title: 'web-service preset: app-service, fastapi-service, sqlalchemy-alembic and caddy-deploy
  facets over the python base'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4766
parent: T-4757
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/data/facets/app-service/**
- src/frob/scaffold/data/facets/fastapi-service/**
- src/frob/scaffold/data/facets/sqlalchemy-alembic/**
- src/frob/scaffold/data/facets/caddy-deploy/**
- src/frob/scaffold/data/presets/web-service.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given the rendered service, when an in-process client requests the liveness
    route, then it returns success
  evidence: []
- text: Given the readiness route with no database reachable, when it is requested,
    then the translated error value produces the expected status, with no exception
    leaking from the service layer
  evidence: []
- text: Given the settings source is changed, when the application and the migration
    environment are both loaded, then both follow the same DSN
  evidence: []
- text: Given the rendered Dockerfile and compose file, when they are parsed, then
    the final stage runs as a non-root user and startup is gated on healthchecks
  evidence: []
- text: Given the web-service preset, when frob check runs in the rendered tree, then
    it is clean with zero REF001
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The gap the owner found: web-app is frontend-only and there is no backend
type of any kind. Measured: a case-insensitive search for fastapi, alembic,
caddy, dockerfile, compose, sqlalchemy, uvicorn or nginx across the entire
scaffold template tree returns ZERO files. web-app's 17 rendered files
contain no server, no API client, no proxy configuration, no environment or
config layer, no container, no reverse proxy, no database, no migrations and
no healthcheck.

web-service is a PRESET, not a type:
python + app-service + fastapi-service + sqlalchemy-alembic + caddy-deploy +
github-ci.

- app-service: the App and AppConfig pattern with the call method running
  the ASGI server, heavy imports deferred into the call method per
  refs/python-app.md.
- fastapi-service: routers imported inside the call method to break the
  cycle; every handler returns from a service-layer function yielding a
  Result, unwrapped at the HTTP boundary into a status code -- never an HTTP
  exception raised from deep code; one error-set per subsystem mapped to
  HTTP codes in a SINGLE translator; a /healthz liveness route and a /readyz
  route doing a database round trip.
- sqlalchemy-alembic: async SQLAlchemy 2.0 with asyncpg, typed model
  attributes, a session factory, and migrations whose environment is wired
  to the SAME settings object so there is no second home for the DSN.
- caddy-deploy: a Caddyfile with automatic TLS, reverse proxy and security
  headers; a multi-stage Dockerfile with a frozen dependency sync, a
  NON-ROOT user and a healthcheck hitting /healthz; a compose file with the
  application, postgres and caddy, with healthcheck-gated startup ordering.
- settings: all fields defaulted, merged CLI over environment over TOML over
  defaults, with an environment example file carrying placeholder values
  only -- the real environment file is never read.
- CI: run migrations against a postgres service container, then the tests,
  then frob check.

web-app-fullstack is deliberately NOT a separate type: it is web-service
plus the react-frontend facet with the dev-server proxy wired, which under
facets costs nothing and as a type would be a sixth fork.

Positive controls:
1. the rendered service starts and /healthz returns success, asserted by an
   in-process test client;
2. /readyz fails with the expected error VALUE when the database is absent,
   proving the Result-to-status translation rather than an exception leaking;
3. the migration environment and the application read the SAME DSN -- a test
   changes the settings source and asserts both follow;
4. the Dockerfile's final stage runs as a non-root user, asserted by parsing
   the rendered file, and the compose file gates startup on healthchecks;
5. frob check clean on the rendered preset, with zero REF001 -- this preset
   adds the most non-imported files of any type and is where the
   conventional-file defaults get their real test.

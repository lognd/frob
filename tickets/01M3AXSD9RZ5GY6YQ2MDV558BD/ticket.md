+++
id = "01M3AXSD9RZ5GY6YQ2MDV558BD"
title = "vet capability kinds per store client library (redis, mongo, dynamodb, neo4j, elasticsearch, clickhouse, s3) so SYS100/SYS101 refuse an undeclared store client in a bound file"
type = "task"
category = "triage"
priority = "medium"
parent = "01M3AXSDBCZ0WN62JE8P0BQRA2"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:00Z"
aliases = ["T-6456"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble"]
scope = ["src/frob/vet/_capability_registry/_kinds.py", "src/frob/vet/_capability_registry/_matrix.py", "src/frob/vet/_capability_registry/_store_clients.py"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD7YZNPPSYE1DAZ2MT42"
+++

Adds one new vet capability kind per store client library --
`store-redis`, `store-mongo`, `store-dynamodb`, `store-neo4j`,
`store-elasticsearch`, `store-clickhouse`, `store-s3` -- to the existing
`_ALL_CAPABILITY_KINDS` vocabulary in `_kinds.py` (the same table `sql`,
`fetch_url`, `deserialize`, `client_storage` etc already live in), so
these join `_selfconform_kinds.py`'s existing `_observed_raw_kinds_by_
node`/`_extended_kinds_view`/`_all_kinds_view` aggregation exactly like
every other wired kind (T-0830's own precedent for a NEW kind joining
the shared observed-kinds table without forking a second one) -- SYS100/
SYS101 then refuse a bound file that exhibits an undeclared store-client
capability the same way they already refuse an undeclared `sql`/
`fetch_url` capability today.

`_store_clients.py` is a new needle table, one `_DangerousOperation`-
shaped entry per client library per language (mirrors
`_dangerous_ops_python.py`'s `sqlite3`/`cursor.execute` entry shape:
`(language, module, api, kind, rationale, remediation, severity,
needles, cwe_refs)`), registering the import/call-site needle each
client library's dominant idiom uses (`import redis`/`redis.Redis(`,
`import pymongo`/`MongoClient(`, `boto3.client("dynamodb"` per
`_resolve_py_boto3_client_call`'s existing boto3-service-name
resolution shape, `from neo4j import GraphDatabase`, `from
elasticsearch import Elasticsearch`, `import clickhouse_connect`,
`boto3.client("s3"`).

Per-language coverage gaps get a `_MatrixExcuse` entry in `_matrix.py`
(same shape as the existing `capability_kind="sql", language="c-cpp"`
excuse rows) rather than a silently-missing pattern, for every
language/client combination this leaf does not cover in its first pass
(e.g. Rust/Go store clients, if left for a follow-up leaf).

Acceptance criteria:
- Every new kind appears in `_ALL_CAPABILITY_KINDS` and in at least one
  `_matrix.py` coverage row (either a working needle table entry or an
  explicit `_MatrixExcuse`).
- A fixture file importing `redis`/`pymongo`/`boto3` (dynamodb client)/
  `neo4j`/`elasticsearch`/`clickhouse_connect` with no matching `.strata`
  `store` declaration trips SYS100/SYS101 the same way an undeclared
  `sql` capability already does.
- No duplicate needle table: this leaf extends the existing per-language
  registry files' SHAPE, it does not fork a second capability-scanning
  mechanism alongside `_capability_python.py`/`_capability_csharp.py`.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"

+++
id = "01M3AXSD96Z5HQ62F3H02R275A"
title = "STORE119: poll loop around `SELECT ... WHERE status='pending'` instead of a queue product (relational)"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSD9STSFC2MR8M369JNE8"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:25Z"
aliases = ["T-6438"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_relational.py", "tests/fixtures/store/store119-relational-db-as-queue/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD8EJE4SFMVFJJF41NMA"

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

Rule id: STORE119.

Authority: Postgres provides `LISTEN`/`NOTIFY` as a notification
primitive, not a durable queue guarantee; this pattern is well
documented as an anti-pattern in the ecosystem generally, but the
research file flags this row **gap**: this fetch pass did not source a
Postgres-specific "don't use us as a queue" quote. Blocked by
T-STORE-401-GAPS.

Call shapes:
- Python: `cursor.execute("SELECT * FROM jobs WHERE status='pending'
  FOR UPDATE SKIP LOCKED")` in a `while True`/APScheduler poll loop;
  SQLAlchemy session polling on an interval
- TS/JS: `knex('jobs').where('status','pending')` in a `setInterval`
  poll loop
- Rust (sqlx): polling loop with `tokio::time::interval`

Detection: polling loop (`while True`/`setInterval`/timer-decorated
function) containing a `SELECT`/`UPDATE` on a table with job/queue-like
column names (`status`, `pending`, `job`, `queue` substrings).

Positive-control fixture:
`tests/fixtures/store/store119-relational-db-as-queue/`.

Relevance gate: relational SQL surface detected
(`frob.sql._extract.sql_relevance`, reused rather than re-sniffed).

Reuse note: this is the relational-paradigm sibling of SQL10x's own
call-shape scan; import `frob.sql._orm_rules`'s `_iter_nodes`/
`_function_defs` walker helpers rather than re-implementing a second
tree-sitter walk.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"

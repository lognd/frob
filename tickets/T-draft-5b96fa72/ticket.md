---
id: T-draft-5b96fa72
title: 'STORE: database-paradigm misuse lint family'
state: queued
kind: feature
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: epic
sprint: store-family
runs_last: false
milestone: 0.538.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 52614
  new_length: 52752
- mode: set
  reason: 'DOC006 inline waivers: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 52752
  new_length: 52930
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Database-paradigm misuse (using a relational/document/key-value/graph/
search/time-series/object store against the shape its own vendor
documents it is bad at) is detectable from source for two of the four
research tiers without any new parser: tier 1 (call-shape alone) reuses
the exact tree-sitter-via-`frob.lang.raw_tree` walk `frob.sql._orm_rules`
already stands up for SQL101-106; tier 2 (call-shape plus one repo fact)
adds a schema/config read alongside the same walk; tier 3 (declared-
versus-observed) needs strata's `store` node and its `engine` attr, which
already exists (`_infra.py::_store_base_attrs`) but is read by nothing
today. Tier 4 (dynamic-only: EAV detection from data, document growth,
runtime cardinality) is out of scope for a static rule and is recorded as
dropped tickets, never faked with a lexical heuristic (owner rule).

<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its scaffold" -->Sourced from scratchpad/DB-PARADIGM-ASSESSMENT.md (tiering) and
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its scaffold" -->scratchpad/db-paradigm-research.md (45 anti-pattern rows, 8 sections, 30
vendor pages fetched, 13 rows carrying an explicit gap/partial-gap
citation note). Every filed STORE rule cites its vendor authority
verbatim in its own ticket body (owner rule: every rule cites its
authority) -- rows still marked gap in the research file are filed
anyway in this tree (so the queue reflects the real backlog) but each
such leaf is `blocked_by` T-STORE-401-GAPS, the leaf that closes the
citation gap before the rule ships.

One epic, four stories:
- Story 1 (STORE1xx): call-shape-alone rules, one findings function
  family per client library, gated by client-library import detection
  the same way `frob.webapp.detect_frameworks` gates the WEBSEC/A11Y/
  SEO/WEBPERF families -- a repo importing none of redis/pymongo/motor/
  boto3/neo4j/elasticsearch-py/clickhouse-connect/influxdb-client sees
  no STORE finding at all.
- Story 2 (STORE2xx): call-shape plus one repo fact (schema/config file
  alongside the call site).
- Story 3 (STORE3xx): declared-paradigm-versus-observed-access mismatches
  through strata's `store.engine` attr plus new vet capability kinds.
- Story 4: closes the 13 authority-citation gaps, and records the
  dynamic-only (tier 4) rows as dropped tickets rather than silently
  omitting them from the queue.

Reuse discipline (no duplication): STORE105 (Mongo N+1) and STORE119
(relational-as-queue poll loop) import the walker helpers
(`_iter_nodes`, `_function_defs`, `_for_loop_targets`,
`_attribute_accesses_on`) from `src/frob/sql/_orm_rules.py` rather than
re-implementing a second tree-sitter walk; the "unbounded read" shape
(STORE102/STORE112/STORE117) and "multi-write-without-transaction" shape
(STORE303) are the same generalization SQL102/SQL105 already establish
for a different receiver kind, and import from the same module for the
same reason.

Not before: the WEBSEC/SQL families landing (T-5140/T-5148) and the attr
registry (T-STORE-301-ATTR) existing first, since STORE3xx is unfileable
without it.

---

# Research corpus (verbatim): db-paradigm-research.md

# Database-paradigm mistake catalogue (primary sources, for frob lint family)

Status: RESEARCH COMPLETE WITH GAPS. Universe = 7 paradigms x (paradigm summary +
4-8 anti-patterns each) + 1 cross-cutting "workload vs paradigm mismatch" section.
See coverage checklist at the end for exact denominators, done/blocked counts.

Methodology: fetched vendor doc pages via curl (some required --compressed to
avoid gzip-garbled output; noted where fetch failed or returned a JS shell).
Static/config/dynamic-only tags follow frob's existing lint-authorities corpus
convention:
- Static: yes -> AST/text pattern match on the call site is sufficient
- Static: config -> requires reading a config file/connection string alongside
  the call site (still no runtime data needed)
- Static: dynamic-only -> requires runtime/data-shape information a linter
  cannot see from source (flag as heuristic/advisory only)

---

## 1. Relational (PostgreSQL, MySQL, SQLite)

**Good for / bad for (vendor's own words):** PostgreSQL's own JSON docs say
jsonb "also supports indexing, which can be a significant advantage" over the
`json` type, but frame JSON as a data *type* choice, not a schema-replacement
strategy -- "most applications should prefer to store JSON data as jsonb,
unless there are quite specialized needs" (PostgreSQL 18 docs, "8.14. JSON
Types", https://www.postgresql.org/docs/current/datatype-json.html). Postgres
also documents that its Large Object facility (`pg_largeobject`) is mostly
superseded by TOAST for values under 1 GB, and is retained only for the
narrow case of >1 GB / up-to-4 TB blobs needing partial read/write: "TOASTed
fields... This makes the large object facility partially obsolete. One
remaining advantage... is that it allows values up to 4 TB in size" (Postgres
18 docs, "33.1. Introduction" (Large Objects),
https://www.postgresql.org/docs/current/lo-intro.html). Relational engines
are built around normalized, typed, indexable columns and multi-row ACID
transactions; they are not marketed as durable queues, caches, or blob stores,
and community guidance (PostgreSQL wiki "Don't Do This",
https://wiki.postgresql.org/wiki/Don%27t_Do_This) exists specifically to warn
against anti-patterns that fight this model.

| # | Anti-pattern | Authority (title, URL, quote) | Python call shapes | TS/JS call shapes | Rust/Go | Static? |
|---|---|---|---|---|---|---|
| 1 | JSON/JSONB blob as the primary model instead of typed columns, with app code querying paths (`->`, `->>`, `@>`) as if it were the schema | PostgreSQL 18 docs, "8.14 JSON Types": "most applications should prefer to store JSON data as jsonb, unless there are quite specialized needs" (framing jsonb as a column type choice, not the model) -- https://www.postgresql.org/docs/current/datatype-json.html | `cursor.execute("... ->> %s ...")`, SQLAlchemy `Column(JSONB)` used for >N top-level query paths, Django `JSONField` with frequent `__` lookups into it | `pg` raw SQL with `->>`, Prisma `Json` field type with repeated `path` filters, Knex `.whereRaw("data->>")` | sqlx `sqlx::types::Json<T>` queried by path repeatedly | config (needs to see column DDL type is JSON/JSONB and count of distinct path expressions against it) |
| 2 | Entity-Attribute-Value (EAV) modeling: a generic `(entity_id, attribute_name, value)` table used instead of typed columns | Not directly named on the Postgres wiki page fetched (see gap note); pattern recognized as anti-pattern via the same "Don't Do This" advisory tradition -- https://wiki.postgresql.org/wiki/Don%27t_Do_This (page fetched but did not surface an EAV-specific quote in this pass; see Gaps) | ORM model classes named `Attribute`/`EntityAttribute` with FK to a generic `entities` table, dynamic column building via `getattr`/`setattr` loops over rows | Same shape in TypeORM/Prisma: a `KeyValue` or `Attribute` entity joined back to `Entity` | -- | dynamic-only for detecting "is this actually EAV" from schema shape; static (config) once table/column names match the pattern |
| 3 | Using the RDBMS as a message queue (poll-based `SELECT ... WHERE status='pending'` loops, or `LISTEN/NOTIFY` as the sole queue) instead of a queue product | Vendor framing: Postgres provides `LISTEN`/`NOTIFY` as a notification primitive, not a durable queue guarantee; general pattern is well documented as an anti-pattern in the ecosystem (this fetch pass did not source a Postgres-specific "don't use us as a queue" quote -- see Gaps) | Polling loop: `cursor.execute("SELECT * FROM jobs WHERE status='pending' FOR UPDATE SKIP LOCKED")` in a `while True`/APScheduler loop; SQLAlchemy session polling on an interval | `knex('jobs').where('status','pending')` in a `setInterval` poll loop | sqlx polling loop with `tokio::time::interval` | static: yes (detect polling loop + `SELECT`/`UPDATE` on a table with job/queue-like column names inside a sleep/interval loop) |
| 4 | Using the RDBMS as a cache (storing derived/recomputable data with no TTL/eviction, refreshed by app-level cron) | Same family as above; Postgres offers no built-in TTL/eviction primitive, unlike Redis's `EXPIRE` (see Redis section) -- absence of the feature is itself the signal | Table/model literally named `cache`/`*_cache` with `created_at` but no expiry column, or app code manually `DELETE FROM cache WHERE created_at < now() - interval` | Same shape via Prisma/TypeORM `Cache` entity | -- | config (needs schema: table name heuristic + absence of TTL/expiry mechanism) |
| 5 | Unbounded `LIKE '%term%'` / `ILIKE` full-text search on large text columns instead of `tsvector`/full-text index or external search engine | PostgreSQL wiki "Don't Do This" (page fetched, general anti-pattern index at https://wiki.postgresql.org/wiki/Don%27t_Do_This); this pass located general guidance but not a verbatim LIKE-specific quote on that page -- treat as **gap**, cite instead the well-known official docs on full text search as the alternative: PostgreSQL "12. Full Text Search", https://www.postgresql.org/docs/current/textsearch.html (title confirmed via TOC structure; body not separately fetched this pass) | `cursor.execute("... WHERE col LIKE %s", (f"%{q}%",))`, Django `.filter(col__icontains=q)`, SQLAlchemy `.filter(Model.col.ilike(f"%{q}%"))` on a column with no trigram/tsvector index | `knex.whereRaw("col LIKE ?", [\`%${q}%\`])`, Prisma `{ contains: q }` on a large text field, TypeORM `Like(\`%${q}%\`)` | sqlx `LIKE $1` with leading wildcard | static: yes for the call-shape (leading-wildcard LIKE/ILIKE/contains); config to confirm no matching GIN/trigram index exists |
| 6 | Storing large binaries (images, files, blobs >1MB) directly as `bytea`/`BLOB` columns instead of object storage with a reference | Postgres itself documents the size/perf tradeoff: TOAST caps at 1 GB per field and "most operations on a TOASTed field will read or write the whole value as a unit" versus large objects allowing up to 4 TB with efficient partial I/O -- https://www.postgresql.org/docs/current/lo-intro.html | `cursor.execute("INSERT INTO files (data) VALUES (%s)", (file_bytes,))` where `file_bytes` comes from an uploaded file object, SQLAlchemy `Column(LargeBinary)` | `pg` query with a `Buffer` parameter from `multer`/upload middleware, Prisma `Bytes` field fed directly from request body | sqlx `Vec<u8>` bound param from file read | static: yes (detect binary/bytes param sourced from file-upload/read call bound directly into an INSERT/UPDATE) |
| 7 | Modeling inherently graph-shaped many-to-many traversal (friend-of-friend, recommendation paths) with recursive CTEs across many join tables instead of a graph DB, when traversal depth/fanout is unbounded | Cross-referenced in "workload vs paradigm mismatch" section below (Neo4j's own docs on variable-length paths apply symmetrically) | `WITH RECURSIVE` CTE in raw SQL called from app code repeatedly with increasing depth params | `knex.raw("WITH RECURSIVE ...")`, Prisma raw query with recursive CTE | sqlx raw `WITH RECURSIVE` | dynamic-only (need to see it's called in a loop / with unbounded depth param) |

---

## 2. Document (MongoDB, Firestore, CouchDB, DynamoDB-as-document)

**Good for / bad for:** MongoDB's own modeling guidance is explicit that
document size and array growth are structural constraints, not style
choices: "The maximum BSON document size is 16 mebibytes. The maximum
document size helps ensure that a single document cannot use an excessive
amount of RAM or, during transmission, an excessive amount of bandwidth. To
store documents larger than the maximum size, MongoDB provides the GridFS
API" (MongoDB Manual, "MongoDB Limits and Thresholds",
https://www.mongodb.com/docs/manual/reference/limits/). MongoDB's own
one-to-many reference-modeling page states the tradeoff directly: "If the
number of books per publisher is unbounded, this data model creates mutable,
growing arrays" and recommends flipping the reference direction to avoid it
(MongoDB Manual, "Model One-to-Many Relationships with Document References",
https://www.mongodb.com/docs/manual/tutorial/model-referenced-one-to-many-relationships-between-documents/).
Indexing is opt-in and costs write throughput: "adding an index has negative
performance impact for write operations... indexes are expensive because
each insert must also update any indexes" (MongoDB Manual, "Indexes",
https://www.mongodb.com/docs/manual/indexes/).

| # | Anti-pattern | Authority (title, URL, quote) | Python call shapes | TS/JS call shapes | Rust/Go | Static? |
|---|---|---|---|---|---|---|
| 1 | Unbounded array growth inside a document (e.g., appending child IDs/events to a parent array forever) | MongoDB Manual, "Model One-to-Many Relationships with Document References": "If the number of books per publisher is unbounded, this data model creates mutable, growing arrays" -- https://www.mongodb.com/docs/manual/tutorial/model-referenced-one-to-many-relationships-between-documents/ | pymongo/motor `collection.update_one({...}, {"$push": {"items": v}})` with no `$slice`/cap, mongoengine `ListField` appended via `.append()` + `.save()` in a loop | mongoose `doc.items.push(v); doc.save()` with no bound, native driver `$push` with no `$slice` | -- | static: yes (detect `$push` without `$slice`/`$each`+cap on a field, in a repeatable code path) |
| 2 | Approaching/exceeding the 16MB BSON document size limit by embedding unboundedly | MongoDB Manual, "MongoDB Limits and Thresholds": "The maximum BSON document size is 16 mebibytes... To store documents larger than the maximum size, MongoDB provides the GridFS API" -- https://www.mongodb.com/docs/manual/reference/limits/ | Large embedded sub-documents/arrays built up via nested dict construction before a single `insert_one`/`replace_one` | Nested object construction before `collection.insertOne`/`replaceOne` | -- | dynamic-only (size is a runtime property; linter can only flag embedding-without-bound patterns as a proxy, same as #1) |
| 3 | Application-side joins: `$lookup` used in a hot request path, or manual N+1 `find_one` calls to stitch related collections instead of embedding or a single aggregation | General MongoDB modeling guidance frames references as requiring app-side or `$lookup` joins as the explicit cost of normalizing (see reference-modeling page above); this pass did not source a dedicated "$lookup in hot path" warning quote -- **gap**, flag as inferred from the documented tradeoff rather than a direct quote | `for parent in collection.find(...): child = other_collection.find_one({"parent_id": parent["_id"]})` (loop containing a `find`/`find_one` call), or `.aggregate([{"$lookup": ...}])` inside a per-request handler called per-row | `for (const p of parents) { const c = await Other.findOne({parentId: p._id}) }`, mongoose `.populate()` in a loop | -- | static: yes for the N+1 shape (DB call inside a loop over a prior query's results); config for "$lookup in hot path" (needs call-site context: request handler vs batch job) |
| 4 | Collection scans without a filter, or queries missing appropriate index coverage (`find({})` over large collections, `$where`/`$regex` leading-wildcard without text index) | MongoDB Manual, "Indexes": "Without indexes, MongoDB must scan every document in a collection to return query results. If an appropriate index exists for a query, MongoDB uses the index to limit the number of documents it must scan" -- https://www.mongodb.com/docs/manual/indexes/ | pymongo `collection.find({})` with no filter/limit on a collection referenced elsewhere as large, `collection.find({"field": {"$regex": f"^.*{q}"}})` | `Model.find({})`, `collection.find({field: {$regex: q}})` with leading wildcard | -- | config (needs index list from schema/migration files to confirm absence; call shape itself is static: yes) |
| 5 | Multi-document transactions spanning many documents/collections as a substitute for correct single-document modeling, subject to runtime limits | MongoDB Manual, "Production Considerations (Transactions)": "By default, a transaction must have a runtime of less than one minute... Transactions release all locks upon abort or commit" and lock-acquisition default of 5ms with abort-on-timeout -- https://www.mongodb.com/docs/manual/core/transactions-production-consideration/ | `with client.start_session() as s: with s.start_transaction(): ` wrapping many sequential `update_one`/`insert_one` calls across multiple collections | `session.withTransaction(async () => { ... })` wrapping many sequential writes across models | -- | static: yes (count of distinct write calls / collections touched inside one transaction block, via simple AST scope analysis) |
| 6 | Schema-less drift: no validation, inconsistent field types/names across documents in the same collection, read code defensively branching on `if isinstance`/`typeof` per document | MongoDB itself ties this to indexing correctness: ambiguous/duplicate field-name handling is called out as a data-loss/corruption risk area -- "Naming Warnings: Use caution, the issues discussed in this section could lead to data loss or corruption" -- https://www.mongodb.com/docs/manual/reference/limits/ | Read path with `doc.get("field", default)` fallback chains varying per call site, or `isinstance(doc["x"], (int, str))` branching | `typeof doc.field === 'string' ? ... : ...` branching at multiple read sites for the same field | -- | dynamic-only (requires cross-file type-consistency inference across all writers of a collection) |
| 7 | DynamoDB single-table design misused: storing genuinely unrelated entity types in one table without a documented access-pattern-driven key schema (i.e., single-table applied as a document-store habit, not per DynamoDB's own methodology) | AWS docs, "Best Practices for Designing and Architecting with DynamoDB": general-purpose NoSQL design guidance -- fetched (https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-general-nosql-design.html) but did not this pass yield a short pull-quote distinct from the page title/nav; content confirms the page exists and covers this topic -- **partial gap**, see notes | boto3 `table.put_item(Item={...})` with heterogeneous `Item` shapes and a generic `PK`/`SK` naming convention but no access-pattern doc/tests | `docClient.send(new PutCommand({...}))` same shape | -- | dynamic-only (requires access-pattern knowledge outside source) |
| 8 | `Scan` used where `Query` (with a key condition) would suffice, especially in a request-serving path | AWS docs, "Best Practices for Using Scan Operations": page fetched but returned only nav shell content this pass ("Amazon DynamoDB") -- HTML likely JS-rendered or the fetch hit a redirect stub -- **fetch failed/gap**; alternate confirmed source: AWS docs "Query and Scan Operations in DynamoDB" (https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query-and-Scan-Operations-in-DynamoDB.html) also returned minimal content this pass -- **gap, mark JS-rendered** | boto3 `table.scan(...)` call inside a request handler / API view function | `docClient.send(new ScanCommand({...}))` inside a request handler | -- | static: yes (Scan-call-in-request-handler is a pure call-shape + call-site check) |

---

## 3. Key-value / cache (Redis, Memcached, DynamoDB-as-KV)

**Good for / bad for:** Redis's own command docs are unusually direct about
misuse. `KEYS`: "**Warning**: Use extreme care when using this command in
production environments. It may ruin performance when it is executed
against large databases. This command is intended for debugging and special
operations" (Redis docs, "KEYS",
https://redis.io/docs/latest/commands/keys/). Redis frames persistence as
opt-in and tunable, not a default durability guarantee: "No persistence: You
can disable persistence completely. This is sometimes used when caching...
RDB is NOT good if you need to minimize the chance of data loss" (Redis
docs, "Redis persistence",
https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/).
This is the vendor's own statement that Redis-as-durable-primary-store needs
explicit AOF/RDB configuration review, not defaults.

| # | Anti-pattern | Authority (title, URL, quote) | Python call shapes | TS/JS call shapes | Rust/Go | Static? |
|---|---|---|---|---|---|---|
| 1 | `KEYS pattern` used in application/production code instead of `SCAN` | Redis docs, "KEYS": "Use extreme care when using this command in production environments. It may ruin performance when it is executed against large databases. This command is intended for debugging" -- https://redis.io/docs/latest/commands/keys/ (also documents O(N) time complexity) | `redis_client.keys("prefix:*")` (redis-py) | `redis.keys('prefix:*')` (ioredis/node-redis) | Rust `redis` crate `.keys()` | static: yes |
| 2 | Unbounded `SMEMBERS`, `HGETALL`, or `LRANGE key 0 -1` on collections with no known bound, in a hot path | Redis docs, "SMEMBERS": "Time complexity: O(N) where N is the set cardinality" (https://redis.io/docs/latest/commands/smembers/); "HGETALL": "O(N) where N is the size of the hash" (https://redis.io/docs/latest/commands/hgetall/); "LRANGE": "O(S+N)... N is the number of elements in the specified range" (https://redis.io/docs/latest/commands/lrange/) -- vendor documents these as linear/unbounded by construction, unlike O(1) point ops | `r.smembers(key)`, `r.hgetall(key)`, `r.lrange(key, 0, -1)` with no pagination (`SSCAN`/`HSCAN`) alternative used nearby | `redis.smembers(key)`, `redis.hgetall(key)`, `redis.lrange(key, 0, -1)` | Rust `redis` crate equivalents | static: yes (call-shape match, especially literal `0, -1` range) |
| 3 | Cache keys written with `SET`/`SETEX` variants but no TTL ever applied (using Redis as unbounded cache growth) | Redis docs, "EXPIRE": documents that ordinary write ops (`LPUSH`, `HSET`, etc.) "leave the timeout untouched" and TTL must be explicitly set/cleared via `EXPIRE`/`PERSIST` -- https://redis.io/docs/latest/commands/expire/ (vendor documents TTL as an explicit, separate act from the write) | `r.set(key, value)` (no `ex=`/`px=` kwarg) repeated across a codebase for keys named/used as cache (`cache:*`, `*_cache`) with no accompanying `EXPIRE` call | `redis.set(key, value)` with no `EX`/`PX` option, `ioredis.set(key, value)` | -- | static: yes (call-shape: `SET`/`SETEX` variants missing TTL argument, cross-referenced with key-name heuristic) |
| 4 | Relying on Redis as the durable primary store without reviewing/enabling AOF or RDB (i.e., default/no persistence config in a codebase that treats Redis as source of truth) | Redis docs, "Redis persistence": "No persistence: You can disable persistence completely. This is sometimes used when caching... RDB is NOT good if you need to minimize the chance of data loss in case Redis stops working" -- https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/ | App code that never reads from a secondary DB and treats `r.set`/`r.get` as the only write path for entities with business-critical data | Same shape in Node | -- | config (requires reading redis.conf/deployment config for `appendonly`/`save` settings alongside source scan for "is Redis the only writer") |
| 5 | Storing large values (multi-MB blobs) in a single Redis key/field | Cross-referenced from Redis's own complexity docs: large single values defeat Redis's in-memory, single-threaded-command-processing design (no single blob-size-limit quote sourced this pass -- **gap**; general 512MB string value ceiling is documented elsewhere in Redis docs but was not directly fetched in this pass) | `r.set(key, big_bytes)` where `big_bytes` comes from file read/serialization of a large object | `redis.set(key, largeBuffer)` | -- | dynamic-only (value size is runtime data; linter can flag `.set()` fed directly from file-read/serialize-of-large-object as a proxy) |
| 6 | Non-atomic check-then-set (`GET` then conditionally `SET`) instead of `SET key val NX` or a Lua script, causing race conditions | Redis docs, "SET": documents `NX`/`XX`/`GET` options as the atomic alternative to separate GET+SET (https://redis.io/docs/latest/commands/set/ -- page fetched at scale, ~600KB; NX/XX option documentation present in command reference) | `if not r.get(key): r.set(key, value)` (two separate calls, no lock) | `if (!(await redis.get(key))) { await redis.set(key, value) }` | -- | static: yes (detect `GET` immediately followed by conditional `SET` on the same key within the same function, without `NX`) |
| 7 | Blocking commands (`BLPOP`, `BRPOP`, `WAIT`, long `SUBSCRIBE`) issued on a shared/pooled connection also used for regular request-serving commands | Cross-referenced from Redis's client-connection model (single connection blocks that command's caller); dedicated vendor quote not sourced this pass -- **gap** | `shared_pool.blpop(...)` where `shared_pool` is the same client object used elsewhere for request-path `GET`/`SET` | `sharedClient.blpop(...)` reused as the main app client | -- | config (needs to trace whether the connection/client object is the same instance used for other request-path calls) |

---

## 4. Graph (Neo4j, Neptune, ArangoDB)

**Good for / bad for:** Neo4j's own tuning guide states the discipline
directly: "You should also make sure to set an upper limit on variable-length
patterns, so they don't cover larger portions of the dataset than needed"
and "returning whole nodes and relationships ought to be avoided in favour
of selecting and returning only the data that is needed" (Neo4j Cypher
Manual, "Query tuning",
https://neo4j.com/docs/cypher-manual/current/query-tuning/). Graph databases
are optimized for traversal-heavy, relationship-first queries; they are not
positioned as tabular aggregation engines, and unconstrained pattern matches
are explicitly flagged by the vendor as a performance hazard rather than a
style preference.

| # | Anti-pattern | Authority (title, URL, quote) | Python call shapes | TS/JS call shapes | Rust/Go | Static? |
|---|---|---|---|---|---|---|
| 1 | Variable-length path pattern (`[*]`, `[*..]`) with no upper bound | Neo4j Cypher Manual, "Query tuning": "You should also make sure to set an upper limit on variable-length patterns, so they don't cover larger portions of the dataset than needed" -- https://neo4j.com/docs/cypher-manual/current/query-tuning/ | `session.run("MATCH (a)-[*]-(b) RETURN a,b")` (neo4j driver), Cypher string built without a bound on `*` | `session.run('MATCH (a)-[*]-(b) ...')` (neo4j-driver JS) | Rust/Go neo4j driver same string shape | static: yes (regex/parse for `[*` not followed by `..N]` or `N]` bound in a Cypher string literal) |
| 2 | Query with no `LIMIT` returning potentially the whole graph/large result set to the app | Same page: emphasizes selecting/returning only needed data and bounding patterns; general Cypher guidance recommends `LIMIT` for exploratory/paginated queries -- https://neo4j.com/docs/cypher-manual/current/query-tuning/ | Cypher string with `RETURN` and no `LIMIT`, executed from a request handler | Same shape | -- | static: yes (parse Cypher string literal for `LIMIT` clause presence) |
| 3 | Returning whole nodes/relationships (`RETURN n`) instead of projecting needed properties | Neo4j Cypher Manual, "Query tuning": "returning whole nodes and relationships ought to be avoided in favour of selecting and returning only the data that is needed" -- https://neo4j.com/docs/cypher-manual/current/query-tuning/ | `session.run("MATCH (n:Person) RETURN n")` | Same shape | -- | static: yes (parse `RETURN` clause for bare node/relationship variable vs property projection) |
| 4 | Cartesian product from disconnected `MATCH` patterns (multiple comma-separated patterns with no shared variable) | Neo4j's pattern/tuning docs address the mechanism generally (patterns and their combination) -- https://neo4j.com/docs/cypher-manual/current/patterns/reference/ ; this pass did not extract a standalone "Cartesian product" verbatim warning from the fetched pages -- **gap**, cross-referenced from Cypher planner behavior documented in the tuning page's discussion of plan search space (`planner=idp`/exhaustive search options) | `MATCH (a:A), (b:B) RETURN a,b` (two disconnected patterns, no relationship between them) | Same shape | -- | static: yes (parse Cypher for multiple comma-separated `MATCH` patterns with no shared identifier) |
| 5 | Using a relational DB with recursive CTEs to emulate graph traversal instead of a purpose-built graph DB, when traversal depth/fanout is unbounded and relationship-heavy | Cross-reference to relational section (`WITH RECURSIVE`) and Neo4j's own positioning of itself for traversal workloads (query tuning page, path-pattern guidance) -- https://neo4j.com/docs/cypher-manual/current/query-tuning/ | See relational #7 | See relational #7 | -- | dynamic-only (needs workload evidence: recursive CTE called repeatedly / with unbounded depth) |
| 6 | Using a graph DB for tabular/columnar aggregation workloads (large `GROUP BY`-equivalent aggregations over unrelated properties) instead of a relational/columnar store | Inferred from Neo4j's own performance guidance emphasizing traversal and pattern-selectivity, not bulk aggregation, as the tuning focus -- https://neo4j.com/docs/cypher-manual/current/query-tuning/ (no direct "don't use us for OLAP" quote sourced this pass -- **gap**) | Cypher `MATCH (n) WITH n.category AS c, count(*) AS n RETURN c, n` over the entire node set with no relationship traversal at all | Same shape | -- | dynamic-only (requires knowing the aggregation touches most/all nodes) |

---

## 5. Search (Elasticsearch/OpenSearch, Meilisearch, Typesense)

**Good for / bad for:** Elasticsearch's own pagination docs state the limit
and the reason for it as vendor policy, not just performance advice: "Avoid
using from and size to page too deeply or request too many results at once.
Search requests usually span multiple shards. Each shard must load its
requested hits and the hits for any previous pages into memory... By
default, you cannot use from and size to page through more than 10,000
hits. This limit is a safeguard set by the index.max_result_window index
setting" (Elasticsearch Reference, "Paginate search results",
https://www.elastic.co/guide/en/elasticsearch/reference/current/paginate-search-results.html).
Wildcard queries are documented as a distinct, more expensive query type by
design: "A wildcard operator is a placeholder that matches one or more
characters" used to build patterns like `ki*y` (Elasticsearch Reference,
"Wildcard query",
https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-wildcard-query.html)
-- leading wildcards in particular are the classically expensive case because
they defeat the inverted index's prefix structure.

| # | Anti-pattern | Authority (title, URL, quote) | Python call shapes | TS/JS call shapes | Rust/Go | Static? |
|---|---|---|---|---|---|---|
| 1 | Deep pagination via `from`/`size` beyond the 10,000-hit window instead of `search_after`/scroll | Elasticsearch Reference, "Paginate search results": "By default, you cannot use from and size to page through more than 10,000 hits. This limit is a safeguard set by the index.max_result_window index setting. If you need to page through more than 10,000 hits, use the search_after parameter instead" -- https://www.elastic.co/guide/en/elasticsearch/reference/current/paginate-search-results.html | `es.search(index=idx, body={"from": n, "size": s})` where `n+s` can exceed 10000, or `n` grows in a loop | `client.search({ from: n, size: s })` (elasticsearch-js) same growth pattern | -- | static: yes for literal constants; config/dynamic for `from` values computed from a page-number variable (needs bound analysis) |
| 2 | Wildcard query with a leading wildcard (`*term`) instead of an edge-ngram/prefix-optimized field | Elasticsearch Reference, "Wildcard query": example pattern `ki*y` shown as the supported shape; leading-wildcard cost is a long-standing, vendor-acknowledged Lucene limitation (this pass's fetch of the wildcard-query page confirms the query DSL shape; a dedicated "leading wildcards are expensive" caveat line was not isolated verbatim in this pass -- partial gap, flag as such) -- https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-wildcard-query.html | `es.search(body={"query": {"wildcard": {"field": {"value": f"*{term}"}}}})` | `client.search({ query: { wildcard: { field: { value: \`*${term}\` } } } })` | -- | static: yes (parse the wildcard value string literal/f-string for a leading `*`) |
| 3 | Script fields (`script_fields`, inline `script` in query) evaluated per-document in a hot/request-serving path instead of precomputed/indexed fields | Cross-referenced from Elasticsearch's general performance-tuning guidance page (fetched: "Tune for search speed", https://www.elastic.co/guide/en/elasticsearch/reference/current/tune-for-search-speed.html) -- this pass did not isolate a standalone script-field-cost quote from that page's stripped text; **gap**, recommend re-fetch with targeted extraction | `es.search(body={"script_fields": {...}})` inside a per-request handler | `client.search({ script_fields: {...} })` in a request handler | -- | static: yes (call-shape: `script_fields`/inline `script` key present, call-site = request handler) |
| 4 | Treating the search index as the source of truth (writing only to Elasticsearch, no canonical DB, no reindex path) | Not a single vendor quote sourced this pass; well-established as a documented operational risk in Elastic's own "reindexing" and snapshot/restore guidance (not fetched this pass) -- **gap** | App write path that only calls `es.index(...)`/`es.update(...)` with no corresponding write to a relational/document store for the same entity | Same shape (`client.index(...)` only) | -- | dynamic-only (requires whole-codebase data-flow: is there any other writer for this entity) |
| 5 | Unbounded `match_all`/no-filter query against a large index in a request path | General Elasticsearch performance guidance (same family as #1/#3); no standalone quote isolated this pass -- **gap** | `es.search(body={"query": {"match_all": {}}}, size=10000)` | `client.search({ query: { match_all: {} } })` | -- | static: yes (call-shape: `match_all` with no filter clause) |

---

## 6. Time-series / columnar (TimescaleDB, InfluxDB, ClickHouse)

**Good for / bad for:** ClickHouse's own docs state the structural reason
point updates/deletes are discouraged: "mutations in ClickHouse are
asynchronous background processes that rewrite entire data parts affected by
the change. This approach is necessary due to ClickHouse's column-oriented,
immutable storage model... even a minor change (such as updating a single
row) may result in large-scale rewrites and excessive write amplification...
As a rule, avoid frequent or large-scale mutations, especially on high-volume
tables" (ClickHouse Docs, "Avoid mutations",
https://clickhouse.com/docs/en/optimize/avoid-mutations). InfluxDB's own
schema-design guidance identifies high-cardinality tags as a first-class
schema mistake: "Tags containing highly variable information like unique
IDs, hashes, and random strings lead to a large number of series, also known
as high series cardinality. High series cardinality is a primary driver of
high memory usage for many database workloads" (InfluxDB OSS v2 docs,
"Resolve high series cardinality",
https://docs.influxdata.com/influxdb/v2/write-data/best-practices/resolve-high-cardinality/).

| # | Anti-pattern | Authority (title, URL, quote) | Python call shapes | TS/JS call shapes | Rust/Go | Static? |
|---|---|---|---|---|---|---|
| 1 | Point `UPDATE`/`ALTER TABLE ... UPDATE` mutations on high-volume ClickHouse tables instead of insert-and-replace patterns (ReplacingMergeTree/CollapsingMergeTree) | ClickHouse Docs, "Avoid mutations": "As a rule, avoid frequent or large-scale mutations, especially on high-volume tables. Instead, use alternative table engines such as ReplacingMergeTree or CollapsingMergeTree" -- https://clickhouse.com/docs/en/optimize/avoid-mutations | `clickhouse_connect` client `.command("ALTER TABLE t UPDATE col=... WHERE ...")` or `.command("ALTER TABLE t DELETE WHERE ...")` | `client.command({ query: 'ALTER TABLE t UPDATE ...' })` (clickhouse-js) | Go `clickhouse-go` `Exec("ALTER TABLE ... UPDATE ...")` | static: yes (parse SQL string for `ALTER TABLE ... UPDATE`/`DELETE`) |
| 2 | Primary-key point lookups / row-by-row access pattern against a columnar store designed for scan-heavy analytical queries | Same ClickHouse mutations page's framing of column-oriented, immutable storage as the reason per-row operations are costly -- https://clickhouse.com/docs/en/optimize/avoid-mutations | Loop issuing `client.query(f"SELECT * FROM t WHERE id = {row_id}")` per row (N+1 style against ClickHouse) | Same loop shape in Node client | -- | static: yes (DB call inside a loop, same detector family as document-store N+1) |
| 3 | High-cardinality tag columns in InfluxDB (unique IDs, timestamps, hashes used as tags rather than fields) | InfluxDB OSS v2 docs, "Resolve high series cardinality": "Tags containing highly variable information like unique IDs, hashes, and random strings lead to a large number of series... a primary driver of high memory usage" and specifically calls out "Writing log messages to tags... Writing timestamps to tags... Unique tag values that grow over time" as common causes -- https://docs.influxdata.com/influxdb/v2/write-data/best-practices/resolve-high-cardinality/ | `Point("measurement").tag("request_id", uuid).tag("timestamp", ts)` (influxdb-client-python) -- tagging with UUID/timestamp-like values | `new Point('m').tag('requestId', uuid)` (influxdb-client-js) | -- | config/dynamic (needs to know the tag value's semantic source -- heuristic: variable name matches `id`/`uuid`/`timestamp`/`hash` bound into `.tag()` rather than `.field()`) |
| 4 | Point deletes on TimescaleDB hypertables instead of chunk-based/partition drops | TimescaleDB docs, "About constraints" page fetched (https://docs.timescale.com/use-timescale/latest/schema-management/about-constraints/); this pass did not isolate a standalone point-delete-cost quote from that specific page -- **gap**, cite general Timescale architecture instead (not independently re-fetched this pass) | `cursor.execute("DELETE FROM hypertable WHERE id = %s", (row_id,))` in a per-row loop | Same shape via node-postgres against a hypertable | -- | static: yes for the call shape; needs schema knowledge (is this table a hypertable) to be non-heuristic -- tag as config |
| 5 | Row-by-row `INSERT` instead of batched writes into time-series stores optimized for batch ingestion | ClickHouse and InfluxDB both structurally favor batch writes (columnar part creation / line-protocol batch writes); a standalone "batch your inserts" quote was not isolated verbatim from the fetched pages this pass -- **gap** | `for row in rows: client.command(f"INSERT INTO t VALUES ({row})")` (ClickHouse) or `write_api.write(bucket, record=point)` per point in a loop (InfluxDB) | Same per-row loop shape in JS clients | -- | static: yes (single-row insert call inside a loop over an in-memory collection) |

---

## 7. Object storage (S3/GCS) as a database

**Good for / bad for:** AWS's own guidance treats `ListObjects`/listing as an
operational/administrative API, not a query mechanism, and directs users
toward prefix design rather than scanning: the S3 CLI/SDK docs page fetched
this pass (AWS docs, "Listing object keys programmatically",
https://docs.aws.amazon.com/AmazonS3/latest/userguide/ListingKeysUsingAPIs.html)
documents `ListObjects`/`ls`-style operations as the retrieval mechanism, and
AWS's separate performance guidance (page referenced, not independently
quoted this pass) frames prefix/key design as the lever for listing/access
performance rather than per-object metadata querying, which S3 does not
support natively (no server-side query language over object metadata).

| # | Anti-pattern | Authority (title, URL, quote) | Python call shapes | TS/JS call shapes | Rust/Go | Static? |
|---|---|---|---|---|---|---|
| 1 | Listing an entire bucket/prefix (`ListObjectsV2` with no prefix or with unbounded pagination) to "find" an object instead of storing/looking up the key directly (e.g., in a real database index) | AWS docs, "Listing object keys programmatically" confirms `ListObjects`/`ls` as the API surface for enumeration (https://docs.aws.amazon.com/AmazonS3/latest/userguide/ListingKeysUsingAPIs.html); this pass did not isolate a standalone "don't use listing as a query mechanism" caveat verbatim -- **partial gap** | `boto3.client('s3').list_objects_v2(Bucket=b)` called repeatedly / in a loop with `ContinuationToken` to search for a specific object by attribute | `s3.send(new ListObjectsV2Command({ Bucket: b }))` in a loop searching by attribute | Go `s3.ListObjectsV2` in a loop | static: yes (call-shape: `list_objects*`/`ListObjectsV2` result filtered/searched in app code rather than a direct `get_object`/`head_object` by known key) |
| 2 | Per-object metadata queries via repeated `HeadObject`/`GetObject` calls to filter a large set, instead of maintaining an external index (DB) of object metadata | Same page family; S3 has no query-by-metadata API, so any "query" necessarily becomes N `HeadObject` calls -- structural absence of the capability is the signal (no dedicated quote sourced this pass -- **gap**) | Loop: `for key in keys: s3.head_object(Bucket=b, Key=key)` to filter by metadata before use | Loop of `HeadObjectCommand` calls | -- | static: yes (S3 metadata call inside a loop over a candidate key list, same N+1 family) |
| 3 | Using S3 key names as a queryable "schema" (e.g., encoding many filterable attributes into the key path and relying on prefix listing to filter) instead of a database | Same listing-API page; AWS's own prefix-design guidance (performance page referenced but not independently quoted this pass) positions prefixes as a throughput/parallelism lever, not a general-purpose query layer -- **gap for a direct anti-quote** | Key construction like `f"data/{tenant}/{year}/{status}/{id}.json"` followed by `list_objects_v2(Prefix=...)` used as the primary lookup path for business queries | Same key-construction + `ListObjectsV2Command({ Prefix })` pattern | -- | dynamic-only (requires knowing listing is the *primary* query path vs an occasional operational tool) |

---

## 8. Workload-versus-paradigm mismatch (cross-cutting signals)

| # | Signal | Authority | Code shape a linter can see | Static? |
|---|---|---|---|---|
| 1 | Many-to-many relationship modeled in a document store with manual application-side join loops (fetch parent, loop, fetch each child) | MongoDB's own reference-modeling docs document the join cost of the reference approach as the explicit tradeoff against embedding -- https://www.mongodb.com/docs/manual/tutorial/model-referenced-one-to-many-relationships-between-documents/ | `find`/`find_one` call inside a loop over a previous query's result set (same N+1 shape flagged in Document section #3) | static: yes |
| 2 | Per-request full-collection/table/index scan (no filter, no limit) in a request-serving code path, regardless of paradigm | Cross-paradigm: MongoDB "Indexes" page (scan-without-index framing, https://www.mongodb.com/docs/manual/indexes/), Elasticsearch "Paginate search results" (shard-load-into-memory framing, https://www.elastic.co/guide/en/elasticsearch/reference/current/paginate-search-results.html) | Query call with no filter/`WHERE`/`match`/predicate argument, located inside a function reachable from an HTTP route handler (call-graph reachability from a router decorator/registration) | static: yes for the call shape; config for "is this reachable from a request handler" (needs light call-graph) |
| 3 | Write pattern requiring multi-entity ACID (all-or-nothing across several records/collections) issued against a store without native multi-record transactions (e.g., plain Redis pipeline, or DynamoDB writes without `TransactWriteItems`) | Redis: pipelining is documented as request/response batching, not atomicity, per Redis's own command-reference distinction between `MULTI/EXEC` (atomic) and plain pipelining (not inherently atomic) -- https://redis.io/docs/latest/develop/using-commands/pipelining/ (page fetched; confirms pipelining as a batching optimization distinct from transactions, consistent with Redis's separate `MULTI`/`EXEC`/`WATCH` transaction docs, not independently fetched this pass -- partial gap) | Multiple sequential single-item writes (`r.set`, `table.put_item`, `collection.update_one`) across different keys/entities within one logical operation, with no surrounding `MULTI`/`WATCH`, `TransactWriteItems`, or DB transaction call | static: yes (detect >1 independent write call to different keys/entities inside one function with no transaction wrapper present) |
| 4 | Recursive/hierarchical, relationship-heavy traversal implemented as repeated relational queries (manual "walk the tree" loops issuing one query per level) instead of a recursive CTE or a graph DB | Neo4j's own traversal-oriented tuning guidance (bounded variable-length paths) implicitly frames this as the graph DB's core competency being reimplemented elsewhere -- https://neo4j.com/docs/cypher-manual/current/query-tuning/ | Loop that issues a `SELECT ... WHERE parent_id = ?` query once per tree level/depth, building up a result set across iterations | static: yes (DB call inside a `while`/recursive-function loop keyed on a `parent_id`/`ancestor` style column) |

---

## Gaps and fetch-failure notes (explicit, not rounded to "done")

- `redis.io/docs/latest/develop/reference/persistence/` returned a 404
  ("Page not found | Redis"); the correct persistence URL was
  `redis.io/docs/latest/operate/oss_and_stack/management/persistence/`, which
  was refetched successfully and is the URL cited above.
- `redis.io/docs/latest/develop/reference/pipelining/` returned an empty
  shell (likely a redirect stub); refetched successfully at
  `redis.io/docs/latest/develop/using-commands/pipelining/` and cited above,
  but only the batching-vs-atomicity framing was pulled, not a full
  `MULTI`/`EXEC`/`WATCH` transaction-guarantee quote (see cross-cutting #3
  gap note).
- `docs.aws.amazon.com/.../bp-use-scan-sparingly.html` and the first
  `Query-and-Scan-Operations-in-DynamoDB.html` fetch both returned only page
  title/nav shell text ("Amazon DynamoDB") with no body -- likely JS-rendered
  content not present in server HTML. Marked as **fetch failed / JS-rendered**
  in Document anti-pattern #8; not backed by a verbatim vendor quote in this
  file as a result.
- `docs.influxdata.com/.../resolve-high-cardinality/` initial fetch returned
  raw gzip bytes (curl without `--compressed` against a server serving
  gzip-encoded content); refetched with `--compressed` and succeeded --
  content used in Time-series section #3.
- Postgres "Don't Do This" wiki page
  (https://wiki.postgresql.org/wiki/Don%27t_Do_This) was fetched (~410 lines
  of stripped text) but a targeted grep for EAV/queue-specific verbatim
  language did not surface a matching quote in this pass; Relational
  anti-patterns #2 and #3 are therefore sourced from the page's general
  existence/framing rather than a specific pull-quote -- flagged inline as
  gaps in those rows.
- Elasticsearch "Tune for search speed" page was fetched but a targeted
  script-fields-cost quote was not isolated from the stripped text in this
  pass (page is large, ~439 lines after stripping) -- Search anti-pattern #3
  is under-cited as a result.
- Neo4j Cartesian-product and OLAP-mismatch claims (Graph #4, #6) are
  inferred from the tuning/patterns pages fetched rather than a standalone
  verbatim warning -- flagged inline.
- S3 per-object-query and key-as-schema anti-patterns (Object storage #2,
  #3) rely on the structural absence of a query API rather than a vendor
  "don't do this" quote, since S3 docs describe capabilities, not
  anti-patterns, for this topic -- flagged inline as an inherent limitation
  of primary-source framing for this paradigm.
- No CouchDB, Firestore-specific (beyond general document-model framing),
  Memcached-specific, ArangoDB-specific, Neptune-specific, Meilisearch/
  Typesense-specific, or MySQL/SQLite-specific vendor pages were fetched in
  this pass; those vendors' names appear in the paradigm list as client
  libraries/products to cover but their own docs were not independently
  sourced -- the paradigm-level anti-patterns above are sourced from the
  lead vendor in each paradigm (Postgres for relational, MongoDB for
  document, Redis for key-value, Neo4j for graph, Elasticsearch for search,
  ClickHouse/InfluxDB for time-series, AWS S3 for object storage) per the
  task's "at least" framing, and should be treated as a first pass, not a
  per-product-exhaustive one.

## Coverage checklist (Phase 2 reconciliation)

Paradigms (7 required, all addressed):
- [x] Relational -- 7 anti-patterns sourced (2 with partial-gap citations)
- [x] Document -- 8 anti-patterns sourced (2 with gap/JS-render notes)
- [x] Key-value/cache -- 7 anti-patterns sourced (2 with gap notes)
- [x] Graph -- 6 anti-patterns sourced (2 with gap notes)
- [x] Search -- 5 anti-patterns sourced (3 with gap notes)
- [x] Time-series/columnar -- 5 anti-patterns sourced (2 with gap notes)
- [x] Object storage -- 3 anti-patterns sourced (2 with partial-gap notes)
- [x] Workload-vs-paradigm mismatch -- 4 cross-cutting signals sourced (1
      with partial-gap note)

Requested anti-pattern categories from the task, explicitly checked:
- [x] JSON-blob-as-model (Relational #1)
- [x] EAV (Relational #2, gap-flagged)
- [x] DB-as-queue (Relational #3, gap-flagged)
- [x] DB-as-cache/pubsub (Relational #4 covers cache; pubsub not separately
      sourced for relational -- **not covered**, minor gap)
- [x] Unbounded LIKE search (Relational #5, gap-flagged)
- [x] Large binaries in relational DB (Relational #6)
- [x] Unbounded array growth (Document #1)
- [x] Unbounded documents / 16MB limit (Document #2)
- [x] Application-side joins / $lookup hot path / N+1 find (Document #3)
- [x] Missing index hints / scans without filter (Document #4)
- [x] Transactions across many documents (Document #5)
- [x] Schema-less drift (Document #6)
- [x] KEYS in production (KV #1)
- [x] Unbounded SMEMBERS/HGETALL/LRANGE 0 -1 (KV #2)
- [x] No TTL on cache keys (KV #3)
- [x] Redis as durable primary without persistence config (KV #4)
- [x] Large values (KV #5, gap-flagged)
- [x] Non-atomic check-then-set (KV #6)
- [x] Blocking commands on shared connection (KV #7, gap-flagged)
- [x] Unbounded variable-length path, no LIMIT (Graph #1, #2)
- [x] Cartesian product in MATCH (Graph #4, gap-flagged)
- [x] Recursive CTE instead of graph DB (Graph #5 / Relational #7 /
      cross-cutting #4)
- [x] Graph DB for tabular aggregation (Graph #6, gap-flagged)
- [x] Search index as source of truth (Search #4, gap-flagged)
- [x] Deep pagination from/size (Search #1)
- [x] Wildcard-leading queries (Search #2)
- [x] Script fields in hot path (Search #3, gap-flagged)
- [x] Point updates/deletes (Time-series #1, #4)
- [x] Primary-key lookups (Time-series #2)
- [x] High-cardinality tags (Time-series #3)
- [x] Listing buckets to find objects (Object storage #1)
- [x] Per-object metadata queries (Object storage #2, gap-flagged)
- [x] Many-to-many in document store with manual joins (cross-cutting #1)
- [x] Per-request full-collection scans (cross-cutting #2)
- [x] Write patterns needing multi-entity ACID without it (cross-cutting #3,
      gap-flagged)

Verdict: universe of 7 paradigms + 1 cross-cutting section fully enumerated
and drained (0 pending). All requested anti-pattern categories addressed
except relational pub/sub-as-DB, which is a minor, explicitly flagged gap
(1 category not separately sourced; folded into DB-as-queue coverage
conceptually but not cited). 13 individual rows across the tables carry an
explicit inline gap/partial-gap citation note (verbatim vendor quote not
isolated in this pass, or page returned JS-rendered/empty content) rather
than being silently presented as fully sourced. Two page fetches failed
outright on first attempt and were successfully recovered on retry (Redis
persistence 404, Redis pipelining stub, InfluxDB gzip); one DynamoDB Scan
page and one DynamoDB Query/Scan comparison page remained JS-rendered/empty
after retry and are marked blocked rather than dropped.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"

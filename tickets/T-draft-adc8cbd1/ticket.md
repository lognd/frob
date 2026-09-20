---
id: T-draft-adc8cbd1
title: 'SQL: extract SQL from host languages, sqlfluff as parser with a frob rule
  plugin for performance semantics, squawk for migrations, ORM N+1 and pooling rules,
  EXPLAIN obligation on flagged queries'
state: queued
kind: feature
origin: human
created: '2026-09-20'
priority: high
parent: T-draft-09897a86
tier: story
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'owner 2026-09-20: carry the research corpus in the ticket body, not only
    as an attachment'
  actor: logan
  at: '2026-09-20'
  old_length: 1794
  new_length: 23704
designated_repro_test: null
attachments:
- path: T-draft-adc8cbd1/attachments/01-untitled.md
  caption: ''
  sha256: d7d52247be114d264d1f193a9a1b5685b25bad3fa52a8945620e9032c058499c
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
30 entries, 23 static. Engine decision: sqlfluff (real multi-dialect parser, plugin API) for parsing and style; frob ships the performance rules sqlfluff lacks as a sqlfluff plugin: HAVING used as WHERE, WHERE vs ON placement on outer joins (semantic difference), SELECT *, non-sargable predicates (function on column, leading-wildcard LIKE, implicit casts), NOT IN over nullable subquery, OR across columns, correlated subquery where a join fits, DISTINCT masking join fan-out, COUNT(*) vs EXISTS, OFFSET pagination, no LIMIT on interactive queries, UPDATE/DELETE without WHERE, ORDER BY without supporting index and LIMIT, missing statement_timeout, long transactions. squawk as the migration-safety adapter (NOT NULL without default, index without CONCURRENTLY, lock-taking rewrites). Extraction: tree-sitter pulls SQL literals and f-string skeletons from cursor.execute, SQLAlchemy text(), Django raw(), Prisma queryRaw, sqlx macros, asyncpg/psycopg calls; any non-literal composition is the injection finding (WEBSEC) except psycopg.sql composition. ORM rules in Python/TS: N+1 from lazy relationship access inside a loop (SQLAlchemy without joinedload/selectinload, Django without select_related/prefetch_related, Prisma without include), .all() without limit on request paths, filter-after-fetch, missing index on FK/WHERE/ORDER columns cross-checked against migrations and models, missing transaction around multi-statement writes, no connection pool config. Proof: a query flagged for performance carries an EXPLAIN ANALYZE obligation before waiver. Authorities: PostgreSQL docs 7.1-7.2 and indexing chapters, MySQL and SQL Server docs, use-the-index-luke, ORM docs. Tools sqlfluff and squawk registered as relevant when SQL literals, .sql files or migrations exist (T-draft-94870246).

# SQL anti-pattern lint authorities

Fills gaps left in lint-authorities.md section F. Sources fetched this pass:
PostgreSQL docs (7.2 Table Expressions -- already cited as F1; SELECT
reference, ddl-constraints.html -- already cited as F2, sql-explain.html,
indexes-types.html), use-the-index-luke.com (already cited as F3),
SQLAlchemy and Rails ORM docs (already cited in lint-seo-web-full.md items
36-37, cross-referenced rather than restated).

### 1. HAVING used where WHERE would suffice
Authority: PostgreSQL Documentation, 7.2.3 The GROUP BY and HAVING Clauses (cross-reference lint-authorities.md item F1)
URL: https://www.postgresql.org/docs/current/queries-table-expressions.html
Quote: same quote as lint-authorities.md item F1 -- "The optional WHERE, GROUP BY, and HAVING clauses in the table expression specify a pipeline of successive transformations."
Lint condition: SQL-linter rule flagging a `HAVING` predicate that references only ungrouped, non-aggregate columns (no `SUM`/`COUNT`/`AVG`/etc.), which should be a `WHERE` predicate evaluated before grouping instead.
Static: yes

### 2. Filtering in WHERE vs ON for outer joins (semantic difference)
Authority: PostgreSQL Documentation, 7.2.1 Joined Tables / SELECT reference
URL: https://www.postgresql.org/docs/current/sql-select.html
Quote: "LEFT OUTER JOIN returns all rows in the qualified Cartesian product ... plus one copy of each row in the left-hand table for which there was no right-hand row that passed the join condition ... Note that only the JOIN clause's own condition is considered while deciding which rows have matches. Outer conditions are applied afterwards."
Lint condition: SQL-linter rule flagging a `LEFT JOIN ... ON a.id = b.a_id` followed by a `WHERE b.column = 'x'` predicate on the right-hand (nullable) table, which silently converts the outer join into an inner join by discarding unmatched left rows -- the filter belongs in the `ON` clause if the outer-join semantics are intended to be preserved.
Static: yes

### 3. SELECT *
Authority: general SQL best-practice guidance; PostgreSQL's own SELECT reference documents explicit column lists as the alternative to `*` (not independently re-quoted with a dedicated anti-`SELECT *` sentence this pass -- flagging as a paraphrase)
URL: https://www.postgresql.org/docs/current/sql-select.html
Quote: BLOCKED for a verbatim "don't use SELECT *" quote this pass; the SELECT reference documents `*` as shorthand for "all columns" without qualifying its performance/maintainability tradeoffs, which are the well-documented industry rationale (schema-change breakage, unnecessary I/O, defeats covering indexes).
Lint condition: SQL-linter rule flagging any `SELECT *` in application code (as opposed to ad hoc interactive queries), especially inside a view definition or a hot-path query.
Static: yes

### 4. Non-sargable predicates -- function on an indexed column
Authority: PostgreSQL Documentation, 11.2.1 B-Tree indexes
URL: https://www.postgresql.org/docs/current/indexes-types.html
Quote: "B-trees can handle equality and range queries on data that can be sorted into some ordering. In particular, the PostgreSQL query planner will consider using a B-tree index whenever an indexed column is involved in a comparison using one of these operators [=, <, <=, >, >=]" -- implying a wrapped column (`WHERE lower(email) = ...`) is no longer "an indexed column involved in a comparison" and the planner cannot use the plain index.
Lint condition: SQL-linter rule flagging `WHERE func(column) = value` (e.g., `LOWER(email) = 'x'`, `DATE(created_at) = 'x'`) with no matching expression index (`CREATE INDEX ON t (func(column))`) on that exact expression.
Static: yes

### 5. Non-sargable predicates -- leading-wildcard LIKE
Authority: PostgreSQL Documentation, 11.2.1 B-Tree (same section as item 4); leading-wildcard `LIKE '%x'` cannot use a standard B-tree prefix scan, a well-documented consequence of B-tree ordering (not restated as a dedicated sentence in the fetched page this pass -- flagging as a paraphrase).
URL: https://www.postgresql.org/docs/current/indexes-types.html
Quote: BLOCKED for a verbatim "leading wildcard defeats the index" quote this pass; derivable from the B-tree ordering description quoted in item 4 (a B-tree can only seek from a known prefix).
Lint condition: SQL-linter rule flagging `LIKE '%term'`/`LIKE '%term%'` on a column with only a standard B-tree index and no trigram (`pg_trgm`) or full-text index, unless the table is small enough that a sequential scan is acceptable by design.
Static: yes

### 6. Implicit type conversion defeating index usage
Authority: same B-tree comparison-operator framing as item 4
URL: https://www.postgresql.org/docs/current/indexes-types.html
Quote: same as item 4 -- the planner requires the comparison to be on "an indexed column," which an implicit cast (e.g., comparing a `text` column to an `integer` literal, forcing a cast on the column side) breaks.
Lint condition: SQL-linter rule flagging a `WHERE` predicate comparing a typed column against a literal/parameter of a different type where the database would need to cast the column (rather than the literal) to evaluate it.
Static: yes

### 7. NOT IN with a nullable subquery
Authority: general SQL semantics (documented behavior across PostgreSQL/MySQL/SQL Server: if the subquery in `NOT IN (subquery)` returns any NULL, the entire `NOT IN` expression evaluates to unknown/false for all rows) -- not independently re-quoted from a dedicated primary-source sentence this pass, flagging as a paraphrase.
URL: not independently re-fetched a dedicated primary-source page for this specific NULL-semantics gotcha this pass.
Lint condition: SQL-linter rule flagging `WHERE col NOT IN (SELECT nullable_col FROM ...)` with no `WHERE nullable_col IS NOT NULL` filter inside the subquery, or recommending `NOT EXISTS` as the NULL-safe alternative.
Static: yes

### 8. OR across columns vs UNION
Authority: general query-planner guidance (an `OR` across two different indexed columns often cannot use a single combined index scan as efficiently as two separate indexed scans combined via `UNION`/`BitmapOr`; PostgreSQL's planner does support `BitmapOr` in many cases, so this is a "check with EXPLAIN" item, not an absolute rule) -- not independently re-quoted from a dedicated primary-source sentence this pass.
URL: https://www.postgresql.org/docs/current/sql-explain.html (the EXPLAIN authority for verifying this per item 16, not a direct citation for the OR/UNION tradeoff itself)
Quote: BLOCKED for a verbatim quote on the OR/UNION tradeoff itself this pass.
Lint condition: dynamic-only in general (requires an actual EXPLAIN plan comparison); static check limited to flagging a `WHERE col_a = x OR col_b = y` predicate across two separately-indexed columns as a candidate for EXPLAIN review against a `UNION` rewrite.
Static: dynamic-only

### 9. Correlated subquery vs join
Authority: general SQL-performance guidance; PostgreSQL's planner can sometimes decorrelate simple subqueries but not all forms -- not independently re-quoted from a dedicated primary-source sentence this pass.
URL: not independently re-fetched a dedicated primary-source page for this item this pass.
Lint condition: SQL-linter rule flagging a `SELECT ... WHERE col = (SELECT ... FROM t2 WHERE t2.fk = t1.id)` correlated-subquery pattern in a hot-path query as a candidate for rewriting as an explicit `JOIN`, verified via `EXPLAIN ANALYZE` per item 16.
Static: dynamic-only

### 10. DISTINCT masking a bad join (fan-out)
Authority: general SQL-antipattern guidance (a `SELECT DISTINCT` added to suppress duplicate rows produced by a one-to-many join is a documented symptom of an unintended row-multiplication join, not a fix) -- not independently re-quoted from a dedicated primary-source sentence this pass.
URL: not independently re-fetched a dedicated primary-source page for this item this pass.
Lint condition: SQL-linter rule flagging a query with both a `JOIN` to a one-to-many related table and a `DISTINCT`/`GROUP BY` on the parent table's primary key with no aggregate function used, suggesting the join produced unwanted row duplication.
Static: yes

### 11. COUNT(*) vs EXISTS for existence checks
Authority: general SQL-performance guidance (documented pattern: `SELECT EXISTS(SELECT 1 FROM t WHERE ...)` can short-circuit on the first match, whereas `SELECT COUNT(*) FROM t WHERE ...` must scan/count all matching rows before returning) -- not independently re-quoted from a dedicated primary-source sentence this pass.
URL: not independently re-fetched a dedicated primary-source page for this item this pass.
Lint condition: SQL-linter/ORM-call lint flagging `COUNT(*) > 0` (or `.count() > 0` in an ORM) used purely to test row existence, recommending `EXISTS`/`.exists()` instead.
Static: yes

### 12. OFFSET pagination (cross-ref)
Authority: use-the-index-luke.com, "No Offset" (cross-reference lint-authorities.md item F3)
URL: https://use-the-index-luke.com/no-offset
Quote: same quote as lint-authorities.md item F3.
Lint condition: same as lint-authorities.md item F3 -- cross-referenced rather than restated.
Static: yes

### 13. Missing LIMIT on interactive/user-facing queries
Authority: general operational-safety guidance; cross-reference item 12's pagination authority for the same "unbounded result set" risk class.
URL: https://use-the-index-luke.com/no-offset
Quote: same underlying concern as item F3 -- an unbounded query against a growing table degrades linearly with table size.
Lint condition: SQL-linter rule flagging a `SELECT` issued from a user-facing request handler with no `LIMIT` clause and no pagination parameter at all (distinct from item 12, which is about OFFSET specifically vs keyset; this item is about queries with no bound whatsoever).
Static: yes

### 14. UPDATE/DELETE without WHERE
Authority: general SQL-safety guidance; documented behavior across all major RDBMSes that an `UPDATE`/`DELETE` with no `WHERE` clause affects every row in the table -- not independently re-quoted from a dedicated primary-source sentence this pass (this is base SQL semantics, not a vendor-specific claim).
URL: not independently re-fetched a dedicated primary-source page for this item this pass.
Lint condition: SQL-linter rule (and a pre-commit/migration-review gate) flagging any `UPDATE table SET ...` or `DELETE FROM table` statement in application code or a migration file with no `WHERE` clause and no explicit comment/flag marking it as an intentional full-table operation.
Static: yes

### 15. Missing index on FK/WHERE/ORDER/JOIN columns
Authority: PostgreSQL Documentation, 5.5.5 Foreign Keys (cross-reference lint-authorities.md item F2) and 11.2.1 B-Tree (item 4's authority, extended to WHERE/ORDER/JOIN columns generally)
URL: https://www.postgresql.org/docs/current/ddl-constraints.html ; https://www.postgresql.org/docs/current/indexes-types.html
Quote: same FK quote as lint-authorities.md item F2, generalized here: any column repeatedly used in `WHERE`, `ORDER BY`, or `JOIN ... ON` predicates benefits from the same B-tree indexing rationale quoted in item 4.
Lint condition: schema/migration lint (extending F2) for a column referenced in a `WHERE`/`ORDER BY`/`JOIN ON` clause in application query code with no corresponding index in the schema, cross-checked via `EXPLAIN` (item 16) showing a sequential scan on a large table.
Static: yes

### 16. EXPLAIN ANALYZE as the proof step
Authority: PostgreSQL Documentation, 14.1 Using EXPLAIN
URL: https://www.postgresql.org/docs/current/sql-explain.html
Quote: "Keep in mind that the statement is actually executed when the ANALYZE option is used. Although EXPLAIN will discard any output that a SELECT would return, other side effects of the statement will happen as usual." (For non-`SELECT` statements, the docs recommend wrapping in a transaction and rolling back: `BEGIN; EXPLAIN ANALYZE ...; ROLLBACK;`.)
Lint condition: not a static code check on its own; a CI/review-process gate requiring a pasted `EXPLAIN ANALYZE` plan (showing no unindexed sequential scan on a large table) attached to any pull request that adds or modifies a query touching a table above a documented row-count threshold.
Static: dynamic-only

### 17. Indexes on low-cardinality columns
Authority: general index-design guidance (a B-tree index on a column with very few distinct values, e.g., a boolean flag, is typically not selective enough for the planner to prefer it over a sequential scan) -- cross-reference the B-tree selectivity framing in item 4's PostgreSQL quote; not independently re-quoted with a dedicated low-cardinality sentence this pass.
URL: https://www.postgresql.org/docs/current/indexes-types.html
Quote: BLOCKED for a verbatim "low cardinality" quote this pass; derivable from the general B-tree comparison-operator framing already quoted in item 4, combined with well-documented query-planner cost-estimation behavior (an index scan's cost estimate rises with the fraction of rows it must fetch).
Lint condition: schema-review lint flagging a standalone index created on a boolean or very-low-distinct-value column with no compound-index/partial-index justification, since it usually adds write overhead with little read benefit.
Static: config

### 18. Redundant indexes
Authority: general index-design guidance; PostgreSQL's own B-tree documentation (item 4's authority) implies a compound index `(a, b)` already serves queries filtering on `a` alone, making a separate single-column index on `a` redundant -- not independently re-quoted with a dedicated redundancy sentence this pass.
URL: https://www.postgresql.org/docs/current/indexes-types.html
Quote: BLOCKED for a verbatim "redundant index" quote this pass; derivable from B-tree leftmost-prefix matching behavior, a well-documented consequence of the ordering property already cited in item 4.
Lint condition: schema lint flagging a single-column index on `a` that is a strict leftmost prefix of an existing compound index `(a, b, ...)` on the same table, recommending the single-column index be dropped unless it is needed as a covering/unique constraint independently.
Static: yes

### 19. N+1 from ORM lazy loading (cross-ref)
Authority: SQLAlchemy Relationship Loading Techniques; Rails Active Record Querying `includes` (cross-reference lint-seo-web-full.md items 36-38)
URL: https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html ; https://guides.rubyonrails.org/active_record_querying.html
Quote: same quotes as lint-seo-web-full.md items 36-37.
Lint condition: cross-referenced rather than restated -- see lint-seo-web-full.md items 36-38.
Static: yes

### 20. Missing transactions around multi-statement writes
Authority: PostgreSQL Documentation, transaction-control framing (cross-reference ASVS V2.3.3, already cited in lint-appsec-authz-business-llm.md item 12); PostgreSQL's own tutorial chapter on transactions (not independently re-fetched a dedicated URL this pass beyond the ASVS cross-reference -- flagging as a partial gap).
URL: https://github.com/OWASP/ASVS (V2.3.3, cross-referenced) ; PostgreSQL transactions chapter not independently re-fetched this pass.
Quote: ASVS V2.3.3 (already quoted in lint-appsec-authz-business-llm.md item 12): "Verify that transactions are being used at the business logic level such that either a business logic operation succeeds in its entirety or it is rolled back to the previous correct state."
Lint condition: code lint for a code path issuing two or more related `INSERT`/`UPDATE`/`DELETE` statements (e.g., debit one row, credit another) with no surrounding `BEGIN`/`COMMIT` (or ORM transaction block), risking a partial write on failure between statements.
Static: yes

### 21. Long-running transactions holding locks
Authority: general PostgreSQL operational guidance (a transaction left open while performing slow non-DB work -- an external API call, a large in-memory computation -- holds its row/table locks and blocks other writers) -- not independently re-quoted from a dedicated primary-source sentence this pass.
URL: not independently re-fetched a dedicated primary-source page for this item this pass.
Lint condition: code lint for a database transaction block that contains a network call (HTTP request, external API, email send) between the `BEGIN` and `COMMIT`, rather than performing all external I/O before opening or after closing the transaction.
Static: yes

### 22. SELECT ... FOR UPDATE misuse
Authority: general PostgreSQL locking guidance (row-level locking via `SELECT ... FOR UPDATE` is the documented mechanism for pessimistic concurrency control, but acquiring it without a bounded transaction scope, or acquiring locks on rows in inconsistent order across code paths, is a well-documented deadlock risk) -- not independently re-quoted from a dedicated primary-source sentence this pass.
URL: not independently re-fetched a dedicated primary-source page for this item this pass.
Lint condition: code lint for two or more code paths that acquire `SELECT ... FOR UPDATE` locks on multiple tables/rows in a different order from each other, a classic deadlock precondition; and for a `FOR UPDATE` lock held across a network call (same class as item 21).
Static: yes

### 23. String-built SQL / no prepared statements (cross-ref)
Authority: cross-reference lint-appsec-injection-output.md item 5 (ASVS V1.2.4) and lint-authorities.md item E5.
URL: https://github.com/OWASP/ASVS
Quote: same as lint-appsec-injection-output.md item 5.
Lint condition: cross-referenced rather than restated -- see lint-appsec-injection-output.md item 5.
Static: yes

### 24. No connection pooling (cross-ref)
Authority: cross-reference lint-seo-web-full.md item 34 (PgBouncer)
URL: https://www.pgbouncer.org/
Quote: same partial-gap note as lint-seo-web-full.md item 34.
Lint condition: cross-referenced rather than restated -- see lint-seo-web-full.md item 34.
Static: config

### 25. No statement timeout configured
Authority: general PostgreSQL operational guidance (the `statement_timeout` server/session parameter is a well-documented PostgreSQL configuration setting; its specific reference-manual page was not independently re-fetched this pass) -- flagging as a partial gap.
URL: not independently re-fetched a dedicated `statement_timeout` runtime-config-parameters page this pass.
Lint condition: database-config lint for a connection pool/role with no `statement_timeout` set, allowing a single runaway query to hold resources indefinitely.
Static: config

### 26. CTE materialization pitfalls
Authority: PostgreSQL Documentation, WITH Queries (Common Table Expressions) -- not independently re-fetched a dedicated URL this pass; PostgreSQL 12+ changed CTEs to be inlined ("not materialized") by default unless recursive or referenced multiple times, a well-documented behavior change from pre-12 versions where every CTE was an optimization fence.
URL: not independently re-fetched a dedicated URL this pass -- BLOCKED for a verbatim quote.
Lint condition: SQL-linter rule flagging a CTE explicitly marked `MATERIALIZED` (or relying on pre-12 optimization-fence behavior) that is then filtered by an outer `WHERE` clause which could otherwise have been pushed down into the CTE, recommending `NOT MATERIALIZED` (the modern default) unless the fence is intentional (e.g., for a data-modifying CTE run once).
Static: yes

### 27. Implicit cross joins
Authority: PostgreSQL Documentation, SELECT reference (cross-reference item 2's authority)
URL: https://www.postgresql.org/docs/current/sql-select.html
Quote: same join-clause text cited in item 2; a comma-separated `FROM a, b` with no `WHERE` join predicate produces "the Cartesian product of their rows," per the general FROM-list behavior documented in lint-authorities.md item F1's quoted text.
Lint condition: SQL-linter rule flagging a `FROM table_a, table_b` (old-style implicit join) with no corresponding `WHERE table_a.fk = table_b.id` predicate joining them, distinguishing an intentional cross join from an accidentally-omitted join condition.
Static: yes

### 28. ORDER BY without a supporting index and no LIMIT
Authority: cross-reference item 15 (index-on-ORDER-BY-columns) and item 13 (missing LIMIT)
URL: https://www.postgresql.org/docs/current/indexes-types.html
Quote: same B-tree ordering-support quote as item 4 -- a B-tree index can satisfy an `ORDER BY` on its indexed column(s) without a separate sort step, per the documented ordering property.
Lint condition: SQL-linter rule flagging a query with `ORDER BY column` on an unindexed column and no `LIMIT`, which forces a full sort of the entire result set.
Static: yes

### 29. GROUP BY on an expression with no matching index
Authority: cross-reference item 4 (expression-index framing)
URL: https://www.postgresql.org/docs/current/indexes-types.html
Quote: same as item 4, applied to `GROUP BY` rather than `WHERE`.
Lint condition: SQL-linter rule flagging `GROUP BY func(column)` on a large table with no expression index on `func(column)`, forcing a full aggregate scan/sort per query.
Static: yes

### 30. Window functions vs self-join
Authority: general SQL-modernization guidance (a window function, e.g., `ROW_NUMBER() OVER (PARTITION BY ...)`, is documented to compute the same result as a self-join-plus-aggregation pattern with a single pass over the data rather than a join-induced row multiplication) -- not independently re-quoted from a dedicated primary-source sentence this pass.
URL: not independently re-fetched a dedicated primary-source page for this item this pass.
Lint condition: SQL-linter rule flagging a self-join used purely to compute a running total, rank, or "latest row per group" pattern, recommending a window function (`ROW_NUMBER`, `RANK`, `SUM() OVER`) rewrite, verified against an `EXPLAIN` comparison per item 16.
Static: dynamic-only

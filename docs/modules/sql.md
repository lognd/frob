# frob.sql._extract -- SQL literal extraction + sqlfluff relevance

One sentence: `frob.sql._extract` walks Python/TypeScript/Rust host-language
AST via `frob.lang.raw_tree` to find SQL-executing call sites, extracting
each call's literal SQL text (or a `?`-holed skeleton for a non-literal
composition) for sqlfluff to parse, and flags a non-literal composition
reaching a sink as WEBSEC107 (CWE-89 SQL injection).

`frob.sql` is a `frob.lang`-only leaf (`[arch.layering.allow]`), never
`frob.webapp` -- SQL-executing call sites appear in code with no web
framework at all (migration scripts, CLI tools, ETL), so this package
stays independent of framework detection on purpose (see
`frob.sql.__init__`'s own docstring).

## Call shapes walked

| host language | call shape | `call_kind` |
| --- | --- | --- |
| Python | `<cursor>.execute(sql, ...)` | `python.execute` |
| Python | Django's `<queryset>.raw(sql)` | `python.raw` |
| Python | SQLAlchemy's bare `text(sql)` | `python.sqlalchemy_text` |
| TypeScript/JavaScript | Prisma tagged template `prisma.$queryRaw\`...\`` / `.$executeRaw\`...\`` | `ts.prisma_queryRaw` |
| TypeScript/JavaScript | Prisma plain call `prisma.$queryRaw(sql)` / `.$executeRaw(sql)` | `ts.prisma_queryRaw` |
| Rust | sqlx `query!`/`query_as!`/`query_scalar!` macro invocations | `rust.sqlx_query` / `rust.sqlx_query_as` / `rust.sqlx_query_scalar` |

Each grammar is read through `frob.lang.raw_tree` (T-5300/T-1604's shared
escape hatch, the same shape `frob.webapp._websec_sinks` uses for its own
JS/TS/Vue walk) -- this module never stands up a second parser.

## Literal vs non-literal, and WEBSEC107

A call site's SQL argument is either:

- a LITERAL: a plain string/template with no interpolation, extracted
  verbatim (`SqlLiteralExtraction.is_literal = True`) for sqlfluff to
  parse as-is;
- a non-literal composition: an f-string/tagged template with a
  substitution, or a `+`/`.format()`-built string -- extracted as a
  `?`-holed skeleton (`is_literal = False`) so sqlfluff still sees a
  parseable SQL shape around the hole.

A non-literal composition reaching a Python string-literal (f-string) or
binary-operator (concatenation) node is itself a WEBSEC107 finding
(CWE-89, reserved for this leaf in `frob.gates._waive._KNOWN_GATE_RULES`'s
T-5141 injection block) -- the same "source reaches a dangerous sink with
no validator/sanitizer hop" shape
`frob.webapp._websec_sinks.WebsecSinkFinding` uses for XSS, kept as this
module's own dataclass rather than importing `frob.webapp` (this package
stays a `frob.lang`-only leaf).

**Exclusion**: psycopg's `sql.SQL`/`sql.Identifier`/`sql.Composed`
composition API (matched by a textual-proxy regex over the call site's own
argument text, the same posture `frob.vet._taint` uses for its own
validator check) is a safe, parameterized composition primitive per the
T-5141 corpus, not a taint sink -- excluded from WEBSEC107 even though its
argument is non-literal. An opaque call/identifier argument (e.g.
`connection.execute(text(...))`'s own already-captured `text(...)` call)
is also not flagged: only a direct string/concatenation composition is,
since this module does not resolve what an opaque callee returns.

This is intra-statement, textual-proxy detection, not resolved data-flow
-- the same disclosed gap SEC005 (T-0781) and WEBSEC101-106 (T-5307)
already carry.

## `sql_relevance` -- the sqlfluff-required-for-family predicate

OWNER DIRECTIVE (T-5334): `sql_relevance(root)` is True if `root` has at
least one tracked `.sql` file OR at least one SQL-executing call site
(the same three host-language shapes above). This predicate is what makes
sqlfluff REQUIRED-for-the-family in 5148-2's tool-registry entry -- a
repo with no SQL surface at all reports sqlfluff's absence as
"unmeasured", not a failure (there is no never-fail flag: absence is
measured relative to whether SQL is actually present). Defined once here
so 5148-2 imports it rather than re-detecting.

## Public API

- `SqlLiteralExtraction` (`src/frob/sql/_extract.py`) -- one call site's
  extraction: `file`, `line`, `call_kind`, `sql_text`, `is_literal`.
- `SqlInjectionFinding` -- one WEBSEC107 finding: `rule`, `file`, `line`,
  `message`.
- `extract_sql_literals(root: Path) -> tuple[SqlLiteralExtraction, ...]`
  -- every SQL-executing call site's extraction under `root`.
- `sql_injection_findings(root: Path) -> tuple[SqlInjectionFinding, ...]`
  -- every WEBSEC107 finding under `root`.
- `sql_relevance(root: Path) -> bool` -- the sqlfluff-required-for-family
  predicate described above.

No gate wires `sql_injection_findings` into `frob check` yet -- that is a
later leaf of the T-5148 epic, the same "extraction substrate lands
before its gate registration" shape T-5302's `frob.sql` package stub
itself documents.

## `frob.sql._orm_rules` -- ORM N+1/pooling/transaction/index rules (T-5337)

`src/frob/sql/_orm_rules.py` is a Python-first (SQLAlchemy/Django) ORM
lint family, walked the same `frob.lang.raw_tree`-via-tree-sitter shape
`frob.sql._extract` already uses. It is the canonical owner of two things
sibling epics import instead of reimplementing: `migration_scan` (the
tracked-`.sql`-migration-file `CREATE INDEX` parser T-5145-3's COMPLY
GDPR storage-limitation PII-retention-TTL-column check blocks on) and the
DB-pool-config detection folded into SQL106 (T-5147-6/WEBPERF blocks on
this leaf for pool config instead of reimplementing it).

Five rule ids, one `orm_rule_findings(root)` call:

- **SQL101** -- a `for`-loop attribute access on the loop variable, with
  no `joinedload`/`selectinload`/`select_related`/`prefetch_related` call
  anywhere in the enclosing function (the classic N+1 lazy-relationship-
  in-a-loop shape).
- **SQL102** -- a bare `.all()` call with no `.limit(` in the same call
  chain -- an unbounded result set on a request path.
- **SQL104** -- an ORM model's `ForeignKey`-declared column with no
  matching index in any tracked migration file (`migration_scan`'s own
  index registry).
- **SQL105** -- two or more write calls (`.save(`, `.delete(`,
  `.execute(`, `.bulk_create(`, `.update(`) in one function body with no
  `atomic`/`transaction`/`begin` token anywhere in that body.
- **SQL106** -- no connection-pool config token (`pool_size`,
  `max_overflow`, `QueuePool`, a `pgbouncer` reference) anywhere in a
  repo `sql_relevance` reports real SQL surface for -- one repo-level
  finding (`file=""`, `line=0`), not a per-file one.

SQL103 (filter-after-fetch) and SQL107 (server-cache-layer-for-repeated-
expensive-queries) are OUT of this leaf's scope, filed as a follow-up
(see T-5337's own done-report) rather than widened in place. A
TypeScript/Prisma N+1 walk (Prisma's `include`/no-`include` mirrors
Django's `select_related`) is likewise a follow-up, not this leaf.

### Public API

- `OrmRuleFinding` -- one SQL10x finding: `rule`, `file`, `line`,
  `message`.
- `MigrationIndexInfo` -- one parsed `CREATE INDEX` statement: `file`,
  `table`, `columns`.
- `migration_scan(root: Path) -> tuple[MigrationIndexInfo, ...]` -- every
  `CREATE INDEX`/`CREATE UNIQUE INDEX` statement in tracked `.sql` files
  under `root`.
- `orm_rule_findings(root: Path) -> tuple[OrmRuleFinding, ...]` -- every
  SQL101/SQL102/SQL104/SQL105/SQL106 finding under `root`.

No gate wires `orm_rule_findings` into `frob check` yet -- a later leaf
folds it into a gate the same one-call-per-family shape
`frob.gates._taint_gate.taint_gate` already uses for
`websec_sink_findings`.

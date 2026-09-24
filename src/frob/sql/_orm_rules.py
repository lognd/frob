"""SQL101-106: ORM N+1/pooling/transaction/index rule family, plus the
migration-schema-scan helper (docs/modules/sql.md#orm-rules, T-5337, the
leaf T-5334's own docstring names as `frob.sql`'s next story item).

This leaf is the canonical owner of two things two sibling epics block on
instead of reimplementing: DB-pool-config detection (T-5147-6/WEBPERF
blocks here for pool config) and the migration-schema-scan helper
(T-5145-3/COMPLY GDPR storage-limitation blocks here for the PII-
retention-TTL-column check) -- both exposed as their own public functions
so those leaves import rather than re-parse migration files or re-sniff
pool config a second time.

Detection is Python-first (SQLAlchemy/Django), the same tree-sitter-via
`frob.lang.raw_tree` AST-walk shape `frob.sql._extract` already uses for
its own call-site scan -- this module never stands up a second parser.
A TypeScript/Prisma N+1 walk is the natural next leaf (Prisma's
`include`/no-`include` shape mirrors Django's `select_related`); left out
of this ticket's scope (`src/frob/sql/_orm_rules.py`,
`tests/fixtures/sql/**` only) and filed separately rather than widened in
place -- see T-5337's own done-report for the filed id.

Six rule ids, each folded into `orm_rule_findings`'s single return rather
than six separate entry points, matching `frob.webapp._websec_sinks`'s
"one findings function, N rule ids" shape a gate can wire in with one
call:

- SQL101: a `for`-loop body attribute-accesses a loop variable that is
  the iteration target of a bare `.query(...)`/`.objects`-style ORM
  fetch, with no `joinedload`/`selectinload`/`select_related`/
  `prefetch_related` call anywhere in the same function body (the classic
  N+1 lazy-relationship-in-a-loop shape).
- SQL102: a bare `.all()` call with no `.limit(` anywhere in the same
  call chain -- an unbounded result set on a request path.
- SQL104: an ORM model's `ForeignKey`-declared column with no matching
  index declared in any tracked migration file (`migration_scan`'s own
  index registry).
- SQL105: two or more write calls (`.save(`, `.delete(`, `cursor.execute`
  of an INSERT/UPDATE/DELETE) in the same function body with no
  `atomic`/`transaction`/`begin` wrapper token anywhere in that body.
- SQL106: no connection-pool config token (`pool_size`, `max_overflow`,
  `QueuePool`, PgBouncer's `pgbouncer.ini`) anywhere in a repo that has
  real SQL surface (`frob.sql._extract.sql_relevance`) -- a repo-level
  finding, not a per-file one (`file=""`, `line=0`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from tree_sitter import Node

from frob.gitio import run_argv
from frob.lang import child_by_field, node_text, raw_tree
from frob.logging import get_logger
from frob.sql._extract import sql_relevance

_log = get_logger(__name__)

__all__ = [
    "MigrationIndexInfo",
    "OrmRuleFinding",
    "migration_scan",
    "orm_rule_findings",
]

#: Tokens that mark a fetch as already eager-loaded -- Python ORM eager-
#: load call names (SQLAlchemy `joinedload`/`selectinload`, Django's
#: `select_related`/`prefetch_related`, Prisma's `include` kwarg name is
#: TS-only and out of this leaf's Python-first scope).
_EAGER_LOAD_NAMES = frozenset(
    {"joinedload", "selectinload", "select_related", "prefetch_related"}
)

#: Attribute names whose bare call is an unbounded-fetch shape when not
#: chained with `.limit(`.
_UNBOUNDED_FETCH_NAME = "all"
_LIMIT_NAME = "limit"

#: Write-call attribute/function names counted toward SQL105's
#: "two-or-more-writes-in-one-function" heuristic.
_ORM_WRITE_NAMES = frozenset({"save", "delete", "execute", "bulk_create", "update"})

#: Tokens that mark a function body as already transaction-wrapped.
_TRANSACTION_TOKENS = ("atomic", "transaction", "begin")

#: Tokens that mark a repo as carrying real connection-pool config.
_POOL_CONFIG_TOKENS = ("pool_size", "max_overflow", "QueuePool", "pgbouncer")

#: `CREATE INDEX ... ON <table> (<col>, ...)`, case-insensitive, the
#: minimal shape every migration tool (Alembic, Django, raw SQL) emits.
_CREATE_INDEX_RE = re.compile(
    r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+\S+\s+ON\s+(\w+)\s*\(([^)]*)\)",
    re.IGNORECASE,
)

#: A SQLAlchemy/Django declarative `ForeignKey("<table>...")` or
#: `ForeignKey(<Model>, ...)` column assignment: `<col> = ... ForeignKey(`.
_FOREIGN_KEY_RE = re.compile(r"(\w+)\s*=\s*[\w.]*ForeignKey\(")


# frob:doc docs/modules/sql.md#orm-rules
@dataclass(frozen=True)
class OrmRuleFinding:
    """One SQL10x finding: an N+1/unbounded-fetch/missing-index/missing-
    transaction/missing-pool-config hit. `file=""`/`line=0` for a repo-
    level finding (SQL106) that names no single call site.

    frob:ticket T-5337
    """

    rule: str
    file: str
    line: int
    message: str


# frob:doc docs/modules/sql.md#orm-rules
@dataclass(frozen=True)
class MigrationIndexInfo:
    """One `CREATE INDEX` statement parsed out of a tracked migration
    file: the table it indexes and the column names in its index
    expression, verbatim (unstripped) as they appeared in the SQL.

    frob:ticket T-5337
    """

    file: str
    table: str
    columns: tuple[str, ...]


def _tracked_files(root: Path, *suffixes: str) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `suffixes`, root-relative
    POSIX paths, `()` on any git failure -- mirrors
    `frob.sql._extract._tracked_files`'s own copy of this shape.

    frob:ticket T-5337
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("orm_rules: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("orm_rules: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(suffixes)
    )


def _iter_nodes(node: Node):  # noqa: ANN201 -- Iterator[Node], mirrors _extract._iter_nodes
    """Every node in `node`'s subtree, depth-first (including `node`
    itself) -- mirrors `frob.sql._extract._iter_nodes`.

    frob:ticket T-5337
    """
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def _function_defs(root_node: Node) -> list[Node]:
    """Every `function_definition` node in `root_node`'s subtree.

    frob:ticket T-5337
    """
    return [n for n in _iter_nodes(root_node) if n.type == "function_definition"]


def _for_loop_targets(func_node: Node) -> list[tuple[str, Node]]:
    """Every `(loop_var_name, for_node)` pair for a `for` statement whose
    body is walked for SQL101's lazy-access check.

    frob:ticket T-5337
    """
    pairs: list[tuple[str, Node]] = []
    for node in _iter_nodes(func_node):
        if node.type != "for_statement":
            continue
        left = child_by_field(node, "left")
        if left is None or left.type != "identifier":
            continue
        pairs.append((node_text(left), node))
    return pairs


def _attribute_accesses_on(name: str, node: Node) -> list[Node]:
    """Every `attribute` node under `node` whose object is the bare
    identifier `name` (e.g. `row.customer` when `name == "row"`).

    frob:ticket T-5337
    """
    hits: list[Node] = []
    for candidate in _iter_nodes(node):
        if candidate.type != "attribute":
            continue
        obj = child_by_field(candidate, "object")
        if obj is not None and obj.type == "identifier" and node_text(obj) == name:
            hits.append(candidate)
    return hits


def _sql101_findings(func_node: Node, rel_path: str) -> list[OrmRuleFinding]:
    """SQL101: a `for`-loop attribute access on the loop variable, with
    no eager-load call name anywhere in the enclosing function body.

    frob:ticket T-5337
    """
    body_text = node_text(func_node)
    if any(name in body_text for name in _EAGER_LOAD_NAMES):
        return []
    findings: list[OrmRuleFinding] = []
    for loop_var, for_node in _for_loop_targets(func_node):
        body = child_by_field(for_node, "body")
        if body is None:
            continue
        hits = _attribute_accesses_on(loop_var, body)
        if not hits:
            continue
        line = hits[0].start_point[0] + 1
        attr_name = node_text(child_by_field(hits[0], "attribute"))
        findings.append(
            OrmRuleFinding(
                rule="SQL101",
                file=rel_path,
                line=line,
                message=(
                    f"SQL101: {rel_path}:{line} `{loop_var}.{attr_name}` "
                    f"accessed inside a loop with no joinedload/"
                    f"selectinload/select_related/prefetch_related in "
                    f"this function -- likely N+1 query. Eager-load the "
                    f"relationship before the loop, or "
                    f'`frob:waive SQL101 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _sql102_findings(func_node: Node, rel_path: str) -> list[OrmRuleFinding]:
    """SQL102: a bare `.all()` call with no `.limit(` in the same call
    chain (the chain's own function-call ancestor text).

    frob:ticket T-5337
    """
    findings: list[OrmRuleFinding] = []
    for node in _iter_nodes(func_node):
        if node.type != "call":
            continue
        func = child_by_field(node, "function")
        if func is None or func.type != "attribute":
            continue
        attr_name = node_text(child_by_field(func, "attribute"))
        if attr_name != _UNBOUNDED_FETCH_NAME:
            continue
        chain_text = node_text(node)
        if f"{_LIMIT_NAME}(" in chain_text:
            continue
        line = node.start_point[0] + 1
        findings.append(
            OrmRuleFinding(
                rule="SQL102",
                file=rel_path,
                line=line,
                message=(
                    f"SQL102: {rel_path}:{line} `.all()` call with no "
                    f"`.limit(...)` in the same chain -- unbounded result "
                    f"set on a request path. Add a `.limit(...)`, or "
                    f'`frob:waive SQL102 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _sql105_findings(func_node: Node, rel_path: str) -> list[OrmRuleFinding]:
    """SQL105: two or more write calls in one function body with no
    transaction-wrapper token anywhere in that body.

    frob:ticket T-5337
    """
    body_text = node_text(func_node)
    if any(token in body_text for token in _TRANSACTION_TOKENS):
        return []
    write_calls: list[Node] = []
    for node in _iter_nodes(func_node):
        if node.type != "call":
            continue
        func = child_by_field(node, "function")
        if func is None:
            continue
        name = None
        if func.type == "attribute":
            name = node_text(child_by_field(func, "attribute"))
        elif func.type == "identifier":
            name = node_text(func)
        if name in _ORM_WRITE_NAMES:
            write_calls.append(node)
    if len(write_calls) < 2:
        return []
    line = write_calls[1].start_point[0] + 1
    return [
        OrmRuleFinding(
            rule="SQL105",
            file=rel_path,
            line=line,
            message=(
                f"SQL105: {rel_path}:{line} {len(write_calls)} write "
                f"calls in one function with no atomic/transaction/begin "
                f"wrapper -- multi-statement write with no transaction "
                f"boundary. Wrap the writes in a transaction, or "
                f'`frob:waive SQL105 reason="..."` with a real '
                f"justification"
            ),
        )
    ]


def _py_orm_findings(path: Path, root: Path) -> list[OrmRuleFinding]:
    """SQL101/SQL102/SQL105 findings for one `.py` file, one
    tree-sitter parse shared across all three per-function checks.

    frob:ticket T-5337
    """
    rel_path = path.relative_to(root).as_posix()
    parsed = raw_tree(path, expect_heterogeneous=True)
    if parsed.is_err:
        _log.debug(
            "orm_rules: skipping unparseable %s: %s", rel_path, parsed.danger_err
        )
        return []
    tree, _source, _language = parsed.danger_ok
    findings: list[OrmRuleFinding] = []
    for func_node in _function_defs(tree.root_node):
        findings.extend(_sql101_findings(func_node, rel_path))
        findings.extend(_sql102_findings(func_node, rel_path))
        findings.extend(_sql105_findings(func_node, rel_path))
    return findings


# frob:doc docs/modules/sql.md#orm-rules
# frob:ticket T-5337
def migration_scan(root: Path) -> tuple[MigrationIndexInfo, ...]:
    """Every `CREATE INDEX`/`CREATE UNIQUE INDEX` statement parsed out of
    tracked `.sql` files under `root` -- the canonical migration-index
    registry T-5147-6 (pool config, a separate helper) and T-5145-3 (the
    PII-retention-TTL-column check) both reuse instead of re-parsing
    migration files a second time.

    frob:ticket T-5337
    """
    root = Path(root)
    infos: list[MigrationIndexInfo] = []
    for rel in _tracked_files(root, ".sql"):
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        for match in _CREATE_INDEX_RE.finditer(text):
            table = match.group(1)
            columns = tuple(c.strip() for c in match.group(2).split(",") if c.strip())
            infos.append(MigrationIndexInfo(file=rel, table=table, columns=columns))
    _log.info("orm_rules: %d migration index declaration(s) under %s", len(infos), root)
    return tuple(infos)


def _sql104_findings(root: Path) -> list[OrmRuleFinding]:
    """SQL104: an ORM model's `ForeignKey`-declared column with no
    matching declared index column anywhere in `migration_scan`'s
    registry (a repo-wide cross-check, not a per-function one).

    frob:ticket T-5337
    """
    indexed_columns: set[str] = set()
    for info in migration_scan(root):
        indexed_columns.update(info.columns)
    findings: list[OrmRuleFinding] = []
    for rel in _tracked_files(root, ".py"):
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            match = _FOREIGN_KEY_RE.search(line)
            if match is None:
                continue
            col = match.group(1)
            if col in indexed_columns:
                continue
            findings.append(
                OrmRuleFinding(
                    rule="SQL104",
                    file=rel,
                    line=lineno,
                    message=(
                        f"SQL104: {rel}:{lineno} ForeignKey column "
                        f"{col!r} has no matching CREATE INDEX in any "
                        f"tracked migration file -- FK columns are the "
                        f"common WHERE/JOIN predicate and usually need "
                        f"an index. Add a migration index, or "
                        f'`frob:waive SQL104 reason="..."` with a real '
                        f"justification"
                    ),
                )
            )
    return findings


def _sql106_finding(root: Path) -> OrmRuleFinding | None:
    """SQL106: no connection-pool config token anywhere under `root`,
    only emitted when `sql_relevance` reports real SQL surface (a repo
    with no SQL at all has nothing to pool).

    frob:ticket T-5337
    """
    if not sql_relevance(root):
        return None
    for rel in _tracked_files(root, ".py", ".toml", ".ini", ".cfg", ".yaml", ".yml"):
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        if any(token in text for token in _POOL_CONFIG_TOKENS):
            _log.debug("orm_rules: pool config token found in %s", rel)
            return None
    return OrmRuleFinding(
        rule="SQL106",
        file="",
        line=0,
        message=(
            "SQL106: no connection-pool config found (SQLAlchemy "
            "pool_size/max_overflow/QueuePool or a pgbouncer.ini) "
            "despite real SQL call sites in this repo -- an unbounded "
            "or default connection pool exhausts the DB under load. Add "
            "explicit pool config, or "
            '`frob:waive SQL106 reason="..."` with a real justification'
        ),
    )


# frob:doc docs/modules/sql.md#orm-rules
# frob:ticket T-5337
def orm_rule_findings(root: Path) -> tuple[OrmRuleFinding, ...]:
    """SQL101/SQL102/SQL104/SQL105/SQL106: every ORM N+1/unbounded-fetch/
    missing-index/missing-transaction/missing-pool-config finding under
    `root`. A gate wires this in the same one-call-folds-into-the-same-
    tuple shape `frob.webapp._websec_sinks.websec_sink_findings` already
    follows for its own sink family.

    frob:ticket T-5337
    """
    root = Path(root)
    findings: list[OrmRuleFinding] = []
    for rel in _tracked_files(root, ".py"):
        findings.extend(_py_orm_findings(root / rel, root))
    findings.extend(_sql104_findings(root))
    pool_finding = _sql106_finding(root)
    if pool_finding is not None:
        findings.append(pool_finding)
    _log.info("orm_rules: %d SQL10x finding(s) under %s", len(findings), root)
    return tuple(findings)

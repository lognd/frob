"""SQL literal extraction from host languages + sqlfluff relevance
(docs/modules/sql.md, T-5334, leaf of the T-5299 epic after T-5302's
`frob.sql` package stub and T-5307's WEBSEC injection substrate).

`frob.sql` is a shared-leaf detection layer the same way `frob.webapp` is
(T-5302's `[arch.layering]` entry): it depends only on `frob.lang`'s
tree-sitter walkers, never `frob.webapp`, because SQL-executing call
sites appear in code that has no web framework at all (migration
scripts, CLI tools, ETL) -- see `frob.sql.__init__`'s own docstring.

Three host-language/ORM call shapes are walked, one tree-sitter AST pass
each via `frob.lang.raw_tree` (T-5300/T-1604's shared escape hatch, the
same shape `frob.webapp._websec_sinks` uses for its own JS/TS/Vue walk):

- Python: `<cursor>.execute(sql, ...)`, Django's `<queryset>.raw(sql)`,
  and SQLAlchemy's bare `text(sql)` call.
- TypeScript/JavaScript: Prisma's `$queryRaw`/`$executeRaw` -- either a
  tagged template (`prisma.$queryRaw`...``) or a plain call
  (`prisma.$queryRaw(sql)`).
- Rust: sqlx's `query!`/`query_as!` macro invocations.

A call site's SQL argument is either a LITERAL (a plain string/template
with no interpolation -- extracted verbatim for sqlfluff to parse) or a
non-literal composition (an f-string/tagged template with a substitution,
or a `+`/`.format()`-built string) -- the latter is itself a WEBSEC-class
injection finding (WEBSEC107, reserved for this leaf in
`frob.gates._waive._KNOWN_GATE_RULES`'s T-5141 injection block) UNLESS
the composition goes through psycopg's `sql.SQL`/`sql.Identifier` API,
which is explicitly excluded per the T-5141 corpus (it is a safe,
parameterized composition primitive, not a taint sink).

`sql_relevance` is this leaf's OWNER-DIRECTIVE predicate: a `.sql` file
OR an SQL-executing call site anywhere in the repo is what makes
sqlfluff REQUIRED-for-the-family in 5148-2's tool-registry entry (T-5148)
-- defined once here so that leaf imports it rather than re-detecting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from tree_sitter import Node

from frob.gitio import run_argv
from frob.lang import child_by_field, node_text, raw_tree
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = [
    "SqlInjectionFinding",
    "SqlLiteralExtraction",
    "extract_sql_literals",
    "sql_injection_findings",
    "sql_relevance",
]

#: Python attribute names treated as a DB-API/ORM SQL-executing sink:
#: `<cursor>.execute(sql, ...)` and Django's `<queryset>.raw(sql)`.
_PY_EXECUTE_METHOD_NAMES = frozenset({"execute", "raw"})

#: Python bare-call name for SQLAlchemy's `text(sql)` construct.
_PY_TEXT_CALL_NAME = "text"

#: Psycopg's safe, parameterized SQL-composition API (T-5141 corpus:
#: explicitly excluded from the non-literal-composition injection check).
_PSYCOPG_SQL_COMPOSITION_RE = re.compile(r"\bsql\s*\.\s*(SQL|Identifier|Composed)\b")

#: JS/TS Prisma raw-query member names (tagged template or plain call).
_TS_PRISMA_RAW_NAMES = frozenset({"$queryRaw", "$executeRaw"})

#: Rust sqlx macro names that take a literal/format-string SQL argument
#: as their first macro token.
_RUST_SQLX_MACRO_NAMES = frozenset({"query", "query_as", "query_scalar"})


# frob:doc docs/modules/sql.md#public-api
@dataclass(frozen=True)
class SqlLiteralExtraction:
    """One SQL-executing call site's extracted SQL text: a verbatim
    literal, or a `?`-holed skeleton for a non-literal composition (the
    interpolated/concatenated pieces replaced with `?` so sqlfluff can
    still parse the surrounding SQL shape).

    frob:ticket T-5334
    """

    file: str
    line: int
    call_kind: str
    sql_text: str
    is_literal: bool


# frob:doc docs/modules/sql.md#public-api
@dataclass(frozen=True)
class SqlInjectionFinding:
    """WEBSEC107: a non-literal, unparameterized string composition
    reaching an SQL-executing sink (CWE-89) -- the same "source reaches a
    dangerous sink with no validator/sanitizer hop" shape
    `frob.webapp._websec_sinks.WebsecSinkFinding` uses for XSS, kept as
    this leaf's own dataclass rather than importing `frob.webapp` (this
    package stays a `frob.lang`-only leaf per `[arch.layering]`, since
    SQL call sites appear in non-web code with no web framework to
    detect).

    frob:ticket T-5334
    """

    rule: str
    file: str
    line: int
    message: str


def _tracked_files(root: Path, *suffixes: str) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `suffixes`, root-relative
    POSIX paths, `()` on any git failure -- the same tracked-file-scan
    shape `frob.webapp._websec_sinks._tracked_files` already uses.

    frob:ticket T-5334
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("sql_extract: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("sql_extract: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(suffixes)
    )


def _iter_nodes(node: Node):  # noqa: ANN201 -- Iterator[Node], tree-sitter's own Node has no public generic alias
    """Every node in `node`'s subtree, depth-first (including `node` itself)
    -- same shape `frob.webapp._websec_sinks._iter_nodes` already uses.

    frob:ticket T-5334
    """
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def _is_py_string_literal(node: Node | None) -> bool:
    """True if `node` is a plain Python string with no f-string
    interpolation -- `node.type == "string"` covers both, so the check is
    whether an `interpolation` child is present anywhere in the string's
    content.

    frob:ticket T-5334
    """
    if node is None:
        return False
    if node.type != "string":
        return False
    return not any(c.type == "interpolation" for c in _iter_nodes(node))


def _py_string_skeleton(node: Node) -> str:
    """The SQL skeleton for a non-literal Python string: every
    `interpolation` child's own text replaced with `?` so sqlfluff still
    sees a parseable SQL shape around the hole.

    frob:ticket T-5334
    """
    text = node_text(node)
    for child in _iter_nodes(node):
        if child.type == "interpolation":
            text = text.replace(node_text(child), "?")
    return text


def _py_call_kind(node: Node) -> str | None:
    """The `call_kind` label for a Python `call` node if it is one of
    `<cursor>.execute(sql)`/`<queryset>.raw(sql)`/`text(sql)`, else `None`.

    frob:ticket T-5334
    """
    func = child_by_field(node, "function")
    if func is None:
        return None
    if func.type == "attribute":
        name = node_text(child_by_field(func, "attribute"))
        if name not in _PY_EXECUTE_METHOD_NAMES:
            return None
        return f"python.{name}"
    if func.type == "identifier":
        name = node_text(func)
        if name != _PY_TEXT_CALL_NAME:
            return None
        return "python.sqlalchemy_text"
    return None


def _py_sql_argument(node: Node) -> Node | None:
    """The first positional argument of a matched Python SQL-executing
    `call` node, or `None` if it takes none.

    frob:ticket T-5334
    """
    args = child_by_field(node, "arguments")
    if args is None:
        return None
    arg_nodes = [c for c in args.named_children]
    return arg_nodes[0] if arg_nodes else None


def _py_injection_finding(
    call_kind: str, rel_path: str, line: int, arg_text: str
) -> SqlInjectionFinding:
    """One WEBSEC107 finding for a Python SQL-executing call site's
    non-literal argument.

    frob:ticket T-5334
    """
    return SqlInjectionFinding(
        rule="WEBSEC107",
        file=rel_path,
        line=line,
        message=(
            f"WEBSEC107: {rel_path}:{line} {call_kind}(...) received "
            f"a non-literal, unparameterized SQL argument "
            f"({arg_text!r}) -- SQL injection sink (CWE-89). Pass "
            f"parameters separately (DB-API bind params, ORM "
            f"query builder) or psycopg's sql.SQL/sql.Identifier "
            f'composition, or `frob:waive WEBSEC107 reason="..."` '
            f"with a real justification"
        ),
    )


def _py_call_findings(
    root_node: Node, rel_path: str, source: bytes
) -> tuple[list[SqlLiteralExtraction], list[SqlInjectionFinding]]:
    """Every Python `<cursor>.execute(sql)`/`<queryset>.raw(sql)`/
    `text(sql)` call site's extraction plus WEBSEC107 findings for a
    non-literal, unparameterized composition (excluding psycopg's
    `sql.SQL`/`.Identifier`/`.Composed` composition API).

    frob:ticket T-5334
    """
    extractions: list[SqlLiteralExtraction] = []
    findings: list[SqlInjectionFinding] = []
    for node in _iter_nodes(root_node):
        if node.type != "call":
            continue
        call_kind = _py_call_kind(node)
        if call_kind is None:
            continue
        sql_arg = _py_sql_argument(node)
        if sql_arg is None:
            continue
        line = sql_arg.start_point[0] + 1
        if _is_py_string_literal(sql_arg):
            extractions.append(
                SqlLiteralExtraction(
                    file=rel_path,
                    line=line,
                    call_kind=call_kind,
                    sql_text=node_text(sql_arg),
                    is_literal=True,
                )
            )
            continue
        arg_text = node_text(sql_arg)
        if _PSYCOPG_SQL_COMPOSITION_RE.search(arg_text):
            _log.debug(
                "sql_extract: %s:%d psycopg sql.SQL composition, excluded",
                rel_path,
                line,
            )
            continue
        skeleton = _py_string_skeleton(sql_arg) if sql_arg.type == "string" else "?"
        extractions.append(
            SqlLiteralExtraction(
                file=rel_path,
                line=line,
                call_kind=call_kind,
                sql_text=skeleton,
                is_literal=False,
            )
        )
        if sql_arg.type not in ("string", "binary_operator"):
            # A call/identifier/other opaque expression (e.g. `execute(text(...))`'s
            # own call to a known-safe wrapper) is not itself a direct string
            # composition -- only a raw f-string or `+`/`%`-concatenation is a
            # WEBSEC107-shaped finding; textual-proxy heuristics do not extend
            # to resolving what an opaque callee returns.
            continue
        findings.append(_py_injection_finding(call_kind, rel_path, line, arg_text))
    return extractions, findings


def _py_findings(
    path: Path, root: Path
) -> tuple[list[SqlLiteralExtraction], list[SqlInjectionFinding]]:
    """Extraction + injection findings for one `.py` file.

    frob:ticket T-5334
    """
    rel_path = path.relative_to(root).as_posix()
    parsed = raw_tree(path, expect_heterogeneous=True)
    if parsed.is_err:
        _log.debug(
            "sql_extract: skipping unparseable %s: %s", rel_path, parsed.danger_err
        )
        return [], []
    tree, source, _language = parsed.danger_ok
    return _py_call_findings(tree.root_node, rel_path, source)


def _is_ts_template_literal(node: Node | None) -> bool:
    """True if `node` is a template string with no `${...}` substitution.

    frob:ticket T-5334
    """
    if node is None:
        return False
    if node.type == "string":
        return True
    if node.type == "template_string":
        return not any(c.type == "template_substitution" for c in node.children)
    return False


def _ts_template_skeleton(node: Node) -> str:
    """The SQL skeleton for a non-literal template string: every
    `template_substitution` child's own text replaced with `?`.

    frob:ticket T-5334
    """
    text = node_text(node)
    for child in node.children:
        if child.type == "template_substitution":
            text = text.replace(node_text(child), "?")
    return text


def _ts_prisma_sql_argument(node: Node) -> Node | None:
    """The SQL argument of a matched Prisma `$queryRaw`/`$executeRaw`
    `call_expression` node -- a tagged template's "arguments" field IS the
    bare `template_string` node (no wrapping container); a parenthesized
    call's "arguments" field is a container whose first named child is
    the argument.

    frob:ticket T-5334
    """
    func = child_by_field(node, "function")
    if func is None or func.type != "member_expression":
        return None
    prop = node_text(child_by_field(func, "property"))
    if prop not in _TS_PRISMA_RAW_NAMES:
        return None
    args = child_by_field(node, "arguments")
    if args is None:
        return None
    if args.type in ("template_string", "string"):
        return args
    arg_nodes = [c for c in args.named_children]
    return arg_nodes[0] if arg_nodes else None


def _ts_prisma_injection_finding(
    rel_path: str, line: int, arg_text: str
) -> SqlInjectionFinding:
    """One WEBSEC107 finding for a Prisma `$queryRaw`/`$executeRaw` call
    site's non-literal argument.

    frob:ticket T-5334
    """
    return SqlInjectionFinding(
        rule="WEBSEC107",
        file=rel_path,
        line=line,
        message=(
            f"WEBSEC107: {rel_path}:{line} $queryRaw/$executeRaw "
            f"received a non-literal, unparameterized SQL argument "
            f"({arg_text!r}) -- SQL injection sink (CWE-89). Use "
            f"Prisma's `Prisma.sql` tagged-template parameterization "
            f'instead, or `frob:waive WEBSEC107 reason="..."` with '
            f"a real justification"
        ),
    )


def _ts_prisma_findings(
    root_node: Node, rel_path: str
) -> tuple[list[SqlLiteralExtraction], list[SqlInjectionFinding]]:
    """Every Prisma `$queryRaw`/`$executeRaw` call site (tagged template
    or plain call), TS/JS/JSX shared walk.

    frob:ticket T-5334
    """
    extractions: list[SqlLiteralExtraction] = []
    findings: list[SqlInjectionFinding] = []
    for node in _iter_nodes(root_node):
        if node.type != "call_expression":
            continue
        sql_arg = _ts_prisma_sql_argument(node)
        if sql_arg is None:
            continue
        line = sql_arg.start_point[0] + 1
        if _is_ts_template_literal(sql_arg):
            extractions.append(
                SqlLiteralExtraction(
                    file=rel_path,
                    line=line,
                    call_kind="ts.prisma_queryRaw",
                    sql_text=node_text(sql_arg),
                    is_literal=True,
                )
            )
            continue
        skeleton = (
            _ts_template_skeleton(sql_arg) if sql_arg.type == "template_string" else "?"
        )
        arg_text = node_text(sql_arg)
        extractions.append(
            SqlLiteralExtraction(
                file=rel_path,
                line=line,
                call_kind="ts.prisma_queryRaw",
                sql_text=skeleton,
                is_literal=False,
            )
        )
        findings.append(_ts_prisma_injection_finding(rel_path, line, arg_text))
    return extractions, findings


def _ts_findings(
    path: Path, root: Path
) -> tuple[list[SqlLiteralExtraction], list[SqlInjectionFinding]]:
    """Extraction + injection findings for one `.js`/`.jsx`/`.ts`/`.tsx` file.

    frob:ticket T-5334
    """
    rel_path = path.relative_to(root).as_posix()
    parsed = raw_tree(path, expect_heterogeneous=True)
    if parsed.is_err:
        _log.debug(
            "sql_extract: skipping unparseable %s: %s", rel_path, parsed.danger_err
        )
        return [], []
    tree, _source, _language = parsed.danger_ok
    return _ts_prisma_findings(tree.root_node, rel_path)


def _rust_sqlx_findings(
    root_node: Node, rel_path: str
) -> tuple[list[SqlLiteralExtraction], list[SqlInjectionFinding]]:
    """Every sqlx `query!`/`query_as!`/`query_scalar!` macro invocation's
    first (SQL) token.

    frob:ticket T-5334
    """
    extractions: list[SqlLiteralExtraction] = []
    findings: list[SqlInjectionFinding] = []
    for node in _iter_nodes(root_node):
        if node.type != "macro_invocation":
            continue
        macro_name_node = child_by_field(node, "macro")
        macro_name = node_text(macro_name_node)
        # `sqlx::query!` parses as a `scoped_identifier` field, so the
        # last `::`-segment is the macro's own bare name.
        short_name = macro_name.rsplit("::", 1)[-1]
        if short_name not in _RUST_SQLX_MACRO_NAMES:
            continue
        # `token_tree` has no grammar field name on `macro_invocation`
        # (only `macro` and the bang do) -- find it by type among the
        # macro's direct children instead.
        token_tree = next((c for c in node.children if c.type == "token_tree"), None)
        if token_tree is None:
            continue
        string_nodes = [
            c for c in token_tree.named_children if c.type == "string_literal"
        ]
        if not string_nodes:
            continue
        sql_arg = string_nodes[0]
        line = sql_arg.start_point[0] + 1
        extractions.append(
            SqlLiteralExtraction(
                file=rel_path,
                line=line,
                call_kind=f"rust.sqlx_{short_name}",
                sql_text=node_text(sql_arg),
                is_literal=True,
            )
        )
    return extractions, findings


def _rust_findings(
    path: Path, root: Path
) -> tuple[list[SqlLiteralExtraction], list[SqlInjectionFinding]]:
    """Extraction + injection findings for one `.rs` file.

    frob:ticket T-5334
    """
    rel_path = path.relative_to(root).as_posix()
    parsed = raw_tree(path, expect_heterogeneous=True)
    if parsed.is_err:
        _log.debug(
            "sql_extract: skipping unparseable %s: %s", rel_path, parsed.danger_err
        )
        return [], []
    tree, _source, _language = parsed.danger_ok
    return _rust_sqlx_findings(tree.root_node, rel_path)


# frob:doc docs/modules/sql.md#public-api
# frob:ticket T-5334
def extract_sql_literals(root: Path) -> tuple[SqlLiteralExtraction, ...]:
    """Every SQL-executing call site under `root`, across Python
    (cursor.execute/.raw()/SQLAlchemy text()), TypeScript/JavaScript
    (Prisma $queryRaw/$executeRaw), and Rust (sqlx query!/query_as!/
    query_scalar! macros) -- one `SqlLiteralExtraction` per call site,
    literal text verbatim or a `?`-holed skeleton for a non-literal
    composition.

    frob:ticket T-5334
    """
    root = Path(root)
    extractions: list[SqlLiteralExtraction] = []
    for rel in _tracked_files(root, ".py"):
        found, _injections = _py_findings(root / rel, root)
        extractions.extend(found)
    for rel in _tracked_files(root, ".js", ".jsx", ".ts", ".tsx"):
        found, _injections = _ts_findings(root / rel, root)
        extractions.extend(found)
    for rel in _tracked_files(root, ".rs"):
        found, _injections = _rust_findings(root / rel, root)
        extractions.extend(found)
    _log.info("sql_extract: %d SQL call site(s) under %s", len(extractions), root)
    return tuple(extractions)


# frob:doc docs/modules/sql.md#public-api
# frob:ticket T-5334
def sql_injection_findings(root: Path) -> tuple[SqlInjectionFinding, ...]:
    """WEBSEC107: every non-literal, unparameterized SQL composition
    reaching an SQL-executing sink under `root` (CWE-89), excluding
    psycopg's `sql.SQL`/`.Identifier`/`.Composed` safe composition API.

    frob:ticket T-5334
    """
    root = Path(root)
    findings: list[SqlInjectionFinding] = []
    for rel in _tracked_files(root, ".py"):
        _extracted, found = _py_findings(root / rel, root)
        findings.extend(found)
    for rel in _tracked_files(root, ".js", ".jsx", ".ts", ".tsx"):
        _extracted, found = _ts_findings(root / rel, root)
        findings.extend(found)
    for rel in _tracked_files(root, ".rs"):
        _extracted, found = _rust_findings(root / rel, root)
        findings.extend(found)
    _log.info("sql_extract: %d WEBSEC107 finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/sql.md#public-api
# frob:ticket T-5334
def sql_relevance(root: Path) -> bool:
    """OWNER DIRECTIVE (T-5334): True if `root` has at least one tracked
    `.sql` file OR at least one SQL-executing call site (Python/TS/Rust,
    the same three shapes `extract_sql_literals` walks) -- this predicate
    is what makes sqlfluff REQUIRED-for-the-family in 5148-2's tool-
    registry entry (a repo with no SQL surface at all reports sqlfluff's
    absence as 'unmeasured', not a failure). Defined once here, reused by
    5148-2 rather than re-detected.

    frob:ticket T-5334
    """
    root = Path(root)
    if _tracked_files(root, ".sql"):
        _log.debug("sql_extract: relevance true, tracked .sql file(s) under %s", root)
        return True
    relevant = bool(extract_sql_literals(root))
    _log.debug("sql_extract: relevance=%s (call-site scan) under %s", relevant, root)
    return relevant

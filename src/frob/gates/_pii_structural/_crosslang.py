"""T-0352: TypeScript/Rust field-shape and env-access equivalents of
PII010/SEC110 -- T-1076 split of `frob.gates._pii_structural`.

Ticket T-0207's module docstring disclosed this as "deliberately not
built" -- this section extends PII010/SEC110 to the same two structural
surfaces (data-structure field names, env-var read sites) over the OTHER
two `frob.lang`-supported languages named in the ticket body, reusing
`frob.lang.raw_tree` (the SAME single tree-sitter grammar-load dispatch
`frob.arch`/`frob.dup._legacy` already share, module docstring: "reuse
the existing tree-sitter parses ... rather than a new parser") instead
of standing up a second `get_parser`/`Parser.parse` call site. Field-name
matching reuses `_field_name_hit`/`FIELD_SIGNATURES` unchanged (a field
named `email`/`ssn`/`password` is the identical structural signal in any
language). T-0352 left TYPE-kind matching (`_field_type_hit`, `EmailStr`/
`SecretStr`) Python-only, disclosing the TS/Rust nominal-type gap as
honest future work rather than guessing at it; T-0762 closes that gap:
`_ts_type_hit`/`_rust_type_hit` match a field's TYPE against the same
single-source `FIELD_SIGNATURES` registry (langs-scoped per entry, see
`_FieldSignature.langs`) -- TS branded/nominal email types and known
secret-wrapper types (`Secret`/`SecretString`/`SensitiveString`), and
Rust `secrecy::Secret`/`SecretString` plus newtype PII wrappers.

NO-FAIL-SILENT (ticket mandate): an unresolvable field shape -- a
TypeScript index signature (`[key: string]: T`) or computed property
name (`[expr]: T`), whose name cannot be read statically -- is REPORTED
via `_pii010_unresolvable_violation`, not silently skipped, mirroring
the existing Python env-access posture (`_scan_python_env_access`
already fires on a non-literal `os.environ[dynamic_key]` rather than
skip it for lack of a static name)."""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Node, Tree

from frob.gates._models import Severity, Violation
from frob.lang import node_text, raw_tree
from frob.logging import get_logger

from ._declared_surface import _EMPTY_DECLARED_SURFACE, _DeclaredSurface
from ._env_access import _is_allowlisted_env_var, _sec110_violation
from ._python_fields import _pii010_violation
from ._self_match import _is_pii_self_pattern_file
from ._signatures import _field_name_hit, _rust_type_hit, _ts_type_hit
from ._tracked import _tracked_files_by_pattern

_log = get_logger(__name__)


def _pii010_unresolvable_violation(
    rel_path: str, lineno: int, description: str
) -> Violation:
    """T-0352 NO-FAIL-SILENT: a field-shape site whose name cannot be
    statically read (a TS index signature or computed property name) --
    reported as a PII010 finding demanding manual review, never silently
    dropped from the scan population."""
    _log.warning(
        "PII010: %s:%d unresolvable field shape (%s) -- cannot statically "
        "determine field name",
        rel_path,
        lineno,
        description,
    )
    return Violation(
        rule="PII010",
        severity=Severity.WARN,
        file=rel_path,
        line=lineno,
        message=(
            f"PII010: {rel_path}:{lineno} has an unresolvable field shape "
            f"({description}) -- the field name cannot be determined "
            f"statically, so it cannot be checked against FIELD_SIGNATURES; "
            f"review manually for PII, or "
            f'`frob:waive PII010 reason="..."` once reviewed'
        ),
    )


def _ts_property_signatures(
    body: Node,
) -> list[tuple[str | None, int, Node | None, str | None]]:
    """`(name, lineno, type_node, unresolvable_description)` for each member
    of a TS `interface_body`/`object_type`/`class_body`: a `property_
    signature`/`public_field_definition` yields its literal name; an
    `index_signature` (`[key: string]: T`) or a computed property name
    (`[expr]: T`) yields `(None, lineno, None, description)` -- reported
    via `_pii010_unresolvable_violation` rather than skipped (NO-FAIL-
    SILENT, this module's docstring)."""
    out: list[tuple[str | None, int, Node | None, str | None]] = []
    for member in body.named_children:
        if member.type in ("property_signature", "public_field_definition"):
            name_node = member.child_by_field_name("name")
            if name_node is None:
                continue
            if name_node.type == "computed_property_name":
                out.append(
                    (None, member.start_point[0] + 1, None, "computed property name")
                )
                continue
            out.append(
                (
                    node_text(name_node),
                    member.start_point[0] + 1,
                    member.child_by_field_name("type"),
                    None,
                )
            )
        elif member.type == "index_signature":
            out.append((None, member.start_point[0] + 1, None, "index signature"))
    return out


def _scan_ts_fields(
    tree: Tree,
    rel_path: str,
    declared: _DeclaredSurface = _EMPTY_DECLARED_SURFACE,
) -> tuple[Violation, ...]:
    """PII010 (T-0352) over TS/TSX `interface_declaration` bodies,
    `type_alias_declaration`s whose value is an `object_type`, and
    `class_declaration` bodies -- the TS field-shape equivalents of
    `_scan_python_fields`'s pydantic/dataclass/TypedDict scan. Reuses
    `_field_name_hit`/`FIELD_SIGNATURES` (name-kind entries) plus `_ts_
    type_hit` (TS-scoped type-kind entries, T-0762) and `declared` (T-0351
    std.pii join) unchanged."""
    violations: list[Violation] = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        body: Node | None = None
        if node.type == "interface_declaration":
            body = node.child_by_field_name("body")
        elif node.type == "type_alias_declaration":
            value = node.child_by_field_name("value")
            if value is not None and value.type == "object_type":
                body = value
        elif node.type == "class_declaration":
            body = node.child_by_field_name("body")
        if body is not None:
            for name, lineno, type_node, unresolvable in _ts_property_signatures(body):
                if unresolvable is not None:
                    violations.append(
                        _pii010_unresolvable_violation(rel_path, lineno, unresolvable)
                    )
                    continue
                assert (
                    name is not None
                )  # frob:invariant terminates reason="the (None, ..., description) branch is handled by the unresolvable arm above; every remaining tuple carries a real name" measure="tuple's unresolvable field is None"  # noqa: E501
                sig = _field_name_hit(name) or _ts_type_hit(type_node)
                if sig is not None and not declared._has_pii(rel_path, sig.category):
                    violations.append(_pii010_violation(rel_path, lineno, name, sig))
        stack.extend(node.children)
    return tuple(violations)


#: TS/TSX env-access dotted-prefix targets (corpus family 3: `process.env`,
#: `import.meta.env` -- the TS equivalents named in the ticket body).
_TS_ENV_PREFIXES = ("process.env", "import.meta.env")


def _ts_dotted_prefix(node: Node) -> str | None:
    """The dotted-name text of a `member_expression`/`meta_property`/
    `identifier` chain (`process.env` -> `"process.env"`, `import.meta.env`
    -> `"import.meta.env"`), or `None` for anything else -- the TS analogue
    of `_dotted_prefix`'s Python AST unparse."""
    parts: list[str] = []
    current: Node | None = node
    while current is not None:
        if current.type == "member_expression":
            prop = current.child_by_field_name("property")
            parts.append(node_text(prop) if prop is not None else "?")
            current = current.child_by_field_name("object")
        elif current.type == "identifier":
            parts.append(node_text(current))
            current = None
        elif current.type == "meta_property":
            parts.append(node_text(current).replace(".", "-"))
            current = None
        else:
            return None
    return ".".join(reversed(parts)).replace("import-meta", "import.meta")


def _ts_string_literal_text(node: Node) -> str | None:
    """The unquoted text of a TS `string` literal node, or `None`."""
    if node.type != "string":
        return None
    frag = next((c for c in node.named_children if c.type == "string_fragment"), None)
    return node_text(frag) if frag is not None else ""


def _scan_ts_env_access(
    tree: Tree,
    rel_path: str,
    declared: _DeclaredSurface = _EMPTY_DECLARED_SURFACE,
) -> tuple[Violation, ...]:
    """SEC110 (T-0352) over `process.env.NAME`/`process.env["NAME"]` and
    `import.meta.env.NAME`/`import.meta.env["NAME"]` access sites -- the TS
    equivalent of `_scan_python_env_access`. A dynamic (non-literal)
    subscript key still fires (NO-FAIL-SILENT, this module's docstring);
    `declared` (T-0351) discharges a file already code-bound to a Secret-
    clearance node."""
    if declared._has_secret(rel_path):
        return ()
    violations: list[Violation] = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "member_expression":
            violations.extend(_ts_env_member_violation(node, rel_path))
        elif node.type == "subscript_expression":
            violations.extend(_ts_env_subscript_violation(node, rel_path))
        stack.extend(node.children)
    return tuple(violations)


def _ts_env_member_violation(node: Node, rel_path: str) -> list[Violation]:
    """`SEC110` violation, if any, for one `process.env.NAME`-shaped
    `member_expression` node (extracted from `_scan_ts_env_access` to cut
    nesting, T-0394)."""
    obj = node.child_by_field_name("object")
    prop = node.child_by_field_name("property")
    if obj is None or prop is None:
        return []
    obj_dotted = _ts_dotted_prefix(obj)
    if obj_dotted not in _TS_ENV_PREFIXES:
        return []
    var_name = node_text(prop)
    if _is_allowlisted_env_var(var_name):
        return []
    return [
        _sec110_violation(rel_path, node.start_point[0] + 1, f"{obj_dotted}.{var_name}")
    ]


def _ts_env_subscript_violation(node: Node, rel_path: str) -> list[Violation]:
    """`SEC110` violation, if any, for one `process.env["NAME"]`-shaped
    `subscript_expression` node (extracted from `_scan_ts_env_access` to
    cut nesting, T-0394)."""
    obj = node.child_by_field_name("object")
    index = node.child_by_field_name("index")
    if obj is None or index is None:
        return []
    obj_dotted = _ts_dotted_prefix(obj)
    if obj_dotted not in _TS_ENV_PREFIXES:
        return []
    var_name = _ts_string_literal_text(index)
    if var_name is not None and _is_allowlisted_env_var(var_name):
        return []
    site = (
        f"{obj_dotted}[{var_name!r}]" if var_name is not None else f"{obj_dotted}[...]"
    )
    return [_sec110_violation(rel_path, node.start_point[0] + 1, site)]


def _rust_struct_field_names(body: Node) -> list[tuple[str, int, Node | None]]:
    """`(name, lineno, type_node)` for each named field of a Rust `struct_
    item`'s `field_declaration_list` body -- tuple structs (`ordered_
    field_declaration_list`, no source names) are out of scope (module
    comment: field-shape by NAME is the signal; a positional tuple field
    has none to match)."""
    out: list[tuple[str, int, Node | None]] = []
    if body.type != "field_declaration_list":
        return out
    for member in body.named_children:
        if member.type != "field_declaration":
            continue
        name_node = member.child_by_field_name("name")
        if name_node is None:
            continue
        out.append(
            (
                node_text(name_node),
                member.start_point[0] + 1,
                member.child_by_field_name("type"),
            )
        )
    return out


def _scan_rust_fields(
    tree: Tree,
    rel_path: str,
    declared: _DeclaredSurface = _EMPTY_DECLARED_SURFACE,
) -> tuple[Violation, ...]:
    """PII010 (T-0352) over Rust `struct_item` named fields -- the Rust
    field-shape equivalent of `_scan_python_fields`. Reuses `_field_name_
    hit`/`FIELD_SIGNATURES` plus `_rust_type_hit` (Rust-scoped type-kind
    entries, T-0762) and `declared` (T-0351) unchanged."""
    violations: list[Violation] = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "struct_item":
            violations.extend(_rust_struct_field_violations(node, rel_path, declared))
        stack.extend(node.children)
    return tuple(violations)


def _rust_struct_field_violations(
    struct_node: Node, rel_path: str, declared: _DeclaredSurface
) -> list[Violation]:
    """`PII010` violations for one Rust `struct_item`'s named fields
    (extracted from `_scan_rust_fields` to cut nesting, T-0394)."""
    body = struct_node.child_by_field_name("body")
    if body is None:
        return []
    out: list[Violation] = []
    for name, lineno, type_node in _rust_struct_field_names(body):
        sig = _field_name_hit(name) or _rust_type_hit(type_node)
        if sig is not None and not declared._has_pii(rel_path, sig.category):
            out.append(_pii010_violation(rel_path, lineno, name, sig))
    return out


#: Rust env-access function-name fragment (corpus family 3: `std::env::var`/
#: `std::env::var_os` -- the Rust equivalent named in the ticket body).
_RUST_ENV_CALL_NAMES = frozenset({"var", "var_os"})


def _rust_scoped_name(node: Node) -> str | None:
    """The bare trailing identifier of a Rust `scoped_identifier`/
    `identifier` (`std::env::var` -> `"var"`), or `None` for anything
    else."""
    if node.type == "identifier":
        return node_text(node)
    if node.type == "scoped_identifier":
        name = node.child_by_field_name("name")
        return node_text(name) if name is not None else None
    return None


def _rust_dotted_prefix(node: Node) -> str:
    """The full dotted text of a Rust `scoped_identifier` chain (`std::env::
    var` -> `"std::env::var"`), for the SEC110 violation's site text."""
    return node_text(node) or "?"


def _rust_string_literal_text(node: Node) -> str | None:
    """The unquoted text of a Rust `string_literal` node's content, or
    `None`."""
    if node.type != "string_literal":
        return None
    frag = next((c for c in node.named_children if c.type == "string_content"), None)
    return node_text(frag) if frag is not None else ""


def _scan_rust_env_access(
    tree: Tree,
    rel_path: str,
    declared: _DeclaredSurface = _EMPTY_DECLARED_SURFACE,
) -> tuple[Violation, ...]:
    """SEC110 (T-0352) over `std::env::var(...)`/`env::var(...)`/
    `std::env::var_os(...)` call sites -- the Rust equivalent of
    `_scan_python_env_access`. A non-literal argument still fires
    (NO-FAIL-SILENT); `declared` (T-0351) discharges a Secret-clearance
    code binding."""
    if declared._has_secret(rel_path):
        return ()
    violations: list[Violation] = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "call_expression":
            func = node.child_by_field_name("function")
            args = node.child_by_field_name("arguments")
            if func is not None and _rust_scoped_name(func) in _RUST_ENV_CALL_NAMES:
                var_name = None
                if args is not None and args.named_children:
                    var_name = _rust_string_literal_text(args.named_children[0])
                if var_name is not None and _is_allowlisted_env_var(var_name):
                    stack.extend(node.children)
                    continue
                site = f"{_rust_dotted_prefix(func)}(...)"
                violations.append(
                    _sec110_violation(rel_path, node.start_point[0] + 1, site)
                )
        stack.extend(node.children)
    return tuple(violations)


#: (glob pattern, scan functions) for each T-0352 cross-language file
#: population -- every entry's tree-sitter parse goes through the SAME
#: `frob.lang.raw_tree` dispatch (module comment: reuse, not a new parser).
_CROSS_LANGUAGE_SCANS: tuple[tuple[str, tuple], ...] = (
    ("*.ts", (_scan_ts_fields, _scan_ts_env_access)),
    ("*.tsx", (_scan_ts_fields, _scan_ts_env_access)),
    ("*.rs", (_scan_rust_fields, _scan_rust_env_access)),
)


def _scan_cross_language_files(
    root: Path, declared: _DeclaredSurface
) -> tuple[tuple[Violation, ...], int]:
    """PII010/SEC110 (T-0352) over every git-tracked `.ts`/`.tsx`/`.rs`
    file under `root`, via `_CROSS_LANGUAGE_SCANS`. Returns (violations,
    scanned-file-count). A file `frob.lang.raw_tree` cannot parse is
    logged at WARNING and skipped (the same degrade-don't-crash posture
    the Python branch's `ast.parse` failure uses, just louder -- a non-
    Python grammar failure is rarer and more worth a human's attention)."""
    violations: list[Violation] = []
    scanned = 0
    seen_paths: set[str] = set()
    for pattern, scan_fns in _CROSS_LANGUAGE_SCANS:
        for rel_path in _tracked_files_by_pattern(root, pattern):
            if rel_path in seen_paths or _is_pii_self_pattern_file(root, rel_path):
                continue
            seen_paths.add(rel_path)
            parsed = raw_tree(root / rel_path)
            if parsed.is_err:
                _log.warning(
                    "pii_structural_gate: skipping unparseable %s: %s",
                    rel_path,
                    parsed.danger_err,
                )
                continue
            tree, _source, _label = parsed.danger_ok
            scanned += 1
            for scan_fn in scan_fns:
                violations.extend(scan_fn(tree, rel_path, declared))
    return tuple(violations), scanned

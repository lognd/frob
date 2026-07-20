"""DOC004: unbound/stale fenced code blocks in docs (docs/modules/gates.md#doc004).

Motivating case (T-0436): a fenced code block in a `.md` doc -- a python
`from X import Y` example, a rust `use crate::path` snippet, a `frob
<subcommand>` console example -- is the highest-drift-risk prose in a repo.
Nothing binds it to the code it demonstrates, so when the referenced symbol
is renamed or the command is removed, the doc silently goes stale. No
existing gate catches this: REF001/002/003 (`frob.gates._refs`) reason about
whole-FILE reachability, never about a fenced block's own text; DOC001/002
(`doclink_gate`/`docanchor_gate` in this package's `__init__.py`) reason
about doc-to-doc/doc-to-symbol link structure, never about code embedded
inside a doc's prose.

SIMPLE, CONSERVATIVE, PROJECT-GENERIC heuristic (per the ticket, three
explicit user refinements folded in):

1. Determine THIS project's own import/crate namespaces from its manifests
   (never the directory name, never a hardcoded per-tool list):
   - Python: `pyproject.toml`'s `[project].name` (normalized `-` -> `_`)
     plus every top-level importable package found under `src/`.
   - Rust: the root `Cargo.toml`'s `[package].name` (normalized `-` -> `_`,
     since `use` paths are always underscore-separated regardless of the
     crate's hyphenated Cargo name) PLUS every `[workspace].members` glob's
     resolved subcrate name -- each subcrate is its OWN namespace (a repo
     packaged as `logandapp_backend` is keyed on that name, not its
     directory).
   - TS/JS: `package.json`'s `name` field (scope preserved, e.g.
     `@scope/pkg`) plus any `workspaces` member's own `package.json` name.
   Computed once per gate run (`_project_namespaces`), not per file.

2. For every git-tracked `.md` file, extract every fenced code block
   (` ```lang ... ``` `) and, per the fence's language tag, extract simple
   reference tokens: python `from X import ...` / `import X...`; rust
   `use X::...;`; ts/js `import ... from "X"` / `require("X")`. A token
   whose root namespace segment is NOT one of this project's own namespaces
   is skipped outright -- external library usage, `numpy`, `tokio`,
   `node_modules` deps, generic shell (`git`, `ls`, `make`, ...), and
   pseudo-code are never flagged (the REF001 false-positive lesson: a noisy
   gate gets blanket-waived, so this stays deliberately narrow).

3. A token that DOES reference this project's own surface is checked two
   ways:
   - STALE (error): the referenced module/crate/symbol does not resolve
     against the real graph (python: checked against `GraphSnapshot`
     symbols keyed by `path::qualname`; rust: checked by scanning the
     resolved crate's tracked `.rs` files for a matching `pub` item
     declaration) -- concrete drift already present.
   - UNBOUND (warn): the reference DOES resolve (or, for TS/JS, could not
     be confidently disproven -- see `_ts_reference_violation`) but the
     block carries no `frob:doc`/`frob:describes`/`frob:tests` binding
     directive within itself or its three immediately-preceding lines, so
     future drift on this exact block would go undetected.

4. `frob:waive DOC004 reason="..."` is honored directly out of the block's
   own nearby text (NOT routed through `frob.graph`'s edge/waiver model --
   `.md` files are never fed through `frob.graph.dsl.parse_directives`,
   only `markdown_anchors`'s narrower `frob:describes` scan, so a
   `.md`-embedded `frob:waive` has no graph edge to attach to). This is a
   deliberate, prominent escape hatch for a genuinely external or
   illustrative block the heuristic cannot confidently classify -- see
   `_nearby_waive_reason`.

Console/bash command-drift checking (the original ticket's tier (a)) is
NOT implemented in this pass: T-0436's refinement 1 explicitly demands a
CONFIGURABLE command source (a `frob.toml`-declared entry point, generic
per project, frob being only one instance) rather than a hardcoded
argparse-of-frob special case, and building that generically was judged
out of scope for a first, conservative landing -- filed as a follow-up
(see this ticket's Done report in tickets.md for the filed id). Every
acceptance case in the ticket body that does NOT require console-command
resolution is covered by this module.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gitio import run_argv
from frob.graph._models import GraphSnapshot
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = ["doc004_gate"]


# ---------------------------------------------------------------------------
# Manifest-derived project namespaces (T-0436 refinement 3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ProjectNamespaces:
    """This project's own import/crate namespaces, derived from manifests."""

    python: frozenset[str] = field(default_factory=frozenset)
    rust: frozenset[str] = field(default_factory=frozenset)
    ts: frozenset[str] = field(default_factory=frozenset)
    # rust namespace -> crate source directory (repo-relative), used to
    # resolve a `use <crate>::path::Item` token to the .rs files that
    # could plausibly define `Item`.
    rust_crate_dirs: dict[str, str] = field(default_factory=dict)


def _read_toml(path: Path) -> dict | None:
    """Best-effort TOML load: `None` on any missing/unreadable/malformed file,
    never a crash -- a missing manifest just means that language contributes
    no namespaces, not a gate failure."""
    if not path.exists():
        return None
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("doc004: %s unreadable: %s", path, exc)
        return None


def _python_namespaces(root: Path) -> frozenset[str]:
    """`pyproject.toml`'s `[project].name` plus every top-level importable
    package under `src/` (a `dir/__init__.py`) -- covers both the packaged
    name and any secondary top-level package a repo ships."""
    names: set[str] = set()
    data = _read_toml(root / "pyproject.toml")
    if data is not None:
        project_name = data.get("project", {}).get("name")
        if isinstance(project_name, str) and project_name:
            names.add(project_name.replace("-", "_"))
    src = root / "src"
    if src.is_dir():
        for entry in src.iterdir():
            if entry.is_dir() and (entry / "__init__.py").exists():
                names.add(entry.name)
    return frozenset(names)


def _rust_crate_name(cargo_toml: Path) -> str | None:
    """`[package].name` from one `Cargo.toml`, normalized `-` -> `_` (the
    form every `use` path actually spells), or `None` if unreadable/absent."""
    data = _read_toml(cargo_toml)
    if data is None:
        return None
    name = data.get("package", {}).get("name")
    if isinstance(name, str) and name:
        return name.replace("-", "_")
    return None


def _rust_namespaces(root: Path) -> tuple[frozenset[str], dict[str, str]]:
    """Root crate name (if any) plus every `[workspace].members` glob's
    resolved subcrate -- each subcrate is its own namespace (T-0436
    refinement 3: `logand.app` -> `logandapp_backend`, not the dir name).
    Returns (namespace set, {namespace: crate-source-dir repo-relative})."""
    names: set[str] = set()
    dirs: dict[str, str] = {}
    root_cargo = root / "Cargo.toml"
    data = _read_toml(root_cargo)
    if data is None:
        return frozenset(), {}
    root_name = _rust_crate_name(root_cargo)
    if root_name is not None:
        names.add(root_name)
        dirs[root_name] = "."
    members = data.get("workspace", {}).get("members", [])
    if isinstance(members, list):
        for pattern in members:
            if not isinstance(pattern, str):
                continue
            for member_dir in sorted(root.glob(pattern)):
                if not member_dir.is_dir():
                    continue
                member_cargo = member_dir / "Cargo.toml"
                member_name = _rust_crate_name(member_cargo)
                if member_name is None:
                    continue
                names.add(member_name)
                dirs[member_name] = str(member_dir.relative_to(root).as_posix())
    return frozenset(names), dirs


def _ts_namespaces(root: Path) -> frozenset[str]:
    """`package.json`'s `name` plus every `workspaces` member's own name."""
    names: set[str] = set()
    data = _read_toml_json(root / "package.json")
    if data is not None:
        name = data.get("name")
        if isinstance(name, str) and name:
            names.add(name)
        workspaces = data.get("workspaces", [])
        if isinstance(workspaces, list):
            for pattern in workspaces:
                if not isinstance(pattern, str):
                    continue
                for member_dir in sorted(root.glob(pattern)):
                    member_data = _read_toml_json(member_dir / "package.json")
                    if member_data is None:
                        continue
                    member_name = member_data.get("name")
                    if isinstance(member_name, str) and member_name:
                        names.add(member_name)
    return frozenset(names)


def _read_toml_json(path: Path) -> dict | None:
    """`package.json` is JSON, not TOML -- separate reader, same fail-open
    posture as `_read_toml` (missing/malformed -> `None`, never a crash)."""
    import json

    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        _log.warning("doc004: %s unreadable: %s", path, exc)
        return None


def _project_namespaces(root: Path) -> _ProjectNamespaces:
    """Compute every language's namespace set once for this gate run."""
    python = _python_namespaces(root)
    rust, rust_dirs = _rust_namespaces(root)
    ts = _ts_namespaces(root)
    _log.debug("doc004: namespaces python=%s rust=%s ts=%s", python, rust, ts)
    return _ProjectNamespaces(
        python=python, rust=rust, ts=ts, rust_crate_dirs=rust_dirs
    )


# ---------------------------------------------------------------------------
# Fenced code block extraction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _FencedBlock:
    """One ` ```lang ... ``` ` block: its language tag, body text, and the
    1-indexed line range (fence-open line, fence-close line) in the doc."""

    lang: str
    body: str
    start_line: int
    end_line: int


_FENCE_OPEN_RE = re.compile(r"^```\s*([A-Za-z0-9_+-]*)\s*$")
_FENCE_CLOSE_RE = re.compile(r"^```\s*$")


def _iter_fenced_blocks(text: str) -> tuple[_FencedBlock, ...]:
    """Every top-level ` ``` ` fenced block in `text`, in document order.

    Deliberately simple line-scan (no nested-fence handling -- markdown
    doesn't nest triple-backtick fences) matching the `doclink_gate`/
    `docanchor_gate` posture of this package: heuristic over raw doc text,
    never a full markdown parser."""
    blocks: list[_FencedBlock] = []
    lines = text.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        open_match = _FENCE_OPEN_RE.match(lines[i])
        if open_match is None:
            i += 1
            continue
        lang = open_match.group(1).lower()
        start_line = i + 1
        body_lines: list[str] = []
        j = i + 1
        while j < n and _FENCE_CLOSE_RE.match(lines[j]) is None:
            body_lines.append(lines[j])
            j += 1
        end_line = j + 1 if j < n else j
        blocks.append(
            _FencedBlock(
                lang=lang,
                body="\n".join(body_lines),
                start_line=start_line,
                end_line=end_line,
            )
        )
        i = j + 1
    return tuple(blocks)


_PYTHON_LANGS = frozenset({"python", "py"})
_RUST_LANGS = frozenset({"rust", "rs"})
_TS_LANGS = frozenset({"ts", "tsx", "js", "jsx", "javascript", "typescript"})


# ---------------------------------------------------------------------------
# Nearby directive / waiver detection (T-0436 refinement 2: prominent waiver)
# ---------------------------------------------------------------------------

_BIND_MARKERS = ("frob:doc", "frob:describes", "frob:tests")
_WAIVE_DOC004_RE = re.compile(r'frob:waive\s+DOC004\s+reason="([^"]*)"')
_NEARBY_LOOKBEHIND = 3


def _nearby_window(doc_lines: list[str], block: _FencedBlock) -> list[str]:
    """The block's own body lines plus its `_NEARBY_LOOKBEHIND` immediately
    preceding doc lines -- where a binding directive or waiver must sit to
    count as "nearby" per the ticket's own wording."""
    pre_start = max(0, block.start_line - 1 - _NEARBY_LOOKBEHIND)
    preceding = doc_lines[pre_start : block.start_line - 1]
    return [*preceding, *block.body.splitlines()]


def _nearby_waive_reason(window: list[str]) -> str | None:
    """The `frob:waive DOC004 reason="..."` text found in `window`, or None.

    Handled directly here rather than through `frob.graph`'s WAIVE-edge
    machinery: `.md` files never go through `frob.graph.dsl.parse_directives`
    (only the narrower `markdown_anchors` describes-only scan), so a waiver
    written inside a doc's prose or fenced block has no graph edge to bind
    to -- see this module's docstring, point 4."""
    for line in window:
        match = _WAIVE_DOC004_RE.search(line)
        if match is not None:
            return match.group(1)
    return None


def _has_binding_directive(window: list[str]) -> bool:
    """Whether any nearby line carries a `frob:doc`/`frob:describes`/
    `frob:tests` marker (bare substring check -- these are advisory anchors
    in doc prose, not parsed DSL edges here, so exact directive syntax is
    not required, only evidence the author meant to bind the block)."""
    return any(marker in line for line in window for marker in _BIND_MARKERS)


# ---------------------------------------------------------------------------
# Python reference resolution
# ---------------------------------------------------------------------------

_PY_FROM_IMPORT_RE = re.compile(
    r"^\s*from\s+([\w][\w.]*)\s+import\s+(.+?)\s*$", re.MULTILINE
)
_PY_IMPORT_RE = re.compile(r"^\s*import\s+([\w][\w.]*)", re.MULTILINE)
_PAREN_IMPORT_RE = re.compile(r"import\s*\(([^)]*)\)", re.DOTALL)


def _collapse_paren_imports(body: str) -> str:
    """Fold `from X import (\\n  a,\\n  b,\\n)` onto one logical line so
    `_PY_FROM_IMPORT_RE` (single-line by design, matching `doclink_gate`'s
    plain-regex posture) sees the full name list instead of a bare `(`.
    Without this, a parenthesized multi-line import produced a garbage
    "name" of `(` and a spurious stale finding (round-2 fix, caught
    dogfooding this gate on frob's own `docs/guides/extending/
    sys-export-formats.md`)."""
    return _PAREN_IMPORT_RE.sub(
        lambda m: "import " + m.group(1).replace("\n", " "), body
    )


def _python_module_map(root: Path) -> dict[str, str]:
    """`{dotted.module.path: repo-relative file path}` for every git-tracked
    `.py` file under `src/` -- `src/frob/gates/__init__.py` maps to
    `frob.gates`, `src/frob/foo.py` maps to `frob.foo`.

    Walked from tracked FILES, not from `GraphSnapshot.symbols` (T-0436
    round-2 fix): a package `__init__.py` that only imports and re-exports
    other modules' symbols (no locally-defined symbol of its own -- e.g.
    `frob.strata`'s `__init__.py`) has zero graph symbols recorded at that
    path, so deriving the module map from symbols alone silently dropped
    every such package and flagged real, working imports of it as stale."""
    spawned = run_argv(("git", "-C", str(root), "ls-files", "src/**/*.py"))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.warning("doc004: git ls-files src/**/*.py failed")
        return {}
    mapping: dict[str, str] = {}
    for path in spawned.danger_ok.stdout.splitlines():
        if not path:
            continue
        rel = path
        for prefix in ("src/", "./"):
            if rel.startswith(prefix):
                rel = rel[len(prefix) :]
        if rel.endswith("/__init__.py"):
            rel = rel[: -len("/__init__.py")]
        elif rel.endswith(".py"):
            rel = rel[: -len(".py")]
        dotted = rel.replace("/", ".")
        if dotted:
            mapping[dotted] = path
    return mapping


def _python_symbol_names_by_path(snapshot: GraphSnapshot) -> dict[str, set[str]]:
    """`{file path: {top-level qualname segments}}` for every python file
    with at least one graph symbol -- built once per gate run alongside
    `_python_module_map`, never as shared mutable global state (this gate
    runs inside `run_gates`'s `ThreadPoolExecutor`)."""
    by_path: dict[str, set[str]] = {}
    for record in snapshot.symbols.values():
        path = record.id.path
        if not path.endswith(".py"):
            continue
        by_path.setdefault(path, set()).add(record.id.qualname.split(".", 1)[0])
    return by_path


_ALL_BLOCK_RE = re.compile(r"__all__\s*=\s*\[(.*?)\]", re.DOTALL)
_IMPORT_PAREN_RE = re.compile(
    r"^\s*from\s+\S+\s+import\s*\(([^)]*)\)", re.MULTILINE | re.DOTALL
)
_IMPORT_LINE_RE = re.compile(
    r"^\s*(?:from\s+\S+\s+import\s+|import\s+)(.+)$", re.MULTILINE
)


def _module_reexports(root: Path, file_path: str, name: str) -> bool:
    """Whether `name` is plausibly re-exported by `file_path` -- either
    listed in its `__all__` list or appearing on one of its own
    `import`/`from ... import` statements (single-line or parenthesized
    multi-line).

    `_python_symbol_names_by_path` only sees names DEFINED in a file (the
    graph indexes definitions, not re-export bindings); a package
    `__init__.py` that imports a submodule's symbol and re-exports it via
    `__all__` is extremely common and correct (`frob.strata`'s own
    `__init__.py` does exactly this for `load_design_ids`), so treating
    that as stale would be a false positive the REF001 lesson warns
    against. Deliberately loose (any textual match within the file's own
    import/`__all__` regions) rather than a full re-export resolver --
    conservative in the FALSE-POSITIVE direction: it can miss a genuinely
    stale re-export, never wrongly flag a real, working one."""
    try:
        text = (root / file_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    blob = "\n".join(
        [
            *_ALL_BLOCK_RE.findall(text),
            *_IMPORT_PAREN_RE.findall(text),
            *_IMPORT_LINE_RE.findall(text),
        ]
    )
    return re.search(rf"\b{re.escape(name)}\b", blob) is not None


def _python_from_import_violations(
    block: _FencedBlock,
    doc_path: str,
    doc_lines: list[str],
    namespaces: frozenset[str],
    module_map: dict[str, str],
    symbol_names_by_path: dict[str, set[str]],
    root: Path,
) -> list[Violation]:
    """Check every `from X import a, b, c` in `block` against `module_map`."""
    violations: list[Violation] = []
    window = _nearby_window(doc_lines, block)
    waive_reason = _nearby_waive_reason(window)
    collapsed_body = _collapse_paren_imports(block.body)
    for match in _PY_FROM_IMPORT_RE.finditer(collapsed_body):
        module = match.group(1)
        root_ns = module.split(".", 1)[0]
        if root_ns not in namespaces:
            continue
        if waive_reason is not None:
            _log.debug(
                "doc004: %s waived (%s): %s", doc_path, waive_reason, match.group(0)
            )
            continue
        names = [
            n.strip().split(" as ", 1)[0].strip()
            for n in match.group(2).split(",")
            if n.strip() and n.strip() != "*"
        ]
        file_path = module_map.get(module)
        if file_path is None:
            violations.append(
                _doc004_violation(
                    doc_path,
                    block.start_line,
                    tier="stale",
                    detail=f"module {module!r} does not resolve to a real symbol",
                )
            )
            continue
        top_names = symbol_names_by_path.get(file_path, set())
        for name in names:
            if (
                name in top_names
                or f"{module}.{name}" in module_map
                or _module_reexports(root, file_path, name)
            ):
                continue
            violations.append(
                _doc004_violation(
                    doc_path,
                    block.start_line,
                    tier="stale",
                    detail=f"{module}.{name} does not resolve to a real symbol",
                )
            )
        if not violations and not _has_binding_directive(window):
            violations.append(
                _doc004_violation(
                    doc_path,
                    block.start_line,
                    tier="unbound",
                    detail=f"python import of {module} is not anchored",
                )
            )
    return violations


# ---------------------------------------------------------------------------
# Rust reference resolution
# ---------------------------------------------------------------------------

_RUST_USE_RE = re.compile(r"^\s*use\s+([\w:]+)(?:::\{([^}]*)\})?\s*;", re.MULTILINE)
_RUST_PUB_ITEM_RE_TMPL = (
    r"\bpub(?:\([^)]*\))?\s+(?:fn|struct|enum|trait|mod|const|static|type)\s+{name}\b"
)


def _rust_crate_source_files(root: Path, crate_dir: str) -> tuple[str, ...]:
    """Every git-tracked `.rs` file under `crate_dir` (repo-relative)."""
    spawned = run_argv(("git", "-C", str(root), "ls-files", f"{crate_dir}/**/*.rs"))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return ()
    return tuple(line for line in spawned.danger_ok.stdout.splitlines() if line)


def _rust_item_defined(root: Path, files: tuple[str, ...], name: str) -> bool:
    """Whether any tracked `.rs` file in `files` declares a `pub` item named
    `name` (fn/struct/enum/trait/mod/const/static/type) -- a textual,
    conservative existence check, not a real rust resolver."""
    pattern = re.compile(_RUST_PUB_ITEM_RE_TMPL.format(name=re.escape(name)))
    for rel in files:
        try:
            text = (root / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if pattern.search(text):
            return True
    return False


def _rust_use_violations(
    block: _FencedBlock,
    doc_path: str,
    doc_lines: list[str],
    root: Path,
    namespaces: _ProjectNamespaces,
) -> list[Violation]:
    """Check every `use X::...;` in `block` against the resolved crate's
    tracked `.rs` sources (`_rust_item_defined`)."""
    violations: list[Violation] = []
    window = _nearby_window(doc_lines, block)
    waive_reason = _nearby_waive_reason(window)
    for match in _RUST_USE_RE.finditer(block.body):
        path = match.group(1)
        segments = path.split("::")
        root_ns = segments[0]
        if root_ns in ("crate", "self", "super"):
            continue
        if root_ns not in namespaces.rust:
            continue
        if waive_reason is not None:
            _log.debug(
                "doc004: %s waived (%s): %s", doc_path, waive_reason, match.group(0)
            )
            continue
        braced = match.group(2)
        items = (
            [i.strip() for i in braced.split(",") if i.strip()]
            if braced
            else [segments[-1]]
            if len(segments) > 1
            else []
        )
        crate_dir = namespaces.rust_crate_dirs.get(root_ns, ".")
        files = _rust_crate_source_files(root, crate_dir)
        block_violations: list[Violation] = []
        for item in items:
            if item in ("*",):
                continue
            item_name = item.split(" as ", 1)[0].strip()
            if files and not _rust_item_defined(root, files, item_name):
                block_violations.append(
                    _doc004_violation(
                        doc_path,
                        block.start_line,
                        tier="stale",
                        detail=(
                            f"use {path}::{item_name} does not resolve to a "
                            f"pub item in crate {root_ns!r}"
                        ),
                    )
                )
        if block_violations:
            violations.extend(block_violations)
        elif not _has_binding_directive(window):
            violations.append(
                _doc004_violation(
                    doc_path,
                    block.start_line,
                    tier="unbound",
                    detail=f"rust use of {path} is not anchored",
                )
            )
    return violations


# ---------------------------------------------------------------------------
# TS/JS reference resolution (UNBOUND tier only -- see module docstring)
# ---------------------------------------------------------------------------

_TS_IMPORT_RE = re.compile(
    r'(?:import\s+.*?\s+from\s+|require\()\s*["\']([^"\']+)["\']', re.MULTILINE
)


def _ts_reference_violations(
    block: _FencedBlock, doc_path: str, doc_lines: list[str], namespaces: frozenset[str]
) -> list[Violation]:
    """UNBOUND-only: no reliable static resolver for TS/JS exports here, so
    this never claims STALE (would risk false positives on export shapes
    this simple regex-scanner cannot see) -- it only flags an unanchored
    reference to the project's OWN package (per `package.json`), leaving
    `node_modules` deps and relative imports (`./`, `../`) untouched."""
    violations: list[Violation] = []
    window = _nearby_window(doc_lines, block)
    waive_reason = _nearby_waive_reason(window)
    seen_project_ref = False
    for match in _TS_IMPORT_RE.finditer(block.body):
        specifier = match.group(1)
        if specifier.startswith((".", "/")):
            continue
        if specifier not in namespaces and not any(
            specifier.startswith(ns + "/") for ns in namespaces
        ):
            continue
        seen_project_ref = True
    if seen_project_ref and waive_reason is None and not _has_binding_directive(window):
        violations.append(
            _doc004_violation(
                doc_path,
                block.start_line,
                tier="unbound",
                detail="ts/js import of a project package is not anchored",
            )
        )
    elif seen_project_ref and waive_reason is not None:
        _log.debug("doc004: %s waived (%s): ts/js block", doc_path, waive_reason)
    return violations


# ---------------------------------------------------------------------------
# Violation building + public entry point
# ---------------------------------------------------------------------------


def _doc004_violation(doc_path: str, line: int, *, tier: str, detail: str) -> Violation:
    """Build one DOC004 `Violation` -- `tier` is `"stale"` (error, a named
    reference does not resolve) or `"unbound"` (warn, a valid reference has
    no nearby binding directive)."""
    severity = Severity.ERROR if tier == "stale" else Severity.WARN
    label = "stale" if tier == "stale" else "unbound"
    return Violation(
        rule="DOC004",
        severity=severity,
        file=doc_path,
        line=line,
        message=(
            f"DOC004: {label} code block in {doc_path}:{line} -- {detail}; "
            f"add a frob:doc/frob:describes/frob:tests anchor, fix the stale "
            f'reference, or `frob:waive DOC004 reason="..."` if this is an '
            f"intentional external/illustrative example"
        ),
    )


def _tracked_md_files(root: Path) -> tuple[str, ...]:
    """Every git-tracked `.md` file under `root`, repo-relative POSIX paths."""
    spawned = run_argv(("git", "-C", str(root), "ls-files", "*.md"))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.warning("doc004: git ls-files *.md failed")
        return ()
    return tuple(line for line in spawned.danger_ok.stdout.splitlines() if line)


# frob:doc docs/modules/gates.md#doc004-unbound-stale-doc-code-blocks-t-0436
# frob:tests tests/test_docblocks_gate.py::TestPythonNamespace.\
# test_python_import_of_nonexistent_symbol_is_stale
# frob:tests tests/test_docblocks_gate.py::TestPythonNamespace.\
# test_anchored_block_passes
# frob:tests tests/test_docblocks_gate.py::TestPythonNamespace.\
# test_unanchored_but_valid_import_warns_unbound
# frob:tests tests/test_docblocks_gate.py::TestPythonNamespace.\
# test_waive_doc004_suppresses
# frob:tests tests/test_docblocks_gate.py::TestPythonNamespace.\
# test_generic_external_shell_block_not_flagged
# frob:tests tests/test_docblocks_gate.py::TestPythonNamespace.\
# test_package_name_differs_from_directory_name
# frob:tests tests/test_docblocks_gate.py::TestRustNamespace.\
# test_rust_use_of_missing_item_is_stale
# frob:tests tests/test_docblocks_gate.py::TestRustNamespace.\
# test_rust_use_of_real_item_passes_or_warns_never_stale
# frob:tests tests/test_docblocks_gate.py::TestRustNamespace.\
# test_external_crate_use_not_flagged
def doc004_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """DOC004: scan every tracked `.md` doc's fenced code blocks for
    references to THIS PROJECT's own code surface (manifest-derived
    namespaces, all languages) that are either STALE (the named
    module/crate/symbol does not resolve -- error) or UNBOUND (it resolves,
    but no nearby `frob:doc`/`frob:describes`/`frob:tests` anchor exists --
    warn). See this module's docstring for the full heuristic and its
    deliberate scope cuts."""
    root = Path(root)
    namespaces = _project_namespaces(root)
    module_map = _python_module_map(root)
    symbol_names_by_path = _python_symbol_names_by_path(snapshot)

    violations: list[Violation] = []
    for doc_path in _tracked_md_files(root):
        text = _read_md(root, doc_path)
        if text is None:
            continue
        doc_lines = text.splitlines()
        for block in _iter_fenced_blocks(text):
            if block.lang in _PYTHON_LANGS:
                violations.extend(
                    _python_from_import_violations(
                        block,
                        doc_path,
                        doc_lines,
                        namespaces.python,
                        module_map,
                        symbol_names_by_path,
                        root,
                    )
                )
            elif block.lang in _RUST_LANGS:
                violations.extend(
                    _rust_use_violations(block, doc_path, doc_lines, root, namespaces)
                )
            elif block.lang in _TS_LANGS:
                violations.extend(
                    _ts_reference_violations(block, doc_path, doc_lines, namespaces.ts)
                )
    _log.info("doc004: %d violation(s) across tracked .md docs", len(violations))
    return tuple(violations)


def _read_md(root: Path, rel_path: str) -> str | None:
    """Best-effort doc text, `None` for unreadable/binary -- never a crash."""
    try:
        return (root / rel_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

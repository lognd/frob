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

5. Console/bash command-drift checking (T-0443, the tier T-0436 deferred):
   a ` ```console ``` `/` ```bash ``` `/` ```sh ``` `/` ```shell ``` ` fenced
   block's lines are scanned for an invocation of a CONFIGURED command
   (never a hardcoded, frob-specific subcommand list -- frob is only one
   instance of a project this gate can run over). `frob.toml`'s
   `[[docblocks.commands]]` array declares each command source generically:

   ```toml
   [[docblocks.commands]]
   prog = "frob"
   parser = "frob.__main__:_build_parser"
   ```

   `prog` is the console word introducing the invocation; `parser` is a
   `module:callable` dotted path to a zero-argument factory returning an
   `argparse.ArgumentParser` (this project's own CLI already has exactly
   one: `frob.__main__._build_parser`). The gate imports that callable AT
   CHECK TIME and walks its live `add_subparsers` tree to derive the valid
   subcommand chains -- this is deliberately NOT a second, hand-maintained
   copy of the CLI surface; the argparse registry IS the single source of
   truth, and a subcommand rename/removal there is picked up automatically
   with zero edits to this gate or to `frob.toml`. A `prog word ...` line
   whose subcommand chain does not walk the tree is STALE (error); one that
   does resolve is checked for a nearby binding directive same as the other
   tiers (UNBOUND, warn). No configured `[[docblocks.commands]]` entries at
   all (a project that has not opted in) means no console/bash checking
   happens -- fail-open, same posture as every other namespace source in
   this module.

DOC005 (T-0435): the same live-registry walk, applied to `README.md`'s
command TABLE rather than fenced code blocks -- a markdown table row
"| `<prog> <name>` | ... |" is checked against the live top-level
subcommand tree the SAME `[[docblocks.commands]]` config already supplies:
a real subcommand with no row is MISSING (error), a row naming a
subcommand that no longer exists is STALE (error). A "N commands" prose
count claim is checked the same way, against the live top-level command
count. See `doc005_gate` for the full mechanism -- it reuses
`_console_command_sources`/`_console_trees` rather than a second
registry-reading mechanism.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from frob.gates._models import Severity, Violation
from frob.gitio import run_argv
from frob.graph._models import GraphSnapshot
from frob.logging import get_logger
from frob.tomlio import read_toml_lenient

if TYPE_CHECKING:
    from frob.gates._docblocks_refs import _ConsoleCommandSource

_log = get_logger(__name__)

__all__ = ["doc004_gate", "doc005_gate"]


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
    no namespaces, not a gate failure. Thin wrapper over `frob.tomlio.
    read_toml_lenient` (extracted T-0861) that fixes this module's own
    `log_prefix`."""
    return read_toml_lenient(path, log_prefix="doc004")


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
            # frob:waive WALK001 reason="Cargo workspace member glob (e.g. 'crates/*'), a single shallow level, not a recursive repo walk"  # noqa: E501
            # frob:waive PERF004 reason="sorted() is this loop's own iterable, not repeated -- a fresh glob() per member pattern, evaluated once at loop entry"  # noqa: E501
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


def _ts_workspace_member_names(root: Path, pattern: str) -> set[str]:
    """Package names declared by every `package.json` matching one
    `workspaces` glob pattern (extracted from `_ts_namespaces` to cut
    nesting, T-0394)."""
    names: set[str] = set()
    # frob:waive WALK001 reason="npm workspaces glob (e.g. 'packages/*'), a single shallow level, not a recursive repo walk"  # noqa: E501
    # frob:waive PERF004 reason="sorted() is this loop's own iterable, not repeated -- a fresh glob() per member pattern, evaluated once at loop entry"  # noqa: E501
    for member_dir in sorted(root.glob(pattern)):
        member_data = _read_toml_json(member_dir / "package.json")
        if member_data is None:
            continue
        member_name = member_data.get("name")
        if isinstance(member_name, str) and member_name:
            names.add(member_name)
    return names


def _ts_namespaces(root: Path) -> frozenset[str]:
    """`package.json`'s `name` plus every `workspaces` member's own name."""
    names: set[str] = set()
    data = _read_toml_json(root / "package.json")
    if data is None:
        return frozenset(names)
    name = data.get("name")
    if isinstance(name, str) and name:
        names.add(name)
    workspaces = data.get("workspaces", [])
    if isinstance(workspaces, list):
        for pattern in workspaces:
            if isinstance(pattern, str):
                names |= _ts_workspace_member_names(root, pattern)
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


# frob:enforces CHK-GATE-DOC004
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
# frob:tests \
# tests/test_docblocks_gate.py::TestPythonNamespace.test_python_import_of_nonexistent_s\
# ymbol_is_stale
# frob:tests \
# tests/test_docblocks_gate.py::TestPythonNamespace.test_anchored_block_passes
# frob:tests \
# tests/test_docblocks_gate.py::TestPythonNamespace.test_unanchored_but_valid_import_wa\
# rns_unbound
# frob:tests \
# tests/test_docblocks_gate.py::TestPythonNamespace.test_waive_doc004_suppresses
# frob:tests \
# tests/test_docblocks_gate.py::TestPythonNamespace.test_generic_external_shell_block_n\
# ot_flagged
# frob:tests \
# tests/test_docblocks_gate.py::TestPythonNamespace.test_package_name_differs_from_dire\
# ctory_name
# frob:tests \
# tests/test_docblocks_gate.py::TestRustNamespace.test_rust_use_of_missing_item_is_stale
# frob:tests \
# tests/test_docblocks_gate.py::TestRustNamespace.test_rust_use_of_real_item_passes_or_\
# warns_never_stale
# frob:tests \
# tests/test_docblocks_gate.py::TestRustNamespace.test_external_crate_use_not_flagged
# frob:tests \
# tests/test_gates.py::TestDoc004ConsoleCommandDrift.test_nonexistent_subcommand_is_sta\
# le
# frob:tests \
# tests/test_gates.py::TestDoc004ConsoleCommandDrift.test_real_subcommand_anchored_pass\
# es
# frob:tests \
# tests/test_gates.py::TestDoc004ConsoleCommandDrift.test_real_subcommand_unanchored_wa\
# rns_unbound
# frob:tests \
# tests/test_gates.py::TestDoc004ConsoleCommandDrift.test_waive_suppresses_console_stale
# frob:tests \
# tests/test_gates.py::TestDoc004ConsoleCommandDrift.test_no_config_means_no_console_ch\
# ecking
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
    console_sources = _console_command_sources(root)
    console_trees = _console_trees(root, console_sources)

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
            elif block.lang in _C_CPP_LANGS:
                violations.extend(
                    _c_include_violations(block, doc_path, doc_lines, root)
                )
            elif block.lang in _CONSOLE_LANGS and console_sources:
                violations.extend(
                    _console_command_violations(
                        block, doc_path, doc_lines, console_sources, console_trees
                    )
                )
    _log.info("doc004: %d violation(s) across tracked .md docs", len(violations))
    return tuple(violations)


# ---------------------------------------------------------------------------
# DOC005: README command-table + checkable-count drift-lock (T-0435)
# ---------------------------------------------------------------------------

# A markdown table row naming a console invocation: `| `frob foo` | ... |`.
# Deliberately narrow (one prog word + one subcommand word, backtick-quoted,
# leading table-pipe) -- prose mentions of `frob` elsewhere in the doc are
# not table rows and are never flagged.
_README_TABLE_ROW_RE = re.compile(r"^\s*\|\s*`([\w.-]+)\s+([\w-]+)`")

# A checkable-count claim in prose: "25 commands", "30 total commands",
# case-insensitive. Narrow to the word "commands" -- this is the one
# checkable count T-0435 names explicitly; other claimed counts (gates,
# tickets) are a documented follow-up, not silently assumed handled here.
_README_COUNT_CLAIM_RE = re.compile(r"\b(\d+)\s+(?:total\s+)?commands\b", re.IGNORECASE)


def _readme_table_rows(text: str) -> list[tuple[int, str, str]]:
    """`(line_no, prog, subcommand)` for every command-table row found in
    `text` -- `line_no` is 1-based, matching every other violation site in
    this module."""
    rows: list[tuple[int, str, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        match = _README_TABLE_ROW_RE.match(line)
        if match is None:
            continue
        rows.append((line_no, match.group(1), match.group(2)))
    return rows


def _readme_count_claims(text: str) -> list[tuple[int, int]]:
    """`(line_no, claimed_count)` for every "N commands" claim found in
    `text` -- see `_README_COUNT_CLAIM_RE`."""
    claims: list[tuple[int, int]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for match in _README_COUNT_CLAIM_RE.finditer(line):
            claims.append((line_no, int(match.group(1))))
    return claims


def _doc005_violation(doc_path: str, line: int, message: str) -> Violation:
    """Build one DOC005 `Violation` -- always ERROR: a claimed command row
    or count that does not match the live subcommand registry is concrete,
    present drift, never advisory."""
    return Violation(
        rule="DOC005",
        severity=Severity.ERROR,
        file=doc_path,
        line=line,
        message=f"DOC005: {message}",
    )


# frob:doc docs/modules/gates.md#doc005-readme-command-table-drift-lock-t-0435
# frob:tests \
# tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift.test_missing_row_for_real_co\
# mmand_fails
# frob:tests \
# tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift.test_stale_row_for_removed_c\
# ommand_fails
# frob:tests \
# tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift.test_fully_covered_table_pas\
# ses
# frob:tests \
# tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift.test_count_claim_mismatch_fa\
# ils
# frob:tests \
# tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift.test_count_claim_matching_pa\
# sses
# frob:tests \
# tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift.test_no_config_means_no_read\
# me_checking
# frob:ticket T-1011
# frob:enforces CHK-GATE-DOC005
# frob:tests tests/test_docblocks_gate.py::TestCliCommandTableGenerator.test_doc005_freshness_passes_after_sync  # noqa: E501
def doc005_gate(root: Path) -> tuple[Violation, ...]:
    """DOC005 (T-0435): bind `README.md`'s command table (and any "N
    commands" count claim) to the LIVE top-level subcommand registry --
    the same `[[docblocks.commands]]`-configured `argparse.ArgumentParser`
    factory DOC004's console tier already walks (`_console_trees`), never
    a second hand-maintained copy of the CLI surface.

    Two checks, both ERROR (concrete, present drift, not advisory):

    - a real top-level subcommand with no "| `<prog> <name>` |" row
      anywhere in README.md ("MISSING" -- README silently omits a command);
    - a README.md table row naming a `<prog> <name>` pair where `<name>`
      is not a real top-level subcommand of the live tree ("STALE" -- the
      command was renamed/removed and the row was never updated);
    - a "N commands" prose claim whose N does not equal the live top-level
      command count, summed across every configured source;
    - T-1011: `docs/modules/cli.md`'s generated command-table block (if
      the doc has opted in via `CLI_COMMAND_TABLE_START`/`_END` markers)
      no longer matches what `generate_cli_command_table` produces right
      now -- a generator-freshness check, distinct from the README half's
      hand-sync MISSING/STALE checking above.

    No `[[docblocks.commands]]` entries configured, or no `README.md` at
    `root`, means no checking happens for the README half -- fail-open,
    same posture as every other DOC004 namespace source. The cli.md
    freshness half is independent and still runs even if README.md is
    absent (it only needs a console source configured)."""
    root = Path(root)
    console_sources = _console_command_sources(root)
    if not console_sources:
        return ()

    violations: list[Violation] = list(_doc005_cli_table_freshness_violations(root))

    console_trees = _console_trees(root, console_sources)
    if not console_trees:
        return tuple(violations)

    readme_path = root / "README.md"
    if not readme_path.is_file():
        return tuple(violations)
    text = readme_path.read_text(encoding="utf-8", errors="replace")
    doc_path = "README.md"

    rows = _readme_table_rows(text)
    violations.extend(
        _doc005_missing_stale_violations(doc_path, console_sources, console_trees, rows)
    )
    violations.extend(_doc005_count_violations(doc_path, console_trees, text))

    _log.info("doc005: %d violation(s) over README.md", len(violations))
    return tuple(violations)


# frob:ticket T-0598
def _doc005_missing_stale_violations(
    doc_path: str,
    console_sources: tuple[_ConsoleCommandSource, ...],
    console_trees: dict[str, dict],
    rows: list[tuple[int, str, str]],
) -> list[Violation]:
    """MISSING (a real subcommand with no README row) and STALE (a README
    row naming a subcommand that no longer exists) DOC005 findings, one
    call per configured console source (`doc005_gate`'s per-source table
    check, split out for ARCH001 -- T-0598)."""
    violations: list[Violation] = []
    for source in console_sources:
        tree = console_trees.get(source.parser)
        if tree is None:
            continue
        live_commands = frozenset(tree.keys())
        documented_commands = frozenset(
            name for _, prog, name in rows if prog == source.prog
        )
        missing = live_commands - documented_commands
        # frob:waive PERF004 reason="own distinct missing-set per console source, not a shared re-sort"  # noqa: E501
        for name in sorted(missing):
            violations.append(
                _doc005_violation(
                    doc_path,
                    0,
                    f"real subcommand `{source.prog} {name}` has no command-"
                    f"table row in README.md -- add one, or the README "
                    f"silently omits a real command",
                )
            )
        for line_no, prog, name in rows:
            if prog != source.prog or name in live_commands:
                continue
            violations.append(
                _doc005_violation(
                    doc_path,
                    line_no,
                    f"README.md table row `{prog} {name}` names a "
                    f"subcommand that no longer exists in the live "
                    f"`{source.parser}` registry -- update or remove the "
                    f"row",
                )
            )
    return violations


# frob:ticket T-0598
def _doc005_count_violations(
    doc_path: str, console_trees: dict[str, dict], text: str
) -> list[Violation]:
    """A README "N commands" prose claim whose N does not match the live
    total command count, summed across every configured source
    (`doc005_gate`'s count-claim check, split out for ARCH001 -- T-0598)."""
    violations: list[Violation] = []
    total_live = sum(len(tree) for tree in console_trees.values())
    for line_no, claimed in _readme_count_claims(text):
        if claimed == total_live:
            continue
        violations.append(
            _doc005_violation(
                doc_path,
                line_no,
                f"README.md claims {claimed} commands but the live "
                f"registry has {total_live} -- update the claimed count",
            )
        )
    return violations


def _read_md(root: Path, rel_path: str) -> str | None:
    """Best-effort doc text, `None` for unreadable/binary -- never a crash."""
    try:
        return (root / rel_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


# ---------------------------------------------------------------------------
# `frob docs sync-commands` generator + DOC005 freshness check (T-1011)
# ---------------------------------------------------------------------------

# Marker comments delimiting the generated block `frob docs sync-commands`
# owns inside `docs/modules/cli.md` -- everything between them is rewritten
# wholesale on every sync, never hand-edited (mirrors T-1002's union-zone
# marker convention in `_land.py`, a distinct mechanism for a distinct
# purpose: THIS block is fully regenerated, not merged).
# frob:doc docs/modules/cli.md#generated-command-reference-t-1011
# frob:ticket T-1011
CLI_COMMAND_TABLE_START = "<!-- frob:generated-start cli-commands T-1011 -->"
# frob:doc docs/modules/cli.md#generated-command-reference-t-1011
# frob:ticket T-1011
CLI_COMMAND_TABLE_END = "<!-- frob:generated-end cli-commands T-1011 -->"


# frob:ticket T-1011
def _top_level_command_help(parser) -> dict[str, str]:  # noqa: ANN001
    """`{subcommand_name: help_text}` for every TOP-LEVEL subparser
    registered via `add_subparsers` on `parser` (T-1011) -- the one extra
    fact `_subparser_tree` (T-0435) does not carry, since DOC005's
    presence/absence check never needed the help STRING, only the tree
    shape. Only one level deep, matching the generated table's own
    granularity (one row per top-level command, not the full recursive
    tree)."""
    import argparse

    help_by_name: dict[str, str] = {}
    subparsers_group = getattr(parser, "_subparsers", None)
    actions = subparsers_group._group_actions if subparsers_group is not None else ()
    for action in actions:
        if not isinstance(action, argparse._SubParsersAction):
            continue
        for choice_action in action._choices_actions:
            help_by_name[choice_action.dest] = choice_action.help or ""
    return help_by_name


# frob:doc docs/modules/cli.md#generated-command-reference-t-1011
# frob:ticket T-1011
# frob:invariant INV-045
# invariant spec: [INV-045](invariants/INV-045.md)
# frob:tests tests/test_docblocks_gate.py::TestCliCommandTableGenerator.test_generate_sorts_rows_across_sources  # noqa: E501
# frob:tests tests/test_docblocks_gate.py::TestCliCommandTableGenerator.test_generate_no_config_is_none  # noqa: E501
# frob:tests tests/test_docblocks_gate.py::TestCliCommandTableGenerator.test_doc005_freshness_flags_stale_generated_block  # noqa: E501
def generate_cli_command_table(root: Path) -> str | None:
    """The exact text `docs/modules/cli.md`'s generated block (between
    `CLI_COMMAND_TABLE_START`/`CLI_COMMAND_TABLE_END`) must hold (T-1011):
    one markdown table row per live top-level subcommand, across every
    configured `[[docblocks.commands]]` source, sorted by `(prog, name)`
    for a deterministic diff. Returns `None` if no console source is
    configured at all (same fail-open posture as `doc005_gate`) -- nothing
    to generate, not an error."""
    console_sources = _console_command_sources(root)
    if not console_sources:
        return None
    rows: list[tuple[str, str, str]] = []
    for source in console_sources:
        factory = _load_parser_factory(source.parser)
        if factory is None:
            continue
        try:
            parser = factory()
        except Exception as exc:  # noqa: BLE001 -- a broken factory never crashes the gate
            _log.warning(
                "docs sync-commands: parser factory %r raised: %s",
                source.parser,
                exc,
            )
            continue
        for name, help_text in _top_level_command_help(parser).items():
            rows.append((source.prog, name, help_text))
    rows.sort(key=lambda r: (r[0], r[1]))
    lines = [CLI_COMMAND_TABLE_START, "", "| Command | Description |", "| --- | --- |"]
    for prog, name, help_text in rows:
        lines.append(f"| `{prog} {name}` | {help_text} |")
    lines.append("")
    lines.append(CLI_COMMAND_TABLE_END)
    return "\n".join(lines) + "\n"


# frob:doc docs/modules/cli.md#generated-command-reference-t-1011
# frob:ticket T-1011
# frob:tests tests/test_docblocks_gate.py::TestCliCommandTableGenerator.test_sync_replaces_only_the_marked_block  # noqa: E501
# frob:tests tests/test_docblocks_gate.py::TestCliCommandTableGenerator.test_sync_no_markers_returns_false  # noqa: E501
def sync_cli_command_table(root: Path, doc_path: str = "docs/modules/cli.md") -> bool:
    """`frob docs sync-commands`'s write step (T-1011): replace the text
    between `CLI_COMMAND_TABLE_START`/`CLI_COMMAND_TABLE_END` inside
    `root / doc_path` with `generate_cli_command_table(root)`'s fresh
    output, in place. Returns `False` (no write) if no console source is
    configured, the doc file does not exist, or the doc has no marker
    block to replace -- callers that want the block CREATED must add the
    marker pair once by hand first, the same one-time opt-in every other
    generated-block convention in this repo uses. Returns `True` after a
    real write (idempotent: a second call with nothing changed still
    returns `True`, since it re-wrote identical content)."""
    generated = generate_cli_command_table(root)
    if generated is None:
        return False
    target = root / doc_path
    if not target.is_file():
        return False
    text = target.read_text(encoding="utf-8")
    start = text.find(CLI_COMMAND_TABLE_START)
    end = text.find(CLI_COMMAND_TABLE_END)
    if start == -1 or end == -1 or end < start:
        return False
    end += len(CLI_COMMAND_TABLE_END)
    new_text = text[:start] + generated.rstrip("\n") + text[end:]
    if new_text == text:
        return True
    target.write_text(new_text, encoding="utf-8")
    return True


# frob:ticket T-1011
# frob:tests tests/test_docblocks_gate.py::TestCliCommandTableGenerator.test_generate_sorts_rows_across_sources  # noqa: E501
# frob:tests tests/test_docblocks_gate.py::TestCliCommandTableGenerator.test_sync_replaces_only_the_marked_block  # noqa: E501
# frob:tests tests/test_docblocks_gate.py::TestCliCommandTableGenerator.test_doc005_freshness_flags_stale_generated_block  # noqa: E501
def _doc005_cli_table_freshness_violations(root: Path) -> list[Violation]:
    """DOC005's freshness half (T-1011): if `docs/modules/cli.md` has a
    `CLI_COMMAND_TABLE_START`/`_END` marker block, its committed content
    must equal what `generate_cli_command_table` would produce RIGHT NOW --
    a generator-freshness check, not the hand-sync MISSING/STALE per-row
    check `doc005_gate`'s README half still does (that half is unchanged;
    this is a second, independent DOC005 source). No marker block present
    means the doc has not opted in yet -- fail-open, nothing to check."""
    doc_path = "docs/modules/cli.md"
    text = _read_md(root, doc_path)
    if text is None:
        return []
    start = text.find(CLI_COMMAND_TABLE_START)
    end = text.find(CLI_COMMAND_TABLE_END)
    if start == -1 or end == -1 or end < start:
        return []
    end += len(CLI_COMMAND_TABLE_END)
    current_block = text[start:end]
    generated = generate_cli_command_table(root)
    if generated is None:
        return []
    if current_block.strip() == generated.strip():
        return []
    return [
        _doc005_violation(
            doc_path,
            text.count("\n", 0, start) + 1,
            f"{doc_path}'s generated command table (between "
            f"{CLI_COMMAND_TABLE_START!r} and {CLI_COMMAND_TABLE_END!r}) is "
            f"stale relative to the live argparse registry -- run `frob "
            f"docs --sync-commands` to regenerate it",
        )
    ]


# T-1195 (LARGE001 residue split): the fenced-block parser, console-command
# source/subparser-tree walk, and per-language reference-violation checkers
# now live in `frob.gates._docblocks_refs`. Re-exported here under their
# original names so `frob.gates._docptr` (which imports several of them
# directly from this module) keeps working unchanged -- a pure module
# split, no behavior change.
from frob.gates._docblocks_refs import (  # noqa: E402
    _C_CPP_LANGS as _C_CPP_LANGS,
)
from frob.gates._docblocks_refs import (  # noqa: E402
    _CONSOLE_LANGS as _CONSOLE_LANGS,
)
from frob.gates._docblocks_refs import (  # noqa: E402
    _PYTHON_LANGS as _PYTHON_LANGS,
)
from frob.gates._docblocks_refs import (  # noqa: E402
    _RUST_LANGS as _RUST_LANGS,
)
from frob.gates._docblocks_refs import (  # noqa: E402
    _TS_LANGS as _TS_LANGS,
)
from frob.gates._docblocks_refs import (  # noqa: E402
    _c_include_violations as _c_include_violations,
)
from frob.gates._docblocks_refs import (  # noqa: E402
    _console_command_sources as _console_command_sources,
)
from frob.gates._docblocks_refs import (  # noqa: E402
    _console_command_violations as _console_command_violations,
)
from frob.gates._docblocks_refs import (  # noqa: E402
    _console_trees as _console_trees,
)
from frob.gates._docblocks_refs import (  # noqa: E402
    _iter_fenced_blocks as _iter_fenced_blocks,
)
from frob.gates._docblocks_refs import (  # noqa: E402
    _load_parser_factory as _load_parser_factory,
)
from frob.gates._docblocks_refs import (  # noqa: E402
    _module_reexports as _module_reexports,
)
from frob.gates._docblocks_refs import (  # noqa: E402
    _python_from_import_violations as _python_from_import_violations,
)
from frob.gates._docblocks_refs import (  # noqa: E402
    _python_module_map as _python_module_map,
)
from frob.gates._docblocks_refs import (  # noqa: E402
    _python_symbol_names_by_path as _python_symbol_names_by_path,
)
from frob.gates._docblocks_refs import (  # noqa: E402
    _resolve_command_chain as _resolve_command_chain,
)
from frob.gates._docblocks_refs import (  # noqa: E402
    _rust_use_violations as _rust_use_violations,
)
from frob.gates._docblocks_refs import (  # noqa: E402
    _ts_reference_violations as _ts_reference_violations,
)

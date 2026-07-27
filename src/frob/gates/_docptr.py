"""DOC006: doc-pointer resolution gate (docs/modules/gates.md#doc006, T-0437).

Motivating case: a doc's prose routinely "seems to point" at something --
`frob edit`, `src/frob/gone.py`, `[bogus.section]`, `docs/missing.md#x` --
and nothing checks whether the pointer is actually real. Detecting fuzzy
"seems to point" intent generically is unhardenable (high false-positive
rate): this gate instead defines a CLOSED SET of RECOGNIZED, MECHANICALLY
RESOLVABLE pointer shapes and only fires when a pointer of a known shape
targets something that does not exist. An unrecognized/ambiguous token is
never flagged -- that is the hardening, not a fuzzy-match improvement.

Five recognized pointer kinds, each detected in an inline code span
(`` `...` ``) or markdown link `[text](target)` across every git-tracked
`.md` file's PROSE (fenced code blocks are DOC004's job, `frob.gates.
_docblocks`, and are skipped here to avoid double-reporting the same
token under two rule ids):

1. FILE/PATH -- a repo-relative path (contains `/`, or is a bare
   well-known manifest basename: `frob.toml`, `pyproject.toml`,
   `Cargo.toml`, `package.json`) must exist as a git-tracked file.
2. CLI INVOCATION -- `` `<prog> <subcommand...>` `` / `` `--flag` ``
   against the SAME `[[docblocks.commands]]`-configured live argparse
   registry `frob.gates._docblocks` already walks for DOC004/DOC005 --
   one live source of truth, not a second copy.
3. CONFIG REFERENCE -- `` `[section]` ``/`` `[section.key]` `` checked
   against this project's own loaded `frob.toml` structure.
4. CODE SYMBOL -- a dotted path (`module.Class.method`) whose root
   namespace is one of this project's own manifest-derived namespaces
   (`frob.gates._docblocks._project_namespaces`), resolved the same way
   DOC004's python tier resolves a `from X import Y`.
5. DOC-ANCHOR LINK -- `docs/x.md#anchor` (inline span or markdown link):
   the file must exist and `anchor` must be a real heading/`<a id>` slug
   in it (`frob.gates.__init__._doc_anchor_slugs`, the same resolver
   DOC002 uses for `frob:doc` edges).

A sixth, source-level check rides alongside the doc-prose scan for the
SAME reason this ticket names explicitly (the DRIFT002 dotted-vs-`::`
confusion, T-0940/T-0945): a `frob:tests` directive's target is itself a
RECOGNIZED, mechanically-checkable shape -- `<file>::<qualname>` with
exactly one `::` separating the file from a DOTTED (`Class.method`)
qualname. A target with a SECOND `::` (pytest's own `Class::method`
collect-only separator, e.g. `foo.py::TestX::test_y`) is definitively the
wrong shape for a graph-facing `frob:tests` target -- this is caught here,
directly, rather than waiting for it to surface later as a generic
DRIFT002 dangling-edge failure with a less specific message.

Every finding is `frob:waive DOC006 reason="..."`-able (same nearby-line
convention as DOC004: same line or up to 3 preceding lines), for a
genuinely external/illustrative/future-facing pointer.
"""
# frob:ticket T-0437
# frob:waive INV006 reason="T-0437 INV006 first-turn-on pool: this module's \
# 'only' usages are source-level design-rationale prose (a docstring/comment \
# describing already-implemented scan-scope behavior, verifiable by reading \
# the code it annotates -- e.g. 'only fires when...', 'checked ... only the \
# top-level one') rather than a separate cross-module contract needing its \
# own tracked invariant; disposed as a calibration batch, same posture as \
# frob.gates._docblocks's own T-0585 INV006 waiver"

from __future__ import annotations

import re
import tomllib
from pathlib import Path, PurePosixPath

from frob.gates._docblocks import (
    _console_command_sources,
    _console_trees,
    _iter_fenced_blocks,
    _module_reexports,
    _project_namespaces,
    _python_module_map,
    _python_symbol_names_by_path,
    _read_md,
    _resolve_command_chain,
    _tracked_md_files,
)
from frob.gates._models import Severity, Violation
from frob.gitio import run_argv
from frob.graph._models import EdgeKind, GraphSnapshot
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = ["doc006_gate"]


# ---------------------------------------------------------------------------
# Token extraction: inline backtick spans + markdown links, prose-only
# (fenced code block bodies are DOC004's territory, skipped here).
# ---------------------------------------------------------------------------

_BACKTICK_RE = re.compile(r"`([^`\n]{2,300})`")
_MD_LINK_RE = re.compile(r"\]\(([^)\s#]+)(#[\w-]+)?\)")


def _blank_fenced_blocks(text: str) -> str:
    """Replace every fenced code block's own lines with blank lines,
    preserving line numbers (so a match's line offset in the ORIGINAL text
    stays correct) while removing its content from the prose scan -- a
    reference embedded in a code block is DOC004's job, not this gate's;
    scanning it here too would double-report the same drift under two rule
    ids."""
    lines = text.splitlines()
    for block in _iter_fenced_blocks(text):
        for i in range(block.start_line - 1, min(block.end_line, len(lines))):
            lines[i] = ""
    return "\n".join(lines)


def _prose_tokens(text: str) -> list[tuple[int, str]]:
    """`(line_no, token)` for every inline backtick span and markdown-link
    target in prose text (1-indexed lines, matching every other gate in
    this package)."""
    tokens: list[tuple[int, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for match in _BACKTICK_RE.finditer(line):
            tokens.append((line_no, match.group(1)))
        for match in _MD_LINK_RE.finditer(line):
            target = match.group(1)
            if match.group(2):
                target += match.group(2)
            tokens.append((line_no, target))
    return tokens


# ---------------------------------------------------------------------------
# Waive handling: same nearby-line convention as DOC004 (module docstring
# point 4) -- `.md` files never reach `frob.graph.dsl`'s edge/waiver model.
# ---------------------------------------------------------------------------

_WAIVE_DOC006_RE = re.compile(r'frob:waive\s+DOC006\s+reason="([^"]*)"')
_NEARBY_LOOKBEHIND = 3


def _nearby_waived(doc_lines: list[str], line_no: int) -> bool:
    """Whether a `frob:waive DOC006 reason="..."` sits on `line_no` or up to
    `_NEARBY_LOOKBEHIND` lines before it."""
    start = max(0, line_no - 1 - _NEARBY_LOOKBEHIND)
    window = doc_lines[start:line_no]
    return any(_WAIVE_DOC006_RE.search(line) for line in window)


# ---------------------------------------------------------------------------
# Violation building
# ---------------------------------------------------------------------------


# frob:enforces CHK-GATE-DOC006
def _doc006_violation(file: str, line: int, kind: str, detail: str) -> Violation:
    """Build one DOC006 violation. Shipped at WARN (T-0688 new-gate-at-
    WARN-first-turn-on precedent) -- a recognized pointer shape that does
    not resolve is real, present drift, but this gate turns on repo-wide
    against existing docs that may already carry some, so it starts
    advisory rather than an immediate hard failure."""
    return Violation(
        rule="DOC006",
        severity=Severity.WARN,
        file=file,
        line=line,
        message=(
            f"DOC006: {kind} pointer in {file}:{line} does not resolve -- "
            f"{detail}; fix the reference or "
            f'`frob:waive DOC006 reason="..."` if intentionally external/'
            f"illustrative/future-facing"
        ),
    )


# ---------------------------------------------------------------------------
# Kind 1 + 5: FILE/PATH and DOC-ANCHOR LINK
# ---------------------------------------------------------------------------

_WELL_KNOWN_MANIFESTS = frozenset(
    {"frob.toml", "pyproject.toml", "Cargo.toml", "package.json"}
)
# a plausible repo-relative path: at least one `/`, or one of the
# well-known bare manifest basenames -- never a bare identifier (the
# hardening: an unrecognized bare token, e.g. a prose word that happens to
# contain a dot, is simply not a recognized FILE/PATH shape).
_PATH_SHAPE_RE = re.compile(r"^[\w.\-]+(?:/[\w.\-]+)+$")


def _looks_like_path(token: str) -> bool:
    """Whether `token` (anchor already stripped by the caller) matches the
    recognized FILE/PATH shape -- see `_PATH_SHAPE_RE`."""
    return token in _WELL_KNOWN_MANIFESTS or bool(_PATH_SHAPE_RE.match(token))


def _file_and_anchor_violations(
    doc_path: str,
    doc_lines: list[str],
    tokens: list[tuple[int, str]],
    tracked: frozenset[str],
    anchor_cache: dict[str, set[str] | None],
    root: Path,
) -> list[Violation]:
    """Kind 1 (FILE/PATH) and kind 5 (DOC-ANCHOR LINK) checks over `tokens`.

    A path rooted at `.frob/` is a runtime-generated artifact this repo's
    own `.gitignore` deliberately keeps untracked (cache db, lease/lock
    files, the coverage/baseline stamps) -- it is real and expected to
    exist when frob has actually run, but is NEVER a git-tracked file by
    design, so checking it against `tracked` would be a systematic false
    positive on every doc that (correctly) mentions one as an example."""
    violations: list[Violation] = []
    for line_no, token in tokens:
        if token.startswith(("http://", "https://", "mailto:")):
            continue
        file_part, _, anchor_part = token.partition("#")
        if file_part.startswith(".frob/") or file_part == ".frob":
            continue
        if not _looks_like_path(file_part):
            continue
        if _nearby_waived(doc_lines, line_no):
            continue
        candidates = {file_part, file_part.lstrip("./")}
        if file_part.startswith("../") or file_part.startswith("./"):
            base = PurePosixPath(doc_path).parent
            candidates.add(str(PurePosixPath(*(base / file_part).parts)))
        if not any(c in tracked for c in candidates):
            violations.append(
                _doc006_violation(
                    doc_path,
                    line_no,
                    "file/path",
                    f"{file_part!r} is not a tracked file",
                )
            )
            continue
        if not anchor_part:
            continue
        resolved = next((c for c in candidates if c in tracked), file_part)
        if resolved not in anchor_cache:
            try:
                anchor_cache[resolved] = _heading_slugs(root / resolved)
            except OSError:
                anchor_cache[resolved] = None
        slugs = anchor_cache[resolved]
        if slugs is not None and anchor_part not in slugs:
            violations.append(
                _doc006_violation(
                    doc_path,
                    line_no,
                    "doc-anchor link",
                    f"#{anchor_part} has no matching heading/anchor in {resolved}",
                )
            )
    return violations


_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
_ANCHOR_ID_RE = re.compile(r'<a\s+id="([^"]+)"')


def _heading_slugs(path: Path) -> set[str]:
    """Every heading/`<a id>` slug in `path` -- mirrors `frob.gates.
    __init__._doc_anchor_slugs` without importing gate-package internals
    that live below `__init__.py`'s own module (this module is imported BY
    `__init__.py`, so importing back from it would cycle)."""
    from frob.graph.dsl import dedupe_slug, slugify

    text = path.read_text(encoding="utf-8", errors="replace")
    seen: dict[str, int] = {}
    slugs = {
        dedupe_slug(slugify(m.group(2)), seen) for m in _MD_HEADING_RE.finditer(text)
    }
    slugs.update(m.group(1) for m in _ANCHOR_ID_RE.finditer(text))
    return slugs


# ---------------------------------------------------------------------------
# Kind 2: CLI INVOCATION (subcommand chains + flags)
# ---------------------------------------------------------------------------

_CLI_TOKEN_RE = re.compile(
    r"^([\w.-]+)((?:\s+(?!-)[\w.-]+)*)((?:\s+-{1,2}[\w-]+)*)\s*$"
)


def _leaf_parser(parser, chain: list[str]):
    """Walk `chain` through `parser`'s `add_subparsers` tree, returning the
    parser object reached (or the deepest one reached if `chain` runs past
    a leaf) -- lets flag resolution check the CORRECT subcommand's own
    `--flag` registry rather than only the top-level one."""
    import argparse

    node = parser
    for word in chain:
        subparsers_group = getattr(node, "_subparsers", None)
        actions = (
            subparsers_group._group_actions if subparsers_group is not None else ()
        )
        found = None
        for action in actions:
            if (
                isinstance(action, argparse._SubParsersAction)
                and word in action.choices
            ):
                found = action.choices[word]
                break
        if found is None:
            return node
        node = found
    return node


def _cli_violations(
    doc_path: str,
    doc_lines: list[str],
    tokens: list[tuple[int, str]],
    console_sources,
    console_trees: dict[str, dict],
    console_parsers: dict[str, object],
) -> list[Violation]:
    """Kind 2 (CLI INVOCATION): `` `<prog> <subcommand...> [--flag...]` ``
    inline spans, checked against the SAME live registry DOC004's console
    tier walks (`_console_trees`), plus each resolved subcommand's own
    `--flag` set (`console_parsers`, this module's own leaf-parser walk --
    `_console_trees` only carries the subcommand shape, not options)."""
    violations: list[Violation] = []
    for line_no, token in tokens:
        match = _CLI_TOKEN_RE.match(token)
        if match is None:
            continue
        prog = match.group(1)
        source = next((s for s in console_sources if s.prog == prog), None)
        if source is None:
            continue
        tree = console_trees.get(source.parser)
        parser = console_parsers.get(source.parser)
        if tree is None or parser is None:
            continue
        if _nearby_waived(doc_lines, line_no):
            continue
        chain = match.group(2).split()
        flags = match.group(3).split()
        if chain and not _resolve_command_chain(tree, chain):
            violations.append(
                _doc006_violation(
                    doc_path,
                    line_no,
                    "cli invocation",
                    f"`{prog} {' '.join(chain)}` does not resolve to a known "
                    f"subcommand",
                )
            )
            continue
        if not flags:
            continue
        leaf = _leaf_parser(parser, chain)
        known_flags = set(getattr(leaf, "_option_string_actions", {}).keys())
        for flag in flags:
            if flag not in known_flags:
                violations.append(
                    _doc006_violation(
                        doc_path,
                        line_no,
                        "cli invocation",
                        f"`{flag}` is not a known option of `{prog} {' '.join(chain)}`",
                    )
                )
    return violations


# ---------------------------------------------------------------------------
# Kind 3: CONFIG REFERENCE ([section] / [section.key] against frob.toml)
# ---------------------------------------------------------------------------

_CONFIG_REF_RE = re.compile(r"^\[{1,2}([\w.-]+)\]{1,2}$")


def _load_frob_toml(root: Path) -> dict | None:
    """This project's own `frob.toml`, or `None` if absent/unreadable --
    fail-open, matching every other manifest reader in this package."""
    path = root / "frob.toml"
    if not path.exists():
        return None
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None


def _config_path_exists(data: dict, dotted: str) -> bool:
    """Whether `dotted` (`section.key`) resolves as a real path through
    `data` -- descends through nested dicts, and through the first element
    of a list-of-tables (`[[array]]` sections, e.g. `docblocks.commands`)."""
    node = data
    for part in dotted.split("."):
        if isinstance(node, list):
            node = node[0] if node else {}
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return True


def _config_violations(
    doc_path: str,
    doc_lines: list[str],
    tokens: list[tuple[int, str]],
    frob_toml: dict | None,
) -> list[Violation]:
    """Kind 3 (CONFIG REFERENCE): `` `[section]` ``/`` `[section.key]` ``
    checked against this project's own loaded `frob.toml` structure."""
    violations: list[Violation] = []
    if frob_toml is None:
        return violations
    for line_no, token in tokens:
        match = _CONFIG_REF_RE.match(token)
        if match is None:
            continue
        dotted = match.group(1)
        if _nearby_waived(doc_lines, line_no):
            continue
        if not _config_path_exists(frob_toml, dotted):
            violations.append(
                _doc006_violation(
                    doc_path,
                    line_no,
                    "config reference",
                    f"[{dotted}] is not a real frob.toml section/key",
                )
            )
    return violations


# ---------------------------------------------------------------------------
# Kind 4: CODE SYMBOL (dotted path against manifest-derived python namespaces)
# ---------------------------------------------------------------------------

_DOTTED_SYMBOL_RE = re.compile(r"^[A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*){2,}$")


def _symbol_violations(
    doc_path: str,
    doc_lines: list[str],
    tokens: list[tuple[int, str]],
    python_namespaces: frozenset[str],
    module_map: dict[str, str],
    symbol_names_by_path: dict[str, set[str]],
    root: Path,
) -> list[Violation]:
    """Kind 4 (CODE SYMBOL): a dotted `module.Class.method`-shaped token
    whose root namespace is one of this project's own (manifest-derived,
    `frob.gates._docblocks._project_namespaces`) resolved the same way
    DOC004's python `from X import Y` tier resolves a symbol.

    Deliberately conservative beyond one level (module + one trailing
    symbol): a token like `module.Class.attr` where `module` resolves and
    `Class` is a real top-level symbol there, but `attr` is a CLASS
    ATTRIBUTE (not a module-level name) is outside what this simple
    module-map resolver can prove-or-refute -- flagging it STALE would be
    exactly the false-positive class the ticket's own conservatism
    directive warns against ("only a pointer ... DEFINITIVELY resolvable-
    or-refutable is checked"), so it is silently skipped, same posture as
    an unrecognized shape. `module.__init__`/`module.__all__` (a doc's own
    convention for naming a package's boundary) count as resolved the
    moment `module` itself resolves -- neither is a real top-level symbol
    name, but both are legitimate ways to refer to the module itself."""
    violations: list[Violation] = []
    for line_no, token in tokens:
        if _DOTTED_SYMBOL_RE.match(token) is None:
            continue
        root_ns = token.split(".", 1)[0]
        if root_ns not in python_namespaces:
            continue
        if _nearby_waived(doc_lines, line_no):
            continue
        module, _, name = token.rpartition(".")
        if token in module_map:
            continue  # the whole dotted token is itself a real module
        file_path = module_map.get(module)
        if file_path is None:
            # the immediate module prefix does not resolve -- before
            # claiming STALE, check whether a SHORTER prefix resolves and
            # the next segment is a real top-level symbol there (a
            # `module.Class.attr`-shaped chain one level deeper than this
            # resolver can prove/refute): if so, silently skip rather than
            # false-flag a legitimate class-attribute reference.
            outer_module, _, maybe_class = module.rpartition(".")
            outer_file = module_map.get(outer_module)
            if outer_file is not None and maybe_class in symbol_names_by_path.get(
                outer_file, set()
            ):
                continue
            violations.append(
                _doc006_violation(
                    doc_path, line_no, "code symbol", f"{module!r} does not resolve"
                )
            )
            continue
        top_names = symbol_names_by_path.get(file_path, set())
        if (
            name in top_names
            or name in ("__init__", "__all__")
            or f"{module}.{name}" in module_map
            or _module_reexports(root, file_path, name)
        ):
            continue
        violations.append(
            _doc006_violation(
                doc_path,
                line_no,
                "code symbol",
                f"{token} does not resolve to a real symbol",
            )
        )
    return violations


# ---------------------------------------------------------------------------
# Recognized-shape hardening for the T-0940/T-0945 DRIFT002 confusion class:
# a `frob:tests` target with a SECOND `::` is definitively the wrong shape
# for this graph's `<file>::<dotted qualname>` convention (pytest's own
# `Class::method` collect-only separator, mistaken for the graph's `Class.
# method`), regardless of whether it happens to still resolve.
# ---------------------------------------------------------------------------

_DOUBLE_SEP_TESTS_TARGET_RE = re.compile(r"::[^:]*::")


def _origin_site(origin: str) -> tuple[str, int]:
    """Best-effort `(file, line)` split of an edge's `path:line` origin
    string -- a narrow local copy of `frob.gates.__init__._site_from_edge_
    origin` (that helper is private to the package `__init__` module,
    which imports THIS module, so importing back would cycle)."""
    file_part, sep, line_part = origin.rpartition(":")
    if sep and line_part.isdigit():
        return file_part, int(line_part)
    return origin, 0


def _tests_target_shape_violations(snapshot: GraphSnapshot) -> list[Violation]:
    """DOC006 over every `frob:tests` edge's TARGET string: a second `::`
    (pytest's `Class::method` collect-only separator) where this graph's
    convention wants a single `::` then a DOTTED `Class.method` qualname is
    a recognized wrong shape, flagged here directly instead of waiting for
    it to surface later as a generic DRIFT002 dangling-edge failure."""
    violations: list[Violation] = []
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TESTS:
            continue
        if _DOUBLE_SEP_TESTS_TARGET_RE.search(edge.target) is None:
            continue
        file, line = _origin_site(edge.origin)
        violations.append(
            _doc006_violation(
                file,
                line,
                "frob:tests target-form",
                f"{edge.target!r} uses pytest's `Class::method` collect-only "
                f"separator; this graph's own convention is a single `::` "
                f"then a DOTTED `Class.method` qualname",
            )
        )
    return violations


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _tracked_all_files(root: Path) -> frozenset[str]:
    """Every git-tracked file in `root`, repo-relative POSIX paths."""
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.warning("doc006: git ls-files failed")
        return frozenset()
    return frozenset(line for line in spawned.danger_ok.stdout.splitlines() if line)


# frob:doc docs/modules/gates.md#doc006-doc-pointer-resolution-gate-t-0437
# frob:tests tests/test_docptr_gate.py::TestDoc006FilePath.test_missing_path_flagged
# frob:tests tests/test_docptr_gate.py::TestDoc006FilePath.test_real_path_passes
# frob:tests tests/test_docptr_gate.py::TestDoc006FilePath.\
# test_unrecognized_prose_not_flagged
# frob:tests tests/test_docptr_gate.py::TestDoc006DocAnchor.test_missing_anchor_flagged
# frob:tests tests/test_docptr_gate.py::TestDoc006DocAnchor.test_real_anchor_passes
# frob:tests tests/test_docptr_gate.py::TestDoc006Cli.\
# test_nonexistent_subcommand_flagged
# frob:tests tests/test_docptr_gate.py::TestDoc006Cli.test_nonexistent_flag_flagged
# frob:tests tests/test_docptr_gate.py::TestDoc006Cli.test_real_command_passes
# frob:tests tests/test_docptr_gate.py::TestDoc006Config.test_bogus_section_flagged
# frob:tests tests/test_docptr_gate.py::TestDoc006Config.test_real_section_passes
# frob:tests tests/test_docptr_gate.py::TestDoc006Symbol.test_nonexistent_symbol_flagged
# frob:tests tests/test_docptr_gate.py::TestDoc006Symbol.test_real_symbol_passes
# frob:tests tests/test_docptr_gate.py::TestDoc006Symbol.\
# test_module_dunder_init_and_all_pass
# frob:tests tests/test_docptr_gate.py::TestDoc006Symbol.\
# test_class_attribute_chain_not_flagged
# frob:tests tests/test_docptr_gate.py::TestDoc006FilePath.\
# test_dot_frob_runtime_path_not_flagged
# frob:tests tests/test_docptr_gate.py::TestDoc006Waive.test_waive_suppresses
# frob:tests tests/test_docptr_gate.py::TestDoc006TestsTargetShape.\
# test_double_separator_target_flagged
# frob:tests tests/test_docptr_gate.py::TestDoc006TestsTargetShape.\
# test_single_separator_target_not_flagged
def doc006_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """DOC006: doc-pointer resolution over a closed set of recognized,
    mechanically resolvable pointer shapes (see this module's docstring)
    -- a pointer of a recognized shape whose target does not exist is
    flagged; an unrecognized/ambiguous token never is."""
    root = Path(root)
    tracked = _tracked_all_files(root)
    namespaces = _project_namespaces(root)
    module_map = _python_module_map(root)
    symbol_names_by_path = _python_symbol_names_by_path(snapshot)
    console_sources = _console_command_sources(root)
    console_trees = _console_trees(root, console_sources)
    console_parsers = _console_parsers(console_sources)
    frob_toml = _load_frob_toml(root)
    anchor_cache: dict[str, set[str] | None] = {}

    violations: list[Violation] = list(_tests_target_shape_violations(snapshot))
    for doc_path in _tracked_md_files(root):
        text = _read_md(root, doc_path)
        if text is None:
            continue
        doc_lines = text.splitlines()
        prose = _blank_fenced_blocks(text)
        tokens = _prose_tokens(prose)
        violations.extend(
            _file_and_anchor_violations(
                doc_path, doc_lines, tokens, tracked, anchor_cache, root
            )
        )
        violations.extend(
            _cli_violations(
                doc_path,
                doc_lines,
                tokens,
                console_sources,
                console_trees,
                console_parsers,
            )
        )
        violations.extend(_config_violations(doc_path, doc_lines, tokens, frob_toml))
        violations.extend(
            _symbol_violations(
                doc_path,
                doc_lines,
                tokens,
                namespaces.python,
                module_map,
                symbol_names_by_path,
                root,
            )
        )
    _log.info("doc006: %d violation(s) across tracked .md docs", len(violations))
    return tuple(violations)


def _console_parsers(console_sources) -> dict[str, object]:
    """`{source.parser: live top-level argparse.ArgumentParser}` -- the
    actual parser OBJECTS (not just the subcommand-shape dict `_console_
    trees` builds), needed here so `_leaf_parser` can walk to a
    subcommand's own `--flag` registry."""
    from frob.gates._docblocks import _load_parser_factory

    parsers: dict[str, object] = {}
    for source in console_sources:
        factory = _load_parser_factory(source.parser)
        if factory is None:
            continue
        try:
            parsers[source.parser] = factory()
        except Exception as exc:  # noqa: BLE001 -- a broken factory never fails the gate
            _log.warning("doc006: parser factory %r raised: %s", source.parser, exc)
    return parsers

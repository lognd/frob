"""REF001/REF002/REF003: anti-orphan gate over every git-tracked file
(docs/modules/gates.md#anti-orphan-file-reference-gate, T-0396).

Motivating case: `docs/design/registry/*.yaml` manifests were read by ZERO
files -- a silently dead (or silently unenforced) artifact that no existing
gate caught, because every other gate reasons about SOURCE symbols (`frob.
graph`'s import/DSL edges), never about a bare tracked file's existence
being justified at all. This module closes that gap generically, over
EVERY git-tracked file regardless of type (source, docs, config, data,
assets) -- not just the languages `frob.lang` knows how to parse.

Detection is three-layered (T-1665 adds the first):

0. RESOLVED IMPORT (`.py` targets only, `frob.graph.imports.build_import_
   graph`): a real AST-resolved `import`/`from ... import` edge, computed
   over every tracked `.py` file once per `ref_gate` run. This REPLACES
   the old text-regex Python-import parsing and, more importantly, the
   bare-stem "quoted string / imported name matches a `.py` file's
   extensionless stem" shortcut the AUTO-SCAN layer used to rely on for
   Python targets (`_tokens_reach`'s old docstring called this out as the
   riskiest heuristic in the module). That shortcut produced exactly the
   false COMFORT T-1665 was filed to remove: a dynamic dispatch table's
   bare quoted module-name string, or an `importlib.import_module(...)`
   call, LOOKED like a reference (the string equals the target's stem)
   without the substrate actually knowing whether that string is ever
   evaluated to reach this specific file. A target reachable only through
   one of THOSE shapes now reports `Severity.UNRESOLVED`, T-1664's third
   outcome, instead of a silent false pass or a false REF001 (see
   `_unresolved_python_target` below) -- honest "cannot determine",
   never "definitely referenced" on a guess.
1. AUTO-SCAN (cross-type, language-agnostic, all NON-.py-import cases):
   file X counts as referenced by file Y if Y names X (full repo-relative
   path or bare basename) in a real reference SYNTACTIC position -- a
   markdown link, a quoted string literal, a backtick-wrapped
   MULTI-COMPONENT path mention (contains a `/` -- e.g. `` `docs/rework.
   md` ``, the repo's own doc convention; T-0467), a `frob:doc`/
   `frob:describes`/`frob:used-by`/`frob:tests` directive target, or a
   non-Python `require`/`include`/`use` statement -- NEVER a bare prose/
   table mention or a backtick-wrapped bare identifier (round-2,
   reviewer-caught: a naive whole-text substring match produced an 86%
   false-positive rate, both false ORPHANS -- import lists only resolving
   their module prefix, never the imported names -- and false PASSES -- a
   doc's prose mention of a filename counted as a reference). This layer
   is deliberately NARROW and stays that way for what layer 0's Python
   substrate cannot see at all (T-1665: "non-code targets have no import
   edges, and the substrate is Python-only, so a pure-import REF001 would
   go blind on every other language") -- a doc, a config file, a data
   file, or a non-Python source file.
2. DECLARED (`frob:used-by <consumer>`): a file can name its own consumer
   explicitly, for references neither layer above can structurally see
   (a path built at runtime, a glob loaded by a directory base). Every
   declaration is VERIFIED, not trusted: the named consumer must be a
   tracked file AND must itself reach the declaring file (same combined
   layer-0/layer-1 check, in reverse) -- a declaration naming a
   nonexistent or non-reaching consumer is REF003, not a silent pass.
   This is the anti-lie half of the ticket: a `frob:used-by` cannot
   manufacture a reference that isn't real.

A `<name>.pyi` type stub sitting beside a `pyproject.toml` whose
`[tool.maturin] module-name` matches the stub's stem is the typed
interface of a compiled native extension (`strata_core.pyi` for the
`strata_core` extension built from `strata-core/`; `frob_core.pyi` for
`frob_core` built from `frob-core/`). That stub<->crate relationship is a
REAL, declarable dependency edge -- T-0449 user correction: exempting it
outright (like the test-filename exemption below) would hide exactly the
kind of unaccounted relationship this gate exists to surface. Instead
`_native_stub_pairs` resolves the pairing structurally, out-of-band from
the text-token scan (a `.pyi` sidecar and its crate's build manifest never
literally NAME each other in any of `_candidate_tokens`'s shapes), and the
manifest is added to the stub's inbound set as a genuine reference --
so a linked stub is LINKED (REF001 does not fire because it has a real
referrer), never silently skipped. A `.pyi` with no adjacent
`module-name`-matching manifest gets no such edge and remains fully
subject to REF001/REF002 like any other file.

A file whose OWN NAME matches a test-collection convention (`test_*.py`,
`*_test.py`, `*.test.ts`, ...; see `_is_collectible_test_filename`) is
exempt from REF001/REF002 entirely: it is referenced by the test RUNNER
via naming convention, which the auto-scan structurally cannot see
(round-2, reviewer-caught: 52% of the original false REF001s were exactly
this). Deliberately narrower than merely "sits under `tests/`"
(`frob.excludes.is_test_file`'s directory-membership rule) -- a fixture/
helper/data file that lives under `tests/` but is not itself a test the
runner discovers is exactly the kind of orphan this gate must still catch
(round-3, reviewer-caught: the broader rule silently hid a genuine
orphan).

Tiers (all WARN severity -- this is an advisory-but-tracked family per the
user, same posture as PERF/FUZZ, never a hard build failure):
- 0 inbound (auto + verified-declared, deduped by consumer file) -> REF001
- exactly 1 -> REF002 (single point of anchor, fragile)
- 2+ -> pass, no violation

`[[refs.entrypoint]]` in frob.toml exempts genuinely-external-facing files
(README.md, LICENSE, ...) from REF001/REF002 -- each entry MUST carry a
`reason`; a malformed entry (missing path/reason) is skipped, not treated
as a wildcard mute.

A `.md` file's OWN text can also carry an inline `frob:waive REF001
reason="..."` or `frob:waive REF002 reason="..."` directive, text-scanned
directly the same way `_docblocks.py` honors `frob:waive DOC004` on a doc
(T-0466) -- `frob.graph`'s edge/waiver model has no edge to attach a waiver
to on a bare tracked `.md` file, so without this a REF001/REF002 finding on
a doc was structurally unwaivable. See `_md_waived_rules`.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path, PurePosixPath
from typing import NamedTuple

from frob.excludes import is_excluded, load_exclude_globs
from frob.gates._models import Severity, Violation
from frob.gates._tracked_files import tracked_files as _shared_tracked_files
from frob.graph.imports import ImportGraph, UnresolvedImport, build_import_graph
from frob.logging import get_logger

_log = get_logger(__name__)

# frob:ticket T-1665
_PY_SUFFIX = ".py"

__all__ = ["ref_gate"]

# Directive lines only, never mid-sentence prose: `frob:used-by <target>`
# must be the first thing after an optional comment leader (`#`, `//`,
# `/*`, `*`, `<!--`) is stripped, same posture `frob.graph.dsl`'s
# `_LINE_RE` takes for every other `frob:<verb>` directive -- a bare
# substring match on "frob:used-by" would also fire on prose that merely
# MENTIONS the directive (e.g. this module's own docstring, a ticket body
# describing the feature), which is exactly the false-positive T-0396's
# own dogfooding run caught.
_COMMENT_PREFIXES = ("<!--", "#", "//", "/*", "*")


def _strip_comment_prefix(line: str) -> str:
    """`line` with leading whitespace and one recognized comment leader
    removed, or just whitespace-stripped if no leader is present."""
    stripped = line.strip()
    for prefix in _COMMENT_PREFIXES:
        if stripped.startswith(prefix):
            return stripped[len(prefix) :].strip()
    return stripped


# Binary/generated-ish extensions the text scan cannot usefully read; a
# reference TO one of these can still be detected (its path/basename is
# text in the referencing file), but scanning its own bytes as text would
# be noise at best and a crash at worst.
_BINARY_EXTS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".ico",
        ".pdf",
        ".woff",
        ".woff2",
        ".ttf",
        ".zip",
        ".whl",
        ".so",
        ".dylib",
        ".pyc",
    }
)


# T-0396 round-3 (reviewer-caught false NEGATIVE): `frob.excludes.is_test_file`
# exempts ANY path with a `tests/` directory component, not just files that
# are themselves tests -- correct for its other callers (the arch gate,
# T-0359, wants "skip everything under tests/"), but wrong here: a dead
# fixture/helper/data file that merely LIVES under `tests/` (e.g.
# `tests/fixtures/orphan_helper.py`, no `test_*` functions, imported
# nowhere) is exactly the kind of orphan this gate exists to catch, and
# the broad rule silently hid it. This gate needs the NARROWER claim --
# "this file's own NAME is what the test runner discovers" -- never "this
# file merely sits in a tests/ directory". Deliberately NOT reusing
# `is_test_file` (playbook: do not weaken/duplicate a shared predicate
# for one caller's narrower need); this is the file-name half of pytest's
# own collection convention (`test_*.py`/`*_test.py`) plus the TS/Rust
# analogs, kept local to this gate.
def _is_collectible_test_filename(rel_path: str) -> bool:
    """True if `rel_path`'s OWN basename matches a test-runner discovery
    convention (`test_*.py`, `*_test.py`, `*.test.ts`, `*_test.rs`, ...)
    -- never true merely because the path sits under a `tests/`
    directory, which is what made `frob.excludes.is_test_file` too broad
    for this gate's purpose (a fixture/helper file under `tests/` with no
    test-shaped name must still be eligible for REF001)."""
    pure = PurePosixPath(rel_path)
    name = pure.stem
    return (
        name.startswith("test_")
        or name.endswith("_test")
        or ".test" in pure.name
        or "_test." in pure.name
    )


def _load_allowlist(root: Path) -> dict[str, str]:
    """`[[refs.entrypoint]]` from frob.toml: path -> reason.

    A malformed entry (missing `path` or `reason`, wrong type) is skipped
    and logged, not treated as covering every file -- the allowlist is a
    small explicit per-file list, never a blanket mute."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return {}
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("ref_gate: frob.toml unreadable: %s", exc)
        return {}
    entries = doc.get("refs", {}).get("entrypoint", [])
    allow: dict[str, str] = {}
    if not isinstance(entries, list):
        return allow
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        reason = entry.get("reason")
        if isinstance(path, str) and isinstance(reason, str) and reason.strip():
            allow[path] = reason
        else:
            _log.warning(
                "ref_gate: malformed [[refs.entrypoint]] entry skipped: %r", entry
            )
    return allow


# frob:ticket T-0449
def _load_maturin_module_name(root: Path, pyproject_rel: str) -> str | None:
    """The `[tool.maturin] module-name` a tracked `pyproject.toml` at
    `pyproject_rel` declares, or `None` if the file is unreadable/
    malformed or declares no maturin module -- the manifest-declared name
    a sidecar `.pyi` stub's stem must match to be recognized as that
    crate's typed interface (T-0449)."""
    try:
        with (root / pyproject_rel).open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.debug(
            "ref_gate: %s unreadable for maturin module-name: %s", pyproject_rel, exc
        )
        return None
    name = doc.get("tool", {}).get("maturin", {}).get("module-name")
    return name if isinstance(name, str) and name else None


# frob:ticket T-0449
# frob:tests tests/test_refs_gate.py::TestNativeStubLinking.test_linked_pyi_beside_matching_manifest_does_not_fire_ref001  # noqa: E501
# frob:tests tests/test_refs_gate.py::TestNativeStubLinking.test_unlinked_pyi_with_no_adjacent_module_still_fires_ref001  # noqa: E501
def _native_stub_pairs(tracked: frozenset[str], root: Path) -> dict[str, str]:
    """Every tracked `.pyi` stub paired with the tracked `pyproject.toml`
    that builds the native extension it types: a manifest sitting in the
    SAME directory as the stub, whose `[tool.maturin] module-name` equals
    the stub's own stem (`frob_core.pyi` <-> `frob-core/pyproject.toml`
    declaring `module-name = "frob_core"`). Maps stub rel_path -> manifest
    rel_path -- a REAL structural edge (resolved from the build manifest,
    not a text-token match, since a `.pyi` sidecar and its crate's
    Cargo/maturin build never literally name each other), used by
    `ref_gate` to count the stub as genuinely LINKED rather than exempted
    (T-0449). A `.pyi` with no such sibling manifest, or whose stem does
    not match any manifest's declared module name, is absent from the
    returned mapping and stays fully subject to REF001/REF002."""
    manifests = tuple(p for p in tracked if PurePosixPath(p).name == "pyproject.toml")
    pairs: dict[str, str] = {}
    for stub in tracked:
        if not stub.endswith(".pyi"):
            continue
        stub_path = PurePosixPath(stub)
        for manifest in manifests:
            if PurePosixPath(manifest).parent != stub_path.parent:
                continue
            if _load_maturin_module_name(root, manifest) == stub_path.stem:
                pairs[stub] = manifest
                break
    return pairs


def _read_text(root: Path, rel_path: str) -> str | None:
    """Best-effort file text, `None` for binary extensions or unreadable
    files -- a file this gate cannot read as text still exists as a
    reference TARGET (others can name it), it just cannot itself scan
    outward for what it references."""
    if PurePosixPath(rel_path).suffix in _BINARY_EXTS:
        return None
    try:
        return (root / rel_path).read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeDecodeError) as exc:
        _log.debug("ref_gate: %s unreadable as text: %s", rel_path, exc)
        return None


# The ticket's own reference shapes -- import/require/include/use
# statements, config/string path literals, markdown/doc LINKS, frob:doc
# directive targets -- all collapse to "a path/basename token appearing in
# one of these SYNTACTIC positions", never a bare prose mention. This is
# the load-bearing distinction T-0396's own dogfooding run needed: a
# README table cell or a ticket-body sentence that merely NAMES a file
# (`` `patterns.yaml` ``, "the docs/design/registry/*.yaml manifests") is
# not a reference in ANY of the ticket's listed shapes, and counting it as
# one silently defeats the gate's entire purpose (it produced a false
# 2+-refs PASS for the exact registry-yaml orphans this gate exists to
# catch -- see this module's own Done report evidence). Restricting to
# these syntactic positions is what makes "prose about a file" and "a real
# reference to a file" distinguishable at all.
_MD_LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
# T-0467: the repo's own doc convention wraps a path mention in backticks
# (`` `docs/rework.md` ``) rather than quotes or a markdown link -- neither
# `_QUOTED_RE` (only "/' quotes) nor `_MD_LINK_RE` (only `[text](target)`)
# ever tokenizes that shape, so ~12 docs referenced ONLY via a backtick
# mention read as false-positive REF001 orphans despite being genuinely
# linked. Restricted to backtick content that itself contains a `/` (a
# real MULTI-COMPONENT path, e.g. `docs/rework.md`) -- deliberately NOT
# "any backtick with a recognized extension", which would also swallow a
# bare-basename prose mention like `` `manifest.yaml` `` in a sentence
# that merely DESCRIBES the file ("the `manifest.yaml` file lists things,
# but nothing loads it") without it being a real reference -- exactly the
# false PASS `TestReferenceDetection.
# test_bare_prose_mention_does_not_count_as_a_reference` guards against.
# A directory component is what distinguishes "this text names a path" (a
# real reference) from "this text mentions a bare filename" (still prose).
_BACKTICK_RE = re.compile(r"`([^`\n]{2,300})`")
# T-0396 round-2 fix-verification (self-caught while sampling remaining
# findings for genuineness): the original `["\']([^"\']{2,300})["\']` opens
# on EITHER quote character and closes on EITHER quote character -- an
# apostrophe inside prose ("argv's", "doesn't") pairs with a distant,
# mismatched `"` and swallows everything between them into one giant
# bogus token, hiding a real short quoted path (e.g. `"_harness.py"`)
# inside it instead of extracting it as its own token. Requires the SAME
# quote character to close (backreference) and forbids newlines inside
# the match, so a stray apostrophe/docstring quote can no longer bridge
# an entire file into one token.
_QUOTED_RE = re.compile(r"(?P<q>[\"'])(?P<tok>(?:(?!(?P=q))[^\n]){2,300})(?P=q)")
# require/include/use (TS/Rust/C/etc): still a single-target regex --
# those grammars' import-lists don't share Python's `from X import a, b,
# c` multi-name shape, so a simple single-capture match is sufficient.
_SINGLE_IMPORT_RE = re.compile(
    r'\b(?:require|include|use)\b\s*[(]?\s*["\']?([./\w-]+\.\w+|(?:[./\w-]+/)+[\w-]+)'
)
# "tests" included (fix-verification round, self-caught while sampling
# remaining findings): `frob:tests <path>::<qualname>` names the exact
# file its test binds to -- a real reference, same footing as `frob:doc`.
_DIRECTIVE_RE = re.compile(r"\bfrob:(?:doc|describes|used-by|tests)\s+(\S+)")

# T-0466: a `.md`-embedded `frob:waive REF001/REF002 reason="..."` produces
# NO graph edge -- `frob.graph`'s edge/waiver model only attaches waivers to
# SOURCE symbols, never to a bare tracked `.md` file -- so REF001/REF002
# findings on a `.md` file were structurally unwaivable. `_docblocks.py`
# (DOC004) already solved the identical problem by text-scanning the raw
# `.md` bytes for the directive directly, never routing it through
# `frob.graph` at all; this gate adopts the SAME posture rather than
# inventing a second waiver mechanism (playbook: no duplication). Unlike
# DOC004's "nearby window" scan (a per-anchor waiver), REF001/REF002 are
# whole-FILE findings, so the directive is honored anywhere in the file's
# text, not tied to a line window.
_WAIVE_REF_RE = re.compile(r'frob:waive\s+(REF00[12])\s+reason="([^"]*)"')


def _md_waived_rules(rel_path: str, text: str | None) -> frozenset[str]:
    """Every `REF001`/`REF002` rule id waived by an inline `frob:waive
    REF00[12] reason="..."` directive found anywhere in `text`, restricted
    to `.md` files (T-0466) -- the same text-scan posture `_docblocks.py`
    uses for `DOC004` on `.md` docs, since `frob.graph` has no edge to
    attach a waiver to on a bare doc file."""
    if text is None or not rel_path.endswith(".md"):
        return frozenset()
    return frozenset(match.group(1) for match in _WAIVE_REF_RE.finditer(text))


# T-1665: Python's own `import`/`from ... import` parsing used to live
# here as a text regex (`_FROM_IMPORT_RE`/`_PLAIN_IMPORT_RE`/
# `_split_import_names`/`_python_import_targets`, T-0396 round-2's fix for
# the multi-name-import gap). Removed in favor of `frob.graph.imports.
# build_import_graph`'s real AST-based resolver (`_python_reach`, below)
# -- a grammar-correct parser is strictly more precise than a regex scan
# for this one language (it finds every import regardless of nesting
# inside `if`/`try`/`TYPE_CHECKING` guards, and never mistakes a
# look-alike string/comment for an import) and, more importantly, it
# NEVER produces a bare stem/dotted-suffix guess the way the old regex
# tokens + `_tokens_reach`'s Python-only stem-matching branch used to --
# see this module's own docstring, layer 0, for why that guess was the
# false-comfort case T-1665 was filed to remove.


def _candidate_tokens(text: str) -> tuple[str, ...]:
    """Every path-shaped token `text` names in a real reference position
    (markdown link target, quoted string literal, a require/include/use
    target, or a `frob:doc`/`frob:describes`/`frob:used-by` directive
    target) -- the universe `_tokens_reach` matches against, deliberately
    excluding plain prose/table/backtick mentions. T-1665: Python's own
    import statements are no longer tokenized here at all -- see
    `_python_reach`, the real AST-resolved replacement."""
    tokens: list[str] = []
    for match in _QUOTED_RE.finditer(text):
        tokens.append(match.group("tok").rstrip("`,.)\"'>"))
    for match in _BACKTICK_RE.finditer(text):
        candidate = match.group(1).strip()
        if "/" in candidate:
            tokens.append(candidate.rstrip(",.)\"'>"))
    for pattern in (_MD_LINK_RE, _SINGLE_IMPORT_RE):
        for match in pattern.finditer(text):
            tokens.append(match.group(1).rstrip("`,.)\"'>"))
    for match in _DIRECTIVE_RE.finditer(text):
        # `frob:tests <path>::<qualname>` and `frob:doc <path>#anchor` both
        # name a SYMBOL/anchor, not a bare path -- split at `::` and `#` so
        # the token is the path alone, matchable against `target_path`/
        # basename the same as every other token (self-caught while
        # sampling remaining findings: `frob:doc docs/x.md#anchor` was
        # producing a token with the `#anchor` suffix still attached,
        # never matching the bare doc path and hiding a real reference).
        raw = match.group(1).split("::", 1)[0].split("#", 1)[0]
        tokens.append(raw.rstrip("`,.)\"'>"))
    return tuple(tokens)


def _tokens_reach(tokens: frozenset[str], target_path: str) -> bool:
    """True if `tokens` (a file's precomputed `_candidate_tokens` set)
    names `target_path` by full repo-relative path or bare basename
    (exact, or as the final `/`-segment of a longer token).

    T-1665: the old THIRD branch here -- for `.py` targets only, also
    matching the file's extensionless STEM as a bare token or the final
    DOTTED component of a longer one (`frob.arch._cpp` -> stem `_cpp`) --
    is REMOVED. That branch was how a dispatch table's bare quoted
    module-name string (`"ack_runner"`) or an `importlib.import_module`
    call's argument used to "resolve" to `ack_runner.py`: the string
    happened to equal the target's stem, with no proof it is ever
    actually evaluated to reach that specific file. `frob.graph.imports.
    build_import_graph` (`_python_reach`, this module) now resolves real
    Python imports precisely via the language's own AST; a `.py` target
    reachable only through a stem-shaped guess like this now reports
    `Severity.UNRESOLVED` instead (see `_unresolved_python_target`) --
    T-1665's own point: false comfort from a guess is worse than an
    honest "cannot determine". Non-`.py` targets were never covered by
    the removed branch (T-0396's own fix-verification round already
    required a full basename+extension for those, precisely to avoid a
    quoted English word colliding with a data file's bare stem, e.g.
    `g.family == "compliance"` vs. `compliance.yaml`) -- unaffected."""
    basename = PurePosixPath(target_path).name
    if target_path in tokens or basename in tokens:
        return True
    return any(
        token.endswith("/" + basename) or token.endswith("/" + target_path)
        for token in tokens
    )


class _ReachIndex(NamedTuple):
    """Reverse indexes over every tracked file's `_candidate_tokens` (built
    once by `_build_reach_index`, consumed by `_reaching_files`) so
    `_auto_inbound` answers "which files reach this target" via O(1)-ish
    lookups instead of an O(files) rescan per candidate (T-0831: 13.5s
    CPU at ~994 tracked files). Fields mirror `_tokens_reach`'s match
    shapes -- see `_reaching_files` -- so results stay byte-identical to
    the old pairwise scan. T-1665 drops the `dot_suffix` field (the
    `.py`-only bare-stem index) along with `_tokens_reach`'s matching
    branch it backed -- see that function's docstring."""

    exact: dict[str, frozenset[str]]
    slash_suffix: dict[str, frozenset[str]]


def _build_reach_index(tokens_by_file: dict[str, frozenset[str]]) -> _ReachIndex:
    """Build `_ReachIndex` in one O(total tokens) pass: `exact` keys every
    token verbatim; `slash_suffix` keys each token's final `/`-segment
    (`token.endswith("/" + basename)`)."""
    exact: dict[str, set[str]] = {}
    slash_suffix: dict[str, set[str]] = {}
    for owner, tokens in tokens_by_file.items():
        for token in tokens:
            exact.setdefault(token, set()).add(owner)
            if "/" in token:
                slash_suffix.setdefault(token.rsplit("/", 1)[1], set()).add(owner)
    return _ReachIndex(
        exact={key: frozenset(value) for key, value in exact.items()},
        slash_suffix={key: frozenset(value) for key, value in slash_suffix.items()},
    )


def _reaching_files(index: _ReachIndex, target_path: str) -> frozenset[str]:
    """Every file whose token set reaches `target_path`: exact match on
    path/basename, or a `slash_suffix` hit on the basename."""
    basename = PurePosixPath(target_path).name
    return frozenset(
        index.exact.get(target_path, frozenset())
        | index.exact.get(basename, frozenset())
        | index.slash_suffix.get(basename, frozenset())
    )


def _auto_inbound(candidate: str, index: _ReachIndex) -> set[str]:
    """Every OTHER tracked file whose token set reaches `candidate`, from
    the precomputed `_ReachIndex` (T-0831)."""
    return set(_reaching_files(index, candidate)) - {candidate}


# frob:ticket T-1665
def _build_python_reverse_edges(import_graph: ImportGraph) -> dict[str, frozenset[str]]:
    """`target .py path -> frozenset(importer paths)`, the REVERSE of
    `ImportGraph.edges` (`importer -> imported targets`) -- the direction
    `ref_gate` needs (given a target, who imports it), built once per
    `ref_gate` run rather than re-scanning `import_graph.edges` per
    candidate file."""
    reverse: dict[str, set[str]] = {}
    for importer, targets in import_graph.edges.items():
        for target in targets:
            reverse.setdefault(target, set()).add(importer)
    return {target: frozenset(importers) for target, importers in reverse.items()}


# frob:ticket T-1665
def _python_resolved_inbound(
    candidate: str, reverse_edges: dict[str, frozenset[str]]
) -> frozenset[str]:
    """Every tracked `.py` file that RESOLVED-imports `candidate`, per
    `frob.graph.imports.build_import_graph`'s real AST-based resolver --
    T-1665's replacement for the old bare-stem text-token guess (see
    `_tokens_reach`'s docstring). Empty for a non-`.py` candidate (the
    substrate's own disclosed Python-only v1 scope) or one nothing
    resolves an import to."""
    return reverse_edges.get(candidate, frozenset())


# frob:ticket T-1665
def _unresolved_python_target(
    candidate: str, unresolved: tuple[UnresolvedImport, ...]
) -> bool:
    """T-1664: whether `candidate` (a `.py` file with zero resolved-import
    and zero auto-scan/declared inbound references) should report
    `Severity.UNRESOLVED` rather than a flat REF001 -- true if ANY
    `UnresolvedImport` in the whole-repo import graph is a `"dynamic-
    import"` or `"relative-import-above-root"` case whose raw `module`
    text plausibly names `candidate` (a best-effort substring match on
    `candidate`'s own dotted module name and bare stem against the
    unresolved call's unparsed source text, e.g. `importlib.import_module
    (f"app.{name}")` against target `app/ack_runner.py`'s stem
    `ack_runner` would NOT match -- string interpolation defeats even
    this best-effort check, correctly staying UNRESOLVED-eligible only
    for the literal-substring cases this heuristic can actually see, not
    a claim to resolve every dynamic shape). Disclosed as a heuristic,
    not a proof: this can both under- and over-attribute a given dynamic
    call to a candidate whose stem happens to collide with unrelated
    text -- deliberately still preferred over BOTH silently passing
    (treating a real orphan as referenced) and silently firing REF001
    (claiming certainty this substrate does not have), matching T-1664's
    own posture that `UNRESOLVED` is for exactly this "cannot determine"
    shape. `"parse-error"`/`"unsupported-language"` reasons are excluded
    here -- those are about the IMPORTER'S own file being unreadable, not
    about a specific unresolved TARGET name, so they carry no target-name
    text to match against at all."""
    if not candidate.endswith(_PY_SUFFIX):
        return False
    dotted = candidate[: -len(_PY_SUFFIX)].replace("/", ".")
    if dotted.endswith(".__init__"):
        dotted = dotted[: -len(".__init__")]
    stem = PurePosixPath(candidate).stem
    for item in unresolved:
        if item.reason not in ("dynamic-import", "relative-import-above-root"):
            continue
        if not item.module:
            continue
        if dotted and dotted in item.module:
            return True
        if stem and stem in item.module:
            return True
    return False


def _directive_target(line: str) -> str | None:
    """The `frob:used-by <target>` target on `line`, or `None` if `line`
    (after stripping its comment leader) is not that directive at all --
    the line-start requirement `_strip_comment_prefix` enforces is what
    keeps prose mentions of "frob:used-by" from being misread as a real
    directive."""
    stripped = _strip_comment_prefix(line)
    if not stripped.startswith("frob:used-by"):
        return None
    rest = stripped[len("frob:used-by") :].strip()
    if not rest:
        return None
    token = rest.split(maxsplit=1)[0].rstrip("`,.)\"'>-")
    if not token:
        return None
    return token.split("::", 1)[0]


def _declared_consumers(rel_path: str, text: str) -> tuple[str, ...]:
    """Every `frob:used-by <target>` directive target found in `rel_path`'s
    own text, `::`-qualname suffixes stripped down to the bare path
    (`frob:used-by src/x.py::Foo` declares `src/x.py` as the consumer)."""
    targets = []
    for line in text.splitlines():
        target = _directive_target(line)
        if target is not None:
            targets.append(target)
    return tuple(targets)


def _declared_line(text: str, target: str) -> int:
    """1-based line number of the first `frob:used-by <target>` directive
    in `text`, for the dangling-declaration violation site (falls back to
    1 if not found -- should not happen given the caller only asks for
    targets it just extracted from this same text)."""
    for index, line in enumerate(text.splitlines(), start=1):
        if _directive_target(line) == target:
            return index
    return 1


# frob:enforces CHK-GATE-REF001
# frob:enforces CHK-GATE-REF002
# frob:ticket T-1665
def _ref001_or_002(
    rel_path: str, inbound: set[str], *, unresolved: bool
) -> Violation | None:
    """The tier violation for `rel_path` given its deduped inbound set, or
    `None` if it clears the 2+ pass bar. T-1665: `unresolved=True` (only
    possible when `inbound` is empty -- see `_unresolved_python_target`)
    reports `Severity.UNRESOLVED` instead of REF001's `Severity.WARN` --
    a `.py` target reachable only through a dynamic import/dispatch shape
    this substrate cannot resolve is an honest "cannot determine", never
    a claimed-dead REF001 finding."""
    count = len(inbound)
    if count == 0:
        if unresolved:
            return Violation(
                rule="REF001",
                severity=Severity.UNRESOLVED,
                file=rel_path,
                line=0,
                message=(
                    f"REF001: {rel_path} has no RESOLVED inbound reference, "
                    f"but at least one dynamic import/dispatch call "
                    f"elsewhere in the repo plausibly names it -- cannot "
                    f"determine whether it is genuinely dead or reached "
                    f"only dynamically; verify by hand, or add a "
                    f'`frob:used-by <consumer>` declaration once you know '
                    f"which caller reaches it"
                ),
            )
        return Violation(
            rule="REF001",
            severity=Severity.WARN,
            file=rel_path,
            line=0,
            message=(
                f"REF001: {rel_path} has no inbound references from any other "
                f"tracked file (checked path/basename mentions and "
                f"`frob:used-by` declarations) -- likely dead or silently "
                f"unenforced; wire it into a consumer, add a `frob:used-by "
                f"<consumer>` declaration, add it to [[refs.entrypoint]] in "
                f"frob.toml with a reason if it is a genuine entry point, or "
                f'`frob:waive REF001 reason="..."` if the gap is intentional'
            ),
        )
    if count == 1:
        (only,) = inbound
        return Violation(
            rule="REF002",
            severity=Severity.WARN,
            file=rel_path,
            line=0,
            message=(
                f"REF002: {rel_path} has exactly one inbound reference "
                f"({only}) -- a single point of anchor is fragile; add a "
                f"second consumer/declaration or "
                f'`frob:waive REF002 reason="..."` if one anchor is '
                f"intentional"
            ),
        )
    return None


# frob:enforces CHK-GATE-REF003
# frob:ticket T-1665
def _consumer_reaches(
    consumer: str,
    target: str,
    tokens_by_file: dict[str, frozenset[str]],
    python_reverse_edges: dict[str, frozenset[str]],
) -> bool:
    """True if `consumer` reaches `target` via EITHER the narrowed
    auto-scan text channel OR a resolved Python import (T-1665) -- the
    combined "does this claimed consumer actually consume it" check both
    `_dangling_declarations` (REF003) and `_ref_gate_file_violations`'s
    own declared-consumer verification share, so a `frob:used-by`
    declaration can be verified by a real import edge, not just a text
    mention."""
    consumer_tokens = tokens_by_file.get(consumer)
    if consumer_tokens is not None and _tokens_reach(consumer_tokens, target):
        return True
    return consumer in _python_resolved_inbound(target, python_reverse_edges)


def _dangling_declarations(
    rel_path: str,
    text: str,
    tracked: frozenset[str],
    tokens_by_file: dict[str, frozenset[str]],
    python_reverse_edges: dict[str, frozenset[str]],
) -> list[Violation]:
    """REF003 for every `frob:used-by` target on `rel_path` that does not
    resolve to a real, reaching consumer -- the anti-lie check: a
    declaration is a claim, and this is where the claim gets verified."""
    violations: list[Violation] = []
    for target in _declared_consumers(rel_path, text):
        valid = target in tracked and _consumer_reaches(
            target, rel_path, tokens_by_file, python_reverse_edges
        )
        if valid:
            continue
        line = _declared_line(text, target)
        _log.warning("REF003: %s:%d dangling frob:used-by %s", rel_path, line, target)
        violations.append(
            Violation(
                rule="REF003",
                severity=Severity.WARN,
                file=rel_path,
                line=line,
                message=(
                    f"REF003: {rel_path}:{line} declares `frob:used-by "
                    f"{target}` but {target} does not exist as a tracked "
                    f"file or does not reference {rel_path} back -- a "
                    f"dangling declaration is not evidence of use; point it "
                    f"at a real, reaching consumer or remove it"
                ),
            )
        )
    return violations


# frob:ticket T-1665
def _build_ref_gate_indexes(
    root: Path, tracked: tuple[str, ...]
) -> tuple[
    dict[str, str],
    dict[str, frozenset[str]],
    frozenset[str],
    _ReachIndex,
    dict[str, frozenset[str]],
    tuple[UnresolvedImport, ...],
]:
    """Read every tracked file once and build its candidate-token set,
    `_ReachIndex`, and the Python resolved-import substrate once, so
    `ref_gate`'s O(n) file loop never re-derives any of them (extracted
    from `ref_gate` for ARCH001; T-0449's native-stub pairing still
    resolves from `tracked_set`; `_ReachIndex` is T-0831's O(files^2) ->
    O(files) fix for `_auto_inbound`; T-1665 adds the reverse Python
    import-edge map and the whole-repo `UnresolvedImport` tuple
    `_unresolved_python_target` scans)."""
    texts: dict[str, str] = {}
    for rel_path in tracked:
        text = _read_text(root, rel_path)
        if text is not None:
            texts[rel_path] = text
    tracked_set = frozenset(tracked)
    tokens_by_file: dict[str, frozenset[str]] = {
        rel_path: frozenset(_candidate_tokens(text)) for rel_path, text in texts.items()
    }
    reach_index = _build_reach_index(tokens_by_file)
    import_graph = build_import_graph(root, tracked)
    python_reverse_edges = _build_python_reverse_edges(import_graph)
    return (
        texts,
        tokens_by_file,
        tracked_set,
        reach_index,
        python_reverse_edges,
        import_graph.unresolved,
    )


# frob:ticket T-1665
def _ref_gate_file_violations(
    rel_path: str,
    text: str | None,
    tracked_set: frozenset[str],
    tokens_by_file: dict[str, frozenset[str]],
    allowlist: dict[str, str],
    native_stub_pairs: dict[str, str],
    reach_index: _ReachIndex,
    python_reverse_edges: dict[str, frozenset[str]],
    unresolved_imports: tuple[UnresolvedImport, ...],
) -> list[Violation]:
    """REF001/002/003 violations for a single tracked file -- the per-file
    body of `ref_gate`'s main loop, extracted for ARCH001 (line-count).
    T-1665: `inbound` now also includes the Python resolved-import
    channel, and a `.py` file left at zero inbound may report
    `Severity.UNRESOLVED` instead of a flat REF001 (`_unresolved_python_
    target`)."""
    violations: list[Violation] = []
    if text is not None:
        violations.extend(
            _dangling_declarations(
                rel_path, text, tracked_set, tokens_by_file, python_reverse_edges
            )
        )

    if rel_path in allowlist or _is_collectible_test_filename(rel_path):
        return violations

    auto = _auto_inbound(rel_path, reach_index)
    python_resolved = _python_resolved_inbound(rel_path, python_reverse_edges)
    declared = set()
    if text is not None:
        for target in _declared_consumers(rel_path, text):
            if target in tracked_set and _consumer_reaches(
                target, rel_path, tokens_by_file, python_reverse_edges
            ):
                declared.add(target)
    inbound = auto | declared | python_resolved
    native_manifest = native_stub_pairs.get(rel_path)
    if native_manifest is not None:
        inbound = inbound | {native_manifest}
    unresolved = not inbound and _unresolved_python_target(
        rel_path, unresolved_imports
    )
    tier_violation = _ref001_or_002(rel_path, inbound, unresolved=unresolved)
    if tier_violation is not None and tier_violation.rule not in _md_waived_rules(
        rel_path, text
    ):
        violations.append(tier_violation)
    return violations


# frob:doc docs/modules/gates.md#anti-orphan-file-reference-gate-t-0396
# frob:ticket T-0396
# frob:tests tests/test_refs_gate.py::TestTiers.test_zero_refs_warns_ref001
# frob:tests tests/test_refs_gate.py::TestTiers.test_two_refs_passes
def ref_gate(root: Path) -> tuple[Violation, ...]:
    """REF001 (0 inbound refs), REF002 (1 inbound ref), REF003 (dangling
    `frob:used-by`) over every git-tracked file under `root`, honoring
    `frob.excludes`, the `[[refs.entrypoint]]` allowlist, and the
    test-discovery IMPLICIT reference (below).

    A file whose own basename matches a test-collection naming convention
    (`_is_collectible_test_filename`: `test_*.py`, `*_test.py`,
    `*.test.ts`, ...) is exempt from REF001/REF002 -- it is referenced by
    the test RUNNER via naming convention, never by another tracked
    file's text, so the auto-scan structurally cannot see it and it would
    otherwise be a permanent false orphan (T-0396 round-2, reviewer-
    caught: 197 of 379 REF001 findings, 52%, were exactly this before the
    fix). Deliberately NOT `frob.excludes.is_test_file` (its broader
    directory-membership rule -- "anything under `tests/`" -- exempted a
    dead, unreferenced NON-test fixture/helper file that merely lives
    under `tests/`, hiding a genuine orphan; T-0396 round-3, reviewer-
    caught). Still subject to REF003 (a test file's own dangling
    `frob:used-by` is still a lie).

    WARN-only (never blocks a build): every orphan must eventually be
    waived-with-reason or fixed, but this gate itself never fails `frob
    check`'s exit code."""
    tracked = _shared_tracked_files(root, caller="ref_gate")
    if not tracked:
        _log.info("ref_gate: no tracked files found, skipping")
        return ()
    exclude_globs = load_exclude_globs(root)
    allowlist = _load_allowlist(root)

    # T-0449: native-extension `.pyi` stub -> build-manifest edges,
    # resolved once up front from `pyproject.toml`/`[tool.maturin]`
    # rather than re-derived per candidate. T-1665: the Python
    # resolved-import substrate (`frob.graph.imports.build_import_graph`)
    # is likewise built once here, not per candidate.
    (
        texts,
        tokens_by_file,
        tracked_set,
        reach_index,
        python_reverse_edges,
        unresolved_imports,
    ) = _build_ref_gate_indexes(root, tracked)
    native_stub_pairs = _native_stub_pairs(tracked_set, root)

    violations: list[Violation] = []
    for rel_path in tracked:
        if is_excluded(rel_path, exclude_globs):
            continue
        violations.extend(
            _ref_gate_file_violations(
                rel_path,
                texts.get(rel_path),
                tracked_set,
                tokens_by_file,
                allowlist,
                native_stub_pairs,
                reach_index,
                python_reverse_edges,
                unresolved_imports,
            )
        )

    _log.info(
        "ref_gate: %d tracked file(s) checked, %d violation(s)",
        len(tracked),
        len(violations),
    )
    return tuple(violations)

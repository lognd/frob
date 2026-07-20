"""REF001/REF002/REF003: anti-orphan gate over every git-tracked file
(docs/modules/gates.md#anti-orphan-file-reference-gate, T-0396).

Motivating case: `docs/design/registry/*.yaml` manifests were read by ZERO
files -- a silently dead (or silently unenforced) artifact that no existing
gate caught, because every other gate reasons about SOURCE symbols (`frob.
graph`'s import/DSL edges), never about a bare tracked file's existence
being justified at all. This module closes that gap generically, over
EVERY git-tracked file regardless of type (source, docs, config, data,
assets) -- not just the languages `frob.lang` knows how to parse.

Detection is two-layered:

1. AUTO-SCAN (cross-type, language-agnostic): file X counts as referenced
   by file Y if Y names X (full repo-relative path or bare basename) in a
   real reference SYNTACTIC position -- a markdown link, a quoted string
   literal, a backtick-wrapped MULTI-COMPONENT path mention (contains a
   `/` -- e.g. `` `docs/rework.md` ``, the repo's own doc convention;
   T-0467), a `frob:doc`/`frob:describes`/`frob:used-by`/`frob:tests`
   directive target, or a Python import (`from X import a, b, c`, a
   parenthesized/multi-line import list, or a plain `import a, b.c`) --
   NEVER a bare prose/table mention or a backtick-wrapped bare identifier
   (round-2, reviewer-caught:
   a naive whole-text substring match produced an 86% false-positive
   rate, both false ORPHANS -- import lists only resolving their module
   prefix, never the imported names -- and false PASSES -- a doc's prose
   mention of a filename counted as a reference). For `.py` TARGETS ONLY,
   a bare imported name / quoted module-name string also resolves via the
   target's extensionless stem (`_tokens_reach`'s docstring has the full
   reasoning for why that shortcut is restricted to Python targets).
2. DECLARED (`frob:used-by <consumer>`): a file can name its own consumer
   explicitly, for references the auto-scan structurally cannot see (a
   path built at runtime, a glob loaded by a directory base). Every
   declaration is VERIFIED, not trusted: the named consumer must be a
   tracked file AND must itself reach the declaring file (same
   syntactic-position check, in reverse) -- a declaration naming a
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

from frob.excludes import is_excluded, load_exclude_globs
from frob.gates._models import Severity, Violation
from frob.gitio import run_argv
from frob.logging import get_logger

_log = get_logger(__name__)

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


def _tracked_files(root: Path) -> tuple[str, ...]:
    """Every git-tracked file under `root`, repo-relative POSIX paths.

    Degrades to `()` (no candidates, no violations) rather than raising on
    a git failure -- consistent with every other gate's "missing state
    skips the gate, never crashes `frob check`" posture."""
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("ref_gate: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("ref_gate: git ls-files exited %d", result.returncode)
        return ()
    return tuple(line for line in result.stdout.splitlines() if line)


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


# frob:doc docs/modules/gates.md#anti-orphan-file-reference-gate-t-0396
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


# T-0396 round-2 (reviewer-caught, T-0396 Done report): the FIRST version of
# this only captured a `from X import ...`'s MODULE PREFIX, never the
# imported NAMES -- `from frob.arch import _cpp, _python` produced only the
# token `frob.arch`, so `src/frob/arch/_cpp.py` (reached only through that
# multi-name import) was a false REF001 orphan. `_python_import_targets`
# below parses every name in a `from`-import (single-line, comma-list, AND
# parenthesized/multi-line continuation) and a plain `import a, b.c as d`,
# producing per-name candidate tokens -- `_tokens_reach`'s stem/dotted-path
# matching (below) is what actually resolves a bare imported name like
# `_cpp` back to a file `_cpp.py`.
_FROM_IMPORT_RE = re.compile(
    r"\bfrom\s+([\w.]+)\s+import\s*(?:\((?P<paren>[^)]*)\)|(?P<line>[^\n]+))"
)
_PLAIN_IMPORT_RE = re.compile(r"^[ \t]*import\s+([^\n]+)", re.MULTILINE)


def _split_import_names(blob: str) -> list[str]:
    """Every distinct name in a comma-separated import clause, `as alias`
    and bare `*` dropped, whitespace/parens trimmed -- shared by both the
    `from X import ...` and plain `import ...` shapes."""
    names: list[str] = []
    for part in blob.split(","):
        name = part.strip().strip("()")
        if not name or name == "*":
            continue
        name = name.split(" as ")[0].strip()
        if name:
            names.append(name)
    return names


def _python_import_targets(text: str) -> list[str]:
    """Every candidate reference token from `text`'s `from X import ...`
    (single-line, comma-list, or parenthesized/multi-line) and plain
    `import a, b.c as d` statements: the module path, `module.name` for
    each imported name, and the bare name alone (so a later `from pkg
    import _cpp` resolves against a file `_cpp.py` regardless of which
    package re-exports it)."""
    tokens: list[str] = []
    for match in _FROM_IMPORT_RE.finditer(text):
        module = match.group(1)
        blob = (
            match.group("paren")
            if match.group("paren") is not None
            else match.group("line")
        )
        for name in _split_import_names(blob or ""):
            tokens.append(module)
            tokens.append(f"{module}.{name}")
            tokens.append(name)
    for match in _PLAIN_IMPORT_RE.finditer(text):
        for name in _split_import_names(match.group(1)):
            tokens.append(name)
    return tokens


def _candidate_tokens(text: str) -> tuple[str, ...]:
    """Every path-shaped token `text` names in a real reference position
    (markdown link target, quoted string literal, an import statement's
    module/name(s), a require/include/use target, or a `frob:doc`/
    `frob:describes`/`frob:used-by` directive target) -- the universe
    `_reaches` matches against, deliberately excluding plain prose/table/
    backtick mentions."""
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
    tokens.extend(_python_import_targets(text))
    return tuple(tokens)


def _tokens_reach(tokens: frozenset[str], target_path: str) -> bool:
    """True if `tokens` (a file's precomputed `_candidate_tokens` set)
    names `target_path` by full repo-relative path, bare basename, or --
    for `.py` TARGETS ONLY -- a dotted-import form that resolves to it:
    the file's extensionless STEM appearing as a token by itself, or as
    the final dotted component of a longer token (`frob.arch._cpp` ->
    stem `_cpp`). This is what makes a multi-name `from X import a, b, c`
    or a dispatch table's bare quoted module-name string (`"ack_runner"`
    reaching `ack_runner.py`) resolve, since neither shape spells the
    target's full path or `.py`-suffixed basename literally (T-0396
    round-2, reviewer-caught false-orphan bug).

    Deliberately restricted to `.py` targets: a bare stem match against a
    NON-Python target (a `.yaml`/`.md`/data file) is exactly the false
    PASS T-0396's fix-verification round caught -- a quoted English word
    that happens to equal a data file's stem (e.g. a test asserting
    `g.family == "compliance"`, unrelated to `compliance.yaml`) is not a
    reference, and treating it as one would silently un-flag the exact
    `docs/design/registry/*.yaml` orphans this gate exists to catch. A
    data/doc file must be named by its FULL basename (with extension) or
    full path -- code that actually opens/loads one always spells it that
    way (`open("some_file.yaml")`, `Path(...) / "some_file.yaml"`, a glob
    pattern) -- so the stricter full-name-only rule loses no real
    coverage for that class of target."""
    basename = PurePosixPath(target_path).name
    if target_path in tokens or basename in tokens:
        return True
    if any(
        token.endswith("/" + basename) or token.endswith("/" + target_path)
        for token in tokens
    ):
        return True
    if not target_path.endswith(".py"):
        return False
    stem = PurePosixPath(target_path).stem
    if stem in tokens:
        return True
    return any(token.endswith("." + stem) for token in tokens)


def _reaches(text: str, target_path: str) -> bool:
    """`_tokens_reach` over a freshly extracted token set -- convenience
    for the single-text (declaration-verification) call sites; `ref_gate`
    itself uses precomputed per-file token sets instead to avoid
    re-extracting the same file's tokens once per candidate (O(n^2))."""
    return _tokens_reach(frozenset(_candidate_tokens(text)), target_path)


def _auto_inbound(
    candidate: str, tokens_by_file: dict[str, frozenset[str]]
) -> set[str]:
    """Every OTHER tracked file whose precomputed token set reaches
    `candidate` (the auto-scan layer -- imports, path literals, doc
    links, directive targets, all collapse to the same token-reach
    check)."""
    return {
        other
        for other, tokens in tokens_by_file.items()
        if other != candidate and _tokens_reach(tokens, candidate)
    }


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


def _ref001_or_002(rel_path: str, inbound: set[str]) -> Violation | None:
    """The tier violation for `rel_path` given its deduped inbound set, or
    `None` if it clears the 2+ pass bar."""
    count = len(inbound)
    if count == 0:
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


def _dangling_declarations(
    rel_path: str,
    text: str,
    tracked: frozenset[str],
    tokens_by_file: dict[str, frozenset[str]],
) -> list[Violation]:
    """REF003 for every `frob:used-by` target on `rel_path` that does not
    resolve to a real, reaching consumer -- the anti-lie check: a
    declaration is a claim, and this is where the claim gets verified."""
    violations: list[Violation] = []
    for target in _declared_consumers(rel_path, text):
        consumer_tokens = tokens_by_file.get(target)
        valid = (
            target in tracked
            and consumer_tokens is not None
            and _tokens_reach(consumer_tokens, rel_path)
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
    tracked = _tracked_files(root)
    if not tracked:
        _log.info("ref_gate: no tracked files found, skipping")
        return ()
    exclude_globs = load_exclude_globs(root)
    allowlist = _load_allowlist(root)

    texts: dict[str, str] = {}
    for rel_path in tracked:
        text = _read_text(root, rel_path)
        if text is not None:
            texts[rel_path] = text
    tracked_set = frozenset(tracked)
    # T-0449: native-extension `.pyi` stub -> build-manifest edges,
    # resolved once up front from `pyproject.toml`/`[tool.maturin]`
    # rather than re-derived per candidate.
    native_stub_pairs = _native_stub_pairs(tracked_set, root)
    # Every file's token set computed exactly once -- `_auto_inbound` and
    # `_dangling_declarations` both need "does file Y's text reach file
    # X", which would otherwise re-run `_candidate_tokens`'s regex sweep
    # once per (X, Y) pair (O(n^2) regex work over the whole repo).
    tokens_by_file: dict[str, frozenset[str]] = {
        rel_path: frozenset(_candidate_tokens(text)) for rel_path, text in texts.items()
    }

    violations: list[Violation] = []
    for rel_path in tracked:
        if is_excluded(rel_path, exclude_globs):
            continue
        text = texts.get(rel_path)
        if text is not None:
            violations.extend(
                _dangling_declarations(rel_path, text, tracked_set, tokens_by_file)
            )

        if rel_path in allowlist or _is_collectible_test_filename(rel_path):
            continue

        auto = _auto_inbound(rel_path, tokens_by_file)
        declared = set()
        if text is not None:
            for target in _declared_consumers(rel_path, text):
                consumer_tokens = tokens_by_file.get(target)
                if (
                    target in tracked_set
                    and consumer_tokens is not None
                    and _tokens_reach(consumer_tokens, rel_path)
                ):
                    declared.add(target)
        inbound = auto | declared
        native_manifest = native_stub_pairs.get(rel_path)
        if native_manifest is not None:
            inbound = inbound | {native_manifest}
        tier_violation = _ref001_or_002(rel_path, inbound)
        if tier_violation is not None and tier_violation.rule not in _md_waived_rules(
            rel_path, text
        ):
            violations.append(tier_violation)

    _log.info(
        "ref_gate: %d tracked file(s) checked, %d violation(s)",
        len(tracked),
        len(violations),
    )
    return tuple(violations)

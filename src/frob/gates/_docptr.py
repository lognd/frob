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

A source-level check rides alongside the doc-prose scan for the SAME
reason this ticket names explicitly (the DRIFT002 dotted-vs-`::`
confusion, T-0940/T-0945): a `frob:tests` directive's target is itself a
RECOGNIZED, mechanically-checkable shape -- `<file>::<qualname>` with
exactly one `::` separating the file from a DOTTED (`Class.method`)
qualname. A target with a SECOND `::` (pytest's own `Class::method`
collect-only separator, e.g. `foo.py::TestX::test_y`) is definitively the
wrong shape for a graph-facing `frob:tests` target -- this is caught here,
directly, rather than waiting for it to surface later as a generic
DRIFT002 dangling-edge failure with a less specific message. As of T-0986
this is its OWN rule, DOC007, at ERROR (not DOC006/WARN): the mistake
recurred four separate times (T-0715, T-0926, T-0976 x8, T-0983), each
only ever surfacing post-land as a DRIFT002 failure, so it now refuses at
author time instead. It is split into a dedicated rule id specifically so
this promotion does not also promote the other ~700 live DOC006 findings
in this repo (an unrelated, still-WARN burn-down) to ERROR.

Every DOC006 finding is `frob:waive DOC006 reason="..."`-able (same
nearby-line convention as DOC004: same line or up to 3 preceding lines),
for a genuinely external/illustrative/future-facing pointer. Every DOC007
finding is likewise `frob:waive DOC007 reason="..."`-able, via the
standard source-level `frob:waive` edge (T-0986's check operates on graph
edges, not doc prose, so it goes through the normal edge-waiver path
`frob.gates.__init__._apply_waivers` uses for every other code-facing
gate, not DOC006's own `.md`-only nearby-line scan).
"""
# frob:ticket T-0437
# frob:waive INV006 reason="T-0437 INV006 first-turn-on pool: this module's 'only' \
# usages are source-level design-rationale prose (a docstring/comment describing \
# already-implemented scan-scope behavior, verifiable by reading the code it annotates \
# -- e.g. 'only fires when...', 'checked ... only the top-level one') rather than a \
# separate cross-module contract needing its own tracked invariant; disposed as a \
# calibration batch, same posture as frob.gates._docblocks's own T-0585 INV006 waiver"

from __future__ import annotations

import bisect
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

_BACKTICK_RE = re.compile(r"`([^`]{2,400}?)`")
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
    this package).

    T-1228: the backtick scan runs over the WHOLE text (not line-by-line)
    so a span an editor line-wrapped mid-token -- commonmark treats a
    single embedded newline inside an inline code span as ordinary
    whitespace, so `` `frob.gates.\n_docptr` `` is the SAME token as
    `` `frob.gates._docptr` `` written on one line -- still resolves. A
    span containing a BLANK line (`\n\n`, a real paragraph break) is
    rejected: that is two unrelated stray backticks, never a genuine
    wrapped span, and the un-bounded content class would otherwise let a
    single stray backtick swallow arbitrarily much following prose."""
    tokens: list[tuple[int, str]] = []
    # PERF002: precompute newline offsets ONCE (not a `.count()` call per
    # match) so per-match line lookup is a bisect, not an O(text) rescan.
    newline_offsets = [i for i, ch in enumerate(text) if ch == "\n"]
    for match in _BACKTICK_RE.finditer(text):
        raw_token = match.group(1)
        if "\n\n" in raw_token:
            continue
        line_no = bisect.bisect_right(newline_offsets, match.start()) + 1
        token = " ".join(raw_token.split()) if "\n" in raw_token else raw_token
        tokens.append((line_no, token))
    for line_no, line in enumerate(text.splitlines(), start=1):
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


# frob:enforces CHK-GATE-DOC007
def _doc007_violation(file: str, line: int, detail: str) -> Violation:
    """Build one DOC007 violation (T-0986): a `frob:tests` target using
    pytest's `Class::method` collect-only separator instead of this
    graph's own single-`::`-then-dotted-qualname convention. Split out of
    DOC006 (rather than promoting that whole family to ERROR) SPECIFICALLY
    so this one recognized-shape mistake refuses at author time -- the
    other ~700 live DOC006 findings in this repo stay at WARN, untouched,
    a separate burn-down. Shipped at ERROR from birth (not the WARN-first-
    turn-on precedent DOC006 itself used): the shape it catches has zero
    live occurrences on `main` (verified by grep before this rule shipped)
    and every historical occurrence (T-0715, T-0926, T-0976 x8, T-0983)
    only ever surfaced post-land as a DRIFT002 dangling-edge failure --
    there is no adoption baseline to protect, only a recurring author-time
    mistake to refuse outright."""
    return Violation(
        rule="DOC007",
        severity=Severity.ERROR,
        file=file,
        line=line,
        message=(
            f"DOC007: frob:tests target-form in {file}:{line} does not "
            f"resolve -- {detail}; fix the reference or "
            f'`frob:waive DOC007 reason="..."` if intentionally external/'
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
# this repo's own top-level tracked directories a genuine DIRECTORY-only
# reference (no file extension on its last segment, e.g. `src/frob/strata`)
# is plausibly rooted at -- kept as an explicit, small, project-local list
# rather than walking `git ls-files` for a first-segment set on every call.
_KNOWN_TOP_LEVEL_DIRS = frozenset(
    {
        "src",
        "tests",
        "docs",
        "scripts",
        "agents",
        "skills",
        "editors",
        "invariants",
        "design",
        "frob-core",
        "strata-core",
        ".frob",
        ".git",
        ".github",
        ".claude",
    }
)


def _looks_like_path(token: str) -> bool:
    """Whether `token` (anchor already stripped by the caller) matches the
    recognized FILE/PATH shape -- see `_PATH_SHAPE_RE`.

    T-1015 matcher hardening: `_PATH_SHAPE_RE` alone (any
    `/`-joined run of word/dot/hyphen characters) also matches prose that
    is NOT a path at all -- a units ratio (`req/s`), a test-permutation
    suffix (`sum_twice_a/b`), or an enumeration/alternatives list written
    with `/` as an "or" separator (`.ts/.tsx/.c/.cpp`, `for/while`,
    `fake/changeme/example/placeholder`, `your-/insert-/-here`). None of
    those are FILE/PATH pointers, so flagging them as unresolved paths is a
    pure false positive, not real doc drift. Three additional shape checks
    narrow the recognized set to what a real repo-relative reference
    actually looks like, without touching the underlying resolution logic
    for anything that still passes:

    - a non-leading segment starting with `.` (an enumerated dotfile/
      extension list, e.g. `.ts/.tsx/.c`) is never a real path segment;
    - a segment that is bare punctuation glued to a hyphen at either edge
      (`your-`, `-here`) is a sentence fragment, never a path component;
    - the LAST segment must either carry a file extension (contain `.`) or
      the token must be rooted at one of this repo's own known top-level
      directories (`_KNOWN_TOP_LEVEL_DIRS`) -- the two genuine FILE/PATH
      shapes this gate resolves (a filename, or a directory-only mention)
      -- a token that is neither (`fake/changeme/example/placeholder`) is
      simply not a recognized pointer shape.
    """
    if token in _WELL_KNOWN_MANIFESTS:
        return True
    if not _PATH_SHAPE_RE.match(token):
        return False
    segments = token.split("/")
    first = segments[0]
    if "." in first and first not in _KNOWN_TOP_LEVEL_DIRS:
        # a first segment with an embedded dot that isn't one of this
        # repo's own directories reads as a bare (protocol-less) HOSTNAME
        # (`martinfowler.com/bliki/...`, `dl.acm.org/doi/...`) or a
        # citation identifier (a DOI like `10.1145/358198.358210`) -- a
        # doc's reference corpus routinely cites external literature this
        # way; that is never a repo-relative FILE/PATH, so it is not a
        # recognized shape at all (T-1015).
        return False
    for i, seg in enumerate(segments):
        if seg.startswith("."):
            if i == 0 and seg in _KNOWN_TOP_LEVEL_DIRS:
                continue
            return False
        if seg.startswith("-") or seg.endswith("-"):
            return False
    last = segments[-1]
    return "." in last or segments[0] in _KNOWN_TOP_LEVEL_DIRS


def _is_tracked_dir_prefix(candidate: str, tracked: frozenset[str]) -> bool:
    """Whether `candidate` is itself a real repo-relative DIRECTORY -- some
    tracked file's path starts with `candidate + "/"`. A doc that mentions
    `src/frob/strata` (a real package directory, no single file by that
    exact name) is pointing at something genuinely real; without this, the
    FILE/PATH check could only ever match an exact FILE, false-flagging
    every directory-only mention as unresolved."""
    prefix = candidate + "/"
    return any(t.startswith(prefix) for t in tracked)


def _is_tracked_path_suffix(candidate: str, tracked: frozenset[str]) -> bool:
    """Whether `candidate` is a trailing-component match of some real
    tracked file's path (`t == candidate` or `t.endswith("/" + candidate)`)
    -- doc prose routinely refers to a file by its shorter, module-relative
    tail (`gates/__init__.py` for `src/frob/gates/__init__.py`,
    `_docptr.py` for `src/frob/gates/_docptr.py`) rather than the full
    repo-relative path; that shorthand is a real, resolvable reference,
    not stale drift."""
    suffix = "/" + candidate
    return any(t == candidate or t.endswith(suffix) for t in tracked)


def _path_candidates(doc_path: str, file_part: str) -> set[str]:
    """Every repo-relative spelling `file_part` (a token's FILE/PATH half,
    anchor already stripped) plausibly resolves to: itself, a `./`-stripped
    form, a doc-relative join for `../`/`./`-prefixed tokens, and a `root/`-
    stripped form for `root/frob.toml`-style doc phrasing -- split out of
    `_file_and_anchor_violations` (T-1015 ARCH001 long-function
    fix) so that function's own body stays under the line-count budget."""
    candidates = {file_part, file_part.lstrip("./")}
    if file_part.startswith("../") or file_part.startswith("./"):
        base = PurePosixPath(doc_path).parent
        candidates.add(str(PurePosixPath(*(base / file_part).parts)))
    if file_part.startswith("root/"):
        candidates.add(file_part[len("root/") :])
    return candidates


def _path_candidate_resolves(candidates: set[str], tracked: frozenset[str]) -> bool:
    """Whether any spelling in `candidates` resolves as a real FILE/PATH --
    an exact tracked file, a tracked directory prefix, or a tracked path
    suffix (see `_is_tracked_dir_prefix`/`_is_tracked_path_suffix`) -- split
    out of `_file_and_anchor_violations` alongside `_path_candidates` for
    the same ARCH001 line-count reason."""
    return (
        any(c in tracked for c in candidates)
        or any(_is_tracked_dir_prefix(c, tracked) for c in candidates)
        or any(_is_tracked_path_suffix(c, tracked) for c in candidates)
    )


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
    positive on every doc that (correctly) mentions one as an example. A
    path rooted at `.git/` (T-1015: `.git/info/exclude`, `.git/
    MERGE_HEAD`) is the identical situation one level up -- git's own
    internal state directory is never itself a git-tracked file, no matter
    how many docs correctly cite a path inside it as a real, existing
    example."""
    violations: list[Violation] = []
    for line_no, token in tokens:
        if token.startswith(("http://", "https://", "mailto:")):
            continue
        file_part, _, anchor_part = token.partition("#")
        if file_part.startswith((".frob/", ".git/")) or file_part in (".frob", ".git"):
            continue
        if not _looks_like_path(file_part):
            continue
        if _nearby_waived(doc_lines, line_no):
            continue
        candidates = _path_candidates(doc_path, file_part)
        if not _path_candidate_resolves(candidates, tracked):
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
            except Exception:
                # A resolved-but-unreadable/malformed tracked doc must not
                # abort the whole doc-pointer scan for every OTHER token in
                # this doc (EXHAUST001/EXHAUST002, T-1371) -- same "cannot
                # confirm the anchor, skip" posture as the OSError branch.
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

#: T-1016 matcher hardening: a bracketed token whose section root is ALL
#: CAPS (`[IN-REPO]`, `[TRUNCATED]`) is a prose citation/label TAG, not a
#: `[section]`/`[section.key]` TOML pointer -- every real frob.toml/
#: pyproject.toml/Cargo.toml table this repo's own loaders read uses a
#: lowercase (optionally dotted) Python-identifier-shaped name, never an
#: all-caps tag. Rejecting this shape before the manifest-lookup path
#: avoids a structurally-impossible DOC006 false positive on citation
#: markup that merely happens to share the `[...]` bracket shape.
_ALL_CAPS_TAG_RE = re.compile(r"^[A-Z][A-Z0-9_-]*$")

#: T-1016 matcher hardening: `[section]`/`[section.key]` names this
#: codebase's own config loaders genuinely read (`data.get("<section>", ...)`
#: chains in `src/frob/**`, verified per-key against the reading module at
#: the time this set was built) but that happen not to appear in THIS
#: project's own `frob.toml`/`pyproject.toml` -- frob does not need to
#: configure `vet`/`policy`/`strata`/etc. on itself for its own operation,
#: so a doc page correctly describing the schema for downstream repos that
#: DO populate these tables was flagged as if the pointer were bogus. Kept
#: as an explicit, individually-verified allowlist (not a source-scanning
#: heuristic) so a genuinely renamed/removed key still fails closed here
#: until re-verified and re-added.
_DECLARED_BUT_UNSET_CONFIG_SECTIONS = frozenset(
    {
        "vet",  # src/frob/vet/_allow.py: data.get("vet")
        "vet.allow",  # same table, `.allow` sub-key
        "vet.detectors",  # src/frob/vet/_capability.py detector-toggle sub-key
        "policy",  # src/frob/policy/__init__.py: doc.get("policy", {})
        "policy.forbidden-import",  # a `[policy]` rule kind, not a nested table
        "policy.pattern",  # a `[policy]` rule kind, not a nested table
        "policy.norm",  # a `[policy]` rule kind, not a nested table
        "strata",  # src/frob/app/deploy_runner.py: data.get("strata", {})
        "strata.benign_capabilities",  # src/frob/strata config sub-key
        "tickets",  # src/frob/gates/__init__.py: tomllib.load(fh).get("tickets", {})
        "check",  # src/frob/app/check_runner.py: data.get("check", {})
        "system",  # `[[system]]` array-of-tables (TEST003/004/009/SystemSpec)
        "perf.heavy",  # src/frob/perf/_redundancy.py: data.get("perf", {}).get("heavy")
        "perf.sketch",  # src/frob/perf/_sketch_store.py: .get("perf", {}).get("sketch")
        "fuzz",  # src/frob/gates/__init__.py: tomllib.load(fh).get("fuzz", {})
        "clean",  # src/frob/clean/_rules.py: data.get("clean", {})
        "tool.frob",  # pyproject.toml form; src/frob/app/config.py
        "repo",  # src/frob/fleet/__init__.py: data.get("repo", [])
        "profile",  # T-1575: src/frob/tickets/_profile.py: doc.get("profile")
        "profile.profile",  # same table, `.profile` sub-key (ProfileName)
    }
)


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
    except Exception:
        # Fail-open (this function's own docstring) over a genuinely
        # unresolvable manifest-load surprise too, not just the two named
        # cases (EXHAUST001, T-1371).
        return None


def _load_toml_manifests(root: Path) -> list[dict]:
    """Every OTHER TOML manifest a `` `[section]` ``/`` `[section.key]` ``
    doc pointer plausibly names, beyond `frob.toml` itself -- T-draft-
    6219ad68 matcher hardening: this repo's own docs routinely cite a
    `pyproject.toml`/`Cargo.toml` section (`[project.optional-
    dependencies]`, `[build-system]`, `[package]`) in the SAME `[section]`
    bracket shape the CONFIG REFERENCE kind recognizes; checking that shape
    ONLY against `frob.toml` was a false-positive class of its own (a real,
    resolvable reference into a sibling manifest, flagged as if it were a
    bogus `frob.toml` key). Loaded once per gate run: the root `pyproject.
    toml` plus every git-tracked `Cargo.toml` (workspace root or any
    per-crate manifest) -- fail-open per manifest, same posture as `_load_
    frob_toml`."""
    manifests: list[dict] = []
    root_pyproject = root / "pyproject.toml"
    if root_pyproject.exists():
        try:
            with root_pyproject.open("rb") as handle:
                manifests.append(tomllib.load(handle))
        except (OSError, tomllib.TOMLDecodeError):
            pass
        except Exception:
            # Fail-open per-manifest (this function's own docstring),
            # same posture as `_load_frob_toml` (EXHAUST001, T-1371).
            pass
    spawned = run_argv(("git", "-C", str(root), "ls-files", "*Cargo.toml"))
    cargo_paths = (
        spawned.danger_ok.stdout.splitlines()
        if spawned.is_ok and spawned.danger_ok.returncode == 0
        else []
    )
    for rel in cargo_paths:
        try:
            with (root / rel).open("rb") as handle:
                manifests.append(tomllib.load(handle))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        except Exception:
            continue
    return manifests


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
    other_manifests: list[dict],
) -> list[Violation]:
    """Kind 3 (CONFIG REFERENCE): `` `[section]` ``/`` `[section.key]` ``
    checked against this project's own loaded `frob.toml` structure, OR --
    T-1015 -- any sibling TOML manifest this repo actually ships
    (`pyproject.toml`, any tracked `Cargo.toml`): a doc legitimately citing
    `[project.optional-dependencies]` or `[package]` is pointing at one of
    THOSE manifests, not `frob.toml`, and resolves there instead. T-1016
    adds two more shape/allowlist escapes: an ALL-CAPS section root
    (`_ALL_CAPS_TAG_RE`) is a citation tag, not a TOML pointer, and a
    dotted name in `_DECLARED_BUT_UNSET_CONFIG_SECTIONS` is a section this
    codebase's own loaders genuinely read even though it happens not to
    appear in this project's own manifests."""
    violations: list[Violation] = []
    if frob_toml is None and not other_manifests:
        return violations
    for line_no, token in tokens:
        match = _CONFIG_REF_RE.match(token)
        if match is None:
            continue
        dotted = match.group(1)
        if _ALL_CAPS_TAG_RE.match(dotted.split(".", 1)[0]):
            continue
        if _nearby_waived(doc_lines, line_no):
            continue
        if (
            (frob_toml is not None and _config_path_exists(frob_toml, dotted))
            or any(_config_path_exists(m, dotted) for m in other_manifests)
            or dotted in _DECLARED_BUT_UNSET_CONFIG_SECTIONS
        ):
            continue
        violations.append(
            _doc006_violation(
                doc_path,
                line_no,
                "config reference",
                f"[{dotted}] is not a real frob.toml/pyproject.toml/"
                f"Cargo.toml section/key",
            )
        )
    return violations


# ---------------------------------------------------------------------------
# Kind 4: CODE SYMBOL (dotted path against manifest-derived python namespaces)
# ---------------------------------------------------------------------------

_DOTTED_SYMBOL_RE = re.compile(r"^[A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*){2,}$")


def _private_twin(names: set[str], name: str) -> str | None:
    """T-1228 private-name awareness: whether `name` (public-looking,
    already absent from `names`) has a leading-underscore TWIN actually
    present in `names` -- the exact "renamed to private, doc never
    updated" class the docs-staleness audit's bare-identifier sweep found
    repeatedly (`digest_sig` -> `_digest_*`, `host_attrs` -> `_host_attrs`,
    `GROWTH_HORIZON_MONTHS` -> `_GROWTH_HORIZON_MONTHS`). Returns the
    private spelling to fold into the violation message, or `None` if no
    such twin exists (an ordinary does-not-exist-at-all case)."""
    if name.startswith("_"):
        return None
    twin = f"_{name}"
    return twin if twin in names else None


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
        violation = _symbol_violation_for_token(
            doc_path, line_no, token, module_map, symbol_names_by_path, root
        )
        if violation is not None:
            violations.append(violation)
    return violations


# frob:ticket T-0976
# frob:waive PII012 reason="'token' here means a parsed dotted-symbol lexical token from this DOC006 doc-pointer scan, not a credential/auth token -- a name-signature false positive"  # noqa: E501
def _symbol_violation_for_token(
    doc_path: str,
    line_no: int,
    token: str,
    module_map: dict[str, str],
    symbol_names_by_path: dict[str, set[str]],
    root: Path,
) -> Violation | None:
    """One dotted CODE SYMBOL `token`'s DOC006 verdict, or `None` if it
    resolves (or is one level deeper than this resolver can prove/refute
    -- `_symbol_violations`'s docstring's conservatism note) -- the per-
    token half of `_symbol_violations`, split from its waiver-check/scan
    loop."""
    module, _, name = token.rpartition(".")
    if token in module_map:
        return None  # the whole dotted token is itself a real module
    if module.endswith(".__init__"):
        # T-1016: a doc author spelling out a package's own `__init__.py`
        # explicitly inside a longer chain (`frob.gates.__init__.perf_gate`
        # naming the `perf_gate` symbol defined directly in `frob/gates/
        # __init__.py`) -- `X.__init__` and bare `X` name the SAME module,
        # so re-resolve against the stripped form rather than treating
        # `X.__init__` as its own (non-existent) submodule.
        module = module[: -len(".__init__")]
    file_path = module_map.get(module)
    if file_path is None:
        # the immediate module prefix does not resolve -- before claiming
        # STALE, check whether a SHORTER prefix resolves and the next
        # segment is a real top-level symbol there (a `module.Class.attr`-
        # shaped chain one level deeper than this resolver can prove/
        # refute): if so, silently skip rather than false-flag a
        # legitimate class-attribute reference.
        outer_module, _, maybe_class = module.rpartition(".")
        outer_file = module_map.get(outer_module)
        if outer_file is not None and (
            maybe_class in symbol_names_by_path.get(outer_file, set())
            # T-1016: `maybe_class` can also be a name RE-EXPORTED (not
            # locally defined) by `outer_file`'s own `__init__.py` --
            # `frob.lang.TreeNode.span` is exactly this shape (`TreeNode`
            # is defined in `frob.lang._models` and re-exported through
            # `frob.lang.__init__`'s own `from ... import` line), the same
            # re-export case the same-level branch below already handles
            # via `_module_reexports` for a plain `module.name` token.
            or _module_reexports(root, outer_file, maybe_class)
        ):
            return None
        return _doc006_violation(
            doc_path, line_no, "code symbol", f"{module!r} does not resolve"
        )
    top_names = symbol_names_by_path.get(file_path, set())
    if (
        name in top_names
        or name in ("__init__", "__all__")
        or f"{module}.{name}" in module_map
        or _module_reexports(root, file_path, name)
    ):
        return None
    twin = _private_twin(top_names, name)
    detail = (
        f"{token} does not resolve to a real symbol -- did it mean the "
        f"private {module}.{twin}?"
        if twin is not None
        else f"{token} does not resolve to a real symbol"
    )
    return _doc006_violation(doc_path, line_no, "code symbol", detail)


# ---------------------------------------------------------------------------
# Kind 6: FILE::SYMBOL -- `path.py::qualname` / `path.rs::name` (T-1228)
# ---------------------------------------------------------------------------

# `<repo-relative-ish path ending .py/.rs>::<name>` -- deliberately does
# NOT allow a second `::` in the symbol half (that shape is DOC007's own
# pytest-collect-only-separator territory over `frob:tests` edges, not a
# doc-prose pointer this kind should also claim).
_FILE_SYMBOL_RE = re.compile(r"^([\w./\-]+\.(?:py|rs))::([A-Za-z_][\w.]*)$")


def _resolve_tracked_file(
    candidates: set[str], tracked: frozenset[str]
) -> tuple[str | None, bool]:
    """`(resolved_path, ambiguous)` for any candidate in `candidates` --
    exact match first, then a tracked path's trailing-component match (the
    same module-relative-shorthand posture `_is_tracked_path_suffix` gives
    kind 1, reused here for the FILE half of `path::symbol`). `resolved_
    path` is `None` when nothing matches OR when a shorthand matches MORE
    THAN ONE distinct tracked file; `ambiguous` (only meaningful when
    `resolved_path is None`) distinguishes those two `None` cases for the
    caller, since they warrant different violations (a genuinely untracked
    file vs. an unrecognized/ambiguous shape that is never flagged).

    T-1228 round-3 fix: a shorthand basename like `_models.py`/`_waive.py`
    is NOT unique in this repo -- 16 different tracked files end in
    `_models.py` alone (`src/frob/refactor/_models.py`,
    `src/frob/strata/_models.py`, ...). Picking the first arbitrary match
    (a `frozenset` iteration order) produced a confirmed false positive:
    `` `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES` `` resolved against
    `src/frob/gates/_waive.py` (which doesn't define it) instead of
    `src/frob/strata/_waive.py` (which does), flagging a real symbol as
    stale. A suffix match against MORE THAN ONE distinct tracked file is
    genuinely ambiguous -- this shape cannot be definitively resolved OR
    refuted without guessing, so it is treated as unrecognized, same
    posture as any other ambiguous token this gate skips."""
    for candidate in candidates:
        if candidate in tracked:
            return candidate, False
    for candidate in candidates:
        suffix = "/" + candidate
        matches = [t for t in tracked if t.endswith(suffix)]
        if len(matches) == 1:
            return matches[0], False
        if len(matches) > 1:
            return None, True
    return None, False


def _file_symbol_violations(
    doc_path: str,
    doc_lines: list[str],
    tokens: list[tuple[int, str]],
    tracked: frozenset[str],
    symbol_names_by_path: dict[str, set[str]],
    root: Path,
) -> list[Violation]:
    """Kind 6 (FILE::SYMBOL): `` `path.py::qualname` `` / `` `path.rs::name` ``
    -- a shape doc authors reach for specifically to disambiguate WHICH
    file a same-named symbol lives in (the dotted CODE SYMBOL kind only
    resolves a symbol via its importable dotted module path, not a bare
    filename). Python: the FILE half must be a tracked `.py` file and the
    first segment of the (optionally dotted) symbol half a real top-level
    name in it -- same one-level conservatism as kind 4 (a `Class.attr`
    second segment is outside what this resolver can prove/refute, so it
    is silently skipped). Rust: the FILE half must be a tracked `.rs` file
    and the (always single, undotted) name an item declaration somewhere
    in it (`_rust_item_defined_in_file`, `pub` optional -- see that
    function's own module-level comment for why).

    T-1228 round-2: `doc_path` in `_LEDGER_FILES` (a ticket ledger's own
    illustrative syntax-example prose, never a live pointer) is excluded
    up front, the same posture `_bare_identifier_violations` takes."""
    if doc_path in _LEDGER_FILES:
        return []
    violations: list[Violation] = []
    for line_no, token in tokens:
        match = _FILE_SYMBOL_RE.match(token)
        if match is None:
            continue
        file_part, symbol = match.group(1), match.group(2)
        candidates = _path_candidates(doc_path, file_part)
        resolved, ambiguous = _resolve_tracked_file(candidates, tracked)
        if resolved is None:
            if ambiguous:
                # T-1228 round-3: a shorthand basename matching more than
                # one tracked file cannot be resolved OR refuted without
                # guessing -- unrecognized shape, never flagged.
                continue
            if _nearby_waived(doc_lines, line_no):
                continue
            violations.append(
                _doc006_violation(
                    doc_path,
                    line_no,
                    "file::symbol",
                    f"{file_part!r} is not a tracked file",
                )
            )
            continue
        if _nearby_waived(doc_lines, line_no):
            continue
        if resolved.endswith(".py"):
            violation = _py_file_symbol_violation(
                doc_path, line_no, resolved, symbol, symbol_names_by_path
            )
        else:
            violation = _rust_file_symbol_violation(
                doc_path, line_no, resolved, symbol, root
            )
        if violation is not None:
            violations.append(violation)
    return violations


def _py_file_symbol_violation(
    doc_path: str,
    line_no: int,
    file_path: str,
    symbol: str,
    symbol_names_by_path: dict[str, set[str]],
) -> Violation | None:
    """The python half of `_file_symbol_violations`: whether `symbol`'s
    FIRST dotted segment is a real top-level name defined in `file_path`."""
    name = symbol.split(".", 1)[0]
    top_names = symbol_names_by_path.get(file_path, set())
    if name in top_names or name in ("__init__", "__all__"):
        return None
    twin = _private_twin(top_names, name)
    detail = (
        f"{file_path}::{symbol} does not resolve -- did it mean the "
        f"private {file_path}::{twin}?"
        if twin is not None
        else f"{file_path}::{symbol} does not resolve to a real symbol"
    )
    return _doc006_violation(doc_path, line_no, "file::symbol", detail)


#: T-1228 round-3: kind 6's rust check is scoped to ONE already-named file
#: (unlike `frob.gates._docblocks_refs._rust_item_defined`'s crate-wide
#: `use` check, where requiring `pub` avoids matching an unrelated
#: same-named PRIVATE helper elsewhere in the crate) -- real-corpus
#: verification found several genuine, currently-defined functions
#: (`parse_node`, `parse_store`, ...) living as trait-impl methods, which
#: never carry an explicit `pub` keyword of their own even though they are
#: real and callable (visibility is inherited from the trait). Since the
#: FILE is already pinned by the doc's own pointer, matching ANY `fn`/
#: `struct`/`enum`/`trait`/`mod`/`const`/`static`/`type` item declaration
#: (`pub` optional) in that one file is precise, not permissive.
_RUST_ITEM_IN_FILE_RE_TMPL = (
    r"\b(?:pub(?:\([^)]*\))?\s+)?(?:fn|struct|enum|trait|mod|const|static|type)\s+"
    r"{name}\b"
)


def _rust_item_defined_in_file(root: Path, file_path: str, name: str) -> bool:
    """Whether `file_path` textually declares an item named `name` -- see
    `_RUST_ITEM_IN_FILE_RE_TMPL`'s docstring-comment for why this, unlike
    `_rust_item_defined`, does not require `pub`."""
    pattern = re.compile(_RUST_ITEM_IN_FILE_RE_TMPL.format(name=re.escape(name)))
    try:
        text = (root / file_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    except Exception:
        # Same fail-closed-to-"not found" posture as the OSError branch --
        # a doc pointer citing an unreadable file is not evidence of a
        # crash-worthy bug (EXHAUST001, T-1371).
        return False
    return pattern.search(text) is not None


def _rust_file_symbol_violation(
    doc_path: str, line_no: int, file_path: str, symbol: str, root: Path
) -> Violation | None:
    """The rust half of `_file_symbol_violations`: whether `symbol` is an
    item declaration somewhere in the single tracked file `file_path`."""
    if "." in symbol:
        return None  # not a recognized rust shape; never a resolvable claim
    if _rust_item_defined_in_file(root, file_path, symbol):
        return None
    return _doc006_violation(
        doc_path,
        line_no,
        "file::symbol",
        f"{file_path}::{symbol} does not resolve to an item in that file",
    )


# ---------------------------------------------------------------------------
# Kind 7: BARE IDENTIFIER, resolved within the doc's own anchored module
# scope (T-1228)
# ---------------------------------------------------------------------------

_BARE_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CAMEL_HUMP_RE = re.compile(r"^[A-Z][a-z0-9]+[A-Z]\w*$")


def _looks_code_shaped_bare_identifier(token: str) -> bool:
    """Whether a bare (undotted, un-pathed, un-bracketed) backtick token
    is CODE-shaped enough to be worth resolving against an anchored
    module's own symbol table at all -- the hardening that keeps this
    kind from firing on ordinary English prose words wrapped in
    backticks. Restricted to `snake_case`/`CONSTANT_CASE` (an embedded,
    non-edge underscore) or multi-hump `CamelCase` (an initial capital
    followed by a lowercase run then another capital) -- the two
    identifier shapes the docs-staleness audit's own bare-identifier
    findings (`digest_sig`, `host_attrs`, `GROWTH_HORIZON_MONTHS`,
    `CycleError`) all share. A single ALL-CAPS acronym or a bare
    Capitalized word (`URL`, `Cycle`) is deliberately NOT matched here --
    both are common in prose/proper-noun use and are outside what this
    conservative shape check can tell apart from a real symbol name."""
    if _BARE_IDENT_RE.match(token) is None or len(token) < 3:
        return False
    if "_" in token.strip("_"):
        return True
    return _CAMEL_HUMP_RE.match(token) is not None


def _anchor_modules_by_doc(root: Path, snapshot: GraphSnapshot) -> dict[str, set[str]]:
    """`{doc_path: {python file paths}}` for every `frob:doc <doc_path>#...`
    edge in the graph. The edge's ORIGIN (`path:line` of the `frob:doc`
    directive itself, `_origin_site`) gives the anchoring file directly --
    more robust than resolving the edge's `src` symref back through
    `snapshot.symbols`, and it is the same origin-based convention
    `_tests_target_shape_violations` already uses in this module for the
    identical reason."""
    mapping: dict[str, set[str]] = {}
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.DOC:
            continue
        doc_path = edge.target.partition("#")[0]
        file_path, _ = _origin_site(edge.origin)
        if not file_path.endswith(".py"):
            continue
        mapping.setdefault(doc_path, set()).add(file_path)
    return mapping


#: T-1228 round-2 (post-close reject): kind 7's ORIGINAL "any frob:doc
#: anchor" scoping was not narrow at all -- a doc page describing a whole
#: module (`docs/modules/gates.md`, `docs/modules/deploy.md`, ...) collects
#: a `frob:doc` edge from EVERY public symbol in that module, so "has at
#: least one anchor" was true for nearly every reference doc in the repo,
#: producing ~1400 false positives on real-corpus verification (moved-
#: module docstrings, cross-file symbol mentions, spec-DSL vocabulary).
#: Genuinely single-module docs -- a small guide page anchored to exactly
#: ONE implementation file -- are the only shape narrow enough that "not a
#: symbol in that one file" is real signal rather than noise; a doc with
#: two or more distinct anchor files is describing a SYSTEM, not one
#: module, and bare identifiers in it are not this kind's business.
_MAX_ANCHOR_MODULES_FOR_BARE_IDENTIFIER = 1

#: T-1228 round-2: `docs/strata/**` and `design/**` are the strata design
#: language's own spec/system-design prose -- their vocabulary
#: (`two_phase_commit`, `capability_kind`, `RULE_ID`, ...) is DSL
#: terminology the strata grammar defines, not python identifiers, even
#: when `snake_case`/`CamelCase`-shaped. These pages are excluded from kind
#: 7 outright rather than relying on the single-anchor-module narrowing
#: alone to filter them (a design doc can easily carry exactly one stray
#: `frob:doc` anchor and still be spec prose, not implementation prose).
_SPEC_PROSE_DOC_PREFIXES = ("docs/strata/", "design/")

#: T-1228 round-2: ticket-ledger files are an append-only historical
#: record whose PROSE quotes illustrative syntax shapes (`path.py::
#: qualname`, ...) -- never a live pointer into the current tree. Excluded
#: from BOTH new T-1228 kinds (file::symbol and bare identifier); the
#: five older kinds already tolerate `tickets.md` fine (its pre-existing
#: file/path and cli-invocation findings are real, tracked drift on
#: `main`), so this exclusion is scoped to these two kinds only, not the
#: whole doc.
_LEDGER_FILES = frozenset({"tickets.md", "tickets-archive.md"})


def _all_project_symbol_names(
    symbol_names_by_path: dict[str, set[str]],
) -> frozenset[str]:
    """The union of every top-level symbol name defined ANYWHERE in the
    project (across every file `symbol_names_by_path` covers) -- T-1228
    round-2's cross-file resolution for kind 7: a bare identifier that
    isn't a top-level name in its doc's single anchor file but IS a real
    symbol somewhere else in the project (`AuditReport`, defined in one
    strata module but discussed in another's doc) is a genuine cross-
    reference, not stale drift; only a name that resolves NOWHERE in the
    project is real signal."""
    names: set[str] = set()
    for file_names in symbol_names_by_path.values():
        names.update(file_names)
    return frozenset(names)


def _bare_identifier_violations(
    doc_path: str,
    doc_lines: list[str],
    tokens: list[tuple[int, str]],
    anchor_files: set[str],
    symbol_names_by_path: dict[str, set[str]],
    all_project_names: frozenset[str],
    root: Path,
) -> list[Violation]:
    """Kind 7 (BARE IDENTIFIER): a code-shaped bare backtick token, checked
    ONLY when `doc_path` is a genuinely SINGLE-implementation-module doc
    (exactly one distinct `frob:doc` anchor file,
    `_MAX_ANCHOR_MODULES_FOR_BARE_IDENTIFIER`) outside the spec-prose
    exclusion (`_SPEC_PROSE_DOC_PREFIXES`) and ledger exclusion
    (`_LEDGER_FILES`).

    T-1228 round-3 (still real-corpus false positives after round-2's
    single-anchor + whole-project-resolution narrowing: field names like
    `bin_path`/`service_account`, and external-system vocabulary like
    `SeDenyInteractiveLogonRight`/`ActiveDirectory`, are code-shaped and
    resolve nowhere in the project's own python symbol table without
    being stale doc pointers at all -- a data/config field or a third-
    party name is never going to be a top-level python symbol, so
    "resolves nowhere" is NOT a resolvable-or-refutable signal for this
    shape the way it is for kind 4's dotted symbol). This kind is
    narrowed to ONLY the one signal that IS definitively resolvable-or-
    refutable: a **private-name rename** -- the identifier does not
    resolve as a real name, but a leading-underscore TWIN (`_name`) is a
    real top-level name in the SAME anchor file. That is unambiguous
    evidence the doc is quoting a name that used to be public and got
    renamed private, not a coincidental non-symbol vocabulary word. A
    bare identifier with no matching name at all (public OR private) is
    silently skipped, same posture as any other unrecognized token in
    this gate."""
    if doc_path in _LEDGER_FILES:
        return []
    if doc_path.startswith(_SPEC_PROSE_DOC_PREFIXES):
        return []
    if len(anchor_files) != _MAX_ANCHOR_MODULES_FOR_BARE_IDENTIFIER:
        return []
    violations: list[Violation] = []
    for line_no, token in tokens:
        if not _looks_code_shaped_bare_identifier(token):
            continue
        if _nearby_waived(doc_lines, line_no):
            continue
        if token in all_project_names:
            continue
        twin: str | None = None
        resolved = False
        for file_path in anchor_files:
            names = symbol_names_by_path.get(file_path, set())
            if _module_reexports(root, file_path, token):
                resolved = True
                break
            candidate = _private_twin(names, token)
            if candidate is not None:
                twin = candidate
        if resolved or twin is None:
            continue
        detail = (
            f"{token!r} does not resolve in its doc's anchored module or "
            f"anywhere else in the project -- did it mean the private "
            f"{twin!r}?"
        )
        violations.append(
            _doc006_violation(doc_path, line_no, "bare identifier", detail)
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
    """DOC007 over every `frob:tests` edge's TARGET string (T-0986,
    formerly a DOC006 sub-check): a second `::` (pytest's `Class::method`
    collect-only separator) where this graph's convention wants a single
    `::` then a DOTTED `Class.method` qualname is a recognized wrong shape,
    flagged here at ERROR directly instead of waiting for it to surface
    later as a generic DRIFT002 dangling-edge failure post-land."""
    violations: list[Violation] = []
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TESTS:
            continue
        if _DOUBLE_SEP_TESTS_TARGET_RE.search(edge.target) is None:
            continue
        file, line = _origin_site(edge.origin)
        violations.append(
            _doc007_violation(
                file,
                line,
                f"{edge.target!r} uses pytest's `Class::method` collect-only "
                f"separator; this graph's own convention is a single `::` "
                f"then a DOTTED `Class.method` qualname",
            )
        )
    return violations


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


# `tickets-archive.md` is a verbatim historical ledger: `frob ticket
# archive` (docs/modules/tickets.md) moves a closed/dropped ticket's
# section -- including its Done report, written at close time -- into this
# file UNCHANGED, forever. A Done report legitimately mentions the config
# keys, file paths, and code symbols that existed AT THE TIME the ticket
# closed; checking that historical prose against the CURRENT tree is not
# this gate's motivating case (a doc that is wrong RIGHT NOW) and would
# incentivize rewriting a supposedly-immutable historical record just to
# quiet a gate -- exactly the failure mode `frob ticket archive`'s
# verbatim-copy contract exists to prevent. T-1015 measured this
# as the single largest DOC006 cluster (154 of 349 findings post-matcher-
# fix, ~44%) before adding this exclusion.
#
# `CHANGELOG.md` (T-1412) is the same class and is excluded for the same
# reason. `frob ticket land` appends an entry at land time describing what
# that change did, naming the symbols and paths as they were THEN, and the
# file is land-owned and append-only thereafter (T-0731's guard refuses a
# hand-edit outright -- which is how this surfaced: a DOC006 on a symbol
# that never existed top-level had no in-worktree path to zero at all,
# because the only honest fix would have been editing an immutable record
# a pre-commit hook correctly refuses to let anyone touch). Checking
# release-note prose written in 2026-06 against the tree as it stands
# today is not this gate's motivating case, and the only way to satisfy
# it would be to falsify history.
_ARCHIVAL_LEDGER_FILES = frozenset({"tickets-archive.md", "CHANGELOG.md"})


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
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006FilePath.test_unrecognized_prose_not_flagged
# frob:tests tests/test_docptr_gate.py::TestDoc006DocAnchor.test_missing_anchor_flagged
# frob:tests tests/test_docptr_gate.py::TestDoc006DocAnchor.test_real_anchor_passes
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006Cli.test_nonexistent_subcommand_flagged
# frob:tests tests/test_docptr_gate.py::TestDoc006Cli.test_nonexistent_flag_flagged
# frob:tests tests/test_docptr_gate.py::TestDoc006Cli.test_real_command_passes
# frob:tests tests/test_docptr_gate.py::TestDoc006Config.test_bogus_section_flagged
# frob:tests tests/test_docptr_gate.py::TestDoc006Config.test_real_section_passes
# frob:tests tests/test_docptr_gate.py::TestDoc006Symbol.test_nonexistent_symbol_flagged
# frob:tests tests/test_docptr_gate.py::TestDoc006Symbol.test_real_symbol_passes
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006Symbol.test_module_dunder_init_and_all_pass
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006Symbol.test_class_attribute_chain_not_flagged
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006FilePath.test_dot_frob_runtime_path_not_flagged
# frob:tests tests/test_docptr_gate.py::TestDoc006Waive.test_waive_suppresses
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006TestsTargetShape.test_double_separator_target_fl\
# agged
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006TestsTargetShape.test_single_separator_target_no\
# t_flagged
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006Config.test_all_caps_citation_tag_not_flagged
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006Config.test_declared_but_unset_section_not_flagg\
# ed
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006Symbol.test_reexported_class_attribute_chain_not\
# _flagged
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006Symbol.test_dunder_init_mid_chain_resolves_to_mo\
# dule
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006FileSymbol.test_py_missing_symbol_flagged
# frob:tests tests/test_docptr_gate.py::TestDoc006FileSymbol.test_py_real_symbol_passes
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006FileSymbol.test_py_private_twin_noted_in_message
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006FileSymbol.test_rust_missing_fn_flagged
# frob:tests tests/test_docptr_gate.py::TestDoc006FileSymbol.test_rust_real_fn_passes
# frob:tests tests/test_docptr_gate.py::TestDoc006FileSymbol.test_missing_file_flagged
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006FileSymbol.test_ambiguous_basename_shorthand_not\
# _flagged
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006FileSymbol.test_rust_non_pub_trait_impl_fn_passes
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006BareIdentifier.test_unanchored_doc_not_checked
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006BareIdentifier.test_anchored_unresolved_without_\
# twin_not_flagged
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006BareIdentifier.test_anchored_real_name_passes
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006BareIdentifier.test_anchored_private_twin_noted
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006BareIdentifier.test_plain_prose_word_not_flagged
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006WrappedSpan.test_wrapped_backtick_span_resolves
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing.test_multi_anchor_doc_no\
# t_checked
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing.test_spec_prose_doc_excl\
# uded
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing.test_cross_file_real_sym\
# bol_passes
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing.test_absent_everywhere_w\
# ithout_twin_not_flagged
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006LedgerExclusion.test_ledger_file_symbol_placehol\
# der_not_flagged
# frob:tests \
# tests/test_docptr_gate.py::TestDoc006LedgerExclusion.test_ledger_bare_identifier_plac\
# eholder_not_flagged
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
    other_manifests = _load_toml_manifests(root)
    anchor_cache: dict[str, set[str] | None] = {}
    doc_anchor_modules = _anchor_modules_by_doc(root, snapshot)
    all_project_names = _all_project_symbol_names(symbol_names_by_path)

    violations: list[Violation] = list(_tests_target_shape_violations(snapshot))
    for doc_path in _tracked_md_files(root):
        if doc_path in _ARCHIVAL_LEDGER_FILES:
            continue
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
        violations.extend(
            _config_violations(doc_path, doc_lines, tokens, frob_toml, other_manifests)
        )
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
        violations.extend(
            _file_symbol_violations(
                doc_path, doc_lines, tokens, tracked, symbol_names_by_path, root
            )
        )
        violations.extend(
            _bare_identifier_violations(
                doc_path,
                doc_lines,
                tokens,
                doc_anchor_modules.get(doc_path, set()),
                symbol_names_by_path,
                all_project_names,
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

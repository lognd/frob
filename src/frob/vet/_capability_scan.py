"""Directory-level aggregation, CVE-fingerprint scanning, self-path
exclusion, and structural-opaqueness detection (T-1420 LARGE001 split, the
"aggregation/fingerprint/opaque tail" out of `frob.vet._capability`
T-1459's design flagged for a follow-up split beyond its own six per-
language binding families). Split verbatim: the self-match exclusion
machinery (`_SELF_PATH`/`_REGISTRY_PATH`/`_FINGERPRINT_CATALOG_PATH`/
`_SELF_PATTERN_SUFFIXES`/`_is_frob_repo_root`/`is_self_pattern_path`), the
per-file/per-directory fingerprint and capability aggregation
(`_binding_fingerprints` through `_aggregate_fingerprints`), and the
`_OpaqueFinding` structural-opaqueness family
(`_split_top_level_args` through `_needle_construct_findings`). Every name
here is re-exported (or imported back) by `_capability` so the module's
public surface (including its `__all__` list) is unchanged."""

# frob:waive INV006 preset="split-carried-prose"
# frob:ticket T-1420
from __future__ import annotations

import re
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from frob.excludes import iter_files
from frob.lang import parse_file, raw_tree
from frob.logging import get_logger

from ._capability_core import (
    _EXT_LANGUAGE,
    ByteSpan,
    _fully_in_any_span,
    _needle_hits_outside_comments_ws,
    _needle_matches_resolved,
    _non_executable_byte_spans,
)
from ._capability_registry import (
    RUNTIME_OPAQUE_CONSTRUCTS,
    RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS,
)

if TYPE_CHECKING:
    from tree_sitter import Node, Tree

    from frob.strata import CveFingerprint

_log = get_logger(__name__)

# absolute paths of this module and the T-0158 registry it compiles
# `_PATTERNS` from -- both excluded from directory aggregation (T-0151/
# T-0158: `_capability_registry.DANGEROUS_OPERATIONS` stores every needle as
# a literal string, same self-match class as this file's derived `_PATTERNS`
# table, so scanning either against itself trivially "observes" every
# capability regardless of what the code actually does).
_SELF_PATH = Path(__file__).resolve()
# T-1420: `_capability_registry.py` split into a package -- no single file
# is "the registry" any more, so `_REGISTRY_PATH` names the package's
# `__init__.py` as the closest equivalent identity anchor. The operative
# exclusion mechanism is `_SELF_PATTERN_SUFFIXES` (updated above for the
# split), not this variable -- neither it nor `_SELF_PATH` is read anywhere
# outside this comment block; both are kept as documented identity anchors
# only, per the T-0253 note below.
_REGISTRY_PATH = (
    Path(__file__).parent / "_capability_registry" / "__init__.py"
).resolve()
# T-0153: `frob.strata._cve_fingerprint` stores every `CveFingerprint.needles`
# entry as a literal string too -- same self-match class as `_REGISTRY_PATH`
# above, so its own file is excluded from directory aggregation on the same
# grounds (module docstring's T-0151/T-0158 self-match note).
_FINGERPRINT_CATALOG_PATH = (
    Path(__file__).parent.parent / "strata" / "_cve_fingerprint.py"
).resolve()

# T-0253: `_SELF_PATH`/`_REGISTRY_PATH`/`_FINGERPRINT_CATALOG_PATH` above are
# identity anchors for THIS running package's own files -- correct only when
# the scanned tree and the running package are the SAME checkout (editable
# install: `uv run frob ...`). Under a non-editable global install (`uv tool
# install frob`), the running package's files resolve to a `site-packages`
# copy, so identity comparison against a SCANNED tree that is frob's own
# repo checkout never matches and every pattern-catalog needle self-matches
# again (36 false SYS100s under `frob sys audit` vs. 0 under `uv run frob
# sys audit`).
#
# Round 1 fix (REJECTED on review): matching by bare PATH SUFFIX (the last
# three path components: package dir / subpackage / filename) with no
# further check. That closed the false-positive but opened a real hole:
# `is_self_pattern_path` is reached from `_scan_directory_capabilities`/
# `_scan_directory_fingerprints`, the SAME public entrypoints `frob vet` uses
# to scan a VENDORED/THIRD-PARTY dependency tree. A malicious dependency
# that places a file at a path ending in `frob/vet/_capability.py` (trivial:
# nest it under any vendor path, or name the package `frob` outright) would
# be silently excluded from capability scanning by suffix alone --
# `is_self_pattern_path` cannot tell "we are auditing frob's own checkout"
# from "we are vetting someone else's tree that happens to mimic frob's
# layout" using the scanned PATH alone.
#
# Round 2 fix (this one): the suffix match stays as the within-frob file
# check, but it is only REACHABLE when a separate SCAN-TARGET discriminator,
# `_is_frob_repo_root`, says the tree actually being scanned is frob's own
# repository -- not the running package's install location (round 1's
# mistake), not the scanned FILE's path alone (round 1 REJECT's mistake),
# but the scanned tree's ROOT identity: `root/pyproject.toml` declares
# `name = "frob"` AND the root also has the `frob-core`/`strata-core` Rust
# crate directories this monorepo actually ships. Requiring both the name
# and the crate directories raises the forgery bar well past "name a PyPI
# package frob" -- a typosquat sdist would also need to vendor two dummy
# top-level directories with those exact names purely to fool this check,
# and gains nothing from doing so since `frob vet`'s dependency scan target
# is the DEPENDENCY's own extracted source root, not frob's repo root,
# in every real invocation. Self-conformance (`_selfconform.py`/
# `_effects.py`) always passes frob's own repo root as `root` by
# construction (self-conformance audits ITS OWN tree), so the discriminator
# is a no-op there; `frob vet` scanning a dependency passes that
# dependency's own source root, which is never frob's repo, so the
# discriminator (correctly) refuses the exclusion and the file gets scanned
# like any other.
# frob:ticket T-0910
_SELF_PATTERN_SUFFIXES: tuple[tuple[str, ...], ...] = (
    ("frob", "vet", "_capability.py"),
    # T-1420 (portion 5): `_capability.py`'s own scanner-core primitives
    # (pattern compilation, needle-matching, embedded-code detection) split
    # out to a sibling module -- it carries the SAME `_PATTERNS`-derived
    # needle-as-data self-match hazard the parent file used to alone, so it
    # needs its own suffix entry here for the same reason the registry
    # package split above already does.
    ("frob", "vet", "_capability_core.py"),
    # T-1420 (tail split): this very module carries the comment block you
    # are reading right now, which quotes `needles=(...)`/`needles: tuple[
    # str, ...]` as literal prose describing the registry package split
    # below -- that quoted text alone trips the drift-lock test's needle-
    # table marker regex on THIS file, same self-match class as every
    # other entry here, so it needs its own suffix entry too.
    ("frob", "vet", "_capability_scan.py"),
    # T-1420: `_capability_registry.py` split into a package -- every
    # submodule that itself carries a `needles=(...)` literal table OR a
    # `needles: tuple[str, ...]` catalog-entry FIELD declaration (the two
    # T-0201 drift-lock shapes -- `_schemas.py`'s `_DangerousOperation`
    # class declares the field even though the actual literal data lives in
    # the two `_dangerous_ops_*.py` tables) needs its own suffix entry here
    # (the exclusion was previously keyed on the single monolithic file; a
    # package has no single file to key on). `__init__.py`/`_kinds.py`
    # carry neither shape (pure re-exports and the plain vocabulary tuple)
    # and are deliberately NOT listed -- scanning them finds nothing to
    # exclude.
    ("frob", "vet", "_capability_registry", "_schemas.py"),
    ("frob", "vet", "_capability_registry", "_dangerous_ops_python.py"),
    ("frob", "vet", "_capability_registry", "_dangerous_ops_other.py"),
    ("frob", "vet", "_capability_registry", "_matrix.py"),
    ("frob", "vet", "_capability_registry", "_opaque.py"),
    ("frob", "strata", "_cve_fingerprint.py"),
    # T-0729: `frob.arch._srp`'s ARCH103 mixed-concern check stores its
    # I/O-classifier signals (`_IO_MODULE_PREFIXES`: `socket.`,
    # `subprocess.`, `requests.`, `urllib.`, ...) as literal string data too
    # -- the exact same self-match class as the two `_capability_registry`/
    # `_cve_fingerprint` entries above: the scanner (by design, for evasion
    # detection) keys on string-literal CONTENT, so a classifier table that
    # merely *names* `socket.`/`subprocess.`/etc. as data reads as live
    # net/exec/fetch_url capability USAGE on the `graphlang` node, which is
    # dishonest -- `_srp.py` does no such I/O itself (module docstring: it
    # only imports `frob.arch._models`/`frob.arch._normalized`). Declaring
    # `may net`/`may exec` on `graphlang` to silence this would be an
    # equally dishonest fix in the other direction, so this file is excluded
    # from self-conformance's capability scan the same way, not given a
    # capability it does not have.
    ("frob", "arch", "_srp.py"),
    # T-0910: `frob.arch._logging_checks`'s ARCH1xx logging-discipline
    # checks store the same class of I/O-classifier signal as `_srp.py`
    # above -- `_BOUNDARY_CALLEE_MARKERS` (`subprocess.`, `requests.`,
    # `httpx.`, `socket.`, ...) is a bare-text needle tuple this module's
    # `_is_boundary_call` compares a CALLEE STRING against, not code that
    # itself execs/opens a socket/fetches a URL. The scanner (by design,
    # for evasion detection) keys on string-literal CONTENT, so a
    # classifier table that merely *names* these substrings as data reads
    # as live net/exec/fetch_url capability USAGE on the `graphlang` node,
    # which is dishonest -- `_logging_checks.py` does no such I/O itself
    # (module docstring: it is written once against `NormalizedModule`,
    # a parsed-fact model, and never touches subprocess/network/sockets
    # directly). Declaring `may net`/`may exec` on `graphlang` to silence
    # this would be an equally dishonest fix in the other direction, so
    # this file is excluded from self-conformance's capability scan the
    # same way `_srp.py` is, not given a capability it does not have.
    ("frob", "arch", "_logging_checks.py"),
    # T-0915: `frob.arch._async_hazards`'s blocking-call classifier stores
    # the same class of I/O-classifier signal as `_srp.py`/`_logging_checks
    # .py` above -- its curated blocking-call-name tables (`subprocess.`,
    # `requests.`, `socket.`, ...) are bare-text needles compared against
    # parsed callee strings, not live I/O; the module itself only reads
    # `NormalizedModule` facts. Excluded from the capability scan for the
    # same reason as its two siblings rather than given `may net`/`may
    # exec` capabilities it does not have.
    ("frob", "arch", "_async_hazards.py"),
)

#: `[project]`-table `name = "frob"` line, tomllib-free (matches this
#: module's existing "cheap substring/regex over parsing" posture) --
#: see `_is_frob_repo_root`.
_FROB_PROJECT_NAME_RE = re.compile(r'(?m)^\s*name\s*=\s*"frob"\s*$')


@lru_cache(maxsize=32)
def _is_frob_repo_root(root: Path) -> bool:
    """True if `root` (resolved) is frob's OWN repository checkout -- the
    scan-target discriminator `is_self_pattern_path` gates its suffix match
    on (T-0253 REJECT round). Requires ALL of: a `pyproject.toml` at `root`
    declaring `name = "frob"`, plus the `frob-core`/`strata-core` Rust crate
    directories this monorepo actually ships alongside it -- name alone is
    forgeable by a typosquat PyPI package; the crate directories are not
    something a dependency being vetted would have any reason to carry.

    Deliberately checks `root` ITSELF only, never an ancestor: `frob vet`
    locates a Python dependency's source under `<project-root>/.venv/lib/
    */site-packages/<name>` (`frob.vet._source._locate_pypi_source`), so
    when frob vets its OWN dependencies, every dependency's located source
    lives NESTED under frob's own repo root. Walking upward from that
    nested path would climb straight back to frob's own `pyproject.toml`/
    `frob-core`/`strata-core` and wrongly classify every one of frob's own
    third-party dependencies as "self" too -- turning the exclusion into a
    scanner-wide bypass for frob's own dependency tree, a strictly worse
    hole than the one this discriminator exists to close. Every real caller
    (self-conformance's `root`, `frob vet`'s located dependency `source_dir`)
    already passes the exact directory that should be checked; the exact
    directory is what this checks. Cached per resolved root: called once
    per file in a directory walk, and the answer cannot change mid-walk."""
    resolved = root.resolve()
    pyproject = resolved / "pyproject.toml"
    if not pyproject.is_file():
        return False
    try:
        text = pyproject.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if not _FROB_PROJECT_NAME_RE.search(text):
        return False
    return (resolved / "frob-core").is_dir() and (resolved / "strata-core").is_dir()


def _binding_fingerprints(
    path: Path,
    language: str,
    comment_spans: tuple[ByteSpan, ...],
    fingerprints: tuple[CveFingerprint, ...],
) -> tuple[CveFingerprint, ...]:
    """T-0380: `fingerprints` entries observed via import/binding-aware
    resolution only -- an aliased import (`import pickle as p; p.loads(...)`)
    resolves to `pickle.loads` through the SAME binding table capability
    scanning already built, so it still matches `FP-DESERIALIZE-PICKLE-001`
    even though the literal text `pickle.loads(` never appears. Mirrors
    `_python_binding_operations`'s shape exactly, against `CVE_FINGERPRINTS`
    instead of `DANGEROUS_OPERATIONS`."""
    from ._capability import (  # T-1420: avoid a circular import
        _resolved_candidates_for_language,
    )

    candidates = _resolved_candidates_for_language(path, language)
    if not candidates:
        return ()
    matched: list[CveFingerprint] = []
    for entry in fingerprints:
        if entry.language != language:
            continue
        for resolved, start, end in candidates:
            if _fully_in_any_span(start, end, comment_spans):
                continue
            if any(
                _needle_matches_resolved(needle, resolved) for needle in entry.needles
            ):
                matched.append(entry)
                break
    return tuple(matched)


# The CVE-fingerprint sibling of `_scan_file_operations` (T-0153): a
# fingerprint's `language` must match `path`'s scanned language bucket AND
# at least one of its `needles` must appear in the file's text, the SAME
# recall-over-precision substring philosophy `_matched_capabilities`
# already uses (module docstring). Imports `frob.strata` LAZILY (not at
# module scope): `frob.strata._effects` imports THIS module for its own
# `_PATTERNS`/`language_for` join, so a top-level `frob.strata` import
# here would be a genuine import cycle -- deferred until call time, when
# both packages have finished initializing.
#
# T-0380: lexical needle-matching alone lets an aliased import evade a
# fingerprint (`import pickle as p; p.loads(...)` never contains the
# literal text `pickle.loads(`) even where capability scanning is already
# binding-aware for the same module. `_binding_fingerprints` folds in
# every fingerprint the file's binding tables resolve to, unioned with the
# existing lexical result by `id` (a fingerprint caught either way is
# reported once, not twice).
# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="docs/modules/vet.md's Public API section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
# frob:ticket T-1329
def _yaml_load_call_lacks_explicit_loader(
    raw: bytes, comment_spans: tuple[ByteSpan, ...]
) -> bool:
    """Whether ANY `yaml.load(` call site in `raw` (outside comments/
    docstrings) lacks an explicit `Loader=` keyword inside its argument
    list. FP-DESERIALIZE-YAML-001's hazard (CVE-2017-18342) is the
    loader-LESS `yaml.load()` default; a call passing `Loader=SafeLoader`/
    `CSafeLoader` is the fingerprint's own prescribed remediation, so a
    plain substring needle firing on it is a false positive (first hit:
    frob's own `tickets/_store.py` after T-1206 switched safe_load ->
    yaml.load(..., Loader=_yaml_loader()) for the C loader). Scans each
    occurrence's argument text up to the balanced close-paren (bounded
    window) for a `Loader` keyword; an unterminated window keeps whatever
    argument text fit in it, so a pathological call still fails toward
    loader-less (fail-closed)."""
    needle = b"yaml.load("
    idx = 0
    while True:
        idx = raw.find(needle, idx)
        if idx == -1:
            return False
        end = idx + len(needle)
        if _fully_in_any_span(idx, end, comment_spans):
            idx = end
            continue
        depth = 1
        pos = end
        window_end = min(len(raw), end + 2000)
        arg_end = window_end
        while pos < window_end:
            ch = raw[pos : pos + 1]
            if ch == b"(":
                depth += 1
            elif ch == b")":
                depth -= 1
                if depth == 0:
                    arg_end = pos
                    break
            pos += 1
        args = raw[end:arg_end]
        if b"Loader" not in args:
            return True
        idx = end


#: fingerprint id -> extra confirmation callable(raw, comment_spans) -> bool,
#: applied ON TOP of the plain substring needle match, same shape as
#: `_SPECIAL_CHECKS` for capability needles (T-0151/T-0209). A fingerprint
#: listed here only counts as matched when its callable ALSO returns True --
#: for needles whose hazard is a specific CALL SHAPE the substring alone
#: cannot discriminate (T-1329: `yaml.load(` with an explicit `Loader=` is
#: the remediation, not the hazard).
# frob:ticket T-1329
_FINGERPRINT_REFINEMENTS: dict[str, Callable[[bytes, tuple[ByteSpan, ...]], bool]] = {
    "FP-DESERIALIZE-YAML-001": _yaml_load_call_lacks_explicit_loader,
}


# frob:ticket T-1329
def _fingerprint_refinement_confirms(
    fingerprint_id: str, raw: bytes, comment_spans: tuple[ByteSpan, ...]
) -> bool:
    """True unless `fingerprint_id` has a `_FINGERPRINT_REFINEMENTS` entry
    that rejects the match -- the default (no refinement registered) keeps
    the plain needle semantics unchanged for every other fingerprint."""
    refinement = _FINGERPRINT_REFINEMENTS.get(fingerprint_id)
    if refinement is None:
        return True
    return refinement(raw, comment_spans)


# frob:ticket T-0153
# frob:tests \
# tests/test_vet.py::TestFingerprintBindingResolution.test_python_aliased_pickle_loads_\
# still_matches
def _scan_file_fingerprints(path: Path) -> tuple[CveFingerprint, ...]:
    """The `frob.strata.CVE_FINGERPRINTS` entries whose needle(s) matched in
    `path`'s raw text, OR whose needle(s) match a binding-resolved
    call/attribute target (T-0380) -- catches an aliased import a lexical
    scan alone would miss."""
    from frob.strata import CVE_FINGERPRINTS

    from ._capability import language_for  # T-1420: avoid a circular import

    language = language_for(path)
    if language is None:
        return ()
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _log.warning("vet: could not read %s for fingerprint scan: %s", path, exc)
        return ()

    comment_spans = _non_executable_byte_spans(path)
    lexical = tuple(
        entry
        for entry in CVE_FINGERPRINTS
        if entry.language == language
        and any(
            _needle_hits_outside_comments_ws(raw, needle.encode("utf-8"), comment_spans)
            for needle in entry.needles
        )
    )
    binding = _binding_fingerprints(path, language, comment_spans, CVE_FINGERPRINTS)
    by_id: dict[str, CveFingerprint] = {}
    for entry in (*lexical, *binding):
        by_id[entry.id] = entry
    matched = tuple(
        entry
        for entry in by_id.values()
        if _fingerprint_refinement_confirms(entry.id, raw, comment_spans)
    )
    if matched:
        _log.info(
            "vet: %s: cve fingerprints matched: %s",
            path,
            sorted(entry.id for entry in matched),
        )
    return matched


# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="docs/modules/vet.md's Public API section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
# frob:waive OPAQUE001 reason="T-1038: scanner false positive on the string literals \
# 'exec' (_EXEC_NEEDLES) below -- this function TEXT-SEARCHES for eval/exec/Function/ \
# etc as substrings in SCANNED source code, it never calls python's exec() itself"
def _decode_to_exec_signal(path: Path) -> bool:
    """True if one function's body reaches both a decode-ish and an exec-ish
    token (docs/modules/vet.md "eval-reachability": the highest-precision detector).

    Uses `frob.lang` symbol extraction so the two tokens must co-occur inside
    the SAME function body, not merely the same file.
    """
    from ._capability import language_for  # T-1420: avoid a circular import

    language = language_for(path)
    if language is None:
        return False
    parsed = parse_file(path)
    if parsed.is_err:
        _log.debug(
            "vet: %s: parse failed for decode-to-exec scan: %s", path, parsed.danger_err
        )
        return False

    for symbol in parsed.danger_ok.symbols:
        if _body_reaches_decode_and_exec(" ".join(symbol.body_tokens)):
            _log.warning(
                "vet: decode-to-exec dataflow in %s::%s", path, symbol.qualname
            )
            return True
    return False


_DECODE_NEEDLES = (
    "base64",
    "b64decode",
    "atob",
    "fromhex",
    "fromCharCode",
    "decode(",
    "zlib.decompress",
)
_EXEC_NEEDLES = (
    "eval",
    "exec",
    "Function",
    "compile",
    "__import__",
    "vm.runInContext",
)


# frob:waive OPAQUE001 reason="T-1038: scanner false positive on the string literals \
# 'exec' (_EXEC_NEEDLES) below -- this function TEXT-SEARCHES for eval/exec/Function/ \
# etc as substrings in SCANNED source code, it never calls python's exec() itself"
def _body_reaches_decode_and_exec(body: str) -> bool:
    """True if one function body's token text reaches both a decode-ish and an
    exec-ish token -- the co-occurrence VET004's highest-precision signal needs."""
    has_decode = any(needle in body for needle in _DECODE_NEEDLES)
    has_exec = any(needle in body for needle in _EXEC_NEEDLES)
    return has_decode and has_exec


# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="docs/modules/vet.md's Public API section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
def _scan_directory_capabilities(
    source_dir: Path, *, max_files: int = 500
) -> tuple[frozenset[str], bool]:
    """Aggregate capabilities across every scannable file under `source_dir`.

    Returns `(capabilities, decode_to_exec_hit)`. Bounded by `max_files` so a
    huge vendored dependency tree cannot make `frob vet` unusable.
    """
    capabilities, decode_to_exec_hit, scanned = _aggregate_capabilities(
        source_dir, max_files
    )
    _log.info(
        "vet: %s: scanned %d file(s), capabilities=%s, decode-to-exec=%s",
        source_dir,
        scanned,
        sorted(capabilities),
        decode_to_exec_hit,
    )
    return frozenset(capabilities), decode_to_exec_hit


def _is_test_path(path: Path) -> bool:
    """True for fixture files under a `test`/`tests` dir -- pure capability noise."""
    return "test" in path.parts or "tests" in path.parts


# True for this module's own source file, the T-0158 registry it compiles
# `_PATTERNS` from, or the T-0153 fingerprint catalog it matches
# `_scan_file_fingerprints` against (excluded from directory aggregation
# since all three contain every needle as literal data, guaranteeing a
# self-match unrelated to what the code does). Public (T-0201): the
# SINGLE shared self-match exclusion -- vet's own directory aggregation
# below AND every `frob.strata._selfconform`/`_effects` join path must
# call this same function rather than keep parallel private copies, or a
# future pattern-catalog file re-introduces the T-0151 self-match class
# in whichever join path forgot to exclude it. This was T-0201's root
# cause: `_selfconform.py`'s extended-kind/all-kind scans and
# `_effects.py`'s line-effect scan all predated this export and had no
# exclusion of their own.
#
# T-0253 round 1 (REJECTED): matched by `_SELF_PATTERN_SUFFIXES` (package-
# relative path suffix) alone, with no scan-target check. That closed the
# non-editable-install false positive but opened a real evasion hole: a
# malicious dependency placing a file at a path ending in
# `frob/vet/_capability.py` would be silently excluded from `frob vet`'s
# capability scan too, since suffix matching cannot distinguish "this is
# frob auditing itself" from "this is frob vetting someone else's tree
# that happens to mimic frob's layout."
#
# T-0253 round 2 (this version): `root` is now the caller's scan-target
# discriminator -- the suffix match only fires when `_is_frob_repo_root
# (root)` says `root` IS frob's own repository checkout (its own
# `pyproject.toml` name plus its `frob-core`/`strata-core` crate
# directories), never based on `path` alone and never based on where the
# RUNNING package's own files happen to live (round 0's bug, identity
# comparison against `_SELF_PATH` et al., which broke under a non-
# editable global install). `root` defaults to `None`, which ALWAYS
# fails the discriminator (fail-closed, deny-by-default, matching this
# codebase's charter posture elsewhere) -- a caller that omits `root`
# gets "never exclude, always scan" rather than a crash, so this stays
# source-compatible with any caller written against the pre-T-0253
# one-argument signature while still closing the evasion hole for every
# real caller in this repo (all of which pass `root` explicitly).
# Self-conformance callers (`_selfconform.py`/`_effects.py`) always pass
# frob's own repo root by construction, so this is a no-op there; `frob
# vet` scanning a dependency passes that dependency's own source root,
# which is never frob's repo, so the exclusion correctly never fires and
# the file is scanned like any other.
# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0201
# frob:ticket T-0253
# frob:waive AFFECT001 reason="T-1371 only widens internal exception handling around path resolution to a broader 'cannot confirm, treat as not a self-pattern path' fallback -- no observable behavior change, so docs/modules/vet.md#public-api needs no update -- doc edits are owned by the concurrent T-1372 DOC006 drain, out of this ticket's scope"  # noqa: E501
def is_self_pattern_path(
    path: Path,
    root: Path | None = None,
    suffixes: tuple[tuple[str, ...], ...] = _SELF_PATTERN_SUFFIXES,
) -> bool:
    """True for this module's own source file, or the T-0158/T-0153 pattern
    catalogs it compiles from, when `root` is frob's own repo checkout.

    `suffixes` (T-0539) defaults to this module's own `_SELF_PATTERN_
    SUFFIXES` but lets an unrelated pattern-table gate (e.g.
    `frob.gates._pii_structural`'s PII011/PII012 detector-definition/
    corpus/fixture self-match class) reuse the SAME root-identity-gated
    discriminator (`_is_frob_repo_root` + path-suffix match) against its
    OWN suffix list, rather than re-deriving a second copy of this
    discriminator for a different pattern-table gate."""
    if root is None or not _is_frob_repo_root(root):
        return False
    try:
        resolved = path.resolve()
        parts = resolved.parts
        return any(
            len(parts) >= len(suffix) and parts[-len(suffix) :] == suffix
            for suffix in suffixes
        )
    except OSError:
        return False
    except (KeyError, TypeError):
        # A genuinely surprising `parts`/`suffix` shape is the same
        # "cannot confirm this is a self-pattern path" outcome as the
        # OSError branch, not a crash (EXHAUST001/EXHAUST002, T-1371).
        return False
    except Exception:
        return False


def _is_self_path(path: Path, source_dir: Path) -> bool:
    """Private alias for `is_self_pattern_path` (T-0201) kept so this
    module's own two pre-existing call sites did not need a rename in the
    same diff as the export; new callers should use the public name.
    `source_dir` (T-0253) is the scan-target discriminator: the directory
    walk's own root, threaded straight through -- see `is_self_pattern_path`
    for why the exclusion must be gated on this rather than on `path`
    alone."""
    return is_self_pattern_path(path, source_dir)


# frob:ticket T-1649
def _files_by_ext(source_dir: Path) -> dict[str, list[Path]]:
    """Every scannable file under `source_dir`, grouped by lowercased
    extension and IN `_EXT_LANGUAGE`'s OWN ORDER (T-1649) -- one
    `iter_files(source_dir)` scan total, shared by `_aggregate_
    capabilities`/`_aggregate_fingerprints` (this file's own docstrings
    already noted these two as "candidate for a genuinely shared helper,
    same walk/exclusion shape"). The pre-fix shape called `iter_files`
    once per extension in `_EXT_LANGUAGE` FROM EACH of the two callers
    separately (PERF011: a fixed, small, always-fully-known table),
    re-walking/re-`git ls-files`-ing the same directory once per
    extension per caller. Grouping (not one flat scan) preserves the
    original per-extension iteration ORDER each caller's own truncation
    logic (`scanned >= max_files`, an ext-major early-break) depends on."""
    by_ext: dict[str, list[Path]] = {ext: [] for ext in _EXT_LANGUAGE}
    for path in iter_files(source_dir):
        lowered = path.suffix.lower()
        if lowered in by_ext:
            by_ext[lowered].append(path)
    return by_ext


def _aggregate_capabilities(
    source_dir: Path, max_files: int
) -> tuple[set[str], bool, int]:
    """Union capabilities plus a decode-to-exec hit across scannable files,
    bounded by `max_files`. Returns `(capabilities, hit, files_scanned)`."""
    capabilities: set[str] = set()
    decode_to_exec_hit = False
    scanned = 0
    by_ext = _files_by_ext(source_dir)
    for ext in _EXT_LANGUAGE:
        if scanned >= max_files:
            break
        # frob:ticket T-0471
        for path in by_ext[ext]:
            if scanned >= max_files:
                _log.warning(
                    "vet: %s: capability scan truncated at %d file(s)",
                    source_dir,
                    max_files,
                )
                break
            if _is_test_path(path) or _is_self_path(path, source_dir):
                continue
            from ._capability import (  # T-1420: avoid a circular import
                scan_file_capabilities,
            )

            capabilities |= scan_file_capabilities(path)
            if not decode_to_exec_hit:
                decode_to_exec_hit = _decode_to_exec_signal(path)
            scanned += 1
    return capabilities, decode_to_exec_hit, scanned


# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="docs/modules/vet.md's Public API section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
# frob:ticket T-0153
def _scan_directory_fingerprints(
    source_dir: Path, *, max_files: int = 500
) -> tuple["CveFingerprint", ...]:
    """Aggregate `frob.strata.CVE_FINGERPRINTS` matches across every scannable
    file under `source_dir` -- the fingerprint sibling of
    `_scan_directory_capabilities` (T-0153: wires `_scan_file_fingerprints`
    into the SAME directory-walk shape `_scan_source` (`frob.vet._scan`)
    already calls `_scan_directory_capabilities` from, so a dependency
    containing e.g. `yaml.load(...)`/`pickle.loads(...)` surfaces a real
    `frob vet` finding, not just a direct-import-only capability). Bounded
    by `max_files`, same test/self-path exclusions as `scan_directory_
    capabilities` (`_is_test_path`/`_is_self_path`)."""
    matched, scanned = _aggregate_fingerprints(source_dir, max_files)
    if matched:
        _log.info(
            "vet: %s: scanned %d file(s), fingerprints=%s",
            source_dir,
            scanned,
            sorted(entry.id for entry in matched),
        )
    return tuple(matched)


def _aggregate_fingerprints(
    source_dir: Path, max_files: int
) -> tuple[set["CveFingerprint"], int]:
    """Union `CveFingerprint` matches across scannable files, bounded by
    `max_files`. Returns `(matched, files_scanned)` -- the fingerprint
    sibling of `_aggregate_capabilities`, same walk/exclusion shape."""
    matched: set[CveFingerprint] = set()
    scanned = 0
    by_ext = _files_by_ext(source_dir)
    for ext in _EXT_LANGUAGE:
        if scanned >= max_files:
            break
        # frob:ticket T-0471
        for path in by_ext[ext]:
            if scanned >= max_files:
                _log.warning(
                    "vet: %s: fingerprint scan truncated at %d file(s)",
                    source_dir,
                    max_files,
                )
                break
            if _is_test_path(path) or _is_self_path(path, source_dir):
                continue
            matched.update(_scan_file_fingerprints(path))
            scanned += 1
    return matched, scanned


# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0665
# frob:waive COV007 reason="T-0871: same -- see COV005 waiver above"
class _OpaqueFinding(BaseModel):
    """One `RUNTIME_OPAQUE_CONSTRUCTS` site (T-0665) found in a file's raw
    text outside a comment span, with the 1-indexed line number
    `frob.gates._opaque`'s `opaque_gate` reports the `OPAQUE001` violation
    at."""

    model_config = ConfigDict(frozen=True)

    construct_name: str
    taxonomy_row: str
    rationale: str
    line: int


# frob:waive PERF003 reason="single linear pass over the call's argument bytes; the inner while only skips one quoted-string span before the outer loop resumes at its end -- both loops advance the shared index i monotonically forward, never re-scanning, so this is O(n) total not a nested cross join"  # noqa: E501
def _split_top_level_args(raw: bytes, start: int) -> list[bytes] | None:
    """Split the comma-separated argument list beginning right after an
    already-matched call's opening `(` (T-0665) into top-level (paren/
    bracket/brace-balanced) argument slices, stopping at the matching
    close paren. Returns `None` if the call is unterminated (truncated
    file, or a needle match inside a string this byte-level scan cannot
    see through) -- `_opaque_indirection_findings` treats `None` the same
    as "argument unknown", i.e. fail-closed (fires), never a silent pass."""
    depth = 1
    arg_start = start
    args: list[bytes] = []
    i = start
    n = len(raw)
    while i < n:
        c = raw[i : i + 1]
        if c in (b'"', b"'", b"`"):
            quote = c
            i += 1
            while i < n and raw[i : i + 1] != quote:
                if raw[i : i + 1] == b"\\":
                    i += 1
                i += 1
            i += 1
            continue
        if c in (b"(", b"[", b"{"):
            depth += 1
        elif c in (b")", b"]", b"}"):
            depth -= 1
            if depth == 0:
                args.append(raw[arg_start:i])
                return args
        elif c == b"," and depth == 1:
            args.append(raw[arg_start:i])
            arg_start = i + 1
        i += 1
    return None


def _arg_looks_literal(arg: bytes) -> bool:
    """True if `arg` (one `_split_top_level_args` slice) is a plain
    string/byte-string literal, allowing python's `r`/`b`/`f`/`rb` string
    prefixes (T-0665) -- these resolve statically, so the ordinary per-
    language resolver already handles them; anything else (an identifier,
    an f-string WITH interpolation, a concatenation, a function call) is
    treated as non-literal and fires the obligation, fail-closed."""
    stripped = arg.strip()
    if not stripped:
        return False
    prefix_end = 0
    while prefix_end < len(stripped) and stripped[prefix_end : prefix_end + 1] in (
        b"r",
        b"b",
        b"f",
        b"R",
        b"B",
        b"F",
    ):
        prefix_end += 1
        if prefix_end > 2:  # noqa: PLR2004 -- longest valid prefix (e.g. "rb") is 2
            return False
    if prefix_end >= len(stripped):
        return False
    quote = stripped[prefix_end : prefix_end + 1]
    if quote not in (b'"', b"'"):
        return False
    # An f-string prefix with a `{` interpolation is NOT a plain literal.
    if prefix_end and stripped[:prefix_end].lower().find(b"f") != -1:
        if b"{" in stripped[prefix_end:]:
            return False
    return stripped.endswith(quote) and len(stripped) >= prefix_end + 2


def _byte_offset_inside_string_literal(raw: bytes, idx: int) -> bool:
    """True if `idx` (a needle match start) sits inside a single-line
    string literal on its own source line (T-0665) -- a same-line unescaped
    `"`/`'` quote-parity check, NOT a full tokenizer. This is a deliberate,
    disclosed heuristic: it exists specifically to keep this module's OWN
    registry files (`RUNTIME_OPAQUE_CONSTRUCTS`'s `needle="getattr("`
    string constants, prose mentioning `eval(` in a docstring/rationale)
    from tripping their own obligation, the single largest false-positive
    class the T-0665 first-turn-on measurement found. It does not attempt
    multi-line string literals (python triple-quoted, JS template
    literals spanning lines) -- a real evasion construct written across a
    line boundary this way is rare and, if missed, still fails closed at
    worst (a missed WARN, not a missed hard block, since this gate ships
    at WARN-tier for its first turn-on regardless)."""
    line_start = raw.rfind(b"\n", 0, idx) + 1
    prefix = raw[line_start:idx]
    dq = 0
    sq = 0
    i = 0
    n = len(prefix)
    while i < n:
        c = prefix[i : i + 1]
        if c == b"\\":
            i += 2
            continue
        if c == b'"':
            dq += 1
        elif c == b"'":
            sq += 1
        i += 1
    return (dq % 2 == 1) or (sq % 2 == 1)


# frob:ticket T-1051
_SUBSCRIPT_CALL_RE = re.compile(rb"[A-Za-z_][A-Za-z0-9_.]*\[([^\[\]\n]{1,200})\]\s*\(")

# frob:ticket T-1051
_EXPLICIT_FNPTR_CAST_CALL_RE = re.compile(
    rb"\(\([A-Za-z_][A-Za-z0-9_ ]*\(\*\)\([^()]*\)\)\s*[A-Za-z_][A-Za-z0-9_]*\)\s*\("
)

# frob:ticket T-1051
_NAMED_TYPE_CAST_CALL_RE = re.compile(
    rb"\(\([A-Za-z_][A-Za-z0-9_]*\)\s*[A-Za-z_][A-Za-z0-9_]*\)\s*\("
)


def _subscript_key_looks_literal(content: bytes) -> bool:
    """True if `content` (a `_SUBSCRIPT_CALL_RE` bracket-interior slice,
    T-1051) is a plain integer or string literal -- these resolve
    statically the same way `_arg_looks_literal` treats a literal call
    argument, so a subscript-then-call site keyed by one is NOT the
    runtime-opaque construct (the ordinary resolver's job); anything else
    (an identifier, an attribute chain, an expression) is non-literal and
    the structural finding fires, fail-closed."""
    stripped = content.strip()
    if not stripped:
        return False
    if stripped.lstrip(b"-").isdigit():
        return True
    return _arg_looks_literal(stripped)


# frob:ticket T-1659
# T-1659: the python builtins whose `RUNTIME_OPAQUE_CONSTRUCTS` needle is a
# BARE, unqualified name (`eval(`, `exec(`, `getattr(`, `setattr(`,
# `__import__(`) -- these are exactly the needles a raw substring scan
# cannot tell apart from (a) the same characters appearing as the tail of a
# longer identifier (`_mutation_for_eval(`, `test_...flags_exec(`, both real
# incidents this repo's own OPAQUE001 waivers already hand-documented as
# "scanner false positive on the ... name") or (b) a dotted attribute/method
# access ending in the same name (`monkeypatch.setattr(`, `model.eval(` --
# pytest's own monkeypatch fixture and z3's `Model.eval`, neither the
# python builtin). Constructs whose needle is ALREADY dotted
# (`importlib.import_module(`) are not in this set -- they need the
# opposite verification (an exact attribute chain, not a bare name) and had
# no reported false positives, so left on the pre-existing text-scan path.
_BARE_PYTHON_BUILTIN_NEEDLES = frozenset(
    {"eval(", "exec(", "getattr(", "setattr(", "__import__("}
)


# frob:ticket T-1659
def _python_bare_call_ok(tree: Tree, start: int, end: int) -> bool | None:
    """Whether the byte span `[start, end)` in `tree` is exactly a python
    `identifier` node used as the UNQUALIFIED callee of a `call` expression
    (T-1659, the coordinator's semantic-check directive following the
    OPAQUE001 symref fix's own audit): `False` when it is the trailing
    `.name` half of a dotted attribute/method access
    (`monkeypatch.setattr(...)`, `model.eval(...)`) or a substring landing
    mid-token inside a longer identifier (`_mutation_for_eval(...)`, a
    needle match that does not start at the identifier's own `start_byte`);
    `None` when the tree has no node cleanly resolving the question (should
    not normally happen for a genuine identifier match) -- treated as
    fail-OPEN by every caller, i.e. still fires, matching this gate's
    existing fail-closed-on-ambiguity doctrine (T-0339): this check only
    ever NARROWS the raw substring scan, never widens it beyond what the
    scan already found."""
    node: Node | None = tree.root_node.descendant_for_byte_range(start, end)
    if node is None:
        return None
    if node.start_byte != start or node.type != "identifier":
        return False
    parent = node.parent
    if parent is None:
        return None
    if parent.type == "attribute":
        return False
    if parent.type == "call":
        # T-1659: tree-sitter's python binding hands back a fresh wrapper
        # object per accessor call, so `is` identity never holds across two
        # separate node lookups even for the SAME underlying tree node --
        # `.id` (the binding's own stable node handle) is the correct
        # comparison, verified empirically against this exact shape.
        func = parent.child_by_field_name("function")
        return func is not None and func.id == node.id
    return None


# frob:ticket T-1659
_SYS_MODULES_NEEDLE = "sys.modules["


# frob:ticket T-1659
def _python_sys_modules_write_ok(tree: Tree, start: int) -> bool | None:
    """Whether the `sys.modules[` match starting at byte `start` is the
    ASSIGNMENT TARGET of a `sys.modules[name] = fake_module` write (T-1659,
    coordinator-directed semantic check) -- `False` for a plain READ
    (`sys.modules["pkg"]` on the right of an assignment, or passed to a
    call/comparison/anywhere else), which is an ordinary, safe dict lookup
    of an already-imported module and not the taxonomy row's "replaces
    what every subsequent import resolves to" write at all. `None` when the
    match cannot be resolved to a `subscript` node at all (should not
    normally happen for a genuine needle hit) -- fail-OPEN, same posture as
    `_python_bare_call_ok`."""
    node: Node | None = tree.root_node.descendant_for_byte_range(
        start, start + len("sys.modules")
    )
    if node is None:
        return None
    subscript = node
    while subscript is not None and subscript.type != "subscript":
        subscript = subscript.parent
    if subscript is None:
        return None
    parent = subscript.parent
    if parent is None or parent.type != "assignment":
        return False
    left = parent.child_by_field_name("left")
    return left is not None and left.id == subscript.id


# frob:ticket T-1051
def _structural_opaque_findings(
    raw: bytes,
    language: str,
    comment_spans: tuple[tuple[int, int], ...],
) -> list[_OpaqueFinding]:
    """`RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS` sites in `raw` (T-1051) --
    the generalized SHAPE-based sibling of `_opaque_indirection_findings`'s
    fixed-needle scan, for taxonomy rows a single literal needle cannot
    express (subscript-then-call with a non-constant key, cast-then-call
    to a function-pointer type) without either missing every real site or
    firing on every ordinary subscript/cast in the file. Each construct's
    `kind` selects one of three structural regexes; `subscript_call`
    additionally re-checks the bracket content against `_subscript_key_
    looks_literal` so a LITERAL-keyed subscript call (already the ordinary
    resolver's job, T-0665's own literal/non-literal split) does not
    double-fire this obligation."""
    findings: list[_OpaqueFinding] = []
    for construct in RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS:
        if construct.language != language:
            continue
        if construct.kind == "subscript_call":
            pattern = _SUBSCRIPT_CALL_RE
        elif construct.kind == "explicit_fnptr_cast_call":
            pattern = _EXPLICIT_FNPTR_CAST_CALL_RE
        elif construct.kind == "named_type_cast_call":
            pattern = _NAMED_TYPE_CAST_CALL_RE
        else:  # pragma: no cover -- registry invariant, never hit in practice
            continue
        for match in pattern.finditer(raw):
            if construct.kind == "subscript_call" and _subscript_key_looks_literal(
                match.group(1)
            ):
                continue
            start, end = match.span()
            if _fully_in_any_span(start, end, comment_spans):
                continue
            if _byte_offset_inside_string_literal(raw, start):
                continue
            # frob:waive PERF002 reason="each match's own (0, start) span needs its own byte-count query over a different sub-range; not a repeated identical count to hoist"  # noqa: E501
            line = raw.count(b"\n", 0, start) + 1
            findings.append(
                _OpaqueFinding(
                    construct_name=construct.construct_name,
                    taxonomy_row=construct.taxonomy_row,
                    rationale=construct.rationale,
                    line=line,
                )
            )
    return findings


# frob:waive DEAD001 reason="T-1024: genuinely called from frob.gates._opaque.opaque_gate, a sibling package under src/frob/gates/ -- DEAD001's intra-package reference graph is built per-directory (dead_symbol_gate's docstring) so a cross-package caller in a different directory is invisible to it; directly unit-tested via the frob:tests directives in tests/test_vet.py"  # noqa: E501
def _opaque_indirection_findings(path: Path) -> tuple[_OpaqueFinding, ...]:
    """`RUNTIME_OPAQUE_CONSTRUCTS` sites in `path` (T-0665, coordinator-
    signed category 1: "evasion-indicative dynamic lookup") -- the
    fail-closed sibling of `scan_file_capabilities`'s ordinary resolver
    path. A construct with `literal_arg_index=None` (eval/exec/reflection)
    always fires; one with a literal_arg_index fires unless that argument
    is a plain string literal (`_arg_looks_literal`), matching the
    coordinator's T-0665 sign-off that a literal-key lookup belongs to the
    ordinary resolver, not this obligation. The rust `libloading` needle
    is additionally gated to files that import `libloading` at all, to
    keep the deliberately-broad bare `.get(` needle from firing on every
    unrelated `HashMap`/`Vec` `.get(` call in a rust file that never
    touches dynamic symbol loading."""
    from ._capability import language_for  # T-1420: avoid a circular import

    language = language_for(path)
    if language is None:
        return ()
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _log.warning(
            "vet: could not read %s for opaque-indirection scan: %s", path, exc
        )
        return ()

    comment_spans = _non_executable_byte_spans(path)
    uses_libloading = language == "rust" and b"libloading" in raw
    # T-1659: parsed once per file, only for python (the only language the
    # `_BARE_PYTHON_BUILTIN_NEEDLES`/`_SYS_MODULES_NEEDLE` semantic checks
    # apply to) -- `raw_tree` is content-hash cached (`frob.lang._parse`),
    # so this costs a real parse once per distinct file content, not once
    # per construct/match.
    python_tree: Tree | None = None
    if language == "python":
        tree_result = raw_tree(path)
        if tree_result.is_ok:
            python_tree = tree_result.danger_ok[0]
    findings: list[_OpaqueFinding] = []
    for construct in RUNTIME_OPAQUE_CONSTRUCTS:
        if construct.language != language:
            continue
        is_libloading_needle = construct.construct_name == "libloading symbol lookup"
        if is_libloading_needle and not uses_libloading:
            continue
        findings.extend(
            _needle_construct_findings(construct, raw, comment_spans, python_tree)
        )
    findings.extend(_structural_opaque_findings(raw, language, comment_spans))
    return tuple(findings)


# frob:ticket T-1659
def _semantic_check_suppresses(
    construct,  # noqa: ANN001 -- frob.vet._capability_registry._OpaqueConstruct
    python_tree: Tree | None,
    idx: int,
    match_end: int,
) -> bool:
    """True if `_needle_construct_findings`'s T-1659 semantic narrowing
    (`_python_bare_call_ok` / `_python_sys_modules_write_ok`) confirms this
    needle match at `[idx, match_end)` is NOT a real indirection site --
    extracted from `_needle_construct_findings`'s own loop body to keep it
    under `ARCH001`'s line threshold, not a behavior change of its own."""
    if python_tree is None:
        return False
    if construct.needle in _BARE_PYTHON_BUILTIN_NEEDLES:
        name_end = match_end - 1  # exclude the needle's trailing "("
        return _python_bare_call_ok(python_tree, idx, name_end) is False
    if construct.needle == _SYS_MODULES_NEEDLE:
        return _python_sys_modules_write_ok(python_tree, idx) is False
    return False


# frob:ticket T-1051
# frob:ticket T-1659
def _needle_construct_findings(
    construct,  # noqa: ANN001 -- frob.vet._capability_registry._OpaqueConstruct
    raw: bytes,
    comment_spans: tuple[tuple[int, int], ...],
    python_tree: Tree | None = None,
) -> list[_OpaqueFinding]:
    """Every site of one `RUNTIME_OPAQUE_CONSTRUCTS` needle in `raw` (T-1051,
    extracted from `_opaque_indirection_findings` to keep it under
    `ARCH001`'s line-count threshold) -- same literal-arg fail-closed logic
    that function always ran inline. T-1659 adds two semantic narrowings,
    both applied BEFORE the literal-arg check even runs, both fail-open
    (only ever narrow the raw substring scan, never widen it):

    - a `_BARE_PYTHON_BUILTIN_NEEDLES` construct with a `python_tree`
      available, confirmed (`_python_bare_call_ok`) to be a dotted
      attribute/method access or a mid-token substring -- neither shape is
      the python builtin this taxonomy row means.
    - the `_SYS_MODULES_NEEDLE` ("sys.modules[") construct, confirmed
      (`_python_sys_modules_write_ok`) to be a plain READ (`mod =
      sys.modules["x"]`, an ordinary already-imported-module lookup) rather
      than the assignment-target WRITE (`sys.modules["x"] = fake`) the
      taxonomy row's own rationale is about.

    Every OTHER construct's behavior is unchanged."""
    findings: list[_OpaqueFinding] = []
    needle = construct.needle.encode("utf-8")
    start = 0
    while True:
        idx = raw.find(needle, start)
        if idx == -1:
            break
        match_end = idx + len(needle)
        start = match_end
        if _fully_in_any_span(idx, match_end, comment_spans):
            continue
        if _byte_offset_inside_string_literal(raw, idx):
            continue
        if _semantic_check_suppresses(construct, python_tree, idx, match_end):
            continue
        fires = True
        if construct.literal_arg_index is not None:
            args = _split_top_level_args(raw, match_end)
            if args is not None and construct.literal_arg_index < len(args):
                fires = not _arg_looks_literal(args[construct.literal_arg_index])
        if fires:
            # frob:waive PERF002 reason="each match's own (0, idx) span needs its own byte-count query over a different sub-range; not a repeated identical count to hoist"  # noqa: E501
            line = raw.count(b"\n", 0, idx) + 1
            findings.append(
                _OpaqueFinding(
                    construct_name=construct.construct_name,
                    taxonomy_row=construct.taxonomy_row,
                    rationale=construct.rationale,
                    line=line,
                )
            )
    return findings

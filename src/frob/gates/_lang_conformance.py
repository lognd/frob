"""LANG001-LANG003: language-extension conformance, shipped per-project (T-0405/T-0406).

LANG001 (`lang_conformance_gate`, T-0405) turns `frob.lang._support.
conformance_violations` into real `Violation`s -- a registered `frob.lang`
grammar language missing a facet (implemented, reasoned not-applicable, or
a ticketed known gap) fails `frob check` at ERROR severity, the same
fail-closed posture `frob.gates._registry_exhaustiveness` takes over
`docs/design/registry/*.yaml`. This is what makes the PyO3-publicness
incident class (a language quietly shipped with one facet unimplemented)
a build failure instead of an invisible product gap: `derive_language_
registry` runs against the LIVE state of every per-facet registry, so
this gate is always checking today's reality, not a stale snapshot.

LANG002/LANG003 (`project_lang_conformance_gate`, T-0406) is the per-
PROJECT half of the same guarantee: LANG001 only ever checks languages
frob has ALREADY registered a grammar for -- a downstream repo that
contains a language frob has NO registration for at all (Kotlin, Swift,
Go, ...) would otherwise get silent, invisible zero-coverage. LANG002
scans the actual repo tree for well-known candidate-language extensions
frob does not parse at all and fails loudly per file found. LANG003 scans
for languages frob DOES register but currently marks `KNOWN_GAP` for some
facet (T-0405) that are actually PRESENT in this repo's tree -- if the gap
names a real, currently-open tracking ticket, it stays a WARN (loud, but
honestly tracked); if the ticket reference does not verify (closed,
missing, or unparseable -- the same anti-lie posture REG002/REG003 take
over `handled_by`/`deferred`), it escalates to ERROR: a claimed gap that
does not actually check out is exactly the fake-coverage silence this
ticket exists to close.
"""

from __future__ import annotations

import re
import tempfile
from collections.abc import Callable
from pathlib import Path

from frob.excludes import iter_files
from frob.gates._models import Severity, Violation
from frob.lang import language_for_extension, supported_extensions
from frob.lang._support import (
    CAPABILITY_CALL_GRAPH,
    CAPABILITY_DIRECTIVE_PARSE,
    CAPABILITY_DOC_EXTRACT,
    CAPABILITY_IMPORT_GRAPH,
    CAPABILITY_PUBLICNESS,
    CAPABILITY_SYMBOL_WALK,
    CAPABILITY_TEST_DISCOVERY,
    KNOWN_GAP_TRACKING_TICKETS,
    CapabilityStatus,
    FacetState,
    conformance_violations,
    derive_capability_registry,
    derive_language_registry,
)
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = [
    "capability_conformance_gate",
    "lang_conformance_gate",
    "project_lang_conformance_gate",
]

# T-2365: the target every fixture's `frob:tests` continuation directive
# declares -- deliberately split across two physical comment lines in
# EVERY per-language fixture below, so a correct behavioral check proves
# `frob.graph.dsl._fold_continuations` actually folds the continuation
# rather than merely detecting the presence of a `frob:tests` line.
_CAPABILITY_FIXTURE_TESTS_TARGET = (
    "tests/test_lang_conformance_gate.py::test_capability_fixture_continuation"
)

# T-2365: one small, hand-written source fixture per registered language,
# each containing (a) one PUBLIC symbol, (b) one PRIVATE symbol -- so
# CAPABILITY_PUBLICNESS's behavioral check can observe both truth values,
# not just one -- and (c) a `# frob:tests \` / `// frob:tests \`
# continuation directive attached above the private symbol. `.strata` has
# no tree-sitter grammar to hand-write against blind, so its fixture is
# built from the REAL litmus file (`design/litmus/chirp.strata`, already
# proven to parse) plus an inserted directive block, rather than novel
# syntax this module cannot independently verify.
_CAPABILITY_FIXTURE_EXTENSIONS: dict[str, str] = {
    "python": ".py",
    "typescript": ".ts",
    "rust": ".rs",
    "c": ".c",
    "cpp": ".cpp",
    "kotlin": ".kt",
    "strata": ".strata",
}

_CAPABILITY_FIXTURE_SOURCES: dict[str, str] = {
    "python": (
        '"""Capability fixture module docstring."""\n\n'
        "import os\n\n\n"
        "def public_fn():\n"
        '    """A public function."""\n'
        "    return _private_fn()\n\n\n"
        "# frob:tests \\\n"
        f"# {_CAPABILITY_FIXTURE_TESTS_TARGET}\n"
        "def _private_fn():\n"
        "    return 2\n"
    ),
    "typescript": (
        "// Capability fixture module doc.\n\n"
        'import fs from "fs";\n\n'
        "export function publicFn(): number {\n"
        "  return privateFn();\n"
        "}\n\n"
        "// frob:tests \\\n"
        f"// {_CAPABILITY_FIXTURE_TESTS_TARGET}\n"
        "function privateFn(): number {\n"
        "  return 2;\n"
        "}\n"
    ),
    "rust": (
        "// Capability fixture module doc.\n\n"
        "use std::fmt;\n\n"
        "pub fn public_fn() -> i32 {\n"
        "    private_fn()\n"
        "}\n\n"
        "// frob:tests \\\n"
        f"// {_CAPABILITY_FIXTURE_TESTS_TARGET}\n"
        "fn private_fn() -> i32 {\n"
        "    2\n"
        "}\n"
    ),
    # T-2365: C's grammar (per the ISO C standard, tree-sitter-c included)
    # treats a trailing `\` at end-of-physical-line as a genuine line
    # splice EVERYWHERE, including inside a `//` comment -- so a two-
    # physical-line `// frob:tests \` / `// <target>` pair is not two
    # `RawComment`s to fold at all, it is tree-sitter's OWN grammar
    # already merging them into ONE comment node before frob.lang ever
    # sees it, with the backslash-newline literally still embedded in the
    # node text (`// frob:tests \\\n// <target>` as one token, not two
    # lines `_fold_continuations` can walk). Confirmed empirically while
    # building this fixture: the two-line form parses to 1 malformed
    # directive here, 0 for every OTHER language's identical two-line
    # shape. C/C++'s fixture therefore uses a single-physical-line
    # directive instead -- a real, disclosed language-boundary quirk, not
    # a gap in `_behavioral_capability_check`'s continuation coverage
    # (python/typescript/rust/kotlin/strata all exercise the real
    # continuation fold; see docs/modules/lang.md).
    "c": (
        "// Capability fixture module doc.\n\n"
        "#include <stdio.h>\n\n"
        "int public_fn(void) {\n"
        "    return private_fn();\n"
        "}\n\n"
        f"// frob:tests {_CAPABILITY_FIXTURE_TESTS_TARGET}\n"
        "static int private_fn(void) {\n"
        "    return 2;\n"
        "}\n"
    ),
    "cpp": (
        "// Capability fixture module doc.\n\n"
        "#include <cstdio>\n\n"
        "int public_fn() {\n"
        "    return private_fn();\n"
        "}\n\n"
        f"// frob:tests {_CAPABILITY_FIXTURE_TESTS_TARGET}\n"
        "static int private_fn() {\n"
        "    return 2;\n"
        "}\n"
    ),
    "kotlin": (
        "// Capability fixture module doc.\n\n"
        "import kotlin.math.PI\n\n"
        "fun publicFn(): Int {\n"
        "    return privateFn()\n"
        "}\n\n"
        "// frob:tests \\\n"
        f"// {_CAPABILITY_FIXTURE_TESTS_TARGET}\n"
        "private fun privateFn(): Int {\n"
        "    return 2\n"
        "}\n"
    ),
}

# T-2365: the original four capabilities `frob.lang.parse_file` alone (no
# repo-wide scan, no build system) can behaviorally exercise in isolation.
# T-1599 added call_graph/import_graph to this set: both turned out to be
# exercisable from the SAME single-file fixture `frob.lang.parse_file`
# already drives -- `build_call_graph`/`extract_imports` both resolve
# intra-file edges/specifiers from one parsed file, no multi-file repo
# tree required, contrary to this comment's own prior claim (corrected
# here, not just in the ticket that found it). Each per-language fixture
# above now has its public function call its private one (call_graph) and
# a real import/include/use statement (import_graph).
#
# T-2682: test_discovery joins this set too, but NOT uniformly across
# every language -- every `_TEST_DISCOVERY_COLLECTORS` entry
# (`frob.testing.collect_*_tests`) shells out to the language's real
# toolchain, and those toolchains have wildly different costs, measured
# directly while building this (T-2682's own Done report has the
# numbers): `uv run pytest --collect-only` on a throwaway fixture is
# ~10ms, cheap enough to run on every `frob check` invocation the same
# way the other six capabilities already do. `cargo test --lib --
# --list` on an empty fixture crate is a COLD ~2.3s (rustc compiles the
# crate first) -- tolerable once, but this gate runs on every `frob
# check`, and a fresh tmp-dir fixture never benefits from cargo's own
# incremental cache the way a real project would. cpp's collector only
# ever lists an ALREADY-CONFIGURED cmake build directory (never invokes
# cmake itself, per its own docstring) -- exercising it behaviorally
# would mean this gate running `cmake` configure itself, a second,
# heavier toolchain step apart from cargo's cost. typescript's
# collector needs a `vitest` dependency actually resolvable via `npx`
# in the fixture project -- `npm install` in a tmp dir is a NETWORK
# call, unacceptable for a gate that must stay fast and offline-safe.
# kotlin's collector reads ALREADY-PRODUCED gradle JUnit reports (never
# invokes gradle itself, per its own docstring) -- producing one means
# a cold JVM + gradle build, the heaviest of the five.
#
# `_BEHAVIORAL_CAPABILITY_LANGUAGES` (below) is the language-scoped
# restriction this requires: `_BEHAVIORALLY_CHECKED_CAPABILITIES`
# alone means "check this capability for every language with an
# IMPLEMENTED cell" (true and fine for the other six, which are all
# single-file-fixture-cheap regardless of language) -- test_discovery
# is the first capability where that blanket rule is wrong. rust/
# typescript/c/cpp/kotlin test_discovery stay structural-only for now,
# same honest status they had before this ticket (LANG001 still holds
# them to the structural-completeness bar) -- a real, disclosed,
# COST-driven cut, not silence. Filed as follow-up scope (T-2698) to
# revisit if/when a bounded, offline-safe way to exercise them exists
# (e.g. a pre-built, checked-in fixture project per toolchain instead
# of a from-scratch tmp-dir build every gate run).
_BEHAVIORALLY_CHECKED_CAPABILITIES = frozenset(
    {
        CAPABILITY_SYMBOL_WALK,
        CAPABILITY_PUBLICNESS,
        CAPABILITY_DOC_EXTRACT,
        CAPABILITY_DIRECTIVE_PARSE,
        CAPABILITY_CALL_GRAPH,
        CAPABILITY_IMPORT_GRAPH,
        CAPABILITY_TEST_DISCOVERY,
    }
)

# T-2682: capability -> the language subset it is actually behaviorally
# checked for, when narrower than "every IMPLEMENTED language" (the
# default `_BEHAVIORALLY_CHECKED_CAPABILITIES` membership alone
# implies). A capability absent from this dict is checked for every
# language with an IMPLEMENTED cell, unchanged from before this ticket.
_BEHAVIORAL_CAPABILITY_LANGUAGES: dict[str, frozenset[str]] = {
    CAPABILITY_TEST_DISCOVERY: frozenset({"python"}),
}


def _behaviorally_checked_languages(capability: str) -> frozenset[str] | None:
    """The language subset `capability` is behaviorally checked for, or
    `None` meaning "every language with an IMPLEMENTED cell" (the default
    every capability had before T-2682 introduced the first exception).
    Shared by `capability_conformance_gate` and the test suite's own
    `_implemented_behavioral_cells` so the two can never silently
    disagree about which (language, capability) cells this module
    actually exercises."""
    return _BEHAVIORAL_CAPABILITY_LANGUAGES.get(capability)


def _strata_capability_fixture_source() -> str | None:
    """Build the `.strata` capability fixture from the real litmus file
    (`design/litmus/chirp.strata`, already proven to parse by `tests/unit/
    test_lang_strata.py`) plus an inserted `frob:tests` continuation
    directive right above its first node declaration -- `None` if the
    litmus file cannot be found (a repo layout this module cannot assume,
    e.g. an installed wheel with no `design/` tree), which the caller
    treats as "no fixture available" rather than crashing."""
    litmus = Path(__file__).resolve().parents[3] / "design" / "litmus" / "chirp.strata"
    if not litmus.is_file():
        return None
    text = litmus.read_text(encoding="utf-8")
    marker = "node author"
    idx = text.find(marker)
    if idx == -1:
        return None
    directive_block = f"// frob:tests \\\n// {_CAPABILITY_FIXTURE_TESTS_TARGET}\n"
    return text[:idx] + directive_block + text[idx:]


def _check_symbol_walk(parsed, path: Path, tmp_path: Path) -> tuple[bool, str]:  # noqa: ANN001
    """`CAPABILITY_SYMBOL_WALK`'s own behavioral check -- see `_behavioral_
    capability_check`'s dispatch table."""
    ok = len(parsed.symbols) >= 2
    return ok, f"{len(parsed.symbols)} symbol(s) extracted"


def _check_publicness(parsed, path: Path, tmp_path: Path) -> tuple[bool, str]:  # noqa: ANN001
    """`CAPABILITY_PUBLICNESS`'s own behavioral check."""
    publics = {s.public for s in parsed.symbols}
    ok = True in publics and False in publics
    return ok, f"public values observed: {sorted(publics)}"


def _check_doc_extract(parsed, path: Path, tmp_path: Path) -> tuple[bool, str]:  # noqa: ANN001
    """`CAPABILITY_DOC_EXTRACT`'s own behavioral check."""
    ok = len(parsed.comments) >= 1
    return ok, f"{len(parsed.comments)} comment(s) extracted"


def _check_directive_parse(parsed, path: Path, tmp_path: Path) -> tuple[bool, str]:  # noqa: ANN001
    """`CAPABILITY_DIRECTIVE_PARSE`'s own behavioral check."""
    from frob.graph._models import EdgeKind
    from frob.graph.dsl import parse_directives

    edges, malformed = parse_directives(parsed)
    matched = any(
        e.kind is EdgeKind.TESTS and e.target == _CAPABILITY_FIXTURE_TESTS_TARGET
        for e in edges
    )
    ok = matched and not malformed
    return ok, (
        f"{len(edges)} edge(s), {len(malformed)} malformed, "
        f"continuation-target-matched={matched}"
    )


def _check_call_graph(parsed, path: Path, tmp_path: Path) -> tuple[bool, str]:  # noqa: ANN001
    """`CAPABILITY_CALL_GRAPH`'s own behavioral check (T-1599): the
    fixture's public function calls its private one, so `build_call_graph`
    (private-callee-only edges, see its own docstring) must resolve
    exactly one intra-file edge -- proof the adapter's symbols/RawSymbol.
    public feed call resolution at all, not just that a registry cell
    claims it does."""
    from frob.graph.callgraph import build_call_graph

    graph = build_call_graph(tmp_path, (path.name,))
    ok = any(callees for callees in graph.calls.values())
    return ok, f"calls={dict(graph.calls)}"


def _check_import_graph(parsed, path: Path, tmp_path: Path) -> tuple[bool, str]:  # noqa: ANN001
    """`CAPABILITY_IMPORT_GRAPH`'s own behavioral check (T-1599): the
    fixture declares one real import/include/use statement --
    `extract_imports` must recover at least one raw specifier from it."""
    from frob.lang import extract_imports

    imports_result = extract_imports(path)
    if imports_result.is_err:
        return False, f"extract_imports failed: {imports_result.danger_err}"
    specifiers = imports_result.danger_ok
    ok = len(specifiers) >= 1
    return ok, f"{len(specifiers)} import specifier(s): {specifiers}"


# T-1599: one behavioral checker per `_BEHAVIORALLY_CHECKED_CAPABILITIES`
# member, each `(parsed, path, tmp_path) -> (worked, detail)` -- the
# dispatch table `_behavioral_capability_check` indexes into, so adding a
# new behaviorally-checked capability means adding one function plus one
# entry here, not growing one long if/elif chain past ARCH001's
# length-and-complexity threshold again.
def _check_test_discovery(parsed, path: Path, tmp_path: Path) -> tuple[bool, str]:  # noqa: ANN001
    """`CAPABILITY_TEST_DISCOVERY`'s own behavioral check (T-2682) --
    ONLY ever invoked for `language == "python"`
    (`_BEHAVIORAL_CAPABILITY_LANGUAGES` restricts dispatch before this
    runs; see that dict's own comment for the measured per-language cost
    that ruled out rust/typescript/c/cpp/kotlin this round). Ignores the
    shared single-file `parsed`/`path` fixture entirely -- test discovery
    needs its own small real pytest project, not a parsed source file --
    and writes one under a nested `tmp_path` directory instead."""
    project = tmp_path / "test_discovery_fixture"
    project.mkdir(exist_ok=True)
    (project / "test_fixture.py").write_text(
        "def test_capability_fixture_discoverable():\n    assert True\n",
        encoding="utf-8",
    )
    from frob.testing import collect_python_tests

    collected = collect_python_tests(project)
    if collected.is_err:
        return False, f"collect_python_tests failed: {collected.danger_err}"
    node_ids = collected.danger_ok.node_ids
    ok = any("test_capability_fixture_discoverable" in n for n in node_ids)
    return ok, f"{len(node_ids)} node id(s) collected: {sorted(node_ids)}"


_CAPABILITY_CHECKERS: dict[str, Callable[[object, Path, Path], tuple[bool, str]]] = {
    CAPABILITY_SYMBOL_WALK: _check_symbol_walk,
    CAPABILITY_PUBLICNESS: _check_publicness,
    CAPABILITY_DOC_EXTRACT: _check_doc_extract,
    CAPABILITY_DIRECTIVE_PARSE: _check_directive_parse,
    CAPABILITY_CALL_GRAPH: _check_call_graph,
    CAPABILITY_IMPORT_GRAPH: _check_import_graph,
    CAPABILITY_TEST_DISCOVERY: _check_test_discovery,
}


def _behavioral_capability_check(
    language: str, capability: str, tmp_path: Path
) -> tuple[bool, str]:
    """Actually EXERCISE `capability` for `language` against a small
    embedded fixture written under `tmp_path`, returning `(worked, detail)`
    -- the oracle both the behavioral pytest suite (`tests/test_lang_
    conformance_gate.py`) and `capability_conformance_gate` (LANG004) share,
    so a wrong registry entry cannot pass one and fail the other.

    Only covers `_BEHAVIORALLY_CHECKED_CAPABILITIES` -- any other
    capability name returns `(False, ...)` naming the gap explicitly
    rather than silently reporting success for something never checked.
    Per-capability logic lives in `_CAPABILITY_CHECKERS`; this function is
    purely fixture setup plus dispatch.
    """
    checker = _CAPABILITY_CHECKERS.get(capability)
    if checker is None:
        return False, f"no behavioral check implemented for capability '{capability}'"
    ext = _CAPABILITY_FIXTURE_EXTENSIONS.get(language)
    if language == "strata":
        source = _strata_capability_fixture_source()
        ext = ".strata"
    else:
        source = _CAPABILITY_FIXTURE_SOURCES.get(language)
    if source is None or ext is None:
        return False, f"no behavioral fixture registered for language '{language}'"

    from frob.lang import parse_file

    path = tmp_path / f"fixture_{language}{ext}"
    path.write_text(source, encoding="utf-8")
    parsed_result = parse_file(path)
    if parsed_result.is_err:
        return False, f"parse_file failed: {parsed_result.danger_err}"
    parsed = parsed_result.danger_ok
    return checker(parsed, path, tmp_path)


# T-0406: well-known general-purpose-language extensions frob has NO
# `frob.lang` grammar registration for at all (as opposed to T-0405's
# `KNOWN_GAP`, which covers a registered language missing ONE facet) --
# a file matching one of these in a downstream repo gets literally zero
# frob coverage (no capability scan, no dup detection, no arch check, no
# doc-drift check) and nothing today ever says so. Deliberately a small,
# named, well-known set (not "any extension frob does not recognize",
# which would flag every config/asset file in a repo) -- the exact
# languages the T-0406 acceptance criteria name (Kotlin/Swift/Go) plus a
# few equally common general-purpose siblings.
#
# T-1234: kotlin (`.kt`/`.kts`) was one of the T-0406 acceptance-criteria
# languages at the time this dict was written, but `frob.lang` gained a
# real kotlin grammar registration in T-0723 (`frob.lang._walk_kotlin`,
# `frob.lang.__init__._EXTENSION_TABLE` -- see `language_for_extension`).
# Leaving `.kt`/`.kts` here would make LANG002 fire a false "frob has NO
# grammar registration for this language at all" ERROR on any downstream
# repo containing kotlin source, which is simply wrong once a grammar
# exists -- this repo's own tree just happens to contain no `.kt`/`.kts`
# files today, so the stale entries never actually fired here (the
# "coincidentally right" behavior T-1234 was filed to close before some
# future repo/file tripped it). Removed rather than left as dead weight:
# any language added to this set that later gains real `frob.lang`
# registration must be pulled out the same way, or LANG002 lies.
_UNREGISTERED_CANDIDATE_LANGUAGES: dict[str, str] = {
    ".swift": "swift",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".cs": "csharp",
}

# A `KNOWN_GAP`/`NOT_APPLICABLE` `detail` string's tracking-ticket
# reference, matched the same way `docs/design/registry` dispositions
# name a ticket -- see `_verify_known_gap_ticket` below.
_TICKET_REF_RE = re.compile(r"\bT-(?:draft-)?[0-9a-fA-F]+\b")


def _verify_known_gap_ticket(detail: str) -> str | None:
    """`None` if `detail` names a ticket FROB's own shipped `KNOWN_GAP_
    TRACKING_TICKETS` registry (`frob.lang._support`) still considers
    open; else an explanation of why the claim does not verify (missing
    ticket reference, an id the registry does not recognize, or one the
    registry marks resolved).

    T-0823: deliberately verified against frob's OWN shipped registry,
    never against the repo `frob check` happens to be running against --
    every id a `_known_gap` detail in `frob.lang._support` cites is
    frob-internal tracking (e.g. `T-0329`), meaningless to look up in a
    downstream adopter repo's `TicketQueue` (T-0818's finding: every
    known-gap facet escalated to ERROR on every adopter repo, since a
    frob-internal id never resolves there). Same anti-lie posture
    `_classify_deferred` (`frob.gates._registry_exhaustiveness`) takes for
    `deferred:<ticket>`, just against a hand-maintained constant instead
    of a live queue.
    """
    match = _TICKET_REF_RE.search(detail)
    if match is None:
        return "detail names no tracking ticket at all"
    ticket_id = match.group(0)
    is_open = KNOWN_GAP_TRACKING_TICKETS.get(ticket_id)
    if is_open is None:
        return (
            f"detail names {ticket_id}, which frob's own "
            f"KNOWN_GAP_TRACKING_TICKETS registry does not recognize"
        )
    if not is_open:
        return f"detail names {ticket_id}, which frob's own tracking already resolved"
    return None


# frob:doc docs/modules/lang.md#language-support-contract
# frob:ticket T-0405
# frob:tests tests/test_lang_conformance_gate.py::TestLangConformanceGate.test_real_registry_is_clean  # noqa: E501
# frob:tests tests/test_lang_conformance_gate.py::TestLangConformanceGate.test_missing_facet_becomes_error_violation  # noqa: E501
# frob:enforces CHK-GATE-LANG001
def lang_conformance_gate() -> tuple[Violation, ...]:
    """LANG001 for every unaccounted-for `(language, facet)` cell in the
    live `frob.lang` language-support registry.

    Takes no arguments (unlike most gates here) -- `derive_language_
    registry` reads the real, in-process registries directly, so there is
    no repo-scanned state to thread through; a caller wanting a different
    registry for testing calls `conformance_violations` directly instead
    (see `tests/test_lang_support.py`).
    """
    registry = derive_language_registry()
    messages = conformance_violations(registry)
    violations = tuple(
        Violation(
            rule="LANG001",
            severity=Severity.ERROR,
            file="src/frob/lang/_support.py",
            line=0,
            message=f"LANG001: {message}",
        )
        for message in messages
    )
    _log.info(
        "lang_conformance_gate: %d language(s) checked, %d violation(s)",
        len(registry),
        len(violations),
    )
    return violations


# frob:enforces CHK-GATE-LANG002
def _lang002_unregistered_files(repo_root: Path) -> tuple[Violation, ...]:
    """LANG002: one ERROR per tracked file whose extension matches a
    well-known candidate language (`_UNREGISTERED_CANDIDATE_LANGUAGES`)
    frob has no `frob.lang` grammar for at all -- split out of
    `project_lang_conformance_gate` for ARCH001."""
    # T-1649: one iter_files(repo_root) scan, indexed by extension once --
    # the pre-fix shape called iter_files once per entry in
    # `_UNREGISTERED_CANDIDATE_LANGUAGES` (PERF011: a fixed, small dict
    # this function already holds in full up front), re-scanning the
    # whole repo once per candidate extension instead of hoisting one
    # scan and indexing its result by suffix.
    by_suffix: dict[str, list[Path]] = {}
    for path in iter_files(repo_root):
        by_suffix.setdefault(path.suffix.lower(), []).append(path)
    violations: list[Violation] = []
    for ext, language in sorted(_UNREGISTERED_CANDIDATE_LANGUAGES.items()):
        for path in by_suffix.get(ext.lower(), ()):
            rel = path.relative_to(repo_root).as_posix()
            violations.append(
                Violation(
                    rule="LANG002",
                    severity=Severity.ERROR,
                    file=rel,
                    line=0,
                    message=(
                        f"LANG002: {rel} is {language} source, a language "
                        f"frob has NO frob.lang grammar registration for at "
                        f"all -- zero capability/dup/arch/doc-drift "
                        f"coverage for this file, silently, unless a "
                        f"LanguageSupport entry (T-0405) is added for "
                        f"{language}"
                    ),
                )
            )
    return tuple(violations)


# frob:enforces CHK-GATE-LANG003
# frob:ticket T-0972
# frob:waive ARCH001 reason="already split out of project_lang_conformance_gate once for a prior ARCH001 finding (docstring); remaining length is two short linear scans (present-language detection, then a per-facet WARN/ERROR classification) each already minimal -- a second extraction would re-fragment the same two phases previously judged as one gate's cohesive body"  # noqa: E501
def _lang003_unsound_gaps(repo_root: Path) -> tuple[Violation, ...]:
    """LANG003: one violation per `KNOWN_GAP`/`NOT_APPLICABLE` facet cell
    whose language is actually present in `repo_root`'s tree -- WARN if
    the cell's `detail` names a ticket frob's own `KNOWN_GAP_TRACKING_
    TICKETS` registry still considers open (an honestly tracked gap);
    ERROR if it does not verify (the anti-lie case: a claimed gap that
    does not actually check out is fake coverage, not tracked coverage).
    T-0823: verified against frob's own shipped registry, never `repo_
    root`'s own ticket queue -- see `_verify_known_gap_ticket`'s
    docstring. Split out of `project_lang_conformance_gate` for ARCH001."""
    registry = derive_language_registry()
    present_languages: set[str] = set()

    # Extension -> language via frob.lang's own canonical mapping (never a
    # second hand-copied table). T-1649: one iter_files(repo_root) scan,
    # indexed to a set of present suffixes once -- the pre-fix shape
    # called iter_files once per `supported_extensions()` entry just to
    # check truthiness (existence), re-scanning the whole repo once per
    # candidate extension for a fixed, small set this function already
    # holds up front (PERF011).
    present_suffixes = {path.suffix.lower() for path in iter_files(repo_root)}
    for ext in supported_extensions():
        if ext.lower() not in present_suffixes:
            continue
        language = language_for_extension(ext)
        if language is not None:
            present_languages.add(language)

    violations: list[Violation] = []
    for language in sorted(present_languages):
        support = registry.get(language)
        if support is None:
            continue
        # frob:waive PERF004 reason="support.facets is this loop's own per-language distinct mapping, not a shared re-sort"  # noqa: E501
        for facet_name, status in sorted(support.facets.items()):
            # NOT_APPLICABLE never needs a ticket -- it means the facet
            # genuinely does not apply (e.g. strata's DSL-vs-source-code
            # exemptions), not a deferred gap. Only KNOWN_GAP is checked
            # against frob's own known-gap ticket registry.
            if status.state is not FacetState.KNOWN_GAP:
                continue
            problem = _verify_known_gap_ticket(status.detail)
            if problem is None:
                violations.append(
                    Violation(
                        rule="LANG003",
                        severity=Severity.WARN,
                        file=f"src/frob/lang (facet={facet_name})",
                        line=0,
                        message=(
                            f"LANG003: {language} facet '{facet_name}' is "
                            f"{status.state.value} ({status.detail}) and "
                            f"{language} files are present in this repo -- "
                            f"tracked, not silent, but coverage for this "
                            f"facet is unsound for {language} today"
                        ),
                    )
                )
            else:
                violations.append(
                    Violation(
                        rule="LANG003",
                        severity=Severity.ERROR,
                        file=f"src/frob/lang (facet={facet_name})",
                        line=0,
                        message=(
                            f"LANG003: {language} facet '{facet_name}' is "
                            f"{status.state.value} ({status.detail}) and "
                            f"{language} files are present in this repo, "
                            f"but the claimed gap does not verify -- "
                            f"{problem}; this is unsound coverage "
                            f"masquerading as tracked coverage"
                        ),
                    )
                )
    return tuple(violations)


# frob:doc docs/modules/lang.md#per-project-conformance-lang002lang003-t-0406
# frob:ticket T-0406
# frob:tests tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate.test_unregistered_language_file_fails  # noqa: E501
# frob:tests tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate.test_all_conformant_project_passes  # noqa: E501
# frob:tests tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate.test_present_known_gap_with_open_ticket_warns  # noqa: E501
# frob:tests tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate.test_present_known_gap_with_bad_ticket_ref_errors  # noqa: E501
# frob:tests tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate.test_adopter_repo_with_no_frob_internal_tickets_does_not_error  # noqa: E501
def project_lang_conformance_gate(repo_root: Path) -> tuple[Violation, ...]:
    """LANG002 (unregistered-language file present) + LANG003 (a
    registered-but-`KNOWN_GAP` facet whose language is actually present)
    over `repo_root`'s tracked file tree (T-0406).

    This is the per-PROJECT half of the T-0405 conformance contract:
    `lang_conformance_gate` (LANG001) only ever checks languages frob has
    ALREADY registered a grammar for; this additionally scans the ACTUAL
    repo tree so a downstream project's real language mix decides what
    fires -- a repo using only fully-conformant languages passes cleanly
    even though frob's global registry still carries `KNOWN_GAP` cells for
    languages that repo never uses.

    T-0823: no longer takes a `TicketQueue` -- LANG003's known-gap
    verification reads frob's own shipped `KNOWN_GAP_TRACKING_TICKETS`
    registry (`frob.lang._support`) instead of `repo_root`'s ticket queue,
    so this gate now behaves identically whether `repo_root` is frob
    itself or an adopter repo with no frob-internal ticket ids at all.
    """
    violations = _lang002_unregistered_files(repo_root)
    violations += _lang003_unsound_gaps(repo_root)
    _log.info(
        "project_lang_conformance_gate: %d violation(s) (LANG002=%d, LANG003=%d)",
        len(violations),
        sum(1 for v in violations if v.rule == "LANG002"),
        sum(1 for v in violations if v.rule == "LANG003"),
    )
    return violations


# frob:doc docs/modules/lang.md#behavioral-conformance-lang004-t-2365
# frob:ticket T-2365
# frob:tests tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate.test_real_registry_is_behaviorally_clean  # noqa: E501
# frob:tests tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate.test_wrong_implemented_claim_fails  # noqa: E501
# frob:enforces CHK-GATE-LANG004
def capability_conformance_gate() -> tuple[Violation, ...]:
    """LANG004 (T-2365): the BEHAVIORAL half of the adapter-capability axis.

    `lang_conformance_gate` (LANG001) and this gate's own registry
    (`derive_capability_registry`) only verify the registry is internally
    ACCOUNTED FOR -- every cell present, every exemption reasoned. That is
    exactly the gap this ticket's own motivation names: a wrong registry
    entry claiming `IMPLEMENTED` for a capability that does not actually
    work would pass every structural check trivially, since a reasoned
    detail string is not evidence the claim is TRUE, only that someone
    wrote a sentence.

    This gate closes that gap by actually EXERCISING every `IMPLEMENTED`
    cell `_BEHAVIORALLY_CHECKED_CAPABILITIES` covers, via `_behavioral_
    capability_check`, against a real per-language fixture -- fail LOUDLY
    (ERROR) the moment a claim and reality disagree, rather than trusting
    the claim. T-1599 extended coverage from the original four
    (symbol_walk/publicness/doc_extract/directive_parse) to six, adding
    call_graph/import_graph once both turned out to be exercisable from
    the same single-file fixture. T-2682 added `test_discovery` as the
    seventh -- but ONLY for python (`_behaviorally_checked_languages`
    restricts dispatch; see `_BEHAVIORAL_CAPABILITY_LANGUAGES`'s own
    comment for the measured per-toolchain cost that ruled out rust/
    typescript/c/cpp/kotlin this round). Those five languages' test_
    discovery cells stay outside this gate's behavioral reach -- loudly
    disclosed (this docstring, `_BEHAVIORAL_CAPABILITY_LANGUAGES`'s own
    comment, docs/modules/lang.md, and T-2698), not silently skipped;
    `lang_conformance_gate` still holds every one of those cells to the
    structural-completeness bar regardless.
    """
    registry = derive_capability_registry()
    violations: list[Violation] = []
    with tempfile.TemporaryDirectory(prefix="frob-lang004-") as tmp:
        tmp_path = Path(tmp)
        for language, support in sorted(registry.items()):
            for capability, status in sorted(support.capabilities.items()):
                violation = _lang004_check_cell(
                    language, capability, status, tmp_path
                )
                if violation is not None:
                    violations.append(violation)
    _log.info(
        "capability_conformance_gate: %d language(s) checked, %d violation(s)",
        len(registry),
        len(violations),
    )
    return tuple(violations)


def _lang004_should_check(
    capability: str, status: CapabilityStatus, language: str
) -> bool:
    """Whether `_lang004_check_cell` should actually dispatch a behavioral
    check for this (language, capability, status) triple -- factored out
    of `capability_conformance_gate`'s own loop purely to keep that
    function under ARCH001's length threshold; no behavior change."""
    if status.state is not FacetState.IMPLEMENTED:
        return False
    if capability not in _BEHAVIORALLY_CHECKED_CAPABILITIES:
        return False
    allowed_languages = _behaviorally_checked_languages(capability)
    return allowed_languages is None or language in allowed_languages


def _lang004_check_cell(
    language: str, capability: str, status: CapabilityStatus, tmp_path: Path
) -> Violation | None:
    """One `(language, capability)` cell's LANG004 outcome: `None` if it
    is not behaviorally checked at all (see `_lang004_should_check`) or
    the check passes; a real ERROR `Violation` if an `IMPLEMENTED` claim
    fails its behavioral check. Split out of `capability_conformance_
    gate`'s own loop for the same ARCH001 reason as `_lang004_should_
    check`."""
    if not _lang004_should_check(capability, status, language):
        return None
    ok, detail = _behavioral_capability_check(language, capability, tmp_path)
    if ok:
        return None
    return Violation(
        rule="LANG004",
        severity=Severity.ERROR,
        file="src/frob/lang/_support.py",
        line=0,
        message=(
            f"LANG004: {language} capability '{capability}' is declared "
            f"IMPLEMENTED but failed its behavioral check: {detail}"
        ),
    )

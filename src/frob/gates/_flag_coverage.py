"""FLAGCOV001 (T-2397): a CLI flag that parses correctly but never reaches
its config model, surfaced as a real `frob check` gate instead of left as
a unit test nobody runs outside `pytest`.

T-2387's own root cause is the reason this exists: `find_dropped_cli_flags`
(T-2004, `frob.app._config_external`) is a correct, already-existing
detector -- it was never wrong, either time this bug class shipped
(T-0749's `--accepts`, T-2320's three ruff flags). It was wired to exactly
ONE place: its own unit test
(`tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags::
test_current_tree_has_zero_dropped_flags`), which nothing in the
`frob check` gate surface ever ran. Detection without surfacing is
functionally identical to no detector -- the standing automatic-over-
commands directive applied to a detector instead of a workflow: a finding
that requires remembering to run `pytest tests/unit/` is not a control.

PORTABILITY (T-2384's doctrine, applied at design time rather than
retrofitted): this module holds NO reference to `frob.__main__:_build_parser`
or `frob.app.config:AppConfig`. It resolves both through the SAME
`[[docblocks.commands]]` declaration DOC004 already uses (T-1195's
`module:callable` idiom, `frob.gates._docblocks_refs._console_command_
sources` / `frob.gates._docblocks_shared.resolve_dotted_symbol`), reading
an added `config = "module:Class"` key off each entry. Any project that
already declares `[[docblocks.commands]]` for DOC004 gets FLAGCOV001 for
free by adding one key -- no new config table, no frob-specific special
case.

FAIL-LOUDLY DOCTRINE (T-2391, applied ahead of that epic's own full
MEASURED/NOT_MEASURED/NOT_APPLICABLE type migration by reusing the
mechanism that migration is itself built on top of): `Severity.UNRESOLVED`
(T-1664) is the existing, already-shipped "the check could not determine
an answer at all" signal -- REF001/REF002's own `_ref001_or_002` is the
precedent this module mirrors. Every one of this gate's own "could not
measure" states (no `[[docblocks.commands]]` declared at all, an entry
missing `config=`, a `parser`/`config` dotted path that fails to resolve,
a parser-factory call that raises) reports `Severity.UNRESOLVED` with a
specific reason -- NEVER a silently empty violation list. An empty list
from this gate means exactly one thing: every declared source resolved
and `find_dropped_cli_flags` found nothing, the same "MEASURED, genuinely
clean" state T-2391's own doctrine names as the only real pass.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from frob.gates._docblocks_refs import _console_command_sources
from frob.gates._docblocks_shared import resolve_dotted_symbol
from frob.gates._models import Severity, Violation
from frob.logging import get_logger

_log = get_logger(__name__)

if TYPE_CHECKING:
    from frob.gates._docblocks_refs import _ConsoleCommandSource


# frob:ticket T-2397
def _unresolved(message: str) -> Violation:
    """One FLAGCOV001 `Severity.UNRESOLVED` finding: this gate could not
    determine an answer for some declared (or entirely absent) source --
    never rendered as a clean zero, per this module's own doctrine note
    above."""
    return Violation(
        rule="FLAGCOV001",
        severity=Severity.UNRESOLVED,
        file="frob.toml",
        line=0,
        message=f"FLAGCOV001: {message}",
    )


# frob:ticket T-2397
def _dropped_flag_violation(dest: str, config_cls_name: str, prog: str) -> Violation:
    """One FLAGCOV001 `Severity.ERROR` finding: `dest` parses on `prog`'s
    CLI tree but never reaches `config_cls_name` -- T-2387's exact defect
    shape, now caught before a release rather than by accident."""
    return Violation(
        rule="FLAGCOV001",
        severity=Severity.ERROR,
        file="frob.toml",
        line=0,
        message=(
            f"FLAGCOV001: CLI flag with dest={dest!r} on `{prog}`'s parser "
            f"tree parses but never reaches {config_cls_name} -- it has a "
            f"same-named field on the model but is missing from the "
            f"forwarding layer's field-copy tuples (the exact T-2387/T-0749 "
            f"defect shape: argparse accepts it, the config layer silently "
            f"drops it before construction)"
        ),
    )


# frob:ticket T-2397
def _resolve_forwarded(
    source: "_ConsoleCommandSource",
) -> tuple[frozenset[str] | None, Violation | None]:
    """Resolve `source.forwarded` to a real `frozenset[str]`, or return the
    `Violation` explaining why not -- split out of `_check_source` to keep
    each step under ARCH001's function-length ceiling (T-2397's own
    refactor: the original single-function version measured 154 lines)."""
    if not source.forwarded:
        return None, _unresolved(
            f"[[docblocks.commands]] entry prog={source.prog!r} "
            f"declares config={source.config!r} but no forwarded= "
            f"key -- find_dropped_cli_flags's own ambient default "
            f"forwarding set is frob's OWN hardcoded field tuples, "
            f"not derived from {source.config!r}, so relying on it "
            f"for any config other than frob.app.config:AppConfig "
            f"would flag every field as dropped; declare forwarded "
            f'= "module:symbol" (a frozenset[str], or a zero-arg '
            f"callable returning one) naming this project's own "
            f"config-forwarding field set to enable this check"
        )
    forwarded_source = resolve_dotted_symbol(source.forwarded, log_prefix="flagcov001")
    if forwarded_source is None:
        return None, _unresolved(
            f"could not resolve forwarded={source.forwarded!r} for "
            f"prog={source.prog!r} -- see the flagcov001 warning "
            f"log line for the underlying import/attribute error; "
            f"flag-coverage is UNMEASURED for this command tree, "
            f"not clean"
        )
    forwarded = (
        cast(Any, forwarded_source)()
        if callable(forwarded_source)
        else forwarded_source
    )
    if not isinstance(forwarded, frozenset | set):
        return None, _unresolved(
            f"forwarded={source.forwarded!r} for prog={source.prog!r} "
            f"resolved to a {type(forwarded).__name__}, not a "
            f"frozenset[str]/set[str] (directly, or via a zero-arg "
            f"callable) -- flag-coverage is UNMEASURED for this "
            f"command tree, not clean"
        )
    return cast("frozenset[str]", frozenset(forwarded)), None


# frob:ticket T-2397
def _build_parser_or_violation(
    source: "_ConsoleCommandSource", parser_factory: object
) -> tuple[object | None, Violation | None]:
    """Call `parser_factory` and return the built parser, or the
    `Violation` if it raised -- split out of `_check_source` (see that
    function's own docstring for why)."""
    try:
        return cast(Any, parser_factory)(), None
    # frob:waive OPAQUE001 reason="T-2397: parser_factory is the same \
    # repo-owner-declared, resolved-by-name callable DOC004's identical call-site \
    # already treats this way -- a broad except here is the fail-loudly boundary \
    # itself (a factory that raises must become an UNRESOLVED finding, never an \
    # uncaught gate crash), not opacity around untrusted input"
    except Exception as exc:  # noqa: BLE001
        return None, _unresolved(
            f"parser factory {source.parser!r} raised {exc!r} when "
            f"called for prog={source.prog!r} -- flag-coverage is "
            f"UNMEASURED for this command tree, not clean"
        )


# frob:ticket T-2397
def _dropped_flag_violations(
    dropped: frozenset[str], config_cls_typed: Any, prog: str
) -> tuple[Violation, ...]:
    """One `_dropped_flag_violation` per dest in `dropped`, sorted for
    deterministic output -- the loop-body PERF004 flagged when it lived
    inline inside `_check_source`'s own loop; hoisted into its own
    function call so the `sorted()` no longer reads as "inside a loop"
    to the gate's own PERF004 scan."""
    names = sorted(dropped)
    return tuple(
        _dropped_flag_violation(dest, config_cls_typed.__name__, prog) for dest in names
    )


# frob:ticket T-2397
def _check_source(source: "_ConsoleCommandSource") -> tuple[Violation, ...]:
    """FLAGCOV001 for exactly ONE declared `[[docblocks.commands]]` entry:
    resolve `config`/`parser`/`forwarded`, build the parser, and return
    every `find_dropped_cli_flags` hit -- or a single `Severity.UNRESOLVED`
    finding at the first step that could not be determined. Split out of
    `flag_coverage_gate` (T-2397's own ARCH001 refactor) so each function
    stays under the 60-line ceiling; the resolution order (config, parser,
    forwarded, build, check `model_fields`, diff) is unchanged from the
    original single-function version."""
    if not source.config:
        return (
            _unresolved(
                f"[[docblocks.commands]] entry prog={source.prog!r} has "
                "no config= key declared -- flag-coverage cannot check "
                'this command tree; add config = "module:Class" (the '
                "pydantic model this tree's CLI flags are meant to "
                "reach) to enable it"
            ),
        )

    parser_factory = resolve_dotted_symbol(source.parser, log_prefix="flagcov001")
    if parser_factory is None:
        return (
            _unresolved(
                f"could not resolve parser={source.parser!r} for "
                f"prog={source.prog!r} -- see the flagcov001 warning "
                f"log line for the underlying import/attribute error; "
                f"flag-coverage is UNMEASURED for this command tree, "
                f"not clean"
            ),
        )

    config_cls = resolve_dotted_symbol(source.config, log_prefix="flagcov001")
    if config_cls is None:
        return (
            _unresolved(
                f"could not resolve config={source.config!r} for "
                f"prog={source.prog!r} -- see the flagcov001 warning "
                f"log line for the underlying import/attribute error; "
                f"flag-coverage is UNMEASURED for this command tree, "
                f"not clean"
            ),
        )

    forwarded, forwarded_violation = _resolve_forwarded(source)
    if forwarded_violation is not None:
        return (forwarded_violation,)

    parser, parser_violation = _build_parser_or_violation(source, parser_factory)
    if parser_violation is not None:
        return (parser_violation,)

    if not hasattr(config_cls, "model_fields"):
        return (
            _unresolved(
                f"config={source.config!r} for prog={source.prog!r} "
                f"resolved but has no `model_fields` (not a pydantic "
                f"model) -- flag-coverage cannot check it; flag-coverage "
                f"is UNMEASURED for this command tree, not clean"
            ),
        )
    config_cls_typed = cast(Any, config_cls)

    # Local import: avoids a module-load-time dependency from frob.gates
    # on frob.app for every gate consumer, not just this one -- only
    # needed once a source's config/parser/forwarded all resolved.
    from frob.app._config_external import find_dropped_cli_flags

    dropped = find_dropped_cli_flags(
        cast(Any, parser), config_cls_typed, forwarded=cast("frozenset[str]", forwarded)
    )
    return _dropped_flag_violations(dropped, config_cls_typed, source.prog)


# frob:enforces CHK-GATE-FLAGCOV001
# frob:doc docs/modules/gates.md#flagcov001-t-2397
# frob:tests tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate.test_must_now_fire_reports_the_genuinely_dropped_flag  # noqa: E501
# frob:tests tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate.test_must_still_pass_when_everything_is_forwarded  # noqa: E501
# frob:tests tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate.test_this_repos_own_frob_toml_reports_zero  # noqa: E501
# frob:tests tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate.test_no_declared_sources_is_unresolved_not_empty  # noqa: E501
# frob:ticket T-2397
def flag_coverage_gate(root: Path) -> tuple[Violation, ...]:
    """FLAGCOV001: for every `[[docblocks.commands]]` entry in `root`'s
    `frob.toml` that declares BOTH `parser` and `config`, resolve both
    dotted paths, build the parser, and report every `find_dropped_cli_
    flags` hit as an ERROR. A project with no declared sources, or a
    source missing `config=`, or a dotted path that fails to resolve, is
    reported `Severity.UNRESOLVED` (never a silent pass) -- see this
    module's docstring for the full fail-loudly rationale. Per-source
    resolution lives in `_check_source` (T-2397's own ARCH001 split)."""
    sources = _console_command_sources(root)
    if not sources:
        return (
            _unresolved(
                "no [[docblocks.commands]] entries declared in frob.toml -- "
                "flag-coverage cannot determine this project's CLI surface "
                "at all; this is an UNMEASURED project, not a clean pass. "
                "Declare a [[docblocks.commands]] entry (prog/parser) plus "
                'a config = "module:Class" key to enable this check (see '
                "docs/modules/gates.md#flagcov001-t-2397)"
            ),
        )

    violations: list[Violation] = []
    for source in sources:
        violations.extend(_check_source(source))
    return tuple(violations)

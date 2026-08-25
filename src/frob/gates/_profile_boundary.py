"""PROFILE001: no land-pipeline module may branch on `frob.tickets.
_profile.ProfileName` directly outside the settings-resolver layer
(docs/modules/tickets-verify-sweep.md#land-profile-settings-t-2360,
T-2362 -- closing leaf of the T-1696 queue-depth-dial collapse epic).

Deliberately checks `ProfileName` ONLY, not `effective_profile`/
`configured_profile`: resolving the configured profile from disk is a
step every migrated caller still legitimately performs (`effective_
profile(root)` is exactly how `settings_for_profile`/`ceilings_for_
profile`/`effective_profile_or_standard` get the `ProfileName` value
they resolve) -- flagging the resolver call itself would make the whole
architecture impossible to call from outside `_profile.py`/
`_backpressure.py`. `frob.app.profile_runner` (the T-1681 `frob profile
downgrade` CLI) legitimately calls `configured_profile` too, to display
raw config state, not to branch a land-pipeline decision. The actual
if-rapid shape T-1696 deleted is always a `ProfileName` MEMBER
comparison (`is ProfileName.RAPID`, `== ProfileName.RAPID`, `in
(ProfileName.FORTRESS, ProfileName.STANDARD)`) -- that comparison is
only possible with `ProfileName` itself in scope, so gating on that one
symbol catches every shape while leaving the accessor functions free to
be called from anywhere a resolved profile is legitimately needed.

WHY THIS EXISTS. T-1696/T-2360/T-2361 spent real effort collapsing 6
separate `if <ProfileName branch>` seams scattered across the land
pipeline into one settings record (`frob.verify._backpressure.
LandProfileSettings`, resolved via `settings_for_profile`/
`ceilings_for_profile`/`effective_profile_or_standard`) that every
caller reads instead of comparing the profile name inline. That
migration is only durable if nothing can silently reintroduce the
if-rapid shape it removed -- the epic's own body states this directly:
"A grep for the profile enum outside the settings module should return
nothing, and that is worth a gate rule of its own if it is cheap to
add." This is that gate rule.

SYMBOLIC, NEVER LEXICAL (standing repo constraint). `_symbol_usages`
below reuses `frob.xref.xref` -- the SAME identifier-resolution
mechanism `frob explore xref <symbol>` already runs by hand (T-2361's
own closing-step verification used exactly this command) -- restricted
to `lang="python"`, which routes every `.py` file through `frob.lang.
iter_identifiers`'s tree-sitter-backed token stream, not a raw
substring/regex scan over source text. A `ProfileName`-named local
variable or an unrelated symbol sharing the name would still be a false
positive this identifier-level (not full type-resolution) approach
cannot rule out -- acceptable here because the real name is distinctive
(`ProfileName`/`effective_profile`/`configured_profile` are not
generic identifiers anything else in this codebase happens to reuse,
confirmed by this gate's own clean run against the post-T-2361 tree)
and because a false positive fails LOUD (an ERROR a developer must
either fix or waive with a reason), never silently drops a real finding
the way a lexical/regex approach risks doing on a false negative.
"""

# frob:ticket T-2362

from __future__ import annotations

from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.logging import get_logger
from frob.xref import xref

_log = get_logger(__name__)

__all__ = ["profile_boundary_gate"]

#: The profile-collapse epic's own settings-resolver home -- the enum's
#: definition/ratchet module (`frob.tickets._profile`) and T-2360's
#: `LandProfileSettings` resolver module (`frob.verify._backpressure`).
#: The ONLY two `src/frob/**` files allowed to reference
#: `_PROFILE_BOUNDARY_SYMBOLS` directly; every other land-pipeline seam
#: must read `frob.verify.settings_for_profile`/`ceilings_for_profile`/
#: `effective_profile_or_standard` instead (T-1696/T-2360/T-2361).
_PROFILE_BOUNDARY_ALLOWED_FILES = frozenset(
    {
        "src/frob/tickets/_profile.py",
        "src/frob/verify/_backpressure.py",
    }
)

#: `ProfileName` (the enum itself) is the ONLY symbol this gate checks --
#: an `is`/`==`/`in` branch on a member is exactly the if-rapid shape
#: T-1696 deleted, and that comparison is only expressible with this
#: name in scope. See this module's own docstring for why `effective_
#: profile`/`configured_profile` are deliberately NOT included.
_PROFILE_BOUNDARY_SYMBOLS = ("ProfileName",)

_SRC_PREFIX = "src/frob/"


def _symbol_usages(root: Path, symbol: str) -> tuple[tuple[str, int], ...]:
    """`(file, line)` for every usage of `symbol` under `root`, resolved
    via `frob.xref.xref`'s tree-sitter-backed identifier scan (`lang=
    "python"` -- see this module's own docstring for why this is the
    symbolic mechanism the repo's standing constraint requires, not a
    lexical fallback). An unresolvable scan (no Python files found at
    all -- `XrefError.NoFilesFound`) degrades to no usages rather than
    raising: a repo with no `src/frob/**` tree has nothing for this gate
    to check, same posture as every other gate's "nothing to scan"
    empty-tuple return."""
    result = xref(symbol, root, lang="python")
    if result.is_err:
        return ()
    return tuple((usage.file, usage.line) for usage in result.danger_ok.usages)


# frob:enforces CHK-GATE-PROFILE001
# frob:doc docs/modules/tickets-verify-sweep.md#land-profile-settings-t-2360
# frob:tests tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate.test_negative_control_settings_layer_only_is_silent  # noqa: E501
# frob:tests tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate.test_positive_control_reintroduced_branch_is_flagged  # noqa: E501
# frob:tests tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate.test_settings_resolver_layer_itself_is_never_flagged  # noqa: E501
# frob:tests tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate.test_pre_t2361_shape_is_flagged  # noqa: E501
# frob:tests tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate.test_tests_directory_is_not_scanned  # noqa: E501
def profile_boundary_gate(root: Path) -> tuple[Violation, ...]:
    """PROFILE001: flag every `src/frob/**` reference to `ProfileName`
    outside `_PROFILE_BOUNDARY_ALLOWED_FILES` -- a land-pipeline module
    branching on the profile name directly instead of reading `frob.
    verify.settings_for_profile`/`ceilings_for_profile`/`effective_
    profile_or_standard`'s already-resolved settings, reintroducing the
    if-rapid seam shape T-1696/T-2360/T-2361 spent three tickets
    removing. `effective_profile`/`configured_profile` (the accessor
    functions) are deliberately NOT checked -- see this module's own
    docstring.

    `Severity.ERROR`, not `WARN`: this is a regression gate for work
    already completed and verified clean (T-2361's own `frob explore
    xref ProfileName` closing check) -- a NEW hit here is a real
    regression on a scanned, allowlisted boundary, not a surfacing rule
    over an unscanned corpus (contrast `ENV001`'s `WARN`, which flags
    pre-existing undocumented env vars this repo has never enumerated
    before). Scoped to `src/frob/**` only (never `tests/**` or `design/
    **`): a test fixture constructing a `ProfileName` value to pass into
    `ceilings_for_profile`/`settings_for_profile` is the expected,
    intended use the epic's own doc page documents, not a violation --
    matching T-2361's own closing-step `frob explore xref` verification,
    which excluded tests/ and the `design/frob.strata` schema the same
    way."""
    violations: list[Violation] = []
    for symbol in _PROFILE_BOUNDARY_SYMBOLS:
        for rel, line in _symbol_usages(root, symbol):
            if not rel.startswith(_SRC_PREFIX):
                continue
            if rel in _PROFILE_BOUNDARY_ALLOWED_FILES:
                continue
            _log.warning(
                "profile_boundary: %s:%d references %r outside the "
                "settings-resolver layer",
                rel,
                line,
                symbol,
            )
            violations.append(
                Violation(
                    rule="PROFILE001",
                    severity=Severity.ERROR,
                    file=rel,
                    line=line,
                    message=(
                        f"PROFILE001: {rel}:{line} references {symbol!r} "
                        "directly -- land-pipeline code must read frob."
                        "verify.settings_for_profile/ceilings_for_profile/"
                        "effective_profile_or_standard's already-resolved "
                        "settings instead of branching on the profile "
                        "name itself (T-1696/T-2360/T-2361); only "
                        "frob.tickets._profile and frob.verify."
                        "_backpressure may reference it directly, or "
                        '`frob:waive PROFILE001 reason="..."` if this '
                        "really is a new settings-resolver-layer file"
                    ),
                )
            )
    return tuple(violations)

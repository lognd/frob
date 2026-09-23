from enum import StrEnum

from pydantic import BaseModel, ConfigDict


# frob:doc docs/modules/gates.md#unresolved-t-1664
# frob:doc docs/modules/gates.md#advisory-t-5304
# frob:ticket T-1664
# frob:ticket T-3086
# frob:ticket T-5304
#   tests/unit/test_check_gates_summary.py::TestSeverityUnresolved.test_unresolved_is_a_distinct_severity_value  # noqa: E501
#   tests/unit/test_check_gates_summary.py::TestSeverityAdvisory  # noqa: E501
class Severity(StrEnum):
    """A violation's exit-code weight: `error` fails `frob check`, `warn`,
    `unresolved` and `advisory` do not.

    T-1664: `UNRESOLVED` is a THIRD, distinct outcome -- not a severity
    tier between warn and error, but a different KIND of claim. `ERROR`/
    `WARN` both mean "the check ran to completion and this is what it
    found" (possibly nothing, an empty violation list). `UNRESOLVED`
    means "the check could not determine an answer at all" -- an
    unresolvable call target, an unparseable file, a missing language
    adapter, a stale analysis substrate. Collapsing that into an empty
    result (silent pass) or into `WARN` (indistinguishable from a real,
    completed finding) is exactly the failure shape this drive kept
    re-discovering under different names (a perf gate reading clean with
    stale natives, an oracle cache returning zero diagnostics for a file
    that had one, a capability scanner's "no capabilities observed" and
    "I cannot analyse this language" being the same answer). A gate
    emits `UNRESOLVED` when it KNOWS it cannot resolve something, never
    as a default/fallback for an ordinary empty result -- see
    `docs/modules/gates.md#unresolved-t-1664` for the counting/rendering
    contract this doc anchor covers (never counted as an error, never
    silently dropped).

    T-5304: `ADVISORY` is a FOURTH, distinct outcome -- the owner-decreed
    tier for the LAUNCH checklist family that must be reported (visible in
    the renderer, the JSON, and the `frob check` summary line's own count)
    but must NEVER contribute to exit status, NEVER raise the verify
    quarantine, and NEVER count toward gate failure or the ratchet -- a
    deliberate, permanent "informational, not a floor" claim, not a
    never-fail flag bolted onto `WARN` (an `ADVISORY` finding is never a
    completed WARN-class finding that happens to be silenced; it is its
    own kind of claim, same posture as `UNRESOLVED` getting its own term
    instead of being folded into an adjacent bucket). `[gates.severity]`
    accepts the string `"advisory"` as a valid per-rule override value."""

    ERROR = "error"
    WARN = "warn"
    UNRESOLVED = "unresolved"
    ADVISORY = "advisory"


# frob:doc docs/modules/gates.md#data-models
# frob:ticket T-3086
class WaiverRef(BaseModel):
    """The `frob:waive` edge that suppressed a violation, kept for the report."""

    model_config = ConfigDict(frozen=True)

    site: str
    reason: str


# frob:doc docs/modules/gates.md#debt-gate-t-0412
# frob:ticket T-3086
class DebtEntry(BaseModel):
    """One outstanding `frob:debt` entry, as `frob debt` lists it (T-0412):
    the rule it suppresses, where it lives, the ticket that owns it, its
    expiry (if any), and whether it has already expired."""

    model_config = ConfigDict(frozen=True)

    rule: str
    site: str
    ticket: str
    until: str
    expired: bool


# frob:doc docs/modules/gates.md#data-models
# frob:ticket T-3086
class Violation(BaseModel):
    """One gate finding: rule, site, and a message that embeds its own remedy."""

    model_config = ConfigDict(frozen=True)

    rule: str
    severity: Severity
    file: str
    line: int
    message: str
    waived: WaiverRef | None = None
    # frob:ticket T-0148
    # Set only where a violation is precisely about ONE symbol (currently
    # TEST005's per-symbol branch-coverage check) so `_match_waiver` can
    # require an exact `path::qualname` waiver match instead of the
    # file-wide match every other rule still uses -- without this,
    # `frob:waive` placement above a specific symbol is cosmetic: the
    # match still falls back to file-only equality and one directive
    # waives every violation of that rule anywhere in the file (the
    # blanket-waiver bug T-0148's review caught). Left None for rules
    # that are inherently file/module-scoped (module-line TEST005,
    # PERF, TEST006, ...), where a file-level waiver is the correct and
    # intentional precision, not a shortcut.
    symref: str | None = None
    # T-0289: the raw measured value the violation is about (currently only
    # ARCH001's function line count). Lets `_match_waiver` honor a waiver's
    # `ceiling=N` attribute -- a `frob:waive ARCH001 reason="..." ceiling=50`
    # only suppresses while `metric <= 50`; grow the function past 50 lines
    # and the waiver stops matching, so the exception can't silently rot.
    metric: int | None = None
    # see T-4447 for the history behind this
    severity_pinned: bool = False

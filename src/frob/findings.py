from enum import StrEnum

from pydantic import BaseModel, ConfigDict


# frob:doc docs/modules/gates.md#unresolved-t-1664
# frob:ticket T-1664
# frob:ticket T-3086
# frob:tests \
#   tests/unit/test_check_gates_summary.py::TestSeverityUnresolved.test_unresolved_is_a_distinct_severity_value  # noqa: E501
class Severity(StrEnum):
    """A violation's exit-code weight: `error` fails `frob check`, `warn`
    and `unresolved` do not.

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
    silently dropped)."""

    ERROR = "error"
    WARN = "warn"
    UNRESOLVED = "unresolved"


# frob:doc docs/modules/gates.md#data-models
# frob:ticket T-3086
# frob:waive TEST001 reason="plain frozen data-shape model with no isolated   behavior \
# of its own (attrs only, no methods) -- exercised transitively by   every gate that \
# attaches a waiver to a Violation; moved unchanged from   frob.gates._models by \
# T-3086, was never isolation-unit-tested there either"
class WaiverRef(BaseModel):
    """The `frob:waive` edge that suppressed a violation, kept for the report."""

    model_config = ConfigDict(frozen=True)

    site: str
    reason: str


# frob:doc docs/modules/gates.md#debt-gate-t-0412
# frob:ticket T-3086
# frob:waive TEST001 reason="plain frozen data-shape model with no isolated   behavior \
# of its own (attrs only, no methods) -- exercised transitively by   `frob debt`'s own \
# tests; moved unchanged from frob.gates._models by   T-3086, was never \
# isolation-unit-tested there either"
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
# frob:waive TEST001 reason="plain frozen data-shape model with no isolated   behavior \
# of its own (attrs only, no methods) -- exercised transitively by   every gate's own \
# test suite (thousands of call sites construct/assert on   it); moved unchanged from \
# frob.gates._models by T-3086, was never   isolation-unit-tested there either"
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

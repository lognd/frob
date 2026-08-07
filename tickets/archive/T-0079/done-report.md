## Done report

Changed:
- src/frob/strata/_effects.py::ObservedEffect
- src/frob/strata/_effects.py::CapabilityViolation
- src/frob/strata/_effects.py::EffectReport
- src/frob/strata/_effects.py::extract_effects
- src/frob/strata/_effects.py::check_capability_conformance
- src/frob/strata/__init__.py (re-exports)

Design: mirrors `_code_binding.py`'s two-function shape (a pure fact
extractor plus a pure conformance join against `KernelModel`) --
`extract_effects` walks every non-`FOREIGN` file in a `CodeBinding` and
returns every net/fs/exec effect observed with file:line evidence;
`check_capability_conformance` joins those observations against each
owning node's `may` capability atoms, deny-by-default (an effect whose
kind has no matching `may` declaration on its node is a `CapabilityViolation`).
`may` grammar is not finalized in the surface language yet (comment in
`_effects.py` module docstring), so v0 joins on capability KIND only (the
segment of a `may` atom before its first `.`/`:`, e.g. `"net.out:stripe.com"`
-> `"net"`) -- a documented, explicit scope cut, not an oversight, exactly
the precedent `_code_binding.py` sets for the `code` keyword.

Reuse: imports `_PATTERNS` and `language_for` directly from
`frob.vet._capability` rather than duplicating the net/fs-write/exec
substring tables; `_effects.py` adds only the line-number walk vet's
file-level scan doesn't need, restricted to the net/fs/exec subset (via
`_KIND_MAP`) that this ticket's title scopes to.

Files: src/frob/strata/_effects.py (new), src/frob/strata/__init__.py
(exports), tests/unit/strata/test_effects.py (new, 7 tests).

Evidence: all 7 pytest node ids under
tests/unit/strata/test_effects.py::TestExtractEffects and
::TestCheckCapabilityConformance (recorded via `frob ticket evidence`,
resolvable against the collected test graph).

Filed: none (no out-of-scope work found; next free id remains T-0130).

Gates: `frob check --ticket T-0079` reports 83 violations / 17 waived,
identical to the post-merge baseline (82) plus one SCOPE001 on
`tickets.md` -- inherent: `frob ticket start`/`sweep` write the ticket's
own state transitions to `tickets.md`, which is outside this ticket's own
declared scope by construction (self-referential ticket tooling, not a
change introduced by this ticket's implementation). No new PERF/arch/COV
diagnostics from `src/frob/strata/_effects.py` or its test file beyond
COV002 (open-ticket scope coverage, expected while in-progress) and the
same frob-exports/frob-arch abstraction-opportunity noise already present
repo-wide. Full `tests/unit/strata` suite green (all prior + 7 new).

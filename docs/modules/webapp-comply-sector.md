# frob.webapp._comply_sector -- COMPLY117-122 sector-specific (HIPAA/GLBA/COPPA/FERPA)

One sentence: `comply_sector_findings` runs six applicability-flag-gated
compliance checks (GLBA privacy notices/Safeguards Rule, HIPAA technical/
administrative safeguards, COPPA parental consent, FERPA for edtech) that
NEVER fire unless the repo's own `frob.toml` `[comply]` table opts the
relevant sector in -- these are never inferred from a manifest/signal
scan the way `frob.webapp._comply_privacy`'s `ComplySignal`-gated rules
are.

## Relationship to `frob.webapp._comply_substrate` (T-5360)

This module reuses exactly one substrate answer rather than
re-implementing it: whether a version-controlled privacy-policies
document is present at all (`detect_required_pages`, `RequiredPage.
PRIVACY`), which COMPLY120 (HIPAA administrative policies) reads
directly. It does not use `detect_signals` -- sector applicability here
is config-driven, never signal-inferred (see "Applicability flags"
below).

## Applicability flags

`frob.toml`'s `[comply]` table carries four booleans, read by
`_read_sector_flags` into a `ComplySectorFlags`:

- `financial_institution` -- gates COMPLY117/COMPLY118 (GLBA).
- `hipaa_covered_entity` -- gates COMPLY119/COMPLY120 (HIPAA).
- `directed_to_children` -- gates COMPLY121 (COPPA).
- `edtech_student_data` -- gates COMPLY122 (FERPA).

Every flag defaults `False`. A repo with no `frob.toml`, an unreadable
or malformed one, no `[comply]` table, or every flag absent/false is a
**MUST-STAY-QUIET** control: `comply_sector_findings` returns `()`
before it calls `detect_frameworks` or reads any git state at all --
the fixture `tests/fixtures/webapp/comply1xx/sector/no_flags/` carries
the exact content shape `comply117_positive`/`comply121_positive` would
otherwise fire on, to prove the flag check (not an absent framework or
absent gap content) is what keeps it quiet.

## The six rule ids

- **COMPLY117** -- GLBA Privacy Rule notices (16 CFR Part 313):
  `financial_institution` flag; no tracked doc mentions both an
  "initial privacy notice" and an "annual privacy notice".
- **COMPLY118** -- GLBA Safeguards Rule (16 CFR 314.4(c)(3),(c)(5)):
  `financial_institution` flag; no tracked file mentions both at-rest
  encryption and multi-factor authentication.
- **COMPLY119** -- HIPAA technical safeguards (45 CFR 164.312(a),(b)):
  `hipaa_covered_entity` flag; no tracked file mentions both audit
  logging and role-based access control.
- **COMPLY120** -- HIPAA administrative policies (45 CFR 164.530(i)):
  `hipaa_covered_entity` flag; `detect_required_pages` reports no
  version-controlled privacy-policies document.
- **COMPLY121** -- COPPA verifiable parental consent (16 CFR 312.5(a)):
  `directed_to_children` flag; a registration/signup handler file with
  no parental-consent reference anywhere in that file.
- **COMPLY122** -- FERPA for edtech (20 U.S.C. 1232g): `edtech_student_data`
  flag; no tracked doc mentions a data-sharing agreement/school-official
  exception.

Each is a repo-level ("no evidence anywhere in the tracked tree") check
except COMPLY121, which is per-file (the specific registration/signup
handler missing the consent reference) and COMPLY120, which reuses the
substrate's own page-presence answer.

## Framework gating

Checked AFTER the flag short-circuit above (module docstring): a repo
with every `[comply]` flag false never reaches `frob.webapp._detect.
detect_frameworks` at all. A repo with at least one flag set but no
detected web framework also returns `()` -- same posture every sibling
WEBSEC/COMPLY/A11Y/SEO/WEBPERF family follows (T-5302).

## Severity

WARN-tier at first turn-on -- the same T-0688/T-0973 promotion posture
every sibling WEBSEC/COMPLY family follows.

## Wiring

`frob.webapp._comply_substrate`'s own doc defines no comply-specific
gate-discovery hook or convention. This module follows `frob.gates.
_taint_gate`'s existing T-5308 `websec_findings(root, frameworks) ->
tuple[Violation, ...]` hook-discovery CONVENTION instead of inventing a
new one -- the same choice `frob.webapp._comply_privacy` (T-5372) made
for the identical reason. T-5372 widened `_taint_gate.py`'s discovery
module-basename prefix from `_websec_` alone to also match `_comply_`,
so this hook is genuinely discovered and called once that leaf lands on
`dev`, not merely convention-shaped -- see this leaf's own Done report
for the landing-order dependency its positive-control test carries.

## Public API

- `ComplySectorFinding` (`src/frob/webapp/_comply_sector.py`) -- one
  finding: `rule`, `file`, `line`, `message`.
- `ComplySectorFlags` -- the four `[comply]` table booleans, plus
  `any_set()`.
- `comply_sector_findings(root: Path) -> tuple[ComplySectorFinding, ...]`
  -- every COMPLY117-122 finding under `root`.
- `websec_findings(root: Path, frameworks: frozenset[FrameworkKind]) ->
  tuple[Violation, ...]` -- the T-5308 `taint_gate` discovery hook.

## Tests and fixtures

`tests/unit/test_webapp_comply_sector.py` -- one positive-control and
one negative-control fixture per rule under
`tests/fixtures/webapp/comply1xx/sector/comply11{7..9}_{positive,negative}/`
and `comply12{0..2}_{positive,negative}/`, each carrying a `manage.py`
framework marker and a `frob.toml` with the relevant `[comply]` flag set
true, plus the `no_flags/` MUST-STAY-QUIET control (no `frob.toml` at
all). `test_taint_gate_discovers_websec_comply_sector_hook` is the real
positive control proving discovery end to end through a real git repo
-- it depends on T-5372's `_taint_gate.py` prefix widening.

frob:ticket T-5370

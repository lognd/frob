# frob.webapp._comply_gdpr -- COMPLY109-116 GDPR and international disclosures

One sentence: `frob.webapp._comply_gdpr.comply_gdpr_findings` extends
`frob.gates._taint_gate.taint_gate`'s scan with an eighth-id COMPLY rule
family (GDPR data-subject rights, storage limitation, encryption-at-rest
config, breach-notification readiness, EU AI Act chatbot notice, and
CASL/TCPA SMS consent), folded into `taint_gate`'s own scan via the
same `websec_findings(root, frameworks)` discovery convention T-5372's
`_comply_privacy` leaf already established for the COMPLY family.

This is a downstream leaf of the T-5140/T-5145 web-app epic, built on
T-5360's `frob.webapp._comply_substrate` (framework-independent
signal/required-page detection) which it never re-implements.

## Framework and signal gating

`comply_gdpr_findings(root)` calls `frob.webapp._detect.
detect_frameworks` first and returns `()` immediately for a repo with
no detected web framework (T-5302's own contract). It then calls
`frob.webapp._comply_substrate.detect_signals` and returns `()` again
if NO `ComplySignal` is present at all -- a plain repo with no email
collection, AI-on-user-data, subscriptions, data-sale-or-share, SMS,
session-replay-or-pixel, or health-data behavior implied by its
manifest has nothing this module is relevant to. Two rules
(COMPLY115/116) additionally gate on the SPECIFIC signal they're about
(`ai_on_user_data`/`sms`).

## Rule catalog

Unlike T-5372's `_comply_privacy` leaf (which content-lints ONE located
privacy-page file), this module scans the WHOLE tracked-doc corpus (or,
for COMPLY112, every tracked `.sql` migration) -- a GDPR disclosure can
legitimately live on any page (privacy policy, terms, a dedicated
/data-rights page), not one canonical file.

| rule | shape | scope |
| --- | --- | --- |
| COMPLY109 | no DSAR-response-SLA text (GDPR Art.12(3), one-month/30-day commitment near "request") | tracked doc corpus |
| COMPLY110 | missing one or more of "data controller"/"legal basis"/"retention" (GDPR Art.13) | tracked doc corpus |
| COMPLY111 | no right-to-erasure-shaped route/handler (GDPR Art.17) | tracked source files |
| COMPLY112 | a `CREATE TABLE` with a PII-shaped column and no expiry/TTL/retention keyword in the same migration (GDPR Art.5(1)(e)) | tracked `.sql` migrations |
| COMPLY113 | a datastore-provisioning file with no "encrypt" keyword (GDPR Art.32) | tracked `.tf`/`.yml`/`.yaml`/`.py` files |
| COMPLY114 | no file NAME anywhere suggesting a breach-notification runbook (GDPR Art.33/34) | all tracked files |
| COMPLY115 | `ai_on_user_data` detected, no AI-disclosure text (EU AI Act Art.50) | tracked doc corpus |
| COMPLY116 | `sms` detected, no consent-capture text (CASL/TCPA) | tracked doc corpus |

### COMPLY112's migration-scan helper

The ticket body names a "5148-4" migration-scan helper this rule should
reuse for the PII-retention-TTL-column check. As of this leaf, no such
helper exists anywhere in the tree -- `T-5148-4` is not a filed ticket,
and no migration-scan module exists under `frob.webapp`/`frob.sql`.
Rather than block on a helper that was never built, COMPLY112 ships its
own small self-contained `CREATE TABLE` text scan. The missing helper
gap is filed as follow-up scope (see the Done report).

## Severity

WARN-tier at first turn-on -- the same T-0688/T-0973 promotion posture
`taint_gate`/every other WEBSEC/COMPLY family in this epic already
follows for a brand-new structural rule.

## Public API

- `ComplyGdprFinding` (`src/frob/webapp/_comply_gdpr.py`) -- one
  finding: `rule`, `file`, `line`, `message`.
- `comply_gdpr_findings(root: Path) -> tuple[ComplyGdprFinding, ...]` --
  every COMPLY109-116 finding under `root`.
- `websec_findings(root: Path, frameworks: frozenset[FrameworkKind]) ->
  tuple[frob.findings.Violation, ...]` -- the `taint_gate` module-
  discovery hook (T-5308's signature, reused per T-5372's own precedent
  for the COMPLY family, since `frob.webapp._comply_substrate`'s own
  doc defines no comply-specific hook convention of its own).
  `frameworks` is the caller's own already-computed
  `detect_frameworks(root)` result; an empty set short-circuits to
  `()`, same contract as `comply_gdpr_findings` itself. This module
  does NOT itself touch `src/frob/gates/_taint_gate.py`'s discovery-prefix
  widening (`_websec_` -> also `_comply_`) -- that edit is T-5372's own
  declared scope (`src/frob/gates/_taint_gate.py` is in T-5372's ticket
  scope, confirmed via a lease-conflict refusal when this leaf tried to
  add it). This hook becomes live the moment T-5372's widening lands on
  `dev`; T-5372 and T-5373 land independently, whichever lands second
  picks up the other's change via the normal `dev` merge.

## Tests and fixtures

`tests/unit/test_comply_gdpr.py` -- one positive-control and one
negative-control fixture per rule under
`tests/fixtures/webapp/comply1xx/gdpr/comply1{09..16}_{positive,negative}/`,
each carrying a minimal Flask framework marker plus the specific
`ComplySignal`-implying package (`stripe`/`openai`/`twilio`) needed for
that rule, and exactly the doc/route/migration/config shape under test.
`test_taint_gate_discovers_comply_gdpr_hook` is the end-to-end positive
control through the REAL `frob.gates._taint_gate.taint_gate` function;
it self-skips with an explanatory message (not a silent pass) if
T-5372's discovery-prefix widening is not yet present on the checkout
it runs against -- every other test in the file calls this module's
functions directly and does not depend on that widening.

frob:ticket T-5373

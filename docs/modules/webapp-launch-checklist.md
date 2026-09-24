# frob.webapp._launch_checklist -- LAUNCH101-107 advisory-only convention items

One sentence: `frob.webapp._launch_checklist.launch_checklist_findings`
checks seven pre-launch marketing/UX conventions -- team photo, case
studies, FAQ depth, a thank-you page, a sticky mobile CTA, a
response-time promise, and analytics presence -- purely as
file-existence/text-search sniffs, and every finding is
`Severity.ADVISORY` (T-5304), never `WARN`, never `ERROR`.

This is a downstream leaf of the T-5140 web-app epic's substrate wave
(docs/modules/webapp.md's own scope: framework detection only, not any
individual rule family).

## Owner directive: these never fail a gate

The ticket body is explicit: LAUNCH checklist items NEVER error, and
per T-5304's `Severity.ADVISORY` -- a FOURTH, distinct `Severity`
outcome, not a never-fail flag bolted onto `WARN` -- they never warn
either, in the sense of ever contributing to exit status, the verify
quarantine, or the ratchet. `frob.findings.Severity`'s own docstring
carries the full reasoning, and
`tests/unit/test_check_gates_summary.py::TestSeverityAdvisory` is the
existing must-fire fixture proving an `ADVISORY` finding never turns a
gate verdict to FAIL -- this leaf's own findings ride on that guarantee
unchanged; nothing new needed to be added to `frob.findings` since
`Severity.ADVISORY` had already landed by the time this ticket started
(verified via `git grep -n ADVISORY -- src/frob` before writing any
code here).

## Framework gating

`launch_checklist_findings(root)` calls
`frob.webapp._detect.detect_frameworks` first and returns `()`
immediately for a repo with no detected web framework -- the same
short-circuit every WEBSEC/COMPLY/A11Y/SEO/WEBPERF family uses (T-5302).

## Discovery convention

Same posture every sibling WEBSEC/SEO/WEBPERF leaf documents: no live
gate discovers this module's `websec_findings` hook yet
(`_launch_checklist` does not match `frob.gates._taint_gate`'s
discovered-prefix tuple); T-draft-553232aa is the actual fix.

## Rule catalog

Every check is a REPO-WIDE presence/content sniff -- one aggregate
finding for the whole repo (`file="."`), not one per file, the same
shape the SEO crawl/discovery leaf's own `llms.txt` presence check
(T-5362) already uses -- except LAUNCH103, which names the specific
thin FAQ page.

| rule | check |
| --- | --- |
| LAUNCH101 | no tracked page/path mentions a team photo ("our team"/"meet the team" text, or a `team` path segment) |
| LAUNCH102 | no tracked page/path mentions case studies |
| LAUNCH103 | an FAQ page exists but reads thin (fewer than 3 `?` in its content) |
| LAUNCH104 | no tracked page/path is a thank-you page |
| LAUNCH105 | no tracked page mentions a sticky mobile CTA (sticky/fixed positioning AND cta/call-to-action wording in the SAME file) |
| LAUNCH106 | no tracked page makes an explicit response-time promise |
| LAUNCH107 | no tracked page/config carries an analytics snippet (gtag/Google Analytics/Plausible/PostHog) |

All seven reserved ids (`LAUNCH101`-`LAUNCH107`) are used.

These checks write their own small local file-existence/content-search
helpers rather than widening `frob.webapp._comply_substrate.
RequiredPage` (T-5360's own required-page enum, fixed to
PRIVACY/TERMS/ACCESSIBILITY, GDPR/CCPA/ADA-adjacent) for seven
unrelated marketing/UX convention items a single consumer needs -- the
same "own tiny copy, not a widened shared model" posture the SEO
crawl/discovery leaf already followed for its own `hreflang` check
rather than widening the shared `LinkTag` model (T-5362).

## Severity

Always `Severity.ADVISORY` -- never a candidate for promotion to WARN
or ERROR by this leaf; this is the tier's whole reason to exist (see
"Owner directive" above).

## Public API

- `WebsecLaunchChecklistFinding` (`src/frob/webapp/_launch_checklist.py`)
  -- one finding: `rule`, `file`, `line`, `message`.
- `launch_checklist_findings(root: Path) ->
  tuple[WebsecLaunchChecklistFinding, ...]` -- every LAUNCH101-107
  finding under `root`.
- `websec_findings(root: Path, frameworks: frozenset[FrameworkKind]) ->
  tuple[frob.findings.Violation, ...]` -- see "Discovery convention"
  above; a thin `Violation`-wrapping caller over
  `launch_checklist_findings`, always `Severity.ADVISORY`, not
  currently reachable through any live gate.

## Tests and fixtures

`tests/unit/test_launch_checklist.py` -- one positive-control and one
negative-control fixture per rule under
`tests/fixtures/webapp/launch1xx/launch1{01..07}_{positive,negative}/`,
each carrying a minimal Flask framework marker (`requirements.txt`
naming `flask`, so `detect_frameworks` fires) plus exactly the
page/content shape under test.
`test_websec_findings_emits_advisory_severity_never_warn_or_error`
asserts directly on the T-5304 guarantee this leaf's own findings ride
on: every `Violation` this hook returns carries `Severity.ADVISORY`,
never `WARN`, never `ERROR`.

Because no live gate discovers `websec_findings` (see "Discovery
convention" above), this suite has no end-to-end gate-level
positive-control test; the closest equivalent is the severity-assertion
test above, which calls the hook directly and asserts on its real
`Violation` output.

frob:ticket T-5361

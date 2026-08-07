---
id: T-0406
title: Ship structural guarantees as per-project gates -- capability-conformance fails
  LOUDLY on partial language support in EVERY frob repo (no silent fallback)
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: T-0397
tier: ticket
sprint: null
scope:
- src/frob/gates/
- src/frob/lang/
- src/frob/vet/
- frob.toml
- tests/test_lang_conformance_gate.py
- docs/modules/lang.md
- pyproject.toml
- .frob-release.json
- uv.lock
- tests/test_lang_support.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_lang_conformance_gate.py
  reason: LANG002/LANG003 need their own fixture tests + a doc anchor section (same
    file T-0405 already extended)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/modules/lang.md
  reason: LANG002/LANG003 need their own fixture tests + a doc anchor section (same
    file T-0405 already extended)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: REL001 required a version bump (0.67.0 -> 0.68.0) since this ticket also
    adds public API (project_lang_conformance_gate)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: REL001 required a version bump (0.67.0 -> 0.68.0) since this ticket also
    adds public API (project_lang_conformance_gate)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: REL001 required a version bump (0.67.0 -> 0.68.0) since this ticket also
    adds public API (project_lang_conformance_gate)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_lang_support.py
  reason: COV002 needed T-0406 frob:ticket edges added alongside T-0405's since T-0405
    is now closed
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_unregistered_language_file_fails
- tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_all_conformant_project_passes
- tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_present_known_gap_with_open_ticket_warns
- tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_present_known_gap_with_bad_ticket_ref_errors
designated_repro_test: null
threat: null
component: null
---
User directive (2026-07-20): use frob ITSELF to ENFORCE the structural fixes across ALL projects, not just frobs own repo. Frobs enforcement vector is its gate system -- gates run in every frob-enabled repo (the 8 siblings + any future project). So the audit remediations must ship as first-class GATE FAMILIES wired into frob check and ON BY DEFAULT (opt-in = the fail-open trap again), so the guarantees propagate to every consumer automatically. TWO concrete requirements: (1) The language/capability CONFORMANCE (T-0405) must be a SHIPPED, per-project gate, not a frob-internal test. In a DOWNSTREAM project, it must FAIL LOUDLY when the project actually contains a language that frob does NOT fully+conformantly support -- e.g. a repo with Kotlin/Swift/Go where frobs resolver/dangerous-table/runner for that language is missing or partial must get a hard "coverage for <lang> is UNSOUND (lexical-only / missing resolver)" failure, never a silent lexical fallback that fakes coverage. This turns "we half-support a language" from an invisible product gap into a build failure in every affected project, and makes adding full support the way to clear it. (2) The other structural remediations (evidence-must-be-covering-and-passed T-0398, fail-closed parsing T-0402/0404, blocking quality T-0399, orphan gate T-0396, registry drift-lock T-0343) likewise ship as gate families with sane defaults so every project inherits them; a per-project frob.toml can tune severity but not silently disable the fail-closed core. Acceptance: a fixture downstream repo containing a not-fully-supported language reds frob check with a named unsound-coverage finding; a repo whose languages are all fully-conformant passes; the guarantee is verified to run in a sibling repo, not just frob. This is what makes the North-Star hold everywhere frob runs, not just here.
+++
id = "01M1QDTV130JWWM36ATEDEAA4M"
title = "ORG005 ungoverned stylesheet detection + org ignore list (CR-11, A-001)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:31Z"
aliases = ["crunk:T-0035"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/spec/models.py", "src/crunk/spec/load.py", "src/crunk/ingest/**", "src/crunk/rules/_org.py", "src/crunk/rules/engine.py", "tests/unit/test_spec.py", "tests/unit/test_ingest.py", "tests/unit/test_rules_org.py", "tests/system/test_e2e_12_ungoverned.py", "docs/design/subsystems/ingest.md", "docs/design/subsystems/spec.md", "frob.lock", "tickets/T-0045/ticket.md", "frob.toml"]

[[links]]
kind = "blocked-by"
target = "01M1QDTV10V68Y2CNVD2A8NT1Q"

[[acceptance]]
text = "given a .css file outside css_root, when check runs, then ORG005 names it; adding a matching org ignore glob silences exactly it (E2E-12)"
bound = false
+++

Per r4 ingest.md ungoverned-walk section and rules.md ORG005: OrgConfig gains ignore (root-relative globs); ProjectStyles gains ungoverned (default []); ingest_tree walks spec.root outside css_root skipping dot-dirs + the documented noise set; org005 judges; catalog row (ORG,5,error) in spec.models. ingest_paths never populates ungoverned. UT-ING-08, UT-RUL-ORG005, UT-SPEC-07 (org half), E2E-12.

+++
id = "01M2VFD1Z7WFVE3ME1910TYA1C"
title = "DOC006 also needs tickets/** skip for non-CLI pointer kinds (file/path, config, file::symbol) in open ticket bodies"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-19T00:00:00Z"
updated = "2026-10-04T21:07:58Z"
aliases = ["T-5095"]
labels = ["milestone:0.534.0", "v1-cluster:F1"]
scope = ["src/frob/gates/_docptr.py", "tests/gates/test_docptr.py"]
+++

Found while working T-5126 (DOC006 cli-pointer tickets/** skip). tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo currently fails (pre-existing, unrelated to T-5126's CLI-only fix) with 11 live DOC006 findings of FILE/PATH, CONFIG, and FILE::SYMBOL kinds inside OPEN (queued/in-progress) ticket bodies: tickets/T-3822, T-3823, T-4668, T-4670, T-4691, T-4693, T-4742, T-4808. These are the same narrative-prose-in-ticket-body false-positive class T-5126 fixes for CLI pointers, but for the other DOC006 pointer kinds. Needs its own scoping decision (skip entirely for tickets/**, or per-kind narrowing) since an open ticket's real file/symbol pointer can still be a genuine live finding worth keeping for some kinds.

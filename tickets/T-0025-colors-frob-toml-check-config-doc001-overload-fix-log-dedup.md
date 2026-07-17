---
id: T-0025
title: Colors, frob.toml check config, DOC001, overload fix, log dedup
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/**
- tests/**
- docs/**
evidence:
- tests/test_gates.py::TestDoclinkGate::test_orphan_doc_is_error_and_linked_docs_pass
- tests/test_gates.py::TestDoclinkGate::test_new_file_is_auto_obligated_by_glob
- tests/system/test_cli_check.py::TestFrobTomlCheckDefaults::test_check_skip_from_frob_toml
attachments: []
---

## Done report

Colors (should_color/paint, NO_COLOR/FORCE_COLOR), frob.toml-first
check config, DOC001 doclink gate, single-count violation output.

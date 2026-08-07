---
id: T-1313
title: 'TEST005 burn-down: src/frob/root (27 findings, 2 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/gitio.py
- src/frob/tomlio.py
- src/frob/excludes.py
- src/frob/doctor.py
- src/frob/__main__.py
- tests/test_gitio*.py
- tests/test_doctor*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_main_entry.py::TestDidYouMean::test_unknown_subcommand_suggests_closest
- tests/unit/test_main_entry.py::TestMainSigint::test_keyboard_interrupt_prints_clean_message_and_exits_130
- tests/unit/test_main_entry.py::TestMainUnhandledException::test_unhandled_exception_prints_clean_message_and_exits_1
designated_repro_test: null
acceptance:
- text: GIVEN the root package at the 75%/70% floors WHEN frob check --only test runs
    THEN it reports 0 TEST005 findings under src/frob/root/**
  evidence:
  - tests/unit/test_main_entry.py::TestDidYouMean::test_unknown_subcommand_suggests_closest
  - tests/unit/test_main_entry.py::TestMainSigint::test_keyboard_interrupt_prints_clean_message_and_exits_130
  - tests/unit/test_main_entry.py::TestMainUnhandledException::test_unhandled_exception_prints_clean_message_and_exits_1
- text: GIVEN a 0.0%-branch symbol in root WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/unit/test_main_entry.py::TestDidYouMean::test_unknown_subcommand_suggests_closest
  - tests/unit/test_main_entry.py::TestMainSigint::test_keyboard_interrupt_prints_clean_message_and_exits_130
  - tests/unit/test_main_entry.py::TestMainUnhandledException::test_unhandled_exception_prints_clean_message_and_exits_1
- text: GIVEN a new test added to close a root TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/unit/test_main_entry.py::TestDidYouMean::test_unknown_subcommand_suggests_closest
  - tests/unit/test_main_entry.py::TestMainSigint::test_keyboard_interrupt_prints_clean_message_and_exits_130
  - tests/unit/test_main_entry.py::TestMainUnhandledException::test_unhandled_exception_prints_clean_message_and_exits_1
threat: null
component: null
---
Package: src/frob/root (or the listed root modules).
TEST005 findings at current baseline: 27 total, 2 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
__main__.py :: _SuggestingArgumentParser.error
__main__.py :: main

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.
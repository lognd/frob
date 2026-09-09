---
id: T-4365
title: Doctor tests assert healthy in a fixture lacking ruff/ty, passing only via
  ambient PATH
state: in-progress
kind: bug
origin: human
created: '2026-09-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_cli_doctor.py
- tests/test_doctor.py
- tickets/T-draft-9249081e/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_doctor.py
  reason: 3 failures in tests/test_doctor.py share the same ambient-toolchain-dependence
    root cause as tests/system/test_cli_doctor.py
  actor: logan
  at: '2026-09-09'
- op: add
  glob: tickets/T-draft-9249081e/**
  reason: T-draft-9249081e's ticket file was created and committed in this worktree
    while filing the out-of-scope WIRE001 finding; scope it so SCOPE001 does not flag
    T-4365's own commit
  actor: logan
  at: '2026-09-09'
evidence:
- tests/test_doctor.py::test_run_diagnosis_natives_present
- tests/test_doctor.py::test_run_diagnosis_natives_absent
- tests/test_doctor.py::test_run_diagnosis_partial_availability
designated_repro_test: tests/test_doctor.py::test_run_diagnosis_natives_present
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE DOCTOR TESTS ASSERT A HEALTHY VERDICT IN A PROJECT THAT GENUINELY LACKS THE
TOOLS DOCTOR IS CHECKING FOR, AND THAT ASSERTION ONLY HELD BECAUSE ONE PLATFORM
HAPPENED TO HAVE THEM INSTALLED GLOBALLY.

MEASURED. Sixteen failures on the macos leg, all in the doctor CLI tests, all
reporting the same thing:

  frob doctor found issue(s)
    remediation: required tool(s) missing: ruff not found -- pip install ruff
                 (or: uv pip install ruff); ty not found -- pip install ty ...

The tests build a throwaway fixture project and assert doctor reports healthy. That
project declares neither of those tools. On the linux runner they are present on
the ambient PATH, so doctor finds them and the assertion passes. On the macos
runner they are not, so doctor correctly reports them missing and the assertion
fails.

THIS CONFIRMS A HYPOTHESIS THAT WAS EXPLICITLY LEFT UNVERIFIED. An earlier ticket
in this chain wrote down, and correctly declined to assert, that macos CI might
lack a global ruff/ty while linux has one. This is that difference, observed
directly. It is the same underlying condition already fixed for the check path --
a tool absent from the target project -- surfacing through a different consumer.

DOCTOR IS PROBABLY NOT THE THING THAT IS WRONG. Reporting a missing required tool
is precisely what a doctor command is for; suppressing that would gut the command.
Start from the assumption that the TEST carries the bad premise, and only conclude
otherwise if you find a specific reason.

SO DECIDE WHAT "HEALTHY" SHOULD MEAN FOR A THROWAWAY FIXTURE. Either the fixture
must provide what it claims to be healthy without -- making the test honest about
its own preconditions -- or the assertion must be narrowed to the subject actually
under test, which for most of these is native-extension availability and derived
state, not toolchain presence. Both are defensible; choose deliberately and record
why. Do NOT make it pass by asserting on a substring that happens to differ.

BEWARE THE AMBIENT-PATH DEPENDENCE ITSELF, because that is the deeper finding. A
test whose outcome depends on what happens to be installed on the runner is not
testing what it claims, and it passed on linux for a reason unrelated to the code
under test. Whatever you change, the result should not depend on the ambient
environment -- and say explicitly how you ensured that.

CHECK THE OTHER FIFTEEN rather than fixing one and assuming. They share a family
and a symptom, but confirm they share the cause; the same log shows several other
small clusters with genuinely different causes.

VERIFY on the platform where it reproduces if you can. If you cannot reach macos,
say so plainly and state which conclusions are inferred -- but note this one is
reproducible anywhere by removing the tools from PATH, which an earlier ticket in
this chain already did successfully by isolating the runner binary.

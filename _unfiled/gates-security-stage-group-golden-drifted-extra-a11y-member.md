+++
id = "01M38BCNASWK1GWJ9Q0AFPG5XF"
title = "gates-security stage-group golden drifted: extra a11y member"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "agent"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:02Z"
aliases = ["T-5465"]
labels = ["milestone:v0.534.0"]
scope = ["tests/system/test_cli_check.py"]
+++

Found while draining CI run 35951365410 (dev 9e0c89bb19). Failing:
tests/system/test_cli_check.py::TestCheckStageGroups::test_gate_stage_group_migration_is_byte_identical

_STAGE_GROUPS["gates-security"] now contains an extra 'a11y' entry versus
its golden/expected set (AssertionError: extra item 'a11y' in the left
set). A gate's stage-group membership drifted from the byte-identical
migration golden this test guards.

Needs: locate the stage-group registration (NOT src/frob/gates/_a11y_gate.py
itself, which is out of touch-scope -- this is the general stage-group
list/golden file) and either update the golden to include 'a11y' if the
membership change was intentional, or remove 'a11y' from gates-security if
it was not.

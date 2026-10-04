+++
id = "01M35RZY844SAQ2THYJQ0KZ9YZ"
title = "claude/agent/natives --help no longer cites T-4522/T-4546 flattening note"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5380"]
labels = ["milestone:0.534.0"]
scope = ["tests/unit/test_cli_single_child_groups.py", "src/frob/_cli_parsers/_core.py", "src/frob/_cli_parsers/_misc.py"]
+++

CI run 35819358270 (all 3 platforms); re-verified failing on dev tip 39b89ed091: tests/unit/test_cli_single_child_groups.py::TestClaudeGroupFlattened::test_help_notes_alias, TestAgentGroupFlattened::test_help_notes_alias and TestNativesGroupFlattened::test_help_notes_alias all fail -- 'frob claude --help'/'frob agent --help'/'frob natives --help' no longer print the T-4522/T-4546 single-child-group-flattening note in their description/epilog (help text now just describes the implied subcommand). Likely one shared CLI-description-builder regression, not three independent breaks -- find the common code path before filing 3 separate fixes. Distinct from T-5092/T-5096/T-5205 (those are the '--path' option-parity drift on ops natives, not the help text).

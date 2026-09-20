---
id: T-4524
title: 'frob check: replace the 20 --skip-<stage> flags with one repeatable --skip
  STAGE[,STAGE] mirroring --only'
state: done
kind: ux
origin: agent
created: '2026-09-16'
priority: medium
parent: T-2994
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: v0.534.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_check.py
- src/frob/_cli_parsers/__init__.py
- src/frob/app/check_runner.py
- tests/unit/test_check_skip_flag.py
- docs/commands/check.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_check_skip_flag.py::TestUnifiedSkipFlag::test_comma_split_sets_both_legacy_attributes
- tests/unit/test_check_skip_flag.py::TestLegacyFlagsDeprecated::test_legacy_flag_still_works
- tests/unit/test_check_skip_flag.py::TestSkipOnlyConflict::test_conflicting_stage_detected
designated_repro_test: null
acceptance:
- text: GIVEN frob check --skip ruff,ty WHEN it runs THEN the ruff and ty stages are
    skipped exactly as --skip-ruff --skip-ty did
  evidence:
  - tests/unit/test_check_skip_flag.py::TestUnifiedSkipFlag::test_comma_split_sets_both_legacy_attributes
- text: GIVEN every old --skip-<stage> spelling WHEN passed THEN it still works for
    one release with a DEPRECATED note in --help, and frob check --help lists 20 flags
    fewer
  evidence:
  - tests/unit/test_check_skip_flag.py::TestLegacyFlagsDeprecated::test_legacy_flag_still_works
- text: GIVEN --skip and --only name the same stage WHEN parsed THEN the CLI refuses
    with a message naming the stage
  evidence:
  - tests/unit/test_check_skip_flag.py::TestSkipOnlyConflict::test_conflicting_stage_detected
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-16 (CLI surface audit): frob check has 39 flags, 20 of them --skip-{arch,bind,build,cargo-check,clang-format,clang-tidy,clippy,cycle,dup,eslint,exports,fmt,gates,prettier,ruff,ruff-check,ruff-format,tests,tsc,ty} (src/frob/_cli_parsers/_check.py:11-91). --only STAGE (repeatable, _check.py:142-148) already defines the stage vocabulary; --skip is its mirror. --skip-ruff is itself a bundle over ruff-check/ruff-format, which a comma list expresses natively.
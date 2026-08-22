---
id: T-2387
title: check_skip_ruff_check/check_skip_ruff_format/check_ruff_fix silently dropped
  by CLI layer -- _BOOL_FLAGS never updated for T-2320's new flags
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/_config_external.py
evidence_scope:
- tests/unit/test_app_config_flag_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags::test_current_tree_has_zero_dropped_flags
- tests/unit/test_app_config_flag_coverage.py::TestT2320RuffFlagsReachAppConfig::test_from_external_carries_all_three_ruff_flags_from_parsed_argv
- tests/unit/test_app_config_flag_coverage.py::TestT2320RuffFlagsReachAppConfig::test_absent_ruff_flags_default_false
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: b201534b2841b715db2da3cbc39dc1492ac60a19
---
Found while auditing T-2244 (repoint trivial Makefile aliases): T-2320
added three new boolean CLI flags (--skip-ruff-check, --skip-ruff-format,
--fix-ruff) with correct argparse wiring AND correct downstream
plumbing (run_check/_python_skip_flags/_run_ruff all consume the
config fields correctly) -- but _BOOL_FLAGS
(src/frob/app/_config_external.py:337) was never updated to include the
three new dest names (check_skip_ruff_check, check_skip_ruff_format,
check_ruff_fix). _apply_bool_flags only copies a CLI bool into
AppConfig if its dest name is listed in _BOOL_FLAGS -- an unlisted flag
is silently dropped before AppConfig(**d) is constructed, so the field
always keeps its False default regardless of what was typed on the
command line.

This is the EXACT bug class T-0749 (config.py:677-681, still documented
in a comment right next to the missing entries) already names and fixed
once for --accepts N: "argparse parsed it into args.X but
from_external silently dropped it before AppConfig(**d)." It
recurred here because T-2320's own tests
(tests/unit/test_check.py::TestRunRuffRealPaths, per its Done report)
call run_check/_run_ruff directly with keyword arguments -- never
through the actual frob check --skip-ruff-format ... CLI parse path --
so nothing caught the drop.

REPRODUCED directly against current main:
  $ frob check --skip-ruff-format --skip-arch --skip-cycle --skip-dup \
      --skip-bind --skip-exports --skip-gates --skip-tests --no-cache
  ... still reports FAIL ruff-format 138 files would be reformatted ...
Confirmed via a debug parse (AppConfig.from_external-equivalent):
argparse itself correctly sets ns.check_skip_ruff_format = True; the
value never survives into the constructed AppConfig.

IMPACT: --skip-ruff-check/--skip-ruff-format are unusable from the
CLI (always run BOTH ruff sub-stages regardless of flags) -- the entire
point of T-2320's split (letting a caller check ruff-lint without
tripping on the repo's 138 pending ruff-format diffs) does not work
today. --fix-ruff is worse: it silently no-ops from the CLI --
check_ruff_fix never reaches True, so the "genuine ruff-autofix
WRITE pass and exit" T-2320 built is completely unreachable via the
documented frob check --fix-ruff invocation; a caller gets a normal
read-only check run instead, with no error or warning that their write
flag was ignored.

FIX: add check_skip_ruff_check, check_skip_ruff_format, and
check_ruff_fix to _BOOL_FLAGS. Positive control: a test that invokes
the ACTUAL CLI parse path (AppConfig.from_external/from_args, not
run_check directly) with each new flag and asserts the corresponding
cfg.* field is True -- the exact test shape T-0749's own fix added
for --accepts, and the shape this defect's own tests skipped.
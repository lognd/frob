## Done report

Changed:
- frob.toml: fourth [[test.runner]] entry, language = "strata" -- command
  runs `uv run pytest -q tests/unit/strata {files}` (touched .strata paths
  fold in beside the covering suite dir, contributing zero collected
  items), all_command runs the suite dir. Deliberately narrower than a
  global fallback = "suite".

Evidence: config-only change with no code symbol of its own; the three
attached node ids (TestRunners::test_placeholder_files / test_no_runner_error /
test_valid_runner_loaded) evidence the exact machinery this entry relies
on -- {files} expansion, the NoRunner failure mode being fixed, and
runner-spec loading. The behavior change itself was verified by direct
reproduction, independently re-executed by the reviewer:
- pre-fix: `frob test --base ea4d24f` errors NoRunner for language
  'strata'; post-fix: [PASS] strata exit=0, [PASS] python exit=0.
- the exact constructed command run by hand (pytest with a .strata path
  argument) exits 0 with 528 items collected -- {files} expansion is
  harmless for non-python paths per _expand_placeholder semantics.
- no-strata touched-sets unchanged (nothing-touched selects no tests).

Gates: `frob check --ticket T-0149` pass, 87 violation(s)/57 waived,
identical to the post-T-0145 main baseline; reproduced twice by the
reviewer. Reviewer verdict: APPROVE.

Filed: none.

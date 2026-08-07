## Done report

Adds `--only <stage-group>` presets (`lint`, `static`, `gates-fast`,
`gates-native`, `gates-security`) plus `--only list` to `frob check`, so an
agent can loop budget-sized chunks instead of one full check/gates pass.
Each group's wall time was measured directly on this repo:

- `lint` (ruff, ty): ~1.2s
- `static` (cycle, dup, arch, bind, exports): ~18s
- `gates-fast` (22 thread-pool gates: drift/coverage/invariant/test/policy/
  doclink/docanchor/fuzz/release/decisions/tickets/refs/registry/docblocks/
  walk_lint/excludehazard/debt/render_lint/parse_failures/lang_conformance/
  lang_project_conformance/scope/prework): ~36.5s
- `gates-native` (archgate, clones, perf -- 3 of the 7 CPU-bound
  process-pool gates): ~15s
- `gates-security` (sys, pii_structural, secrets, dead_symbols -- the
  remaining 4 process-pool gates): ~12.7s

versus the original unchunked `--only gates` at ~113s (over the ~120s
foreground cap) plus the individual tool stages on top -- every new group
is comfortably under a ~90s per-stage budget. `--only list` prints exactly
the stage names, one per line, nothing else (machine-splittable by a shell
`for` loop); `--json` wraps the same list as `{"stages": [...]}`. A group
name is pure sugar over `--only`'s existing tool/gate vocabulary
(`frob.check._STAGE_GROUPS`, expanded in `_resolve_only` before its
existing gate/tool split) -- hand-listing individual names still works
unchanged, and mixing a group with individual names is additive.

Second guarantee: when `FROB_AGENT` is set (T-0574), a bare `frob check`
with no `--only` selection (and not a `--stamp-coverage`/`--stamp-baseline`
exit-early mode) now refuses immediately (exit 1) instead of running and
stalling -- `_refuse_full_check_for_agent`/`_refuse_full_check_message` in
`check_runner.py`. The message names the sanctioned chunked loop.
`FROB_ALLOW_FULL_CHECK=1` opts a specific invocation back into the full
run. Verified both directions directly: `FROB_AGENT=1 frob check` exits 1
naming T-0627 and the loop; `FROB_AGENT=1 frob check --only lint` and
`FROB_AGENT=1 FROB_ALLOW_FULL_CHECK=1 frob check` both exit 0; `frob check`
without `FROB_AGENT` is unaffected.

`--stamp-baseline` is intentionally NOT refused (it is a legitimate
one-shot warm-up step, not a repeatable verification loop) but it still
runs the full undelta'd gates pass and can still exceed the cap -- this is
called out explicitly in the playbook update rather than silently glossed
over, and filed as a separate follow-up ticket (below) rather than solved
here.

Updated `docs/guides/agent-playbook.md` sections 3b (names the refusal and
the chunked loop as the sanctioned path, explains why a bare `frob check`
is the single most common way to trip the "never background a
verification" anti-pattern by accident) and 6 (flags `--stamp-baseline`'s
residual risk and points at the chunked `--only` loop for every
verification pass after the initial stamp). Also updated
`docs/commands/check.md`'s `--only`/gates-integration section with the
same stage-group table, `--only list`, and the `FROB_AGENT` refusal
(reviewer round 1 finding -- see below).

Filed (both out of this ticket's scope):
- T-0750 (ex-draft, id lost at land) -- pre-existing (not caused by this ticket): a wide
  swath of `tests/system/test_cli_check.py` fails on this worktree's
  post-warm-up-merge main because `_make_project`'s tmp_path fixture never
  git-inits and newly-merged gates (COV002/SCOPE001/TODO001) now error
  loudly instead of degrading quietly on a missing repo. Verified this
  ticket's own new tests are not among the failures.
- T-0751 (ex-draft, id lost at land) -- follow-up: `--stamp-baseline` itself still runs the
  full undelta'd gates pass and is not refused under FROB_AGENT; T-0627's
  own ticket body named "make --stamp-baseline incremental" as an
  alternative option and left it unbuilt.

Reviewer round 1 rejected on two cheap items, both now fixed and
re-verified:
- `_refuse_full_check_message`'s loop-instruction string used a
  single-quoted literal that failed `ruff format --check` under both the
  project-pinned (`uv run ruff`) and PATH `ruff` binaries (playbook 12).
  Reformatted; `frob check --ticket T-0627 --only lint` is now clean:
  `ruff-check: no issues`, `ruff-format: all files formatted`, `ty: no
  issues`, exit 0 under both binaries.
- `docs/commands/check.md` (the canonical command reference, and the
  anchor `available_stages`' `frob:doc` edge points at) now documents the
  `--only` stage-group vocabulary, `--only list`, and the `FROB_AGENT`
  refusal alongside the existing `agent-playbook.md` coverage --
  document-as-you-go, same change as the code, not a follow-up.

Gates: `frob check --ticket T-0627 --only <group>` clean (exit 0) for
`lint`, `static`, `gates-native`, `gates-security`. `gates-fast` shows
REL001 (public API version bump -- this dispatch's explicit instructions
say pyproject.toml/CHANGELOG/uv.lock are the coordinator's land-time job,
not an implementer agent's) plus COV003 findings against T-0724/T-0726's
OWN recorded evidence ids (`tests/system/test_cli_sys_plan.py::
TestSysAuditContentionCli::test_duplicate_port_fires_sys200_through_cli`,
`tests/test_gates.py::TestTick006PhantomFiling::*`) -- neither file nor
test belongs to this ticket's scope or diff; these are worktree-skew
against tickets this branch has not landed/synced, not violations T-0627
introduced, and are expected to resolve at land against the merged tip.

### Changed
```
 docs/commands/check.md                |  79 ++++++++++++++++++-
 docs/guides/agent-playbook.md         |  48 ++++++++++++
 src/frob/app/check_runner.py          | 105 +++++++++++++++++++++++++
 src/frob/check/__init__.py            |  84 +++++++++++++++++++-
 tests/system/conftest.py              |  17 ++++-
 tests/system/test_cli_check.py        | 140 ++++++++++++++++++++++++++++++++++
 tests/unit/test_app_runners_batch6.py |  94 +++++++++++++++++++++++
 7 files changed, 560 insertions(+), 7 deletions(-)
```

### Evidence
(no evidence recorded)

## Done report

**Round 2 (reviewer REJECT fix).** Round 1's Done report below is kept
for the file list and the DEPLOY003/shared-`_load_current_model`/litmus-
structure work, which the reviewer confirmed was fine. This preamble
records what round 2 actually changed, since it is the security-relevant
part.

Round 1 REJECTED: `extract_mutation_surface` was a per-line regex
requiring a LITERAL command name at line start plus a DOUBLE-QUOTED
target on the SAME line -- despite the round-1 docstring's "structured
extraction, not naive grep" framing, it was, in the reviewer's words,
"a naive grep with a quoting requirement". Every one of these ORDINARY
shapes evaded it silently (DEPLOY002 reported clean): `useradd evil`
(no quotes), `useradd 'evil'` (single quotes), `systemctl enable
evil.service` (unquoted), `/usr/sbin/useradd "evil"` (full binary
path), `true; useradd "evil"` (`;`-prefixed compound), `env useradd
"evil"`/`eval "useradd evil"` (wrapper), and a line-continued target.
For a red-team tamper detector this is worse than not running it --
a reviewer trusting "DEPLOY002: clean" would be misled.

**Fix**: `extract_mutation_surface` (`src/frob/deploy/_conform.py`) was
rewritten from regex to GENUINE shell tokenization: `shlex` (POSIX mode,
`punctuation_chars` enabled) tokenizes each physical line (after joining
`\`-newline continuations), tokens are split into simple commands on
`;`/`&&`/`||`/`|`/`&`/`(`/`)` and shell keyword boundaries (`if`/`then`/
`fi`/...), and each simple command's real verb is resolved via
basename-of-argv[0] after stripping leading `NAME=value` assignments and
wrapper commands (`env`/`sudo`/`nice`/`nohup`/`exec`/`command`/`time`);
`eval "..."` re-tokenizes its own concatenated argument as a fresh
command line (mirrors bash's actual eval semantics). New helpers:
`_tokenize_line`, `_split_commands`, `_resolve_command`,
`_clean_positional_args` (drops flags and redirection targets so `2>&1`
noise never masquerades as a real positional argument),
`_mutation_for_command`, plus the `_TokenizeError` fail-closed path: a
line that cannot be tokenized at all (e.g. an unterminated quote) is
NOT dropped -- it becomes a `kind="parse-error"` sentinel target that
can never match a declared manifest entry, so it always surfaces as
DEPLOY002 rather than silently vanishing.

New regression tests, `tests/unit/deploy/test_conform.py::TestEvasion`
(9 cases): every one of the reviewer's battery items
(`test_bare_word`, `test_single_quoted`, `test_systemctl_bare`,
`test_full_path`, `test_semicolon`, `test_env_wrapper`,
`test_eval_wrap`, `test_line_cont`) plus one not in the explicit list
but the same evasion class (`test_compound_and`, `&&`), plus an
end-to-end check (`test_evasion_fires_through_full_check`) that hand-
appends `true; useradd evil-backdoor` to a REAL generated `install.sh`
and asserts DEPLOY002 fires through the public
`deploy_conformance_violations` entry point, not just the unit-level
extractor. All 9 evasion cases now fire; the full `tests/unit/deploy/`
suite (28 tests, extraction + expected-surface + conformance + evasion)
passes.

Module docstring corrected to not overclaim: it now says "GENUINE SHELL
TOKENIZATION, not a quoting-shaped grep (the round-1 regex mistake --
reviewer REJECT...)" and explicitly names the one still-honest scope
cut left -- heredoc BODY lines (unit-file content between `cat > ... <<
'EOF'` and its closing marker) are still walked per physical line like
any other line, since they are inert (never executed, only ever written
as literal data to a file), so this can only ever add a spurious extra
match, never hide a real mutation (fail-closed-shaped, not fail-open).
This is NOT evasion-proof against a hypothetical shell feature this
tokenizer does not model (e.g. `$()`/backtick command substitution
executing a smuggled command as part of building an argument string,
or a deeply obfuscated base64-decode-and-eval chain) -- it closes the
reviewer's full ORDINARY-shell battery, which was the actual gap found,
not a claim of exhaustive shell-Turing-completeness coverage.

`_load_current_model`, DEPLOY003, and the litmus test structure are
unchanged from round 1 (the reviewer found no issue with them).

Round 2 evidence (observed via `uv run pytest tests/unit/deploy/ -q` --
28 passed):
- `tests/unit/deploy/test_conform.py::TestEvasion::test_bare_word`
- `tests/unit/deploy/test_conform.py::TestEvasion::test_single_quoted`
- `tests/unit/deploy/test_conform.py::TestEvasion::test_systemctl_bare`
- `tests/unit/deploy/test_conform.py::TestEvasion::test_full_path`
- `tests/unit/deploy/test_conform.py::TestEvasion::test_semicolon`
- `tests/unit/deploy/test_conform.py::TestEvasion::test_env_wrapper`
- `tests/unit/deploy/test_conform.py::TestEvasion::test_eval_wrap`
- `tests/unit/deploy/test_conform.py::TestEvasion::test_line_cont`
- `tests/unit/deploy/test_conform.py::TestEvasion::test_compound_and`
- `tests/unit/deploy/test_conform.py::TestEvasion::test_evasion_fires_through_full_check`
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen` (re-ran
  green after the rewrite, via `uv run pytest tests/unit/strata/
  test_selfconform.py -k TestRealGateGreen -q`)

Round 2 gates: merged `main` first (tip moved to `07bd928`, verified via
`git log --oneline -1` after merge); full `uv run frob check` (not
`--ticket`) -- 0 errors, 5 pre-existing warnings, 27 pre-existing
waived; `DRIFT002`: 0. `uv run frob check --ticket T-0258` -- 0 errors
(re-swept via `frob ticket sweep T-0258` after the scope extension).
`git diff main --diff-filter=D --stat` empty. `frob-core/Cargo.lock`/
`strata-core/Cargo.lock` build churn from `make core` reverted again
before finishing.

---

## Round 1 Done report

Changed:
- `src/frob/deploy/_conform.py` (NEW): `MutationTarget`,
  `extract_mutation_surface`, `expected_mutation_surface`,
  `ConformanceViolation`, `deploy_conformance_violations`. Structured
  (regex-anchored to `_generate.py`'s exact check-then-apply command
  shapes, never a blind grep) extraction of a committed script's mutation
  surface -- `useradd`/`groupadd`/`userdel`/`groupdel`/`mkdir`/`install`/
  `cp`/`chown`/`chmod`/`rm -f`/`rm -rf`/`systemctl enable|disable|start|
  stop`/unit-file heredoc writes, each mapped to a `(kind, target)` pair
  -- compared bidirectionally, per-script (`install.sh` and
  `uninstall.sh` independently), against the current design model's
  `HostManifest`-derived expected surface: DEPLOY002 = script mutation
  with no manifest declaration; DEPLOY003 = manifest declaration with no
  implementing script mutation.
- `src/frob/deploy/_drift.py`: extracted `_load_current_model` out of
  `_current_model_output` (design-dir read + merge, previously inlined)
  so DEPLOY001 and DEPLOY002/DEPLOY003 share the ONE model-loading path
  instead of duplicating it.
- `src/frob/deploy/__init__.py`: exports the new `_conform.py` public
  surface.
- `src/frob/app/check_runner.py`: new `_deploy_conformance_result`,
  wired into `_dispatch_check`'s flow the same "extra stage beyond
  `frob.gates`'s job table" shape `_deploy_drift_result` (DEPLOY001)
  already uses -- opt-in on `deploy/` existing.
- `tests/unit/deploy/test_conform.py` (NEW): extraction unit tests
  (including a heredoc-body-is-never-a-mutation regression), the
  manifest-derived expected-surface test, and the litmus quartet: no
  `deploy/` dir -> clean; a real `frob deploy generate` output -> clean
  both directions; a hand-appended rogue `useradd` in `install.sh` ->
  DEPLOY002 fires on exactly that target, `uninstall.sh` stays clean; a
  hand-removed `userdel` line from `uninstall.sh` -> DEPLOY003 fires
  for the now-unimplemented `("user", "api-svc")` manifest entry.
- `docs/strata/host.md`: new "DEPLOY002/DEPLOY003: conformance" section
  (`#deploy002deploy003-conformance`); updated the "Scope boundary"
  bullet that previously (inaccurately, after this ticket landed)
  described T-0258 as a live-host checker -- reworded to point at
  T-0259's VM auditor, since T-0258 turned out to be the committed-
  script<->manifest structural check, not a live-host one.
- `docs/commands/deploy.md`: new "DEPLOY002/DEPLOY003: bidirectional
  conformance" section, `See also` entry for `_conform.py`.
- `CHANGELOG.md`: new `[0.7.0] - unreleased` section (REL001 demanded
  >=0.7.0 after `frob release stamp` computed the new public surface,
  per the agent-playbook's "0.6.0 stays unless a bigger surface, then
  disclose" rule -- disclosed here) carrying the T-0258 public API
  entry; the prior T-0257 entry stays under `[0.6.0]`.
- `pyproject.toml`: version 0.6.0 -> 0.7.0 (REL001-driven).
- `.frob-release.json`: `frob release stamp` re-run at 0.7.0 (857 public
  symbols stamped).

Evidence (observed via `uv run pytest tests/unit/deploy/ -q` -- 18
passed, and `uv run frob test --base main` -- selected + ran the same
10 node ids, `exit=0`):
- `tests/unit/deploy/test_conform.py::TestExtract::test_install`
- `tests/unit/deploy/test_conform.py::TestExtract::test_no_heredoc`
- `tests/unit/deploy/test_conform.py::TestExpected::test_from_host`
- `tests/unit/deploy/test_conform.py::TestConform::test_no_dir`
- `tests/unit/deploy/test_conform.py::TestConform::test_clean_pass`
- `tests/unit/deploy/test_conform.py::TestConform::test_extra_002`
- `tests/unit/deploy/test_conform.py::TestConform::test_missing_003`
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen` (self-
  conformance over the changed `src/frob/deploy/**`/`src/frob/app/
  check_runner.py`, ran green via `uv run pytest tests/unit/strata/
  test_selfconform.py -k TestRealGateGreen -q`)

Filed: none. No out-of-scope work found. SCOPE001 fired for
`src/frob/app/check_runner.py` (the `frob check` wiring point, same
DEPLOY001-precedent shape T-0257 used `src/frob/app/**` scope for) plus
`CHANGELOG.md`/`pyproject.toml`/`.frob-release.json`/`uv.lock` (the
REL001-driven version bump's own touch set) -- extended T-0258's
declared `scope` to add `src/frob/app/**`, `CHANGELOG.md`,
`pyproject.toml`, `.frob-release.json`, `uv.lock` (playbook section 4:
scope extension via `tickets.md`, not silently folded in).

Gates: `uv run frob check` (full, not `--ticket`) -- 0 errors, 5
warnings (pre-existing, unrelated to this ticket's files), 27 waived
(all pre-existing). `ruff-format` reports 1 file needing reformatting
(`tests/test_lang.py`) -- pre-existing from the `main` merge (T-0182's
rust directive fix, commit `1e64899`), not touched by this ticket, left
as-is. `DRIFT002`: 0 (confirmed clean in the full `frob check` output).
`git diff main --diff-filter=D --stat` is empty (deletion-filter land
rule, section 9 of the playbook). `frob-core/Cargo.lock`/`strata-core/
Cargo.lock` churn from `make core` reverted before finishing (`git
checkout -- frob-core/Cargo.lock strata-core/Cargo.lock`); `uv.lock`'s
one-line `frob` version bump (0.6.0 -> 0.7.0) kept, since it tracks the
legitimate `pyproject.toml` bump.

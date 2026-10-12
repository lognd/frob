# frob v2 adoption trial, 2026-10-07 (binary 0.532.0 debug)

Fixture: <scratchpad>/adopt/
(proj = python pkg in py/ + rust crate in rs/ + one git repo; v1repo, v1b, tb, mst = side trials).
Docs used: README.md, docs/guides/{release,upgrade-from-v1}.md, docs/migration/*, docs/reference/*.
Everything below was run against the installed `frob`; grimble/crunk from target/debug (both present).

What worked well (so the list below is read in context): init (branch auto-detected, also master),
ticket new/update/list, cycle new/assign/close/velocity, milestone, work (worktree), SCOPE001 lease
enforcement, REL003 changelog gate, evidence + --accepts binding, land (merge, close, worktree cleanup),
release status/cut (tag, CHANGELOG from fragments), WIP limits, and error envelopes: nearly every
error carries code + cause + a concrete remedy command. Exit codes 0/1/2/3 behaved as documented.
Most commands run in 0.03-0.3 s.

## Findings

### F1 HIGH - No getting-started guide; README is the v1 text and links dead files
- Step: first read of the docs.
- Command: read README.md, ls docs/guides
- Happened: README says "sections below still describe the v1 Python implementation", its Quickstart uses
  `frob graph build`, `frob ticket new --kind feature` , `frob work --here T-0001`, `frob ticket close`
  (all v1 forms; `graph build`, `--kind`, T-0001 ids do not exist in v2), and advertises `frob serve`,
  `frob vet`, `frob agent`, `frob scaffold` etc. which v2 rejects. It links docs/guides/quickstart.md and
  docs/guides/command-reference.md; neither exists (docs/guides has only release.md and upgrade-from-v1.md).
  Install section: "not yet published, cargo build".
- Docs said: the above. A newcomer cannot learn init -> ticket -> work -> test -> evidence -> land
  from any doc; I reconstructed it from `--help` and error remedies.
- Fix: write docs/guides/quickstart.md (the loop I ran, with real output) and a "concepts" page (handle vs
  ULID vs alias, categories, lease/scope, evidence/--accepts, trunk ledger commits); rewrite README
  top-to-bottom for v2; delete or mark v1-only verbs.

### F2 HIGH - Rust crate in a subdirectory: `frob test` runs nextest at the repo root and fails
- Step: frob test on the rust ticket (rs/Cargo.toml, no root Cargo.toml).
- Command: `frob test --base <sha>`
- Happened: selection is right (`geom tests::perimeter_works`, framework nextest) but the run fails:
  `tests failed (0 executed, exit Some(102)): no failing test name captured; evidence ... recorded`.
  Evidence transcript (only visible via `frob ticket evidence list`): `error: could not find Cargo.toml in
  <worktree> or any parent directory`. A failed run is also recorded as (committed) evidence each time,
  piling commits on the branch.
  The Python subdir (py/) worked: pytest ran with rootdir py/.
- Workaround found: add a root Cargo.toml `[workspace] members=["rs"]`.
- Docs said: nothing about repo layout / where tests run.
- Fix: run nextest in the nearest Cargo.toml/workspace root of the touched crate (like pytest does);
  failing that, put the cause in the error message (not only in the evidence blob) with the remedy
  "add a workspace Cargo.toml at the root"; document the layout rule.

### F3 HIGH - Ticket branch (orphan `frob-tickets`) setup is undocumented and does not work end to end
- Step: "ticket-branch setup if the docs describe one".
- Commands: `frob ticket branch init` (works: creates orphan `frob-tickets`), then tried
  `[tickets] ref_mode="branch"` and `ref="refs/heads/frob-tickets"`.
- Happened: only docs/design/mirror.md and the config table mention it. `[tickets] branch` is only used by
  `branch init`; `ref_mode = "branch"` means "commit to the checked-out code branch" (NOT the orphan
  branch, easy to misread). To use the orphan branch you must set `ref = "refs/heads/frob-tickets"`.
  With that: `ticket new/list/doctor` work, but `frob work <t>` creates the ticket worktree FROM the
  tickets-branch tip (contains only README.md + tickets/, no code, no frob.toml), and `frob land`
  there fails `E-NO-CONFIG ... run frob init`. So the supported flow breaks at `work`.
- Fix: either make `work` branch from the code base (check.base) when ref is not the code branch, or
  refuse with a teaching error ("ledger ref is a ticket-only branch; ticket worktrees need ..."). Add a
  guide section "ledger on its own branch" with the exact knob set; rename/clarify `ref_mode` values.

### F4 HIGH - `release bump`/`cut` is Rust-workspace-shaped; python versions untouched, Cargo rewritten
- Step: milestone 0.1.0 -> `frob release cut 0.1.0`.
- Happened: cut succeeded (tag v0.1.0, CHANGELOG compiled, ledger record) but it rewrote my layout:
  created `[workspace.package] version` in the root Cargo.toml and changed rs/Cargo.toml to
  `version.workspace = true`. `frob release bump 0.2.0 --dry-run` only touches Cargo.toml; py/pyproject.toml
  `version` is never bumped (coincidentally equal to 0.1.0 here, so the miss was silent).
- Docs said: release.md is written for cutting frob itself (crates.io/PyPI environments, 35 crates, frob-v*
  tags); "bumps every crate to one version (the wheels take it from Cargo)". Nothing for a generic or
  python project.
- Fix: bump pyproject.toml (`[project] version`) and package.json versions, or refuse loudly with
  "pyproject.toml not managed: set [release] version_files = [...]"; do not restructure Cargo.toml without
  saying so; write a generic "release your project" guide separate from "release frob".

### F5 HIGH - v1 migration: documented command fails as written; step order in the guide is wrong
- Step: upgrade-from-v1.md "Move your tickets".
- Command: `gob-dev import-v1-tickets --from tickets --to ../out --dry-run` (guide form, using
  target/debug/gob-dev; `cargo dev import-v1-tickets` is the same thing)
- Happened: `Error: error: docs/migration/v1-selection.toml: No such file or directory`. The default
  `--selection` is the frob repo's OWN selection file (relative path, resolved against the cwd). The guide
  never mentions --selection or --all. With `--all` it works (map, report, aliases T-0004 resolve,
  blocked-by and parent links kept, acceptance carried unbound) and the report is full of frob-repo
  vocabulary (clusters, areas, "private-term rules").
- Step order: the guide says replace tickets/, run `frob init` and `frob ticket doctor`, then commit. Doctor
  before the commit reports `tickets: 0` (v2 reads the ledger from git, not the working tree); after the
  commit it reports 4 tickets/4 events. Following the text literally looks like a failed import.
- Other: importer is not installable (needs a source checkout + Rust build; guide admits this).
  `frob-v1 init` (named in my brief) does not exist; v1 has no init, so a v1 repo is created by
  `ticket new` alone (no frob.toml) - the guide does not say what to do when v1 frob.toml is absent.
- Fix: guide command gets `--all`; make `--selection` default to none (import everything) when the file
  is absent; reorder steps to "init, commit, doctor"; ship the importer in the `frob` binary
  (`frob migrate v1 --from tickets`) so it is not a source-checkout tool.

### F6 MEDIUM - Fresh repo `frob check` is noisy: 7 "unresolved" from frob's own files
- Command: `frob check` right after `frob init` (text and json)
- Happened: `DRIFT001/2/3, INV001, REF001, TEST001, TODO001 unresolved: 2 opaque text file(s) (no adapter,
  first .gitattributes) were not read` - the two files are frob.toml and .gitattributes that init just wrote
  (3 later with grimble.toml). Exit code stays 0 ("required_unresolved 0") so nothing blocks, but a new
  user sees 7 alarming lines and `lines` is the only field that explains them. PM033 "ready queue is 1,
  below 4" advisory also appears with 5 tickets.
  Same family: ledger event files under tickets/ show up in `frob test` as `unresolved_files` and TEST001
  ("test selection is undecided for 5 changed file(s) with no adapter (first py/pyproject.toml)").
- Fix: treat frob-owned files (frob.toml, .gitattributes, tickets/**, changelog.d/**, lockfiles, pyproject/
  Cargo manifests) as known non-code; or give them a no-op adapter; collapse the 7 into one line.

### F7 MEDIUM - `--text` output is a YAML-ish dump of the JSON, not a human view
- Commands: `frob ticket list --text`, `cycle assign --text`, `check --text`, `ticket evidence add --text`
- Happened: 15 lines per ticket in `ticket list`; `cycle assign` repeats the whole cycle object; `check
  --text` prints ~60 lines of fidelity/stat counters, empty keys (`findings:`, `siblings:`), then the
  real findings under `lines:`; `evidence add --text` dumps the whole pytest transcript. Only `board` has a
  real human view. `none` is printed for null.
- Fix: per-verb text templates (table for list/doable, one line per finding for check, summary line for
  mutations like "cycle.assign: ~E4KECE2 -> cycle ~WYFW03N (6 pts committed)"); keep the dump behind -v.

### F8 MEDIUM - Failed test run diagnostics are hidden in evidence, test ids are mangled
- Command: `frob test --base main` with a pytest collection error (module `calc` not importable, src layout)
- Happened: `tests failed (1 executed, exit Some(4)): tests/test_mul.py::tests.test_mul; evidence ... recorded`.
  No cause, remedy null; the id `tests/test_mul.py::tests.test_mul` is not a real node id; the real error
  (ModuleNotFoundError) is only in `ticket evidence list`. Three failed attempts produced three evidence
  commits on the branch (history noise). After the fix, ticket show lists the four records with passed false/
  false/false/true - fine, but failed ones are never superseded.
- Fix: include the last ~10 lines of the transcript (or the first error) in the error and set remedy to
  `frob ticket evidence list <t>`; map collection errors to "collection failed" not a test name; option
  to not record failing runs (`--record-failures`) or squash them.

### F9 MEDIUM - Frob-specific text leaks into other projects
- `frob release status`: "unresolved: registry setup: owner action: trusted publishing on PyPI (frob) and
  crates.io, reserved crate names confirmed; see docs/guides/release.md#one-time-setup" appears in a project
  that has nothing to do with frob (and that file is not in the project).
- `frob ticket fragment` writes `frob: Add mul to calc.` (compiled CHANGELOG strips it, but the fragment
  carries a "frob:" prefix, product name default).
- `frob check --explain NOPE001`: "no rule NOPE001; see docs/reference/rules" - that path only exists in the
  frob source tree, not for an installed binary; there is also no `frob check --list-rules`.
- Fix: gate "registry setup" on `[release] registry = ...` config; use the repo/product name in fragments or
  no prefix; make --explain error list near ids; ship the rule pages in the binary.

### F10 MEDIUM - Default definition of done requires a changelog fragment even when the project has no changelog
- Commands: `frob check --ticket T` -> `REL003 ticket has no changelog fragment`, `frob ticket close` of an
  epic -> `E-DONE-CHANGELOG-FRAGMENT`. A project that does not want changelog.d must set
  `[pm] done_requires` (long knob) or close with `--no-changelog --reason` each time (epics always need it).
  Docs never tell a new user this on init. Also closing any task needs measured evidence
  (E-EVIDENCE-MISSING remedy only suggests nextest; a docs ticket needs `--provider command|file`).
- Fix: have `frob init` ask/offer presets (`--profile minimal|full`); exempt epics/containers from the
  fragment and evidence guards; mention provider=file for docs in the remedy.

### F11 MEDIUM - v1 frob.toml handling inconsistent and the guide's config advice is thin
- Commands: `frob init` / `frob doctor` / `frob check` in a repo whose frob.toml has `[tickets]
  default_milestone`.
- Happened: `init` -> `error[E-CONFIG]: unknown key default_milestone in [tickets]; remedy: fix frob.toml as
  described, then rerun` (the "suggestion=None" is visible only in a stderr WARN). `doctor` and `check`
  print the same WARN but exit 0 with config.error none and `ok: true`. The guide says init and config
  show fail; check/doctor do not. No v1->v2 config mapping exists.
- Fix: one behaviour (warn+continue everywhere, or fail everywhere); E-CONFIG message should name file, line
  and the nearest valid key; ship a key-mapping table for v1 keys in the migration guide.

### F12 MEDIUM - Worktrees default to a sibling dir outside the repo; Cargo.lock/untracked build files block cut
- `[worktree] dir = "../{repo}-wt"`: `frob work` writes outside the project root. A sandboxed agent (Claude
  Code with project-only write permission) will be denied; docs do not warn or show `--worktree`/config.
- `frob release cut` refused `E-CUT-DIRTY: Cargo.lock` after tests generated it (fine, correct) but `frob
  init` does not offer `.gitignore` entries for build output or suggest committing Cargo.lock.
- Each Rust ticket worktree needs its own cargo build (first nextest run was 2.5 s even trivial; real crate
  = full compile per worktree). A shared `CARGO_TARGET_DIR` hint is not given.
- Fix: document the sandbox implication and a `.claude/settings` allow rule; suggest target dir sharing.

### F13 MEDIUM - Agents working on the primary checkout (`work --here`): no base to diff against
- With `frob work --here` and commits made on main, `frob check --ticket` (base=main) and `frob test
  --base main` see an empty diff ("no tests reach the touched set; nothing was run"); you must pass an
  explicit older sha, and every evidence commit moves HEAD so `--base HEAD~n` drifts (my own mistake cost
  two runs). Not mentioned in docs (the migration table says "--here: no new worktree").
- Fix: record the lease's start commit and use it as default base for --here leases; say so in help.

### F14 LOW - Cosmetic / consistency
- `cycle new` JSON says state "active", the following `cycle assign` says "planned", `cycle show` says
  "active" (same day). `cycle close` requires <CYCLE> while `cycle show` defaults to current.
- `cycle plan` with fewer than 3 closed cycles: E-CYCLE-NO-CAPACITY, the remedy `frob cycle plan --points N`
  is good, but a brand-new repo must always pass --points (first run of every project).
- `milestone add <EPIC> <VERSION>` : args reversed from `milestone show/criterion add <VERSION>`; swapping them
  gave "no milestone has version ~EQBN3GA" (no hint about the order).
- `lease widen` takes `--glob`, but `--add`/`--add-scope` is what users reach for; error gave no hint.
  (`ticket update --add-scope` does rescope the lease; fine, but not documented as the way.)
- `ticket evidence add` is not idempotent: repeating it appends another record.
- Unknown subcommand remedies are random nearest-name guesses: `frob vet` -> remedy "frob test",
  `frob rules` -> "frob release".  Usage errors have `"verb": null` in the envelope and the "remedy: usage"
  string echoes `--text`/`--json` back.
- JSON strings contain a Rust-style `\u{2500}` escape in evidence transcripts (valid JSON text, not a JSON escape).
- Help for group verbs is "ticket commands", "cycle commands", "config commands" - no description.
- `frob doctor` reports a stale `crunk 0.1.1.dev45` from PATH (~/.local/bin/crunk) as the crunk sibling.
- Epics count as done-with-unclosed epic: `release status` said READY with the milestone epic still open
  (only the fragment guard noticed it when I closed it).
- `ticket list` shows parent as a full ULID, not the handle.

## Step 3: agent ergonomics

- JSON: every verb accepts `--json`; auto-switches to JSON when stdout is not a tty (verified). Envelope
  `{verb, already, ok, data, findings, warnings, error{code,message,remedy,retryable}, schema_version:1}` is
  stable across verbs (also for usage errors; `verb` is null there). `frob <verb> --schema` and `frob schema`
  print JSON schemas. Tracing logs go to stderr, stdout stays one JSON document (verified). Gap: success
  `warnings` are often only on stderr as text; JSON `warnings` stayed `[]` for e.g. "unresolved TEST001"
  that the text view printed.
- Errors teach: code, cause, remedy command, `retryable`. Best examples: E-WIP-REPO (lists holders),
  E-NO-CONFIG, E-DONE-UNMERGED, E-CYCLE-NO-CAPACITY, REL003, SCOPE001. Weak: F8, F11, bare `remedy: null`
  on E-USAGE (points, outcome) and E-LINK-SELF.
- Exit codes: 0 ok, 1 negative, 2 usage, 3 refused, 4 internal: consistent in all my probes.
- Missing for a Claude Code agent in the project:
  * MCP server: `frob serve` absent (known). README still advertises it.
  * `frob vet` (dependency vetting hook) absent: `frob vet --json` -> E-USAGE unrecognized subcommand.
  * No `frob agent`/guard env, no `frob claude`/sync-skills equivalent: nothing generates a CLAUDE.md /
    `.claude/settings.json` stanza (permission allowlist for frob verbs, a PreToolUse hook that blocks edits
    outside the lease scope, a Stop hook running `frob check --ticket`). Suggest `frob init --agent claude`.
  * No "what should I do now" verb for agents beyond `ticket doable`; `doable` lists unscoped tickets and
    epics are excluded but there is no rank/why field. (WIP default of 2 repo-wide is tight for several agents;
    per-identity limit counts actor+worktree so agents in separate worktrees each get one.)
  * No `frob check --list-rules`, no machine-readable rule catalogue outside the source tree.
  * `ticket list` JSON lacks scope/acceptance (need `ticket show` per ticket).
  * Output of `work` is large (lease history etc.); an agent needs only path/branch/scope.
- grimble/crunk: both binaries exist. `grimble init` then `frob check` picked grimble up as a sibling
  (found "beside-frob"; not on PATH otherwise, `doctor` says absent). grimble check printed WARN "root file
  is not among the supplied files design/model.grmb" 3 times on a freshly `grimble init`-ed repo (7.4 s,
  debug build). `crunk check` needs crunk.toml (clear error). docs/crunk/README.md says the rule set is empty.
  No user guide for grimble.

## Timings (> 2 s flagged; everything else <= 0.7 s)

| command | wall | note |
|---|---|---|
| `frob init` in v1repo (first run) | 2.51 s | later runs fast |
| `frob ticket doctor` first run after migration | 2.4-3.1 s | 0.11 s later |
| `frob doctor` | 0.7-4.8 s, varied run to run (1.0 s typical) | toolchain/sibling probes + gc |
| `frob test` rust (cold cargo compile, debug) | 2.46 s | expected |
| `frob check` with tool stages (ruff+clippy) | 1.76 s cold, 0.25 s warm | |
| `grimble check` (debug build) | 7.37 s | outlier, 0.3 s init |
| `frob land` | 0.7-1.1 s | |
| everything else (ticket/cycle/milestone/board/work/requeue/release) | 0.02-0.5 s | |
(debug build; machine also running other work, so treat the doctor spread as noise-plus.)

## Must fix before adopting in another project (ranked)

1. F2 Rust crate in a subdirectory: `frob test` fails (nextest at repo root). Layout-dependent, silent cause.
2. F1 Write the quickstart + concepts guide and fix the README (docs are the only thing a new project has).
3. F4 Release for python/mixed projects: bump pyproject, stop silently restructuring Cargo.toml, write a
   generic release guide (or state release is Rust-only).
4. F10 + F6 Make a fresh project's defaults quiet and workable: preset or one-line opt-out for changelog
   fragments, epics exempt from evidence/fragment guards, exempt frob-owned files from the 7 unresolved lines.
5. F13 `work --here` default base (otherwise `check --ticket`/`test` see an empty diff on the main checkout).
6. F5 Fix the migration doc (`--all`, step order) and default `--selection` to "all" when the file is absent;
   better, ship the importer in the binary.
7. F3 Either support the orphan ticket branch through work/land or document that it is unsupported and refuse
   early.
8. F8 Surface the cause of failed test runs in the error and stop recording noise commits.
9. F7 Real text views for list/check/mutating verbs (humans and agents reading logs).
10. Agent kit: `frob init --agent claude` writing allowlist + hook + CLAUDE.md snippet; remove `frob serve`
    and `frob vet` from the README until they exist (dependency vetting and MCP are the known gaps).
11. F9 frob-specific leaks (registry setup line, `frob:` fragment prefix, rule docs path) in non-frob repos.
12. F12 Document the out-of-repo worktree default for sandboxed agents.

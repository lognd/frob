# CLI contract and verb surface

Status: current
Owner: frob
Decisions: none
Audience: contributor

Provenance: written under T-0001 (a v1-format id that migrates with an alias). Inputs: notes/v1/cli-surface.md (51 verbs, 243
parser nodes), notes/v1/agent-usage.md (36,610 agent calls over 34
days; 30,467 process calls over 13 days).

## 1. What the usage data says

- Concentration: 14 verbs are 79 percent of agent calls (check, land,
  show, evidence, scope, new, done-report, work, body, start, metadata
  setters, promote). 20 verbs cover 99 percent. Six ticket verbs and
  nine top-level verbs were never used.
- Exit codes are overloaded: `check` exits 1 on 98 percent of calls and
  `verify status` on 88 percent, meaning "findings exist" or "not
  ready", not "tool failed". Agents cannot tell the two apart.
- Half of failures are blind retries with identical arguments; `work`
  on an already-started ticket errors instead of returning the lease.
- Draft ids cost 958 promote calls at 62 percent failure, 59 hand
  repairs, and 100 "exists only on this branch" refusals.
- Half of all process invocations were `land --status` polls (v2 has no
  land status to poll: `land` is synchronous, section 3).
- Metadata ceremony: 3,149 one-field setter calls at 5 to 13 s each.
- `--json` on 3 percent of calls; agents scraped text with grep, tail,
  sed. The most common line agents saw was an informational notice
  prefixed "ERROR:".
- 8 percent of agent calls were `--help`; 2,642 usage dumps.

## 2. Output contract

Every verb, every time:

```json
{"verb": "ticket.update", "already": false, "ok": true, "data": {...},
 "findings": [], "warnings": [], "error": null, "schema_version": 1}
{"verb": "ticket.start", "already": false, "ok": false, "data": null,
 "findings": [], "warnings": [],
 "error": {"code": "E-LEASE-HELD", "message": "...",
           "remedy": "frob work --here ~6C0D1E2 --wait 60",
           "retryable": true},
 "schema_version": 1}
```

- The envelope is `gob_diagnostics::Envelope` (`ok`, `data`,
  `findings`, `warnings`, `error`, `schema_version`); `gob-cli` wraps it
  with two fields in front, `verb` (the dotted verb path) and `already`.
  The fields `next`, `elapsed_ms`, `retry_after_ms` and `holder` shown
  in earlier drafts are not modelled yet; frob-lease adds the holder and
  retry hint, and `next` and `elapsed_ms` are Milestone 2 or later (D36).
- Output is chosen by `--format json|text|auto`; `auto` (the default) is
  JSON when stdout is not a TTY and text when it is. `--json` and
  `--text` are aliases of `--format json` and `--format text`. Text
  rendering is a view over the same envelope, so nothing exists in text
  that is absent from JSON.
- A verb whose gate fails with findings (`check`, exit 1) returns `ok`
  false with every finding as a structured record in `findings`, the
  verb `data` kept, and a one-line `error.message` summary; the finding
  lines are text-view detail only (`CliError::Findings`). Sibling
  products keep the `ok` true document-on-exit-1 form (`CliError::Gate`).
- Exit codes are one table, implemented as `gob_diagnostics::RefusalClass`
  (`DomainNegative` 1, `UsageError` 2, `GuardRetryByWaiting` 3 with
  `retryable`, `GuardNeedsAction` 3, `Timeout` 3 with `retryable`,
  `Internal` 4); `ExitCode` converts to `i32` because the crate may not
  name `std::process`, and the `frob` binary builds the process exit.
  Agents branch on the code, not on prose.
  `retryable` means exactly one thing: the same argv may succeed later
  without any other action by the caller.

| Code | Class | `retryable` | When | Examples |
|---|---|---|---|---|
| 0 | ok | not present | the verb did what was asked; domain states that are answers are not failures | `check` with findings and no `--fail-on` (and no required Unresolved, see below); an idempotent repeat (`already: true`); `cycle assign` within capacity; `forecast` below `min_history` (reported as Unresolved with the sample count) |
| 1 | domain negative | false | the caller asked for the verb's yes/no answer as an exit code and the answer is no | `check --fail-on error` (or `[check] fail_on`) with a finding at or above the level; `check` with a required Unresolved finding under `[check] fail_on_unresolved`; `test` when a selected test fails |
| 2 | usage | false | bad flags, unknown verb, input that fails its schema | `E-USAGE` with did-you-mean |
| 3 | guard, clears by waiting | true | a guard that clears without caller action; `retry_after_ms` is set | `E-LEASE-HELD` (holder named), land lock held, ledger CAS lost after `[git] cas_retries`, `E-WAIT-TIMEOUT` (a `--wait <secs>` expired before the lock freed) |
| 3 | guard, needs action | false | a guard that needs the caller to change something; `remedy` is the exact command | `ticket close` with missing evidence (`E-CLOSE-EVIDENCE`), dirty root, `E-STATE-TRACKED` (git tracks a state or cache directory), empty scope, `cycle assign` over capacity (remedy `--over-commit --reason`), `land` whose check failed (`E-LAND-CHECK`), stale plan token (`E-PLAN-STALE`), a file changed between `check` and `check --fix` (`E-FIX-STALE`, remedy rerun `frob check` then `--fix`) |
| 4 | internal error | false | a bug, with a report path in the envelope | `E-INTERNAL` |

- There is no "job failed" class in milestone 1: `land` is synchronous
  (D25), so a failed check inside `land` is a guard that needs action.
- The environment never changes the exit contract. The earlier CI
  environment switch is gone: set `[check] fail_on` in `frob.toml`
  (materialized, architecture.md section 6) or pass `--fail-on <severity>`.
- Unresolved and the gate (the one mechanism; rules.md section 4 step 8,
  products.md, boundaries.md, grimble-model.md 9.5 and universal-model.md
  4.2 refer here). `Unresolved` is a finding severity orthogonal to the
  `Error | Warn | Advisory` threshold: `--fail-on` and `[check] fail_on`
  never count it. A materialized knob `[check] fail_on_unresolved =
  "required" | "never" | "all"` (default `"required"`) adds a second
  test to the gate: under `"required"`, a finding that is Unresolved and
  marked `required` fails the gate with exit 1 (a negative domain
  answer), never exit 3, which stays reserved for refusals; `"all"`
  fails on any Unresolved and `"never"` on none. The required
  Unresolved findings are exactly three: (a) a configured sibling
  product that is unusable, in any of five reasons, all required:
  `absent` (not installed), `incompatible` (`--json` with another
  `schema_version` or a different `[compute]` digest), `failed` (exit 2,
  3 or 4, a failure envelope or a spawn error), `timeout` (`[check]
  sibling_timeout_secs` elapsed) and `malformed` (stdout not exactly one
  schema-valid document, or over the output cap), reported as one
  `SIB001` per product (sibling-contract.md section 6);
  `[check] require_siblings`, default true, is what makes a configured
  sibling required; (b) an `annotation-required` opaque on the public
  surface when `[compute]` requires the declaration (universal-model.md
  4.6); (c) a rule flagged `must_measure` that examined zero subjects.
  Every other Unresolved is reported, counted in the summary, and does
  not fail under `"required"`. The `required` mark travels on the
  finding record and in sibling JSON, so frob applies it to a sibling's
  findings without re-deriving it. Landed state: `gob-diagnostics`
  (`exit.rs`) skips Unresolved today; changing it is the first item of
  build-test-ci.md Milestone 2.
- `frob check` merges sibling findings under this same contract; crunk
  and grimble adopt it (crunk's v1 0/1/2 contract maps onto it: exit 1
  only through `--fail-on`).
- `--schema` on any verb prints the bare JSON schema of that verb's
  data payload (not of the envelope or its inputs) and exits; `frob
  schema` dumps all. Generated from the handler types. `--schema` waives
  every required positional and flag of the verb (the root rebuilds the
  clap tree with arguments optional when argv carries `--schema`), so
  `frob work --schema` prints the schema and exits 0.
- Every error names the exact corrected command in `remedy`.
- No prefix abbreviation of flags (clap `infer_long_args = false`);
  did-you-mean on unknown verbs and flags.
- A verb path may have any number of words (`ticket show`, `graph why`,
  `ticket evidence add`): the `gob-cli` command tree nests one clap
  subcommand per word. `ticket evidence add|list|fetch` are three real
  verbs with their own `--help`, `--schema` and verb names
  (`ticket.evidence.add` in the envelope).
- `--dry-run` is a per-verb opt-in declared in the verb's metadata
  (`#[derive(Command)]`), not a global flag; a verb that does not opt in
  rejects it as a usage error.

## 3. Verb semantics

- Idempotent mutations: repeating a request that already holds returns
  `ok: true, already: true` and exit 0. `work` and `work --here` are
  idempotent only for the same holder (actor plus worktree path): the
  holder gets the existing lease and worktree back; any other caller
  gets exit 3 `E-LEASE-HELD` naming the holder. `new` creates a distinct
  ticket unless the call carries `--idempotency-key K` (stored on the
  created event; the same key returns the same ticket) or is an
  identical full request (same type, title, body, scope and links);
  two tickets with the same title and different bodies are two tickets.
- Worktrees: `frob work <ticket>` creates `../<repo>-wt/<handle>` (the
  parent is `[worktree] dir`, default `../{repo}-wt`; `<handle>` is the
  `~handle` without the `~`, which git refs forbid) on branch
  `ticket/<handle>`, records that path in the lease, and on a repeat by
  the holder reuses the worktree found through the lease (or, if the
  lease is gone, through the branch name). `frob work --here` (hidden alias `start`) takes the
  lease for the current checkout and records that checkout's root as the
  holder path.
- Acceptance: `ticket update <id> --add-acceptance TEXT` (repeatable,
  the text is taken whole, commas included), `--remove-acceptance N`
  (repeatable, 1-based as `show` and `brief` number them) and
  `--clear-acceptance`; each command writes one `field` event carrying
  the old and new lists and an index map (tickets.md section 2a), and
  removing a criterion that has bound evidence reports that evidence.
- Batching: `ticket update <id> --set priority=high --set points=3
  --add-label x --link blocks:01J9QKX3M8Z4T7N2V5B6C0D1E2` is one commit,
  one lock. `frob batch` (Milestone 2 or later (D36)) reads JSON lines
  of verb calls from stdin, accepts only ledger-only verbs (`ticket
  new|update|link|unlink|comment|body|accept`), and is all or nothing:
  one lock, one commit, and any failing line aborts and writes nothing.
  Verbs with side effects outside the ledger (`work`, `land`,
  `check --fix`) are refused inside a batch.
- Preview: `--dry-run` on the mutating verbs that opt in returns the planned
  changes in the same envelope in milliseconds and a `plan` token. A
  plan token is the BLAKE3 digest of the request, the inputs it read
  and the planned diff; it is stored nowhere. `--apply <plan>`
  recomputes the digest and refuses with `E-PLAN-STALE` (exit 3, needs
  action) if any input changed.
- Waiting: `land` is synchronous and prints LAND-PROOF; there are no
  job records and no job verbs in milestone 1 (D25). `--wait <secs>` on
  `land` and on lease-taking verbs bounds lock acquisition only; when it
  expires the verb exits 3 `E-WAIT-TIMEOUT` with `retryable: true`. If
  jobs ever exist they arrive with the daemon and a job store under
  `.git/frob/jobs/`. No polling loops.
- `check --ticket <id>` adds the ticket's scope-and-lease context and
  narrows per-file rules to the ticket's files plus `[check]
  ticket_hops` hops of dependents (rules.md section 4 is the single
  definition). The text view leads with findings on paths in the
  ticket's diff (the same branch-changes set SCOPE001 judges), always
  prints errors, required and gate-failing findings in full, and folds
  the rest into one count line per rule and severity; `-v` lists them
  all and `--json` is unchanged (every finding present).
- `ticket evidence add --ref` (~XR3342F): the value is taken whole even
  when it starts with `-`. For `nextest` it is the filter arguments for
  `cargo nextest run`; for `command` it is the command line. Both are
  tokenized with POSIX shell quoting and never reach a shell: whitespace
  separates words, `'...'` is literal, `"..."` honours backslash only
  before `"`, `\`, `$`, backtick and newline, and an unquoted backslash
  escapes the next character. No expansion happens (`$`, `|`, `;`, `*`
  and `#` are ordinary characters), and the words go to the tool as an
  argument vector. An unterminated quote or a trailing backslash is a
  usage error (exit 2, `E-EVIDENCE-REF`) and records nothing. `file`
  takes the value as a path, untokenized.
- Reads never take locks or commit; they are served from the index.

## 4. Verb surface

### 4.0 Verb admission (D104)

A verb exists only for its own effect (it writes something), its own
policy (semantics of its own, such as the board's WIP limits shared with
PM013 or doable's lease-aware dispatch order) or its own object (a noun:
cycle, release, lease). A different presentation of an existing query is a
flag (`--tree`, `--brief`, `--format md`, `--live`), never a verb; an
analysis of an object lives under that object's noun; each metric family
and each forecast is computed in exactly one place and only displayed
elsewhere. The v1 usage data (section 1: six ticket verbs and nine
top-level verbs never used) is the reason. A test fails when a registered
verb has no row below naming its justification (effect, policy or object).
Removed verbs keep a hidden alias for one minor release, then go.

One table is the source of truth: every verb, the product that ships
it, the crate that owns the handler, whether a repeat of the same
request is safe, the exit codes it can return (table in section 2), and
the milestone that builds it (D36). Verbs marked 2 are designed here and
described in their own files, and are Milestone 2 or later (D36).

| Verb | Product | Crate | Idempotent | Exit codes | M |
|---|---|---|---|---|---|
| `init` | frob | frob (bin) | yes, adds only missing knobs; a missing `[tickets] ref` is written as `refs/heads/<default branch>` and a missing `[check] base` is that default branch: the remote HEAD of `origin` when present, else a local `main`, else the checked-out branch (an unborn branch counts, a detached HEAD is refused with `E-DETACHED-HEAD`); `--ledger-ref refs/heads/<branch>` overrides the ref; `config sync` detects both the same way; an existing value is never changed; the merge driver is written as bare `frob` only when `frob` on PATH (resolved without a shell) is the running executable (same canonical path, else same version), otherwise as the running executable's absolute path, and the output says why; `--driver-command TEXT` overrides; an existing driver that resolves to the running frob is left alone, one that resolves to a different frob is reported and rewritten only with `--fix-driver` | 0 2 3 4 | 1 |
| `doctor` | frob | frob (bin) | yes; reports a ledger merge driver that resolves to a different frob than the running one (or to nothing) with the exact fix command (`<running frob> init --fix-driver`); reports each sibling binary (`siblings`: location `beside-frob`, `path` or `absent`, its version, and a second copy with a different version, D87); reports each corrupt lease file (`leases.corrupt`: path and parse error) as a warning with its remedy; `--fix` installs the merge driver and moves corrupt lease files aside as `<name>.toml.corrupt` (`leases.quarantined`), never deleting them | 0 2 4 | 1 |
| `doctor --languages` | frob | frob (bin) | yes, read-only; prints per-language fidelity level, capability precision and the rules that are NotApplicable once per language (universal-model.md 3.3, 4.2) | 0 2 4 | 2 |
| `init --ci` (open question, cicd.md section 7) | frob | frob (bin) | yes, adds only missing files | 0 2 4 | 2 |
| `audit --online` (open question, cicd.md section 7: the online action-currency and advisory check) | frob | frob-check | yes, read-only | 0 2 3 4 | 2 |
| `config show --effective` | frob | gob-config | yes, read-only | 0 2 4 | 1 |
| `config sync` | frob | gob-config | yes | 0 2 4 | 2 |
| `schema` | frob | gob-cli | yes, read-only | 0 2 4 | 1 |
| `stats [--section velocity\|capacity\|cost\|activity\|flow] [--live]` (one metrics verb, frob-metrics; absorbs `cycle velocity`) | frob | frob-pm | yes, read-only | 0 2 4 | 2 |
| `clean` | frob | gob-cache | yes | 0 2 4 | 2 |
| `migrate tickets\|directives\|config\|exceptions` | frob | frob-ledger | yes, skips what is imported | 0 2 3 4 | 2 |
| `exceptions list` | frob | frob-obligations | yes, read-only | 0 2 4 | 1 |
| `exceptions audit\|convert\|prune\|budget` | frob | frob-obligations | yes | 0 2 3 4 | 2 |
| `narrative move` | frob | frob-obligations | yes | 0 2 3 4 | 2 |
| `rule test` (also `grimble rule test`) | frob, grimble | gob-rules | yes, read-only | 0 1 2 4 | 2 |
| `batch` | frob | frob-ledger | yes, all or nothing | 0 2 3 4 | 2 |
| `ticket new` | frob | frob-ledger | only with `--idempotency-key` or an identical request | 0 2 3 4 | 1 |
| `ticket show [--events] [--format md]`, `ticket list [--tree] [--category C] [--full]` (`--full` adds every row's aliases and events in one pass) | frob | frob-ledger | yes, read-only | 0 2 4 | 1 |
| `ticket doable` (policy: lease-aware dispatch order) | frob | frob-lease | yes, read-only | 0 2 4 | 1 |
| `ticket update\|link\|unlink\|comment\|body\|accept` | frob | frob-ledger | yes, same request | 0 2 3 4 | 1 |
| `ticket attach\|component` | frob | frob-ledger | yes | 0 2 3 4 | 2 |
| `ticket triage accept\|decline\|snooze\|duplicate` | frob | frob-ledger | yes; a repeat of the same decision is `already`, one ledger commit per call (tickets.md section 11.1) | 0 2 3 4 | 1 |
| `ticket triage` list view is `ticket list --category triage` | frob | frob-ledger | yes, read-only | 0 2 4 | 1 |
| `ticket evidence`, `ticket done-report` | frob | frob-evidence | yes | 0 2 3 4 | 1 |
| `ticket evidence fetch` (the action `fetch` is a positional of `ticket evidence`) | frob | frob-evidence | yes | 0 2 3 4 | 2 |
| `work [--here]`, `requeue` (top-level: lease and worktree lifecycle) | frob | frob-lease | `work --here` only for the same holder; others get 3 | 0 2 3 4 | 1 |
| `ticket close\|drop\|reopen` | frob | frob-ledger | yes | 0 2 3 4 | 1 |
| `ticket review` | frob | frob-ledger | yes | 0 2 3 4 | 2 |
| `ticket reconcile\|doctor` | frob | frob-ledger | yes | 0 2 3 4 | 1 |
| `merge-driver` (hidden, git invokes it) | frob | frob-ledger | yes, pure union and re-fold | git contract: 0 merged, 1 conflict | 1 |
| `cycle new\|assign\|plan\|close`; `forecast <milestone\|epic\|ticket\|release>` (the one forecast) | frob | frob-pm | yes | 0 2 3 4 | 2 |
| `board [--brief] [--live]` | frob | frob-pm | yes, read-only | 0 2 4 | 1 |
| `lease list [--contention]` | frob | frob-lease | yes, read-only | 0 2 4 | 1 |
| `work <ticket>` | frob | frob-worktree | only for the same holder; others get 3 | 0 2 3 4 | 1 |
| `worktree sweep\|remove` | frob | frob-worktree | yes | 0 2 3 4 | 2 |
| `land <ticket> [--wait <secs>] [--dry-run]` | frob | frob-land | yes, a landed ticket returns `already` | 0 2 3 4 | 1 |
| `check [--ticket] [--fix] [--fail-on]` | frob | frob-check | yes | 0 1 2 3 4 | 1 |
| `fix` | frob | frob-check | yes | 0 2 3 4 | 1 |
| `ack` | frob | frob-ack | yes | 0 2 3 4 | 1 |
| `test [--base]` | frob | frob-tests | yes | 0 1 2 4 | 1 |
| `coverage` | frob | frob-tests | yes | 0 2 4 | 2 |
| `graph why\|affects` | frob | frob-ack | yes, read-only | 0 2 4 | 1 |
| `graph query\|outline\|map\|xref` (one graph noun; `explore` folds into it) | frob | frob-explore | yes, read-only | 0 2 4 | 2 |
| `release new\|stamp\|sync\|publish\|status\|changelog` (status prints the `forecast` line) | frob | frob-release | yes | 0 2 3 4 | 2 |
| `serve [--mcp\|--http]` (no `tui` verb: `board --live` and `stats --live` exec the sibling `frob-live` binary, D105) | frob | frob-serve | not applicable | 0 2 4 | 2 |
| `hook <event>` | frob | frob-hook | yes | 0 3 4 | 2 |
| `fleet status\|route` | frob | frob-fleet | yes, read-only | 0 2 4 | 2 |
| `git -- ...` | frob | gob-exec | explicit passthrough | 0 2 4 | 2 |
| `frob2 compare --against frob` | frob | frob (bin) | yes, transitional (migration.md) | 0 2 4 | 2 |
| `grimble check\|status\|graph\|shrink\|init\|packs` | grimble | grimble-check | yes | 0 1 2 3 4 | 2 |
| `grimble doctor [--languages]` | grimble | grimble-check | yes, read-only | 0 2 4 | 2 |
| `grimble fmt` | grimble | grimble-model (the alpha-normal printer) | yes | 0 2 4 | 2 |
| `grimble exceptions list` | grimble | grimble-check over gob-rules | yes, read-only | 0 2 4 | 2 |
| `grimble ack` | grimble | grimble-bind on gob-lock | yes | 0 2 3 4 | 2 |
| `grimble vet [--hook]` | grimble | grimble-vet | yes | 0 1 2 4 | 2 (after the G01-G19 cut; build-test-ci.md Milestone 2 item 8) |
| `grimble explore outline\|map\|xref` | grimble | grimble-check over gob-symbols | yes, read-only | 0 2 4 | 2 |
| `grimble serve --mcp` | grimble | grimble-serve | not applicable | 0 2 4 | 2 |
| crunk verbs (notes/crunk.md section 1) | crunk | crunk-* | per crunk | the shared table in section 2 | 2 |

`frob check` merges sibling findings when they are installed or linked
(products.md section 1, boundaries.md section 1). `status` exists in
two products with different meaning: `frob status` is work and
exceptions, `grimble status` is model drift. `migrate` in frob is only
the v1 importer; there are no v2-to-v2 migration verbs.

Removed from frob relative to v1: promote, renumber, sweep-async (no
detached background land exists, D25), `job` and `land --status` (land
is synchronous), plan, fail, board-as-separate, epic, flow, all
deprecated aliases, parse, refactor, mutate, perf, deploy, natives,
process, claude, sync-skills, exports, whereis, ci, the quality/design/
ops groups, `waive audit` and `pool` (replaced by `exceptions`). v1's
`sys`, `cycle`, `dup`, `arch`, `bind` live in grimble; `vet` too
(boundaries.md section 2.3).

### 4.1 `serve`: read-only MCP from verb metadata (D134)

`frob serve [--mcp]` speaks MCP (newline-delimited JSON-RPC 2.0) on
stdin and stdout and lists one tool per live verb declared
`#[command(read_only)]`; there is no hand-written second API.

- Tool name: product and verb words joined by `_` (`frob_ticket_show`).
- Input schema: derived from the verb's own clap arguments (flags are
  booleans or integers for counts, repeatable options are arrays, enums
  list their values, positionals are named by their id), with
  `additionalProperties: false`. The verb's `data` schema is not in the
  listing (it is 100 KB across the tools); `frob <verb> --schema` prints it.
- Result: the same JSON envelope the CLI prints for the verb (the call
  runs the verb in-process with `--json`); `isError` is true for exit
  codes 2 and above, and a negative result (exit 1) is not an error.
- Absent by construction: any verb without `read_only` (default false),
  deprecated aliases, and the write flags `--fix` and `--dry-run` of
  read-only verbs; a call that names them is refused as invalid params.
- Server-side work happens only inside a call. Between calls the process
  blocks on stdin, so idle CPU is zero; EOF on stdin exits 0.
- Tools run in the directory `serve` was started in; point the client
  at the repository by launching it there (or with `--cwd`).

## 5. Human ergonomics kept

Color and tables on a TTY, `-v` for the span tree, shell completions,
man pages, `frob <verb> --help` generated from the same metadata as
the generated CLI reference (documentation.md section 3), and tickets
accepted by full ULID or by `~handle` (goals.md).

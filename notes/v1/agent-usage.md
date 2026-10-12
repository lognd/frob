# frob v1: how agents and the human actually used it

Purpose: behavioral evidence for redesigning the CLI and ticket system in Rust.
Complements (does not repeat) the per-subcommand count/median/p90 tables produced
separately. All numbers are measured from read-only data; scripts and
intermediates live in the session scratchpad, no source file was touched.

## 0. Method, universe and honest caveats

| Item | Value |
|---|---|
| Source A: .frob/telemetry.jsonl | 145,586 lines, 2026-09-15 .. 2026-09-27 (13 days) |
| A kinds | tool 112,263; cli 30,467; dispatch 1,828; ticket 807; gate_rule_counts 221 |
| Source B: Claude Code transcripts (-home-logan-projects-frob) | 753 JSONL files, 742 are subagent files, 11 are top-level sessions; 2026-08-25 .. 2026-09-27 (34 days), ~1.6 GB |
| B frob invocations extracted | 36,610 (resolved to a tool_result: 36,600; 10 unresolved) |
| Excluded | ~/.claude/projects/<project> (this redesign session, not v1 usage) |
| ticket verbs in the parser | 57 (regex over src/frob/_cli_parsers/_ticket); top-level verbs 52 |

Fields in `kind=cli`: args_head (<= 512 chars, truncated), subcommand, subverb/verb (absent on 19% of
records, so verb is re-parsed from args_head here), duration_ms, exit, iso_ts, tree_hash,
home_config_hash (4,089 distinct values: not an identity), external_path_hash ("none" on 94%).
There is NO message/error field in telemetry; failure reasons come only from transcripts.

Caveats that change how to read every number:

1. cli telemetry is partial. Agent-side `tool` records (7,723 frob invocations with verb parsed) show
   `ticket evidence` 682 and `ticket done-report` 346 times, while cli has 123 and 23. cli has ZERO
   `test`, `format`, `fmt` records although transcripts show 675 / 405 / 325 calls. Likely causes:
   worktree-local .frob dirs, un-instrumented verbs, and processes killed before the exit hook.
   Treat cli counts as a floor for work-heavy verbs and an accurate record for the cheap ones.
2. Polling loops are invisible in transcripts (one Bash call wraps `until ... sleep 6`) but dominate
   cli telemetry. The two sources therefore measure different things: A = process invocations,
   B = deliberate agent calls.
3. Exit code is overloaded as a status signal. `check --json` exits 1 on 436/443 calls, `verify status`
   on 88%: nonzero means "findings/not ready", not "tool broke". Raw exit-1 rates below are
   labelled accordingly.
4. Only 7 dispatch ids (long orchestrator sessions) carry tool records. 93% of transcript invocations
   come from subagents (workers in git worktrees), not the top-level sessions.
5. The human is nearly invisible. No `<bash-input>` frob command exists in any top-level
   transcript, and no telemetry field marks human vs agent (see section 5).

## 1. What was invoked (behavior, not latency)

### 1.1 Concentration

| Rank | Telemetry A (process calls, n=30,467) | share | cum | Transcripts B (agent calls, n=36,610) | share | cum |
|---|---|---|---|---|---|---|
| 1 | ticket land --status | 50.0% | 50.0% | check | 17.5% | 17.5% |
| 2 | verify status | 9.4% | 59.3% | ticket land | 10.2% | 27.6% |
| 3 | ticket new | 5.5% | 64.8% | ticket show | 9.5% | 37.1% |
| 4 | ticket show | 4.4% | 69.2% | ticket evidence | 9.4% | 46.5% |
| 5 | ticket sprint (assign) | 3.8% | 72.9% | ticket scope | 7.4% | 53.9% |
| 6 | ticket promote | 3.1% | 76.1% | ticket new | 6.7% | 60.6% |
| 7 | ticket land (plain) | 2.6% | 78.7% | ticket done-report | 6.5% | 67.1% |
| 8 | ticket work | 2.6% | 81.3% | ticket work | 5.2% | 72.3% |
| 9 | ticket land --dry-run | 2.2% | 83.5% | ticket body | 3.6% | 75.9% |
| 10 | ticket body | 1.8% | 85.3% | ticket start | 2.9% | 78.7% |

Family level: `ticket` is 87.6% of A and 72.1% of B. `check` is 17.5% of B. Excluding the land-status
poll, A's top 10 verbs are 70.6% of the remaining 15,243 calls, led by verify status (18.7%),
ticket new (11.0%), ticket show (8.7%), ticket sprint (7.5%), ticket promote (6.3%).

### 1.2 Ticket verb frequency, raw exit-1 rate, median duration (telemetry A)

Land is split by mode because the modes behave like different commands.

| Verb | n | exit 1 | median | Verb | n | exit 1 | median |
|---|---|---|---|---|---|---|---|
| land --status | 15,224 | 0.9% | 1 ms | ticket close | 51 | 90.2% | 17.6 s |
| ticket new | 1,674 | 58.3% | 8.3 s | ticket sweep | 35 | 2.9% | 39.2 s |
| ticket show | 1,326 | 7.5% | 2.4 s | ticket done-report | 23 | 0.0% | 138.8 s |
| ticket sprint assign | 1,144 | 14.2% | 7.3 s | ticket tier | 23 | 4.3% | 10.7 s |
| ticket promote | 958 | 61.7% | 5.3 s | ticket requeue | 22 | 45.5% | 7.6 s |
| land (plain) | 804 | 49.5% | 84 s | ticket fail | 20 | 55.0% | 5.4 s |
| ticket work | 784 | 72.7% | 52.3 s | ticket brief | 21 | 0.0% | 3.7 s |
| land --dry-run | 680 | 53.7% | 158 s | ticket attach | 14 | 14.3% | 2.6 s |
| ticket body | 538 | 29.0% | 10.0 s | ticket contention | 12 | 0.0% | 2.5 s |
| ticket scope | 491 | 27.9% | 13.2 s | ticket priority | 12 | 91.7% | 9.1 s |
| ticket points | 478 | 17.4% | 6.6 s | ticket epic | 10 | 0.0% | 0.18 s |
| land --queue | 413 | 62.2% | ~0 s (2 ms) | ticket reopen | 6 | 0.0% | 3.8 s |
| ticket block | 317 | 20.2% | 5.4 s | ticket doable | 5 | 0.0% | 244 s |
| ticket milestone | 187 | 7.5% | 5.8 s | ticket kind | 3 | 66.7% | 9.5 s |
| ticket set-parent | 184 | 59.8% | 6.6 s | ticket board | 3 | 0.0% | 69 ms |
| land --drain | 281 | 66.5% | 356 s | ticket reconcile | 3 | 0.0% | 28.7 s |
| ticket sweep-async | 174 | 75.9% | 952 s | ticket scope-ack | 1 | 0.0% | 10.6 s |
| ticket list | 145 | 0.0% | 0.7 s | ticket archive | 2 | 0.0% | 6.6 s |
| ticket evidence | 123 | 17.9% | 18.1 s | ticket wave / admin | 2 / 2 | 0% / 50% | 110 s / 17 s |
| ticket merge-driver | 94 | 0.0% | 2 ms | ticket accept | 60 | 13.3% | 7.8 s |
| ticket drop | 94 | 54.3% | 4.7 s | ticket unblock | 58 | 29.3% | 5.3 s |
| ticket set | 92 | 1.1% | 6.6 s | ticket start | 86 | 57.0% | 11.1 s |
| verify dispose | 92 | 25.0% | 1.0 s | | | | |

Non-ticket verbs: verify status 2,849 (88.5% exit 1, status semantics), verify drain-async 335 (66.6%),
check 443 (98.4%, status semantics), vet 8, xref 16, natives build 13, explore 12.

Reading it:

- Mutating metadata verbs take 5-13 s each (sprint 7.3 s, points 6.6 s, milestone 5.8 s, set-parent 6.6 s)
  because each is a commit-producing ledger write. `land --status` is 1 ms: a read of local state.
  The 3,149 calls to sprint/points/milestone/set-parent/tier/priority/set/body/scope (10.3% of A) are
  a metadata ceremony that `ticket new` is supposed to absorb but does not (see 1.3).
- High raw exit-1 on new (58%), promote (62%), work (73%), start (57%), drop (54%), close (90%),
  land (50-67%) are genuine refusals (transcripts section 3 names them), not status codes.
- `land --queue` exits 1 in about 2 ms on 62% of calls: probably a "queued, not landed yet" return
  code; unverified, but exactly the kind of overloaded exit semantics v2 should split.

### 1.3 Flags actually used per verb (telemetry A; share of that verb's calls)

| Verb | Flags observed (share of calls) |
|---|---|
| ticket new (1,674) | --kind 100, --title 100, --body-file 78, --scope 76 (repeated), --priority 72, --parent 72, --tier 51, --sprint 49, --milestone 42, --origin 30 (lower bound, args truncated), --ack-related 15, --acceptance, --blocked-by, --component 8, --wait 16, --json 17 |
| ticket land (17,402) | --status 87, --worktree 11, --dry-run 4, --allow-cross-ticket 3.4, --queue 2.4, --drain 1.6, --onto 0.7, --push ~0 |
| ticket body (538) | --reason 94, --append-file 51, --set-file 38, --wait 33, --no-commit 22, --append 10, --only 8 |
| ticket scope (491) | --reason 98, --add 85, --path 25, --remove 16, --wait 13, --declare-no-scope 9, --no-check 1 |
| ticket show (1,326) | --json 14, --path 8 |
| ticket evidence (123) | --path 88, --base-ref 88, --accepts 68, --designate-repro 12, --check-repro 5 |
| ticket close (51) | --no-behavior-change(-reason) 73, --accepts 49, --evidence-cmd 49 |
| ticket drop (94) | --reason 100, --absorbed-by 37 |
| ticket start (86) | --path 47, --unsized-ack 2, --steal 1 |
| check (443) | --json 95, --budget 9, --only 6, --base 4, --files 2 |
| verify dispose (92) | --file-ticket 99, --reason 30 (flag prefixes truncated: --fil, --reas, --f seen: argparse abbreviation in use) |

Cross-check from transcripts B (flag presence over the matched frob segment): --ticket 3,935,
--reason 3,727, --only 3,499, --worktree 3,207, --help 2,969, --add 2,185, --title 2,088, --kind 2,076,
--json 1,960, --scope 1,693, --why-file 1,536, --body 1,086, --base-ref 1,030, --dry-run 684.

Mandatory-ish ceremony flags: --reason is attached to 98% of scope calls, 94% of body, 100% of drop,
tier, unblock. --worktree is passed on 82% (3,055/3,723) of agent land calls: it is effectively
required (a refusal exists for omitting it, section 3).

### 1.4 Top 20 full args_head shapes (telemetry A; ids/values normalized)

| # | n | exit 1 | median | shape |
|---|---|---|---|---|
| 1 | 15,224 | 1% | 1 ms | ticket land --status ID |
| 2 | 2,848 | 88% | 4.0 s | verify status |
| 3 | 1,130 | 14% | 7.4 s | ticket sprint assign ID NAME |
| 4 | 979 | 4% | 2.3 s | ticket show ID |
| 5 | 958 | 62% | 5.3 s | ticket promote ID |
| 6 | 764 | 73% | 52.9 s | ticket work ID |
| 7 | 564 | 55% | 161 s | ticket land ID --worktree P --dry-run |
| 8 | 478 | 17% | 6.6 s | ticket points ID N |
| 9 | 454 | 43% | 83.5 s | ticket land ID --worktree P |
| 10 | 411 | 63% | 2 ms | ticket land ID --worktree P --queue |
| 11 | 362 | 99% | 277 s | check --json |
| 12 | 335 | 67% | 326 s | verify drain-async |
| 13 | 264 | 23% | 5.7 s | ticket block ID --by ID |
| 14 | 234 | 51% | 59 s | ticket land ID --worktree P --allow-cross-ticket |
| 15 | 232 | 67% | 382 s | ticket land --drain --allow-cross-ticket ... |
| 16 | 189 | 90% | 2.9 s | ticket new --title ... --kind --priority --parent --tier --milestone --body-file --scope --scope (truncated) |
| 17 | 187 | 7% | 5.8 s | ticket milestone ID NAME |
| 18 | 182 | 1% | 3.0 s | ticket show ID --json |
| 19 | 174 | 76% | 952 s | ticket sweep-async ID --commit SHA |
| 20 | 155 | 91% | 3.8 s | ticket new --title ... --kind --priority --parent --tier --sprint --body-file --scope --scope |

There are 707 distinct shapes in 30,467 calls. `ticket new` appears as two 9-flag shapes (#16, #20)
that fail 90-91% of the time: the long, fully-specified `new` is the one that gets refused
(lock contention, root-write guard, empty/overlapping scope), then is retried (section 2.3).
Shapes 7, 9, 10, 14, 15 show that `land` has five caller-visible modes, all with a
50-67% refusal rate.

### 1.5 Agent-visible call profile (transcripts B)

| Verb | n | failed (is_error or Exit != 0) | --help in call | --json in call |
|---|---|---|---|---|
| check | 6,391 | 22% | 4.6% | 27.3% |
| ticket land | 3,723 | 12% | 4.4% | 0% |
| ticket show | 3,462 | 2% | 0.1% | 2.7% |
| ticket evidence | 3,430 | 2% | 11.9% | 0.1% |
| ticket scope | 2,701 | 6% | 5.4% | 0.1% |
| ticket new | 2,440 | 28% | 4.2% | 1.3% |
| ticket done-report | 2,383 | 22% | 18.7% | 0.3% |
| ticket work | 1,899 | 26% | 2.6% | 0.3% |
| ticket body | 1,314 | 5% | 17.8% | 0.1% |
| ticket start | 1,062 | 2% | 3.8% | 0.1% |
| ticket close | 1,022 | 5% | 13.5% | 0.2% |
| ticket sweep | 709 | 1% | 0.4% | 0% |
| test | 675 | 29% | 6.5% | 1.6% |
| natives | 630 | 2% | 1.6% | 0% |
| format / fmt | 405 / 325 | 1% / 2% | 5.2% / 4.9% | 1.0% / 0.3% |
| ticket list | 290 | 5% | 4.5% | 17.2% |
| ticket accept | 156 | 3% | 33.3% | 1.9% |
| ack | 184 | 2% | 25.0% | 0% |
| ticket promote | 126 | 5% | n/a | 0% |
| ticket brief | 123 | 2% | 0% | 0% (brief has its own cluster flag) |

Overall: 4,353 of 36,600 resolved calls failed (11.9%); 2,986 calls (8.2%) contained --help,
i.e. agents spend about 1 in 12 frob calls reading usage. The verbs with the most help-seeking
(done-report 18.7%, body 17.8%, accept 33.3%, ack 25%, close 13.5%, evidence 11.9%) are the
ones with the richest flag grammar: the grammar is not learnable from the first attempt.
Invocation form (first extraction pass, counted on full command strings): about 82% `uv run frob`,
8% `.venv/bin/frob` absolute path, remainder bare `frob`; `uv run --no-sync` appears ~1,500 times
(agents added it to dodge uv sync stalls).

## 2. Sequences and retry loops

### 2.1 Bigrams, telemetry A (consecutive cli records <= 5 min apart; n=30,467)

Dominated by polling and by parallel agents interleaving. Notable transitions
(percentage = share of the first verb's outgoing transitions).

| Bigram | n | share |
|---|---|---|
| land --status -> land --status | 12,591 | 83% |
| verify status -> verify status | 1,329 | 47% |
| ticket new -> ticket new | 561 | 34% |
| ticket sprint -> ticket sprint | 554 | 49% |
| ticket show -> ticket show | 495 | 38% |
| ticket new -> land --status | 369 | 22% |
| ticket promote -> land --status | 286 | 30% |
| verify status -> land --queue | 275 | 10% |
| verify status -> land (plain) | 252 | 9% |
| ticket work -> ticket work | 245 | 32% |
| land (plain) -> verify status | 241 | 32% |
| land --drain -> land --status | 199 | 72% |
| ticket promote -> ticket promote | 196 | 20% |
| ticket block -> land --status | 162 | 51% |
| check -> verify drain-async | 158 | 37% |
| land --dry-run -> land (plain) | 152 | 23% |
| ticket points -> ticket points | 156 | 33% |

### 2.2 Per-ticket bigrams (same ticket id, <= 30 min, land --status removed)

Keyed on the ticket id in args so parallel agents do not interleave. (For `new`, the id is the
--parent, so these are siblings filed under one epic.)

| Bigram | n | share of first |
|---|---|---|
| new -> new (siblings under one parent) | 1,342 | 93% |
| promote -> promote | 507 | 88% |
| block -> block | 315 | 71% |
| land --dry-run -> land --dry-run | 308 | 51% |
| work -> work | 306 | 52% |
| show -> show | 285 | 34% |
| scope -> scope | 263 | 54% |
| body -> body | 254 | 65% |
| land --dry-run -> land | 238 | 40% |
| set-parent -> set-parent | 235 | 70% |
| points -> points | 210 | 50% |
| set -> set | 143 | 100% |
| show -> work | 129 | 16% |
| points -> work | 113 | 27% |
| work -> land --dry-run | 98 | 17% |
| sprint -> milestone | 93 | 36% |
| evidence -> evidence | 76 | 68% |
| land -> sweep-async | 42 | 14% |

Observed lifecycle: new (draft) -> [scope, points, sprint, milestone, set-parent, body edits, each a
separate call] -> promote -> work/start -> evidence -> done-report -> land --dry-run -> land ->
land --status polling. The canonical new -> promote -> start chain exists (promote is followed by
land --status 30% of the time because agents file-and-land tickets in one pass), but the dominant
pattern is a verb repeated many times on the same ticket (same-verb repeats 50-100% for
promote, block, set, set-parent, body, scope, points).

### 2.3 Sequences, transcripts B (per session, time-ordered; subagent streams merged)

| Bigram | n | share of first |
|---|---|---|
| check -> check | 2,819 | 44% |
| ticket evidence -> ticket evidence | 1,394 | 41% |
| ticket land -> ticket land | 1,267 | 34% |
| ticket new -> ticket new | 995 | 41% |
| ticket show -> ticket show | 789 | 23% |
| ticket done-report -> done-report | 740 | 31% |
| ticket scope -> ticket scope | 668 | 25% |
| ticket work -> ticket work | 530 | 28% |
| evidence -> done-report | 455 | 13% |
| scope -> check | 442 | 16% |
| show -> work | 400 | 12% |
| done-report -> land | 369 | 15% |
| ticket sweep -> check | 356 | 50% |

`sweep -> check` at 50% is the pre-work-sweep handoff into a verification run. The close-out spine
(evidence -> done-report -> land) is a 3-call chain agents repeat per ticket; each link has a 22-41%
chance of being re-issued before the next.

### 2.4 Retry loops (quantified)

Definition: a call exits nonzero and the identical args_head (A) or identical command (B) recurs
within 120 s (A) or immediately after (B).

| Metric | Telemetry A | Transcripts B |
|---|---|---|
| failed calls (raw nonzero) | 7,884 | 4,353 |
| followed by identical retry | 4,404 (55.9%) | 2,055 of 4,351 with a successor (47.2%) |
| same, excluding verify status polls | 2,227 of 5,363 (41.5%) | n/a |
| failure followed by a different verb | 3,921 (75.6% of 5,186 non-status failures) | 1,468 (33.7%) |
| failure followed by same verb, new args | 531 (10.2%) | 785 (18.0%) |
| failure followed by --help of same verb | n/a | 43 (1.0%) |

Per verb, share of failures that were immediately retried identically:

| Verb | A: fails | A: retried | B: fails | B: retried |
|---|---|---|---|---|
| ticket new | 976 | 80% | 675 | 64% |
| ticket promote | 591 | 65% | - | - |
| ticket work | 570 | 47% | 488 | 76% |
| ticket body | 156 | 67% | 69 | 4% |
| ticket sprint | 162 | 63% | - | - |
| ticket set-parent | 110 | 65% | - | - |
| ticket points | 83 | 71% | - | - |
| ticket drop | 51 | 90% | - | - |
| check | 436 | 15% | 1,401 | 42% |
| ticket done-report | 0 | - | 532 | 60% |
| ticket land (plain/dry-run/queue/drain) | 1,207 | 2-15% | 429 | 37% |
| ticket evidence | 22 | - | 65 | 26% |
| ticket scope | 137 | 14% | 159 | 24% |

Chain-length distribution of identical consecutive failures (A, <=120 s gaps): 318 chains of 2, 123
of 3, 48 of 4, 35 of 5, then a long tail with spikes at 9-10 (72 chains: a fixed 10-attempt retry
budget in a script) and a handful of 30-639 runs. The two longest (639, 633) and most >50 are
`verify status` poll loops; the longest non-status loop is `ticket set-parent T-draft-... T-N`
(45 consecutive failures) and `land --status T-5303` (90).

Promote loops: 390 drafts needed 958 promote calls; 334 drafts promoted on the first try, but 28
drafts needed >= 10 calls (max 70), and 26 drafts show no successful promote in the window.
Mean attempts to first success 1.33; median 1. The tail is lock contention, not logic errors.
`ticket new` loops: 709 distinct titles took 1,674 calls; 170 titles needed >1 attempt (max 45);
the median successful new takes 23.3 s versus 4.3 s for a refused one, so refusals are cheap and
agents hammer them.

### 2.5 `land` polling (telemetry A)

| Metric | Value |
|---|---|
| `land --status` calls | 15,224 (50% of ALL cli records, 87.5% of land calls) |
| distinct tickets polled | 161 (159 also had a real land call; 427 tickets had a real land) |
| polls per ticket | median 2, p90 9, max 14,346 (T-5325); next 125, 108, 99 |
| inter-poll interval | median 6.8 s, p10 6.1 s, p90 8.1 s (a sleep-6 loop) |
| land --drain followed by land --status | 72% of drains |
| polls exiting nonzero | 137 (0.9%) |

One runaway loop (T-5325) accounts for 94% of all polls (14,346/15,224). Without it, polling is
878 calls, still the largest single behavior beyond ticket new. In transcripts the same activity
shows as `land --status` 247 calls and `land --finish` 297 calls (agents wrap the poll in shell loops
or use the blocking --finish form), and 258 "waiting up to Ns ... land.lock is held" warnings.
Land has no push notification or blocking-with-timeout contract that the agents trust; they
build their own.

## 3. Failure analysis

Telemetry has no error text; reasons below are from transcripts (tool_result lines). Counts are
records (a call can match several). Help-dump text ("usage:") is included only as one row.
Lines that were help-body text (e.g. "--steal override a refusal ...") were dropped.

### 3.1 Which verbs fail (raw exit 1, A) ranked by absolute failures

| Verb | fails | rate |
|---|---|---|
| verify status | 2,521 | 88.5% (status code) |
| ticket new | 976 | 58.3% |
| ticket promote | 591 | 61.7% |
| ticket work | 570 | 72.7% |
| check | 436 | 98.4% (status code) |
| land plain / dry-run / queue / drain | 398 / 365 / 257 / 187 | 50 / 54 / 62 / 67% |
| verify drain-async | 223 | 66.6% |
| ticket sprint | 162 | 14.2% |
| ticket body | 156 | 29.0% |
| ticket scope | 137 | 27.9% |
| sweep-async | 132 | 75.9% |
| set-parent | 110 | 59.8% |
| land --status | 137 | 0.9% |

### 3.2 Top failure/refusal reasons (transcripts B, 30 most common distinct lines)

| # | n | Line (normalized) | Mostly raised by |
|---|---|---|---|
| 1 | 854 | ERROR: ticket done-report: T-N Done report recorded ONLY on this worktree's own branch -- NOT yet visible on main; `frob ticket land` will carry it across (ERROR prefix on an informational notice) | done-report |
| 2 | 554 | usage: frob ticket evidence [-h] ... (argparse dump) | evidence |
| 3 | 482 | WARNING: land: wip add's :!.frob pathspec hit the ignored-path refusal -- falling back | land |
| 4 | 444 | WARNING: tickets: refused -- a land is in progress for T-N (land.lock held by {pid,...}) | scope 153, work 98 |
| 5 | 342 | usage: frob ticket done-report [-h] [--why TEXT] ... | done-report |
| 6 | 319 | ERROR: ticket start failed: T-N is already in-progress -- run `frob ticket sweep T-N` instead | work 285, start 33 |
| 7 | 258 | ERROR: scope change failed: ScopeLeaseConflict: requested --add glob overlaps a path leased by another in-progress ticket | scope |
| 8 | 258 | WARNING: land: land.lock is held by {...} -- waiting up to Ns | land |
| 9 | 242 | usage: frob ticket body [-h] | body |
| 10 | 212 | ERROR: body change failed: BodyTextAmbiguousSection: text contains a structural heading (## Done report / ## Failure log / ## Drop reason) | body |
| 11 | 188 | ERROR: ticket land: T-N quarantine is raised -- deferred landing OFF, forcing synchronous verification | land |
| 12 | 184 | frob: refusing WRITE to the shared root -- writes to the primary checkout are default-DENIED | land 71, new 23 |
| 13 | 173 | WARNING: tickets: refused -- a `frob ticket land` process is running even though land.lock is not held | scope 62, work 30 |
| 14 | 171 | WARNING: tickets: in-flight land did not finish within its wait budget, refusing rather than waiting | scope 57, work 36 |
| 15 | 158 | ERROR: frob ticket land requires --worktree <path> | land |
| 16 | 145 | ERROR: ticket start failed: T-N has an EMPTY scope -- add scope or declare no scope | work 108, start 36 |
| 17 | 137 | usage: frob ticket scope [-h] [--add GLOB] [--remove GLOB] | scope |
| 18 | 136 | ERROR: ticket land failed: NotCloseable: ticket is missing evidence or a Done report | land |
| 19 | 134 | ERROR: build_graph: cache lock never released: database is locked | new 89, land 20 |
| 20 | 127 | ERROR: ticket evidence failed: UnknownEvidence: id does not resolve to a collected test | evidence |
| 21 | 124 | usage: frob ticket new [-h] --title ... --kind ... | new |
| 22 | 123 | ERROR: tickets: T-N ledger change left worktree DIRTY -- the commit step failed (GitFailed) | work 63, evidence 25 |
| 23 | 120 | ERROR: land: T-N cannot land -- missing evidence or a Done report | land |
| 24 | 118 | ERROR: ticket T-N: scope's ledger edit is WORKTREE-LOCAL and NOT visible on main -- a land is in progress | scope |
| 25 | 117 | refusing on an empty scope (T-N) | scope |
| 26 | 110 | ERROR: frob ticket scope requires --reason TEXT or --reason-file PATH | scope |
| 27 | 109 | WARNING: tickets: refused -- a land is in progress (land.lock held ...) | scope 45, work 20 |
| 28 | 107 | WARNING: ticket new: T-N filed with an EMPTY scope -- `start` will refuse it | new |
| 29 | 106 | ERROR: frob ticket body requires --reason TEXT or --reason-file PATH | body |
| 30 | 106 | ERROR: ticket start failed: T-N's declared scope collides with in-progress T-N's lease on '...' | work 60, start 45 |

Next in line: promote draft-id rejections (100, "promote T-draft -> T-N: exists ONLY on this
worktree's branch"), "no ticket T-draft" (63), EvidenceConfirmatoryOnly (88 + 88), DirtyMain (71),
`ticket work: LandInProgress` (71), `ticket new: LandInProgress` (87), PassengerTickets (67),
StaleClaimsInDoneReport (60), `check refusing a full/unchunked run under FROB_AGENT` (57),
AcceptanceIndexOutOfRange (91), sqlite "database is locked" variants (78 + 72).

### 3.3 Failure families (grouped; records mentioning each)

| Family | records | Share of 36,610 calls |
|---|---|---|
| Argparse usage dumps (wrong/missing args) | 2,642 | 7.2% |
| Land in progress / land.lock / tickets.lock contention | 1,422 | 3.9% |
| "Worktree-local, not visible on main" notices | 1,274 | 3.5% |
| Scope lease conflict / lease collision | 508 | 1.4% |
| Empty-scope refusal | 406 | 1.1% |
| Already in-progress (start/work idempotency) | 327 | 0.9% |
| Missing --reason | 271 | 0.7% |
| Evidence id / acceptance index errors | 224 | 0.6% |
| BodyTextAmbiguousSection | 212 | 0.6% |
| sqlite cache locked (graph cache under concurrency) | 209 | 0.6% |
| NotCloseable / missing evidence | 201 | 0.5% |
| EvidenceConfirmatoryOnly | 198 | 0.5% |
| refusing write to shared root | 184 | 0.5% |
| draft id errors (no ticket T-draft, promote T-draft) | 164 | 0.4% |
| land requires --worktree | 158 | 0.4% |
| DirtyMain | 147 | 0.4% |
| PassengerTickets | 84 | 0.2% |
| StaleClaimsInDoneReport | 77 | 0.2% |
| check full-run refused under FROB_AGENT | 57 | 0.2% |

About 10% of all agent calls hit an avoidable concurrency refusal (lock/lease/worktree-visibility
families), and 7% are argument-shape errors. Only a minority of refusals encode real policy
(evidence, scope, quality).

## 4. Hand-editing tickets (verb inadequacy), transcripts B

Writes aimed at tickets/T-*/ files outside the CLI (444 candidate events across 10 sessions; categories
non-exclusive, reads such as `git show` and python read-only parses excluded where detectable):

| Pattern | Count | What it indicates |
|---|---|---|
| Edit tool on tickets/T-*/ticket.md | 48 (46 in worktrees, 2 on root) | direct frontmatter or body edits |
| Edit/Write tool on tickets/T-*/done-report.md | 28 (Write 16, Edit 12) | agents write the Done report file directly instead of via `done-report --why-file` |
| sed -i on tickets/T-*/ticket.md | 27 | one-line surgical changes |
| `cat >> tickets/T-*/ticket.md << EOF` | ~46 (11 are frob:waive appends) | appending directives/notes; `ticket body --append` exists but requires --reason and refuses structural headings |
| python write_text / re.sub over ticket.md | ~76 (incl. read-only extracts) | merge-conflict resolution, body extraction |
| Merge-conflict marker repair (`<<<<<<<` handling) | 58 | the ledger merge driver did not cover the case |
| Draft id rewrite after promote (`sed id: T-draft-xxxx -> T-NNNN`, git mv dir) | 59 | promote left a worktree copy under the draft id |

Interpretation: roughly 150-200 distinct hand-edits in 34 days against 36,610 verb calls (0.5%).
Small, but concentrated in three gaps: (1) draft-id reconciliation inside a worktree, (2) merge
conflicts in ticket.md, (3) Done-report authoring. Each is a verb that should exist or a state
machine step that should not need manual repair. Also: 21 `renumber` calls (transcripts B) and 16 `reconcile`
calls (telemetry A tool records) are admin-grade repairs agents ran regardless.

## 5. Agent vs human

Direct signals do not exist:

- `kind=cli` has no FROB_AGENT, session, or worktree field; home_config_hash has 4,089 distinct values
  over 30,467 records; external_path_hash is "none" on 94%.
- Transcripts contain zero human `!frob` bash-input lines; the human works through agents.
- `ticket new --origin` is the only declared signal: of 504 telemetry `new` calls whose truncated
  args still show --origin, 436 (86.5%) say `agent` and 68 (13.5%) say `human`. Floor only
  (args_head is cut at 512 chars, and 1,170 of 1,674 `new` calls lost the flag).
- Telemetry `ticket` events: created 763 (761 as T-draft-*, 2 numeric), started 24, requeued 13, done 7.
  100% of tickets are born as drafts; the numeric id is assigned later by promote.

Proxy split. A cli record is "agent-attended" if any `tool` telemetry record from a dispatch lies
within 30 s of it; otherwise "unattended" (hooks, CI, background loops, human, or agents in
untracked worktrees).

| Metric | agent-attended | unattended |
|---|---|---|
| records | 21,300 (69.9%) | 9,167 (30.1%) |
| raw exit-1 | 25.0% | 28.0% |
| --json used | 3.0% | 3.3% |
| land --status | 10,001 | 5,223 |
| verify status | 1,468 | 1,381 |
| ticket new | 1,252 | 422 |
| verify drain-async | (low) | 140 |
| check | 281 | 162 |
| land --drain | (low) | 114 |

The two distributions are nearly the same, which says the proxy is weak, not that humans behave like
agents. The defensible reading: the vast majority of v1 traffic, including all of the heavy
sequences, is agent-driven; the human's footprint is nearly all indirect (hooks, `verify`, spot
`check`). The only human-leaning items are `ticket list` (145; 0% fail), `ticket board` (3),
`ticket epic` (10), `ticket brief` (21), `explore` and `vet` (21 combined). The v2 design
should add an explicit actor field (env + flag) to telemetry rather than infer it.

## 6. What agents need from a ticket CLI that Jira users do not

Grounded in the numbers above.

### 6.1 Machine-readable output as the default, not an option

- --json appears on 933/30,467 (3.1%) of cli calls and on 5.5% (1,997) of agent calls; zero of 17,402
  land calls and zero on promote, work, scope, body, sprint, points despite those being the verbs agents
  parse results from.
- Where --json is offered, it is used when the output is large and structured: check 95% (A) / 27% (B),
  list 24% / 17%, show 14% / 2.7%. Everything else is scraped from text, then `grep`/`tail`/`sed -n`
  (tool telemetry: grep -n 2,354, tail 1,717, sed -n 1,331, wc -l 487 shell shapes).
- The most common single transcript line is an "ERROR:" prefix on a successful informational
  notice (854 done-report). Prefix-matching on the prose is already unreliable.
- Need: one structured envelope (status, code, retryable, next-step, ticket/state/lease ids) on every
  verb, nonzero exit only for failure (never for "findings exist", "not ready" or "queued"),
  with check/verify/land --queue/--status exit codes separated from tool errors.

### 6.2 Idempotency and retry semantics

- 56% of raw failures (A) and 47% (B) are retried with identical args; 42-76% for new, work,
  done-report, check. Median refusal costs 4 s but agents reissue it 1-45 times.
- Already-in-progress (327) and "no ticket T-draft" (63) show the verbs are not idempotent: `work`
  on an in-progress ticket errors instead of returning the existing lease (285 of 319 raised via `work`).
- Need: every mutating verb safe to repeat (client-supplied idempotency key or natural key, such as
  title hash or ticket id + target state), returning the prior result with `already: true`; a built-in
  bounded `--retry-for 30s` or explicit `retry_after_ms` instead of agents inventing 10-attempt scripts
  (spikes at exactly 9-10 identical attempts in chain data).

### 6.3 Dry-run, preview and plan-then-apply

- `--dry-run` is used 686 times in A (680 of 2,178 non-poll land calls = 31% of land
  attempts in A were dry-runs) and 684 times in B (16.4% of agent land calls).
- Dry-run is itself slow (median 158 s) and fails 54% of the time; dry-run -> real land follows
  23-40% of the time (per-ticket 238 transitions), i.e. the preview cost is paid and its outcome is
  frequently invalid by the time the real call runs.
- Need: preview that is cheap (seconds), transactional (token/plan id that `apply` can consume) and
  covers creates (`new --dry-run` was used only 5 times), scope changes and promote renames.

### 6.4 Draft-id friction

- All tickets are born with a random draft id (761 of 763 creates); numeric id arrives on promote.
- promote: 958 calls for 390 drafts, 62% exit 1, 28 drafts needing >= 10 calls (max 70), 26 never
  promoted in the window. Agents then hand-rewrite ids (59 sed/mv sequences), and hit "no ticket
  T-draft" (63) and "exists ONLY on this worktree's branch" (100). 21 renumber calls.
- 2,764 telemetry calls reference a draft id, 958 of them promote itself.
- Need: ids allocated at creation (monotonic, collision-safe: content-addressed or per-actor range
  with a registry), so there is no rename step; if offline-local drafts are required, a stable
  alias that survives promotion in every worktree and a single atomic `new --and-start` path.

### 6.5 Scope lease friction

- Starting a ticket requires non-empty scope. Resulting refusals: empty scope 406, scope lease
  conflicts 508 (258 ScopeLeaseConflict + 73 cannot-lease-add-glob + 106 start collisions + ...),
  `ticket scope` 28% failing in A, 'requires --reason' 271, `scope` is the 5th most used agent verb
  (2,701; 7.4%) and the second most helped-with after evidence and body.
- `--steal` used 10 times (B) / 3 times (A, all 3 failed); `scope-ack` 51 times (B) / 1 (A); `contention`
  29 / 12 (agents read the lease map before acting on about 0.08% of calls); `--wait` 513 (A) /
  66 (B). The collision tools exist but are barely used, and when used the call mostly fails;
  agents resolve collisions by waiting or re-planning scope.
- Need: lease as a first-class, queryable resource: `lease acquire --paths ... --ttl` returning
  holder/expiry, queued acquisition with notification (not poll), glob overlap computed once and
  shown in the refusal with the holder's ticket and age, automatic expiry on dead worktrees, and
  scope declared at `new` time and amended with a diff (add/remove in one call) rather than 85%
  `--add` one glob at a time ("command once per glob. Refused" appears 67 times).

### 6.6 Land / long-operation handling

- 17,402 land calls; 87.5% are status polls (15,224), 94% of those one runaway loop; real land
  attempts fail 50% (plain), 54% (dry-run), 62% (queue), 67% (drain); median wall time 84 s plain,
  158 s dry-run, 356 s drain, 952 s for the detached sweep-async.
- land has five modes (plain, --dry-run, --queue, --drain, --status) plus --finish, --onto, --push;
  --worktree is mandatory in practice (158 refusals for omitting; present on 82% of agent lands).
- Contention while a land runs blocks unrelated verbs: 1,422 records mention land-in-progress
  / lock held, hitting scope (153+), work (98+), new (87), body, promote.
- Need: land as a job (`land submit` returns job id; `land wait <id> --timeout` blocks server-side
  with a defined exit contract; `land status <id> --json` is O(1) and rate-limit-friendly), no
  global ledger lock held for minutes, and non-landing writes allowed concurrently (queued).

### 6.7 Ceremony and metadata batching

- 3,149 calls (10% of A) set one field at a time (sprint 1,144, points 478, milestone 187, set-parent
  184, body 538, scope 491, set 92, tier 23, priority 12), each a 5-13 s commit. `new` already
  takes 10+ flags and is the most refused verb when it carries them.
- Need: one `update` with a patch (many fields, one commit, one lock), or batch mode taking
  JSON lines on stdin; commit-free reads must be sub-100 ms (v1 `show` median 2.4 s, `list` 0.7 s).

### 6.8 Self-describing surface

- 8.2% of agent calls include --help; done-report 18.7%, body 17.8%, accept 33%, ack 25%. 2,642
  argparse usage dumps in results. 57 ticket verbs (and 52 top-level) exist; 15 never reached telemetry.
- Need: a small closed verb set, a machine-readable schema command (`--schema` printing the
  JSON schema for flags/inputs/outputs), error messages with the exact corrected command, and
  stable abbreviation-free flags (argparse prefixes like --fil, --reas appear in telemetry).

### 6.9 Top 10 verbs by volume (design priority)

| Rank | Agent calls (B) | Process calls excl. polls (A) |
|---|---|---|
| 1 | check | verify status |
| 2 | ticket land | ticket new |
| 3 | ticket show | ticket show |
| 4 | ticket evidence | ticket sprint (assign) |
| 5 | ticket scope | ticket promote |
| 6 | ticket new | ticket land |
| 7 | ticket done-report | ticket work |
| 8 | ticket work | ticket land --dry-run |
| 9 | ticket body | ticket body |
| 10 | ticket start | ticket scope |

The union of these is about 14 verbs: show, new, work/start, scope, body, evidence, done-report,
land, check, verify status, sprint/points/milestone (metadata), promote. They are about 79% of agent calls
(B) and about 74% of non-poll process calls (A, top 10 shapes); v2's hot path should cover just these, with metadata
folded into new/update.

### 6.10 Verbs never used (or effectively never)

Parser verbs absent from BOTH telemetry A (cli) and transcripts B:

| Group | Verbs |
|---|---|
| ticket subverbs, zero uses in both | component, deprecated, review, runs-last, runs-last-parallel-safe, tokens |
| top-level verbs, zero uses in both | bind, debt, deploy, dup, map, mutate, parse, stats, sync-skills |

Seen in only one source:

| Verb | Telemetry A | Transcripts B | Note |
|---|---|---|---|
| ticket board | 3 | 0 | |
| ticket debt | 1 (exit 1) | 0 | removed alias; telemetry hit |
| ticket sweep-async | 174 | 0 | internal callback spawned by land |
| ticket merge-driver | 94 | 4 | internal git hook |
| ticket anchor, migrate, plan, label, waive-audit, flow, attach, wave, admin | each 0-14 | 1-5 | near-dead (B <= 5 uses in 34 days) |
| ticket renumber, restore, reverify | 0 | 21 / few / few | admin-grade, used only via reconcile/renumber repair |
| top-level xref | 16 | 0 | |
| top-level test, format, fmt, coverage, cycle, sys, worktree, docs, registry, release, graph, pool | 0 | 7 - 675 | not instrumented in cli telemetry, heavily used by agents |

So of 57 ticket verbs, 6 were never used anywhere and about 15 were used <= 5 times; 20 verbs
cover over 99% of calls. Hidden or removed in v1 already (docs/commands/ticket.md): migrate, debt,
deprecated (removed, exit 2), merge-driver and sweep-async (hidden callbacks), renumber/restore/
reconcile (folded under admin).

## 7. Summary of design implications (one line each)

1. Exit codes must separate "tool failed" from "domain state": check and verify status exit 1
   on 88-98% of calls today.
2. Make every verb idempotent and cheaply retryable; half of all failures are blind repeats.
3. Kill draft ids and the promote step; they cost 958 calls, 62% failure and 59 hand repairs.
4. Replace polling of `land --status` with a blocking/subscribe call; 50% of all v1 process
   invocations were that poll.
5. Make leases first-class and queued; scope + start refusals are about 1,100 of 36,610 agent calls.
6. One update call for metadata instead of nine one-field verbs at 5-13 s each.
7. Default structured output with a schema; use human text only on TTY.
8. Remove the global ledger lock from reads and unrelated writes; contention touches about 4% of
   agent calls and spills into five verbs.
9. Add actor attribution (agent id, session, worktree, human flag) to every telemetry record.
10. Instrument every verb in cli telemetry; v1 missed test/format/fmt and undercounted worktree work.

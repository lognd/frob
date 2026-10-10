# Formal model of the one-way ticket mirror

Status: current
Owner: frob
Decisions: none
Audience: contributor

Provenance: model-checked 2026-10-03 with TLC 2.19 (tla2tools.jar of the
v1.7.4 release, sha256 936a2620...0e88). Subject: docs/design/mirror.md
section 3.1 (reconcile, never block), security.md 2.11 (I12) and the
event model of tickets.md 2a. Nothing in mirror.md was edited; the
protocol changes the model calls for are in section 7 below.

Summary. The protocol as written violates four of the stated guarantees:
no loss of tracker edits, convergence, never two issues for one ticket,
and the map file never pointing a ticket at another ticket's issue.
Nine small changes (section 7) repair it. With them, every safety
property holds in every configuration checked, and every liveness
property holds under weak fairness of the mirror, finitely many
disturbances and a per-run budget of at least one ticket's reads plus
one write. One guarantee is unattainable on GitHub's API: a create whose
request times out can take effect later, so two issues for one ticket
can exist. The repaired protocol bounds that and repairs it (closes the
duplicate and keeps reading its history). Convergence (eventually always
equal) fails against an adversary that never stops editing; what still
holds then is stated in section 6.3.

## 1. Files

| File | What |
|---|---|
| `Mirror.tla` | The main model: ledger, map file, tracker with append-only history, adversarial humans, a non-atomic mirror with crashes, failures, rate-limit refusals, lost, late and duplicated deliveries, stale map reads. Ten boolean protocol switches select the protocol as written (FALSE) or repaired (TRUE). |
| `MirrorRace.tla` | An abstraction for an adversary with no bound on edits (history reduced to per-issue flags so the state space stays finite): convergence, no-loss and starvation under a per-run budget. |
| `MC_fixed_*.cfg` | Repaired protocol, safety, one adversary mix each. |
| `MC_live_*.cfg` | Repaired protocol, safety plus liveness under fairness. |
| `MC_aswritten.cfg` | Every switch FALSE: the protocol as the text reads. |
| `MC_abl_*.cfg` | Ablations: the repaired protocol with exactly one switch turned off, against the adversary that breaks it. |
| `MC_Race_*.cfg` | `MirrorRace.tla` with bounded or unbounded edits, round robin or fixed order, several budgets. |

## 2. What is modeled

Correspondence with mirror.md 3.1:

| mirror.md | Model |
|---|---|
| ledger, the source of truth | `led[t]`: the projection of the repository-owned field `r` per ticket; changed only by `LCommit` (a maintainer's ticket verb) and `Accept` (accepting a proposal) |
| proposal events on the ticket | `prop[t]` (one collapsed proposal per ticket for the one human user: latest value plus the set `hs` of tracker event ids folded in) and `rec[t]` (tracker event ids already recorded) |
| map file `mirror.toml` | `mapf`: ticket to issue number, history cursor, last comment day, round-robin pointer; `mapPrev` is the previous version, which a stale read returns |
| tracker issue | `iss[i]`: existence, author (bot or human), creation-time marker `mk0` (immutable), current body marker `mk` (editable), repository-owned `r`, tracker-owned `tf`, open or closed |
| change history (timeline, body edit history) | `hist`: append-only sequence; the position is the tracker event id; every change by anyone appends one entry |
| find-by-ULID | `Found(t)`: bot-authored issues whose marker names `t`, through a search index `idx` that lags (or a consistent lookup) |
| one comment per issue per day | `com[i][d]`, `day`, `Tick` |
| one serialized writer | one mirror process `m` with local state that a crash loses |
| per-run rate budget | `m.b`: every tracker call costs 1; at 0 the next call is refused and the run stops cleanly |

The mirror run, per ticket, in this order; each arrow is a separate
step where anything else can interleave:

    start (snapshot ledger, read map, maybe stale)
      -> find?   (only if no map entry, or every run when ScanDups)
      -> create? (only if find found nothing)
      -> rstate  (read the issue's current state)
      -> rhist   (read history since the cursor)
      -> prop?   (ledger commit of proposal events for new human edits of r)
      -> write?  (revert r and the marker to the ledger snapshot, if they differ)
      -> close*  (close duplicate issues, ScanDups only)
      -> comment? (if proposals were recorded this run)
      -> fin     (advance the cursor in the local copy of the map)
    -> next ticket ... -> commit (write the map file) -> idle

The environment, all without fairness:

- `HEditR`, `HEditT`: any human edits `r` or `tf` of any issue at any time,
  including between the mirror's read and its write.
- `HSpoof`: a human pastes another ticket's marker into a bot issue's body;
  `HCreate`: a human creates an issue carrying a copied marker.
- `LCommit`, `Accept`, `Decline`: maintainers; each is a push to the ledger
  that triggers a run.
- `MCrash` at any step; `MFail`: a call fails with no effect; `MRefuse`:
  the budget is spent.
- Network (`NetKinds`): `lost` (create took effect, response lost),
  `delay` (create timed out with no effect yet, takes effect at any later
  time or never), `dupw` / `dupc` (a write or comment delivered twice, the
  copy arriving later).
- Stale map: a run starts from `mapPrev` instead of `mapf` (CI checks out
  the triggering commit, not the tip).
- `IndexI`: the search index catches up (weakly fair).

Bounds per configuration: 1 or 2 tickets, 1 to 3 issues, values {0,1},
1 to 3 human edits, at most 1 of each fault kind, 0 or 1 day change. NT=1
configurations check the race and no-loss properties, where a second
ticket only multiplies interleavings; NT=2 configurations check map,
spoofing, duplicate and starvation properties, which need two tickets.

## 3. Assumptions about the tracker and the platform

The results depend on these. Where an assumption fails, the property
it supports can fail.

- A1 History is append-only and complete for each repository-owned
  field: every change appends an entry with its author, field and new
  value; entries are never edited or deleted.
- A2 History reads are consistent prefixes: a read returns every entry
  up to some position, and no entry later appears at an earlier position.
  The cursor is a position (event id), not a wall-clock time. If the
  tracker can surface an event late with an earlier position, the cursor
  must lag by a window and rely on dedupe by event id (change 9), which
  makes re-reading harmless.
- A3 Issue author and the creation revision of the body are immutable and
  readable (GitHub: issue `user`, and the first revision of
  `userContentEdits`). Only the bot can author bot issues.
- A4 For changes 5 and 6, a lookup of a ticket's issues that is
  read-your-writes (for example: list the bot's issues filtered by a
  per-ticket label, instead of the search API). UNVERIFIED for GitHub
  list endpoints, to be checked at implementation; the search API is
  documented as eventually consistent.
- A5 A call that reports failure had no effect, except create, whose
  effect is unknown (it may exist now, appear later, or never). Writes are
  "set field to value" and so are idempotent; a late duplicate of a write
  is an old value arriving late.
- A6 One writer: at most one mirror run at a time (CI concurrency group).
  A second, concurrent mirror (an opt-in local push) is not modeled.
- A7 The mirror's own pushes to the ticket branch do not trigger runs (true
  for GitHub Actions pushes made with `GITHUB_TOKEN`); otherwise runs
  would loop until idempotent, which is harmless but wasteful.
- A8 Rate limits are per token: human edits do not spend the mirror's
  budget. If an adversary can exhaust the mirror's quota (a shared token,
  secondary limits per repository), liveness needs a bound on that
  adversary too.
- A9 Issues are never deleted and humans do not reopen closed duplicates
  (both are outside the model; a deleted issue is recreated per mirror.md,
  a reopened duplicate is re-closed by the next scan).

## 4. Protocol switches

Each switch is FALSE for the protocol as written and TRUE for the
repaired protocol. Section 7 gives the text of each change.

| Switch | FALSE (as written) | TRUE (repaired) |
|---|---|---|
| `Sched` | runs start only on pushes to the ticket branch | also on a schedule |
| `CursorAtRead` | history cursor = position after the last publish ("since its last publish") | cursor = position observed when reading |
| `EarlyCursor` | that position is taken at the history read | taken at the first read of the ticket (find or state read), and kept across a create |
| `MapCAS` | map file written blindly (path-level commit on the ref CAS) | compare-and-swap on the map file's content |
| `AuthCreation` | find-by-ULID trusts the marker in the current body (author is the bot, HMAC valid) | trusts only the marker of the bot-authored creation revision |
| `ConsistentFind` | find through a lagging search index | read-your-writes lookup |
| `ScanDups` | duplicates looked for only when the map has no entry | every run lists the ticket's issues, reads all their histories, closes extras |
| `CommentCheckTracker` | "one comment per day" decided from the map file | decided from the issue's comments |
| `RoundRobin` | every run starts at the first ticket | starts at the ticket after the last one completed |
| `Dedupe` | proposals recorded for every human edit read | proposals keyed by tracker event id; known ids are skipped |

## 5. Properties

All are in `Mirror.tla` (section "Properties") and `MirrorRace.tla`.
`Own(i)` is the ground truth: the ticket a bot-authored issue was created
for (`mk0`), 0 for human-authored issues. `HumanR(p)`: history entry `p`
is a human edit of the repository-owned field.

Safety (invariants unless marked as action properties):

- S1 `NoTrackerOwnedWrite`: `\A p : hist[p].u = BOT => hist[p].f # "tf"`,
  and the action form `NoTrackerOwnedWriteA`: every change of a
  tracker-owned field is a human `HEditT` step.
- S2 `CursorSound` (no loss, the inductive core):
  `\A t, p : p <= mapf.cur[t] /\ HumanR(p) /\ Own(hist[p].i) = t => p \in rec[t]`.
  Every human edit of a repository-owned field of a ticket's issue that
  lies at or before the committed cursor is recorded as a proposal. The
  liveness form is L2.
- S3 `NoDupIssue`: `\A t : Cardinality({i : Own(i) = t}) <= 1`.
- S4 proposals never modify the tracker:
  `ProposalsNoTrackerEffect` (action): a step that records proposals
  leaves issues, history, comments and the network unchanged;
  `WritesFromLedger`: every value the bot writes to `r` (directly or in
  flight) is a value the ledger held for that ticket;
  `SnapshotIsLedger` (action): a run's snapshot equals the ledger;
  `LedgerOnlyByVerbs` (action): the ledger changes only by `LCommit` or
  `Accept`. Together: tracker users reach the ledger only through a
  maintainer's accept (I12).
- S5 `MapOwn`: `\A t : mapf.m[t] # 0 => iss[mapf.m[t]].au = BOT /\ iss[mapf.m[t]].mk0 = t`
  (the map never points a ticket at another ticket's issue, nor at a
  human's issue).
- S6 `CommentBound`: `\A i, d : com[i][d] <= 1 + dupCom[i][d]` (one comment
  per issue per day, plus duplicated deliveries, which no client can
  prevent).
- S7 `RunBound`: tracker mutations per run `<= Budget` and `<= 3 * NT + MaxIssues`
  (one create, write and comment per ticket plus closes).
- S8 `NoReopen`: a pending proposal never contains an event id already
  accepted or declined.
- S9 `Idempotent`: a run that starts converged (`Clean`), from a fresh map,
  and is not disturbed, makes no tracker mutation and no ledger commit.
- Model sanity: `HistBound` (`Len(hist) <= HMax`), `NotStuck` (issue
  numbers not exhausted), `TypeOK`.

Liveness (`Spec` = `Init /\ [][Next]_vars /\ WF_vars(MirrorStep) /\ WF(IndexI)`;
no fairness for humans, maintainers or the network; all disturbances
bounded by the configuration):

- L1 `Converge`: `<>[](\A t : Synced(t))`, where `Synced(t)` is: the map has
  an issue for `t`, its `r` equals `led[t]` and its marker names `t`.
- L2 `NoLoss`: `\A t, p : [](Unrec(t, p) => <>~Unrec(t, p))`, where
  `Unrec(t, p)` is: `p` is a human edit of `r` on an issue of `t` and
  `p \notin rec[t]`. Repeated edits by the same user collapse into one
  proposal whose event set contains them all, so "or is superseded by a
  later edit of the same user and field" is covered: the superseded
  edit is recorded in the same collapsed proposal.
- L3 `NotStarved`: `\A t : []<>(m.pc = "fin" /\ m.ct = t)`: every ticket is
  completed by some run infinitely often.
- L4 `DupsClosed`: `<>[](\A t : at most one open issue i with Own(i) = t)`.

`MirrorRace.tla` restates L1 to L3 for unbounded edits plus
`InfOften == \A i : []<>(R[i] = L)` and the safety property
`WritesOnlyLedger`.

## 6. Results

### 6.1 Repaired protocol (all switches TRUE)

Command per row: see section 8. "distinct" is distinct states. All runs
on 4 workers, `-Xmx8g`; RSS is the peak resident size of the JVM.

| Config | Adversary | Checked | Result | States (generated / distinct) | Time | RSS |
|---|---|---|---|---|---|---|
| `MC_fixed_race` | NT=1, 3 edits of r, 1 of tf, 1 ledger commit, 1 crash | S1-S9 | holds | 6,514,916 / 2,908,842 | 25 s | 3.4 GB |
| `MC_fixed_faults` | NT=2, 1 edit, 1 commit, 1 crash, 1 failure, 1 lost create or duplicated write, 1 stale map | S1-S9 | holds | 26,463,452 / 12,757,837 | 2 min 53 s | 4.1 GB |
| `MC_fixed_spoof` | NT=2, 1 edit, 1 marker spoof or human-created marked issue, 1 lost create, 1 stale map | S1-S9 | holds | 1,649,234 / 1,109,825 | 12 s | 3.1 GB |
| `MC_fixed_comments` | NT=1, 3 edits, a day change, 1 crash, 1 duplicated comment | S1-S9 | holds | 1,930,758 / 767,592 | 9 s | 2.9 GB |
| `MC_fixed_delay` | NT=1, 2 edits, 1 crash, 1 late create | S1-S9 without S3 | holds | 593,001 / 315,451 | 4 s | 1.9 GB |
| `MC_fixed_delay_dup` | same | S3 | violated (inherent, see 6.2 row D0) | 145 / 101 | <1 s | |
| `MC_fixed_budget` | NT=2, budget 3, 2 edits, 1 commit | S1-S9 | holds | 106,204 / 54,627 | 2 s | 0.6 GB |
| `MC_live_race` | NT=1, 2 edits, 1 commit, 1 crash, 1 failure, 1 duplicated write | S1-S9, L1-L4 | holds | 1,979,243 / 814,434 | 5 min 41 s | 4.4 GB |
| `MC_live_lost` | NT=2, 1 edit, 1 crash, 1 lost create, 1 stale map | S1-S9, L1-L4 | holds | 148,698 / 90,101 | 54 s | 3.0 GB |
| `MC_live_delay` | NT=1, 1 edit, 1 crash, 1 late create | S1-S9 without S3, L1-L4 | holds | 25,276 / 14,743 | 7 s | 1.0 GB |
| `MC_live_budget` | NT=2, budget 4, 2 edits, 1 commit | S1-S9, L1-L4 | holds | 1,947,162 / 1,035,312 | 13 min 25 s | 5.6 GB |
| `MC_live_budget3` | NT=2, budget 3 | L1-L4 per property | L1, L2, L3 violated; L4 holds (see 6.2 row B3) | 106,204 / 54,627 (L4) | 3-6 s each | 1.5 GB |

Safety holds with a budget of 3 calls per run, lower than one ticket's
reads plus a write, against edits made faster than the budget allows:
a refused call ends the run cleanly, and nothing it did is unsafe.

### 6.2 Counterexamples: the protocol as written and each ablation

Each row is the repaired protocol with one switch off (or all off for
D1), the property TLC reports, and the shortest trace (BFS) in plain
words. Every one is a protocol flaw, not a model artifact; each is
fixed by the change in section 7 with the same number.

| Id | Config | Violated | Shortest counterexample | States to find |
|---|---|---|---|---|
| D1 | `MC_aswritten` (all off) | S5 MapOwn | Ticket 1 is published as issue 1. A human pastes ticket 2's marker into issue 1's body. Ticket 2's first sync runs find-by-ULID: issue 1 is bot-authored and its (copied) HMAC is valid, so it is adopted; the map points ticket 2 at ticket 1's issue, so ticket 2's projection is then written into ticket 1's issue (and, with both mapped, each run reverts the other's write). | 8,646 |
| F1 | `MC_abl_sched` | L1, L2, L3 | Ticket published; a human edits the title; no further push to the ticket branch ever happens, so no run starts: the edit is never reverted and never becomes a proposal. | 9 |
| F2 | `MC_abl_cursor` | S2 (and L2) | A run reads the issue (title = 0); a human edits the title to the ledger's new value; the write finds nothing to change or overwrites it; the cursor is set to "after the publish", past the human edit, which is never read again and never becomes a proposal. Contradicts "The race" paragraph of 3.1. | 4,720 |
| F3 | `MC_abl_early` | S2 | Create #1 for ticket 1 times out (no effect yet). Next run: find returns nothing; the late create lands as issue 1; a human edits issue 1; the mirror creates issue 2 and puts the cursor after its own create, past the human edit on issue 1. | 348 |
| F4 | `MC_abl_auth` | S3 NoDupIssue (and S5 in other traces) | Create for ticket 1 succeeds but the response is lost. A human changes issue 1's marker. Next run: find by current marker misses issue 1 and creates issue 2 for the same ticket. With the marker pointing at another ticket, D1 follows. | 491 |
| F5 | `MC_abl_find` | S3 NoDupIssue | Create succeeds; the mirror crashes before committing the map file. Next run: find-by-ULID through the search index, which has not indexed the issue yet, returns nothing; a second issue is created. | 273 |
| F6 | `MC_abl_scan` | S2 (and L4, L2 in `MC_abl_scan_live`; L1 holds there) | A create times out and lands late as a second issue after the retry created the first. The map points at the first; the second is never looked at again: it stays open forever with the old rendering, and a human edit on it is never read. | 2,500 |
| F7 | `MC_abl_comment` | S6 CommentBound | Proposal recorded, comment posted, crash before the map commit (which held "commented today"). Same day, a new edit: a new proposal, the map file says no comment today, a second comment. | 18,669 |
| F8 | `MC_abl_rr` | L3 NotStarved (also L1, L2) | Budget 4 per run. Every run starts with ticket 1 (3 reads) and is refused on ticket 2's second call; ticket 2 is never completed. | 38,503 |
| F9 | `MC_abl_dedupe` | S9 Idempotent, S8 NoReopen | Proposal recorded, crash before the map commit (cursor not advanced). Next run re-reads the same edit and records it again (not idempotent); if a maintainer accepted or declined it in between, it is reopened as pending (S8). | 31,177 |
| D0 | `MC_fixed_delay_dup` | S3 NoDupIssue | Create times out (no effect yet), crash. Next run: consistent find returns nothing (correctly), creates issue 1; then the first request lands as issue 2. No client protocol prevents this without an idempotency key on create. | 101 |
| B3 | `MC_live_budget3` | L1, L2, L3 | Budget 3 equals the reads of one ticket (find, state, history); the write is always the refused fourth call, so a ticket that needs a write never converges, its processing never completes, and the round-robin pointer never moves past it, so the other ticket's edits are never read. Found as a model sizing error first (the config was meant to hold), then kept as the evidence for the budget condition of change 8. | 23,846 |

`MapCAS` alone: `MC_abl_cas` (blind map writes, stale reads, all other
repairs on) holds S1-S9 over 29,030,180 / 14,260,313 states (4 min 5 s,
4.1 GB). With a consistent, authenticated find and dedupe by event id, a
stale map only costs re-reads: a regressed cursor re-reads recorded
edits, which dedupe skips; a lost map entry is re-found. CAS on the map
file is therefore defense in depth, not needed for these properties.
It is still recommended, since it saves re-reads and keeps a stale run
from regressing `rr`.

### 6.2a Iteration log (model bugs versus protocol flaws)

- The first repaired model set the cursor after a create to the position
  of the create. `MC_abl_early` produced the F3 trace on it within 342
  states. That was a bug in the repaired model, not just in the ablation:
  the create path skipped the early cursor. The create step now keeps the
  cursor taken at the find. All repaired configs were re-run after the
  fix, and every number above is from the fixed model.
- `MC_live_budget` with budget 3 was meant to hold and did not (B3). The
  trace shows a real requirement, not a model error: a run must afford
  one ticket's reads plus one mutating call. It became change 8's budget
  condition, with budget 4 as the holding config.
- The first model kept a full ledger history ghost and the previous map
  version unconditionally. The state space exceeded 45 million states
  without finishing, so both were reduced (value sets, `mapPrev` only
  when stale reads are enabled), and the checks were split into
  single-concern configs.
- Every other counterexample (D1, F1-F9, D0) was judged a protocol flaw:
  each trace uses only behaviour the tracker, CI or the network really
  exhibits, under assumptions A1-A9.

### 6.3 Liveness under an adversary that never stops (`MirrorRace.tla`)

Two issues, the repaired cursor, per-run budget, weak fairness of the
mirror only; edits unbounded unless stated.

| Config | Converge | InfOften | NoLoss | NotStarved | WritesOnlyLedger | States (distinct) |
|---|---|---|---|---|---|---|
| `MC_Race_bounded` (3 edits, round robin, budget 6) | holds | holds | holds | holds | holds | 2,068 |
| `MC_Race_unbounded` (round robin, budget 6) | violated | holds | holds | holds | holds | 1,947 |
| `MC_Race_unbounded_tight` (round robin, budget 5) | violated | holds | holds | holds | holds | 3,817 |
| `MC_Race_unbounded_fixedorder` (fixed order, budget 5) | violated | violated | holds | violated | holds | 2,443 |
| `MC_Race_budget_too_small` (3 edits, budget 2) | violated | violated | violated | violated | holds | 532 |

Each run finishes in about 1 s.

The Converge counterexample (`MC_Race_unbounded`, a lasso): the mirror
reads issue 1 (value 0), records the edits, and is about to write; the
adversary edits issue 1 to 1 after the read; the write sets 0; the
adversary edits again; and so on forever. Every write succeeds, every
edit is recorded, and the issue is never stably equal to the ledger.
No protocol can do better: the adversary owns the last word between any
two runs.

What holds precisely:

- Safety (S1-S9) holds for any number of edits and any budget: refusals
  and edits only interrupt, never corrupt. (Checked in Mirror.tla with
  edits faster than the budget, `MC_fixed_budget`, and in MirrorRace with
  unbounded edits, `WritesOnlyLedger`.)
- No loss (L2) holds under unbounded edits if every ticket's history read
  fits in a run's budget at least once per rotation: budget >= the reads
  of one ticket (3 calls with the scan) and round robin. It fails when
  the budget is below the reads of one ticket (`MC_Race_budget_too_small`).
- Each issue is equal to the ledger infinitely often (`InfOften`) under
  unbounded edits, with round robin and budget >= reads + one write of one
  ticket. It fails with a fixed order when the budget does not cover all
  tickets (the adversary keeps ticket 1 dirty so its write uses the call
  ticket 2 needs).
- Convergence (L1, eventually always) holds if and only if the
  disturbances are finite: finitely many human edits of repository-owned
  fields, ledger commits, faults and late deliveries. Weaker sufficient
  condition: after some point, each ticket gets one complete processing
  (find, read, write) with no edit to its issue between its read and its
  write. The required fairness is weak fairness of the mirror's steps
  (runs are always eventually started: scheduled runs, change 1), plus
  budget >= reads + one write of one ticket, plus round robin.

## 7. Protocol flaws and the minimal changes

Proposed wording for mirror.md 3.1. Not applied: mirror.md is unchanged.

1. Runs (F1). Add: "Runs are also scheduled (for example hourly), not only
   triggered by pushes to the ticket branch; a tracker edit made after the
   last push is otherwise never seen." The same applies to section 3's
   "Incremental by default: only tickets with events after the last
   published event are touched". That selection must also include issues
   updated in the tracker since the last run (one listing call with
   `since`), or tracker edits to quiet tickets are never reverted or
   captured. (Paper finding: the model has every run visit every ticket.)
2. Cursor (F2). Replace "the tracker's change history since its last
   publish" with "the change history after the cursor, where the cursor is
   the last history position (event id) the mirror read, never the time
   of its publish; the cursor advances only to a position the run has
   read and recorded". As written, an edit between read and write falls
   before the cursor and is lost, which contradicts "The race".
3. Cursor position (F3). Add: "The position is taken before the ticket's
   issues are listed (the first read for the ticket), and a create does
   not advance it."
4. Authenticated markers (F4, D1). security.md 2.11 checks the issue's
   author and an HMAC of the ULID. Both pass for a body a human edited:
   the author is still the bot, and the HMAC is a constant string anyone
   can copy. Change: "A marker counts only in the bot-authored creation
   revision of the issue body (or in a field only the bot can write); a
   marker that later appears in or changes in an edited body is ignored
   for lookup and reported as MIR003." Corollary: the map file entry is
   authoritative; markers are a recovery path.
5. Find-by-ULID (F5). Add: "The lookup must be read-your-writes (list
   the bot's issues with the ticket's label, not the search API). If only
   an eventually consistent search exists, a create whose outcome is
   unknown blocks a new create for that ticket until the lookup is
   current." (Assumption A4.)
6. Duplicates (F6, D0). Replace "Duplicate detection on first sync" with:
   "Every run lists the ticket's issues with the lookup of change 5. The
   map's issue, or the lowest-numbered one, is canonical. Others are
   closed as duplicates of it (never deleted), and their history is read
   with the same cursor, so edits made on them become proposals." The
   claim "never duplicated" must be weakened. A create that times out can
   take effect later, and GitHub's create has no idempotency key, so a
   second issue can exist. The guarantees are: at most one more issue
   per create with an unknown outcome; duplicates eventually closed (L4);
   no edit on them lost (S2).
7. Comment rate (F7). Add: "Before commenting, the mirror reads the
   issue's comments and skips if the bot already commented today; the
   state is the tracker, not the map file." Duplicated deliveries can still
   double a comment (S6 bound: 1 + duplicates). Paper finding: a comment
   whose call is refused is not retried (the next run records no new
   proposal), so the comment is best-effort; record "comment owed" if it
   must not be skipped.
8. Fair order under the rate limit (F8, B3). Add: "Each run resumes at the
   ticket after the last one completed (a pointer in the map file), and
   the per-run budget is at least the reads of one ticket plus one write."
9. Proposal idempotence (F9). Add: "A proposal event carries the tracker
   event id; an event id already recorded on the ticket is skipped." It
   makes "a second run changes nothing" true across a crash between the
   proposal commit and the map commit, and keeps accepted or declined
   edits closed.

Not needed for these properties: compare-and-swap of the map file's
content (see 6.2). Recommended as defense in depth.

## 8. How to run

Java 17+ and `tla2tools.jar` (https://github.com/tlaplus/tlaplus/releases,
v1.7.4). From this directory:

    java -Xmx8g -XX:+UseParallelGC -cp tla2tools.jar tlc2.TLC \
        -workers 4 -deadlock -metadir /tmp/tlc-states \
        -config MC_fixed_race.cfg Mirror.tla

Use `MirrorRace.tla` for the `MC_Race_*` configs. `-deadlock` turns off
deadlock reporting: with the as-written trigger, the system rightly
stops when no push is pending. TLC stops at the first violated
property. The configs that list several temporal properties report only
the first violation. To get a verdict per property (as in the tables),
run once per property, for example:

    for p in Converge InfOften NoLoss NotStarved; do
      sed '/^PROPERTIES/,$d' MC_Race_unbounded.cfg > /tmp/one.cfg
      printf 'PROPERTIES\n    %s\n' "$p" >> /tmp/one.cfg
      java -cp tla2tools.jar tlc2.TLC -workers 4 -deadlock -config /tmp/one.cfg MirrorRace.tla
    done

Every config finishes in under 14 minutes and under 6 GB resident on 4 workers (the slowest is `MC_live_budget`, 13 min 25 s, 5.6 GB). A first, combined fault-liveness config exceeded 15 minutes and was split into `MC_live_lost` and `MC_live_delay`.
To check a different adversary, edit the bounds; state counts grow by
roughly 5 to 40 times per additional human edit.

## 9. Why safety holds beyond the bounds (inductive invariant sketch)

Repaired protocol, any number of tickets, issues, edits, faults and runs,
under A1-A6. Let `Inv` be the conjunction below, with the local
counterparts (the same statements about the mirror's local copy `m.mL`
and its in-flight run) included.

1. Ownership is stable. `au` and `mk0` are set once at creation and never
   written; issues are never deleted. So `Owned(t)` only grows, and
   `Owned(t)`, `Owned(u)` are disjoint for `t # u`.
2. `MapOwn` for `mapf`, `mapPrev` and `m.mL`. Initially all entries are 0. An
   entry is set only by a create the bot made for `t` (so `mk0 = t`,
   author bot) or by a lookup that returns only issues with `au = BOT` and
   `mk0 = t` (change 4). `mapf` takes values only from `m.mL`, and
   `mapPrev` only from `mapf`. Preserved by every step; by (1), nothing
   can invalidate an entry later.
3. Data flow (S1, S4). The only steps that change `r` are human edits,
   `MWrite`, `MCreate`, and deliveries of messages put in flight by
   `MWrite` or `MCreate`. The latter carry `m.sL[t]`, which equals `led`
   at the run's start. No mirror step changes `tf`. The proposal step
   changes only `prop` and `rec`. `led` changes only in `LCommit` and
   `Accept`.
4. Cursor soundness (S2). For every `t`, every human `r` edit at position
   `p <= mapf.cur[t]` on an issue in `Owned(t)` is in `rec[t]`. Proof of
   preservation: `rec` only grows and history is append-only (A1), so only
   a cursor change can break it. The cursor changes only at the map
   commit, to `m.hp` taken at the ticket's first read (changes 2 and 3).
   Let `P` be the history length at that read. By A2 and the
   read-your-writes lookup (A4, change 5), the issue set `S` listed after
   that point contains every issue in `Owned(t)` that existed at `P`. Any
   human edit at a position `<= P` is on an issue that existed at `P`, so
   it is on an issue in `S`. The history read covers `(cur, Len]`, a
   superset of `(cur, P]`. Every such edit not yet in `rec[t]` is in
   `m.ents` (change 9 only removes ids already in `rec`). `MProp` adds them
   to `rec[t]` before `MFin` sets the local cursor to `P`, and a crash
   discards the local cursor. A stale map lowers cursors, which only
   weakens the premise.
5. No reopen (S8). `resolved` is a subset of the union of `rec`, since
   accept and decline only resolve recorded ids. `m.ents` is disjoint
   from `rec[t]` (change 9). A pending proposal's `hs` is built from
   `m.ents`, or extended by them, so it stays disjoint from `resolved`.
6. Comment bound (S6). The bot posts only after reading zero bot comments
   for that issue and day (change 7). With one writer (A6), the only
   other comments for that day are delayed duplicates, counted in
   `dupCom`.
7. Duplicates (S3 and its weakening). A new bot issue for `t` appears only
   (a) from a create the run issued after a consistent lookup found none,
   or (b) from a late delivery of an earlier create. With change 5, (a)
   cannot add a second issue while one exists. So `|Owned(t)| <= 1 +` the
   number of creates with an unknown outcome, and the bound is exact
   (D0).

`Inv` holds initially and is preserved by every action, so it holds in
every reachable state, whatever the sizes. The model checker
cross-checks (1)-(7) for small sizes, including the local counterparts.

Liveness (paper argument). Assume the disturbances are finite, weak
fairness of the mirror holds, runs are scheduled, the budget is at least
the reads of one ticket plus one write, and runs use round robin. Then,
after the last disturbance:
- Each run completes at least the ticket it starts with, or makes one
  persistent mutation (a create, a write, a close). Such mutations are
  never undone, because there are no more disturbances.
- Round robin moves the start forward, so every ticket is completed
  infinitely often (L3).
- At the first completion of `t` after the last disturbance, the run
  - records every outstanding edit (by 4, L2),
  - closes all duplicates (change 6, L4),
  - writes `led[t]`, which no longer changes, and the issue stays equal
    (L1).

## 10. Limits of the model

- One human user, so the per-user collapse of mirror.md is per ticket here;
  unmapped users' per-issue collapse is not modeled.
- Fields: one repository-owned and one tracker-owned value per issue; the
  body marker is a separate field reverted with `r`. Marker edits are not
  turned into proposals (they are spoofing, MIR003).
- Value domain {0,1}: a human edit back to the ledger value is still a
  proposal, which the protocol allows. `WritesFromLedger` checks values
  against the set of values the ledger held, because a full ledger
  history ghost made the state space too large.
- Each tracker call is one atomic step. "List comments and post" is one
  call (justified by A6). The history read is one call returning a
  consistent prefix (A2).
- The ledger snapshot is the tip at run start; only the map file can be
  stale. If the ledger is read stale too, a run publishes an older
  projection, which the next run corrects; safety is unaffected because
  the stale value was a ledger value.
- Conditional writes (If-Match) are not modeled. They are not needed:
  no-loss rests on the history (A1). For fields whose tracker has no
  history, the race in 3.1 does lose the edit unless conditional writes
  exist, as mirror.md already says for adapter capabilities.

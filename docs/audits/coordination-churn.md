# Coordination churn self-audit (2026-07-26/27 zero-drive)

Coordinator-authored retrospective over ~160 ticket closures landed in
one continuous drive. Every item below recurred enough times to be a
design defect in the workflow, not operator error. Source: the drive's
own land logs and send-back cycles. Each item names its design-out;
the fix tickets are filed as children of the churn-reduction epic.

## Ranked churn items

### 1. Benign ClaimDivergence re-land cycles (~10 occurrences)
Every post-close touch (mutant-kill send-back, merge, recap edit) or
main advance stales the Done report's captured test-count claim, and
land refuses with `recorded 0/0, re-run shows N/N passing`. The cure
is always identical: `done-report --base-ref main`, commit, re-land.
When the fresh count is a strict improvement (0/0 -> N/N passing, or
N/N -> M/M with M >= N, all passing), the refusal protects nothing.
**Design-out:** land auto-accepts a strictly-improved passing
test-count claim and rewrites the recap itself in the landing commit;
only genuine regressions (fewer passing, any failing) still refuse.

### 2. Stacked-sibling "CommitFailed" false alarms (~8 occurrences)
When one worktree carries several tickets, the first land's squash
absorbs the siblings' files and ledger state; each subsequent land
stages an EMPTY squash and the final commit exits 1 with no stderr,
reported as scary `CommitFailed` -- the coordinator then manually
verifies state+content on main every time (T-0916, T-0739, T-0902,
T-0653..T-0657, T-0965, T-0963...). **Design-out:** land detects the
empty-stage case, verifies the ticket is `done` on main with its
scoped content present, and reports `absorbed by prior land` as a
clean success.

### 3. Append-only merge-conflict hotspots (~8 occurrences)
Three regions conflict on nearly every concurrent land: `frob.toml`'s
`[gates.severity]` block, `_KNOWN_GATE_RULES` in
`src/frob/gates/__init__.py`, and `docs/audits/*.md` remediation
logs. All are semantically append-only unions; every conflict was
resolved keep-both-chronological, mechanically. **Design-out:**
land-side union merge for registered append-only regions (marker
comments delimit them), or a merge driver keyed on one-entry-per-line
structure, so concurrent appends never conflict.

### 4. Land invocation ergonomics (~15 occurrences)
Every land requires the ritual: `git checkout -- uv.lock` on both
sides, cd to the ROOT checkout (the root==worktree guard fires on any
chained cd), then the land command. The uv.lock half was reduced by
T-0789 (Makefile) but worktree flap persists; the cwd half burns a
round-trip whenever forgotten. **Design-out:** land resolves the
registered root itself regardless of cwd (it knows the worktree; the
root is its git common dir's primary checkout) and performs the
uv.lock reset internally on both sides before the dirty check.

### 5. Harness auto-background stalls (~10 occurrences)
Long commands get auto-backgrounded by the agent harness at ~120s and
agents then "wait for the notification" that never comes, requiring a
coordinator nudge each time. Process rules in dispatch prompts reduced
but never eliminated it, because the playbook itself documents
backgrounding as normal. **Design-out:** playbook rewrite -- foreground
with explicit `timeout` wrappers is the ONLY sanctioned pattern for
agents; plus a `frob check --budget <seconds>` mode that self-chunks
stage groups to fit, removing the main reason agents run long
commands at all.

### 6. Post-close evidence mutation is second-class (~5 occurrences)
TEST016 send-backs after close work fine for `scope`/`evidence`/
`done-report` (they apply to a done ticket), but `close` refuses
`done -> done` and `start`/`sweep` refuse on done tickets, so the
lifecycle cannot re-run its own verification after strengthening --
the coordinator lands on trust in the recap instead. **Design-out:** a
`frob ticket reverify <id>` verb that re-runs close's full check suite
against a done ticket without a state transition, for exactly the
send-back-after-close flow.

## Already designed out during the drive (for the record)
- done-report hang: T-0887/T-0919 (fail-fast base-ref + shared spawn).
- Reactive scope-adds: T-0998 (doc/code/test-edge closure at
  declaration time, in flight).
- Directive target-form mistakes: DOC007 born at ERROR (T-0986).
- Version/archive/ledger clobbers by land: T-0992/T-0959/T-0740
  monotonicity + splice + id-integrity guards.
- Stale-baseline confusion (486 "TEST warnings" that were 15):
  decompose-then-execute protocol with fresh measurement (T-0972,
  T-0875) is now the standing pattern for any old count.

# v1 to v2 gap analysis (2026-10-04)

Four slices, each proving coverage of its inventory. Status labels: BUILT,
TICKETED, DESIGNED (not ticketed), DROPPED-ON-PURPOSE, MISSING.

| Slice | Inventory | BUILT | TICKETED | DESIGNED | DROPPED | MISSING |
|---|---|---|---|---|---|---|
| [A](A-keep-recommendations.md) earlier KEEP/MERGE notes | 677 items | 267 | 61 | 286 | 40 | 23 |
| [B](B-backlog.md) v1 open backlog | 970 tickets, 25 clusters | 219 | 2 | 158 | 192 | 170 (+229 v1-internal) |
| [C](C-features.md) v1 source modules and features | 118 findings | 31 | 15 | 31 | 23 | 18 |
| [D](D-incidents.md) incidents and structural bugs | 45 failure classes | 16 | 7 | 5 | 3 | 14 |

## Confirmed v2 bugs (reproduced against the v2 binary), filed

| Ticket | Bug | Source |
|---|---|---|
| ~CKZS2R3 | close done with unmerged branch commits | C P-01, A PT-3, B PT-1 |
| ~KAD47SZ | unreadable tracked files vanish from check | C P-02 |
| ~SDX5V8M | a +++ line in a field corrupts ticket.md | D P-01 |
| ~0V1WTNR | close/drop leave the lease behind | D P-03 |
| ~A6C2R1C | rule evaluation errors yield zero findings; corrupt index passes check | D P-05 |
| ~X4HH43T | ledger CAS retries have no backoff | D |
| ~G7AXHR1 | closing a ticket blocked by an open ticket succeeds | D, A PT-3 |
| ~BDHEZAT | linked-worktree ledger commit leaves a staged deletion in the primary | D P-04 |
| ~M0388X5 | one corrupt lease file blocks the whole clone | D |
| ~F4YA3S9 | land ratchet is count-blind; base cache not keyed by engine | D P-06, P-07 |
| ~WS4WZBD | check --fix writes non-atomically without a digest guard | D P-02 |

## Highest-value proposals not yet filed (deduplicated across slices)

1. Rule-id map v1 to v2 and refusal of ambiguous ids in migration; resolve v2's own TICK004/TICK005 collisions with planned tickets (A PT-1).
2. Bug repro must fail at the parent commit (A PT-4, B PT-4).
3. Land guards: every ticket-owned hunk published, deletion filter, passengers (A PT-5, B PT-6).
4. Scope glob lint at write time: zero matches, bare names, whitespace (B PT-2).
5. Skipped or ignored tests never satisfy evidence (B).
6. Build identity in --version, the envelope and doctor (B PT-9).
7. frob hook with measured precision (A PT-13, B PT-3).
8. First-party Python adapter, then TypeScript and C-family (C P-03): 7 of 9 fleet repositories are Python-dominant.
9. frob serve: a thin MCP surface generated from command metadata (C P-04).
10. SYS013/SYS014 undeclared-flow and public-surface rules (A PT-6).

## Owner decisions needed

1. v1 backlog import: migration.md imports all 970 open tickets; B proposes importing done/dropped as history, only requirement-bearing clusters as open, and bulk-closing the rest as wont-fix.
2. Web-app and STORE/SYSDESIGN lint families: dropped only in a note, never in the decision log; formally drop or keep as an optional pack.
3. Priority of language adapters (Python first?).
4. Shape of frob serve (generated thin MCP surface vs none).

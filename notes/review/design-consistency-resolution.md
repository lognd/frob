# Resolution of notes/review/design-consistency.md

Status: 2026-10-02 pass over docs/design only. No code, no cargo, no frob,
no commit. Decisions D1-D11 are the coordinator's; they win over the
review's alternatives. Decision-log rows added: D61 (supersessions), D62
(Unresolved gate and rule metadata), D63 (layering and owners), D64
(digest scheme and milestone 2). Rows D56-D60 stay decisions with the
acceptance parenthetical (D7).

Legend: applied = review's suggested edit made; Dn = coordinator decision
applied instead; ticket = recorded as a milestone-2 item in
build-test-ci.md Milestone 2.

| Id | Outcome | Where |
|---|---|---|
| H1 | applied (D2 for layering): code-model.md 5 is a pointer, `ir_map` became `rho`, `bind`, `cap`; rules.md level-2 rules use `group` role loop and `apply` role call; boundaries gob-ir row; goals; README D4 | code-model.md 3 and 5, rules.md 2-3, boundaries.md 2.1, goals.md |
| H2 | D2 | architecture.md 1, boundaries.md 2.1, 4, 6, code-model.md 3, README D31 and D63 |
| H3 | D1: one mechanism `[check] fail_on_unresolved`, exit 1, three required cases; landed exit.rs skips Unresolved, ticket item 1 | cli.md 2, rules.md 1 and 4, products.md 6, boundaries.md 1 and 6, grimble-model.md 9.5, universal-model.md 4.2, build-test-ci.md, README D62 |
| H4 | D3: NotApplicable is a query answer; whole-scope NotApplicable emits nothing and is listed once per language in the fidelity report. The evidence note lint-requirements.md 3.1 was NOT edited (outside the allowed paths); universal-model.md 4.2 is now authoritative on the point | universal-model.md 4.1, 4.2, 6.1, 8 |
| H5 | D3: P+ on an opaque subject emits one Unresolved with the reason code | universal-model.md 4.2, 4.6 |
| H6 | applied: `polarity` required, `needs(Q::...)` replaces `inputs`, `subjects_examined`, `must_measure`, `source_rule`, three-fixture doctrine, page rows for polarity and needs | rules.md 2, documentation.md 3 |
| H7 | D4: NEAT, CI, DK are grimble (grimble-lints, new grimble-ci); family table, capability map, config rows, cicd.md and neatness.md say grimble | boundaries.md 1, 2.3, 2.5, rules.md 3 and 8, neatness.md, cicd.md 3, 5, 6 |
| H8 | D5: scheme 2 facets Sig, Body, Doc, Attr, Contract; `digest_scheme`; D43 superseded; consumer import waits; REATTEST reworded to stale/DRIFT | universal-model.md 7.1, code-model.md 2, grimble-model.md 9.2, migration.md, README D43 and D64 |
| H9 | applied (second option): frob binds `frob:` directives in .grmb only through `grimble graph --json` (`grimble.graph/1`); `Language` is an open registry | grimble-model.md 9.3, code-model.md 3, documentation.md 3 |
| H10 | applied with D9: one hierarchical atom registry and one callee table per language in gob-ir; `[neat.effects]` and detectors are views; `frob:effects` claims and `grimble:effect` attestations name registry atoms | grimble-model.md 9.6, code-model.md 4 and 7, neatness.md 3, boundaries.md 2.3 |
| H11 | applied: lexical queries (`text`, `literals`, `prose`) read an opaque payload; marked `lexical` in the 47-query table | universal-model.md 2.2, 5 |
| H12 | D6: sixth cell `not-applicable` (never Unresolved); `unknown` is Unresolved; detector row schema and `detectors(lang, atom)` copied into 9.6; code-model.md 7 points there | grimble-model.md 4 and 9.6, code-model.md 7 |
| M1 | applied: EBNF in code-model.md 2 with `{n}` anonymous index; multi-part units are one identity; migration says additive | code-model.md 2, universal-model.md 2.6, migration.md 3 |
| M2 | applied: `kind = symbol \| flow`, `digest_scheme`, optional attr, frob.lock symbol entries only, planner to gob-lock (G05), LOCK_VERSION bump with v1 reader | grimble-model.md 9.2, code-model.md 2 |
| M3 | D5: the Contract facet replaces norm_sig; flow entries carry the contract digest per end | grimble-model.md 9.2, universal-model.md 7.1 |
| M4 | D10: every new knob added with product file, default, enforcement flag, owning crate | architecture.md 6, universal-model.md 4.6 |
| M5 | applied: `[compute]` has one home (frob.toml), sibling JSON carries the compute digest, mismatch is an incompatible sibling | architecture.md 6, cli.md 2 |
| M6 | applied: `[rules.<id>] severity` | cicd.md 5 |
| M7 | D9: milestone-2 directive table with surface, target, evaluator; `frob:idempotent` discharged by a bound idempotent test; `grimble:binds` added | code-model.md 4, grimble-model.md 4 |
| M8 | applied: `doctor --languages` is milestone 2 with U semantics; added `grimble doctor|fmt|exceptions`, `init --ci`, `audit --online`; `grimble vet` is milestone 2 after the cut | cli.md 4, grimble-model.md 9.7 |
| M9 | D8: Milestone 2 section; frob-check and frob-land marked landed, self-host switch pending | build-test-ci.md, monorepo.md 5, README D55 |
| M10 | D11 and applied: 47-query table, polarity table, CI predicates, detector schema, sibling JSON fields, G01-G19 and NEAT table are now in design files; notes stay as evidence | universal-model.md 4.2 and 5, cicd.md 5, grimble-model.md 9.5-9.6, build-test-ci.md |
| M11 | applied: survey numbering adopted (DK002 base-pinned, DK003 no-latest, CI015 archived or EOL, CI002 predicate, GHA F3 first), "note" mapped to Advisory, section pointer fixed | cicd.md 4 and 5 |
| M12 | applied: tool stage `parser` and id map, `source_rule` on Finding, EXC017 for native suppressions; spawn table lists zizmor, actionlint, hadolint | rules.md 2 and 4, exceptions.md 6, git-io.md |
| M13 | applied: gob-check, gob-pattern, grimble-ci rows, recount (24, 16, 12, 10), `apply_exceptions` named as the thing G06 moves | boundaries.md 2.1, 4, architecture.md 1, rules.md 8 |
| M14 | applied: Location enum, FindingRecord `location` object, SARIF logical locations listed | universal-model.md 8 |
| M15 | applied: one Must/May/Unknown vocabulary with landed-variant mapping; selection is a lower bound reporting Unresolved and widening to the crate | code-model.md 6, rules.md 4, build-test-ci.md 5 |
| M16 | applied: a site whose outcome was Unresolved is not stale | exceptions.md 3, universal-model.md 4.2 |
| M17 | applied: Unresolved accepts only defer and baseline; EXC016 | exceptions.md 1 and 6, universal-model.md 4.2 |
| M18 | applied: boundaries family rows follow D45; REATTEST digest source is `frob.lock` only | boundaries.md 2.5, exceptions.md 1 and 2, architecture.md 3 |
| M19 | applied: Pn and Pc decide on bounds, P0 needs Exact | universal-model.md 4.2 |
| M20 | applied: CAP002 is P-, polarity column added to the drift table, shrink tied to Exact absence | grimble-model.md 4 and 9.4 |
| M21 | applied: PM026 polarity P+, Unknown surface gives Unresolved on the close guard | pm-enforcement.md |
| M22 | D7: D56-D60 kept as decisions with the acceptance parenthetical; precedence sentence names the new files; D61 lists superseded rows | README.md |
| M23 | applied: version answered (D42), remaining spike is ast-grep `Doc` over U, blocks G17 | rules.md 3 |
| M24 | applied: compute-config digest in the parse key, scope graph is a repo-scope artifact | code-model.md 8, architecture.md 2 |
| L1 | applied | grimble-model.md 9.8 |
| L2 | applied: open question 5 | universal-model.md 9 |
| L3 | applied | universal-model.md 2.4 |
| L4 | applied: excused = atom explicitly excluded with a reason | grimble-model.md 9.6 |
| L5 | applied: `because` in the .grmb grammar and examples | grimble-model.md 2 and 4 |
| L6 | applied as a note (conversion happens at the self-host switch) | build-test-ci.md status |
| L7 | applied: glossary row in U 4.1; SYS001 alias SYS-EMPTY-SELECTOR; UnresolvedExit; "reaches" | universal-model.md 4.1, grimble-model.md, boundaries.md, exceptions.md, code-model.md 6 |
| L8 | applied: build-test-ci.md says "Target" and states the current gap; workflow lint row added | build-test-ci.md 4 |
| L9 | applied: `TicketSchema`, `Lang`, scope File or Repo; ticket.json note, sibling.json and fidelity page rows, polarity row | rules.md, boundaries.md, tickets.md, documentation.md |
| Finding 13 (design claims only in research notes) | D11 | see M10 |

Not applied here: edits to notes/research/lint-requirements.md 3.1 (H4)
and any other note, because the task limited changes to docs/design and
this file. Their supersession is stated in the design files.

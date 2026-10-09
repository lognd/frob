# Exceptions: waivers, debt, quick fixes, and permanent decisions

Status: current
Owner: gob
Decisions: none
Audience: contributor

Provenance: written under T-0001 (a v1-format id that migrates with an alias). Owner direction 2026-10-02: v1 never had a
clean line between a waiver, debt, a quick fix that should expire
"somehow", and a permanent decision. Evidence: notes/v1/gates-and-rules.md
sections 15-16 (waive with until, follow_up, permanent, presets, debt,
deprecated, ratchet pools, rapid debt, twelve waiver hygiene rules, an
audit watermark), notes/crunk.md FROBLEMS rows 7 and 15 (permanent
waivers impossible because WIRE002 demanded an open ticket, so anchor
tickets were kept open forever; self-citing follow_up blocked lands).

## 1. One primitive, four kinds, every kind has a machine-checkable exit

An exception suppresses one rule at one site. What differs is how it
ends. The kind is mandatory and determines the exit condition the tool
can evaluate without human judgement; there is no kind whose exit is
"someone remembers". Which findings each kind may park: an Unresolved
finding (universal-model.md 4.2) can be parked only by `defer` (with a
ticket) or `baseline`, never by `accept`, because accepting a loud
"could not examine" would silence the failure without supplying the
declaration that fixes it; an `accept` that names an Unresolved finding
is EXC016.

| Kind | Meaning | Exit condition (evaluated by the tool) | Must carry |
|---|---|---|---|
| `accept` | this rule does not apply here by design; permanent | never expires, but is re-validated: becomes STALE when a fresh full evaluation finds no matching finding, and REATTEST when the bound symbol's body digest differs from the attested digest the accept verb recorded as a lock entry in `frob.lock` (D45; the one REATTEST source) | `because` naming an ADR, a style anchor, or a one-sentence reason; for Error-severity rules a `review` event by a second identity or by an owner listed in `[exceptions] owners` (an audit trail, not an authorization control: the actor is a label, so a determined caller can set any label; real approval control is the host's review and branch protection) |
| `defer` | real debt, to be paid by a ticket | the named ticket reaches a terminal state (then the defer goes red until removed), or an optional earlier `until` date or metric target | an open ticket of type bug, task or chore; a reason |
| `hotfix` | a quick solution that must be revisited | hard expiry at `[exceptions] hotfix_days` (default 14), no extension; converting to `defer` requires a ticket; `land --hotfix` files the follow-up ticket itself | reason; the auto-filed ticket id |
| `baseline` | mass legacy findings admitted when a rule is introduced or tightened | a baselined key disappears when its finding disappears; the pool can only shrink; a key may be removed with a reason, never added after creation | the rule id, creation reason, and the pool file |

What is gone: `permanent="true"` (that is `accept`), `follow_up=`
(that is `defer`), `frob:debt` as a separate verb (it is `defer`),
presets (a preset was a way to avoid writing a reason; `accept
because=style#anchor` covers the legitimate cases), rapid-debt
(there is no deferred verification to owe), the anchor-ticket
workaround (nothing requires an open ticket to be permanent).

Evaluation boundary. An exit that names a ticket (`defer`, and the
auto-filed ticket of `hotfix`) is evaluated by frob only, because only
frob knows tickets (D28). grimble and crunk parse the exception, treat
`ticket=` as an opaque string and emit it in their `--json`; frob's
orchestrated check reads that JSON to decide EXPIRED and to enforce the
close guard. A standalone grimble or crunk reports such an exception as
UnresolvedExit (an exception state, not the Unresolved severity of
universal-model.md 4.1): parsed, valid, not evaluable here. Date-based and
digest-based exits are evaluated by each product itself. The budget per
component uses frob's component registry, so budgets are frob's too.

Milestone 1 (D36) implements `accept` and `defer` only, with EXC001,
EXC003, EXC005 and EXC007 (section 6 gives their meaning as built);
`hotfix`, `baseline`, budgets, the audit and `convert` are Milestone 2
or later (D36). A flagged exception still suppresses its finding; the
EXC finding is what fails the gate. The optional `until=` is parsed but
not evaluated yet.

## 2. Syntax

Inline, one line, machine-read, exempt from the NARR narrative rules
(documentation.md section 4):

```
# frob:accept COV006 because="docs/decisions/2026-10-02-dispatch-tables.md"
# grimble:defer ARCH001 ticket=01J9QKX3M8Z4T7N2V5B6C0D1E2 because="split after the parser lands"
# grimble:hotfix SEC002 because="rotate key, see incident ticket" ticket=01J9QMA7R2K5W8Y1H3F6G9P4S0
```

All four exception verbs spell the reason `because=` (the milestone-1
parser accepts only that spelling).

File- or package-scoped exceptions and anything longer than one line
live in `exceptions.toml` at the repo root (tracked), with one array
per product (`[[frob.exception]]`, `[[grimble.exception]]`,
`[[crunk.exception]]`; each product reads only its own), one table per
exception with the same fields plus `scope = "crates/x/**"`. The same
file holds only exception records; the attestation of every `accept`
(the attested body digest and time) is written by the accept verb as a
`symbol` entry in `frob.lock` (gob-lock, D45), and REATTEST compares the
live digest with it, so there is one source of truth for the digest. The
baseline pool is
`<product>-ratchet.lock.json` as before. grimble and crunk use the same
primitive through `gob-rules` with their own namespaces
(`grimble:accept`, `crunk:defer`).

frob also writes an `exception` event on the ticket a `defer` or
`hotfix` names, so the ticket page shows what is parked on it, and a
ticket cannot close while a `defer` still points at it (found through
the sibling `--json`) unless the land that closes it removes the defer
(the finding is fixed) or converts it.

## 3. Lifecycle and the single audit view

```
                 created
                    |
   accept --------- active ---- STALE (matches nothing)  -> removed by --fix
      |              |
      |          REATTEST (symbol body changed)          -> ack with reason or remove
   defer ---------- active ---- EXPIRED (ticket closed, date or metric met) -> error
   hotfix --------- active ---- EXPIRED (days elapsed)   -> error, convert or fix
   baseline ------- active ---- RETIRED (finding gone)   -> key dropped automatically
```

`frob exceptions` is the one verb: `list [--kind --stale --expiring
--by-rule --by-component]`, `audit` (a sampled review pass that records
verdicts STILL NEEDED, OBSOLETE, COP-OUT as events; the watermark idea
from v1 kept, but the sample is small and the verdicts are data),
`convert <id> --to defer --ticket ...`, `prune` (removes STALE and
RETIRED, is the `--fix` for EXC rules), `budget` (section 4).

STALE is decided only from a fresh full evaluation of that rule over
that file in the current run: never from a cached memo, never after an
`--only` run that skipped the rule, and never after a rule version bump
or a deleted `.frob/` (unknown is not stale). A site where the rule's
outcome in this run was Unresolved (an opaque subject, a `hole` such as
a parse error, a May edge) is not stale either: it is unprovable, so the
rule outcome must carry its Unresolved sites and neither EXC013 nor
`exceptions prune` may treat an accept there as matching nothing.
`exceptions prune`
performs that evaluation itself before removing anything. A baseline
key is a fingerprint (rule id, symref or file path, hash of the
normalized message), never a line number.

## 4. Budgets, so debt cannot quietly become the plan

| Control | Default | Effect when exceeded |
|---|---|---|
| `[exceptions] max_defers_per_component` | 25 | new `defer` in that component refused until one is paid or an owner raises the budget with a `budget-raise` event under the root `events/` |
| `[exceptions] max_defer_age_days` | 90 | EXC010 Warn at 60, Error at 90: the defer must be paid, converted to `accept` with review, or re-justified (a `review` event under `events/` that resets the clock at most once) |
| `[exceptions] hotfix_days` | 14 | hotfix EXPIRED, Error |
| `[exceptions] max_hotfixes_open` | 5 | `land --hotfix` refused |
| baseline pool growth | zero | a pool can never gain a key after creation; tightening a rule creates a new pool with its own reason |
| accept density | `max_accepts_per_rule_per_file` 3 | more than that is a sign the rule or the file is wrong; EXC011 Warn, the remedy suggests a style decision or a rule config change |

All `[exceptions]` knobs, including `owners`, `reattest_warn_days` and
`max_duplicate_reasons`, are materialized in the config file by `frob
init` (architecture.md section 6, which lists them); a missing one is
CFG001. Budgets and the audit are Milestone 2 or later (D36).

`frob status` prints the exception ledger beside the ticket queue:
counts by kind, age distribution, those expiring within a `--within <days>` window, and the trend
since the last release. The PM cycle report shows debt paid versus
added per cycle.

## 5. Reason quality (the cop-out problem)

Shared with ack reasons and waiver reasons in v1, now one checker in
`gob-rules`: minimum length, a boilerplate deny-list, no duplicate
reason text across more than `[exceptions] max_duplicate_reasons`
exceptions, and for `accept` on Error-severity rules the reason must
resolve to a document anchor or carry a `review` event. A reason that merely restates the rule name
("COV006 does not apply") is refused at write time.

## 6. Rules (family EXC, replacing the twelve v1 waiver rules, the three v1 debt rules, and parts of WIRE and REL001)

Milestone 1 ids, as implemented in `frob-obligations` (these four
numbers are authoritative; the design numbering that followed the
earlier draft is re-spelled below):

| Id | Fires when | Severity | Crate |
|---|---|---|---|
| EXC001 | exception with a bad reason (empty, boilerplate, restates the rule id, repeated words, under the minimum length) | Error | frob-obligations |
| EXC003 | `defer` names a ticket that has reached a terminal state | Error | frob-obligations (ticket-bound, frob only) |
| EXC005 | `accept` whose bound symbol body digest differs from the digest in `frob.lock` (REATTEST) | Warn | frob-obligations |
| EXC007 | `defer` names a ticket that does not exist | Error | frob-obligations (ticket-bound, frob only) |

Milestone 2 or later (D36), designed and not yet implemented:

| Id | Fires when | Crate |
|---|---|---|
| EXC002 | exception names a rule that can never match at this site (wrong scope) | gob-rules |
| EXC004 | `accept` REATTEST escalates to Error after `[exceptions] reattest_warn_days` | gob-rules |
| EXC006 | `hotfix` EXPIRED | gob-rules |
| EXC008 | exception on a rule declared `waivable = false` | gob-rules |
| EXC009 | over-broad scope (package exception on a rule that is not package-scoped) | gob-rules |
| EXC010 | defer older than the age budget | gob-rules |
| EXC011 | accept density exceeded | gob-rules |
| EXC012 | `accept` on an Error rule without a document anchor or review | gob-rules |
| EXC013 | exception is STALE (a fresh full evaluation finds no match; Warn, the fix is `prune`) | gob-rules |
| EXC014 | `defer` EXPIRED by date or metric target (`until=`) | frob-obligations (ticket-bound, frob only) |
| EXC015 | `defer` names a ticket not of an allowed type, or names itself | frob-obligations (ticket-bound, frob only) |
| EXC016 | `accept` names a rule at a site where the finding is Unresolved (park it with `defer` or `baseline`) | gob-rules |
| EXC017 | a native suppression (`#[allow(...)]`, `# zizmor: ignore[...]`, `// eslint-disable`) of a rule bound through a `[[check.tool]]` stage with no matching frob exception | gob-rules |

Severity defaults: EXC016 is Error and EXC017 is Warn; EXC005 is Warn in milestone 1; from Milestone 2 EXC004
is Warn for `[exceptions] reattest_warn_days` (default 14) then Error,
measured from the commit date of the change that made the digest differ
(found through the symbol history; nothing extra is stored); EXC013 is
Warn; everything else Error. Release (`frob release
stamp`) refuses while any EXPIRED exception exists; it does not refuse
on open `defer` (v1's REL001 refused on any debt, which pushed people
toward permanent waivers instead of honest defers).

## 7. Migration from v1

`frob migrate exceptions` rewrites: `frob:waive` with `follow_up=` or
`until=ticket-closed:` to `defer`; `frob:waive permanent="true"` to
`accept` with the reason, flagged for review if the rule is Error;
`frob:waive` with only a reason to `accept` when the reason resolves
or cites a doc, otherwise to `defer` against an auto-filed triage
ticket per component ("classify legacy waivers in X"); `frob:debt` to
`defer`; `until=<date>` to `hotfix` if within `[exceptions] hotfix_days` else
`defer`;
presets expanded to their text. The anchor tickets v1 kept open as
waiver targets are closed in the same migration once nothing points
at them.

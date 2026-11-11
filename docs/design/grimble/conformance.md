# The .grmb language: conformance, example and milestones

Status: draft
Owner: grimble
Audience: rule author

Section 18 of the [.grmb language specification](grmb-spec.md), moved here verbatim by ticket ~EBGD47R to keep that file under 2500 lines. The section numbers are unchanged, so a citation such as "18.2" or "18.3" names the section below.

## 18. Conformance, example and milestones

### 18.1 Conformance corpus

The conformance corpus is `crates/grimble-model/tests/corpus/`, run by
gob-mdtest (one case per directory with an `expect` file, D51; U cases hold
the expected term and scope graph, shared/universal-model.md 3.3). Its groups: `lex/` and `encoding/` (2),
`directive/` (8), `include/` (3; the directory keeps its pre-`use` name),
`version/` (3.4), `entity/` (4), `scope/` (5), `selector/` (6),
`exception/` (7), `u/` (9), `fmt/` (9.3, 9.6), `recovery/` (holes),
`plan/` (sections 11-16: one directory per construct and per MDL022-MDL034
rule, plus `web_app` and `thermostat`, the rev 1 worked examples) and
`example/frob.grmb` (a model of this repository that loads with zero
Errors and the documented MDL005 warnings). notes/research/grmb-corpus/
is the DESIGN corpus, the home of worked examples (by hand, never run).

### 18.2 Example

One file, both layers. The braced `system` at the top level makes the
file's other planning items members of `web_app` (11.2).

```
grimble = "2";
module shop;

/// The web shop.
system web_app { ambient restart max 3 within 60 s else escalate; }

node frontend : authenticated { owns "src/frontend/**"; }
node backend : trusted { owns "api/**"; }
flow f_ui_api : frontend -> backend { label Pii; }
flow f_api_ui : backend -> frontend { label Internal; }
boundary b_session endorse f_ui_api : authenticated -> trusted when "session checked";

actor customer : human;
goal customer { browse; place_order requires browse; }

step customer.submits_cart;
step customer.pays : { ok, declined, timeout };
step system.confirms_order;

/// Guest or account checkout.
scenario checkout realizes customer.place_order {
  customer.submits_cart
    -> customer.pays => {
      ok => system.confirms_order -> end ok;
      declined => retry max 3;
      timeout => end err(timeout);
    }
  verified_by "tests/e2e/checkout.spec.ts";
}

impl system.confirms_order for checkout {
  handler = "api/orders.py::confirm";
  verified_by "tests/api/test_orders.py::test_confirm";
}

claim checkout_fast { bound latency web_app.checkout <= 2 s; }
```

Typing: `checkout` is exhaustive over `{ ok, declined, timeout }`; the
retry targets `customer.pays` (the matched element) and ends `end
err(declined)` after 3 tries, so `E(checkout) = { declined, timeout }`.
What the rules report, assuming every named file exists (complete for the
families MDL, FLOW, CLAIM, PLAN, SYS015/SYS016, AMB):

- No MDL or FLOW finding (the `endorse` boundary carries the flow).
- PLAN001 on `web_app.customer.browse` (no scenario); PLAN003 on the uses
  of `customer.submits_cart` and `customer.pays` (no impl), so `checkout`
  stays `declared`; PLAN005 on the leaves `browse` and `place_order`.
- PLAN006 once per pair `customer.pays.ok`, `.declined`, `.timeout` (no
  `for`); PLAN016 on `declined => retry max 3` (`pays` not `idempotent`).
- SYS015 Unresolved on `(submits_cart, pays)` and `(pays,
  confirms_order)` (`pays` has no node); SYS016 Unresolved on both flows
  (P- over Unknown nodes, D179).
- AMB008 on the policy; CLAIM003 Unresolved on `checkout_fast`; the impl
  is `covered` (both selectors resolve).

Adding `fraud_hold` to `customer.pays` makes `checkout` MDL022 naming
`fraud_hold`. Larger models, one per domain, are in the design corpus
(d01-d11).

### 18.3 Milestones

| Id | Milestone | Content | Exit |
|---|---|---|---|
| P0 | think-aloud check | five authors read and write the operators, `unknown`, `one_of` and `sorry` aloud on the corpus (notes/research/grmb-corpus/) before the grammar freezes (C32, D139) | the confusion list is empty or each item has a ticket |
| P1 | grammar and well-formedness | lexer tokens and contextual words, parser for the seven items, MDL022-MDL034 including exhaustiveness and error-set typing, U encoding of section 9, fmt rules of 9.6, conformance corpus (`plan/` directories per rule and per construct), the keyword table of 2.6 in grimble-model, shared/rules.md MDL range note; the cycle 1 respellings with MDL012 on the old forms | corpus green; every MDL row of every design-corpus EXPECTED and IF EDITED block is reported, and no MDL finding outside those lists fires on the unedited text (each later milestone checks its own families the same way) |
| P2 | binding and status | realization, waypoint and `verified_by` rows in B, `status` and `status_hi` (12.8), obligations, PLAN family registration and PLAN001-PLAN005, PLAN007-PLAN010, PLAN012-PLAN016, PLAN018, PLAN020, PLAN027, graph JSON additions (section 17.1) and sibling.json `$defs` | graph JSON of the examples validates against the strict schema; every row of the design corpus for the PLAN ids in this milestone's content is reported and no other finding of those ids fires |
| P3 | the frob join | `implements design:` validation for planning anchors, overlay (17.3), PLAN021, PLAN022 and PLAN052 (they read the lock), PM037-PM039, PM046-PM049, close guards `design_bound` and (opt-in) `design_verified`, `frob plan --from-design` with `--apply` and `--findings` | a plan run on the example of 18.2 is idempotent; a close is refused while an impl is declared |
| P4 | verification and coverage | `verified_by ... for` arm evidence, PLAN006 and the verification rules PLAN050, PLAN051, PLAN056-PLAN058, derived V-model levels and links (13.3) fed to the kernel closure with suppression | closure over a mixed vmodel and planning model reports one finding per root cause; every PLAN006, PLAN050, PLAN051 and PLAN056-PLAN058 row of the design corpus is reported and no other finding of those ids fires |
| P5 | renderings | `grimble graph --mermaid` sequence per scenario, structure view and goal tree; `grimble show --prose`; `grimble trace` | insta snapshots of the example of 18.2 and corpus d02 |
| P7 | impl chains and ambient faults | sections 14-19: waypoint chains, outcome maps, required waypoints, AMB rules and the code-fact rules PLAN011, PLAN030-PLAN034, PLAN041, PLAN042, PLAN044, and PLAN040; incremental re-check within a stated budget (C33) | the corpus d01 chain checks on a Python and a TS binding with the Unresolved path exercised; every AMB, PLAN011 and PLAN030-PLAN044 row (PLAN043 retired) of the design corpus is reported and no other finding of those families fires |
| P6 | behaviour to architecture | `node(st, s)` (13.4), PLAN009, SYS015 | every SYS015 and SYS016 row of the design corpus is reported (d02: SYS015 Unresolved on its two pairs, an Error on one once its nodes are declared as its IF line says) and no other SYS015 or SYS016 finding fires |

Order: P0 before P1; P1 before everything; P2 before P3, P4, P5, P6; P3 to P6 may then
run in that order or in parallel.

## Done report

Mechanism chosen: a flow attribute, reusing (and generalizing) the
existing terminal-edge machinery T-0282 already built for
`krb_no_transit`, rather than a new claim-level exclusion. That
machinery was already sound and already exercised in
`strata-core/src/lib.rs::reachable` (the 5th `transitive` edge flag) --
the gap was that it was wired to exactly ONE hardcoded attr string,
krb-specific in name even though the Rust kernel itself has no notion
of krb. Generalized it: added a bare `utility;` flow marker to the
surface grammar (desugars to flow attr `"utility"`, no new kernel
primitive, charter law 1) and widened `_facts.py`'s check from
`"krb_no_transit" not in f.attrs` to a shared
`_NON_TRANSITIVE_ATTRS = frozenset({"krb_no_transit", "utility"})`
set-intersection test. `krb_no_transit` keeps working unchanged (no
behavior change for any existing krb model).

Soundness: unchanged for every edge NOT explicitly marked `utility` --
the closure stays fully transitive by default (deny-by-default, charter
law 2). Only an edge the model author explicitly opts in on stops
chaining past itself; a real transitive flow through an unmarked hub is
still caught, proven by
`test_utility_attr_does_not_defeat_a_real_transitive_flow` and by the
`f_logs_server` edge in `utility_hub_hardened.strata` staying fully
transitive (only `f_tui_logs` is marked) while the same model's
`noflow tui -> server` claim still PROVES.

Changed:
- `strata-core/src/parse/mod.rs::Parser.parse_flow` -- new `utility;` bare
  flow property, desugars to attr `"utility"`.
- `strata-core/src/parse.rs` test module -- `parses_flow_utility` unit
  test.
- `editors/vscode-strata/syntaxes/strata.tmLanguage.json` -- added
  `utility` to the clause-keywords alternation (tmLanguage drift-lock,
  scope widened for this file, see above).
- `src/frob/strata/_facts.py::FactBase.reachable` -- generalized the
  non-transitive-edge check via new module constant
  `_NON_TRANSITIVE_ATTRS`; updated docstring.
- `docs/strata/kernel.md` (`#strata-core`) and `docs/strata/surface.md`
  -- documented the new `utility;` flow marker and its terminal-edge
  semantics.
- `tests/unit/strata/test_facts.py` -- two new `TestClosure` cases
  (terminal-hop behavior, no-weakening regression).
- New litmus pair `tests/unit/strata/litmus/utility_hub_vuln.strata` /
  `utility_hub_hardened.strata` reproducing the ticket's originating
  sibling-repo scenario (a shared logging hub defeating a `noflow`
  claim, then surviving it once the hub edge is marked `utility`), plus
  `tests/unit/strata/test_litmus_utility_hub.py` driving both end to end
  through the real `strata_core` parser.
- `tickets.md` -- this ticket's scope widened (see paragraph above) and
  this Done report.

Evidence (all collected and passing, verified via
`uv run pytest <files> -q` and `cargo test --lib parses_flow_utility`
after `make core`):
- `tests/unit/strata/test_facts.py::TestClosure::test_utility_attr_stops_chaining_past_that_hop`
- `tests/unit/strata/test_facts.py::TestClosure::test_utility_attr_does_not_defeat_a_real_transitive_flow`
- `tests/unit/strata/test_litmus_utility_hub.py::TestUtilityHubVulnLitmus::test_unmarked_hub_edge_refutes_the_noflow_claim`
- `tests/unit/strata/test_litmus_utility_hub.py::TestUtilityHubHardenedLitmus::test_marked_utility_hub_edge_lets_the_noflow_claim_prove`
- `strata-core/src/parse/mod.rs::tests::parses_flow_utility`

Filed: none -- no out-of-scope work discovered.

Gates: `uv run frob check --ticket T-0226` clean -- 0 errors, 10
warnings (all pre-existing/unrelated, e.g. TEST005 in
`src/frob/testing/_collect.py`, ARCH001 line-count notes elsewhere), 202
waived (pre-existing waivers, all with a `reason=`). No REL001 observed.
`make core` rebuilt both natives before every verification pass; `cargo
test --lib` (strata-core) 112/112 passed including the new
`parses_flow_utility`. Coverage stamped separately by the coordinator at
land time per updated instruction (not run again here after the initial
successful `make coverage` pass, source_sha=00bb7d00, 405 files
stamped).

Not closing this ticket per instruction -- leaving for the reviewer/
coordinator to close.

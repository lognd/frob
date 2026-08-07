## Done report

Changed:
- design/litmus/payments.strata (new)
- design/litmus/payments_hardened.strata (new)
- tests/unit/strata/test_litmus_surface.py (new)
- docs/strata/roadmap.md (litmus program section, phase-1 exit noted met)

design/litmus/payments.strata is the surface-syntax twin of
`_payments_model(hardened=False)` in test_litmus_payments.py: same node
ids/trust/clearance, same flow ids/labels/ages (5 min on f_repl, 30 s on
f_dash) and delivery=at_least_once attrs, same b_ingress endorse boundary,
same five claims including the assume (owner logan, review 2026-10-01).
design/litmus/payments_hardened.strata adds b_stripe_resp and b_webhook
endorse boundaries, idempotent attrs on api/webhookq, and reads the refund
decision directly off the ledger (f_refund_read: ledger -> refund),
matching `_payments_model(hardened=True)`.
tests/unit/strata/test_litmus_surface.py loads both files (repo root
resolved by walking up from __file__ to the first frob.toml), runs
parse_module -> elaborate -> evaluate_claims (today=2026-07-17), and
asserts byte-identical goldens to test_litmus_payments.py: golden 1
(stripe->ledger REFUTED with the 5-element counterexample), golden 2
(c_fresh_refund REFUTED, "330.0s > 60.0s", 7-element read path), golden 3
(build_facts f_wq_api at-least-once diagnostic), the browser-noflow PROVED
forall, the audit-reach PROVED exists witness, the assume ASSUMED with
"logan" in detail, and the hardened file's four PROVED asserts plus empty
diagnostics. One render_report smoke test confirms REFUTED sorts before
PROVED and the exact witness-path line
`  path: stripe -> f_stripe_resp -> api -> f_api_ledger -> ledger`
(format matched against src/frob/strata/_report.py's `"  path: " +
" -> ".join(counterexample)`).

The v0 surface grammar (strata-core/src/parse.rs) expressed every kernel
construct needed with no gap: `attr key=value` covers
`delivery=at_least_once`; `age N unit` covers `5 min` / `30 s`; `assume ID
noflow ... owner ID review "date"` covers the owner/review pair verbatim.
No parser-gap ticket was filed -- none was needed.

Evidence:
- tests/unit/strata/test_litmus_surface.py::TestNaiveSurfaceGoldens::test_golden_1_third_party_response_reaches_ledger_unendorsed
- tests/unit/strata/test_litmus_surface.py::TestNaiveSurfaceGoldens::test_golden_2_refund_decision_reads_a_stale_replica
- tests/unit/strata/test_litmus_surface.py::TestNaiveSurfaceGoldens::test_render_report_shows_refuted_before_proved_with_the_witness_path
- tests/unit/strata/test_litmus_surface.py::TestHardenedSurfaceGoldens::test_every_assert_holds_after_the_remedies

Filed: none.

Gates: `frob ticket sweep T-0063` recorded (dup=48, xref=7, all pre-existing
repo-wide noise unrelated to this diff); `frob check --ticket T-0063` exit
0; plain `frob check` exit 0; `uv run pytest tests/unit/strata -q` all 92
tests green; `uv run ruff format --check` and `uv run ruff check` clean on
tests/unit/strata/test_litmus_surface.py; `uv run ty check` clean.

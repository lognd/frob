## Done report

Changed:
- src/frob/strata/_threat.py::check_effect_completeness (new, THREAT004/THREAT005)
- src/frob/strata/_threat.py::_undeclared_sink_violation (new)
- src/frob/strata/_threat.py::_unclassified_sink_violation (new)
- src/frob/strata/_threat.py::_discharges_as_chokepoint (new)
- src/frob/strata/_threat.py::_check_one_discharge (tightened: chokepoint shape gate)
- src/frob/strata/_threat.py::check_discharge_completeness (threads nodes_by_id)
- src/frob/strata/_threat.py::evaluate_threats (optional binding/root -> THREAT004/005)
- src/frob/strata/__init__.py (export check_effect_completeness)
- docs/strata/threat.md (phase-C shipped note)
- tests/unit/strata/test_threat.py (13 new tests, listed in evidence)

Two independent pieces per threat.md phase C:

(a) Code-level capability classification (THREAT004/THREAT005).
`check_effect_completeness(model, binding, root, catalog, benign)` joins
`_effects.py::extract_effects`'s observed net/fs/exec sinks into the
SAME `_entries_by_capability_kind(catalog)` taxonomy join THREAT002 and
`_fired_obligations` already use -- no parallel taxonomy. THREAT004
reuses `check_capability_conformance`'s undeclared-capability join
directly (an observed sink whose owning node declares no matching `may`)
rather than re-detecting it. THREAT005 is the sink-classification half:
a declared-and-conformant effect whose `kind` maps to no catalog
`capability_kind`, unless a `BenignCapability` excuses it. `fs` effects
are deliberately left unclassified by THREAT005 -- CWE-22 (path
traversal) already has `capability_kind=None` in `CWE_CATALOG` (its
precondition is a flow pattern, not a capability kind), so there is no
sink-taxonomy entry for THREAT005 to join `fs` against; inventing one
would be a taxonomy decision this ticket does not own. `evaluate_threats`
gained optional `binding`/`root` params; THREAT004/005 run only when both
are given (a design-level-only caller has no code tree to bind, and an
absent join is never silently assumed clean -- charter law 2).

(b) Mitigation chokepoint verification (tightens THREAT003, no new rule).
`_discharges_as_chokepoint` requires a non-catalog-agnostic discharging
`Claim.body` to be `NoFlow(src=<a foreign-trust node, or the "foreign"
trust level>, dst=<firing node>)` -- exactly the shape `_eval_noflow`
(`_claims.py`) already proves over the closure engine's boundary-aware
`FactBase.reachable` (a flow carrying a `Boundary` stops the influence
walk). A claim at the right id/rung whose body is some other shape (e.g.
`Reach`, or a `NoFlow` naming the wrong `dst`) no longer discharges --
"declared somewhere" is insufficient, matching the charter's explicit
phase-C ask. This is a shape gate only: no new closure primitive, no new
call into `strata_core` -- REFUTED detection (a real unmitigated path
survives the boundary-aware closure) was already `_check_one_discharge`'s
job and is unchanged.

Verifiable-core cut: `_effects.py`'s sink vocabulary (`net`/`fs`/`exec`)
is coarser than the catalog's `capability_kind` vocabulary
(`fetch_url`/`sql`/`exec`/`deserialize`/`client_storage`/`html_render`).
`_EFFECT_KIND_TO_CAPABILITY` was considered but not added as a second
join table (would violate structurally-single-source: two tables mapping
overlapping capability spaces can desync). Instead THREAT004/005 join
`effect.kind` directly against `_entries_by_capability_kind(catalog)`,
which only has a `"exec"` entry today (`CWE-78`) -- `net` effects
therefore always report THREAT005 unless a model declares
`BenignCapability(kind="net", ...)` or the catalog gains a
`capability_kind="net"` entry (demonstrated in
`test_non_default_catalog_moves_the_sink_taxonomy_with_it`). This is the
same "destination-scoped capability grammar" gap `_effects.py`'s own
module docstring already defers (T-0079) -- noted here again as a phase-C
cut, not silently dropped: a finer `may net.out:<host>` grammar is a
surface-language follow-up, not a kernel change.

Evidence: 13 new pytest node ids (listed in the ticket's `evidence:`
field above), recorded via `frob ticket evidence T-0113 ...`; bound via
`frob:tests src/frob/strata/_threat.py::<symbol> kind="unit"` directives
in tests/unit/strata/test_threat.py.

Filed: none (no out-of-scope discoveries).

Gates (round 1, superseded by round 2 below): `uv run pytest
tests/unit/strata/` 336 passed; `uv run pytest tests/unit` 753 passed, 2
skipped. `frob ticket sweep T-0113` re-recorded. `uv run frob check
--ticket T-0113`: 88 gate violation(s) / 23 waived, identical to the
pre-change baseline (verified via `git stash` before/after).

## Round 2 (reviewer REJECT on the chokepoint crux)

Reviewer verdict: THREAT004/005 and taxonomy single-sourcing PASSED, but
the round-1 chokepoint shape gate (`_discharges_as_chokepoint`) accepted
ANY boundary as discharging proof -- `_eval_noflow`'s `reachable` stops
at every `Boundary` regardless of `direction`/`predicate`, so a
`declassify` boundary with predicate `"legal_review_signed_off"`
discharged a CWE-79 `output_encoding` obligation exactly like a genuine
`endorse output_encoding` boundary. The kernel already has the matching
vocabulary (`WeaknessEntry.mitigation`, `Boundary.direction`,
`Boundary.predicate`); round 1 never joined them.

Changed (round 2, in addition to round 1's changes above):
- src/frob/strata/_threat.py::_matching_boundary_ids (new)
- src/frob/strata/_threat.py::_restricted_to_boundaries (new)
- src/frob/strata/_threat.py::_claim_holds (new)
- src/frob/strata/_threat.py::_mitigation_is_chokepoint (new)
- src/frob/strata/_threat.py::_check_one_discharge (reordered: rung ->
  assumed -> REFUTED -> mitigation-kind, so the pre-existing REFUTED
  message still wins when a claim is genuinely unblocked, and an assumed
  claim bypasses the new check exactly like it bypasses REFUTED)
- src/frob/strata/__init__.py (Boundary/BoundaryDirection already
  exported; no new export needed for these, they are private)
- docs/strata/threat.md (phase-C shipped note rewritten: shape (1) +
  kind (2) layers, disclosed per-path-vs-per-model precision cut)
- tests/unit/strata/test_threat.py (5 new tests, `TestMitigationKind
  Chokepoint`, listed in evidence)

Design: `_mitigation_is_chokepoint(model, entry, claim)` isolates the
boundaries carrying the catalog's EXACT required mitigation
(`_matching_boundary_ids`: `direction=ENDORSE` and `predicate ==
entry.mitigation`) and re-evaluates the SAME `NoFlow` claim
(`_claim_holds`, wrapping `evaluate_claims`) on a model copy with every
OTHER boundary removed (`_restricted_to_boundaries`) -- the SAME
`_eval_noflow`/`reachable` call round 1 already leaned on, no new
closure primitive, no new `strata_core` call. A vacuous-path
short-circuit (evaluate first with ALL boundaries removed; if the claim
still holds, no path exists at all and no boundary of any kind is doing
any work) preserves round-1's fixtures that declare no flows/boundaries
at all and were correctly vacuously PROVED before phase C existed.

Quantifier implemented and disclosed in both the docstring and
threat.md: PER-MODEL, not per-path. `FactBase.reachable` reports
reachability, not which boundary blocked which path, so the check cannot
distinguish "every path carries a matching boundary" from "some paths
do, others are saved only by a non-matching boundary" at finer
granularity than one re-evaluation of the whole claim. This is sound in
the conservative direction: removing non-matching boundaries can only
ADD reachability, never remove it, so a PROVED result on the restricted
model really does mean the matching boundaries alone cut the closure;
a path saved only by a non-matching boundary reopens when that boundary
is stripped out, correctly REFUTING the restricted claim and failing
discharge (demonstrated by `test_mixed_paths_matching_on_one_wrong_kind
_on_other_does_not_discharge`). The disclosed gap is precision (no
per-path attribution), never soundness (no false accept is possible).

Ordering fix: the mitigation-kind check runs AFTER the rung/assumed/
REFUTED checks (round 1 had no such ordering concern since it was the
last check). This keeps the pre-existing violation messages
("required_rung ... below catalog rung", "is REFUTED: ...") intact for
the cases they already covered, and reserves the new "not of the
required mitigation kind" message for the specific gap the reviewer
found: a claim that WOULD have looked clean under every round-1 check
because some boundary (of the wrong kind) sat on every path.

Regression tests (`TestMitigationKindChokepoint`, 5 new):
(a) `test_declassify_boundary_does_not_discharge` -- wrong direction.
(b) `test_endorse_boundary_with_wrong_predicate_does_not_discharge` --
    right direction, wrong predicate.
(c) `test_endorse_boundary_with_matching_predicate_discharges` --
    correct kind, discharges cleanly.
(d) `test_mixed_paths_matching_on_one_wrong_kind_on_other_does_not_
    discharge` -- two Evil->Web flows, one boundary of each kind; the
    ORIGINAL (unrestricted) NoFlow proves (both flows carry SOME
    boundary), but the restricted-to-matching-only re-evaluation REFUTES
    (the wrong-kind flow reopens), so discharge correctly fails --
    exercises the documented per-model (not per-path) quantifier
    directly.
(e) `test_assumed_claim_bypasses_the_mitigation_kind_check` -- an
    assumed claim with owner+review still discharges without ever
    reaching `_mitigation_is_chokepoint` (never touches the closure).

Evidence: 5 new pytest node ids (18 total on the ticket now), recorded
via `frob ticket evidence T-0113 ...`; bound via `frob:tests
src/frob/strata/_threat.py::check_discharge_completeness kind="unit"`
directives (the new tests exercise the public entrypoint, matching the
existing `TestDischargeChokepointShape`/`TestDischargeCompleteness`
convention in this file rather than binding to the new private helpers
directly).

Filed: none (no out-of-scope discoveries).

Gates (round 2, current, NO stash used per reviewer instruction): `uv
run ruff check` / `uv run ruff format --check` -- both clean on the
touched files. `uv run ty check` -- clean. `uv run pytest
tests/unit/strata/` -- 341 passed (5 more than round 1's 336). `uv run
pytest` (full suite) -- 1620 passed, 3 skipped. `frob ticket sweep
T-0113` re-recorded (round-1's sweep had gone stale against round 2's
edits). `uv run frob check --ticket T-0113`: 88 violation(s) / 23
waived -- identical to round 1's post-sweep number, confirming round 2's
new code introduces no new unwaived gate diagnostic (checked by grepping
the unwaived-violation listing for any `_threat.py` or `test_threat.py`
line: none appear outside the pre-existing `frob:waive` directives
already present before round 2). No `frob/gates` or `frob/vet` files
touched.

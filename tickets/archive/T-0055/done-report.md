## Done report

Delivered src/frob/strata/: _errors.py (StrataError closed ErrorSet),
_models.py (Lattice + TRUST/LABELS cores, Quantity with unit dimensions,
Capacity, Node, Flow + FlowCondition/Outcome conditional-flow extension,
Boundary + BoundaryDirection, Metric, claim bodies NoFlow/Reach/BoundClaim,
Rung, Claim with assume owner/review, Scenario + RemoveNode/ScaleRate/
SetTrust rewrites, KernelModel, ClaimResult/Verdict/Quantifier),
__init__.py public API. All frozen pydantic, identity-of-value. 11 unit
tests bound via frob:tests; frob:doc edges to docs/strata/kernel.md#data-models
for every public symbol incl. methods (T-0044 workaround used). Ticket
check exit 0. Deviations: TRUST/LABELS constants are invisible to the
graph (python CONST extraction gap) -- filed T-0087 rather than widening
scope; their describes anchors deferred to that ticket.

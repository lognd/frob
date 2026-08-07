## Done report

Reconciled docs/design/registry/compliance.yaml (27 catalogued entries)
against actual enforcement. Unlike T-0385/T-0386/T-0387, these entries
were NOT already honestly dispositioned: 17 of 27 carried
disposition: "deferred:T-0388" -- T-0388 is this very ticket, a
review-gated reconciliation ticket expected to close, so deferring to
it would break REG003 (deferred-to-closed-ticket) the moment it closes.

Fixed honestly rather than pinned around: filed T-0607
("implement checkable-control enforcement for CMPL-* compliance
registry units") as the real standing home for the future
compliance-checkable-control implementation work, and re-pointed all 17
deferred entries (SOC2 categories/CC-families, PCI-DSS requirements,
HIPAA technical standards, GDPR articles, NIST 800-53 families, NIST
800-63 volumes, SSDF practice groups, ISO 27002 themes/controls, CIS
controls/safeguards, ASVS chapters/requirements, FedRAMP impact tiers,
SLSA build levels, frob-std catalog entries) to it. The remaining 10
entries stay out_of_scope, each tagged organizational/process or
organizational/advisory per the source corpus's own checkability field
(HIPAA admin/physical standards, GDPR chapters, CCPA core rights, CPRA
added rights, NIST CSF functions, CIS implementation groups, ASVS
levels, SAMM functions/practices) -- src/frob/strata/_compliance.py
enforces COPPA/erasure/retention/lawful-basis/BAA/minimization at the
strata-model level, which is a different (model-level, not
registry-id-level) enforcement surface than what these 27 entries
name, so none of them are handled_by an existing check today. Zero
undispositioned (REG001), zero dangling handled_by/deferred/
duplicate_of targets after the re-pointing, zero malformed entries.
`uv run frob check --only registry` and `uv run frob check --ticket
T-0388` both report 0 registry errors for this file.

What this ticket added: the file-specific EXHAUSTIVENESS meta-test the
acceptance criterion calls for, over REAL data -- same posture as the
sibling reconciliation pin tests (T-0385/T-0386/T-0387), plus one extra
test this file's own hazard earned:
test_no_entry_defers_to_this_reconciliation_ticket, which locks that no
entry names T-0388 as a deferral target (so a future edit cannot
silently reintroduce the self-referential-deferral bug this ticket
fixed). New file tests/test_registry_reconciliation_compliance.py pins:
the file loads under the unified model with zero malformed entries; the
declared total (27) matches audit_registry_file's total; audit.exhausted
is True with 0 unaccounted; handled+deferred+duplicate+out_of_scope ==
27; every deferred: entry names a real, open ticket (T-0607,
which exists and is not done); no entry defers to T-0388 itself; and
registry_gate over the real registry dir raises zero violations scoped
to compliance.yaml. Wired into the default `frob check` run (gate:registry
runs unconditionally), so a future silent gap in this file fails the
build via both the gate and this test.

Filed: T-0607 (feature ticket for the deferred CMPL-* registry-id-level
enforcement work). This ticket originally minted a provisional
T-0607 (ex-draft, id lost at land) for the same purpose; the coordinator filed the real
T-0607 on main (draft ids do not survive `frob ticket land`, T-0577),
so all 17 deferred entries, the pin test, and this Done report were
re-pointed to T-0607 and the draft's ledger block dropped.

No code changes to src/frob/strata/_compliance.py were needed for this
reconciliation itself -- the unified registry model and gate
(src/frob/gates/_registry_exhaustiveness.py, src/frob/registry/) already
generically enforce this file once honestly dispositioned; the actual
CMPL-*-level checks remain future work tracked by T-0607.

### Changed
```
 tickets.md | 590 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 587 insertions(+), 3 deletions(-)
```

### Evidence
(no evidence recorded)

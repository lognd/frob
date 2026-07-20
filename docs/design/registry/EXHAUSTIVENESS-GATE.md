# Registry exhaustiveness drift-lock (T-0343)

The unified design-knowledge registry (`docs/design/registry/*.yaml`,
README.md's "Unified design-knowledge registry") was built and documented
as a machine-readable, enforced catalog, but was in fact read by ZERO
code -- catalogued, not enforced, with no gate watching the gap. This is
the fix: `frob.gates._registry_exhaustiveness.registry_gate`, wired into
`frob check` at ERROR severity as the `registry` gate, family `REG001`-
`REG005`.

## Disposition grammar

Every entry's `disposition:` string is parsed and VERIFIED, never taken
at face value:

- `handled_by:<rule-id>` -- `<rule-id>` must name a rule this build's own
  gate/policy rule registry actually knows about (checked against the
  live `frob.gates._KNOWN_GATE_RULES | policy rule ids` union at call
  time, never a hardcoded snapshot). A dangling reference is `REG002`.
- `deferred:<ticket-id>` -- `<ticket-id>` must resolve to a ticket that
  is not `done`/`dropped`. A deferral to a closed or nonexistent ticket
  is `REG003`.
- `duplicate_of:<id>` / `duplicate-of:<id>` -- `<id>` must resolve to a
  real entry id somewhere in the registry. A dangling duplicate
  reference is `REG004`.
- `out_of_scope:<reason>` / `out-of-scope:<reason>` /
  `out-of-scope(<reason>)` -- valid if `<reason>` is non-empty. Routing
  through Area-2's verified `caught_by` mechanism (T-0382) is a named,
  tracked gap: that mechanism does not exist yet in this build, so
  `caught_by` is accepted as a free-form string for now, not verified.
- anything else -- missing, `pending`, or a bare `addressed` with no
  `handled_by` attached -- is `REG001`, undispositioned. A bare
  `addressed` claim with nothing backing it is deliberately treated as
  undispositioned, not accepted at face value.

## REG004 (also): documented splits

`RECONCILIATION.md` finding (b) names real-world concepts split across
multiple, currently-unlinked registry ids. Any backtick-quoted registry
id that table names is required to carry a non-empty `cross_refs` list;
an id still showing `cross_refs: []` despite being a documented split
fails `REG004`.

## REG005: declared-total drift

A registry file may declare a `total:` (or, for a split entry-list key
like `weaknesses.yaml`'s `cwe_entries`, a `<prefix>_total:`) alongside its
`entries:` list. If declared, it must equal the actual entry count -- a
silent future add/drop without updating the denominator fails `REG005`.
Files/lists with no declared total are not checked.

## Honest first-turn-on state

On first turn-on this gate is RED for the ~1950 entries the registry
carries today (the great majority `pending`, `addressed` with nothing
backing it, or a legacy CWE `duplicate-of`/`out-of-scope` disposition
that predates and does not yet match this grammar). That red is the
honest current state of the corpus, not a bug in the gate -- it is
driven green only by the per-registry reconciliation tickets
(T-0384..T-0392 doing the real per-entry disposition work), never by
suppressing or bulk-waiving this gate.

# Dataset construct (T-3964)

Standalone doc row for T-3964's accepted design. Filed as a standalone
file rather than folded into `docs/modules/gates.md` because that file
was leased by another in-progress ticket (T-4111) at implementation
time -- fold this section in there once that lease clears, and the
`_KNOWN_GATE_RULES`/dispatch wiring gap below has been appended to
T-4605's body (the same live fold-in ticket T-3961's implementation
used) for the same reason.

## Background (F-177, T-3942 item 3 / T-3919 item 5)

`carries()` (`frob.strata._pii`) attaches PII atoms to a WHOLE `Node` --
today `store` desugars to an ordinary `Node` at elaborate time (no
separate kernel `Store` class exists), so a password hash into an audit
log and an email into a Redis key have historically been invisible: both
stay inside a node already cleared for the atom generally.

INVESTIGATED FIRST (before implementing): grepping `_models.py` confirms
there is no separate kernel `Store` class -- `store` is purely a
surface-syntax word. `_pii.py`'s `node_pii_tags` already reads
`carries()` PER-NODE, not globally. This means a fine-grained data
region declared as its OWN `Node` already gets independent `carries()`
for free, with zero new code -- proven by
`tests/test_dataset_construct.py::TestDatasetIndependentCarries`. The
actual gap this ticket closes is narrower than the original framing:
not "carries() can't be scoped independently" (it already can be) but a
STRUCTURAL LINK from a fine-grained dataset back to the coarser store
that contains it, plus an `append_only` declaration a gate can observe.

## parent_store

An attr on a node naming the store `Node` it is a fine-grained
sub-region of. Zero `strata-core` grammar change -- no new `dataset`
keyword; an ordinary `node` declaration IS a dataset the moment it
carries this attr, the same attr-desugar convention `pii=`/`code=`/
T-3961's `derived_from:`/`trust_identity:` already use.

```
node postgres {
    trust = trusted
}

node audit_log {
    trust = trusted
    attr "parent_store=postgres"
    attr "pii=behavioral.access_log"
    attr "append_only"
}
```

Parsing: `frob.strata._dataset.node_parent_store`,
`frob.strata._dataset.node_is_dataset`.

## append_only

A bare flag (mirrors T-3961's `trust_identity`/T-4073's `no_pii`
bare-attr convention) declaring a dataset/node append-only. Parsing:
`frob.strata._dataset.node_is_append_only`.

**Cheap first step, deliberately (disclosed, not silently dropped)**:
this ticket's own acceptance text only asks for "an append_only
attribute that a gate can check" -- the attr-parsing helper above IS
that "can check" capability. A deeper semantic check (e.g. cross-
referencing a node's `may` capability grants for a delete/overwrite-
shaped atom against a declared `append_only` flag) would need an
established "delete"/"overwrite" capability-atom taxonomy that does not
exist in this codebase today; real future work, not required for this
ticket's first landing.

## SYS118 dangling parent_store reference

`frob.strata._dataset.check_dangling_parent_store`: a `parent_store=<id>`
attr naming a node id that does not exist anywhere in the model -- a
typo'd or stale reference, deny-by-default the same structural-reference
shape SYS101/SYS113 take.

Rule id choice: SYS114/SYS115 (T-4113) and SYS116/SYS117 (T-4612, T-3961's
implementation) were both held-for-landing but not yet on `dev` at this
ticket's implementation time -- SYS118 is the next id past every
currently in-flight claim, verified via `git grep` across both those
worktrees plus `dev`'s own `docs/modules/gates.md`.

**Not yet wired** (disclosed, not silently dropped) into any
`frob.gates` dispatch or `_KNOWN_GATE_RULES` -- this module is kept
gate-agnostic on purpose (returns plain finding strings, not a
`Violation`/`PiiViolation` model), mirroring T-3961's own
`_sys_provenance.py` posture; wiring SYS118 into a live gate is a
follow-up appended to T-4605's body alongside T-3961's own SYS116/SYS117
wiring gap.

## Open questions (not resolved here)

- Whether `append_only` should eventually cross-reference `may`
  capability grants once a delete/overwrite atom taxonomy exists.
- Whether a dataset needs its own `trust`/`clearance` distinct from its
  parent store's, or always inherits the parent's -- left unconstrained
  for now (a dataset `Node` can declare its own `trust` today, same as
  any node; no explicit inheritance rule is enforced).

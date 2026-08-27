<!-- frob:ticket T-3026 -->
<!-- frob:waive REF002 reason="linked from docs/index.md's strata design-doc list (the canonical entry point for every docs/strata/*.md page) plus mentioned by name in docs/strata/surface.md's construct-semantics section; REF002's own path/basename scan does not appear to count a same-subtree (docs/strata/) cross-link as a second independent anchor, but this is a normal, recently-added (T-3006) design doc in an established series (charter.md/kernel.md/surface.md/etc, all reached the identical single-inbound-link-from-index.md way) -- not an orphan." -->
# Entity / architecture / configuration (T-3006, T-3004 section 5)

Strata's `.strata` surface, before this ticket, was ONLY an implementation
language: `node`/`flow`/`store`/`module` describe how a system is built,
never what it is obligated to do independent of that build. T-3004 section
5 named this the core half-baked gap and chose VHDL's entity/architecture/
configuration split as the fix, deliberately as a redesign of the concept
rather than a bolt-on.

## The three constructs

```
entity storage_component {
    may "net.out:s3.amazonaws.com";           // ceiling: the MOST this
                                                // entity's obligations may
                                                // ever require
    obligation "persist a submitted blob durably before acking the caller";
    obligation "reject a write once past-quota rather than silently drop it";
}

module storage_fast

node writer : trusted {
    may "net.out:s3.amazonaws.com" via "src/pkg/fast_writer.py";
}

architecture fast of storage_component {
    binds storage_fast;
}
```

- **`entity`** is the BEHAVIOUR half: obligations (free-text, declarative
  requirements -- not machine-checkable content, T-3004 section 2's
  "structural closure, not quality") plus a `may` capability ceiling. No
  implementation. An entity with zero `obligation` statements is refused
  at parse time -- an empty block is not a behaviour contract.
- **`architecture ... of ENTITY { binds MODULE; }`** is the IMPLEMENTATION
  half -- today's whole `.strata` surface (`node`/`flow`/`store`/...),
  unchanged, now labeled as ONE way of realizing a named entity's
  obligations. `binds` names the module the architecture realizes.
- **`configuration NAME { entity E; architecture A; }`** selects which
  architecture currently satisfies which entity. The plain selection edge
  T-3004 section 6's milestone/partial-closure model will build on later;
  this ticket does not build milestones or `KNOWN_GAP` semantics, only the
  selection construct they need to exist first.

**One entity, many architectures** is the property that matters: two (or
more) architecture blocks -- in the same file or, as the worked example
below shows, different files -- can each bind a different module and both
satisfy the same entity. That is what lets an incremental release (T-3010)
pick a cheaper architecture for one milestone and a fuller one for the
next without inventing separate machinery -- see
`tests/unit/strata/entity_arch/storage_fast.strata` and
`storage_cheap.strata`.

## Scope of this first slice (deliberately narrow)

- **Single-file resolution.** `of ENTITY` and `binds MODULE` resolve only
  against entities/the module already parsed earlier in the SAME file.
  Cross-file entity references (an architecture in one file satisfying an
  entity declared in another) are not yet supported -- each file that
  wants to offer an architecture for a shared entity currently repeats
  that entity's declaration verbatim (see the worked example: both
  `storage_fast.strata` and `storage_cheap.strata` declare
  `storage_component` identically). A follow-up ticket is needed before
  that duplication is worth removing structurally (a cross-file entity
  registry needs a home in the loader, which this ticket does not touch).
- **Parse-time enforcement, not a new `frob check` gate row.** SYS300-303
  below are structural refusals returned by `strata_core.parse_source`
  itself (the same `err{line,col,message}` shape every existing parse
  error uses), not new entries in `src/frob/gates/_sys.py` or
  `src/frob/gates/__init__.py`. This was a deliberate scope decision: both
  files were owned by a concurrently-live agent (the gates dict + docs
  narrative work) during this ticket, and parse-time refusal is at least
  as strict as a post-hoc gate finding -- a malformed entity/architecture
  pairing cannot exist in a parsed AST at all, the same "type-checked, not
  discovered later" posture T-3004 section 4 asks for. Promoting these to
  first-class `SYS3xx` gate rows (for a `frob check --only sys` summary
  line, waiver support via `frob:waive`, etc.) is real follow-up work, not
  done here.
- **No cross-cutting obligation verification.** An `obligation` string is
  today pure declared intent with no verifier attached -- T-3004 section 1
  ("requirement <-> customer test" pairing) and section 7 (TDD ordering)
  are the follow-on work that gives obligations a verification edge. This
  ticket only makes the BEHAVIOUR half exist as a real, parseable,
  type-checked construct; it does not yet check that an obligation is
  fulfilled.

## What SYS300-303 catch (both fixture directions live in
`strata-core/src/parse/mod.rs`, `#[cfg(test)] mod tests`)

| Rule | Fires on (must-fire fixture) | Stays quiet on (must-stay-quiet fixture) |
| --- | --- | --- |
| SYS300 | `architecture a of ghost_entity` where `ghost_entity` is never declared | `architecture a of real_entity` where `real_entity` was declared earlier |
| SYS301 | `architecture a of e { binds some_other_module; }` where `some_other_module` != this file's own `module` name | `binds` names this file's own module |
| SYS302 | a node inside the bound module grants a `may` atom the entity's ceiling never declared | the bound module's grants are a subset of (or equal to) the entity's ceiling |
| SYS303 | `configuration c { entity e2; architecture a; }` where `a` is declared `of e1`, not `e2` | `entity`/`architecture` in the configuration actually match |

Each row above is one must-fire test paired with one must-stay-quiet test
with the same shape, per this repo's standing doctrine that a clean
verdict with no must-fail case proves nothing.

## SYS302 IS the shrink-only ratchet, carried forward on purpose

T-2920/T-2923 established that a node's `may=` ceiling only ever SHRINKS
under automation; T-2922 deleted a live auto-widening Tier-A fixer for
exactly that reason. SYS302 is the same rule at the new layer: an
architecture's realized capabilities (the union of its bound module's
node-level `may` grants) must be a SUBSET of its entity's declared
ceiling, checked at parse time, and there is no code anywhere in this
change that synchronizes the ceiling UP to match an architecture that
exceeds it. Widening the ceiling is, and stays, a hand-edit to the
`entity` block, reviewed like any other behaviour-contract change.

## SYS200-205 (resource conflicts) are untouched

This ticket adds new top-level statement kinds; it does not touch
`grammar_node.rs`'s `access`/`resource` productions or the Python
contention checks in `src/frob/strata/_contention.py` that implement
SYS200-205. Every existing node/flow/store/resource construct parses
exactly as it did before this ticket -- the new grammar is strictly
additive at the top level (see "Migration" below).

## Migration: the 8 existing `.strata` files, including `design/frob.strata`

**No existing `.strata` file needs to change.** `entity`/`architecture`/
`configuration` are new OPTIONAL top-level statement kinds; a file with
none of them (every current file, including the self-model
`design/frob.strata`) parses to exactly the same AST as before this
ticket, with the three new fields (`entities`, `architectures`,
`configurations`) simply empty
(`existing_bare_module_files_parse_unchanged_no_entity_required`, a
dedicated regression test for this guarantee). This is the additive
compatibility path T-3004 section 5's migration concern asked for
explicitly, not silent invalidation of the self-model.

Migrating `design/frob.strata` itself to actually DECLARE an entity for
frob's own architecture-level obligations was the owner's suggested
worked example (T-3004 section 5) but is deliberately NOT done in this
ticket: `design/frob.strata` is the live self-model five other files and
every `frob check --only sys` run depend on, editing it here would risk
the exact repo-wide `SYS100-112` blast radius the epic explicitly warns
about (a foreign-repo run fired `SYS103` x140 from the existing
bookkeeping-shaped family), and a second concurrent agent's work this
session already touches shared gates/docs surfaces. The worked example
instead lives in `tests/unit/strata/entity_arch/` (a fixture directory
already git-scanned by pytest but NOT by `frob check`'s live
`design/**/*.strata` discovery, so it cannot pollute the repo's own gate
floor with a demonstration file's deliberately-nonexistent `code=` glob).
Migrating the self-model is real follow-up work, filed separately.

## SYS100-112's bookkeeping shape

T-3004 section 5 flags `SYS100-112` (declared-vs-observed self-conformance)
as bookkeeping-shaped and already being narrowed to a shrink-only ratchet
under T-2920. This ticket does not touch `src/frob/strata/_selfconform*.py`
at all -- narrowing that family's noise is T-2920's job, not this one's.
What this ticket DOES do toward the "declaration should carry intent, not
duplicated facts" goal is add a construct (`obligation`) whose entire
content IS intent, structurally incapable of being a duplicated observed
fact the way a `SYS103`-style declared-vs-observed check can drift out of
sync -- there is nothing to observe an obligation string against, by
design, until a verification edge (T-3004 sections 1/7, deferred) gives it
one.

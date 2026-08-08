# strata policy -- the five universal forms and policy packs

<!-- frob:ticket T-0048 -->

One sentence: an L4 policy is a universally quantified syntactic rule --
checked over every file in a semantically resolved scope -- and the five
forms below are the complete vocabulary in which such rules may be written
(T-0067).

## The five forms

<!-- frob:describes src/frob/strata/_ast.py::ForbidCall -->
<!-- frob:describes src/frob/strata/_ast.py::ForbidImport -->
<!-- frob:describes src/frob/strata/_ast.py::ConfineUse -->
<!-- frob:describes src/frob/strata/_ast.py::AtCallRequire -->
<!-- frob:describes src/frob/strata/_ast.py::Mediate -->

| Form | Shape | Example |
|---|---|---|
| **Prohibition** | no occurrence of pattern P in scope S | `forbid call eval, exec` |
| **Confinement** | occurrences of P only inside home H | `confine use psycopg to src/api/db.py` |
| **Obligation-at-site** | every P must carry Q | `at call subprocess.run require arg timeout` |
| **Chokepoint** | all uses of capability C mediated by F, F itself proved | `mediate db.write via db.py::TenantScopedSession require proof >= L3` |
| **Structural** | every symbol matching P has property Q | `every public function in Api returns Result` |

Prohibition, confinement, and obligation-at-site match token/AST patterns
(decidable by tree-sitter query closure). Chokepoint is confinement plus a
mediator proof obligation -- the semantic-to-syntactic reduction from
`evidence.md` as a single construct ("complete mediation" made
declarable). Structural rules quantify over frob graph symbols rather
than raw tokens.

## Semantic scoping

<!-- frob:describes src/frob/strata/_ast.py::ScopeSpec -->
<!-- frob:describes src/frob/strata/_ast.py::PolicyDecl -->

Policies attach to model entities, not paths:

```
policy DbChokepoint on component Api { ... }
policy NoDynamicCode on trust >= trusted { ... }
policy NoPiiInLogs   on label >= Pii { ... }
```

The elaborator resolves scope to files via the components' `code` globs.
Consequences: reorganizing directories never silently un-scopes a rule,
and a new `trusted` component inherits every trusted-scoped policy the
moment it is declared.

<!-- frob:invariant INV-030 -->

Under refinement, policies inherit downward monotonically -- a child may
only strengthen an inherited policy, never weaken it (a weakening is a
refinement error).

### Refinement monotonicity (INV-051, T-1482)

<!-- frob:invariant INV-051 -->
<!-- frob:describes src/frob/strata/_policy.py::PolicyWeakening -->
<!-- frob:describes src/frob/strata/_policy.py::find_policy_weakenings -->
<!-- frob:describes src/frob/gates/_policy_weakening_gate.py::policy_weakening_gate -->

`find_policy_weakenings` is the enforcing code: for every pair of
`CompiledPolicy` whose `node_ids` sets are related by strict containment
(a `component` policy's single node nested inside a broader `trust`/
`label` policy, or one `trust`/`label` threshold nested inside a laxer
one), it diffs every rule the NARROWER (child) policy re-declares for a
target atom the containing (parent) policy already constrains, and flags
any re-declaration that is strictly less restrictive:

- `forbid call`/`forbid import` are deliberately NOT diffed: they are
  purely additive prohibitions under union enforcement (below), so a
  child re-declaring the form with a different ident set can never make
  the parent's own prohibitions stop applying -- there is no way for
  this form to be weakened by a child re-declaration.
- `confine use` -- the child's `home` for a shared `ident` must equal or
  narrow (sub-path of) the parent's `home`.
- `at call ... require arg` -- if the child re-engages an `ident` the
  parent already constrains, it must keep every `arg` the parent required.
- `mediate` -- there is no proof-strength ordering between two distinct
  mediators at TIER-1, so ANY mediator swap for an already-mediated
  `ident` is flagged, fail-closed rather than silently assumed
  equivalent.

(T-1844 perf fix: the pairwise scan now generates distinct (parent,
child) pairs via `itertools.permutations` instead of a nested loop with
an inner `==` self-exclusion check, and `_at_call_require_weakenings`
sorts the flattened dropped-arg set once instead of once per `ident` --
same findings, same order, cheaper.)

Deliberately silent when the child never re-declares a given target at
all -- TIER-2 conformance enforcement applies the UNION of every policy
whose scope covers a node (docs/strata/policy.md#compilation), so an
untouched target is inheritance, not weakening. This pass is TIER-1 only
(a pure diff over already-compiled `CompiledPolicies`).

**T-1843: wired into a real `frob check` gate.**
`frob.gates._policy_weakening_gate.policy_weakening_gate` (rule
`INV051`) loads+elaborates every `.strata` file under `design/` (or
`[strata].design_dir`) the same way `frob.gates.sys_gate` does, compiles
the merged `PolicyDecl`s it finds against the merged `KernelModel`
(`compile_policies`), and runs `find_policy_weakenings` over the result --
opt-in behind a `design/` directory existing, silent on any design load
failure (SYS004 reports that separately) or when no policies are
declared. `forbid_call`/`forbid_import` stay excluded per the bullet
above; the gate surfaces whatever `find_policy_weakenings` itself
returns and adds no filtering of its own.

## Compilation

<!-- frob:describes src/frob/strata/_policy.py::compile_policies -->
<!-- frob:describes src/frob/strata/_policy.py::CompiledPolicy -->
<!-- frob:describes src/frob/strata/_policy.py::CompiledPolicies -->
<!-- frob:describes src/frob/strata/_policy.py::CompiledPolicies.enabling -->
<!-- frob:describes src/frob/strata/_design_load.py::DesignIds -->

T-1843: `DesignIds.policies` (`frob.strata._design_load`) carries every
loaded `.strata` file's parsed `Module.policies`, merged pre-elaboration
across files -- the same "not a `KernelModel`-level fact, only the parsed
`Module` has it" limitation `DesignIds.resources`/`store_ids` already
document. A caller that needs `compile_policies(module, model)` builds a
throwaway `Module(name=..., policies=design_ids.policies)` against
`design_ids.models[0]`, exactly as `frob.gates._policy_weakening_gate`
does.

Surface patterns (`call`, `import`, `attribute`, `decorator`, `arg`,
`string`) compile to per-language tree-sitter queries across all
`frob.lang` grammars; exotic cases drop to a raw per-language tree-sitter
query as the escape hatch. Mechanically this extends the existing
`frob.toml` `[policy]` machinery (POL gates) with semantic scope
resolution and `enables` bookkeeping rather than replacing it.

## Packs

<!-- frob:describes src/frob/strata/_packs.py::require_analyzable -->

Named, versioned bundles of policies:

| Pack | Contents | Status |
|---|---|---|
| `std.policy.analyzable` | no eval/exec/dynamic import/reflection dispatch; FFI only via `frob bind`; anti-aliasing rules (no `f = eval`); monkey-patching bans | **mandatory** for any `trusted` component; root of the enables cascade (T-0068) |
| `std.policy.errors-total` | per-language: exhaustive ErrorSet match, no discarded Result, no bare raise/except outside the error module, no unwrap/expect/panic outside tests, no floating promises, noexcept on public C++ surface, checked returns in C | required by `errors total` claims (T-0070) |
| `std.policy.observe` | every error-consumption arm logs or propagates; emits carry trace_id; boundary crossings and declared state transitions have emit sites | enables detection SLAs (T-0070) |
| `std.policy.crypto` | confine crypto primitives to one vetted module; forbid homemade constructions | phase 2+ |
| `std.policy.pii` | Pii newtype discipline (L5) + no Pii type at log/serialize sites (L4) | phase 2+ |

The base pack is self-defending: it contains the anti-aliasing rules that
keep its own prohibitions sound.

## v0 implementation

What compiles now (T-0067/T-0068): the surface grammar for all five
`policy_rule` forms and `SCOPESPEC` (`strata-core/src/parse/mod.rs`), typed
AST models with `enables`/`rationale` split out as policy-level metadata
(`_ast.py::PolicyDecl`), and `compile_policies` (`_policy.py`) -- semantic
scope resolution against the elaborated `KernelModel` (component name,
or a trust/label lattice floor via `Lattice.leq`), producing a frozen
`CompiledPolicies` handoff artifact per policy: resolved node ids, the
typed rule set, and `enables` atoms.

What does not compile yet: TIER-2 execution -- turning `rules` into actual
per-language tree-sitter queries run over real source files -- is phase 4
(T-0079/T-0080). `CompiledPolicies` is exactly the artifact that phase-4
file scanning will consume; nothing here reads a file off disk.

**Auto-inject amendment.** `docs/strata/policy.md#packs` above states
`std.policy.analyzable` is mandatory for any `trusted` component. v0
enforces that by auto-injecting the pack (`_packs.py::require_analyzable`)
into a module that declares a trusted component without it, rather than
failing the module -- logged at WARNING since it silently changes what is
checked. Rationale: the pack is mandatory regardless of whether it is
spelled out, so refusing to proceed without an explicit declaration would
only add friction, not safety; declaring the policy id yourself is instead
how you override individual pack members (the auto-inject step is a no-op
once the id is already present).

## Honesty

L4 soundness is conditional on the analyzable subset -- that is exactly
what `enables extraction_soundness` records, and why waiving any base-pack
rule downgrades dependent claims to ASSUMED automatically rather than
leaving a silent hole (`evidence.md`).

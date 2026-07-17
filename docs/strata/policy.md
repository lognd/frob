# strata policy -- the five universal forms and policy packs

<!-- frob:ticket T-0048 -->

One sentence: an L4 policy is a universally quantified syntactic rule --
checked over every file in a semantically resolved scope -- and the five
forms below are the complete vocabulary in which such rules may be written
(T-0067).

## The five forms

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

Policies attach to model entities, not paths:

```
policy DbChokepoint on component Api { ... }
policy NoDynamicCode on trust >= trusted { ... }
policy NoPiiInLogs   on label >= Pii { ... }
```

The elaborator resolves scope to files via the components' `code` globs.
Consequences: reorganizing directories never silently un-scopes a rule,
and a new `trusted` component inherits every trusted-scoped policy the
moment it is declared. Under refinement, policies inherit downward
monotonically -- a child may strengthen an inherited policy, never weaken
it (a weakening is a refinement error).

## Compilation

Surface patterns (`call`, `import`, `attribute`, `decorator`, `arg`,
`string`) compile to per-language tree-sitter queries across all
`frob.lang` grammars; exotic cases drop to a raw per-language tree-sitter
query as the escape hatch. Mechanically this extends the existing
`frob.toml` `[policy]` machinery (POL gates) with semantic scope
resolution and `enables` bookkeeping rather than replacing it.

## Packs

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

## Honesty

L4 soundness is conditional on the analyzable subset -- that is exactly
what `enables extraction_soundness` records, and why waiving any base-pack
rule downgrades dependent claims to ASSUMED automatically rather than
leaving a silent hole (`evidence.md`).

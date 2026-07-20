# Adversarial hardening of the structural linters (arch + strata)

Status: design north-star for the arch epic (T-0330), the strata-systems
epic (T-0331), and the conformance-totality epic (filed alongside this doc).

## The one principle

Every structural check reasons over a REPRESENTATION of the code. Evasion is
always the same move: **widen the gap between the representation the checker
sees and the ground truth the code actually is, then hide the violation in
that gap.** The capability scanner was evadable because its representation
was raw text (`grep`); aliasing (`xyz = run`) lived in the gap between text
and resolved bindings. We closed it by moving the representation to the
resolved symbol/binding graph (T-0328/T-0337) and, for the residue no static
pass can resolve, failing closed (T-0339).

The same move hardens EVERY structural check. Four rules make a check
nearly un-evadable:

1. **Ground-truth grounding.** Reason over the resolved semantic structure
   (binding-resolved symbol graph, call graph, extracted effects), never a
   surface proxy. No text matching, no syntactic-unit counting where a
   logical-unit is what matters.
2. **Model<->code conformance.** Where a declaration exists (a `.strata`
   node, a declared interface, a layering contract), the declaration is
   CROSS-CHECKED against the extracted ground truth. A declaration may never
   claim a property the code does not have, nor omit a property the code
   does have.
3. **Fail closed on the unprovable.** Any construct the analysis cannot see
   through (dynamic dispatch, reflection, opaque store round-trips,
   unresolvable flow) becomes a first-class obligation that FIRES and must
   be discharged by a reasoned waiver -- never a silent pass. (T-0339
   generalized from capabilities to flows, effects, and structure.)
4. **Bounded, quality-gated escape hatches.** Waivers/assumes/exemptions are
   counted, reason-required, staleness-dated, budget-limited, and their
   reasons are quality-checked. "Waive everything" is itself a detectable
   smell, not an escape.

Plus a fifth, meta rule that guards the guards:

5. **Config is gated.** Thresholds, baseline views, and exemption markers
   cannot be silently loosened; loosening is an audited event. You cannot
   evade by turning the check down.

## Adversarial catalog: how you'd evade today, and the defense

### Code architecture (frob arch, ARCH1xx)

| Evasion | Defense (which rule) |
|---|---|
| God-class split across a `_impl` sidecar / mixins / partial files so each syntactic class is small | Measure the LOGICAL unit: cluster by call-graph cohesion + co-change; a helper module only-ever-called-by-one-class IS that class (rule 1, reuse T-0288 call graph) |
| Long function shattered into N one-line single-caller private helpers | Inline private single-caller helpers before measuring complexity (rule 1; the T-0288/T-0289 tension, shared call-graph substrate) |
| Layering violation via re-export through a neutral module, or via DI passing the forbidden concrete in at runtime, or via dynamic/string import | Resolve re-exports transitively (rule 1, like T-0328); DI of a concrete is itself the DIP smell (construct-vs-inject); dynamic import fails closed (rule 3) |
| Fake abstraction: interface with exactly one implementation to "satisfy DIP" | Detect single-implementation interfaces (no polymorphic benefit) as its own smell (rule 1) |
| SRP evasion: a class does 5 things but is named "Manager"/"Service" | LCOM4 disjoint field-usage components = N responsibilities (rule 1; already in T-0330) |
| Hide the smell behind a feature flag / unreachable branch | Reachability over the call graph; unreached capable code is its own finding (rule 1/3) |
| Launder hand-written bad code as generated (abuse the T-0234 marker) | Generated marker must match real generator provenance and only exempts the DOC obligation, never arch/security (rule 5) |
| Just `frob:waive ARCH001` everything | Waiver budget + density gate + reason-quality + staleness (rule 4) |
| Lower the arch threshold in frob.toml | Per-function reasoned override only (T-0289); global threshold loosening is an audited config event, never silent (rule 5) |

### System design (strata, SYS/THREAT), incl. the .strata conformance question

The sharpest evasion is **the model is a lie**: a clean `.strata` file that
does not match the code. The defenses form the conformance-totality
requirement:

| Evasion | Defense |
|---|---|
| **Un-modeled module**: the dangerous code simply has no `.strata` node, so no obligation fires | **Coverage totality (SYS-COV):** every deployable/public module (and every module the scanner finds ANY capability in) MUST bind to exactly one strata node -- unbound-but-capable code is a hard failure, like COV001 for docs. No code hides outside the model. |
| **Under-declared capability**: node uses exec but doesn't declare it | **Effect conformance (>=):** the binding-aware, exhaustive scanner (T-0328/0337/0339) derives the ACTUAL effect set; the node must declare AT LEAST those. Scanner-found-but-undeclared = fail (closed-world accounting, T-0180). |
| **Undeclared public surface**: node declares interface {f,g} but code also exports `secret_backdoor` | **Interface conformance (exact):** the declared interface must EQUAL the code's actual public surface -- an undeclared public export is a failure, and a declared-but-absent symbol is a failure. Forces every module to declare its interface and keeps the two in lockstep. |
| **Purpose drift**: a "logging" module that opens sockets | **Purpose contract:** every node declares a PURPOSE, and a purpose carries an allowed-effect PROFILE; effects outside the profile need reasoned discharge. Purpose is a typed constraint, not a comment. A network effect in a declared pure/logging purpose fires. |
| **Binding laundering**: node binds to file X, real logic sits in unbound file Y | **Binding totality:** the code<->node binding is a TOTAL function over capable code; incomplete binding (capable file bound to no node) fails. |
| **Flow-break**: taint laundered through a serialize round-trip / global / DB write-read so the closure engine loses the edge | **Fail closed on flow:** a value entering an opaque store and re-emerging is treated as still-tainted OR flagged as an unprovable flow requiring reasoned discharge (rule 3). |
| **Fake mitigation**: discharge a CWE by declaring a sanitizer boundary that doesn't sanitize | **Evidence rung:** a mitigation must carry evidence at its required rung (a test/property proving it sanitizes), not a bare declaration (already the evidence ladder; T-0331 rule (a)/(c)). |
| **Assume-away**: `assume all input trusted` | Assumptions counted, dated, review-bounded; a trust-elevating assumption is high-risk and gated (rule 4). |
| **View narrowing**: pick the weakest baseline view so few obligations fire | A floor view that cannot be dropped; view selection is an audited config event (rule 5). |

## What this means for "do we force every module to declare purpose + interface?"

Yes -- that is exactly the conformance-totality requirement, and it is the
hardening the user asked for:

- **Declare or be flagged.** Every public/deployable module must bind to a
  strata node (coverage totality). Un-modeled capable code fails.
- **Declare your interface, exactly.** The node's declared interface must
  equal the code's real public surface (interface conformance). No hidden
  exports; no phantom declarations.
- **Declare your purpose, and live within it.** The node declares a purpose
  with an allowed-effect profile; effects outside it need a reasoned
  discharge (purpose contract).
- **Every claim is proven against code.** Declared capabilities/flows are
  checked against the exhaustive, binding-aware extracted effects; declare
  too little and the scanner catches you, declare a mitigation and it needs
  rung-level evidence (no bare declaration -- T-0331).
- **The residue fails closed.** Anything the analysis cannot resolve is an
  obligation, not a gap (T-0339).

Net: a module cannot be dangerous-and-silent. It either (1) resolves to a
declared, code-conformant, purpose-bounded node, or (2) trips coverage /
interface / effect / purpose / opaque-indirection findings that must be
explicitly, honestly discharged. That is the "nearly impossible to evade"
property, built the same way we hardened the capability scanner: ground
truth + conformance + fail-closed + bounded escape hatches + gated config.

## Soundness dependency (stated once, loudly)

All of strata's proof-against-code is only as sound as the code analysis.
An evadable scanner makes every SYS/THREAT proof unsound. So T-0328
(import/binding resolution), T-0337 (local-rebind aliases), and T-0339
(exhaustive-per-spec + fail-closed) are the FOUNDATION of this entire
document; the conformance layer inherits their soundness and their residue.

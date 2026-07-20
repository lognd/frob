# strata audit -- "if a proof/gate passes, the property actually holds"

Scope read in full: `_facts.py`, `_claims.py`, `_selfconform.py`, `_threat.py`
(1607 lines), `_audit.py`, `_deploy.py`, `_native_staleness.py`; plus targeted
greps across `_code_binding.py`, `_effects.py`, `_host.py`, `_models.py`.
Native kernels (`strata_core.reachable/worst_age/propagated_demand`) NOT read
(Rust, not in scope files); their behavior is taken from the Python callers'
contracts, which is itself a gap (see G10).

---

## (A) WHAT strata proves and HOW

**Kernel (`_facts.py`).** A `KernelModel` (nodes with trust/clearance/`may`
capabilities, flows with label/age/rate/size/attrs, boundaries on flows,
lattices) is validated (`build_facts`: unique ids, resolvable refs, known
lattice levels, acyclic lattices, non-negative quantities, `strata_core`
present) into a `FactBase`. Three closures run in Rust: `reachable` (BFS
influence closure; a flow carrying any boundary stops taint unless
`through_barriers`; a flow carrying `utility`/`krb_no_transit` is a TERMINAL
edge -- reachable but not chained past), `worst_age` (longest-path staleness,
`+inf` on positive-age cycle), `propagated_demand` (additive fanout-multiplied
load, `+inf` on positive-rate cycle).

**Prover (`_claims.py`).** Each `Claim` -> one `ClaimResult`. `noflow` PROVED
iff barrier-respecting closure from src reaches no dst; `reach` PROVED (exists)
with a through-barriers witness; `independent` PROVED iff no src->dst witness
shares a node with avoid's closure; `readers`(set-equality) exact closure
match; `bound` age/rate/utilization/latency/size arithmetic (utilization is
skew-aware + growth-saturation-horizon refuted). `assume` is never proved
(ledgered/owned/expiring). An `extraction_soundness`-waiver cascade downgrades
PROVED noflow/reach/independent/readers to ASSUMED.

**Threat (`_threat.py`).** THREAT001 catalog-completeness (every CWE a *view*
names is cataloged or explicitly out_of_scope); THREAT002 capability-
classification (every `may` kind is in the sink taxonomy or `BenignCapability`-
excused); THREAT003 discharge (every FIRED obligation -- node declares the
`may` kind an entry maps to -- has a `weakness:<cwe>:<node>` claim that is a
proven mitigation chokepoint of the right kind, at/above rung, not REFUTED);
THREAT004/005 code-level (observed sink undeclared / unclassified).

**Selfconform (`_selfconform.py`).** SYS100 capability observed in code but not
in `may`; SYS101 `may` declared but never observed; SYS102 a top-level
`src/frob/` directory with no `code=` owner.

**Audit (`_audit.py`).** `evaluate_exhaustiveness` conjoins THREAT001-003
(security+quality views), COMPLIANCE, PII, lint, CVE-fingerprint drift, and
HOST001/002 + blast-radius, applies `waive` clauses, reports named gaps.
`proved == no gaps`.

**Deploy (`_deploy.py`).** Validates endorsement-chain boundaries exist and are
ENDORSE-directed, canary levels are real, then generates SetTrust (canary) /
RemoveNode (rollback) scenarios and reuses `evaluate_scenarios`. (There is no
`DEPLOY001-003` rule id in the code; the task's naming is aspirational.)

---

## (B) FALSE-NEGATIVE / VACUOUS-PROOF findings (PRIORITY)

### TOP 5 (ranked)

**1. [HIGH] Boundaries are never bound to code -- every THREAT003 discharge is
a declaration, not a proof.**
`_threat.py:1090 _matching_boundary_ids` / `1190 _mitigation_is_chokepoint`.
THREAT003 is discharged when the author declares a `Boundary` with
`direction=ENDORSE` and `predicate == entry.mitigation` on the paths from a
foreign source, and the `NoFlow` claim then "proves" because
`FactBase.reachable` stops taint at ANY boundary. Grep confirms NO module in
strata joins a `Boundary` against observed code (`_selfconform.py`,
`_code_binding.py`, `_effects.py` bind only `may` capabilities and imports; the
only files importing both `Boundary` and effect-scanning are `_models`,
`__init__`, `_threat`, and `_threat` uses boundaries purely declaratively).
Repro: node with `may "sql"`, add `boundary b { flow f; endorse;
predicate="parameterization" }` on the only foreign inflow and a
`weakness:CWE-89:<node>` NoFlow claim -> THREAT003 PROVED with zero real
parameterization in the code. The string `"parameterization"` is free-form and
unregistered. This is the T-0256/T-0193 class: the property "a mitigation
actually interposes" reduces to "a string was typed in the model."
Fix direction: add a SYS-family rule binding each ENDORSE boundary's predicate
to an observed sanitizer site in the `code=`-bound files (analogous to SYS100),
or at minimum require chokepoint boundaries on managed/unmanaged nodes to carry
an evidence ref (`code=`/claim) that selfconform verifies -- otherwise document
loudly that THREAT003 is a TCB declaration, not a proof.

**2. [HIGH] `_mitigation_is_chokepoint` passes VACUOUSLY when no foreign->node
flow is modeled.**
`_threat.py:1196`. The first branch returns `True` if the `NoFlow` holds with
*every boundary removed* -- i.e. the sink is simply not reachable from foreign
in the model. A node that declares a firing capability (`may "sql"`,
`html_render`, `deserialize`, ...) but whose actual untrusted-input flow is
absent/under-modeled discharges its obligation with NO mitigation at all.
Nothing forces flow-completeness: selfconform checks `may` vs observed effects
but never checks that modeled flows cover real data paths. Repro: declare the
sink node and its capability, omit the inbound `flow` from the foreign node ->
THREAT003 PROVED "by absence of a flow." Combined with G1, an attacker-authored
or merely incomplete `.strata` passes the full exhaustiveness conjunction while
the real system is exploitable.
Fix direction: for a fired obligation, require at least one modeled path from a
foreign source to the firing node before accepting the vacuous short-circuit as
a discharge (or emit a distinct "obligation fires but sink is unreachable in
model -- verify the model is complete" diagnostic instead of silent PROVED).

**3. [HIGH] `eval` (dynamic code execution) is globally BenignCapability-
excused -- direct-RCE sinks pass THREAT002/THREAT005 with no obligation.**
`_threat.py:225-243 DEFAULT_BENIGN_CAPABILITIES`. `eval` is excused with reason
"no CWE_CATALOG entry targets dynamic code evaluation as a sink." But CWE-94
(Code Injection) IS cataloged (`CWE_TOP_25_CATALOG:485`) -- mapped to
capability_kind `"exec"`, not `"eval"`. So a node/file with dynamic
`eval`/`compile`/`__import__` fires NO obligation and observed `eval` in code is
THREAT005-excused. The single most dangerous capability is a global no-op.
Repro: `may "eval"` on any node, or an `eval(...)` site in bound code -> clean
threat report. `env`/`ffi`/`install-hook` are similarly globally excused.
Fix direction: map `eval` to CWE-94 (add capability_kind `"eval"` to CWE-94 or
alias eval->exec in the taxonomy) and drop it from the default benign tuple, so
it fires a real, dischargeable obligation.

**4. [HIGH] A FOREIGN file dropped into an already-modeled directory escapes
ALL sys rules (SYS100/101/102 and THREAT004/005 code scan).**
`_selfconform.py:538 _unmodeled_violations` marks a directory "owned" if ANY
file in it is non-FOREIGN (`prefix_owned` union). SYS100/101 and effect-
extraction scan only `_sorted_owned_files` (non-FOREIGN). So a new `.py`/`.ts`
file placed in an existing modeled directory but matched by no `code=` glob is
FOREIGN -> invisible to capability observation (no SYS100/THREAT004/005) AND
does not trip SYS102 (its directory is already prefix_owned). SYS102 also only
iterates *directories* (`_top_level_dirs`), so a FOREIGN file placed directly
under `src/frob/` (not in a subdir) also escapes.
Repro: add `src/frob/vet/backdoor.py` doing `subprocess.run(user_input)` where
no node's `code=` glob matches `backdoor.py` -> `frob sys audit` stays clean.
Fix direction: SYS102 must fire per-FOREIGN-file (or per unowned file within an
owned dir), not per fully-FOREIGN top-level dir; effect extraction should raise
on any FOREIGN capability-scannable file rather than skipping it.

**5. [HIGH/MEDIUM] `utility` flow marker silently defeats security `noflow`
claims (and thus THREAT003 chokepoints).**
`_facts.py:63,160`. Any flow carrying the surface attr `utility` (or synthetic
`krb_no_transit`) is a TERMINAL edge: taint does not chain past it. This is
honored on the *security* noflow side (`_eval_noflow` uses the same
`reachable`). A real exfiltration path that transits a hub edge marked
`utility` is invisible to noflow -> the claim PROVES and any THREAT003 discharge
built on it is vacuous. The marker is author-controlled with no compensating
check that the edge is genuinely non-relaying.
Repro: `flow log_hub { src=secret_store; dst=logger; utility }` then
`flow leak { src=logger; dst=foreign_sink }`: `noflow(secret_store, foreign_
sink)` PROVES despite the two-hop leak.
Fix direction: forbid `utility` on flows whose payload label is above a floor,
or exclude `utility` termination when evaluating confidentiality noflow (keep
it only for capacity/availability closures where T-0226 actually needed it).

---

## (C) FALSE-POSITIVE / soundness (lower priority; engine leans deny-by-default)

- `propagated_demand` treats an unresolvable `rate` unit as "propagate source
  demand" (over-counts) -- deliberate deny-by-default, sound direction, may
  produce spurious RATE/UTILIZATION refutations (`_facts.py:202` docstring
  owns this). Acceptable.
- `_mitigation_is_chokepoint` is conservative (per-model, not per-path); a
  model saved by a mix of matching+non-matching boundaries REFUTES. Sound,
  precision-only gap, already disclosed at `_threat.py:1172`. Acceptable.

No unsound false-positive (PROVED-should-be-REFUTED) found in the arithmetic
paths; the danger is entirely on the false-negative side.

---

## (D) Per-component pessimistic verdict

- **`_facts.py` kernel**: RIGHT for what it models (flow/trust/age/rate). But
  the model is only as sound as its flow-completeness, which nothing enforces.
  Good engine, blind to un-modeled edges. B.
- **`_claims.py` prover**: mechanically correct decision procedures; forall/
  exists quantifiers honest. The soundness hole is upstream (boundaries/flows
  unbound to code), not here. B+.
- **`_threat.py`**: the exhaustiveness *framing* is strong (deny-by-default,
  every gap named) but the DISCHARGE is declaration-based (G1/G2) and the
  default coverage is ~8 CWEs (owasp-top-10) with `eval` excused (G3). "Feels
  exhaustive, discharges on trust." C+ as a security proof, B as a bookkeeper.
- **`_selfconform.py`**: solid capability reconciliation, but the FOREIGN-file
  blind spot (G4) is a real hole in "the model can't lie about the code."
  Checks `may`, ignores boundaries entirely. C+.
- **`_audit.py`**: clean composition, good waiver hygiene. Inherits every
  underlying gap. B.
- **`_deploy.py`**: endorsement-chain validation is declaration-only (same G1
  class -- ENDORSE boundary existence, not code evidence). Reuses scenarios
  soundly. B-.
- **`_native_staleness.py`**: mtime comparison, NOT content digest -- a
  `touch`ed artifact or checkout-order artifact defeats it (G9). Dev-convenience
  warning mislabeled as provenance. Fine for its stated purpose, weak as tamper
  detection.

---

## (E) Concrete GAPS/DEFECTS

- **G1 [HIGH]** Boundaries never bound to code; THREAT003 chokepoint is a
  declared string. `_threat.py:1090,1190`. Repro in B1.
- **G2 [HIGH]** Vacuous discharge when foreign->sink flow un-modeled.
  `_threat.py:1196`. Repro in B2.
- **G3 [HIGH]** `eval`/`env`/`ffi`/`install-hook` globally benign-excused;
  CWE-94 maps to `exec` not `eval`, so dynamic-code-exec fires nothing.
  `_threat.py:225`. Repro in B3.
- **G4 [HIGH]** FOREIGN file in a modeled dir (or loose file directly under
  `src/frob/`) escapes SYS100/101/102 + THREAT004/005. `_selfconform.py:538,508`.
  Repro in B4.
- **G5 [MEDIUM]** `utility`/`krb_no_transit` terminal edges defeat
  confidentiality `noflow`. `_facts.py:63,160`. Repro in B5.
- **G6 [MEDIUM]** Default security coverage is `VIEWS = {owasp-top-10}` = 8
  CWEs; `cwe-top-25` is NOT in `DEFAULT_SECURITY_VIEWS` (only `tuple(VIEWS)`,
  `_audit.py:109`). A default `frob sys audit` proves exhaustiveness over 8
  weaknesses and reports "proved". `_threat.py:653`, `_audit.py:109`.
- **G7 [MEDIUM]** `_discharges_as_chokepoint` accepts `src=="foreign"` trust
  level; if the model declares NO foreign-trust node, `_expand("foreign")`
  yields an empty source set and the NoFlow proves vacuously (no source to walk
  from), discharging obligations with no adversary modeled. `_threat.py:1084`,
  `_claims.py:160-169`.
- **G8 [MEDIUM]** THREAT005 indexes `binding.owner[effect.file]`
  (`_threat.py:1474`) but `extract_effects` is what populates effects; if a file
  is present in effects but keyed differently than `binding.owner`, this
  KeyErrors (crash, not fail-closed). Verify `extract_effects` only yields
  owned-file effects; if it can yield FOREIGN, this is a crash on hostile input.
- **G9 [LOW]** Native staleness is mtime-only, not a content hash;
  `touch strata_core*.so` hides a stale/edited native so `frob check` runs the
  OLD parser against new grammar. `_native_staleness.py:89,160`.
- **G10 [LOW]** `FactBase.reachable/worst_age/demand` assert `strata_core is not
  None` and trust the Rust kernel's correctness un-audited here; the entire
  soundness of every noflow/reach/bound proof rests on three Rust functions not
  in the reviewed set. `_facts.py:153,180,223`. At minimum add differential/
  property tests against a pure-Python reference.
- **G11 [LOW]** `_eval_bound_latency_or_size` silently returns REFUTED "declares
  no X to check" when `body.metric is LATENCY` because `declared` is hardcoded
  to `flow.size if SIZE else None` -- LATENCY bounds can NEVER prove, always
  refute-as-missing. `_claims.py:564`. Either LATENCY is unsupported (then it
  should error, not masquerade as a refutation) or it is a dead metric.
- **G12 [LOW]** `BenignCapability` per-repo channel
  (`load_repo_benign_capabilities`, `_threat.py:290`) lets a consuming repo
  excuse ANY capability kind from its own `frob.toml` with just a reason string
  -- a repo can self-excuse `sql`/`html_render` and pass THREAT002/005. Reason
  is required but unvalidated; there is no allowlist of excusable kinds.

---

## Notes -- checked & correct (don't re-verify)

- Arithmetic decision procedures in `_claims.py` (age/rate/utilization/zipf/
  saturation) are internally consistent; quantifier tags match the procedures;
  `+inf` cycle handling is honest.
- `build_facts` fail-closed ordering (native, lattice-acyclic, ids, levels,
  non-negative) is correct and typed.
- Waiver hygiene across `_selfconform.py`/`_audit.py` (stale-waiver-as-violation,
  sub-target matching, host channel exclusion) is careful and correct.
- THREAT002 taxonomy-wide-vs-per-family split (`ALL_CATALOG`) is sound.
- `_mitigation_is_chokepoint` conservative direction is genuinely sound (removing
  boundaries only adds reachability).

## Notes -- skipped / skimmed (audit boundary)

- Rust kernels (`strata-core/src/lib.rs`, `parse.rs`) NOT read -- G10.
- `_compliance.py`, `_pii.py`, `_host_isolation.py`, `_scenarios.py`,
  `_breach.py`, `_atomic.py`, `_crash.py`, `_cve_fingerprint.py`, `_elaborate.py`,
  `_lint.py`, `_export.py`, `_infra.py`, `_secrets.py`, `_krb.py` read only via
  grep/imports -- the compliance catalog completeness (analogous ~30-of-N
  concern to G6) and PII undeclared-flow detection deserve the same
  false-negative pass as THREAT003 but were not opened line-by-line here.
- `_effects.py::extract_effects` internals skimmed; G8's KeyError hypothesis
  needs confirmation there.
</content>
</invoke>

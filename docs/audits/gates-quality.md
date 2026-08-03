# Audit: quality/security detector gates

Status: 2026-07-28

North-star under test: **"if `frob check` passes (exit 0), the code is actually good."**
Verdict up front: **badly false** for the entire quality surface. The dup, perf, PII,
structural-secrets, and architecture detectors are individually reasonable pieces of
engineering, but the *gate wiring around them* means almost none of them can turn a
green `frob check` red. `frob check` exits nonzero **only when `total_errors > 0`**
(`src/frob/app/check_runner.py:394`). Every one of PERF001-004, PII010, SEC110, ARCH001,
and the lower-tier secret rules is emitted at `Severity.WARN`, and WARN is explicitly
"visible, not blocking" (`src/frob/gates/__init__.py:834`). The most impactful clone
detector (DUP) and FUZZ are **off by default**. So a repo can carry O(n^2) perf smells,
undeclared PII fields, god-classes, deep nesting, and clones, and still exit 0.

---

## (A) What each detector catches and how

### Secrets (`gates/_secrets.py`, SEC001/SEC002/SEC003)
- Line-oriented regex scan of every `git ls-files` tracked file against a fixed table of
  ~28 provider patterns (`_PATTERNS`). Most fire `Severity.ERROR`; Stripe *test* keys,
  Twilio account SID, JWT, and Plaid fire `Severity.WARN`.
- SEC003 (`sk_live_`, PEM private-key header) is on `_UNWAIVABLE_RULES`.
- SEC002: a tracked `.env`/`.env.*` file (excludes `.example/.sample/.template`).
- Suppression: `_looks_fake(token)` (placeholder runs `XXXX`/`****`, template-shape
  fullmatch, low-entropy `your-/insert-/-here`, or the substring words
  `fake/changeme/example/placeholder`), plus a `frob:secret-fake` line/prev-line marker.
- Redaction via `_redact` (never echoes token).

### Structural PII / env-secrets (`gates/_pii_structural/`, PII010/SEC110) -- both WARN
- AST over tracked `.py`. PII010: a pydantic/dataclass/TypedDict/NamedTuple/attrs class
  `AnnAssign` field whose `_`-split name token equals a `FIELD_SIGNATURES` keyword, or
  whose annotation contains `EmailStr`/`SecretStr`. Deny-by-default; discharged only by a
  `frob:waive`.
- SEC110: `os.environ[...]` / `os.environ.get` / `os.getenv` sites, minus an env-var-name
  allowlist (`DISPLAY`, `PATH`, `XDG_*`, etc.).

### Perf (`perf/_rules.py`, PERF001-004) -- all WARN
- Runs over `RawSymbol.body_tokens` (flat, **position-free** leaf token stream) per
  function. PERF001 membership-in-list-in-loop; PERF002 `.index()/.count()` in loop;
  PERF003 nested-loop equality-join (with outer-loop-variable operand guard); PERF004
  `sorted()/.sort()` in loop. `_bracket_depths` distinguishes real depth-0 loop headers
  from comprehension `for`. TS/Rust get PERF001/002 best-effort via `.includes/.indexOf/
  .contains` token literals. Line number recovered by a **second regex pass** over source.

### Arch (`arch/_python.py`, `arch/_cpp.py`, `gates/_arch.py`) -- ARCH001 WARN
- tree-sitter. Categories: long-function, god-class, deep-nesting, high-coupling,
  large-file, abstraction-opportunity. long-function fires only when a function is BOTH
  over `max_function_lines` AND `_py_is_complex` (nesting >=3 OR cyclomatic-proxy >=8).
- **Only `long-function` is channeled to a `Violation` (ARCH001).** Every other category
  is a non-gate WARN suggestion by design (`gates/_arch.py:13-16`).

### Dup (`dup/**`, DUP001/DUP002) -- off by default
- Rung ladder R1 (exact token hash) / R2 (alpha-renamed token hash) pure-Python; R1.5/R3/
  R4/R5 require `frob_core` native; R6/R7 opt-in behavioral/SMT. Gate compares
  diff-touched refs against the snapshot.
- Gate is gated three ways: `[dup].enforce` (default **false**), `core_available()`,
  and `diff` touched-set.

---

## TOP-5 RANKED FINDINGS

### 1. [HIGH] The whole quality surface is non-blocking: WARN never fails `frob check`
`frob check` exits nonzero only on `total_errors > 0` (`app/check_runner.py:394`), and
PERF001-004, PII010, SEC110, ARCH001, plus WARN-tier secrets are all `Severity.WARN`
("visible, not blocking", `gates/__init__.py:834`).
**Repro:** add a function with `sorted(x)` inside a `for` loop and a pydantic model with a
`password: str` field. `frob check` prints warnings and **exits 0**. North-star violated
directly: green != good.
**Fix direction:** either promote these rules to ERROR by default (with the existing
`[gates.severity]` table as the *downgrade* escape hatch, inverting today's default), or
make `frob check` exit nonzero on unwaived WARNs. At minimum document loudly that a green
check makes no claim about perf/PII/arch. The current default is the honest-gate
anti-pattern this repo elsewhere polices.

### 2. [HIGH] DUP detector is off by default AND silently no-ops when native core absent
`dup_gate` returns `()` when `[dup].enforce` is false (default) -- frob's own `frob.toml`
has no `[dup]` block, so **DUP never runs in this repo** -- and returns `()` again when
`core_available()` is false (`gates/__init__.py:3067-3072`). A missing/unbuilt
`frob_core` (fresh worktree -- see the repo's own "worktree natives artifact" note) turns
the entire semantic-clone ladder R3-R5 into a green no-op with only a `_log.warning`.
**Repro:** in a worktree without `frob_core` built, or any repo not opting in, paste a
whole duplicated function; `frob check` is green.
**Fix direction:** make DUP enforce default-on for repos that ship `frob-core`; when
`enforce` is true but core is missing, emit a blocking ERROR ("clone detection requested
but unavailable"), not a silent skip -- a requested-but-unavailable security/quality
control failing open is the exact degrade-to-green failure the task names.

### 3. [HIGH] `frob:secret-fake` marker suppresses real secrets with zero accountability
`_line_marks_fake` (`gates/_secrets.py:511`) suppresses *every* secret match on a line
(and the line below) whenever the literal `frob:secret-fake` appears, with **no reason
string, no ticket, no waiver record** -- unlike `frob:waive`, which requires
`reason="..."`. Additionally `_looks_fake` suppresses any token merely *containing* the
substring `example`/`fake` (`_PLACEHOLDER_WORDS`, matched against the token text).
**Repro (pre-T-0968):** commit `AWS_KEY = "AKIA` + `IOSFODNN7EXAMPLE"  #` + ` frob:secret-fake`
(split here across several code spans purely so this doc's own text no longer trips this
repo's own tightened SEC001/SEC004 gate -- the underlying finding is unchanged) -- or any
real key whose value happens to contain `example` -- and SEC001 was silently discharged;
nothing tracked that a human vouched for it.
**Fix direction (landed, T-0968):** `frob:secret-fake` now requires `reason="..."`
(bare markers fire their own SEC004, mirroring WAIVE001); the bare-substring
`example`/`fake` suppression is dropped from `_PLACEHOLDER_WORDS` in favor of the
anchored template-shape/entropy checks only. NOT landed: literally routing discharged
hits through the graph-edge `frob:waive`/WAIVE004 machinery -- the marker stays a
DSL-reserved, graph-invisible verb (T-0157), so WAIVE004's zero-findings staleness
check does not watch it yet; see the follow-up ticket `_secrets.py`'s module docstring
cites.

### 4. [MEDIUM] Arch complexity is trivially gameable; 4 of 6 categories are non-gate
god-class (`arch/_python.py:171`) iterates only `t.root_node.children` (top-level
classes) and counts only direct `function_definition` children of the class body.
Nesting/large-file/coupling are all **per-file, per-function**. None are `Violation`s
except long-function.
**Repro / evasions:**
- Split a 40-method god-class into a base class + 3 mixins across files -- each under
  `max_class_methods`, god-class never fires (and wouldn't be a gate error even if it did).
- Nest a class inside a function or inside another class -- not in `root_node.children`,
  invisible to god-class entirely.
- Extract deeply-nested blocks into helper functions -- per-function nesting drops below
  threshold while total complexity is unchanged; deep-nesting silent (and non-gate).
- Move imports into functions or split a file -- coupling/large-file per-file counts drop.
**Fix direction:** recurse god-class into nested/function-local classes; consider
aggregating coupling across a package, not just per-file; and make a deliberate decision
about promoting god-class/deep-nesting to gate `Violation`s (the module explicitly forbids
this without a "fresh design decision" -- this is that flag).

### 5. [MEDIUM] PII010 misses camelCase / non-underscore field names
`_field_name_hit` (`_pii_structural.py:159`) lowercases and splits the field name on `_`,
then matches single-word keywords by **exact token equality**. A camelCase or
concatenated field name never produces the token.
**Repro:** `class User(BaseModel): passwordHash: str` -> lowered `passwordhash`, split
`{"passwordhash"}`, keyword `password` not present as a whole token -> **no PII010**.
Same for `apiKey`, `ssnValue`, `creditCardNo`, `dateOfBirth`. TypeScript/Rust models are
entirely out of scope. (Even when it fires, it is WARN -- see finding 1.)
**Fix direction:** split on camelCase boundaries too (or substring-match single-word
keywords with a short curated stop-set to avoid `token`-in-`tokenizer`), and file the
already-disclosed TS/Rust field-shape follow-up as a real ticket.

---

## Additional gaps/defects (>=10 total with the above)

6. [MEDIUM] **Secrets scanner is line-oriented -- line-wrapped or assembled secrets evade.**
   `_scan_line` matches each physical line independently (documented, `_secrets.py:46-50`).
   Repro: a key literal split across two physical lines by a formatter, or a base64 secret
   hard-wrapped, passes with zero findings. Fix: also scan a whitespace-joined logical-line
   view for the fixed-prefix providers.

7. [MEDIUM] **Secrets table is a closed provider list -- any unlisted format is a false
   negative.** No generic entropy fallback (deliberate). Repro: an Azure connection
   string, a DigitalOcean `dop_v1_...`, a Mailgun `key-...`, a raw 64-hex DB password,
   or any bearer token not in `_PATTERNS` commits clean. The gap is documented, but the
   north-star claim ("code is good") is still false for these. Fix: add a context-gated
   entropy pass (assignment RHS near a secret-ish identifier) as a WARN, and/or expand.

8. [MEDIUM] **PERF004 is indentation-blind -- known false negatives.** Documented in
   `tickets.md:7917` (T-0367 disposition): the token-stream `_loop_gate` cannot tell a
   `sorted()` that is *inside* a loop body from one merely lexically after a loop header
   at the same function scope. Repro sites named in the ticket: `dup/_template.py:159`,
   `graph/__init__.py:153`. Same class affects PERF001-003: `_loop_gate` fires on "a
   depth-0 `for/while` appears anywhere before the pattern", so a pattern in a function
   that merely *contains* an earlier unrelated loop can false-fire, and a pattern genuinely
   inside a loop that lexically precedes the loop keyword is missed. Function-granular
   approximation, not real block nesting; real fix needs per-token line/block structure.

9. [MEDIUM] **PERF is lexical where it should be structural -- aliasing/wrapping evades.**
   `_container_kinds` only recognizes `name = [..]` / `set(..)` literal shapes in the same
   token stream. Repro: `items = get_list()` then `x in items` in a loop -> container kind
   unknown -> PERF001 never fires (the O(n^2) is real). `.index()` reached through a local
   alias, a comprehension-built list, or a helper return is invisible. "Do not fire on
   unknown" is a pure false-negative machine for any non-literal container.

10. [MEDIUM] **SEC110 is WARN-only and narrow.** `_scan_python_env_access` only
    allowlist-checks when the var name is a bare string literal; the whole rule is WARN so
    it blocks nothing. `load_dotenv()`, `process.env` (TS), `std::env::var` (Rust) are out
    of scope (disclosed). Net: env-secret surfacing is advisory-only.

11. [MEDIUM] **DUP R1/R2 catch only exact/alpha-rename clones; R3+ needs opt-in native.**
    R2 abstracts *all* identifier tokens uniformly, but keyword/operator/statement-reorder
    changes defeat R1/R2 entirely (`dup/_pipeline.py:27-32`). Semantic clones with
    different tokens require R3-R5 (native + off by default). Repro with dup enforced but
    core absent: two functions differing only by `for`/`while` or reordered independent
    statements are not flagged. Cross-language clones are never detected. So even *with*
    DUP on, "different tokens, same behavior" largely escapes unless R6/R7 (opt-in) run.

12. [MEDIUM] **DUP gate only inspects diff-touched refs -- pre-existing duplication is
    invisible.** `_dup_gate_violations` filters to `touched_refs(snapshot, diff)`
    (`gates/__init__.py:3100`). A repo that already contains 10 copies of a function is
    green forever until one is touched; a fresh clone only trips if the *new* symbol is in
    the diff. A whole-repo baseline sweep is absent from the gate path. Fix: offer a
    non-diff full-repo dup audit mode that the gate can require on first adoption.

13. [LOW] **`_looks_low_entropy` gate is defeatable and its 3.7 bits/char cut is a magic
    constant calibrated to this repo's fixtures** (`_secrets.py:440`). A crafted
    low-entropy single-case token containing `your-`/`insert-`/`-here` suppresses SEC001.
    Bounded blast radius (attacker must shape the token) but a documented soundness
    compromise in a security gate.

14. [LOW] **`_is_data_structure` misses common model bases.** PII010 only recognizes
    `BaseModel`/`TypedDict`/`NamedTuple` bases and `dataclass/define/attrs/frozen`
    decorators. A model subclassing an intermediate project base (`class User(OrmBase)`,
    SQLAlchemy `DeclarativeBase`, Django `models.Model`) is not a "data structure", so its
    `password`/`ssn` columns are never scanned -- a false negative for the most common real
    PII carriers (ORM rows).

15. [LOW] **`_field_type_hit` matches annotation names anywhere in the subtree.** A field
    `x: Callable[.., EmailStr]` where `EmailStr` is incidental would false-fire PII010.
    Minor precision nit; WARN-only.

---

## (D) Per-detector pessimistic verdict

- **Secrets:** Best of the set -- mostly ERROR/blocking, redaction is disciplined, gaps are
  honestly documented. But closed-list + line-oriented + accountability-free `secret-fake`
  marker mean it is FAST-and-narrow, not RIGHT. Good enough as a tripwire; do not market
  it as "no secret gets through".
- **PII structural:** Right idea, weak reach. camelCase blindness, ORM-base blindness, and
  WARN-only severity make it advisory. Not good enough to claim PII coverage.
- **Perf:** Honest about being a coarse lexical linear-scan; that honesty is the point.
  Real O(n^2) through any indirection is invisible, and it is WARN. FAST, not RIGHT --
  fine as a nudge, useless as a guarantee.
- **Arch:** long-function is reasonable and gated; the other five categories are
  computed-then-discarded from the gate and trivially gameable. Not a quality guarantee.
- **Dup:** Genuinely sophisticated engine (WL, APTED, anti-unification, SMT). Undermined
  by being off-by-default, native-dependent with silent fail-open, and diff-scoped. RIGHT
  algorithm, wrong wiring -- the correctness is stranded behind three "off" switches.

---

## Notes: checked and correct / deliberately skipped

**Verified correct (fixer need not re-check):**
- `core_available()` in *this* repo returns true (`frob_core` importable at
  `.venv/.../frob_core`), so R3-R5 work here; the fail-open concern is about *other* repos/
  worktrees.
- `_redact` never returns the raw token; every violation message routes through it.
- `_bracket_depths` correctly excludes comprehension/generator `for` from loop context
  (T-0161 fix is sound for the depth-0 vs depth>=1 distinction).
- PERF003's outer-loop-variable operand guard (`_perf003_inner_equality_hit` +
  `_operand_names`) genuinely narrows the sibling-loop false positive.
- `_is_env_file` correctly excludes `.env.example/.sample/.template`.
- SEC003 rules are on `_UNWAIVABLE_RULES` and are ERROR (real blocking).
- `run_gates` registry includes perf/secrets/archgate/pii_structural by default; clones and
  fuzz are opt-in (confirmed at `gates/__init__.py:3600-3620`, `dup_gate`/`fuzz_gate`).

**Skipped / skimmed (audit boundary):**
- FUZZ (`fuzz/_rules.py`) read only at the enforce-gate level (default OFF, same class as
  DUP finding 2); did not audit obligation-resolution internals.
- `dup/_legacy*.py`, `_template.py`, `_cache.py` internals and the frob-core Rust kernels
  (WL/APTED/winnow correctness) not verified -- treated as trusted given they are native and
  out of Python-editable scope; a real dup correctness audit needs the Rust sources.
- `arch/_cpp.py` skimmed (parity structure with `_python.py`; same non-gate-category issue
  applies, C++ has even fewer categories).
- Did not run the detectors against adversarial fixtures live; repros above are derived
  from reading the algorithms, each tied to a concrete input.

---

## T-0399: executed promotion plan (2026-07-27)

Measured live warning counts on `main` via chunked `frob check --only <stage>`
(docs/guides/agent-playbook.md section 3b's sanctioned loop; a single unchunked run
exceeds the foreground budget on this repo). Counts below are "unwaived" (the
`gate:<X>` summary line's `warnings` figure) -- the separate `waived` figure is
findings already discharged by a reasoned `frob:waive`.

| Family | Rule(s) | Unwaived | Waived | Classification | Disposition |
| --- | --- | --- | --- | --- | --- |
| Perf | PERF001-004 | 1730 | 30 | promotable-after-burn-down | child filed, count named |
| PII structural | PII010/PII012 | 167 | 3 | promotable-after-burn-down | child filed, count named |
| Env-secret reads | SEC110 | 16 | 10 | promotable-after-burn-down (small, near-term) | child filed, sites named |
| Arch | ARCH001 (only gated category) | 101 | 13 | promotable-after-burn-down + fresh design decision on the other 5 categories | child filed |
| Clones | DUP001/DUP002 (fail-open half) | n/a (off by default) | n/a | promotable-now | **executed**: `dup_gate` now fails CLOSED (DUP003, ERROR) when `[dup].enforce=true` but frob-core is unavailable |
| Clones | DUP (default-off half) | n/a | n/a | promotable-after-burn-down | child filed: live-tried `enforce=true` here and it blew the ~150s chunk budget (`find_clones` indexes the whole snapshot, not just the diff) -- needs profiling/caching before it can default on |
| Secrets suppression accountability | `frob:secret-fake` marker (finding 3) | n/a (marker, not a rule count) | n/a | promotable-after-burn-down | child filed: every existing bare marker in the tree needs a `reason=` added in the same change that tightens the parser, and none of those call sites are in T-0399's scope |
| Stale-waiver watchdog | WAIVE004 | 796-926 per chunk (chunk-dependent, see caveat) | -- | advisory-by-design | not part of this audit's named families; WAIVE004 is explicitly documented (its own message text) as "known-flaky for diff-scoped rules and any `--only`-excluded gate; trust this only from a full, unscoped run" -- promoting a partial-run-unreliable gate to blocking would red every chunked check by construction, not just this repo's real debt |

Why nothing else promoted straight to ERROR this round: T-0399's own declared scope is
`src/frob/gates/`, `src/frob/app/config.py`, `frob.toml` (plus `docs/modules/gates.md`
and this file, added via `frob ticket scope --add` for the required doc updates). Every
family above except DUP's fail-open half has its live findings sitting in files OUTSIDE
that scope (`src/frob/deploy/`, `src/frob/arch/`, `src/frob/strata/`, `tests/**`, ...) --
promoting the rule to ERROR without first waiving/fixing those findings would
immediately red `main`, which the dispatching instructions for this ticket explicitly
rule out. The children below are scoped precisely to the files that would need touching.

**Executed this ticket:**
- `dup_gate` (`src/frob/gates/__init__.py`) fails closed with a new `DUP003` ERROR
  violation when `[dup].enforce=true` but `frob-core` is not installed/built, instead of
  silently returning `()`. `DUP003` added to `_KNOWN_GATE_RULES` and documented in
  `docs/modules/gates.md`. Covered by
  `tests/test_gates.py::TestOptInGates::test_dup_gate_fails_closed_when_enforced_but_core_missing`.
- frob.toml gained a documented, deliberate decision NOT to flip `[dup].enforce=true` on
  yet, with the measured reason (chunk-budget blowout) recorded inline so a future reader
  does not have to re-derive it.

**Children filed (parented under the new epic below):**
- Epic: `T-0969` -- "burn WARN-tier quality gates to zero, then promote to ERROR"
- `T-0972` -- PERF001-004 burn-down (1730 findings)
- `T-0971` -- PII010/PII012 burn-down (167 findings)
- `T-0973` -- SEC110 burn-down (16 findings, sites named in the ticket body)
- `T-0970` -- ARCH001 burn-down + fresh design decision on the other 5 arch
  categories (101 findings)
- `T-0974` -- profile/cache `find_clones` so `[dup].enforce=true` fits the check
  budget, then default it on
- `T-0968` -- `frob:secret-fake` requires `reason=` and routes through the
  waiver ledger (audit finding 3)

Draft ids above are renumbered to real `T-####` ids at land time per this repo's normal
ticket-drafting convention; re-resolve via `frob ticket show` / the ledger at pickup time
rather than trusting the draft id past this session.

---

## T-0970: ARCH001 burn-down (partial) + the fresh design decision on the other ARCH categories

Measured live via chunked `frob check --only gates-native --json` (2026-07-27,
post-`main`-merge). The original "101 findings" figure in T-0399's table above is the
**sum across all four gated ARCH codes**, not ARCH001 alone: `52 (ARCH001) + 2 (ARCH101)
+ 23 (ARCH102) + 24 (ARCH103) = 101`, 13 already waived. Splitting it out this way
matters for the decision below -- T-0399's own finding 4 predates T-0728, which already
wired the "computed then discarded" categories (god-class/deep-nesting/high-coupling/
large-file/abstraction-opportunity) into three real gated-WARN codes:
`low-cohesion-class`/ARCH101, `god-module`/ARCH102, `mixed-concern-function`/ARCH103
(`src/frob/gates/_arch.py`). They are no longer silently discarded -- they show up in
`frob check` output today -- but none of the three has ever been promoted to `ERROR`.

### ARCH001 (long-function) -- burn-down status: partial, child filed

This ticket landed 5 of 52 unwaived ARCH001 findings:
- 3 genuine extractions that dropped the function below threshold entirely (no waiver
  needed): `_run_stamp_baseline` -> `_run_baseline_chunks`
  (`src/frob/app/check_runner.py`), `check_layering_violations` ->
  `_layering_violations_for_file` (`src/frob/arch/_layering.py`), and
  `check_no_di_construction`'s duplicated method/function loops merged into one shared
  `_append_no_di_findings` helper (same file -- also removes a real duplication, not
  just an ARCH001 fix).
- 2 honest `frob:waive ARCH001` additions, each with a specific structural argument (not
  a blanket waiver): `_check_pool_inside_pool` (`src/frob/arch/_concurrency.py`, two
  related checks sharing one pass's classified call lists) and `_tarjan_sccs`
  (`src/frob/graph/summary.py`, an indivisible iterative Tarjan implementation).
- 1 more waiver: `check_over_broad_except` (`src/frob/arch/_fallibility.py`, one closure
  emitting two related per-catch findings off the same loop variable).

47 unwaived ARCH001 findings remain (measured post-fix). `[gates.severity] ARCH001` stays
`"warning"` in `frob.toml` -- flipping it to `"error"` with 47 live findings would red
`main` immediately, which this ticket's own instructions rule out. **Decision: promote
once the remainder child below drives ARCH001 to zero/near-zero unwaived.** Remainder
child: `T-0976` (carries the exact 47-item list at hand-off).

### ARCH101/ARCH102/ARCH103 -- the fresh design decision (finding 4)

Per-category promote-or-advisory decision, each with its live unwaived count:

- **ARCH101 (low-cohesion-class, LCOM4) -- 2 live, 0 waived. Decision: promotable-
  after-burn-down, near-term.** The count is small (both findings are in
  `src/frob/mutate/__init__.py`) and the LCOM4 field-usage-group computation is a real
  structural signal, not the trivially-gameable top-level-only god-class scan finding 4
  originally complained about (T-0728 rewrote it) -- burn the 2 down and flip to error.
- **ARCH102 (god-module / export-cohesion clustering) -- 23 live, 0 waived. Decision:
  stays advisory (WARN) for now, NOT promoted.** The naming/usage clustering heuristic
  that groups a module's top-level exports has not itself been audited for the same
  class of blind spot finding 4 found in the old god-class scan (a heuristic gameable by
  restructuring exports without changing real cohesion) -- promoting an unaudited
  heuristic to a blocking gate risks the same "green != good" failure this whole audit
  exists to catch. Burn-down + heuristic-soundness check tracked in
  `T-0977`.
- **ARCH103 (mixed-concern-function / SRP-ish I/O+branch mixing) -- 24 live, 0 waived.
  Decision: promotable-after-burn-down**, same treatment as ARCH001 -- burn the 24 down
  (extract or waive with a real argument) via `T-0977`, then flip to error.

Draft ids (`T-0976`, `T-0977`) are renumbered to real `T-####` ids at
land time per this repo's normal convention; re-resolve via `frob ticket show` at pickup
time rather than trusting the draft id past this session.

---

## T-0977: ARCH101/102/103 burn-down + fresh design decision on ARCH102's heuristic

Measured live via chunked `frob check --only gates-native --json` (2026-07-27,
post-`main`-merge, natives rebuilt). Baseline at pickup: ARCH101 2 live/0 waived,
ARCH102 23 live/0 waived, ARCH103 24 live/0 waived (matching T-0970's hand-off).

### Root-cause bug found and fixed: `frob.arch._python`'s field-access extractor

Both ARCH101 findings (`_Mutator`, `_PointCollector` in `src/frob/mutate/__init__.py`)
turned out to be false positives from a bug in `_py_collect_body_events`
(`src/frob/arch/_python.py`): every `attribute` tree-sitter node was recorded as a
`self.<field>` read/write regardless of (a) whether the object half was actually `self`
(`node.ops`, a local AST-node parameter, was being counted as a "field" access), or (b)
whether the attribute was the callee of a method call (`self._hit(...)`, a call, not a
field read/write -- already captured separately via `NormalizedCall`). This inflated
`_Mutator`'s/`_PointCollector`'s apparent field-usage graph with coincidental shared
"fields" that were really just shared helper-method names, producing exactly the kind of
gameable, structure-blind false signal finding 4 already flagged for other `frob.arch`
checks. Fixed via a new `_py_is_self_attribute` guard (object must be the bare identifier
`self`, and the attribute must not be a call's own callee); both ARCH101 findings drop to
zero without touching `mutate/__init__.py` itself. Covered by the existing
`tests/unit/test_arch_srp.py` / `tests/unit/test_arch.py` suites (symref format changed --
tests updated to the now-path-qualified `path::qualname` shape below).

### Second bug found and fixed: ARCH1xx symrefs were never waivable

Independently of the above, `frob.arch._srp.check_lcom4`/`check_mixed_concern_function`
set `symref` to a BARE qualname (`"BigService"`, `"run"`) while `frob.gates._match_waiver`'s
symref-exact matching path (used whenever a violation carries a `symref`) requires the
`path::qualname` shape `frob.graph.dsl._enclosing_src` produces for every
`frob:waive`-bearing symbol (the same shape `ARCH001`'s `frob.arch._python` symref already
used). This meant NO `frob:waive ARCH101`/`ARCH103` placed above a class/function could
ever match -- an invisible-until-tested gap, since neither rule had ever needed a real
waiver before this ticket. Fixed by qualifying both symrefs with `module.path::` in
`frob.arch._srp` (ARCH102 has no per-symbol `symref` at all -- module-level only -- so it
was unaffected). Verified working by exercising the 22 waivers below (see ARCH103 section).

### ARCH101 (low-cohesion-class) -- 0 live, promoted to error

Both findings were the false positives above; fixed at the root cause (extractor, not the
2 sites). `[gates.severity] ARCH101 = "error"` in `frob.toml`. Verified: a full
`frob check --only gates-native` run after the flip shows `pass gate:ARCH 0 errors, 82
warnings, 16 waived` -- the flip does not red `main`.

### ARCH102 (god-module) -- 23 -> 11 live, heuristic fixed, STAYS advisory

Audited the clustering heuristic (`frob.arch._srp._god_module_clusters`) for finding 4's
named blind spot ("gameable by restructuring exports without changing real cohesion").
Found it: a module whose top-level exports are predominantly pure DATA classes (zero
methods -- a pydantic `BaseModel`, a `dataclass`, a `StrEnum`, an `ErrorSet`) has, BY
CONSTRUCTION, no possible "usage" edge (a data class calls nothing) and its naming-prefix
signal is just its own unique class name -- so a conventional, deliberate `_models.py`
catalogue of N unrelated DTOs inevitably clusters into N singleton groups, the maximum
possible fragmentation, regardless of how well-organized the file actually is. Confirmed
against this repo's own findings: `cve/_models.py` (15 classes, 0 methods),
`dup/_models.py` (11/0), `gates/_models.py` (14/0), `strata/_ast.py` (39 classes/1 method)
were exactly this shape. Fixed by excluding zero-method classes from the export/cluster
count entirely in `_export_name_and_prefix` (`frob.arch._srp`); new tests
`test_data_only_classes_are_excluded_from_god_module` /
`test_method_bearing_classes_still_count_toward_god_module` in
`tests/unit/test_arch_srp.py` pin both the fix and that method-bearing classes still
count. Live findings dropped 23 -> 11 (measured, see the table below).

**Decision: ARCH102 stays advisory (WARN), NOT promoted.** The heuristic's most severe,
audit-named unsoundness is fixed, but 11 real findings remain, all requiring an actual
module split (or an honest per-file waiver) to clear -- out of this ticket's time budget
and, for 2 of the 11 (`gates/__init__.py`, which is also `T-0976`'s ARCH001 scope),
overlapping a sibling agent's concurrent work. Promoting with 11 live findings would red
`main` immediately, which this ticket's own dispatch instructions rule out. Burn-down +
promotion tracked in a filed follow-up (draft id at write time, renumbered at land per
this doc's normal convention -- resolve via `frob ticket show` at pickup).

Remaining 11 (module, exports/clusters): `gates/__init__.py` 302/3, `gitio.py` 15/3,
`graph/__init__.py` 21/3, `graph/cache.py` 21/3, `lang/__init__.py` 22/11,
`perf/_sketch_store.py` 13/3, `render/_elements.py` 10/9, `stats/_sketch.py` 10/5,
`strata/_sysdoc.py` 13/3, `tickets/__init__.py` 111/7, `tickets/_models.py` 21/5.

### ARCH103 (mixed-concern-function) -- 24 -> 2 live, promotion blocked on 2 sites

Burned down 22 of 24 via a reasoned `frob:waive ARCH103` at each site (CLI
`frob.app.*_runner` entrypoints and best-effort I/O helpers whose whole documented job IS
the orchestration/degrade-and-log shape the check flags -- see each waiver's `reason=` in
the source for the specific argument per site). The remaining 2
(`src/frob/gates/_fmt_directives.py:288 format_paths`,
`src/frob/natives/_build.py:122 build_natives`) are BOTH in `T-0976`'s concurrent ARCH001
finding list for the same files/functions -- left untouched per this ticket's own
coordination instruction (do not refactor, and by extension do not permanently waive
either, functions a sibling agent's ticket is actively deciding extract-vs-waive on for a
different rule). **Decision: ARCH103 stays "warning" in `frob.toml`, NOT promoted this
round** (2 live findings would red `main`); promotion tracked in the same follow-up as the
2 sites, blocked on `T-0976`.

**Executed this ticket:**
- `frob.arch._python._py_is_self_attribute` (new): restricts `NormalizedFieldAccess`
  extraction to genuine `self.<field>` reads/writes, fixing the ARCH101 false-positive
  root cause. `tests/unit/test_arch.py`/`test_arch_srp.py` cover the existing suite
  (updated for the now-qualified symref shape) plus the fixed extraction.
- `frob.arch._srp._is_data_only_class` (new) + `_export_name_and_prefix` filtering: the
  ARCH102 heuristic-soundness fix, with 2 new tests in `test_arch_srp.py`.
- `frob.arch._srp.check_lcom4`/`check_mixed_concern_function`: `symref` now
  `f"{module.path}::{name}"`, matching `frob.graph.dsl._enclosing_src`'s waiver-binding
  shape -- fixes ARCH101/103 waivability (previously silently broken).
- `[gates.severity] ARCH101 = "error"` in `frob.toml` (0 live findings).
- 22 `frob:waive ARCH103 reason="..."` sites across `src/frob/app/*_runner.py`,
  `src/frob/check/_ts.py`, `src/frob/fuzz/_signatures.py`, `src/frob/gates/__init__.py`,
  `src/frob/testing/_collect.py`, `src/frob/testing/_runners.py`,
  `src/frob/tickets/_store.py`, `src/frob/vet/_nvd.py`, `src/frob/vet/_registry.py`.

**Children filed:**
- Draft id at write time (renumbered at land) -- ARCH102 burn-down + promotion (11
  findings, module list above).
- Draft id at write time (renumbered at land), `blocked_by` the real id `T-0976`
  resolves to -- ARCH103's last 2 sites + promotion.

### DOC006 (doc-pointer resolution) -- 771 -> 131 live, NOT promoted this round

T-1015 measured DOC006 (`frob.gates._docptr`, WARN since T-0437) at 771
live findings via a chunked `frob check --only docblocks --json`, clustered by
recognized-shape kind: 539 file/path, 144 config reference, 45 code symbol, 23 cli
invocation, 20 doc-anchor link. Most of the volume was matcher false positives, not
real doc drift -- fixed the matcher (`_docptr.py`), not by mass-waiving:

- **FILE/PATH shape hardening** (`_looks_like_path`): the old shape check
  (`^[\w.\-]+(?:/[\w.\-]+)+$`) matched prose that was never a path at all -- units
  ratios (`req/s`), test-permutation suffixes (`sum_twice_a/b`), enumeration/
  alternatives lists using `/` as "or" (`.ts/.tsx/.c/.cpp`, `for/while`,
  `fake/changeme/example/placeholder`), and bare protocol-less hostnames/DOIs cited in
  reference corpora (`martinfowler.com/bliki/...`, `10.1145/358198.358210`). Narrowed
  to require: no non-leading dot-segment, no hyphen-glued sentence fragments
  (`your-`/`-here`), a first segment that isn't itself a bare hostname, and either a
  file extension on the last segment or a first segment rooted at one of this repo's
  own known top-level directories (`_KNOWN_TOP_LEVEL_DIRS`).
- **FILE/PATH resolution broadening**: added directory-prefix resolution (`src/frob/
  strata` resolves if any tracked file starts with that prefix -- a real directory-only
  mention, not a bogus exact-file check) and trailing-suffix resolution (`gates/
  __init__.py` resolves against `src/frob/gates/__init__.py` -- doc prose routinely
  uses a shorter module-relative tail). Also extended the existing `.frob/` runtime-
  artifact exemption to `.git/` (git's own internal state dir, `.git/info/exclude` /
  `.git/MERGE_HEAD`, is never itself git-tracked either) and added a `root/` prefix
  alias for `root/frob.toml`-style doc phrasing.
- **CONFIG REFERENCE multi-manifest resolution**: `[section]`/`[section.key]` was <!-- frob:waive DOC006 reason="[section]/[section.key] here quotes _docptr's own illustrative placeholder shape, not a real config reference" -->
  checked ONLY against `frob.toml`, so any doc legitimately citing a `pyproject.toml`
  section (`[project.optional-dependencies]`, `[build-system]`, `[tool.pytest.
  ini_options]`) or a `Cargo.toml` section (`[package]`) was flagged as a bogus
  `frob.toml` key. Now resolves against `frob.toml` OR the root `pyproject.toml` OR any
  tracked `Cargo.toml`.
- **Scope exclusion**: `tickets-archive.md` is a verbatim historical ledger (`frob
  ticket archive` copies a closed ticket's Done report there UNCHANGED forever, per
  docs/modules/tickets.md) -- checking its historical prose against the CURRENT tree
  was the single largest cluster (154 of 349 post-matcher-fix findings, ~44%) and
  would have incentivized rewriting supposedly-immutable history to quiet a gate.
  Excluded from DOC006's doc-prose scan entirely.
- A handful of targeted `frob:waive DOC006 reason="..."` sites for the DOC006 section
  of docs/modules/gates.md's own illustrative examples (`frob edit`, `src/frob/gone.py`,
  `[bogus.section]`, `src/frob/pkg/sub/deep.py`, etc. -- deliberately fictional tokens
  quoting `_docptr`'s own module docstring) and one C++/Rust standard-grammar-clause
  citation table in docs/design/capability-evasion-taxonomy.md (19 sites: `[dcl.ptr]`, <!-- frob:waive DOC006 reason="[dcl.ptr]/[namespace.udecl] quoted here are the same ISO standard clause tags cited above, not real frob.toml keys" -->
  `[namespace.udecl]`, etc. are ISO standard clause tags, not frob.toml keys -- a
  narrow, single-doc citation convention, not a generalizable matcher shape).

Measured reduction (each step re-verified via `tests/test_docptr_gate.py` staying
green and a fresh chunked `--only docblocks --json` count): 771 -> 349 (FILE/PATH shape
hardening) -> 195 (tickets-archive.md exclusion) -> 189 (multi-manifest CONFIG
REFERENCE) -> 168 (capability-evasion-taxonomy.md waivers) -> 143 (`.git/` exemption +
domain/DOI shape rejection + `root/` alias) -> 131 (gates.md illustrative-example
waivers). **83% reduction, 771 -> 131.**

**Decision: DOC006 stays WARN, NOT promoted this round.** 131 live findings would red
`main` immediately if promoted to ERROR; the remainder is fragmented across ~30 doc
files (docs/modules/vet.md 16, docs/modules/gates.md 12, docs/modules/perf.md 8,
CHANGELOG.md 7, docs/strata/threat.md 6, plus ~25 files with 1-4 each) with no single
dominant cluster left to fix mechanically in this pass -- each remaining finding needs
its own genuine-drift-vs-illustrative disposition. Promotion tracked in the same
follow-up.

**Children filed:**
- T-1016 -- DOC006 burn-down round 2, the 131-finding remainder + eventual
  promotion decision.

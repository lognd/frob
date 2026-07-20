# Audit: quality/security detector gates

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

### Structural PII / env-secrets (`gates/_pii_structural.py`, PII010/SEC110) -- both WARN
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
**Repro:** commit `AWS_KEY = "AKIAIOSFODNN7EXAMPLE"  # frob:secret-fake` -- or any real key
whose value happens to contain `example` -- and SEC001 is silently discharged; nothing
tracks that a human vouched for it.
**Fix direction:** require `frob:secret-fake reason="..."` and route it through the same
waiver ledger as `frob:waive` so suppressions are auditable; drop the bare-substring
`example/fake` suppression in favor of the anchored template-shape/entropy checks only.

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

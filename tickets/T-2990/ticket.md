---
id: T-2990
title: 'frob refactor has no module/file move verb: symbol-scoped only, so a module
  rename falls back to hand-editing imports'
state: queued
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'record the owner directives: reuse the existing move machinery where it
    is genuinely shared rather than forking it, and require typed validated operands
    so a symbol-to-filepath move like app:run to attachments/img.jpg is structurally
    inexpressible'
  actor: logan
  at: '2026-08-26'
  old_length: 5027
  new_length: 10111
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`frob refactor` has three verbs: `move` (a SYMBOL between modules), `rename` (a
SYMBOL), and `split` (N symbols out of one module into a new sibling). There is
no verb that moves or renames a MODULE / FILE.

Confirmed missing, not merely undocumented: `frob refactor --help` lists only
those three, and a grep across `src/`, `docs/` and comments for
`move a module|module rename|rename a module|whole-module|move_module|
rename_module|file-level refactor` finds no implementation and no recorded plan.
The only mention anywhere is the note I left in T-2989.

WHY IT IS NEEDED: T-2989 renames `frob.yaml_io` -> `frob.yamlio` for io-seam
naming consistency (`gitio`, `tomlio`, and the incoming `ghio` carry no
underscore). With no module verb, that has to be expressed as a symbol move plus
manual residue cleanup, or done by hand -- and hand-editing imports is exactly
what the owner asked to avoid. Module rename/move is a common operation and the
tool should support it directly.

WHAT "FIXES IMPORTS AND CODE" MUST MEAN HERE. A module move is NOT a text
substitution, and this repo has a standing rule that checks and rewrites must
parse and compare SYMBOLS, never substrings -- a lexical match is wrong in both
directions (it matches inside comments and strings, and it misses aliases). The
verb must handle at minimum:

- `import frob.yaml_io`, `from frob import yaml_io`, `from frob.yaml_io import X`
- aliased forms: `import frob.yaml_io as y`, `from frob import yaml_io as y`
- relative imports from within the same package
- re-exports through `__init__.py` and `__all__` entries
- the moved module's OWN intra-package relative imports, which may need
  rewriting if the move changes its package depth

NON-PYTHON REFERENCES -- this is where a naive implementation will silently
break the repo, and frob is unusually exposed because it configures itself by
dotted string:

- `frob.toml` carries `module:symbol` values, e.g.
  `known_keys = "frob.gates._profile_schema:PROFILE_KNOWN_KEYS"`. A module move
  that misses these leaves the gate unable to resolve its own config. Note that
  post-T-2891 such a gate renders UNRES rather than a false `pass`, so it fails
  visibly rather than silently -- but it still breaks.
- `pyproject.toml` entry points and plugin registrations by dotted path.
- `design/*.strata` `code="<glob>"` bindings, which bind nodes to file paths.
- `frob:doc` / `frob:tests` / evidence node ids that cite FILE PATHS. Moving a
  test module orphans other tickets' evidence -- this repo has already had that
  be 4 of 4 of its error floor.
- ticket `scope` entries, which are path globs.
- docs prose and anchors.

DYNAMIC AND STRING-FORM IMPORTS: `importlib.import_module("frob.yaml_io")`,
`__import__`, and any dotted-path string resolved at runtime are invisible to an
AST import rewrite. frob itself uses `importlib.import_module` (the guarded
`fcntl`/`msvcrt` backends do). The verb must at minimum DETECT string-form
references to the moved module and either rewrite them or REFUSE with a report,
rather than completing and leaving them dangling.

ERRONEOUS-REFACTOR GUARDS (the owner asked for this explicitly). The verb must
NOT:
- rewrite a prose or string occurrence that merely contains the module name
  (a docstring discussing YAML I/O generally; a log message; a test fixture
  containing the literal text);
- corrupt a DIFFERENT module sharing a prefix -- `frob.yaml_io` must not rewrite
  `frob.yaml_io_extra` or `frob.yaml_iomodel`. Substring-prefix collision is the
  classic failure here;
- leave the tree half-moved. `src/frob/refactor/_transaction.py` already exists
  and is the precedent -- the move must be transactional and roll back cleanly
  on failure;
- lose git rename detection. Prefer `git mv` so history and blame follow the
  file.

VERIFICATION, matching what the existing verbs already do: run the
`frob check --delta` post-condition and the pytest collect rather than skipping
them, and add a post-condition specific to this verb -- ZERO surviving
references to the old dotted path anywhere in the repo (code, config, docs,
tickets, design), since a partial rename is the whole failure mode.

ACCEPTANCE
- A `frob refactor move-module` (or equivalently named) verb exists and is
  documented in `--help` and the command docs.
- Must-fire fixtures, each proving a rewrite actually happens: plain import,
  aliased import, `from X import Y`, relative import, `__init__` re-export, and
  a `frob.toml` dotted-string reference.
- Must-NOT-fire fixtures, each proving no erroneous rewrite: a prefix-colliding
  sibling module that must be left untouched, and a string/comment occurrence of
  the name that is not a reference.
- A dynamic `importlib.import_module("<old path>")` is either rewritten or
  reported as an unhandled reference -- never silently left broken.
- Failure mid-move rolls back to a clean tree.
- Proven end-to-end by using the new verb to perform T-2989 (`frob.yaml_io` ->
  `frob.yamlio`), with `git grep -c "yaml_io"` returning 0 afterwards.

REUSE THE EXISTING `move` MACHINERY -- yes, and here is the shape.

The owner asked whether the existing `move` verb can be reused. It should be,
but NOT by naively composing N symbol-moves. The distinction matters:

REUSE (these are the hard parts, they exist, they are tested, and duplicating
them would violate this repo's own no-duplication rule -- two copies of a
rewrite rule is a bug waiting to desync):
  - the reference-rewriting engine that `move` already uses to find and rewrite
    every call site;
  - `--alias-conflict` policy handling;
  - the transaction/rollback in `src/frob/refactor/_transaction.py`;
  - the `frob check --delta` post-condition and the pytest-collect check;
  - `--full-repo-collect` / `--skip-check-delta` flag semantics, so the new verb
    behaves like its siblings rather than inventing its own contract.
Factor the shared core so both verbs call it. Do not fork it.

DO NOT simply loop `move` over every symbol. A module move is not the sum of its
symbol moves, and the gap is exactly where the bugs would live:
  - `import frob.yaml_io` and `from frob import yaml_io` reference the MODULE,
    not any symbol in it. A symbol-by-symbol loop never sees them.
  - Module-private symbols (`_coverage_tracer_active` in the T-2989 case) are not
    part of a public-surface move but must travel with the file.
  - The module docstring, `__all__`, and any module-level side effects have no
    symbol to hang off.
  - N symbol moves leave an empty husk that then has to be deleted separately;
    git then records delete+create and rename detection is lost, so blame and
    history stop following the file. Prefer `git mv` for the file itself so
    history survives, then rewrite references.
  - The non-Python references listed above (frob.toml dotted `module:symbol`
    values, `.strata` `code=` globs, `frob:doc`/`frob:tests` path citations,
    ticket `scope` globs) are keyed on the MODULE PATH. A symbol move does not
    change a file path and so has no reason to touch them; a module move does
    and must.

So: new verb, module-aware, delegating to the shared rewrite core for the parts
that are genuinely the same. If on inspection the existing core turns out to be
too symbol-shaped to factor cleanly, say so with specifics rather than forcing
it -- a bad abstraction shared between two verbs is worse than two clear
implementations, and that is a judgement worth reporting rather than guessing at.

OPERAND SEMANTICS -- TYPED, VALIDATED, AND REFUSED LOUDLY. This is a direct
requirement from the owner and it is the main risk created by sharing machinery
between the verbs. Today `move` takes `MODULE:QUALNAME -> MODULE:QUALNAME`. A
module verb takes a different operand kind. If both funnel into one shared core
without typed operands, nothing structurally prevents nonsense like:

    frob refactor move app:run attachments/img.jpg

-- a symbol reference on the left, an arbitrary file path on the right. That
must be IMPOSSIBLE to express, not merely unlikely to be typed.

Required:
- Operand kinds are DISTINCT TYPES, not strings: a symbol reference
  (`module:qualname`), a module reference (dotted path), and a file path are
  three different things. Parse each operand into its kind up front and let the
  type system carry it, rather than passing raw strings into a shared rewriter
  that guesses.
- Each verb DECLARES the operand kinds it accepts, and mismatches are refused
  with a named, typed error naming both the expected and the received kind.
  `move` (symbol) must reject a module or file operand; the module verb must
  reject a `module:qualname` operand. Per the house rule these are recoverable
  user errors, so they are Result values, not exceptions and not tracebacks.
- The DESTINATION must be validated as a legal Python module location before
  anything is written: inside a declared source root, an importable package
  path, a `.py` file, and a valid Python identifier per path segment. A
  destination under `attachments/`, a non-`.py` extension, a path outside the
  source roots, or a segment that is not a valid identifier is refused.
- Collision is refused, not silently merged: a destination module that already
  exists must error unless an explicit policy flag says otherwise, consistent
  with how `--alias-conflict` already handles the symbol case.
- Refusal happens BEFORE any file is touched. A validation failure must leave
  the tree byte-identical -- not roll back, simply never start.

Must-not-fire fixtures required for each of these, because a guard with no
must-fire case is indistinguishable from an absent guard:
  - symbol operand given to the module verb -> refused, tree untouched;
  - module operand given to `move` -> refused, tree untouched;
  - destination with a non-`.py` extension (the `attachments/img.jpg` shape)
    -> refused, tree untouched;
  - destination outside the declared source roots -> refused;
  - destination path segment that is not a valid Python identifier -> refused;
  - destination module already exists -> refused absent an explicit policy flag.

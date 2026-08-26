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

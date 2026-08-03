# frob refactor: transactional move/rename/split (T-1135 design)

<!-- frob:waive DOC006 reason="design proposal (T-1135) for a not-yet-built CLI verb -- every `frob refactor` mention in this file names the proposed future command, not a shipped subcommand" -->
One sentence: a new `frob refactor` verb that moves/renames/splits a Python
symbol or module and rewrites every frob-owned reference and every prose
mention atomically, refusing and rolling back rather than leaving a
half-done move.

## Why this exists

Today a refactor is a human hand-editing imports and call sites, plus --
the actually expensive part -- hand-carrying frob's own symbol-attached
bookkeeping: `frob:tests`/`frob:doc`/`frob:enforces` targets, waiver
symrefs (including `path::qualname` forms), PII012's `(file, token)`
allowlist keys, check-coverage registry `handled_by` citations, and
archived-ticket evidence node ids. Every one of these has bitten this
drive concretely:

- 3 coordinator INV006 waiver carries in one wave (commit `0abc4e3a`).
- PII012 allowlist re-keying on every move (T-1076).
- The ARCH101/103 waiver-symref `path::` bug: a waiver placed above a
  specific symbol stops matching the moment that symbol moves, because
  the match is keyed on `(file, qualname)` pairs that a move invalidates
  (see `src/frob/gates/_waive.py`'s `_match_waiver` commentary, lines
  ~1205-1240, for the three existing matching modes this design must not
  regress).
- Archived evidence repoints after litmus renames (commit `8dae48c5`).
- DRIFT002 edge repoints, generally: any `frob:doc`/`frob:uses-contract`
  edge whose target textually names a `path::qualname` that a move just
  invalidated.

<!-- frob:waive DOC006 reason="design proposal (T-1135) -- names the not-yet-built future verb" -->
`frob refactor` closes this by making the move ITSELF the unit of work:
one command, one transaction, one disclosed report -- never a chain of
manual greps.

## Survey: what already exists to build on (read before designing further)

frob already owns the three substrates a rewrite engine needs. This
design adds a **rewrite orchestration layer on top of them**, not a
parallel graph/parser/edge model.

1. **`frob.lang`** -- the five-language parser front end (`RawSymbol`,
   `RawComment`, `ParsedFile`, `SymbolKind`). Already used by every gate
   and by `frob.graph` to get symbol boundaries and comment text. The
   refactor verb's Python-first scope means it drives this the same way
   `frob.graph.build_graph` does today: parse, get symbol spans, get comment
   text -- but Python only for v1 (see "Language boundary" below).
2. **`frob.graph`** -- the indexed symbol+edge graph.
   - `frob.graph.dsl` (`_VERB_TABLE`, `_LINE_RE`, `_ATTR_RE`) is the
     canonical parser/serializer for every `frob:<verb> <target>
     key="value"` directive line, across all 5 languages' comment
     syntax. The rewrite engine reuses this parser to find every
     directive whose TARGET names a moving symbol -- it must not write
     a second regex for the same grammar.
   - `frob.graph._models.Edge`/`EdgeKind`/`GraphSnapshot` is the typed
     edge model already keyed on `(src, target, kind)` triples where
     `src`/`target` are `path` or `path::qualname` symrefs. This is
     exactly the reference-kind inventory item 2 below needs to walk.
   - `frob.graph.affects.affects()` already answers "what must review
     when X's digest changes" via a bounded `uses-contract` closure
     walk. The refactor verb's own transitive-impact scan (which
     `frob:doc`/`frob:tests`/`frob:uses-contract` edges point at a
     moving symbol, directly or through a chain) is the SAME closure
     shape over the SAME `GraphSnapshot` -- reference-rewrite engine
     should call into (or refactor out a shared helper from)
     `frob.graph.affects`, not re-walk edges independently.
   - `frob.graph.callgraph.build_reference_graph`/`closure` already
     resolve private-helper call sites within a file/package. Import
     rewriting for PUBLIC symbol references is a different problem
     (module-qualified `from x.y import z` / `x.y.z(...)` sites found
     via `frob.lang` token scan, not this call graph) but private-helper
     callers moving along with a symbol inside the same package can
     reuse this resolution.
   - `frob.graph.lock` (`frob.lock`, tracked) holds acks keyed on
     symbol identity+digest. A move changes a symbol's `path::qualname`
     identity without changing its digest -- the ack-carry rule (item 2)
     is: same digest at the new symref inherits the ack, key renamed not
     invalidated.
3. **`frob.exports`** (generated `__init__.py`) and **`frob.bind`**
   (pybind11/PyO3 BIND-comment verification) are the two existing
   "generated surface must track the source" mechanisms; the refactor
   verb's own re-export shim generation for a split (see child 4) is a
   third instance of the same idea and should read `frob.exports`'
   existing generation logic before inventing new codegen.
4. **`frob.registry`** (`_corpus.py`, `_models.py`, `_staleness.py`) and
   `frob.gates._registry_exhaustiveness` (REG004-011) own the
   `handled_by`/`caught_by` citation model in `docs/design/registry/
   *.yaml`. These citations reference concept ids, not symrefs directly,
   but `_reg008_undeclared_enforcement`/`_reg009_phantom_enforcement`
   cross-check against code-declared `frob:enforces` edges -- so a
   moved `frob:enforces` directive (covered by the directive carrier,
   child 2) transitively keeps the registry citation correct as long as
   the directive target it's checked against was rewritten. No separate
   registry-YAML text rewrite is needed UNLESS a registry entry embeds a
   literal `path::qualname` string outside a `frob:enforces` edge --
   survey during child 3's implementation, not assumed here.
5. **`frob.gates._waive`** (`_match_waiver`, `_UNWAIVABLE_RULES`) is the
   waiver-matching spine with its three documented matching modes
   (per-symbol exact symref, file-scoped, package/system-prefix). The
   directive carrier (child 2) must preserve all three: a waiver's `src`
   is itself a symref/path that needs rewriting exactly like a
   `frob:doc` target does.
6. **T-1072/T-1077 "family-extraction pattern"** (the precedent for
   child 4's split verb): a cohesive family of code is pulled into a
   new private sibling module; the OLD module re-imports and
   re-exports every moved name UNCHANGED (so external `from frob.gates
   import x` call sites never need to change); `frob:*` directives
   travel with the moved code; DRIFT002/AFFECT001 doc/test references
   to the old module path get updated; land incrementally, verified by
   the full test suite after each chunk.
<!-- frob:waive DOC006 reason="design proposal (T-1135) -- names the not-yet-built future verb" -->
   `frob refactor split` is this
   exact manual playbook made mechanical and atomic, plus the
   directive/registry/evidence carrying this design adds on top.
7. **No existing rename/move verb.** `frob.mutate` is mutation testing
   (unrelated name collision, not to be confused with this work).
<!-- frob:waive DOC006 reason="design proposal (T-1135) -- names the not-yet-built future verb; docs/commands/refactor.md is explicitly noted as not yet added" -->
   `frob refactor` is new CLI surface (`docs/commands/refactor.md` to
   be added by child 1), following the existing `docs/commands/*.md`
   per-command doc convention (see `check.md`, `exports.md`, etc.).

## Transaction model

`frob refactor {move,rename,split} ...` runs as a single in-process
transaction over a throwaway working copy of the repo state (or an
explicit git worktree scratch branch -- decision: **use the caller's own
git worktree with an isolated scratch commit**, not a separate temp
checkout; git already gives us cheap `stash`-free rollback via `git
reset --hard <pre-refactor-sha>` scoped to `HEAD~1` since section 1b of
the agent playbook forbids `git stash` repo-wide, so the transaction
commits its own WIP as it goes and rolls back via `git reset --hard` to
its own pre-transaction commit if it must abort, never by touching
`refs/stash`).

Phases, each of which can abort the whole transaction:

1. **Resolve.** Parse the move/rename/split target(s) via `frob.lang` +
   `frob.graph`, confirm the symbol(s) exist and are unambiguous. Refuse
   immediately (no writes yet) if the target does not resolve, or if a
   destination path/name already exists and no `--alias-conflict` policy
   (see below) was given.
2. **Plan.** Build the full rewrite plan BEFORE touching any file:
   - every import/call-site rewrite (absolute-import form; new alias if
     the destination name collides with something already imported at
     the call site).
   - every frob-owned reference rewrite (item-2 inventory below), each
     with its exact old-target -> new-target string.
   - every prose-rewrite candidate (item-3 scope below), each flagged
     resolvable or unresolvable up front.
   This plan is the disclosed report's spine -- computed once, applied
   once, never re-derived mid-apply.
3. **Apply.** Execute the plan: move/rename the actual code (AST-level
   move preserving formatting outside the moved span, not a full
   reformat), rewrite import/call sites, rewrite every frob-owned
   reference, rewrite every resolvable prose mention. Commit as one WIP
   commit in the caller's worktree (per the playbook's own "commit your
   WIP, never stash" discipline).
4. **Verify post-conditions, in-command, before declaring success:**
   - import graph resolves (`frob.graph` rebuild + `frob cycle`-style
     import-resolution check finds no new unresolved import).
   - `pytest --collect-only` succeeds repo-wide (or over the affected
     test files at minimum -- decision needed, see open questions) with
     no new collection error.
   - `frob check --delta` against a pre-refactor baseline stamp is
     diff-clean: the refactor introduces exactly zero NEW gate findings
     (a finding that existed before the move, at the old location, and
     still exists after, at the new location, is not "new" -- it is the
     same finding, symref-renamed; the diff must be identity-aware, not
     a raw count).
5. **Commit or rollback.** Any phase-4 check failing rolls the whole
   transaction back (`git reset --hard` to the pre-transaction commit
   inside the caller's own worktree) and prints the disclosed report
   with every attempted rewrite and exactly why it could not complete.
   Success prints the same report shape, marked complete, plus the alias
   report (every auto-generated import alias, so a human can spot an
   ugly one) and the list of any unresolvable prose mentions (never
   silently dropped -- named explicitly, per the epic's acceptance [2]).

## Reference-kind inventory (must move with the symbol)

Every one of these is a `(old_symref_or_path) -> (new_symref_or_path)`
string substitution site the rewrite engine must enumerate and rewrite,
sourced from the substrate above:

| Kind | Where it lives | Substrate to query |
|---|---|---|
| Python imports/call sites | any `.py` file | `frob.lang` token scan + `frob.graph.callgraph` for private-helper resolution |
| `frob:doc` targets | comment DSL | `frob.graph.dsl` parse, `EdgeKind.DOC` |
| `frob:tests` targets | comment DSL (in test files) | `frob.graph.dsl`, `EdgeKind.TESTS` |
| `frob:enforces` targets | comment DSL | `frob.graph.dsl`, `EdgeKind.ENFORCES` |
| `frob:uses-contract` targets | comment DSL | `frob.graph.dsl`, `EdgeKind.USES_CONTRACT` |
| `frob:invariant`/`frob:ticket`/`frob:todo`/`frob:decision`/`frob:channel`/`frob:boundary`/`frob:secret`/`frob:protocol`/`frob:transition`/`frob:requires`/`frob:acquire`/`frob:release`/`frob:escapes` | comment DSL | same parser, every `EdgeKind` whose target or `src` can embed a moving symref |
| `frob:waive RULE reason="..."` symrefs, incl. `path::qualname` | comment DSL, `src` field | `frob.gates._waive._match_waiver`'s 3 modes -- must preserve per-symbol vs file-scoped vs package-prefix matching after rewrite |
| PII012 `(file, token)` allowlist entries | `frob.gates._pii_structural` allowlist (wherever keyed -- confirm exact storage at implementation time) | keyed on file path; a move changes the file half of the key |
| check-coverage registry `handled_by`/`caught_by` citations | `docs/design/registry/*.yaml` | `frob.registry._corpus`/`_models`, cross-checked by `frob.gates._registry_exhaustiveness` against `frob:enforces` edges |
| archived-ticket evidence node ids | `tickets.md`/`tickets-archive.md` evidence lines (`path::Class.method` / pytest `::` form) | ticket ledger text, both live and archived |
| `frob.lock` ack entries | `frob.lock` (tracked) | `frob.graph.lock`, keyed on symbol identity+digest -- same digest at new symref carries the ack forward, never re-flagged stale by the move itself |

The directive/waiver carrier child (T-1199) owns every DSL-target row;
the registry/evidence repointer child (T-1200) owns the registry-YAML
and ticket-ledger rows; the reference-rewrite engine child (T-1197) owns
the Python import/call-site row and is the shared substrate (parse +
plan + apply + verify machinery) the others are built on top of, not
parallel to; the prose/doc-anchor carrier child (T-1267) owns every row
in the "Prose-rewrite scope" section below -- free text is NOT a DSL
target and is NOT covered by T-1199.

## Prose-rewrite scope

Distinct from the frob-owned DSL rewrite above -- this is free text that
happens to NAME a moved symbol. Owned in full by the prose/doc-anchor
carrier child (T-1267), not by the directive carrier (T-1199), which
only rewrites structured `frob:*` DSL directive targets:

- Docstrings and comments naming the dotted path, anywhere in the repo
  (not just attached to the moved symbol) -- e.g. "see `frob.gates.
  _waive._match_waiver` for..." in an unrelated module.
- `docs/**` prose and embedded code references (fenced code blocks
  citing the old import path, prose sentences naming the old module).
- Doc anchor slugs whose heading text embeds the symbol/module name
  (e.g. `#inv006-t-0408` style anchors already keyed on gate id, but a
  heading literally titled with a module name changes its slug on
  rename) -- checked against `frob.gates._doclink_docanchor`'s
  `doclink_gate`/`docanchor_gate` (DOC001/DOC002) as the post-condition
  proof that no anchor broke.
- Every `frob:` comment-DSL directive TARGET anywhere in the repo that
  names the moved symbol, even on a directive whose OWNING symbol is
  not itself moving (epic acceptance [2]'s explicit scope -- this is
  broader than the reference-kind inventory above, which only covers
  edges attached to code that travels; this row is "any other file's
  directive that merely points at the moved thing"). This particular row
  is structured DSL text, not prose, so it is T-1199's to rewrite even
  though it shares this section's "anywhere in the repo, not just on the
  moved symbol" scope with the free-text rows above.

Unresolvable prose (ambiguous natural-language mention, a name that is
also a common English word, a mention inside a generated/vendored file)
is listed explicitly in the disclosed report as "not rewritten -- review
by hand", never silently skipped and never silently rewritten on a
guess.

## Alias-conflict policy

When a moved/renamed symbol's name collides with something already
bound at an import site:

- Default: auto-generate an import alias (`import x.y as y2`-style,
  exact scheme TBD by the alias-conflict policy child) at the colliding
  call site only; the destination module keeps the symbol's real name
  unaliased.
- Every auto-generated alias is named in the disclosed report (the
  "alias report" the epic's acceptance [0] requires) so a human reviews
  it rather than discovering it later via a confusing diff.
- A destination-name collision (two symbols with the same name landing
  in the same module, e.g. a `split` moving something into a module
  that already defines a same-named symbol) is a HARD refusal, not an
  auto-alias -- the destination module's own namespace is not something
  the tool silently renames into. `--alias-conflict {error,rename-dest}`
  flag: default `error`; `rename-dest` is an explicit opt-in escape
  hatch for the rare deliberate case.

## Python-first / multi-language-later boundary

v1 operates on Python source only: symbol resolution via `frob.lang`'s
Python grammar, import rewriting via Python's `from x import y` / `import
x.y` forms only. The comment-DSL rewrite (directive carrier) already
works across all 5 languages today (the DSL parser is language-agnostic
by construction, per `frob.graph.dsl`'s own docstring) -- so directive
rewriting is NOT gated on the language boundary the same way import
rewriting is; a directive attached to a Rust/TS/C++/Kotlin symbol that
merely NAMES a moved Python symbol in its target is in scope for v1's
directive rewrite even though moving a Rust/TS/C++/Kotlin symbol itself
is not. Binding tables (`frob.bind`'s BIND comments joining a Python
symbol to its pybind11/PyO3 native counterpart) are explicitly OUT of
v1's move/rename mechanics -- moving a Python symbol that has a native
BIND counterpart is a disclosed unresolvable-prose-class case in v1
(the BIND comment itself is flagged, not silently rewritten), with full
multi-language extension tracked as explicit follow-on epic scope, not
built here.

## Children filed (see ticket list in the Done report)

1. Reference-rewrite engine (shared substrate: resolve/plan/apply/verify
   pipeline, Python import+call-site rewriting, transaction/rollback
   machinery, post-condition verification).
2. Directive/waiver carrier (absorbs T-1134's reusable
   `find_carried_waiver` helper; rewrites every `frob:*` DSL target and
   `frob:waive` `src` symref, preserving `_match_waiver`'s 3 matching
   modes; carries `frob.lock` acks by digest).
3. Registry/evidence repointer (PII012 allowlist re-keying, registry
   YAML citation check, ticket-ledger evidence node id rewriting for
   both live `tickets.md` and `tickets-archive.md`).
4. Split verb (built on the T-1072/T-1077 family-extraction pattern:
   re-export shim generation so external call sites see no change,
   incremental per-chunk verification).
5. Alias-conflict policy (the `--alias-conflict` flag, alias-naming
   scheme, disclosed alias report format).
6. Prose/doc-anchor carrier (docstring/comment mentions repo-wide,
   `docs/**` prose and embedded code references, doc-anchor heading-slug
   rewriting, and the disclosed unresolvable-mentions report -- epic
   acceptance [2]'s three prose-rewrite items, distinct from child 2's
   structured DSL-target rewrite).

Dependency order: 1 is the foundation every other child calls into; 2,
3, and 6 all depend on 1's plan/apply/verify pipeline existing (they
extend its reference-kind inventory, not re-implement transaction
mechanics); 5 is a policy layer that 1 must expose an extension point
for, so 5 depends on 1 too; 4 (split) is the highest-level verb, built
last, depending on 1+2+3+6 all being usable underneath it for a split's
own reference/directive/registry/prose carrying -- a split is a move of
many symbols at once, so it needs prose mentions carried too, the same
as a single move/rename does.

## Open design questions for the coordinator

- Post-condition `pytest --collect-only` scope: full repo-wide collect
  (safest, matches the epic's acceptance wording literally) vs. only
  files touched by the plan (faster, matches the playbook's "run only
  your own changed test files" dispatch discipline in section 6b). This
  design assumes full repo-wide for now since the epic's acceptance [1]
  says "tests collect" unqualified, but this is worth an explicit
  coordinator call before child 1 locks its interface, since it affects
  child 1's own runtime budget under the 120s foreground cap discussed
  in the playbook.
- Where PII012's allowlist is actually persisted (module-level constant
  vs. a tracked data file) was not pinned down exactly during this
  design pass -- child 3's own plan should open by locating it exactly
  (`src/frob/gates/_pii_structural/` was the closest hit found) before
  writing the repoint logic.
<!-- frob:waive DOC006 reason="design proposal (T-1135) -- names the not-yet-built future verb" -->
- Whether `frob refactor`'s scratch-transaction commit should be a
  distinct git commit the caller keeps (visible history of "the
  refactor's own WIP") or squashed away once verified -- affects how
  child 1's rollback recipe interacts with the playbook's own "one
<!-- frob:waive DOC006 reason="design proposal (T-1135) -- names the not-yet-built future verb" -->
  clean commit per ticket" convention when `frob refactor` itself is run
  BY an agent mid-ticket rather than by a human directly.

# Rule authoring: how it works today, and the simplest design

Date 2026-10-06. Read-only study of <frob-v2> (HEAD 91fbe9548, branch experimental).
All citations are path:line against the working tree. ASCII only.

## 0. Honesty block (denominator and coverage)

- Universe: 82 registered rules. 49 frob (docs/reference/rules has 49 pages), 32 grimble
  (21 MDL in crates/grimble-model/src/rule_defs.rs, 11 SYS in crates/grimble-bind/src/rule_defs.rs),
  1 crunk (COLOR001). Declared at 52 attribute sites in 19 files (50 direct `#[rule(` plus the two
  macro_rules templates `mdl_rule!` and `sys_rule!` that stamp out 32 rules).
- Read: every declaration file; every product wiring (frob-check/product.rs, grimble-check/product.rs,
  crunk-check/product.rs, gob-check pipeline/filecheck/repo/status/product); gob-macros derive;
  gob-rules meta/registry; gob-mdtest coverage; gob-dev render/rules + link anchor; gob-symbols adapter
  capability code; GRL AST/catalog/plan IR; design docs rules.md, testing.md, plugins.md, packs.md (3.1-3.2),
  grl-spec.md (2, 7.3, 9, 12), universal-model.md (4.1, 4.2, 4.4, 8), code-model.md 3, notes/research/codegen-macros.md
  (head and structure; the full 40 KB was skimmed, not line-read), tickets ~D3ZK8NM ~67J8R53 ~0H3WYTR ~JMDMEKV
  ~7WRK7XC plus ~YPRBJPF ~4CNF0P9 ~VB2EYG6 ~T5H07H5 ~HDFYHNJ ~JY79XVV ~NCZA04W and the parent's children list.
- NOT verified (nothing was built or run; read-only): (a) that a proc macro can read a sibling .md via
  CARGO_MANIFEST_DIR and still have cargo track it through an emitted include_str! (expected yes, it is
  how many crates embed files; spike S1 proves it); (b) const-fn string `contains` loops at the MSRV in use;
  (c) that host-trait-generic rule impls compile cleanly through `Snapshot<P>` (spike S1);
  (d) per-rule evaluation cost versus today's fused group evaluation (ticket ~AKMV3C3 says file-rules already
  dominate a cold run: 20 s of 29 s).
- Pending/blocked nodes: none in the research. Unstudied by choice: the other inventory registries
  (ConfigTable, Command, Directive, Artifact, Adapter, Frameworks) and the GRL executor; only their
  interaction with rules is discussed.

---------------------------------------------------------------------------------------------------

## 1. How it works today

### 1.1 One rule = information in up to eight places

Per rule the current code spreads these facts across files and crates:

| Fact | Where it lives today |
|---|---|
| metadata (id, slug, severity, polarity, scope, must_measure, version, since, doc) | `#[derive(Rule)]` + `#[rule(..)]` on a marker struct, in the family crate |
| evaluation | a free function in the same or another crate, found by convention only |
| wiring | a `RepoGroup::new("name", vec![X.meta(), ..], closure)` or a `FileCheck::rules()` vec in the PRODUCT crate |
| applicability | a string-id match in gob-check, plus an `if meta.id == ".."` chain in the product, plus per-product tables |
| subject count | a `.counting(|s| vec![("COV001", n)])` closure in the product |
| docs | generated into docs/reference/rules/ID.md by gob-dev from META + a corpus found by FILENAME |
| tests | tests/mdtest/<lowercase id>.md plus a hand-written per-crate runner |
| coverage | a shrink-only allowlist file naming gaps (crates/gob-mdtest/coverage-allowlist.toml, 59 entries) |

The connection between declaration and evaluation is: by TYPE inside the rule crate (`&Todo001` handed to
`Finding::new` helpers, `Todo001.meta()`), by STRING id everywhere else (see 1.6 item 3), and by NOTHING at
the point that matters: nothing proves a declared rule is ever evaluated.

### 1.2 Declaration mechanics

- Derive: crates/gob-macros/src/lib.rs (RuleArgs at :60-80; validation :150-205; expansion :207-255;
  doc :258-266). Generates `impl X { pub const META: RuleMeta }`, `impl Rule for X { fn meta }` and an
  `inventory::submit!(RuleEntry::new(&X::META))` (:250).
- Required attrs: id, slug, family, severity, tier, scope, fix, version. Defaulted: `product = "frob"` (:82),
  `since = "2.0.0"` (:86), `polarity = Pplus` (:183, silently), `must_measure = false`.
  So polarity is omitted at 23 of the 51 sites and must_measure at 44; `product` is omitted at 48 sites, which
  is why docs/reference/rules shows `product | frob` on all 49 pages including neutral gob-check/gob-config/
  gob-directives rules.
- RuleMeta: crates/gob-rules/src/meta.rs:85-110. `Rule` trait is only `fn meta()` (crates/gob-rules/src/lib.rs:34).
  There is no evaluation method on any rule type.
- Which META fields have behavior: `id`/`version` (cache key, crates/gob-check/src/filecheck.rs:272-278),
  `product` (Product::includes, crates/gob-check/src/product.rs:173), `must_measure` (pipeline,
  crates/gob-check/src/pipeline.rs:371-380), `family` (fidelity roll-up). `tier`, `scope`, `fix`, `polarity`,
  `since` have NO behavior: they are read only by gob-dev docs rendering (crates/gob-dev/src/render/rules.rs:99-108).
  Proof for tier: grep of `Tier::`/`.tier` outside gob-macros finds only render/rules.rs:52-53 and test fixtures.
  `scope` does not choose the evaluation path either: a rule declared `scope = File` is a file rule only
  because someone put it in `ObligationFileCheck::rules()`.
- Polarity: the evaluator that applies the polarity table exists (crates/gob-ir/src/eval/program.rs:297-411)
  but no Rust rule uses it; Rust rules decide fire/clean themselves (design rules.md 2 promised the framework
  would apply it).

### 1.3 Inventory of evaluation shapes (the real count is eight)

| # | Shape | Rules | Evaluation site | Wiring site |
|---|---|---|---|---|
| A | per-file, cached | TODO001 DOC001 DOC002 REF001 | frob-obligations/src/lib.rs:148-161 `file_rules` (one fused call) | frob-check/src/filecheck.rs:96-146 `ObligationFileCheck`; metas listed again at frob-obligations/src/lib.rs:164 and filecheck.rs:98-103 |
| B | repo group, cached per rule | COV001 TODO002 INV001 INV002 (obligations); DRIFT001-003 AFFECT001 (ack); TEST001; PM034 PM001 PM002; PM013; PM033; REL001; REL002; REL003; TICK001/3/4/5 | closures calling crate fns (frob-check/src/product.rs:332-410, helper fns :139-290, :620-720) | `Frob::repo_groups` (product.rs:332) |
| C | repo group, grimble | MDL000-MDL020 via `check_model`; SYS001-011 via grimble-bind | grimble-model/src/rules.rs:57 `check_model`; grimble-bind/src/lib.rs (binding computed in `collect`) | grimble-check/src/product.rs:197-232; id lists by FILTER (`model_rules()` :80 filters family == "MDL" plus `DIRECTIVE_RULES` const :74; `binding_rules()` :91 filters `grimble_bind::RULES` :58) |
| D | repo group, crunk | COLOR001 | crunk-check/src/rules/color001.rs:70-140 | crunk-check/src/product.rs:59 `vec![color001::group()]` |
| E | neutral repo group, all products | PROC001 | declared gob-check/src/rules.rs:13, scanned in gob-exec/src/proc001.rs:44 (own WalkDir over crates/*/src), group built in gob-check/src/repo.rs:121,157 | appended by the pipeline (repo.rs:172) |
| F | ticket-scoped | SCOPE001, TICK002, REL003 (missing-fragment part) | frob-lease/src/rule.rs:32; frob-check/src/scope.rs; product.rs:634 | `Frob::scoped_rules` (product.rs:444) |
| G | stage-emitted (no check function: the finding is stamped by a pipeline stage or a tool parser) | PARSE001 DSL001 DSL002 (gob-directives/src/scan.rs:196-223, in `collect`); READ001, PERF001 (gob-check/src/pipeline.rs:255,163); TOOL001 (tools.rs:340); TOOL002, CI001 CI003 CI006 CI007 CI010 CI014 (tool_parse.rs id maps, 15 string ids); SIB001 (frob-check/src/sibling/mod.rs:243); EXC001/003/005/007 (exceptions stage); CFG001 (frob doctor, frob/src/doctor.rs:384); COV003 (never emitted alias of TEST001, rules.rs:~44) | 26 rules | none: they only need a declaration |
| H | standalone duplicate of A+B | the same obligation rules | frob-obligations `evaluate()` (lib.rs:278) and `gate_file` (:174-225) re-implement the pipeline's subject_status gating for tests and tools | n/a |

So about a third of the rules (shape G, 26 of 82) have no evaluation function at all; any design that requires
`impl Check for X` on every rule would fail for them (flagged in Design 2.4).

### 1.4 Registration, selection, and the touchpoint count

Registration is link-time `inventory` (gob-rules/src/meta.rs:143). Selection is NOT registration:
the registry says what exists, the product's `repo_groups()`/`file_checks()` say what runs. A rule can be
registered, documented, "covered", and never run. Nothing checks it. (Evidence: COV003 is registered and
documented but never emitted, by design; the same hole would swallow a forgotten group.)

`Product::includes(meta)` = `meta.product == name` (gob-check/src/product.rs:173). It is used for `--only`
validation and for choosing must_measure rules (pipeline.rs:371). Because 48 sites default `product = "frob"`,
grimble and crunk runs never count the neutral rules (PROC001) for must_measure; frob does.

Link-time pitfall, observed in this repo: crates/gob-dev/src/lib.rs:48-67 `link_inventories` calls
`crunk_spec::OWN_TABLES.len()` purely as a linker anchor, and gob-dev does not depend on crunk-check,
grimble-model or grimble-bind at all (crates/gob-dev/Cargo.toml has only crunk-spec). Consequence, verified:
docs/reference/rules/ has NO COLOR001, MDL* or SYS* page (82 rules registered, 49 pages), and no test fails.
Duplicate ids are found only at runtime (`Registry::verify_unique`, called from gob-product/src/lib.rs:38 and
three tests).

Touchpoints to add ONE rule today (measured from the commits that added a rule, then enumerated):

frob file-scope rule in frob-obligations (9 hand edits, 3 crates + generated docs):
1. struct + attrs in rules.rs; 2. evaluation fn in a module; 3. call in `file_rules` (lib.rs:156);
4. `file_rule_metas()` array whose length is a const generic `[_; 4]` (lib.rs:164);
5. `ObligationFileCheck::rules()` (frob-check/src/filecheck.rs:98); 6. `side_input`/`examines` arms keyed
by string id (filecheck.rs:109-131) when it reads a ledger or links; 7. `need_of` arm (gob-check/src/status.rs:66-75)
when it needs a capability or reads comments, else it is silently "always examined";
8. `Frob::applicable` branch when it has a precondition (frob-check/src/product.rs:511-582);
9. `pub use` in lib.rs:87 and frob-check/src/lib.rs:45-52; plus 10. tests/mdtest/<id>.md and
11. generated docs page + README row (committed) and possibly 12. an allowlist entry.

frob repo-scope rule (PM013, commit 150825fa6): 8 files: product.rs (+27), rules/mod.rs, wip.rs (declaration + evaluation),
tests/corpus.rs (+22: the runner is a hand-written dispatch), tests/mdtest/pm013.md, docs page, README row,
changelog fragment. Plus, had it been must_measure, a `.counting` entry and an `applicable` arm.

grimble rule: a `mdl_rule!`/`sys_rule!` invocation (rule_defs.rs), the evaluation inside `check_model`/grimble-bind,
the `RULES` const (`[&str; 11]`, a length that must be edited, grimble-bind/src/lib.rs:58), `DIRECTIVE_RULES`
for relayed ids (grimble-check/src/product.rs:74), a `declare_not_applicable` tuple plus `sysNNN_inapplicable`
fn (grimble-bind/src/lib.rs:111-135), allowlist entry (32 grimble rules have no corpus). About 6 edits.

crunk rule (COLOR001, commit 0d06692ec, 10 files): rules/color001.rs (declaration + group + evaluation +
a local `meta()` that does `Registry::global().by_id("COLOR001")` at :50 and a local `rule_id()` at :56),
rules/mod.rs, product.rs (`repo_groups`), lib.rs, Cargo.toml (deps), tests/color001.rs (runner),
tests/mdtest/color001.md, allowlist, a frob conformance test. No docs page (see above). About 7 edits.

### 1.5 Applicability today

There is no applicability declaration on the rule. `Tier::{Universal,Lang}` is documentation only and `Lang`
carries no language. Applicability is computed by FOUR independent mechanisms keyed by string id:

1. `gob_check::status::need_of(id)` (crates/gob-check/src/status.rs:66-76): a 13-id table giving
   `Need::{Capability, EveryTextArtifact}`, `min_fidelity`, `symbol_subjects`. Entries: TODO001 REF001 TEST001
   INV001 DRIFT001-004 (text, F1); DOC001 INV002 (capability F1, symbols); DOC002 (capability F1); COV001
   AFFECT001 (capability F2, symbols). Any other id returns None = "always Examine". Consumed by
   `subject_status_for` (status.rs:90-124) for FILE rules, and by pipeline.rs:211 for opaque-text repo rules.
   Outcome table: opaque F0 + capability need -> `NotApplicable` (status.rs:102); opaque + text need ->
   Unresolved unless scanned or binary; parse Failed -> Unresolved; fidelity < min -> Unresolved.
2. `Product::applicable(snap, meta) -> bool` (gob-check/src/product.rs:274), default true. frob overrides it with an
   8-branch if-chain over string ids (frob-check/src/product.rs:511-582: PM034/PM001/PM002 milestones>0;
   REL001; REL003; `LEDGER_RULES` const (:36); REF001/TODO002 via `ledger_rule_applicable`; COV001 =
   "any file whose Language::detect == Rust" with the comment "only Rust has one today", :574-579).
   It returns bool; the reason goes to a log line (ticket ~YPRBJPF exists for exactly that).
3. grimble: `declare_not_applicable` (grimble-bind/src/lib.rs:111): eight `("SYSnnn", fn(model)->Option<&str>)`
   tuples, results stored in `binding.not_applicable` and read back by `Grimble::applicable` (grimble-check/src/product.rs:239).
   This one carries reasons and reports them (fidelity.not_applicable_rules).
4. crunk: none. COLOR001 hard-codes `STYLE_TAGS = [css tsx jsx ts js html]` (color001.rs:54) and `spec.is_none()` skips.
   Plus the standalone copy in frob-obligations `gate_file` (shape H) and `ObligationFileCheck::examines`
   (REF001 needs a ledger, filecheck.rs:109).

The per-language capability cells are NOT consulted by any rule: `Adapter::capabilities()`
(crates/gob-symbols/src/adapter.rs:269; impls rust.rs:86, python.rs:80, markdown.rs:101, grimble-model/src/adapter.rs:137)
is read only by `registry.rs:233` to print docs/reference/languages.md. `Capability` has 9 variants
(adapter.rs:52-71), `Precision` 10 (None, NotApplicable, Lexical, LexicalImports, ByNameInCrate, LinkTargets,
Keyword, Syntactic, Declared, Manifest), `Fidelity` F0-F4. universal-model.md 4.4 and testing.md 4 say the
expected class per (rule, language) is DERIVED from needs and the cells; the code derives it from `need_of`
and ignores the cells.

Language vocabulary is triple: `gob_languages::Language` (12 enum variants incl. Toml, Tsx, Jsx),
`gob_walk::LanguageHint::tag()` string (rust, markdown, toml, or the raw extension) and `Adapter::language()`
tag (rust, markdown, yaml, python, csharp, typescript, css, html, opaque, grmb), joined by string at
`FileInfo.language` (gob-symbols/src/graph.rs:104). code-model.md 3 says "Language is an open registry,
not a closed enum"; the code is a closed enum.

Which rules are language-specific today, and how it is expressed:
- COLOR001: `tier = Lang` plus hard-coded tag list (no machinery).
- DOC002: really markdown-only (is_markdown, link digest; grl-spec.md 12 writes it `lang markdown`) but
  `tier = Universal` and class "Capability F1".
- PROC001: really Rust-only (WalkDir over `*.rs`, gob-exec/src/proc001.rs:44-70) but `tier = Universal`,
  and it bypasses the shared walk (design rules.md 1: "No rule walks the tree itself").
- COV001: universal in tier; examines Rust+Python (cov.rs:37-48 `test_capable_files`), but is applicable only if a
  Rust file exists (product.rs:574): a Python-only repo gets COV001 subjects but is "not applicable".
- MDL*/SYS* (32 rules): `tier = Lang` but they are model-language rules about .grmb, not language-specific code rules;
  the tier is used as "not universal". `Tier::Lang` therefore means three different things.
- GRL already has the right vocabulary: `lang *`, `lang [rust, python]`, `lang -` (grl-spec.md 7.3, ast.rs:LangSet,
  plan/ir.rs:86 `Langs::{Any, Nothing, Only}`); Rust rules do not.

### 1.6 Duplicates and inconsistencies (numbered)

1. Eight evaluation shapes (1.3), three layouts: `rules.rs` (obligations, ledger, ack, gob-check, gob-directives),
   `rules/` dir (frob-pm, crunk-check), one file per rule (frob-release rel001-003, crunk color001), macro tables
   (grimble rule_defs.rs), inline in lib/other (frob-lease rule.rs, frob-tests rule.rs, gob-config check.rs,
   frob-check sibling/mod.rs).
2. The four file rules are listed three times (file_rules, file_rule_metas, ObligationFileCheck::rules); the
   obligation set is evaluated by two code paths (shape A and H) with the same gating written twice.
3. String rule ids outside declarations: 59 distinct ids; hot spots frob-check/src/product.rs (26), tool_parse.rs (15,
   legitimate id maps), status.rs (13), grimble-model/src/directive.rs (9), frob-pm/src/rules/mod.rs (6),
   required.rs (5). Design rules.md 2 states "nothing else references the id as a string literal"; false today.
4. `rule_id()`/`meta()` helper boilerplate with `unreachable!` repeated in 11 modules (19 files mention the
   `derive validates the id` message); crunk resolves its own meta from the global registry BY STRING (color001.rs:50).
5. Three `Need` notions: gob_check::status::Need (Capability|EveryTextArtifact, status.rs:26), gob_plan::plan::Need
   (side relations Config|Diff|Lease|Model, plan/ir.rs:28), design `needs(Q::..)` queries (rules.md 2). Three
   `Severity` enums (gob_rules, GRL ast, crunk_spec), `Scope` duplicated in GRL ast.
6. Polarity default silent; must_measure default silent; `since` default silent "2.0.0"; `product` default "frob".
7. `tier` mis-set (DOC002, PROC001, MDL, SYS) and unused (1.2).
8. Applicability by 4 mechanisms keyed by string (1.5); bool-without-reason hook (~YPRBJPF); behavior contradicts
   testing.md 4: opaque F0 + capability need returns NotApplicable (status.rs:102) where D106 says Unresolved
   reason `fidelity` (NotApplicable reserved for binary and declared-NA cells).
9. Capability matrix is documentation-only (1.5).
10. Docs and tests discovered by different conventions: docs load `tests/mdtest/<lowercase id>.md` by FILENAME across all
    crates (gob-dev/src/render/rules.rs:161-190); coverage scans every `tests/mdtest/**/*.md` by BLOCK content
    (gob-mdtest/src/coverage.rs:~160). A corpus whose file is misnamed passes coverage but yields a docs page with
    no examples.
11. gob-dev docs miss every non-frob rule silently (1.4); coverage allowlist has 27 frob + 32 grimble gaps.
12. mdtest runners are hand-written per crate: frob-obligations/tests/corpus.rs (tempdir + `evaluate_tree`),
    frob-pm/tests/corpus.rs (a ledger DSL + direct `evaluate`), crunk-check/tests/color001.rs (the real pipeline),
    frob-release (REL001 dispatched inside the rel002 test binary, ticket ~HDFYHNJ). Only crunk exercises the
    real applicability path, so a rule can pass its corpus and misbehave in the pipeline.
13. One rule's information is split across crates in these concrete cases (owner requirement 2):
    PROC001 = gob-check/rules.rs:13 (declaration) + gob-exec/proc001.rs (scan) + gob-check/repo.rs:121,157 (finding
    builder + group); COV001 = frob-obligations rules.rs:~35 + cov.rs + frob-check product.rs:332,574 (+ status.rs:72);
    REF001 = rules.rs + refs.rs + filecheck.rs:109,121 + product.rs:556 + product.rs `LEDGER_RULES`;
    SYS001-011 = grimble-bind rule_defs.rs + rules.rs/drift.rs + lib.rs:58,111 + grimble-check/product.rs:91;
    PM034/PM001/PM002 = frob-pm rules + frob-check product.rs:201,511.

### 1.7 D76 (built-ins are logically identical to plugins): where we are

plugins.md 6.1 lists the equalities: same registry entry (provenance std|pack), same metadata, same config, same
explain. Today: GRL parses (gob-plan/src/grl, catalog, plan IR with `PlanParts{rule, provenance, polarity, langs,
needs: NeedSet(side relations), prefilter, cost, ...}`) but there is no registry that merges std Rust rules and
loaded plans (ticket ~4CNF0P9, blocked). GRL header fields (ast.rs: lang, polarity, severity, scope, must_measure,
needs, rollup, knob) are a SUBSET of RuleMeta with no family/product/fix/version/since; id+slug are the rule header.
The pack registry is inventory too (packs.md 3.2). So the metadata isomorphism is not yet checked by anything.

---------------------------------------------------------------------------------------------------

## 2. Design

### 2.1 Decisions in one screen

1. One declaration type, `#[rule(..)]` on a unit struct, with EVERY field required (no defaults) except where
   derivable; it generates a `RuleDef` const that is also the GRL rule header 1:1.
2. Applicability is declared data: `applies = universal(..) | languages(..) | project`. NotApplicable and
   Unresolved are computed by ONE function from `applies` and the per-language capability matrix. `need_of`,
   `Tier`, `Product::applicable`'s id chains, `STYLE_TAGS`, `*_inapplicable` tables and `gate_file`'s copy go away;
   product-fact preconditions become a method on the rule itself.
3. Evaluation is a trait method on the same type: `FileRule` or `RepoRule` (chosen by `scope`), plus a third
   body kind `stage(..)` for the 26 rules emitted by pipeline stages. No group wiring by hand.
4. Layout: one `.rs` and one `.md` per rule, side by side in `<crate>/src/rules/`. The `.md` is the rule page
   source, the mdtest corpus and the docs (ty style). The macro `include_str!`s it, so a missing file is a compile error.
5. Registration: explicit per-crate rule list GENERATED into `src/rules/mod.rs` by `cargo dev gen rules-index`
   (clippy update_lints / ruff generate-all style, GEN001-checked), plus ONE hand-written line per rule crate in
   the product. Not inventory, not build.rs (repo bans build.rs: security.md 2.8, packs.md 10).
6. The language matrix, the rule page, coverage and the NotApplicable listing are all derived from the same
   `resolve(applies, language)` function; tests assert it, authors never write it.

### 2.2 The declaration (one shape for Rust, 1:1 with GRL)

```rust
#[rule(
    id = "COV001",                    // FAMILY(2-6 caps) + 3 digits; family is DERIVED from it
    slug = "untested-public-function",
    severity = Warn,                  // Error | Warn | Advisory   (Unresolved is never a default severity)
    polarity = Pminus,                // required: Pplus | Pminus | P0 | Pn | Pc
    must_measure = true,              // required bool
    scope = Repo,                     // File | Repo        (selects FileRule or RepoRule)
    fix = Manual,                     // Manual | Deterministic | VerifyCommit | FixIt
    applies = universal(needs = [TestItems, Visibility], min_fidelity = F2),
    version = 1,                      // cache version, bump on behavior change
    since = "2.0.0",                  // semver <= CARGO_PKG_VERSION, or `next` before a release cut
    // optional: renamed_from = ["OLD001"], corpus = pending(~C5DQ4WJ), inputs = [Diff, Lease]
)]
pub struct Cov001;
```

Field map to GRL and RuleMeta (no field exists on one side only, except `product` and `needs` below):

| Rust attr | GRL header (grl-spec.md) | Notes |
|---|---|---|
| id, slug | `rule ID "slug" {` | family derived from id in both; macro today checks family == prefix (lib.rs:155-160): drop the attr |
| severity | `severity error` | same enum (reuse gob_rules::Severity; delete the GRL copy) |
| polarity | `polarity P-` | required in both (GRL already requires it) |
| must_measure | `must_measure` | |
| scope | `scope repo` | |
| fix | `fix ...` clause | FixKind derived from the fix template tier in GRL (~DW4RJVG, ~16R03NG) |
| applies=universal | `lang *` | |
| applies=languages(a,b) | `lang [a, b]` / `lang a` | |
| applies=project | `lang -` (reads side relations only, e.g. SCOPE001) | |
| needs = [Capability..] | INFERRED by the plan compiler from the catalog (Kind.query, catalog.rs:56); `rule check` prints them | In Rust it is declared because the compiler cannot infer it from code; the const check (2.8 #6) keeps it honest only against the matrix, not against the body |
| min_fidelity | derive from catalog `Kind.languages`; add an optional `fidelity F2` header only if a rule needs more than the catalog implies | small GRL addition, open question O2 |
| inputs = [Diff, Lease, Config, Model] | `needs diff, lease` | NAME CLASH: GRL calls side relations `needs`; I use `inputs` in Rust. Recommend renaming the GRL header to `reads` (O1) |
| version, since | pack version + per-rule `since` | GRL has neither per rule; add `since` header |
| product | pack provenance (`Provenance::Std|Pack(name)`, plan/ir.rs:19) | NOT an attribute: product membership is positional (2.6) |
| doc comment / colocated .md | `explain """..."""` plus `example` blocks | same classes fire/clean/unresolved/notapplicable/known-gap/fixed (testing.md 1, grl-spec.md 9) |

Removed from the declaration: `tier` (replaced by the `applies` form; "universal" vs "lang" is now a consequence,
not a label), `family` (derived), `product` (positional), `Default` boilerplate. Everything else is required, so
omission is a compile error (the failure table is 2.8).

### 2.3 Applicability: `applies` and the one resolver

```
applies = universal(needs = [..], min_fidelity = F1)        // every language, derived per cell
applies = languages(rust, python; needs = [..], min_fidelity = F1)   // named languages only
applies = project                                           // not about files in a language: ledger, release, model, config
```

`needs` is a list of `Capability` variants (the existing 9 plus ONE new one, `Comments`: comment nodes and directive
binding, replacing `Need::EveryTextArtifact`). `min_fidelity` defaults to F1 and is the only optional field.

The resolver (pure, in gob-check; replaces status.rs `need_of`, `Need`, `RuleNeed`, the guts of `subject_status_for`):

```
resolve(applies, FileFacts{lang, fidelity, parse_status}) -> Verdict
  Project                       -> Examine          (the rule's own `inapplicable()` decides, see 2.4)
  Languages(set), lang not in set -> NotApplicable("rule is for rust,python; file is css")
  for each need c: cell = MATRIX[lang][c].precision
      Precision::NotApplicable  -> NotApplicable("css has no test_items by construction")  [declared cell]
      Precision::None (a Gap)   -> Unresolved("no `test_items` for csharp yet")           [one per rule+language, rolled up]
  parse Failed                  -> Unresolved("failed to parse")
  fidelity < min_fidelity       -> Unresolved("fidelity F1 below the F2 the rule needs")
  otherwise                     -> Examine (+ hole caveat when any need is a symbol capability and parse is Partial)
```

Verdict semantics are exactly universal-model.md 4.1-4.2 and testing.md 4: NotApplicable is never a finding, is
counted once per (rule, language) in the fidelity report; Unresolved is a finding rolled up per rule and language.
`symbol_subjects` is derived (any of ResolveRef, ApplyTargets, Visibility, TestItems, Imports in `needs`), so it
stops being a hand-set bit. `scanned` and `binary` stop being per-call booleans: two PSEUDO-languages are
rows of the matrix: `opaque-text` (no adapter, text) and `binary` (every cell NotApplicable). Toml/scanned text gets
`Comments = Syntactic` on its row (this is what `Product::scans_text` means today).

Dynamic (product-fact) applicability stays, but moves onto the rule: `fn inapplicable(&self, cx) -> Option<Reason>` with
default `None`. It returns a reason that the pipeline counts and prints (satisfies ~YPRBJPF) and replaces
`Frob::applicable`, `grimble declare_not_applicable`, `LEDGER_RULES`, `PM034_NA`, `ObligationFileCheck::examines`.
Static (language/capability) and dynamic (product fact) applicability are the only two kinds; they are both on the rule.

Compile-time guards on `applies` (all via the macro plus a const check against `gob_caps::MATRIX`, see 2.8):
- an identifier that is not a `Lang` or `Capability` variant is a compile error with a span;
- `languages(L; needs)` where the matrix gives `L` precision `None` or `NotApplicable` for a need is a compile error
  ("COV002: rust has no `effects` capability; matrix: crates/gob-caps/src/matrix.rs") because the rule could
  never fire there;
- `universal(needs)` where NO language provides all needs is a compile error (the rule could never examine anything).

Where the matrix and `Lang` live: a new LEAF crate `gob-caps` (no dependencies) holding `Fidelity`, `Capability`
(+`Comments`), `Precision`, the `Lang` enum (the adapter-level languages: Rust, Python, CSharp, TypeScript (covers
ts/tsx/js/jsx), Css, Html, Markdown, Yaml, Toml, Grmb, plus the pseudo rows OpaqueText and Binary) and a CONST
`MATRIX: [(Lang, Fidelity, [Precision; N])]`. Reason: gob-rules is below gob-ir/gob-symbols (Cargo deps:
gob-ir -> gob-rules; gob-symbols -> gob-ir), so rule metadata cannot name `gob_symbols::Capability` without
a cycle. Each adapter's `capabilities()` becomes a read of its const row, so there is ONE source (the languages page
and the rule matrix cannot disagree). `gob_languages::Language`, `LanguageHint::tag()` and `Adapter::language()`
get one mapping function to `Lang`. Plugin languages (tier-4 packs, plugins.md 8) are runtime strings and appear in
GRL `lang` only; Rust built-ins use the closed enum because that is what makes compile errors possible. The
closed-enum-vs-open-registry gap with code-model.md 3 is stated, not hidden (open question O3).

### 2.4 Evaluation: one trait per scope, on the same type

```rust
// gob-rules (no gob-check dependency)
pub trait Rule { const DEF: &'static RuleDef; fn id() -> RuleId where Self: Sized; }   // generated by #[rule]

pub trait FileRule<P: ?Sized>: Rule {
    fn check(&self, cx: &FileCx<'_, P>, out: &mut Out<'_, Self>);
    fn side_input(&self, _cx: &FileCx<'_, P>) -> Option<String> { None }      // cache key extension (REF001 ledger tip, DOC002 link digest)
    fn inapplicable(&self, _cx: &ProjectCx<'_, P>) -> Option<Reason> { None }
}
pub trait RepoRule<P: ?Sized>: Rule {
    fn check(&self, cx: &RepoCx<'_, P>, out: &mut Out<'_, Self>);
    fn inapplicable(&self, _cx: &RepoCx<'_, P>) -> Option<Reason> { None }
}
pub trait Measured<P: ?Sized>: RepoRule<P> { fn subjects(&self, cx: &RepoCx<'_, P>) -> usize; }  // required when must_measure = true
```

- `Out<'_, R>` is a typed sink: `out.fire(span, msg)`, `out.unresolved(span, reason)`, `out.fix(..)`. It stamps
  `R::id()`, so a rule cannot emit another rule's id and nobody calls `.parse::<RuleId>()` or
  `Registry::global().by_id("COLOR001")`; the 11 `rule_id()` helpers disappear.
- `P` is the HOST: the rule crate defines a small host trait it needs (frob-obligations: `ObligationHost { fn
  obligations(&Snapshot<Self>) -> ObligationInputs<'_> }`, which is exactly the existing `s.inputs.obligations()`
  adapter in frob-check/src/product.rs:337) and writes `impl<P: ObligationHost> RepoRule<P> for Cov001`. The product
  implements each host trait once (`impl ObligationHost for Frob`). A product that lists a rule crate it cannot host is a
  compile error (unsatisfied bound). This is why rule crates stay below frob-check: the layering that separates
  declaration from evaluation today (rule crates cannot name `Frob`) is solved by a trait, not by moving code to the product.
- `scope = File` requires `FileRule`, `scope = Repo` requires `RepoRule`; the macro emits a `const DEF` that uses
  `RuleDef::file::<Self, P>` or `::repo::<..>`, so a missing impl is "the trait bound `Cov001: RepoRule<_>` is
  not satisfied" at the declaration. `must_measure = true` additionally requires `Measured` (replaces the `.counting`
  closures).
- Stage-emitted rules (shape G, 26 rules): `scope = Repo, body = stage(DirectiveScan)` etc. `Stage` is a closed enum in
  gob-check (DirectiveScan, ReadWalk, Perf, ToolStage, Sibling, Exceptions, TicketScope, Doctor, Alias(of)); no trait is
  required, the stage code stamps findings through `Cov003::id()`-style consts. They get declaration, docs, matrix,
  registry, uniqueness; they do not get a `check`. This is real extra surface (flag F2).
- Shared per-file/per-run work (today fused: `directives_of`, `Tickets::new`, ledger read for PM001/PM002/PM034):
  memoized inside the Cx (`OnceLock` fields). Rules are evaluated one at a time; the cache key is already per rule
  (filecheck.rs:272-278), so fused groups buy no cache benefit today, only shared computation. If a measurement shows
  the memo is slower than the fused call, a rule family may share a `Cx` memo type; do NOT add a `group = ..` attribute.

### 2.5 File layout (per product; rules may live in several crates)

```
crates/<owner-crate>/
  Cargo.toml                      [package.metadata.gob] families = ["COV", "INV"]    (checked by gen, see 2.8 #14)
  src/lib.rs                      pub mod rules;
  src/rules/mod.rs                @generated: mod decls + `pub const METAS` + `pub fn bind::<P>()`; sorted; GEN001
  src/rules/cov001.rs             #[rule(..)] struct + impl RepoRule + (private helpers, or `use crate::cov::..`)
  src/rules/cov001.md             rule page source AND mdtest corpus (format 2.7)
  src/<helpers>.rs                shared algorithms used by several rules (call-graph reach, link resolution)
  tests/                          crate tests that are not rule corpora (the corpus is the .md)
```

- File stem == lowercase id: compile error otherwise (const compare against `file!()`, plus the macro reads the .md by that
  name). One rule per file. Family -> crate ownership stays as boundaries.md 2.5 says; the scaffold reads it.
- Product crates (frob-check, grimble-check, crunk-check) contain NO rule declarations and NO rule wiring. They contain
  `rules.rs`: one line per rule crate (2.6) and the host-trait impls.
- Cross-crate pieces of one rule (the PROC001 case): the scanning algorithm moves from gob-exec/src/proc001.rs into the rule
  file (it needs the shared walk, not its own WalkDir, so it reads `cx.files()` rust files). Rule rule: everything that is
  about ONE rule is in its two files; shared algorithms used by >=2 rules stay in plain modules of the same crate and are
  imported; a rule never imports another rule.

### 2.6 Registration: generated per-crate list, one line per crate in the product (pick and justify)

Pick: a GENERATED, committed `src/rules/mod.rs` per rule crate (`cargo dev gen rules-index`, GEN001-checked,
modelled on clippy `cargo dev update_lints` and ruff `generate-all`), and one hand-written product list.

```rust
// crates/frob-check/src/rules.rs  (the only registration a human maintains)
gob_check::product_rules! {
    product = Frob;
    crates  = [frob_obligations, frob_ack, frob_tests, frob_ledger, frob_pm, frob_release, frob_lease,
               gob_directives, gob_config, gob_check];
}   // expands to: pub fn rules() -> Vec<RuleDef<Frob>>  and  const _: () = assert_unique(&[A::METAS, B::METAS, ..]);
```

Why not inventory (status quo, ticket ~67J8R53's "keep inventory + test"):
- link-time: an unlinked rule crate contributes nothing and nothing fails (proved by the missing COLOR001/MDL/SYS docs, 1.4);
  the `link_inventories` anchor hack is the symptom; duplicate ids only at runtime;
- registry != selection: it cannot prove the rule is run by its product; a list can (the pipeline iterates the list; a rule
  in the list is run);
- it gives no compile-time facts (duplicates, unlisted rules, product/host mismatch).
Why not build.rs: repo policy (security.md 2.8 "never build.rs"; packs.md 10 even makes `build.rs` a Warn for packages)
and the T5H07H5 ticket repeats it. Why not a proc macro reading `src/rules/*.rs`: stable cargo does not track a newly added file, so
a new rule is invisible until something touches lib.rs (stale incremental builds in shared-target worktrees); tracked_path is nightly.
Why committed generated files are acceptable: merge-conflict risk is one sorted line pair per rule; the fix for a
conflict is `cargo dev gen rules-index --write` (and `frob check --fix` can run it). 

What the list buys (compile time): the generated `const METAS: &[&RuleMeta]` gets `assert_unique` (ids, slugs,
renamed_from, retired ids: a const-fn double loop over <100 items) at the crate level and again at the product's
`product_rules!` and at gob-dev's all-products list. A rule crate that is a Cargo dependency of the product but absent
from `product_rules!` is flagged by `#![deny(unused_crate_dependencies)]` in the product crate (rustc, compile time) and
by the existing cargo-shear step in `cargo dev ci` (~19X37CZ, done). A rule file present in `src/rules/` but missing from the
generated index is NOT a compile error (rustc never sees the file): this is the one failure that is gen-time (GEN001), by design
and justified by the build.rs ban; `frob check` runs GEN001, `cargo dev new-rule` writes both files and regenerates, and a
crate unit test `rules_index_is_fresh` fails `cargo test -p <crate>` too.

D76 / plugins: `RuleDef` is the single runtime type. Built-in Rust rules are `Body::File|Repo|Stage` with
`Provenance::Std`; a GRL pack rule is `Body::Plan(PlanId)` with `Provenance::Pack(name)`. `Registry::of(&[product lists],
&loaded_packs)` merges them (this IS ticket ~4CNF0P9 with `inventory::iter` replaced by the product lists), so
`rules list`, config, severities, explain and docs treat them identically; `replaces = "ID"` is checked against the const-unique std set.
GRL-to-Rust codegen (`cargo dev gen rules`, ticket ~T5H07H5) emits the same `src/rules/<id>.rs` shape plus its `.md`, so a
GRL-generated std rule and a hand-written one are indistinguishable to the index and the registry. Link-time pitfalls of
the other inventory registries (ConfigTable, Command, Directive, Artifact, Adapter) are untouched; rescope ~67J8R53 to rules
and revisit the others separately (O4).

### 2.7 The colocated `.md`: docs, mdtest corpus, language matrix

```
<!-- mdtest: rule=COV001 -->
# COV001 untested-public-function

Public callables should be reached by at least one test.            <- first paragraph = summary (RuleMeta.summary)

## What it does                ...
## Why it matters              ...
## Remedy                      ...
## Examples
### A public fn with no test fires
```rust expect=fire file=src/lib.rs
pub fn double(x: i32) -> i32 { x * 2 }       // warn: COV001
```
### A tested fn is clean
```rust expect=clean ...```
### A python-only reach is unresolved
```python expect=unresolved reason=fidelity file=lib.py ...```
```

- Same fence grammar as gob-mdtest/FORMAT.md today (info-string `rule=`, `expect=fire|clean`, markers); D106 adds
  `unresolved` and `notapplicable` (testing.md 1), `lang=` optional (defaults from the fence language). A pure
  superset of the file crunk already uses (crates/crunk-check/tests/mdtest/color001.md).
- The macro reads `<manifest>/src/rules/<id_lower>.md` at expansion (path convention fixed by the layout), validates the
  section headings, `rule=ID` header, and presence of at least one `expect=fire` and one `expect=clean` fence, emits spanned
  errors on the attribute, and emits `include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/src/rules/cov001.md"))` so cargo tracks it.
  Structural validation is therefore COMPILE time; running the examples is test time.
- Language matrix: derived, not written. For each (rule, Lang) the harness computes `resolve(applies, Lang)`; for any cell that
  is NotApplicable or Unresolved it runs the language's canonical one-file sample (kept next to the adapter corpus) through the
  product pipeline and asserts the derived class (this is testing.md 4, "a written expectation that disagrees with the derived one
  fails"). Authors write fire/clean blocks only for cells that Examine: universal rules need them in one language (more if
  desired for parity), `languages(a,b)` rules in each listed language (test-time check, since it needs the fence parse).
- The same `.md` generates docs/reference/rules/ID.md (META table incl. the derived applicability and the language matrix table) via
  the existing gob-dev renderer; examples are read from the rule's own file, not found by filename convention (fixes 1.6 #10).
- The mdtest runs through the REAL product pipeline (`--only ID` on a tempdir repo), via a product `Harness` with one hook,
  `materialize(&Case, &Path)` (default writes the fenced files; frob-pm supplies its ledger-DSL materializer). This deletes the
  per-crate hand runners and makes every corpus exercise `resolve`, `inapplicable`, caching and must_measure. The generic test is one
  line per product: `gob_mdtest::rule_suite!(product = Frob, harness = FrobHarness);` (reports one case per fence, names the .md file and line).

### 2.8 Failure modes: where each is caught (pushed as early as Rust allows)

C = compile time (rustc), G = gen time (GEN001 / `cargo dev gen --check`), T = test only.

| # | Mistake | Caught | How / why not earlier |
|---|---|---|---|
| 1 | missing or malformed metadata (id, slug, severity, polarity, must_measure, scope, fix, applies, version, since) | C | all attrs required; darling errors with spans; trybuild UI cases |
| 2 | no evaluation | C | `RuleDef::file/repo::<Self,P>` bound: unsatisfied `FileRule`/`RepoRule` at the declaration |
| 3 | must_measure = true but no `subjects` | C | `Measured` bound |
| 4 | applicability not declared | C | `applies` required |
| 5 | language-specific rule names an unknown language | C | `Lang::Xyz` path resolution, span on the ident |
| 6 | names a capability the language's adapter lacks | C | const assert against `gob_caps::MATRIX` with a message naming rule, language, capability, matrix path |
| 7 | universal rule no language can satisfy | C | const assert (exists-language) |
| 8 | capability or language typo | C | enum variants |
| 9 | duplicate id / slug / renamed_from / retired id within a crate | C | const `assert_unique` over generated `METAS` |
| 10 | duplicate across crates of one product | C | const assert in `product_rules!` |
| 11 | duplicate across products | C | const assert in gob-dev's all-products list (and in any binary that lists several) |
| 12 | rule not run by its product (crate listed? host impl?) | C | listed crate is iterated by construction; missing host impl is an unsatisfied bound; dep not listed is `unused_crate_dependencies` (deny) |
| 13 | rule file exists but index not regenerated | G | rustc never sees an unreferenced file; GEN001 + `cargo test` freshness; unavoidable without build.rs (banned) |
| 14 | rule in a crate that does not own its family | G | `rules-index` checks `families` from Cargo metadata; ownership is a repo fact not a type fact |
| 15 | missing .md | C | macro read + `include_str!` of the conventional path |
| 16 | .md lacks required sections / rule= header / fire / clean fence | C | macro validates at expansion with spans |
| 17 | file stem != lowercase id | C | const compare of `file!()` stem and id |
| 18 | `since` in the future or not semver; `version` 0 | C | macro compares with `CARGO_PKG_VERSION` at expansion |
| 19 | rule emits another rule's id | C | `Out<R>` stamps the id; no raw `Finding::new` with an id in rule bodies (a gob-rules lint test greps for it: T) |
| 20 | stale docs/reference/rules page or languages page | G | GEN001; one freshness test per generated kind (~JMDMEKV AC4) |
| 21 | docs miss a product's rules | C | gob-dev lists products explicitly (compile error if a crate is removed), no linker anchor |
| 22 | corpus has no fire/clean pair for a required language | T | needs the fence language attribute parsed against `applies`; one test over all rules; names rule and language |
| 23 | the examples actually fire/clean/unresolved as stated; derived matrix cells hold | T | requires running the engine; cannot be compile time |
| 24 | polarity conformance (a P+ rule fires on a May-only edge) | T | testing.md 7 per-polarity standard repos; engine behavior |
| 25 | `needs` list disagrees with what the body actually reads | T (weak) | Rust cannot see inside the body; the dependency-injected `Cx` exposes only capability-gated accessors (`cx.test_items()` needs `TestItems` in `needs`: the accessor is generic over a const marker the macro emits), so an undeclared read is a compile error; if that proves too heavy keep it a test (O5) |
| 26 | existing rules lacking a corpus (59 gaps) | C once migrated | transitional `corpus = pending(~HANDLE)` on the rule, ticket shape checked by the macro, ticket existence and the shrink-only count by a test; the allowlist file is deleted |

### 2.9 The scaffold: `cargo dev new-rule`

```
cargo dev new-rule COV007 untested-thing --universal --scope repo [--needs TestItems,Visibility]
cargo dev new-rule NEAT040 some-slug --lang rust,python --scope file [--needs Imports]
```
Writes `src/rules/<id>.rs` and `<id>.md` in the crate that owns the family (from `[package.metadata.gob] families`; `--crate` overrides), runs
`gen rules-index`, then `cargo test -p <crate> <id>` as its own acceptance. The generated rule is a toy that fires on the literal
`NEWRULE_FIRE` and the .md carries a fire and a clean block, so it builds and passes unedited; `--lang L` pre-fills `applies = languages(L; needs=[..])`
and the fence language. A CI step scaffolds into a temp copy, builds, runs its test, and deletes it (ticket ~0H3WYTR AC2). Zero registration
edits because the list is generated; zero product edits unless a NEW crate (then one line in `product_rules!` plus a host impl).

### 2.10 What a new rule costs after the change

- Universal or language rule in an existing crate: 2 hand-written files (`x.rs`, `x.md`) + 2 generated/refreshed
  (index line, docs page). Today: 9-12 edits across 3 crates (1.4).
- New rule crate in a product: add crate to `product_rules!` (1 line), implement its host trait once.
- Nothing else: no `need_of`, no `applicable` arm, no group, no `.counting`, no corpus runner, no allowlist, no `pub use`.

### 2.11 Complexity flags (what I would watch, and what I deliberately did NOT add)

F1. Host-trait generics (`impl<P: ObligationHost> RepoRule<P>`). Biggest technical risk; fallback is a concrete `Cx` struct per rule
    crate and `Supplies<Cx>` on the product (same compile-time properties, slightly more boilerplate). Spike S1 decides.
F2. Stage-emitted rules (26 of 82) need a third body kind. Not avoidable: they are real and need declaration/docs/matrix/uniqueness.
F3. New leaf crate `gob-caps` and a re-export churn in gob-symbols/gob-languages for `Fidelity/Capability/Precision`; the behavior-preserving
    migration must keep the generated languages page byte-identical.
F4. Policy decision hidden in the matrix: opaque F0 text with a capability need is NotApplicable today (status.rs:102) but Unresolved
    by D106 section 4. Land the resolver behavior-preserving (set the `opaque-text` row cells so today's answers hold), then flip as a separate
    ticket with the fidelity report diff reviewed (O6).
F5. Per-rule evaluation versus today's fused group computation; mitigated by Cx memoization, measured with `--timing` before/after (ticket ~AKMV3C3).
F6. Running every mdtest through the real pipeline is slower than calling `evaluate` directly; mitigate with `--only ID` and the product's
    cache (the pipeline already caches per file digest). Ledger-heavy corpora (frob-pm) go through the Harness hook.
F7. Committed generated index files (GEN001 noise, rare conflicts). Cheaper than build.rs (banned) and than inventory (silent).
F8. GRL header naming clash `needs` (O1) and GRL's lack of `since`/`min_fidelity` (O2): small spec edits, not code.
Not added, on purpose: no `group =` attribute; no per-rule feature flags; no `tier`; no runtime defaults; no inventory for rules; no second
metadata file (TOML) next to the rule; no generic "plugin hooks" for built-ins (D76 parity is achieved by one RuleDef type, not by a back door).

---------------------------------------------------------------------------------------------------

## 3. Before and after for real rules

### 3.1 TODO001 (universal, file scope)

BEFORE (touchpoints: 9 across 3 crates + 2 generated docs):
- declaration `crates/frob-obligations/src/rules.rs:44-67` (`#[derive(Rule)] #[rule(id, slug, family="TODO", severity=Error, tier=Universal,
  scope=File, fix=Manual, polarity=Pplus, version=1)] pub struct Todo001;`), docs comment above it;
- evaluation `crates/frob-obligations/src/todo.rs:94` (`todo001(file, path, text, directives)` building findings with `&Todo001`);
- fused call `crates/frob-obligations/src/lib.rs:156`; metas array `lib.rs:164-166`; `ObligationFileCheck::rules()` `frob-check/src/filecheck.rs:98`;
- applicability `crates/gob-check/src/status.rs:67-69` ("TODO001" in the text-need arm) and the duplicate in `gate_file` (`lib.rs:174`);
- re-exports `lib.rs:87`; corpus `crates/frob-obligations/tests/mdtest/todo001.md` + runner `tests/corpus.rs`; page `docs/reference/rules/TODO001.md`.

AFTER (`crates/frob-obligations/src/rules/todo001.rs` + `todo001.md`; the rest generated):
```rust
use crate::host::{FileCx, ObligationHost};
use gob_rules::prelude::*;

#[rule(
    id = "TODO001", slug = "bare-work-marker",
    severity = Error, polarity = Pplus, must_measure = false,
    scope = File, fix = Manual,
    applies = universal(needs = [Comments], min_fidelity = F1),
    version = 1, since = "2.0.0",
)]
pub struct Todo001;

impl<P: ObligationHost> FileRule<P> for Todo001 {
    fn check(&self, cx: &FileCx<'_, P>, out: &mut Out<'_, Self>) {
        for c in cx.comments() {                       // `comments()` exists only because `Comments` is in needs
            if is_bare_marker(c.text()) && !cx.owned_by_todo_directive(c) {
                out.fire(c.span(), "bare work marker: file a ticket, then add `frob:todo <ulid>`");
            }
        }
    }
}
```
`todo001.md` holds the explanation (What it does / Why it matters / Remedy), a fire block, clean blocks (including the "owned by `frob:todo`"
case) and nothing for the matrix: the resolver derives that css/yaml/rust/python/markdown Examine, opaque-text is Unresolved by D106 (or
NotApplicable under the behavior-preserving first step), binary NotApplicable. Deleted by this change: lib.rs:156/164, filecheck.rs:98, status.rs:68
arm, `gate_file` special-casing for the rule, the hand-maintained docs row.

### 3.2 COV001 (universal, repo scope, must_measure; shows applicability and subject accounting)

BEFORE: declaration frob-obligations rules.rs:~35-49 (`must_measure = true`, `polarity = Pminus`); evaluation cov.rs; group `Frob::repo_groups`
(product.rs:332-343 with `.counting(|s| vec![("COV001", cov001_subjects(..))])` at :340); applicability in three disagreeing places:
`need_of` arm `"COV001" | "AFFECT001" => capability F2, symbols` (status.rs:72), `Frob::applicable` "COV001 = any Rust file" (product.rs:574-579), and
`test_capable_files` "Rust or Python" (cov.rs:37-48).

AFTER:
```rust
#[rule(
    id = "COV001", slug = "untested-public-function",
    severity = Warn, polarity = Pminus, must_measure = true,
    scope = Repo, fix = Manual,
    applies = universal(needs = [TestItems, Visibility, ApplyTargets], min_fidelity = F2),
    version = 1, since = "2.0.0",
)]
pub struct Cov001;

impl<P: ObligationHost> RepoRule<P> for Cov001 {
    fn check(&self, cx: &RepoCx<'_, P>, out: &mut Out<'_, Self>) { /* body of cov::cov001 */ }
}
impl<P: ObligationHost> Measured<P> for Cov001 {
    fn subjects(&self, cx: &RepoCx<'_, P>) -> usize { cx.files_where_examined(self).count() }   // generic: files whose Verdict is Examine
}
```
Verdicts follow from the matrix: Rust (TestItems Syntactic, F3) Examine; Python (TestItems Syntactic, F2) Examine; C# (TestItems Gap, F1) Unresolved
"no test_items for csharp yet"; markdown/css (TestItems NotApplicable) NotApplicable. This removes the Rust-only hack AND the Rust+Python list, and fixes the
Python-only-repo inconsistency; `subjects()` no longer needs a hand-written file filter because the framework already knows which files Examine.

### 3.3 DOC002 (language-specific, file scope; today mis-tiered Universal)

BEFORE: `tier = Universal` (rules.rs:~113-130), capability class F1 in `need_of` (status.rs:70), markdown-ness hard-coded in
`ObligationFileCheck::side_input` (`is_markdown`, filecheck.rs:109-131).
AFTER: `applies = languages(markdown; needs = [ResolveRef], min_fidelity = F1)`. The matrix has `markdown ResolveRef = LinkTargets` so the const check
passes; on every other language the resolver says NotApplicable once per language. `side_input` (the link-target digest) is a method of the same type.
Same shape for PROC001: `applies = languages(rust; needs = [])` and its scan reads the shared walk instead of its own WalkDir.

### 3.4 crunk COLOR001 (language-specific by the `style` capability)

BEFORE (crunk-check/src/rules/color001.rs, 253 lines, plus product.rs:59, tests/color001.rs, tests/mdtest/color001.md, allowlist, Cargo.toml):
`tier = Lang` with no language; `STYLE_TAGS: [&str; 6]` (:54); a local `meta()` that looks itself up by string (:50); a local `group()` returning
`RepoGroup::new("repo:color", vec![meta()], run).counting(..)` (:70-79); `spec.is_none()` as an in-body not-applicable; severity read from the spec inside the body (:90-96).

AFTER (`crates/crunk-check/src/rules/color001.rs` + `color001.md`, no product edit beyond the existing crate line):
```rust
#[rule(
    id = "COLOR001", slug = "color-off-palette",
    severity = Error, polarity = Pplus, must_measure = false,
    scope = Repo, fix = Manual,
    applies = languages(css, typescript, html; needs = [Style], min_fidelity = F1),   // `Style` = the existing `style` capability (language-engines.md 2)
    version = 1, since = "0.532.0",
)]
pub struct Color001;

impl<P: CrunkHost> RepoRule<P> for Color001 {
    fn inapplicable(&self, cx: &RepoCx<'_, P>) -> Option<Reason> {
        cx.spec().is_none().then(|| Reason::new("no valid crunk.toml"))
    }
    fn check(&self, cx: &RepoCx<'_, P>, out: &mut Out<'_, Self>) {
        let spec = cx.spec_or_unreachable();
        for site in cx.style_sites() { /* palette conformance as today; severity from spec.severity("COLOR001") via out.fire_at(sev, ..) */ }
    }
}
```
Notes: `Style` (and `Markup`) are in the existing capability table in universal-model.md 4.4 but not in the 9-variant `Capability` enum yet; adding them is part
of the gob-caps migration (the matrix then proves css/typescript/html provide it, and `tsx/jsx/js` fold into the `typescript` Lang). `STYLE_TAGS`, the group, the
local meta/rule_id, the product wiring and the hand runner disappear; the corpus file moves to `src/rules/color001.md` (content unchanged). Crunk gains docs pages
and the language matrix for free. `crunk.toml [lint] COLOR001 = off` stays config-driven; the id is checked by ~7WRK7XC against `renamed_from`.

---------------------------------------------------------------------------------------------------

## 4. Migration plan (small tickets)

Order matters only where stated. Each ticket: scope, acceptance. S = spike, new work; A = amends, X = supersedes.

M0 (S1) Spike: the whole loop on ONE rule in a scratch crate.
  Scope: gob-macros (new `rule` attribute next to the derive), gob-rules (RuleDef, FileRule, RepoRule, Out), throwaway crate.
  Accept: TODO001-shaped rule compiles with `FileRule<P: Host>`; deleting its `.md`, a section, the fire fence, the trait impl, or mistyping a
  language/capability each fails with a spanned message; `include_str!` tracking verified by touching the .md and rebuilding; decision recorded on
  F1 (host trait vs Supplies<Cx>).

M1 `gob-caps` leaf crate: Lang, Fidelity, Capability(+Comments, Style, Markup), Precision, const MATRIX; adapters read their row.
  Scope: new crates/gob-caps, gob-symbols (adapter.rs, registry.rs, each adapter's capabilities()), gob-languages mapping, grimble-model adapter.
  Accept: docs/reference/languages.md is byte-identical (GEN001 clean); a test asserts every adapter's `capabilities()` equals its const row; one `Lang` mapping
  function from Language/LanguageHint/Adapter tag with a test over all three vocabularies; `opaque-text` and `binary` rows exist.

M2 Applicability resolver. Replaces `need_of`/`Need`/`RuleNeed`/`subject_status_for` internals (behavior-preserving).
  Scope: gob-check/src/status.rs, filecheck.rs, pipeline.rs:211, frob-obligations `gate_file`.
  Accept: the existing status.rs unit table (status.rs:360+) passes unchanged against `resolve` fed the equivalent `applies`; `opaque-text` row set so
  today's NotApplicable/Unresolved answers hold; Verdict carries reasons that reach the check JSON (this is ~YPRBJPF, X ~YPRBJPF).

M3 The `#[rule]` attribute and `RuleDef`. X ~D3ZK8NM (ACs 1, 2, 4 satisfied; AC3 satisfied at compile time for structure, test time for examples).
  Scope: gob-macros, gob-rules, trybuild cases.
  Accept: one UI test per row 1-8, 15-18 of the failure table; the old `#[derive(Rule)]` still compiles and is marked deprecated; RuleDef records file!()/line!().
  A: ~KCJ0F5T stays a blocker only for column assertions, not for this ticket.

M4 Product rule lists and uniqueness. A ~67J8R53 (rescoped to rules: its AC1, AC2, AC4, AC5, AC6 are met by lists + const asserts; AC3 by `renamed_from`
  and `retired`; inventory for tables/commands/directives/artifacts is split into a follow-up).
  Scope: gob-rules (Registry::of), gob-check (`product_rules!`), gob-dev (explicit product deps; delete `link_inventories` rule anchor), gen kind `rules-index`.
  Accept: removing a crate from `product_rules!` while keeping the dependency fails `cargo check` (unused_crate_dependencies); a duplicate id across two
  crates of a product fails to compile naming both modules; `cargo dev gen --check` includes `rules-index`; gob-dev has no linker anchor for rules.

M5 Pipeline runs `RuleDef`s. Delete RepoGroup/FileCheck/`Product::repo_groups/file_checks/applicable/includes` for rules (keep adapters during migration).
  Scope: gob-check (pipeline, filecheck, repo, product), host traits.
  Accept: a toy product with two rules (one file, one repo) runs without any group wiring; `inapplicable()` reasons reported once in JSON and --text;
  must_measure zero-subject path uses `Measured`.

M6a Migrate frob-obligations, frob-ack, frob-tests (shapes A, B, H). Delete file_rules/file_rule_metas/ObligationFileCheck/`LEDGER_RULES` arms and `gate_file`'s copy.
  Accept: frob check output on this repo is byte-identical before/after (cargo dev ecosystem or `frob check --json` diff); `--timing` file-rules stage not slower than +10 percent.
M6b Migrate frob-ledger, frob-pm, frob-release, frob-lease, gob-config (shapes B, F, G). Ledger/PM shared work via Cx memo.
  Accept: same byte-identical check; PM034/PM001/PM002 `inapplicable` reason appears in the NotApplicable list.
M6c Migrate gob-check neutral rules + gob-directives + tool-bound ids (shape E, G). PROC001 moves into one file and uses the shared walk; `Stage` enum introduced.
  Accept: PROC001 results identical; no rule id string literal remains in tool_parse.rs except the external tool id maps (those become `Rule::id()` values).
M7 Migrate grimble (MDL 21, SYS 11). `check_model` stays one stage; each rule gets a 2-file declaration with `body = stage(ModelCheck|Binding)`.
  Scope: grimble-model, grimble-bind, grimble-check. Delete `RULES`, `DIRECTIVE_RULES`, `declare_not_applicable`, family filters.
  Accept: grimble check output identical; corpora may be `corpus = pending(~QSK0WB1)`.
M8 Migrate crunk COLOR001 (3.4). A ~JY79XVV (use the new macro; `crunk-rules` crate not needed), A ~8MQFYVM ~Q6DBW3W ~PTNEDQ0 ~BWK6MXR (write the new rules in the
  new shape; add a note that they must not use the derive).
  Accept: COLOR001 docs page generated; `STYLE_TAGS` gone.
M9 mdtest as docs: colocated `.md`, `rule_suite!` + product Harness, derived matrix cases, `unresolved`/`notapplicable` classes. X ~HDFYHNJ; A ~VB2EYG6 (share the
  class vocabulary and the example parser between GRL examples and the .md corpus), A ~1X6M6MS (strict mode default in the harness).
  Accept: frob-pm's DSL corpus runs through `materialize`; a deliberately wrong derived-matrix expectation fails naming rule and language; allowlist file deleted
  once the 59 gaps are `pending(..)`; A ~C5DQ4WJ and ~QSK0WB1 (they become `pending` burn-down tickets).
M10 Docs generation from the same data. A ~JMDMEKV (rule pages, languages page, per-rule matrix are one generated kind each with freshness test; the page reads
  the rule's own .md).
  Accept: docs/reference/rules contains all 82 rules (incl. COLOR001, MDL, SYS); stale page fails `cargo test -p gob-dev` naming the path.
M11 `cargo dev new-rule`. X ~0H3WYTR (re-specified with --universal/--lang and no registration step).
  Accept: scaffold builds and passes unedited; CI step scaffolds in a temp copy.
M12 Plugin parity. A ~4CNF0P9 (merge product lists, not `inventory::iter`), A ~T5H07H5 (codegen emits `src/rules/<id>.rs` + `.md` in the std pack crate),
  A ~VNVVACK; GRL gains optional `since` and `reads` (O1, O2).
  Accept: `rules list --json` has the same fields for a std Rust rule, a std GRL rule and a repo pack rule; the conformance test (plugins.md 6.1) can address both through `RuleDef`.
M13 Config/rule-id consistency. A ~7WRK7XC (becomes a pure function over `Registry::of` + `renamed_from`; no ad hoc id scan).
  Accept: as in the ticket.
M14 Cleanup: delete the derive, `Tier`, `RuleEntry`, `inventory` dependency in gob-rules, `Product::includes`, the string-id lint exemptions.
  Accept: grep for `"[A-Z]+[0-9]{3}"` in non-test, non-id-map code finds nothing; GEN001 clean.

Suggested order: M0, M1, M2 (parallel after M0), M3, M4, M5, then M6a-c/M7/M8 in parallel (they touch disjoint crates), M9-M11, M12-M14.
New rules written before M3 lands should use the old derive; after M3, new rules use only the new attribute (add to the coordinator brief).

---------------------------------------------------------------------------------------------------

## 5. Open questions (decide-and-record candidates; owner delegates decisions)

O1. GRL header `needs diff, lease` vs Rust `needs = [capabilities]`: rename the GRL header to `reads` (recommended) so `needs` means capabilities in both.
O2. Add optional `since` and `fidelity` headers to GRL (small spec edit) so metadata is a true isomorphism.
O3. Closed `Lang` enum for built-ins versus the open registry of code-model.md 3: recommend closed for Rust built-ins, strings for packs; amend code-model.md 3.
O4. Rescope ~67J8R53 to rules only and file a follow-up for ConfigTable/Command/Directive/Artifact/Adapter registries (same list-plus-const-unique treatment where a per-product list is natural).
O5. Capability-gated Cx accessors (`needs` enforced by types) versus a plain test: start with the test, move to types only if undeclared reads appear.
O6. Flip opaque-F0 text from NotApplicable to Unresolved per D106 section 4 (behavior change, own ticket, after M2).
O7. Keep `Advisory`-only stage rules (e.g. TOOL002) as declarations only, or fold the CI/TOOL family into the grimble-ci crate named by their doc comments (gob-check/src/rules.rs: "until grimble-ci owns the CI family").

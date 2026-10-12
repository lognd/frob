# crunk survey (for frob v2 / shared Rust workspace planning)

Source: <crunk>, branch `main`, HEAD 8ce8c29 (2026-09-27).
Python >= 3.11, version 0.1.1.dev57. Previously named "apollo": frob.lock
and FROBLEMS.md still say `src/apollo/...`, so frob.lock is stale (last
written 2026-09-06).

## 1. What crunk does

A design-system linter, token exporter and autofixer for front-end code.
CSS uses tinycss2. TS/TSX uses tree-sitter. Tailwind is checked by running
the project's own Tailwind through node. There is also an opt-in screenshot
gallery that uses playwright.
Pipeline: crunk.toml -> DesignSpec; tree -> ProjectStyles; rules ->
list[Violation]; then report | fixes | tokens.

### CLI verbs and flags (src/crunk/__main__.py, docs/commands/*.md)

Global: `--version`, `-v/--verbose`. Binaries: `crunk` and alias `crk`.
Nearly every pipeline verb accepts `--config PATH` and `--root PATH`. The
exceptions are `init` and `cache`.

| Verb | Flags / args | Notes |
|------|--------------|-------|
| init | --preset NAME (default/mono), --force | scaffold crunk.toml, bucket dirs, reset.css, tokens; auto-detects [jsx]/[tailwind] |
| check | PATH..., --json, --contrast or --report (mutex), --no-cache | exit 0/1/2; --report = Markdown or v2 JSON |
| tokens | --format css/json/tailwind, --check | bare = only writer; --format previews to stdout; --check = drift exit 1 |
| fix | PATH..., --dry-run, --no-cache | byte-range edits; dry-run output is byte-identical to the real run |
| map | --json, --no-cache | organization inventory (no rules) |
| query find TERM | --json | ranked: exact > prefix > substring, then use count |
| query component NAME | --json | BEM card |
| query dupes | --threshold (0.6), --json | shared (prop,value) / smaller set |
| query unused | --json | exported tokens never var()'d |
| query uses NAME | --json | every var(--NAME) site |
| query color VALUE | --json | nearest palette entries |
| query violations | --rule ID, --path GLOB, --json | filtered check results; query never exits 1 |
| explain NAME | --json, --no-cache | token value + every use; exit 2 on unknown, names close matches |
| preview | --color | ANSI truecolor token sheet (NO_COLOR aware) |
| diff OTHER | --color | token-set diff vs another spec dir/file |
| cache ls / prune | prune: --age DAYS (30), --all | user cache dir, outside the repo |
| gallery enumerate/render/triage/check | --manifest; render: --artifacts-dir; triage: --host, --reviewer; check: --json | screen-approval pipeline |
| doctor | --json | renderer + Tailwind presence table |

Exit codes: 0 clean, 1 error-severity violation, 2 cannot run (an Err
escaped to the shell, or an argparse usage error). JSON output is versioned
(`{"version":1,...}`; report v2; query
`{"version":1,"kind":...,"results":[...]}`). Command-line typos get no
"did you mean" hint beyond argparse's default.

### crunk.toml schema (docs/design/02-specification.md, CR-01)

Unknown keys anywhere are an exit-2 error that names the key.

| Section | Keys | Required |
|---------|------|----------|
| [project] | css_root, tokens_file (rel. css_root), root_font_size | yes |
| [palette] | name -> CSS color literal | yes |
| [palette.roles] | role -> [fg,bg] or {pair, floor} | no |
| [scales] | spacing, font_sizes (req), radii, sizes (opt) | yes |
| [breakpoints] | sm/md/lg/xl px, base_required list | no (Tailwind v3 defaults when a TW config exists) |
| [typography] | families, weights; [typography.stacks] name -> list | yes |
| [layers] | name -> z-index | optional since r11 |
| [org] | buckets (req), class_case, component_prefix, tokens_only_custom_props, model (buckets or utility-first), ignore, entry | buckets yes |
| [tokens] / [tokens.prefixes] | header, json_file; color/space/font_size/radius/layer/font_family prefixes | no |
| [jsx] | globs | no |
| [tailwind] | config, tokens_file, namespace_keys, alpha_channels, engine (static) | no |
| [lint] | RULEID = error/warn/off, fix_tolerance (0.15), color_tolerance (8.0) | no |
| [[platform]] | id, renderer (web or command), engine, viewport, device_scale, locale, media, command | no |
| [[screen]] + [[screen.states]] | id, entry, applies_to; state id/fixture/setup | no |

Path-base quirk: `[project]` *_file keys resolve against css_root, and every
other *_file key resolves against the project root. The spec calls this
"compatibility law".

### Rule catalog (src/crunk/rules, registry in rules/engine.py)

| Family | Ids | Lints | Fixable |
|--------|-----|-------|---------|
| COLOR | 001, 002 | off-palette literal (alpha-aware); undefined var(--x) | 001 |
| SPACE | 001 | margin/padding/gap/inset off spacing scale | yes |
| TYPE | 001, 002, 003 | font-size off scale; family stack; weight | 001 |
| RADIUS | 001 | border-radius off radii | yes |
| SIZE | 001 | width/height off sizes (max-width exempt) | yes |
| LAYER | 001 | z-index not a declared layer | no |
| CONTRAST | 001 | role pair below WCAG floor (4.5 default) | no |
| ORG | 001-005 | bucket placement, class case, component prefix, custom props outside tokens file, ungoverned sheet | no |
| TW | 001-005 | arbitrary values off scale, theme->var(--x) undefined, alpha on non-alpha color, Tailwind default color, Tailwind default scale key | no |
| BP | 001-003 | media query off breakpoints, responsive variant without mobile base, fixed width > smallest bp | no |
| TOKENS | 001 | generated files drifted (fixed by `crunk tokens`) | yes |
| WAIVE | 001 | `crunk:waive` without reason | no |
| GALLERY | 001-005 | missing render, unapproved, expired, rejected, undeclared route (005 = warn) | no |

Registry: a hand-written `dict[str, RuleFn]` checked by assert against
`spec.models.RULE_IDS`. GALLERY uses a separate dispatch (its input is a
Manifest). Output is sorted by (path, line, rule) (INV-005). JSX
style-prop declarations go through the same rules but are never auto-fixed.

### Autofix engine (crunk.fixes, 205 LOC)

- Rules attach FixPayloads, and `plan_fixes` groups them per file. When
  edits overlap, the first is kept and the rest are dropped with a log line.
  `apply_plans(dry_run)` writes each file atomically (tmp + rename). It
  fails fast and does not roll back.
- There are no fix tiers or safe/unsafe levels. The one gate is the
  tolerance check (fix_tolerance and color_tolerance). Only
  COLOR/SPACE/TYPE001/RADIUS/SIZE get fixes. Translucent colors are
  rewritten as `color-mix(...)`.
- Invariants: INV-FIX-01 (bytes outside the edited spans are untouched)
  and INV-FIX-02 (re-checking a fixed site is clean).

### Token export targets (crunk.tokens)

`render_css` (tokens.css with a GENERATED banner and an optional verbatim
header), `render_json` (flat JSON), and `render_tailwind` (a Tailwind
theme-mapping JSON). Naming comes from spec.naming. Optional extras are
`-rgb` alpha-channel companions and namespaced keys. `tw_defaults.py` holds
static Tailwind v3 default-key tables used for collision warnings. CSS drift
is compared byte for byte; the JSON files are compared after parsing.

### TS/TSX layer

- `crunk.semantic.ts` (2.5k LOC) has parser, symbols, bindings,
  module_graph and consteval modules. It wraps the tree-sitter Node type,
  so raw tree-sitter objects never leave the module. Syntax errors come
  back as diagnostics data, not as Err. tree-sitter is pinned `<0.26`
  because of an ABI segfault with tree-sitter-typescript 0.23.2.
- `crunk.ingest.jsx` (_ast, _classnames, _style, _consts, _tokens) pulls
  out style props and className utilities. Computed classNames are scanned
  only in their static fragments.
- `crunk.adapters` defines the FrameworkAdapter Protocol plus a registry.
  `react_ts` and `react_router` (route discovery) are the only
  implementations.
- `tailwind_runtime`: `node/helper.mjs` runs the project's own tailwindcss
  (scrubbed env, timeout, output size cap, first-run notice) and parses the
  compiled CSS with tinycss2. Without node it reports
  "unresolved-by-tailwind" rather than guessing. Results are cached
  (`cache/tailwind_runtime.py`). Note that this executes project code.
- Open epic T-0203 ("semantic, not lexical"): T-0294 will replace the regex
  utility parsing; T-0213 will add a frob policy that forbids lexical
  source analysis.

### CSS parsing

tinycss2 is used in ingest/parse.py, ingest/tailwind.py, jsx/_style.py,
rules/_org.py, rules/_layers.py, tailwind_runtime and scaffold/detect.
Unparseable CSS becomes a per-file ParseDiagnostic and the run continues.
Waivers are `/* crunk:waive RULE reason="..." */`, attached during ingest
and honored in rules.

### Gallery / playwright (opt-in)

The extra `crunk[gallery] = playwright>=1.40`, imported lazily through
`gallery/_playwright.py`. Without the extra, rendering returns
`Err(RenderError.PlaywrightMissing)`. The stages are enumerate -> render
(V*S*B PNGs, hashed) -> triage (local HTTP contact sheet, keyboard verdicts)
-> check. The `command` renderer runs external capture tools (e.g. a Gradle
task). gallery is the largest package (4.0k LOC).

### schemas/

gallery-check.v1.json and gallery-manifest.v1/v2/v3.json are JSON Schemas
for the gallery manifest and the `gallery check --json` output. They are
validated in tests (jsonschema is a dev dependency). There are no schemas
for crunk.toml or the check JSON.

## 2. Architecture

### Packages (src/crunk, LOC incl. docstrings; total 24.5k)

| Package | LOC | Role |
|---------|-----|------|
| gallery | 3983 | screen render/triage/manifest |
| rules | 2952 | rule fns + engine |
| ingest (+jsx) | 2867 | CSS/TSX/tailwind-config -> ProjectStyles |
| semantic/ts | 2476 | tree-sitter wrapper, module graph, const eval |
| app | 2077 | shell (app.py alone 1876) + AppConfig |
| spec | 1836 | crunk.toml load/validate, naming |
| tokens | 1582 | export renderers, tw defaults |
| tailwind_runtime | 1195 | node helper, doctor |
| query | 1037 | reuse analysis |
| report | 1009 | terminal/json/markdown/preview |
| adapters | 960 | framework Protocol + registry |
| cache | 789 | content-addressed store |
| scaffold | 588 | init, presets, detection |
| values | 520 | Color/Length, contrast, distance |
| fixes | 205 | edit plans |
| logging | 69 | stdlib logging + TOML dictConfig |
| __main__ | 337 | argparse |

Dependency direction (03-system-design.md, enforced by frob cycle/arch):
shell -> {report, fixes, tokens, rules, query, cache, scaffold};
report/fixes/tokens/rules/query -> {ingest, spec}; ingest -> {spec,
values}; spec -> values. The leaves are values, cache (stores opaque
strings) and logging.

### How it uses frob

| Artifact | State |
|----------|-------|
| frob.toml | profile rapid (auto-ratcheted to standard at 393 files); GATERULE001 lowered to warn; lowered testing thresholds; [vet.allow] for each dependency; [[docblocks.commands]] pointing at `_build_parser`/AppConfig for FLAGCOV; [[system]] crunk-cli min_e2e=9; 13 [[refs.entrypoint]] |
| tickets/ | 250 dirs (T-0001..T-0294, with gaps): 178 done, 41 queued, 29 dropped, 2 in-progress (T-0164, T-0225). Each has ticket.md (YAML front matter) + done-report.md |
| invariants/ | INV-001..INV-010 (YAML front matter: statement, criticality, evidence test ids) |
| frob.lock | doc-drift ack ledger (sig/body digests), stale apollo paths |
| frob-coverage.lock.json, .frob/ | coverage stamp, daemon state |
| directives in src/tests/docs | frob:tests 1364, frob:ticket 839, frob:doc 387, frob:waive 211, frob:describes 31, frob:invariant 23, frob:debt 9 |

Makefile has only install/clean/upload: "frob IS the interface" for
format, check, test and coverage.

### Borrowed from frob

- typani `Result`/`Option`/`ErrorSet` at every fallible boundary (33
  modules import typani; 18 ErrorSets). ErrorSet members are fixed enum
  values and cannot carry a payload, so error context goes into log lines.
- Logging: `get_logger(__name__)` with a TOML dictConfig, BelowLevelFilter
  and SimpleFormatter. This is a cut-down copy of frob/logging.
- Waiver DSL: `crunk:waive RULE reason=...`, explicitly modeled on
  `frob:waive`.
- Exit-code contract 0/1/2, versioned `--json`, and pydantic frozen models
  match frob's own conventions.

### Tests

1158 test functions. unit: 43 files / 20.6k LOC. integration: 13 files /
1.5k (INT-01..12, real tmp_path, no subprocess). system: 58 files / 5.8k
(E2E through the real CLI, including a wheel build). Fixtures in
tests/fixtures (web_pages, tailwind_v4, screens_v1_1, gallery005_routes).
INT-04 uses golden files; there are no markdown corpora or snapshot
library. pytest-xdist is used, and there is a known flake under
coverage+xdist (T-0202). CI: .github/workflows/{ci,release,branch-protection}.yml.

## 3. Overlap a shared Rust workspace would dedupe

| Concern | crunk today | frob today | Shared crate candidate |
|---------|-------------|------------|------------------------|
| tree-sitter parsing | semantic/ts typed Node wrapper, TS/TSX only, ABI pin pain | frob/lang/_walk_* for ~16 languages incl. typescript, css, vue | `*_parse` (grammar loading, typed node, span, ERROR/MISSING -> diagnostics) |
| spans / locations | Span half-open, Location line/col/offset | per-lang models | `*_text_size` + `*_source_file` (line index) |
| rule declare/registry/docs | dict + assert vs RULE_IDS; docs hand-written in spec table | gate registry, _KNOWN_GATE_RULES, docblocks | `*_rule` (macro-declared rules with id/family/default severity/fixable/doc), generated catalog docs |
| findings model + render | Violation (rule, severity, path, line, message, fixable, waived, suggested_token); terminal/JSON/Markdown | frob.findings Severity incl. unresolved/advisory | `*_diagnostics` + `*_render` (text/json/markdown/sarif) |
| waivers | crunk:waive + WAIVE001 | frob:waive + WAIVE00x, follow_up | one directive parser with a pluggable namespace (`crunk:` / `frob:`) |
| config loading | pydantic, unknown-key = error, --config/--root, no upward discovery | frob.toml via tomlio | `*_config` (serde deny_unknown_fields, located errors, JSON Schema emit) |
| autofix | byte-range edits, overlap-drop, atomic write, dry-run | frob format/refactor | `*_fix` (Edit/Fix with applicability tiers, conflict resolution, dry-run diff) |
| file discovery/ignore | globs, [org].ignore, css_root walk | excludes.py, gitio | `*_walk` (ignore crate, gitignore aware) |
| caching | sha256 content-addressed store, outside repo, XDG | .frob caches, coverage file cache | `*_cache` (content-addressed KV, atomic, prune) |
| CLI scaffolding | argparse, --json, --version, no did-you-mean | _cli_parsers | `*_cli` (clap helpers, global --json/--color/--verbose, exit-code enum) |
| test harness | pytest golden/E2E | pytest | `*_test` (insta snapshots, fixture-tree builder, CLI e2e runner) |
| logging | stdlib + TOML dictConfig | same plus color/quiet | `*_log` (tracing + subscriber setup, stdout/stderr split) |
| Result/ErrorSet | typani | typani | native Result + error sets; this also removes the payload-less ErrorSet limitation |
| CSS | tinycss2 | _walk_css (tree-sitter) | shared CSS tokenizer/parser crate (e.g. on cssparser or lightningcss) |

## 4. crunk-specific (stays in its own crates)

| Crate (proposed) | Contents |
|------------------|----------|
| crunk_values | Color parse (hex/rgb/hsl), weighted-sRGB distance, WCAG luminance/contrast, Length + rem/px; future OKLab/OKLCH (T-0075/T-0079) |
| crunk_spec | DesignSpec, crunk.toml model, token naming scheme, presets |
| crunk_ingest | CSS -> declarations, bucket/org model, JSX style/className extraction |
| crunk_tailwind | utility candidate parsing, default-theme tables (v3/v4), node runtime bridge, theme mapping |
| crunk_rules | COLOR/SPACE/TYPE/RADIUS/SIZE/LAYER/CONTRAST/ORG/TW/BP/GALLERY |
| crunk_tokens | css/json/tailwind exporters, drift check |
| crunk_query | find/dupes/unused/uses/color |
| crunk_gallery | manifest (schemas v1-v3), render orchestration, triage server; playwright is external, so do it as a subprocess or feature flag |
| crunk_adapters | FrameworkAdapter trait, react_ts, react_router |

## 5. Recommendation

Single monorepo (ruff/ty style). Structure: `crates/` with shared core
crates and two binaries (`frob`, `crunk`), one Cargo workspace and one
Cargo.lock.

Reasons:
- About 12 of the 14 rows in section 3 are real duplication. If they lived
  in separate repos as published crates, every change to a core API would
  need a publish/bump/adopt cycle. ruff/ty avoid that by never publishing
  internal crates.
- crunk already sets its tree-sitter pin from frob's, and was hit by the
  same ABI problem. A single lock ends that drift.
- Most of FROBLEMS.md is about frob mis-handling a downstream consumer
  (GATERULE001, the pytest PATH, cwd inference). If crunk is in the same
  workspace, frob's CI is a downstream-consumer test by construction.
- frob enforces itself. With crunk in the same tree, frob's gates run on
  crunk on every PR, which is the dogfooding FROBLEMS.md credits as "the
  best gate".

Costs and mitigations:
- Release cadence: version the binaries separately (as ruff and ty are)
  and release them with tag prefixes (`frob-v*`, `crunk-v*`). The shared
  crates stay `publish = false`.
- CI time: use path-filtered jobs (crates/crunk_* -> crunk tests; any
  shared crate change -> both), cargo-nextest, and sccache. Keep the
  node/playwright gallery tests in a separate optional job.
- Ticket ledger: use one ledger with a per-product scope field or
  prefix rather than two. Cross-product tickets (e.g. "rule registry
  macro") are common, and crunk's own FROBLEMS shows upstream markers
  (T-0023, T-0024) stranded in the wrong ledger. This needs the frob v2
  ticket store to support components/areas.
- Domain rule ids: frob v2 must let a repo declare its own rule-id
  namespaces (COLOR001 etc.) so the gate does not treat them as frob gate
  ids. In a shared repo that is even more necessary.

The two-repo option only wins if crunk needs outside contributors or a
different license or governance. Nothing in the repo suggests that.

### FROBLEMS.md: top complaints (design input for frob v2)

| # | Complaint | v2 design implication |
|---|-----------|-----------------------|
| 1 | Subprocesses spawn the global pytest, not the project venv; root cause of failed coverage runs, xdist noise, SKIPPED-UNMEASURED reverify, about 18 stale-stamp quarantines | resolve the toolchain from the project environment explicitly; never rely on bare PATH |
| 2 | Every land raises a TEST006 stale-coverage-stamp quarantine (pure ceremony) | land refreshes and carries its own stamp |
| 3 | GATERULE001 assumes every repo is frob (domain rule ids flagged) | per-repo declared rule-id namespaces |
| 4 | vet hook: blocks in "advisory" mode, ignores [vet.allow], vets the whole resolution instead of the delta, adding allow flips to enforced (cliff), VET004 entropy false positives make clean unreachable | delta-only vetting; allowlist honored everywhere; no mode cliffs |
| 5 | DOC006 scans frob-generated ticket bodies/reason strings | exempt generated ledger text, or validate when it is written |
| 6 | cwd-inferred roots: land/dispose/ticket verbs run inside a worktree hit the wrong store, creating phantom leases | always resolve the primary repo from git metadata |
| 7 | Self-citing waiver follow_up blocks the land; permanent waivers impossible (WIRE002 needs an open ticket, so T-0024 is kept open forever) | warn when written; first-class permanent waiver posture |
| 8 | Remedies that other gates reject (ROOT001 suggests a directive DSL001 rejects; TEST006 says `make coverage`, which the scaffold does not ship); scaffold fails its own check | test gate remedies against the gates; scaffold must pass check |
| 9 | Ticket-store merge conflicts on ticket.md evidence blocks (resolving --theirs clobbered evidence) | merge driver or append-only record format |
| 10 | Exclusive scope leases block parallel registry appends (SCOPE001) | shared/append lease mode; macro registries reduce hotspot files |
| 11 | COV002 adjacency/provenance edges checked only at land; re-indenting an edge counts as a passenger ticket | check at write time; whitespace-insensitive directive diffing |
| 12 | Inline vs deferred post-land sweep depends on load (one did `git reset --hard` on main) | deterministic, configured sweep mode |
| 13 | `frob format` is repo-wide while the FMT gate is diff-scoped | one scope model |
| 14 | FLAGCOV/DOC resolver imports the consumer package in frob's interpreter (manual PYTHONPATH) | parse statically; never import user code |
| 15 | Minor: evidence --accepts is 1-based but displayed 0-based; frob.lock flagged as dead by REF; auto-ratchet changes strictness with no ticket trail; `done-report` success printed as ERROR | consistency pass |

Many crunk queued tickets are frob-friction trackers rather than product
work (T-0023, T-0024, T-0194/0216/0274/0287 "post-land sweep regression
from an unattributed source", T-0237, T-0238, T-0280, T-0281, T-0291,
T-0293).

Caveats: crunk's autofix has no tiers (a shared fix crate adds them, not
inherits them); the node/Tailwind helper and the playwright gallery execute
project code and stay out-of-process after a rewrite; frob.lock still points
at `src/apollo/...` and is stale.

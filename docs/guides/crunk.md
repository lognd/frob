# crunk user guide

Status: current
Owner: crunk
Decisions: none
Audience: user

crunk is the CSS and design-token product of the goblin family, and it is part of this repository (the frob monorepo): its crates, docs and releases live here beside frob and grimble. It ships the `crunk` binary,
the `crunk-check` crate with the rule set listed in [the rules index](../reference/rules/README.md), the
`crunk.toml` schema ([config reference](../reference/config/crunk.md)) and a design-token exporter (`crunk tokens`).

## Verbs

| Verb | Needs `crunk.toml` | What it does |
|---|---|---|
| `crunk check` | yes | Runs the rule set and prints the `gob.sibling/1` document with `product = "crunk"` (`--json`), or a count summary. `--only`, `--fail-on`, `--base`, `--ticket-scope` as for `grimble check`. `--json` data carries `schema_version: "gob.sibling/1"`. `--report markdown` adds `report_markdown`, `--report json` adds the v2 machine report under `report` (`version: 2`, counts, findings), `--report slop` the slop evidence vector, and `--contrast` a `contrast` table of every role pair in every mode. |
| `crunk cache ls`, `crunk cache prune [--all]` | yes | Lists the shared check cache (path, size, row counts) or deletes rows no run of this build can hit (`--all`: every row); `--dry-run` reports only. |
| `crunk doctor` | no | Reports the crunk version, the repository root and the state of `crunk.toml`. |
| `crunk tokens` | yes | Writes, previews (`--target` css, json or tailwind) or drift-checks (`--check`) the generated token files. |
| `crunk query KIND [ARG]` | yes | Read-only questions: `find NAME` (exact, then prefix, then substring, with use counts), `component NAME` (BEM structure; unknown is exit 2), `dupes [--threshold 0.6]` (sheet pairs repeating declarations), `unused` (tokens nothing references), `uses TOKEN` (`var()` sites), `color HEX` (every palette color by redmean distance), `violations [--rule ID] [--path GLOB]` (check findings, always exit 0). `--no-cache` is accepted and a no-op: queries always ingest fresh. |
| `crunk import dtcg INPUT [--store PATH]` | no | Validates a W3C DTCG token file (names, a resolvable `$type` per token, value shapes, `{a.b}` references without cycles) and stores it losslessly (default `design/tokens.dtcg.json`); `--dry-run` validates only. A bad file is a refusal (`E-DTCG`). |
| `crunk export css [--out PATH]` | no | Prints the CSS custom-property export, or writes it to `--out`. Same render as `crunk tokens --target css`; an unknown target exits 2 naming the valid ones. |
| `crunk export tailwind [--out PATH]` | no | Prints the Tailwind theme export, or writes it to `--out`. Same render as `crunk tokens --target tailwind`; an unknown target exits 2 naming the valid ones. |
| `crunk export uss [--out PATH]` | no | Prints the Unity USS variable sheet, or writes it to `--out`. Same render as `crunk tokens --target uss`; an unknown target exits 2 naming the valid ones. |
| `crunk export csharp [--out PATH]` | no | Prints the C# constants export, or writes it to `--out`. Same render as `crunk tokens --target csharp`; an unknown target exits 2 naming the valid ones. |
| `crunk export dtcg [--store PATH] [--out PATH]` | no | Prints the stored DTCG document, or writes it to `--out`; import then export equals the input up to key order. |
| `crunk rename ID NEW` | no | Renames a `[palette]` colour, a `[layers]` token, a `[typography.stacks]` font family (`--font-family-mono` to `--font-family-code`) or a custom token defined in `design/tokens/*.toml` (`--brand-ink` to `--brand-text`; the new name must stay in the same group, and `{brand.ink}` aliases are retargeted, dotted and quoted keys included) and rewrites every reference in one all-or-nothing write: the `crunk.toml` key and role names, stylesheets under `css_root`, `[jsx] globs` sources, `design/**/*.toml` specs, `var(...)` uses in `design/**/*.html` scenes, and the regenerated token exports. CRLF files keep their line endings. Comments and unrelated strings are left alone and `--color-ink-bg` is not touched by renaming `--color-ink`. `--dry-run` previews. Derived tokens (colour `-rgb` channels, the base font stack, `--space-N` and `--font-size-N` scale steps) are refused with `E-RENAME-DERIVED` and a reason naming the source to change instead. Refusals: `E-RENAME-NAME`, `-MISSING`, `-SAME`, `-EXISTS`, `-KIND`, `-DEF`, `-DERIVED`. |
| `crunk edit FILE --patch PATCH.json` | no | Applies an RFC 6902 JSON Patch to a `*.screen.toml`, `*.component.toml` or `design/content/*.toml` file. Array elements are addressed by `id` (else `name`), e.g. `/key/home.title/text`. The patch is applied in memory, the result is re-validated by the file's schema and written atomically; the output carries a unified diff and the findings of a fresh check restricted to the touched ids. Only the keys the patch changes are rewritten: comments, spacing, key order and line endings elsewhere stay byte-identical, and a file that is not valid TOML is refused unchanged. `--dry-run` previews (no findings). Refusals: `E-EDIT-PATH`, `-READ`, `-PATCH`, `-SCHEMA`, `-WRITE`. |
| serve patch tool `crunk_edit_patch` | yes | The same engine as `crunk edit`, exposed as an opt-in write MCP tool (`crunk::serve_patch::PatchTool`): arguments `file`, `patch` (an array of RFC 6902 operations) and optional `dry_run`. The reply is the diff and the findings of the touched nodes only; a patch or schema failure returns an error result (`code`, `file`, located `message`, `written: false`) and writes nothing. In a read-only session the tool is not listed and a call is refused as an unknown tool. |
| `crunk new component\|screen\|flow\|token NAME [--from FILE]` | no | Scaffolds one design file under `design/components`, `screens`, `flows` or `tokens` (`NAME.component.toml`, `NAME.screen.toml`, `NAME.flow.toml`, `NAME.toml`). NAME is a lowercase identifier (`a-z`, digits, `-`, `_`, starting with a letter, 64 characters at most). The skeleton, or the `--from` copy of an existing file of the same kind with its `name`/`id` set to NAME and `status`/`content_hash` dropped, is validated by the kind's schema before anything is written (a flow file is `name`, `nodes` as unique `screen:state` strings and `edges` with `from`, `to`, `trigger` and optional `action` and `motion`; a flow error names its code and key path, for example `E-FLOW-DANGLING at edges[1].to`, and cycles are allowed). An existing target is never overwritten; a refusal writes nothing. `--dry-run` previews. Refusals: `E-NEW-NAME`, `-EXISTS`, `-FROM`, `-PATH`, `-SCHEMA`, `-WRITE`. A file created in the instant between the existence check and the atomic rename can be replaced. |
| `crunk extract-token LITERAL [--name KEY] [--scale SCALE]` | no | Promotes a hex colour (`#abc` or `#aabbcc`, any case) to a `[palette]` token (default key `c<hex>`), or a px/rem length (`16px`, `1rem`) to a `[scales]` step (`--scale spacing` (default), `font-sizes` or `radii`; rem is stored as px via `root_font_size`), and rewrites its uses in stylesheets and JSX sources to `var(--TOKEN)`. Lengths match the same unit only (`16px` does not rewrite `1rem`) and normalise case and number form (`16PX`, `1.0rem`, `.5rem`); negatives, identifier fragments, `url(...)`, `@media`/`@container`/`@supports`/`@import` preludes, comments and strings are skipped. Durations are refused because `crunk.toml` has no duration table. `--dry-run` previews. Refusals: `E-EXTRACT-LITERAL`, `-NAME`, `-EXISTS`, `-DEF`, `-SCALE` (flag with a colour), `-DURATION` (`ms`, `s`), `-UNIT` (`%`, `em`, ...), `-ZERO`, `-NEGATIVE`. |
| `crunk map` | yes | The style inventory bucketed by `[org] buckets` order, plus strays. |
| `crunk explain NAME` | yes | Value, group, definition file, `var()` sites and utilities of one token; an unknown name exits 2 and lists close matches. |
| `crunk gallery enumerate` | yes | Opt-in (`gallery` feature): lists the spec's `(screen, state, platform)` cells; `--screen`, `--state`, `--platform` narrow it. |
| `crunk gallery render` | yes | Opt-in: renders the selected cells to PNGs under `--out` (default `gallery/renders`) and records path and SHA-256 in the manifest; a changed image clears that cell's verdict. |
| `crunk gallery triage` | no | Opt-in: serves a local contact sheet on `127.0.0.1` (`--port`, default 8765) and saves keyboard verdicts (`a` approve, `r` reject, `p` pending, arrows move, Finish saves) to the manifest as v3 with `--reviewer` and optional `--expires-in DAYS`. Blocking std-only server, no async runtime; every request needs the per-run token and a loopback `Host`. |
| `crunk gallery check` | yes | Opt-in (`cargo install crunk --features gallery`): checks `gallery/manifest.json` (`--manifest`) against the spec's cells with GALLERY001 to GALLERY005 (`--route` repeats, feeding GALLERY005). The default build refuses with `E-GALLERY-NOT-BUILT` and that remedy. |
| `crunk preview` | yes | Prints the palette, spacing, font-size and radius scales, font stacks and layers as a terminal sheet. `--color always` adds truecolor swatches; `NO_COLOR` set suppresses every escape code. |
| `crunk diff OTHER` | yes | Compares the generated tokens with those of the spec in directory (or file) `OTHER`: `+ NAME VALUE` added, `- NAME VALUE` removed, `~ NAME CURRENT -> OTHER` changed, or `no differences`. Always exit 0. |
| `crunk render` | yes | Solves each screen/state/platform scene (`design/scenes/<screen>.<state>.scene.html`, else `<screen>.scene.html`) and writes one layout-solve JSON per cell under `--out` (default `.crunk/render`). `--engine solve` is the default; `--engine browser` needs the gallery feature. A screen with no scene file exits 2 naming it. Output order is the same for every `--jobs`. |
| `crunk snapshot` | no | Solves the same cells and compares them with the baselines under `--baselines` (default `design/baselines`). A missing baseline fails naming its path; a differing one lists each changed node id with field deltas. `--update` writes only the baselines whose bytes changed. |
| `crunk init [--preset default\|mono] [--force]` | no | Scaffolds `crunk.toml` (the preset plus detected `[jsx]` and `[tailwind]` sections), the `[org] buckets` directories under `css_root`, a starter `base/reset.css` and the token files; the result passes `crunk check`. An existing `crunk.toml` is a usage error (exit 2) without `--force`. |
| `crunk fix [--dry-run]` | yes | Applies the machine-applicable (Tier A) fixes of `crunk check` to stylesheets; `--dry-run` prints the diff and writes nothing. |
| `crunk review` | yes | Lists the screen states that need a human review and what changed since the last ack. |
| `crunk ack [SUBJECT]...` | yes | Records a human review of screen states (`screen/<id>/<state>` or a screen id) into `crunk.lock`; needs a terminal unless `--non-interactive`; `--dry-run` reports only. |
| `crunk rule catalog` | yes | Lists the std pack rules that `[packs]` in `crunk.toml` switches on. |
| `crunk schema` | no | Built-in: the JSON Schema of a verb's output. |

Query output is the gob envelope: `data` holds `{kind, results}` (`query`), `{buckets, strays}` (`map`)
or `{results}` (`explain`); the Python `version` field is dropped, rows are otherwise identical.
`query violations` omits unresolved findings (rules that could not run), reports line 0 for a
finding anchored at the start of a file, and words its messages as the Rust rules do. `dupes`
scores whole sheets by shared `(property, value)` declarations over the smaller sheet.

Global flags (`--json`, `--text`, `--format`, `--color`, `-v`, `--version`) come from
`gob-cli`; `--version` prints the workspace lockstep version.

## Information architecture (opt-in UX pack)

`design/ia/sitemap.toml` lists the project's routes: `home` (default `/`), `max_depth` (default 3, home
is depth 0) and `[[pages]]` with `route`, `label`, optional `screen` (a screen id; without it the
screen whose `entry` has the same route shape serves the page), optional `parent` and `links`.
A dynamic segment is `:id`, `[id]` or `{id}`; only the position of dynamic segments matters.
`design/ia/content-model.toml` lists content `[[types]]` with `name` and `fields`.

The UX IA checks (`crunk_rules::ux::ia::check_ia`) report a route without a screen, a screen
without a route, a code route absent from the sitemap, a page deeper than `max_depth` (once per
deepest path), sibling labels equal ignoring case, and pages unreachable from home over parent and
`links` edges. A parent cycle is a schema error (`E-IA-CYCLE`). When routes in code cannot be
discovered the code comparison is reported as unresolved, never clean. A project with no sitemap
gets no IA findings.

## Exit codes (docs/design/shared/cli-contract.md section 2)

| Code | Meaning here |
|---|---|
| 0 | ok |
| 1 | `check` found findings at or above `--fail-on` |
| 2 | usage error |
| 3 | `E-NO-CONFIG`: no `crunk.toml` at or above the working directory (an empty file is a valid config), or `E-CONFIG` for a malformed one |
| 4 | internal error |

## Rules

Rules are declared with `#[rule]` in `crunk-rules` (two files per rule, `src/rules/<id>.rs` and
`<id>.md`, the index generated by `cargo dev gen rules-index`); the registry page is
[the rules index](../reference/rules/README.md). Families and their shared metadata (check tiers, whether a
waiver applies, the severity at the release gate) are `crunk_rules::family::FAMILIES`.

- `[lint]` of `crunk.toml` sets a rule to `error`, `warn` or `off`; `off` drops the rule's findings.
- `crunk:waive RULE reason="why"` in a CSS, TSX or HTML comment suppresses that rule at the
  declaration it trails or precedes (an `accept` exception, counted in the report). A waiver with
  no reason (or a blank one) grants nothing and is WAIVE001; organisation (ORG), waiver, token and
  gallery families cannot be waived. This differs from the Python crunk, where a reasonless waiver
  still silenced its rule.
- Findings are reported ordered by file, then position, then rule.

## CI

<!-- frob:ticket 01M43ARWT173GKANZ322H41VF1 -->
Path-filtered jobs and the optional node job: [crunk in CI](#crunk-in-ci). Moving from the Python crunk, verb by verb: [from the Python crunk](crunk-from-python.md). Switching a consumer from the Python
crunk (CI step), with the reasoned divergence list: [the hullbreach exit page](crunk-hullbreach.md).

## Boundary

No frob crate is a dependency of `crunk` or `crunk-check` (`crates/crunk/tests/boundary.rs`).

## Gallery (opt-in)

The `gallery` cargo feature of `crunk` pulls in `crunk-gallery`; it is off by default so the default
binary and the PyPI wheel stay small. The crate holds the manifest (v1 per-screen approvals, v2
per-state cells with a hashed render, v3 attributed verdicts that can expire; schemas
`docs/schemas/crunk-gallery-manifest-v{1,2,3}.json`), the cell enumeration (screens, then states,
then platforms, in spec order; `applies_to` on a state narrows its screen's, `tag:<name>` expands
to tagged platforms) and the check report (`docs/schemas/crunk-gallery-check-v1.json`).

| Rule | Severity | Meaning |
|---|---|---|
| GALLERY001 | error | a cell has no render |
| GALLERY002 | error | a render is not approved (no verdict, or pending) |
| GALLERY003 | error | an approval's `expires_at` is before today |
| GALLERY004 | error | a render was rejected |
| GALLERY005 | warn | a router route has no `[[screen]]` with that entry (query and one trailing slash ignored; `*` never needs a screen) |

Not yet verified: the manifest shapes and cell order were rebuilt from the design notes and the
shipped fixtures because the Python source is not in this checkout; the parity check is tracked as
a follow-up ticket. Rendering is separate work (render orchestration).

## Scene ingest and layout solve

The T1 solver corpus lives in `crates/crunk-layout/tests/corpus/`: scenes (`*.scene.html`) are solved twice at 375 and 1280 px, must be byte-identical, and must match the committed `baselines/<scene>.<width>.layout.json`. LAYOUT001/002 findings come from `crunk_layout::findings` (`child_overflows`, `sibling_overlaps`), the same functions the crunk-rules LAYOUT001/002 rules call on the solver output of each `design/scenes/*.scene.html`, so the rules and the corpus cannot disagree; they are compared, with the RESP root-width and GX002-005 findings, against `baselines/<scene>.findings.json`. No browser is involved. Rewrite baselines with `CRUNK_UPDATE_BASELINES=1 cargo nextest run -p crunk-layout -E 'binary(corpus)'`.

Solver-vs-browser parity is a separate gate: `crates/crunk-gallery/src/parity.rs` compares the solver's boxes with the browser's by node id within a 1.0 px tolerance and names every node that differs or is missing on one side. It runs as the `crunk-parity` CI job; locally it skips when Playwright is unavailable, and `CRUNK_REQUIRE_PLAYWRIGHT=1` turns that skip into a failure.

`crunk-ingest::scene` reads a JSON scene description of boxes and text runs and solves it with taffy into a layout-solve JSON. The LAYOUT and RESP rules read that solve; it does not render anything.

### Scene format

```json
{ "viewport": { "width": 320, "height": 480 },
  "root": { "id": "page", "kind": "box", "style": { "direction": "column", "padding": 16 },
            "children": [ { "id": "title", "kind": "text", "text": { "content": "Hello", "font_size": 20 } } ] } }
```

- `kind` is `box` or `text`; ids are unique strings.
- `style` keys: `display` (`flex`, `block`, `none`), `direction` (`row`, `column`), `wrap`, `gap`, `padding`, `margin`, `width`, `height` (pixels, `"auto"` or `"N%"`), `grow`, `shrink`. Unknown keys are rejected.
- `interactive` (default false) marks a pointer or touch target; LAYOUT005 sizes it and LAYOUT004 keeps it inside the safe area. A scene's top-level `safe_area` (pixels, default 0) is the inset from every viewport edge that text and targets must stay inside.
- Project scene files live at `design/scenes/*.scene.json`; LAYOUT003-005 and RESP001 solve each one and RESP001 matches their viewport widths to `[breakpoints]`. LAYOUT001/002 instead read the crunk-layout solve of the HTML scene documents at `design/scenes/*.scene.html`.
- A `text` node carries `text.content`, `text.font_size`, optional `line_height` (default 1.2) and `max_width`.

### HTML scene documents

- Authored scenes live at `design/scenes/**/*.scene.html`: nested directories are searched, the suffix matches in any case, and ignore files are honored. Each file is read as bytes and parsed through `crunk_scene::parse_scene_bytes`; results are ordered by project-relative path.
- A file that cannot be loaded is never a crash. SCENE005 reports it as a finding at the file: unreadable, over the 4 MiB size cap, not UTF-8, no elements (empty, blank or comments only), or a name (file name without the suffix, case-insensitive) already used by an earlier file. The loadable files are still checked by the other SCENE rules.

### Text metrics

There is no font engine, so the solve is identical everywhere: a character is `0.6 * font_size` wide, a line is `font_size * line_height` tall, and a run wraps at `max_width`.

### Layout-solve JSON

`viewport_width`, `viewport_height` and `nodes` in document order. Each node has `id`, `parent`, `kind`, absolute `x`, `y`, `width`, `height` in whole pixels, and `text` (`content`, `font_size`, `lines`) for text runs. Serialization is stable: the same scene yields byte-identical output.

### Not yet

Grid layout, per-side padding and margin, CSS-derived styles and a CLI verb are follow-up work.

## The crunk-web pack

The `crunk-web` std pack holds crunk's web markup and asset rules in GRL (design D89). It is
opt-in: the `[packs] crunk_web` switch is off by default, and `crunk_check::packs::PacksSwitch`
is read from `crunk.toml` by `crunk_spec` (`DesignSpec::packs`) and listed by `crunk rule catalog`.

### Families

| Family | Rule | Checks |
|--------|------|--------|
| A11Y | A11Y101 | `img` elements carry an `alt` attribute |
| A11Y | A11Y102 | the `html` element carries a `lang` attribute |
| A11Y | A11Y103 | `iframe` elements carry a `title` attribute |
| SEO | SEO101 | `a` elements carry an `href` attribute |
| SEO | SEO102 | a `link rel="canonical"` carries an `href` attribute |
| SEO | SEO103 | a `meta name="description"` carries a `content` attribute |
| LAUNCH | LAUNCH101 | no lorem-ipsum placeholder text ships |
| WEBPERF | WEBPERF101 | `img` elements carry a `width` attribute |
| WEBPERF | WEBPERF102 | `img` elements carry a `height` attribute |
| WEBPERF | WEBPERF103 | `img` elements carry a `loading` attribute (lazy loading) |
| WEBPERF | WEBPERF104 | an external classic `script` carries `async` or `defer` (no render-blocking) |
| WEBPERF | WEBPERF105 | a font `link rel="preload"` carries `crossorigin` |
| WEBPERF | WEBPERF106 | an `src` attribute does not name a legacy image (`.png`, `.jpg`, `.jpeg`, `.gif`); serve WebP or AVIF |
| WEBPERF | WEBPERF107 | a stylesheet `link` carries a `media` attribute (no render-blocking) |

Each family ships worked rules; more land under the same prefixes. WEBPERF1xx covers markup and
assets only (server-side WEBPERF lives in grimble-websec, 2xx). A file type with no adapter (for
example markdown) is reported NotApplicable by each rule's `notapplicable` example, never clean.

### Layout

- `packs/crunk-web/pack.toml`: the manifest (name, version, families, rule globs).
- `packs/crunk-web/rules/*.grl`, `rules/a11y/*.grl`, `rules/seo/*.grl` and `rules/webperf-assets/*.grl`: one rule per file, each with a firing, a clean and a
  not-applicable example. A rule without a firing and a clean example fails to compile (GRL011).

### Embedding and lock

`crates/crunk-check/src/packs.rs` embeds the manifest and rules with `include_str!`.
`packs::plans()` compiles them, `packs::catalog()` yields the `crunk rule catalog` rows
(pack, family, rule; empty when the switch is off), and `packs::locked(root)` returns the lock
entry after `verify_tree(root)` confirms the tree on disk equals the embedded sources. The lock
digest is the gob-packs tree digest of `packs/crunk-web`.

## crunk in CI

`.github/workflows/ci.yml` starts with a `changes` job that maps the diff to job sets
(`.github/scripts/plan-jobs.py`, tested by `crates/gob-dev/tests/ci_plan.rs`). The mapping is data in
`crates/gob-dev/changes.toml`, read by both the script and `gob_dev::changes` (`cargo dev changes`,
`cargo dev ci --since <base>`), with one unit test per class. It is a job-level
filter, never a workflow `paths:` filter: a workflow that never starts leaves the commit with no
checks, and a skipped job counts as passing.

| Change | `rust` (whole workspace, Linux and Windows) | `crunk` | `crunk-node` (optional) |
|---|---|---|---|
| only `changelog.d/`, `notes/`, `docs/design|decisions|migration/` | skipped | skipped | skipped (the `docs-only` job runs fmt, gen check and frob check instead) |
| only `crates/crunk*` or `docs/guides/crunk*.md` | skipped | runs | when the node runtime changed |
| anything else, including every `crates/gob-*` crate | runs (all three products) | skipped | no |

- The `crunk` job runs rustfmt, clippy, rustdoc and nextest for the crunk packages only (the
  `CRUNK_PACKAGES` list, kept equal to the `crates/crunk*` directories by a test) and the
  one `cargo dev gen all --check`, which covers all three products. frob and grimble tests do not
  run for a crunk-only change.
- The `crunk-node` job runs the node Tailwind runtime tests with `CRUNK_REQUIRE_NODE=1` (a missing
  node fails instead of skipping). It is `continue-on-error`, nothing lists it in `needs`, and it
  must never be a required check, so red or skipped never blocks a merge or the dev channel. The
  playwright gallery tests join it when the gallery port lands.
- The `docs-only` job runs only when every changed path is in a docs class; any other change
  (including a workflow edit, which also sets the `workflows` output) selects the full set.
- An unreadable diff base runs everything.
- A crunk-only push does not refresh the dev channel (the dev jobs wait for `rust`, and a skipped
  job skips its dependants); the next change outside crunk does.
- A frob-only or grimble-only change still runs the whole workspace; scoping the workspace job by
  product needs a package filter in `cargo dev ci` and is tracked separately.

# crunk design research, 2026-10-08

Scope: research only. No code, no tickets, no repo modified (one scratch copy of
hullbreach crunk.toml was run through the built crunk binary inside the scratchpad).
ASCII only. Claims I did not confirm against a primary source are marked [verify].
Fetched-and-read sources are listed per section; "from memory" means not re-fetched.

## 0. Honesty block (denominators and coverage)

| Inventory | Denominator (how established) | Covered | Gaps |
|---|---|---|---|
| A. Figma capabilities | 16 groups listed in the brief, 78 rows below | all 16 groups, 78 rows | Figma Help Center pages (help.figma.com) returned 404 or shell pages to curl, so row text for UI features is from memory + developers.figma.com pages that did load; those rows are tagged [verify] where specific |
| B. Comparables | 30 tools/specs named in brief (incl. Figma plugin list) | 30 | only DTCG, Style Dictionary, Penpot, Storybook (docs source), axe-core, Unity USS/TSS, taffy, Game Accessibility Guidelines were fetched; rest from memory with [verify] |
| C. Python crunk | 12 top-level verbs (argparse `add_parser` count in src/crunk/__main__.py), 13 sub-verbs (gallery 4, cache 2, query 7), 30 rule ids in 13 families (catalog table in docs/design/02-specification.md and crates/crunk-spec/src/catalog.rs agree), 21 config table headings (docs/crunk/config.md `##` count) + `[layers]` | all enumerated | Python src not read line by line; behaviors taken from docs/commands/*.md and docs/design/subsystems/*.md |
| D. hullbreach | platform/ (crunk.toml, web/src 12 files) and game/ (5 prefabs, HudPrefabBuilder, HudColor) | all of web/src; UI-relevant game files | no Unity run; no scene YAML read |
| E. Synthesis | rows = union of A/B/F capabilities | below | proposal, not verified by prototype |
| F. Design cycle + GX | 8 phases in the brief + 10 GX topics + 4 Unity topics | all | industry practice rows from memory |

Pending: 0. Blocked: help.figma.com pages (fetch returned 404/shell) -- not dropped, covered
from developers.figma.com + memory with tags. Phase-2 verdict is in section 9.

---

## A. Figma capability inventory

Sources fetched: developers.figma.com/docs/rest-api/ (+ /variables/, /variables-endpoints/,
/rate-limits/, /scopes/), /docs/plugins/api/Variable/, /docs/figma-mcp-server/ (+ /write-to-canvas/,
/tools-and-prompts/), /docs/code-connect/quickstart-guide/. Rest from memory.

"Text equivalent" = what an agent-first, text-file-based crunk would hold.

### A1. Document model
| # | Capability | What it is | Text-file equivalent |
|---|---|---|---|
| 1 | File / pages | A file holds pages (canvases) of top-level nodes | one `design/` dir; a page = a folder or `*.screen.*` group |
| 2 | Frame | Container with size, clip, fills, layout; the unit of a screen/artboard | `<frame>` element in a scene file with explicit size/constraints |
| 3 | Group | Lightweight selection group, no layout/clip of its own | omit; use a plain container (groups are an anti-pattern for lintability) |
| 4 | Section | Organizing region on canvas, also the "ready for dev" unit | folder/tag + `status` field in screen spec |
| 5 | Vector network | Paths as graph (not just lists) with fills/strokes | SVG `<path d>`; store as .svg asset, lint only bounds/colors |
| 6 | Boolean ops | union/subtract/intersect/exclude of shapes | bake to SVG path at export; keep source as asset, not model |
| 7 | Masks | A layer clipping siblings above it | CSS `clip-path` / overflow clip on the container |
| 8 | Shapes | rect/ellipse/polygon/star/line, corner radius (incl. per-corner, smoothing) | scene primitives; radius is a token |
| 9 | Text nodes | Styled runs, truncation, auto-resize modes | `<text>` with a style ref; runs only when needed |
| 10 | Image fills / nodes | Raster fill with scale mode (fill/fit/crop/tile) | asset ref + `object-fit`; lint: exists, size, alt |
| 11 | Node IDs / naming | Every layer has an id and free-text name; naming is unconstrained | stable human ids; lint naming (see COMP/STRUCT lints) |
| 12 | Hide/lock/opacity/blend | Layer-level flags, blend modes | `hidden`, `opacity`, `blend` attrs; lint hidden-leftovers |
| 13 | Rotation / flips / transforms | Per-node affine | allow only on leaf/decor; lint transform on layout children |

### A2. Layout
| # | Capability | What it is | Text-file equivalent |
|---|---|---|---|
| 14 | Auto layout (h/v) | Flexbox-like stack: direction, gap, padding, alignment, hug/fill/fixed sizing | `display:flex` semantics: `layout = "row"|"col"`, `gap`, `pad`, `align`, sizing modes `hug|fill|<px>` |
| 15 | Auto layout wrap | Multi-line flow with row gap | `wrap = true`, `gap`/`row-gap` |
| 16 | Min/max width/height | Constraints on auto-layout children/frames | `min-w`, `max-w`, ... as tokens or px |
| 17 | Absolute-position children | Child opts out of auto layout, positioned with constraints | `position = "absolute"` + anchors; lint overuse |
| 18 | Constraints (non-auto-layout frames) | pin left/right/top/bottom/center/scale | anchors on absolute children |
| 19 | Layout grids | Column/row/grid overlays on frames (count, gutter, margin) | `[grid]` per breakpoint: columns, gutter, margin; lint snap to grid |
| 20 | CSS Grid layout (auto layout "grid" flow) | Figma added a grid auto-layout mode [verify date/rollout] | `display:grid` track definitions |
| 21 | Responsive resize | Frame resize applies constraints/auto-layout live | same scene rendered at N viewports (platform list) |
| 22 | Aspect ratio lock | Fixed ratio | `aspect = "16/9"` |
| 23 | Spacing between / tidy up | Editor helpers | n/a (CLI fix verb) |

### A3. Components
| # | Capability | What it is | Text-file equivalent |
|---|---|---|---|
| 24 | Main component / instances | Master + linked copies | `components/<name>.component` + `<Name .../>` usage in scenes |
| 25 | Overrides | Instances override text, fills, visibility, nested instances | named props only; lint "detached/raw override" |
| 26 | Variants | A component set with property matrix (e.g. size=sm/md, state=hover) | `variants { size = [sm, md, lg]; state = [...] }` + per-combo style table |
| 27 | Boolean property | toggles a layer's visibility | `bool` prop |
| 28 | Text property | exposes text content | `text` prop |
| 29 | Instance-swap property | swap nested instance, with preferred instances | `component<Icon>` prop typed by allowed set |
| 30 | Variant property | picks variant | `enum` prop |
| 31 | Slots | Slot properties let instances hold arbitrary content in a designated region (introduced 2025; rolling) [verify] | `slot` prop with allowed-children constraint |
| 32 | Component description / docs links | Free text + doc URL | `doc` field |
| 33 | Nested instances, detach | Components in components; detach breaks link | lint detach equivalent: inline copy of a component's anatomy |
| 34 | Interactive components | Variants with in-component prototype transitions (hover->pressed) | `states` table + `on:` transitions |
| 35 | Component libraries | See A8 | package/workspace import |

### A4. Variables and styles
| # | Capability | What it is | Text-file equivalent |
|---|---|---|---|
| 36 | Variable types | Color, Number (float), String, Boolean (REST: COLOR, FLOAT, STRING, BOOLEAN) (rest-api/variables) | DTCG types: color, dimension, number, fontFamily, fontWeight, duration, cubicBezier, string-like extensions |
| 37 | Collections | Named group of variables sharing modes | one DTCG file or group per collection |
| 38 | Modes | Per-collection value sets (light/dark, density, brand) | DTCG resolver "modifiers"/contexts (designtokens.org resolver module) |
| 39 | Aliasing | Variable references another variable (primitive -> semantic) | DTCG `{group.token}` alias |
| 40 | Extended collections | A collection can extend another and override values per mode (Plugin API Variable page mentions "extended collection") | resolver set layering / `$extends` |
| 41 | Scoping | `scopes` restrict which fields can bind a variable (fill, corner radius, gap, text content, etc.) | `scopes = ["fill","gap"]` metadata; lint wrong-scope binding |
| 42 | Code syntax | Per-platform names (WEB, ANDROID, iOS) stored on a variable (Plugin API `codeSyntax`) | export name map per target (css var, USS var, swift) |
| 43 | Publishing hidden | `hiddenFromPublishing` | `private = true` |
| 44 | Bound variables | Nodes record `boundVariables` | scene attr `fill="{color.surface}"` |
| 45 | Variables in prototypes | Variables drive conditionals/set-variable actions | see A7 |
| 46 | Styles: color/paint | Named paint styles | token or `fill` preset |
| 47 | Styles: text | Typeface, size, weight, line-height, tracking, case, decoration, paragraph spacing | DTCG `typography` composite |
| 48 | Styles: effect | Shadows, blurs | DTCG `shadow` composite |
| 49 | Styles: grid | Layout-grid presets | `[grid]` presets |
| 50 | Variables REST API | GET local/published variables, POST bulk create/update/delete; Enterprise full-seat only; scopes file_variables:read/write (rest-api/variables, variables-endpoints) | `crunk tokens` import/export; the Enterprise gate is a strong reason a text source of truth is needed |

### A5. Typography, effects, images
| # | Capability | What it is | Text-file equivalent |
|---|---|---|---|
| 51 | Typography features | Font family/weight/italic, size, line height (px/%/auto), letter spacing, paragraph spacing/indent, case, decoration, truncation + max lines, text auto-resize, OpenType features (ligatures, tabular nums, stylistic sets) , variable-font axes [verify list], vertical trim | typography tokens + `font-feature-settings`, `font-variation-settings` |
| 52 | Text rendering notes | Missing-font warnings; font fallback | lint font declared + licensed + file present |
| 53 | Effects | Drop/inner shadow, layer blur, background blur, noise/texture/glass [verify newer ones] | shadow token; restrict blur on perf-sensitive targets |
| 54 | Gradients, fills, strokes | linear/radial/angular/diamond; stroke align/dash/caps/joins | DTCG gradient/strokeStyle/border |
| 55 | Images | Upload, fills, crop, filters (exposure, contrast, ...), video fills | asset manifest with dimensions/hash |
| 56 | Export settings | Per-node PNG/JPG/SVG/PDF @1x/2x | `exports` table; render verb |

### A6. Prototyping
| # | Capability | What it is | Text-file equivalent |
|---|---|---|---|
| 57 | Flows | Named starting points + connections | `flow` file: node list + edges (screen/state ids) |
| 58 | Triggers | click, hover, press, drag, key/gamepad, mouse enter/leave, after delay | `on = "click"` etc.; includes `gamepad:` for GX |
| 59 | Actions | navigate, open overlay, swap overlay, back, scroll to, open link, set variable, conditional | `do = [...]` list |
| 60 | Transitions | instant, dissolve, move/push/slide, smart animate, easing + duration | motion tokens (duration, easing) |
| 61 | Smart animate | Matches layers by name across frames and tweens | match by stable id across states; lint unmatched ids |
| 62 | Variables + conditional logic in prototypes | set variable, if/else on variables/expressions | small expression DSL; or reject in v1 (test via real app) |
| 63 | Scroll / overflow / sticky / fixed | Overflow scrolling, fixed children | CSS overflow/position |
| 64 | Presentation / device preview | Play on device | n/a (render verb) |
| 65 | Motion (new product) | Figma Motion keyframe animation, exposed via MCP get_motion_context (tools-and-prompts) | `motion` spec: keyframes + tokens |

### A7. Dev Mode
| # | Capability | What it is | Text-file equivalent |
|---|---|---|---|
| 66 | Inspect | CSS/iOS/Android snippets, spacing, tokens used | `crunk explain <node>` |
| 67 | Measurements | Distances between layers | `crunk measure <a> <b>` from layout solve |
| 68 | Annotations | Notes/measurements pinned for devs | `notes` array on node/screen |
| 69 | Ready for dev | Status per frame/section; change tracking vs last-ready | `status = "draft|ready|changed"` + content hash; lint ready requires all lints green |
| 70 | Code Connect | Maps Figma components to code components (CLI "template files" approach, framework-agnostic; also Code Connect UI) (code-connect/quickstart-guide) | component spec carries `code = { path, export }`; verify existence statically |
| 71 | Dev resources | links from nodes to tickets/code (REST: Dev Resources endpoints) | `links` on component/screen |
| 72 | MCP server | Remote MCP: read tools (get_design_context, get_variable_defs, get_screenshot, get_metadata, search_design_system, get_code_connect_map ...) and write tools (use_figma, generate_figma_design, create_new_file, generate_diagram, add_code_connect_map ...) (figma-mcp-server/tools-and-prompts) | crunk MCP/CLI with same read/write split |

### A8. Libraries, versioning, collaboration
| # | Capability | What it is | Text-file equivalent |
|---|---|---|---|
| 73 | Libraries / publishing | Publish components, styles, variables; consumers get update prompts; swap libraries | design-system package (git repo / crate) with semver; `crunk` lock of tokens version |
| 74 | Version history | Named versions, autosave history; REST "Version history" endpoint | git history; tagged releases |
| 75 | Branching and merging | Branches of a file with merge review (Org/Enterprise) | git branches; text-mergeable files are the whole point |
| 76 | Comments | Pinned threaded comments; REST comments endpoints; webhooks | `review/*.toml` comments anchored to ids (or tickets) |
| 77 | Plugin API | Full read/write scene access in JS in the editor (Plugin API reference; Variable API etc.); runs in the editor, not headless | scripted patches against the text model, run headless |
| 78 | REST API | Read files (node tree JSON), images export, comments, components/styles, variables (Enterprise), webhooks, dev resources, library analytics (rest-api); rate-limited by seat/plan tier since 2025-11-17 (rest-api/rate-limits) | file system + git; nothing to rate limit |

Agent read/write summary for Figma (A, for the matrix): READ is broad (REST file JSON, MCP
get_design_context); WRITE to canvas is now possible through MCP `use_figma`, which executes
Plugin-API JavaScript in a file; it needs a Full seat, has a 20kb per-call output cap and no
asset import yet (figma-mcp-server/write-to-canvas, fetched 2026-10-08). Variables write via
REST requires Enterprise (rest-api/variables). Accessibility in Figma is mostly plugin-based
(Stark, Able, A11y - Color Contrast Checker) plus Dev Mode annotations; Figma itself has
contrast in the color picker, no built-in lint [verify]. The take-away: Figma is now agent
writable but remains a closed, binary, seat-priced source of truth with no batch lint; that
is crunk's wedge.

---

## B. Comparable tools and specs

| Tool | What it is / data model | Lint or check it runs | Headless batch? |
|---|---|---|---|
| Penpot | Open source (MPL-2.0 [verify]) design tool; files > pages > shapes tree, components, tokens; SVG/CSS-native: flex/grid layout in the model, boards = frames. Docs: help.penpot.app/technical-guide/developer/data-model/ (read). `.penpot` file format is a documented zip of JSON (3.02.01 in the same TOC). Has an MCP server ("Any agent can design in Penpot", penpot.app/dev-tools) and a plugin system | none built-in beyond design-token checks [verify] | Backend RPC + export CLI exist; self-hostable; most promising import/export target |
| DTCG format | W3C Design Tokens CG. First stable version 2025.10 announced (designtokens.org home, fetched). Format module "2025.10" status: "Draft Community Group Report" (not a W3C Recommendation). `$schema: designtokens.org/schemas/2025.10/format.json`. Types: color (object with colorSpace + components, supports srgb/hsl/oklch/display-p3 etc. - color module), dimension, fontFamily, fontWeight, duration, cubicBezier, number, strokeStyle, border, transition, shadow, gradient, typography; aliases `{a.b}`; JSON-pointer refs into composites; `$extends` groups [verify: grep found none, check spec] | schema validation only | yes (pure JSON) |
| DTCG resolver | Separate module (designtokens.org/tr/drafts/resolver/ fetched): "Resolver" file describes sets and modifiers (contexts such as light/dark) and enumerates permutations; designed to dedupe values across themes. Draft status, not yet 2025.10 stable [verify exact version string] | n/a | yes |
| Style Dictionary | Token build tool (Amazon); v4 has first-class DTCG; v5 in progress for 2025.10 per styledictionary.com/info/dtcg (fetched: "latest format 2025.10 does not have full support yet") ; platforms/transforms/formats pipeline | none (transform errors, reference-not-found, name collisions) | yes (Node) |
| Tokens Studio | Figma plugin storing tokens as JSON in git (own format, "Tokens Studio format", moving toward DTCG) ; themes/sets; syncs to GitHub/GitLab | none | plugin is GUI; JSON is batch-readable; CLI `token-transformer`/SD integration [verify] |
| Storybook | Component workshop. Stories (CSF) = named states: `args` (props), `play` functions (interaction tests via testing-library), parameters, decorators. Test paths in docs (storybook.js.org/docs/writing-tests, source read): Vitest addon (needs Vite), a11y addon built on axe-core (default rules WCAG 2.0/2.1 + best practices; `region` rule off by default), visual tests via Chromatic cloud (snapshots of every story vs baselines) | axe-core per story; interaction test pass/fail; visual diff | yes: `vitest` addon / test-runner headless; Chromatic is cloud |
| tldraw | Infinite canvas SDK; records-in-a-store (shapes with typed props, `TLShape` JSON); docs list "Driving the editor", "Mermaid diagrams", "LLM documentation" (tldraw.dev/docs/shapes) | none | editor runs in browser; store JSON is plain; agent-drawable but loosely layout-less (absolute coordinates) |
| Excalidraw | JSON scene (`elements[]` with x,y,w,h, type, style); `.excalidraw` open format; Mermaid-to-excalidraw | none | JSON only |
| Framer | Hosted design+site tool; React components with property controls; code components | none public | no |
| Plasmic | Visual builder that stores design as JSON ("PlasmicLoader" or codegen to React); component props, variants, slots, tokens (plasmic.app) | none | codegen CLI exists [verify] |
| Builder.io | Visual CMS; also maintains Mitosis | none | API |
| Mitosis | Write once in JSX-like source, compile to React/Vue/Angular/Svelte/Solid/Qwik... (github.com/BuilderIO/mitosis, read) ; "Sync design systems from Figma to code" | none | yes (Node CLI) |
| Figma Code Connect | Figma<->code component mapping, template files (framework-agnostic) (developers.figma.com/docs/code-connect) | none (publish validates props) | CLI (`figma connect publish`), needs token |
| Figma "Design Lint" plugin | Community plugin (destefanis/design-lint [verify]) | Flags layers not using styles/variables: fills, strokes, effects, text styles, radii | No; runs in editor UI |
| Stark | Accessibility suite (Figma/Sketch/Adobe XD plugin + browser) : contrast, vision simulation, focus order, alt text, touch target | contrast, color blind sim, focus order, alt-text annotations [verify] | No for plugin; has CI tooling [verify] |
| axe-core | Deque rules engine on a live DOM. Rule table in repo doc/rule-descriptions.md (fetched, 4.14): ~100 rule ids, tagged wcag2a/aa/aaa, wcag21/22, best-practice (31 best-practice rows seen), includes `color-contrast`, `color-contrast-enhanced`, `target-size`, `label`, `button-name`, `image-alt`, `aria-*` | contrast, names, roles, ARIA validity, landmarks, focus traps, target size | yes (needs DOM: jsdom or browser) |
| pa11y / pa11y-ci | CLI loading pages in headless Chrome (puppeteer) running HTML_CodeSniffer or axe runner (pa11y.org) | WCAG 2.x A/AA via runners | yes, batch (pa11y-ci iterates URL list) |
| Lighthouse | Chrome audits (a11y score is a weighted axe subset; also perf, SEO, best-practices) (developer.chrome.com/docs/lighthouse/accessibility/scoring) | a11y subset of axe, CWV, SEO | yes (CLI, CI) |
| BackstopJS | Visual regression: scenarios (url, selectors, viewports, interactions) -> screenshot -> pixel diff vs reference (github.com/garris/BackstopJS) | pixel diff with threshold | yes (puppeteer/playwright) |
| Playwright visual compare | `expect(page).toHaveScreenshot()` with baselines, `maxDiffPixels`, masks, `--update-snapshots`; per-platform baseline files (playwright.dev/docs/test-snapshots) | pixel diff; also ARIA snapshots (`toMatchAriaSnapshot`) [verify name] | yes |
| Chromatic | Cloud visual testing for Storybook with human accept/reject review ("verdict" model, same as crunk gallery) | pixel diff + human approval | cloud, headless |
| taffy (Rust) | Layout library; implements CSS Block, Flexbox, Grid (github.com/DioxusLabs/taffy, read); used by Zed/GPUI and Lapce/Floem, Bevy UI; no text shaping (needs measure callback) | n/a | yes, pure Rust |
| Unity UI Toolkit | UXML (XML tree) + USS (CSS-like, supports `:root`, `--custom-props`, `var()`, `@import`, selectors) + TSS theme sheets (docs.unity3d.com 6000.0 UIE-USS*, UIE-tss, read) | UI Builder/Debugger only; no static lint | Unity batch mode only |

Takeaways from B: (1) DTCG is the interchange for tokens; Style Dictionary is the incumbent
build; neither lints. (2) Storybook = state enumeration + axe + visual; its model (component,
args, states) is the closest existing analogue of crunk's screens/states. (3) Linting of
design (as opposed to code) exists only as Figma plugins and none are headless. (4) Penpot
and Figma now both expose MCP servers: agent-authoring is table stakes; batch lint is not.

---

## C. Python crunk (predecessor) vs Rust crunk

Sources: ~/projects/crunk (src/crunk/__main__.py, docs/commands/*.md,
docs/design/02-specification.md, docs/design/subsystems/*.md, pyproject.toml),
crunk-testbed README, frob-v2 crates/crunk*, docs/crunk/*, notes/v1/crunk.md.
Rust today (verified by running target/debug/crunk 0.532.0): verbs `check`, `doctor`, `schema`
(+help); config load fully ported; ONE rule implemented (COLOR001).

### C1. CLI verbs
| Python verb | What it does | Rust status |
|---|---|---|
| `init [--preset default|mono] [--force]` | scaffold crunk.toml + buckets + reset.css + tokens; auto-detect React/TS/Tailwind | NOT ported (presets text exists in crunk-spec presets.rs, no verb) |
| `check [PATH...] [--json] [--contrast|--report] [--no-cache] [--config] [--root]` | lint; `--contrast` role table; `--report` CI view; cache | PARTLY: `check` emits gob.sibling/1 doc with COLOR001 only; no --contrast, --report, PATH narrowing (ticket-scope/--only/--fail-on/--base exist instead) |
| `tokens [--format css|json|tailwind] [--check]` | export or verify tokens; writes tokens.css, tailwind theme json, flat json; drift = TOKENS001 | NOT ported (naming + Color math exist; no renderers, no drift) |
| `fix [PATH...] [--dry-run]` | snap values to tokens within fix_tolerance; color-mix for alpha | NOT ported (COLOR001 sets fix=Manual) |
| `map [--json]` | organization inventory (buckets, components, strays) | NOT ported |
| `explain NAME [--json]` | one token: value + every use | NOT ported |
| `preview [--color]` | terminal token sheet (swatches, scale bars) | NOT ported |
| `diff OTHER [--color]` | token-set diff vs another spec | NOT ported |
| `doctor [--json]` | renderer + Tailwind truth presence | PARTLY: Rust doctor reports version/root/config state only |
| `gallery enumerate|render|triage|check` | screen approval pipeline | NOT ported (config tables only) |
| `cache ls|prune [--age|--all]` | result cache | NOT ported as verb (gob-cache exists workspace-wide) |
| `query find|component|dupes|unused|uses|color|violations` | ask the design system | NOT ported |
| (Rust only) `schema` | JSON Schema of outputs and config | new in Rust |
| global `--config PATH --root PATH` | explicit spec/root | Rust: root discovery via gob-cli; `--config` [verify] |

Count: 12 top-level + 13 sub = 25 verb forms in Python; Rust: 0 ported fully, 2 partly
(check, doctor), 1 new (schema).

### C2. Rule catalog (30 ids, 13 families; severity default in parentheses)
Ported = rule implemented in crates/crunk-check. The Rust catalog (crunk-spec catalog.rs) lists all 30
ids with the same default severities so `[lint]` overrides validate; `product_rules!` lists no
rule crates and the one rule lives in crunk-check/src/rules/color001.rs.

| Family | Ids | Meaning | Static? | Fixable (Py) | Rust |
|---|---|---|---|---|---|
| COLOR | 001 (E) literal off palette; 002 (E) `var()` undefined token | static | 001 yes | 001 PORTED (no fix payload); 002 not ported |
| SPACE | 001 (E) margin/padding/gap/inset off scale | static | yes | not ported |
| TYPE | 001 (E) font-size off scale; 002 (E) family not declared stack; 003 (W) weight undeclared | static | 001 yes | not ported |
| RADIUS | 001 (W) | static | yes | not ported |
| LAYER | 001 (E) z-index not declared | static | no | not ported |
| CONTRAST | 001 (E) role pair below floor | static (computed from palette) | no | not ported (maths in crunk-values) |
| ORG | 001..005 (E) file outside bucket; class case; component prefix; custom prop outside tokens; ungoverned stylesheet | static | no | not ported |
| TW | 001 (E) arbitrary value off palette/scale; 002 (E) theme maps to undefined var; 003 (W) alpha on non-alpha color; 004 (E) default Tailwind color; 005 (E) default scale key | static (+ node runtime for truth) | no | not ported (crunk-tailwind has candidate parsing + v3 default tables only) |
| TOKENS | 001 (E) generated files drifted | static | yes (regenerate) | not ported |
| WAIVE | 001 (E) waiver without reason | static | no | replaced by shared gob exceptions [verify parity] |
| SIZE | 001 (W) width/height off sizes scale | static | yes | not ported |
| BP | 001 (E) media query px not a declared breakpoint; 002 (E) responsive utility without mobile base; 003 (E) fixed width > smallest breakpoint | static | no | not ported |
| GALLERY | 001 (E) missing render; 002 (E) unapproved; 003 (E) expired verdict; 004 (E) rejected; 005 (W) discovered route undeclared | needs rendered artifacts + manifest | no | not ported |

Ported: 1/30. Partly (catalog row only): 29/30. Python behaviors beyond the ids: alpha handling
(translucent variant of opaque palette color conforms), channel-triplet custom props
(`40 40 40`), JSX `style={{}}` and className string/template scanning, `.ts` class-constant
scan, rem->px by root_font_size, waiver comments (`crunk:waive`), result cache.

### C3. Config tables (21 documented headings + [layers])
All 21 headings in docs/crunk/config.md are ported (crunk-spec table.rs, validate.rs, located errors,
did-you-mean, JSON Schema in docs/schemas/crunk.json): breakpoints, jsx, lint, mock_set, org,
palette(+roles), platform (+media, network_throttle, viewport), project, scales, screen
(+states, states.media, states.network), session, tailwind, tokens (+prefixes), typography.
Gap found: `[layers]` is implemented (table.rs:504, in docs/schemas/crunk.json, used by
hullbreach) but docs/crunk/config.md has no `[layers]` section -- the generated reference
omits it [verify why the reference generator skipped it]. Known strictness divergences listed
in crunk-spec/src/lib.rs (strict types, lexical path normalization).

### C4. Renderer / screenshot / gallery features
| Feature | Python behavior | Rust |
|---|---|---|
| screens | `[[screen]]` id, entry route, applies_to platform ids/tags, named states | config ported; nothing consumes it |
| states | actions (click, hover, focus, fill, press, wait_for), expect_url, fixture, setup, session, mock, network overrides (abort, status, delay, hold), media (color_scheme, reduced_motion), settle_ms, diff_against | config ported only |
| mock sets / sessions | `[[mock_set]]`, `[[session]]` rosters: id + opaque data, injected as `window.__CRUNK_STATE__ = {screen,state,platform,session,mock}` before app scripts so MSW/auth bootstrap can read it | config ported only |
| platforms | `[[platform]]` renderer `web` (playwright chromium/firefox/webkit; viewport, device_scale, locale, media, cpu_throttle, network_throttle, init_scripts, base_url, settle_ms, tags) or `command` (external tool writing PNG: `--screen --state --platform --out --setup`; used for Kotlin Compose via gradle, RN, simctl) | config ported only |
| deterministic capture | networkidle (5s cap) -> `document.fonts.ready` -> animations/transitions/caret disabled -> clock pinned (playwright >=1.45) -> settle_ms | not ported |
| render | `gallery render` -> PNG per (screen,state,platform) cell + sha hash; platform preflight (`doctor`) | not ported |
| manifest | gallery-manifest v3 JSON (schemas/gallery-manifest.v3.json): entries, VerdictRecord(state_id, platform, reviewer, approved/rejected, platform_hash, expiry), RenderArtifact; staleness: any change in source/fixture bytes resets verdict | not ported |
| triage UI | local HTTP server, screen x platform grid, bulk approve/reject, needs-review filter, diff_against side-by-side/overlay toggle | not ported |
| CI check | `gallery check [--json]` -> gallery-check.v1.json with GALLERY001-005 | not ported |
| route discovery | adapters/react_router discovers routes -> GALLERY005 | not ported |
| framework adapters | Protocol FrameworkAdapter (react_ts, react_router) | gob-symbols languages/frameworks cover TS/CSS/HTML parsing (crunk "does not parse a language") ; adapters themselves not ported |
| Tailwind runtime | node helper runs the project's own tailwindcss to get the true class->CSS; static fallback; doctor probes | not ported (static candidate parser only) |
| testbed | crunk-testbed: web-react (Vite/React/Tailwind v4, 10 screens), static-html (4 pages), rn-expo (3), kotlin-compose (3, headless PNG CLI) | untouched; reusable as corpus for Rust ports |

Key observation: Python gallery verdicts are pixel-hash approvals by a human (Chromatic-style);
there is no pixel-diff threshold and no a11y/layout assertion at render time.

---

## D. Real consumer: project-hullbreach

### D1. platform/ (React 18 + Tailwind 4 + vite)
- `platform/crunk.toml` declares: project (css_root web/src/styles, root_font_size 16);
  palette of 8 (ink, paper, panel, muted, accent, stress-ok/warn/fail) + 5 roles; scales
  spacing [0,4,8,12,16,24,32,48,64], font_sizes 8 steps, radii [0,4,8,16]; typography families
  (Inter, system-ui, sans-serif) and weights; `[layers]` base/dropdown/overlay/toast; org buckets
  (base, components, layouts, utilities), kebab, prefix; `[jsx]` globs web/src/**/*.tsx;
  `[tailwind]` config web/tailwind.config.ts, tokens_file web/tailwind.theme.json,
  namespace_keys=true; `[lint]` SPACE001=warn, tolerances.
- Generated artifacts committed: web/src/styles/tokens.css (37 lines), web/tailwind.theme.json.
  Source: 2 pages (Login, Register), Header, Footer, router, one reset.css; 4 vitest files.
  No [[screen]], [[platform]], gallery manifest, no [breakpoints] (Tailwind default seeding
  applies in Python when `[tailwind].config` set [verify for v4]).
- Contrast of declared roles (computed in this run, WCAG 2.x): ink/paper 15.88, ink/panel 14.21,
  muted/paper 6.32, accent/paper 7.09, stress-fail/paper 5.95; additional: muted/panel 5.66,
  accent/panel 6.34, stress-fail/panel 5.32. All pass AA 4.5; none declared for the
  stress-ok/warn colors on a background.
- Features relied on: `crunk tokens` (generation of both files), TOKENS001 drift, COLOR/SPACE/TYPE
  family on CSS, TW001-005 on className strings (namespaced utilities `gap-space-8`), ORG
  buckets, CONTRAST roles. Doc text in docs/picking-up-work.md says stock Tailwind classes
  fail `crunk check`; platform/frob.toml lists crunk-generated files as "referenced by name".
- Run of Rust crunk 0.532.0 on this crunk.toml (scratch copy, no sources): exit ok, zero findings,
  `rules: []` in the document [verify: the empty rules list with COLOR001 registered looks like
  rules are only listed when a file matched; not investigated].
- What Rust crunk lacks for this consumer to switch: `tokens` verb (blocks generation of both
  generated files), TOKENS001, CONTRAST001, TW001-005, ORG001-005, TYPE/SPACE/RADIUS/SIZE/LAYER/BP.
  It would additionally need: [[screen]]/[[platform]] for Login/Register states (idle, error
  401/429 banner - note Login.tsx has a role="alert" error state, a loading state is absent),
  a11y lints on TSX (form labels, role=alert present), a dark-mode/mode story (palette is
  dark-only: no light mode), and a way to share tokens with the game.

### D2. game/ (Unity 6) UI usage
Checked ~/projects/project-hullbreach/game.
- UXML/USS/TSS files: NONE (find for *.uxml *.uss *.tss found nothing). Packages/manifest.json
  includes com.unity.modules.uielements but no UI Toolkit assets exist.
- uGUI: yes. 5 prefabs in Assets/Prefabs/UI (HudCanvas 3352 lines YAML, StatusPanel 1680,
  BuilderPanel 941, HullWarningBanner 530, ChannelBar 489), TextMeshPro assets, com.unity.ugui 2.0.0.
  The prefabs are GENERATED by an editor script, Assets/Editor/Hullbreach.Editor/HudPrefabBuilder.cs
  (Screen Space Overlay canvas, 1920x1080 reference resolution, match 0.5; panel color
  `new Color(0,0,0,0.55f)`; label `fontSize = 18`, `Color.white`). Design doc: game/docs/design/ui-port.md.
- Engine-free color table: Assets/Scripts/Hullbreach.Hud/HudColor.cs (ThrustRed (0.9,0.2,0.15)
  = #e63326, ReverseGreen = #33d94c, WarningOkGreen = #4cff66 ...). These do NOT match the web
  palette (stress-fail #ff4d4f, stress-ok #3fd17c) though the platform crunk.toml comment says
  "stress-* mirror the in-game hull-stress gradient": drift between two UIs already exists and
  nothing checks it.
- Input: com.unity.inputsystem 1.14.2 installed; no *.inputactions asset found; jira-export.md
  lists open questions "controller support in v1?", "rebindable keys?" (SCRUM-134 S27-2 rebindable
  keys To Do) and a Sprint-2 "colorblind-safe palette toggle (HudColor)" (ui-port.md line ~302,
  SCRUM-156) and "colorblind-safe alternative to green/red?". So GX concerns (rebinding,
  colorblind, controller) are all open and unlinted.
- Testing: PlayMode tests DemoHudTests, DemoScreenshots (opt-in PNG dump to HULLBREACH_SHOTS),
  DemoStructureTests. Screenshots exist as a mechanism but no baseline/approval flow.
- Implication: crunk's Unity story for hullbreach is (a) token export to C# (HudColor) or USS
  rather than hand-copied floats, (b) lint on the generator script's literals, (c) a headless
  Unity render via the existing `command` renderer contract (crunk `[[platform]] renderer="command"`
  was designed for this), (d) decide whether to adopt UI Toolkit (USS = the same CSS-like
  language the token rules already parse) for new screens.

---

## E. Synthesis

### E1. Capability matrix
Legend: Y full, P partial, N none, - n/a. Columns: Fig=Figma, Pen=Penpot, SB=Storybook,
Py=Python crunk, Rs=Rust crunk today, Prop=proposed crunk.

| Capability | Fig | Pen | SB | Py | Rs | Prop |
|---|---|---|---|---|---|---|
| Visual canvas editing (human drag) | Y | Y | N | N | N | N (non-goal; Penpot/Figma remain optional front ends) |
| Text-file source of truth | N | P (zip of JSON) | Y (code) | P (toml tokens) | P | Y |
| Pages/frames/scene tree | Y | Y | N | N | N | Y (scene files) |
| Vector/boolean/mask editing | Y | Y | N | N | N | P (SVG assets only) |
| Auto layout (flex) incl wrap, min/max | Y | Y | - (CSS) | N | N | Y |
| Grid layout / layout grids | Y | Y | - | N | N | Y |
| Absolute children, constraints | Y | Y | - | N | N | Y |
| Components + instances | Y | Y | Y | N (CSS BEM map) | N | Y |
| Variants / component props (bool, enum, text, swap) | Y | P | Y (args) | N | N | Y |
| Slots | P | N | P (children) | N | N | Y |
| Tokens/variables with modes + alias | Y (Ent. API) | Y | P | P (flat, no modes) | P (parse only) | Y (DTCG 2025.10 + resolver) |
| Token scoping | Y | N | N | N | N | Y |
| Styles (text/effect/grid) | Y | Y | - | N | N | Y (typography/shadow composites) |
| Typography incl. OpenType | Y | Y | - | P (family/weight/size) | P | P->Y |
| Effects/gradients | Y | Y | - | N | N | P |
| Images/assets | Y | Y | Y | N | N | P (manifest) |
| Prototype flows/interactions | Y | Y | P (play fn) | P (state actions) | P (cfg) | Y (flow files) |
| Smart animate / motion | Y | P | N | N | N | P (motion tokens + lint) |
| Prototype variables/logic | Y | N | N | N | N | N/P (defer) |
| Dev mode inspect/measure | Y | Y | P | P (explain) | N | Y (explain, measure) |
| Ready-for-dev status | Y | N | N | P (verdicts) | N | Y (status + gate) |
| Code mapping (Code Connect) | Y | N | Y (it is code) | N | N | Y |
| Libraries/publish/version | Y | Y | Y (pkg) | N | N | Y (git + lock) |
| Branch/merge | Y (paid) | P | git | git | git | git |
| Comments/review | Y | Y | P | P (triage) | N | P (review files) |
| Plugin/REST API | Y | Y | Y | N | N | Y (CLI/MCP/patch) |
| Agent write path | Y (MCP use_figma) | Y (MCP) | code | N | N | Y (patch verb) |
| Headless render | N (export via API) | P | Y | Y (playwright) | N | Y |
| State enumeration (screens x states x platforms) | N | N | Y (stories) | Y | cfg only | Y |
| Visual regression | N | N | Y (Chromatic) | P (hash+human) | N | Y (pixel + perceptual + human) |
| Token drift check (spec vs generated) | N | N | N | Y | N | Y |
| Palette/scale conformance lint | P (Design Lint plugin) | N | N | Y | P (COLOR001) | Y |
| Contrast lint | P (plugins) | N | Y (axe addon) | P (roles only) | N | Y (roles + rendered) |
| DOM a11y lint (axe) | N | N | Y | N | N | Y (via rendering) |
| Tailwind-aware lint/export | N | N | P | Y | P | Y |
| Export to CSS/Tailwind/USS/Swift | P (Dev Mode) | Y | N | P (css/json/tw) | N | Y |
| Import from Figma variables / DTCG | - | P | N | N | N | Y |
| Responsive checks | P | P | P (viewport addon) | P (BP rules) | N | Y |
| Localization/RTL checks | P | N | P | N | N | Y |
| Game UI (gamepad nav, safe area, TV) | N | N | N | N | N | Y (GX pack) |
| Unity UXML/USS/uGUI support | N | N | N | N | N | P->Y |
| Waivers/severity/CI exit codes | N | N | P | Y | Y (gob) | Y |

### E2. Proposed agent-first crunk model

Principle: everything an agent edits is text that diffs, merges, validates against a JSON Schema,
and has a stable id; everything visual is derived. Mirror Figma's concepts, not its UI.

Source-of-truth files (all under `design/`, configured by `crunk.toml` which keeps policy):
1. `design/tokens/*.tokens.json` -- DTCG 2025.10 token files (collections = files/groups;
   aliases; composite typography/shadow/border; color objects w/ colorSpace) +
   `design/tokens/theme.resolver.json` (resolver module) for modes (light/dark, density, brand,
   platform). `crunk.toml [palette]/[scales]` becomes either a view of these or a TOML dialect
   that compiles to DTCG (decision D1 below). Scale rules (allowed px steps) remain policy in
   crunk.toml; they apply to tokens, not just to CSS literals.
2. `design/components/<name>.component.toml` -- anatomy (scene subtree), props (bool, enum/variant,
   text, slot, component-swap), variants matrix, states (default, hover, focus-visible, active,
   disabled, loading, error, empty), token bindings, a11y contract (role, accessible-name source,
   keyboard map, min target), responsive rules, `code = {path, export}` (Code Connect equivalent),
   `status`, `doc`.
3. `design/screens/<id>.screen.toml` -- extends today's `[[screen]]` model: id, entry route or
   scene root, states each with scene overrides/props, session/mock ids, actions, applies_to
   platforms, expected a11y landmarks/headings, copy keys, `status = draft|ready|changed` and
   content hash. Existing screen/state/platform/mock/session tables stay compatible.
4. `design/scenes/*.scene` -- the headless-renderable layout description. Choice: a restricted
   HTML+CSS dialect (flex/grid/absolute, `var(--token)` references, `<Component prop=.../>`),
   because agents are fluent in it, it maps 1:1 to the browser, to Tailwind, and to UXML/USS.
   Alternative: KDL/TOML-tree dialect (cleaner schema, less agent prior). Decision D2 below.
5. `design/flows/*.flow.toml` -- user flows and prototype wiring: nodes = screen:state, edges =
   trigger (click, key, gamepad:south, timeout) + action; lintable graph (reachability, dead ends,
   focus path).
6. `design/motion.tokens.json` (duration/easing/transition types are in DTCG) + per-component
   transition tables.
7. `design/content/*.toml` -- copy deck/microcopy keys with length budget, tone rules, locales;
   scenes reference keys, not literals (enables I18N lints).
8. `design/a11y.toml`, `design/targets.toml` -- platform profiles: web (viewports, breakpoints),
   tv/console (safe area %, min text px at 10ft, focus rules), mobile (target size 44/48),
   game HUD profiles.
9. Generated, never edited: tokens.css, tailwind theme json, `tokens.uss`, `HudTokens.cs`,
   Figma-variables JSON, Swift/Kotlin if wanted; `design/.baseline/` image + layout-solve baselines
   (git LFS or CI artifact; today's policy is screenshots are CI-only, keep that default and
   commit the layout-solve JSON baselines, which are small and diffable).

Verbs (agent-facing; every verb has --json, stable exit codes as today):
- Create/edit: `crunk new component|screen|flow|token <name> [--from]`, `crunk edit <file>
  --patch patch.json` (RFC 6902 JSON Patch / TOML-edit ops with schema validation and
  id-addressing; returns the diff and re-lints only the touched nodes), `crunk rename <id>`
  (updates all references), `crunk extract-token <literal>` (promote a literal to a token and
  rewrite uses, the existing `fix` generalized), `crunk apply-theme <mode>`.
- Render: `crunk render [--screen --state --platform|--component --variant] [--engine
  layout|browser]` -> PNG + layout-solve JSON (boxes, text overflow, tab order, computed styles).
- Snapshot/diff: `crunk snapshot [--update]`, `crunk diff [--visual|--layout|--tokens|--a11y]
  <a> <b>` (token diff exists in Python), `crunk gallery triage` (human verdicts, kept).
- Check/fix: `crunk check [--family F] [--static|--render] [--changed]` (batch, SARIF/JSON),
  `crunk fix [--dry-run]` (tiered applicability: safe/needs-review as in the shared fix design),
  `crunk explain`, `crunk measure a b`, `crunk query` (unchanged).
- Interop: `crunk export css|tailwind|uss|csharp|dtcg|figma-variables|storybook`, `crunk
  import dtcg|figma-variables|penpot|css`, `crunk sync figma` (optional, token-only at first),
  `crunk mcp` (read/write tools mirroring the Figma MCP split: get_design_context,
  get_variable_defs, search_design_system, use_patch).
- Process: `crunk status <id> ready` (refuses unless lints green; records content hash),
  `crunk review` (comments/verdicts files).

Tiers so that batch-check works with no browser: T0 static (parse files; no layout), T1
solve (layout engine, no pixels: boxes, overflow, overlap, targets, safe areas), T2 render
(pixels: visual regression, rendered contrast), T3 live DOM (axe, focus, real fonts via
Playwright), T4 human (verdict). Every lint declares its minimum tier.

### E3. Lint catalogue (proposed; E existing in Python, E(Rs) existing in Rust)
Tier: S=static, L=layout-solve (no pixels), R=needs rendering (pixels or live DOM), H=human.
Ids are proposals. "has" = exists in Python crunk.

TOKEN (design tokens)
| Id | Check | Tier |
|---|---|---|
| TOKENS001 (has) | generated outputs drifted from source | S |
| TOKEN002 | DTCG schema invalid / unknown $type / bad alias | S |
| TOKEN003 | alias cycle or unresolved reference | S |
| TOKEN004 | token unused (query unused today) / unreferenced primitive used directly by component (skips semantic layer) | S |
| TOKEN005 | naming convention (kebab, tier prefix primitive/semantic/component) | S |
| TOKEN006 | mode completeness: every token has a value in each declared mode | S |
| TOKEN007 | scope violation (spacing token bound to fill) | S |
| TOKEN008 | duplicate values under different names (near-dupe colors within color_tolerance) | S |
| TOKEN009 | deprecated token used | S |

COLOR / CONTRAST
| COLOR001 (has, Rs) | literal not in palette | S |
| COLOR002 (has) | var() undefined | S |
| CONTRAST001 (has) | declared role pair below floor | S |
| CONTRAST002 | role pairs in EVERY mode and state (hover/disabled/focus) meet floor (APCA optional) | S |
| CONTRAST003 | rendered text-on-background contrast, including over images/gradients/alpha | R |
| COLOR003 | color-only meaning: stress ok/warn/fail distinguishable under deuteranopia/protanopia/tritanopia simulation; require secondary cue (icon/label) | S (tokens delta-E) + R |
| COLOR004 | gamut/space: p3/oklch literals have srgb fallback | S |
| COLOR005 | non-text contrast 3:1 for UI component boundaries and focus rings | S/R |

TYPE (typography)
| TYPE001-003 (has) | size/family/weight off scale | S |
| TYPE004 | line-height below 1.4 body / >1.2 for display ratios per policy | S |
| TYPE005 | min size per platform profile (web 12px, TV 10ft table, mobile 11pt) | S |
| TYPE006 | font file declared, present, licensed, subset covers locales | S |
| TYPE007 | measure (chars per line) 45-90 | R |
| TYPE008 | text overflow/truncation not clipped important content; max-lines declared | L |
| TYPE009 | fallback stack metric-compatible (CLS risk) | S + R |

SPACE / LAYOUT
| SPACE001, SIZE001, RADIUS001, LAYER001 (has) | off scale | S |
| LAYOUT001 | absolute positioning used for in-flow content | S |
| LAYOUT002 | fixed width/height on text containers (clipping risk) | S |
| LAYOUT003 | overlap between siblings not declared as overlay | L |
| LAYOUT004 | overflow: content exceeds container or viewport (horizontal scroll) at any declared viewport | L |
| LAYOUT005 | alignment/grid snap: edges off layout grid / inconsistent paddings in a repeated pattern | L |
| LAYOUT006 | touch/click target below min (44px web/iOS, 48dp Android) and spacing between targets | L |
| LAYOUT007 | safe area: interactive/critical elements inside platform safe area (TV 90%/mobile notch) | L |
| LAYOUT008 | z-order: layer tokens only; modal above all | S |
| LAYOUT009 | container query / density mode consistency | L |

COMP (components and variants)
| COMP001 | variant matrix complete (every combo declared or explicitly excluded) | S |
| COMP002 | props typed; required props have defaults in stories | S |
| COMP003 | raw literals in component bodies (token-only inside components) | S |
| COMP004 | duplicate/near-duplicate components (query dupes today) | S |
| COMP005 | component mapped to code (Code Connect equivalent): path exists, exports prop names | S |
| COMP006 | detached copy: inline subtree structurally equal to a component | S |
| COMP007 | slot allowed-children violated | S |
| COMP008 | unused component | S |
| COMP009 | naming/ID stability (renames without alias) | S |
| ORG001-005, TW001-005 (has) | file/class/Tailwind policy | S |

STATE (coverage)
| STATE001 | every interactive component declares default, hover, focus-visible, active, disabled | S |
| STATE002 | data-bound screens declare loading, empty, error, partial states | S |
| STATE003 | forms: error, success, validation states | S |
| STATE004 | each screen state rendered on each applicable platform (GALLERY001 generalized) | R |
| GALLERY001-005 (has) | approval ledger | R+H |
| STATE005 | state diff sanity: `diff_against` states differ by > threshold (else state not applied) | R |
| STATE006 | game: menu focus default, pause, disconnect, low-hull, death states | S |

A11Y (accessibility)
| A11Y001 | accessible name source declared for every interactive node (label, aria, alt) | S |
| A11Y002 | heading order / landmarks per screen spec | S |
| A11Y003 | keyboard map: every action reachable; tab order = visual order (declared vs solved) | L |
| A11Y004 | focus ring present and 3:1 in every state | S/R |
| A11Y005 | live DOM axe-core run per state (about 100 rules; includes color-contrast, target-size, label, button-name, image-alt) | R |
| A11Y006 | reduced-motion variant exists for each motion token use | S |
| A11Y007 | images alt / decorative flagged | S |
| A11Y008 | forms: labels, autocomplete, error association | S |
| A11Y009 | text resize 200% / zoom 400% reflow check | R |
| A11Y010 | language and direction attributes | S |

RESP (responsive)
| BP001-003 (has) | breakpoint hygiene | S |
| RESP004 | each screen has a scene at every declared breakpoint without overflow (LAYOUT004) | L |
| RESP005 | mobile-first: base styles unprefixed (BP002 generalized) | S |
| RESP006 | image srcset/sizes and aspect ratio reserved | S |
| RESP007 | orientation/foldable/TV viewports | L |

MOTION
| MOTION001 | duration/easing from tokens, within bounds (e.g. 100-500ms UI, <= 1s) | S |
| MOTION002 | reduced-motion alternative | S |
| MOTION003 | smart-animate matching: every animated id exists in both states | S |
| MOTION004 | flashing/strobing (3 flashes/sec, WCAG 2.3.1) in frame sequence | R |
| MOTION005 | animation of layout properties (perf) vs transform/opacity | S |

CONTENT / I18N
| CONTENT001 | literal strings in scenes (must use copy keys) | S |
| CONTENT002 | copy length budget per slot, with pseudo-locale expansion (+40%) still fits | L |
| CONTENT003 | tone/terminology glossary (banned words, consistent terms, button verb-first) | S |
| CONTENT004 | placeholder text (lorem ipsum, TODO) | S |
| I18N001 | RTL: mirrored layout declared, no physical left/right in properties (use start/end) | S + L |
| I18N002 | locale coverage: every key has every locale | S |
| I18N003 | fonts cover scripts | S |

VIS (visual regression)
| VIS001 | pixel diff vs baseline within threshold (BackstopJS/Playwright style) | R |
| VIS002 | layout-solve diff (box moved > 1px) -- cheaper and less flaky than pixels | L |
| VIS003 | perceptual diff (SSIM/delta-E) | R |
| VIS004 | design-vs-build: rendered app vs scene render (Figma "design QA") | R |
| VIS005 | human verdict required for changed cells (existing gallery) | H |

THEME / EXPORT / PROC
| THEME001 | every screen renders in every mode; no hardcoded mode-specific literals | S + R |
| EXPORT001 | generated files stale / hand-edited (TOKENS001 generalized) | S |
| EXPORT002 | cross-target parity: same token resolves to same value in CSS, USS, C# outputs (fixes hullbreach drift) | S |
| PROC001 | `status = ready` but content hash changed or lints red | S |
| PROC002 | screen lacks owner/ticket link (opaque `ticket=` rule as in products.md) | S |
| PROC003 | open comments/critique items at ready | S |
| UX001 | heuristic checklist items (Nielsen) with agent-produced evidence; mechanical subset: visibility of status (loading state declared), error prevention (confirm for destructive), consistency (component reuse ratio) | S + H |

GX (game UX pack; section F2)
| GX001 | every focusable has a defined next in each cardinal direction (no focus dead-ends/traps) | S (graph) |
| GX002 | every action bound for keyboard+mouse also bound for gamepad; no hold-only or mash-only required (GAG) | S |
| GX003 | remappable bindings declared; no hard-coded keys in UI hints (glyph keys resolved by device) | S |
| GX004 | TV/console safe area (title-safe 90%, action-safe 93%-ish [verify]) respected | L |
| GX005 | minimum HUD text size at reference viewing distance and resolution (e.g. >= 28px at 1080p for 10ft guidance [verify]) | L |
| GX006 | HUD never relies on color alone (stress gradient must pair with icon/number) | S/R |
| GX007 | HUD scale option and opacity option declared (GAG: allow interfaces to be resized) | S |
| GX008 | subtitle/caption size, background, speaker label options declared | S |
| GX009 | UI contrast against worst-case game background (render sample frames) | R |
| GX010 | no flashing in HUD feedback (MOTION004) | R |
| GX011 | FTUE: each mechanic has a first-use tutorial/hint entry; skippable; replayable | S (coverage graph) + H |
| GX012 | feedback coverage: every player action maps to visual + audio (+ haptic) feedback entry | S |
| GX013 | platform cert UI rules (button glyphs correct per platform, confirm/cancel convention, no unsupported terms, loading indicator for > Ns) -- public rules summarized only [verify, TRC/XR specifics are NDA] | S/H |
| GX014 | Unity: uGUI prefab literals not from tokens (generator script literals; HudColor drift) | S |

### E4. Hard problems and options

1. Layout engine (needed for T1 tier)
   - taffy (Rust, pure, Block+Flexbox+Grid per its README, used by Zed/Lapce/Bevy): fast, deterministic,
     embeddable, no I/O. Gaps: no inline/text flow, no floats, no table, no CSS cascade/units
     (calc, vw, container queries partly); needs a text measure callback; so you must feed it a
     style tree already resolved from tokens. Risk: divergence from browser results at edges
     (min-content of text, margin collapse irrelevant).
   - Headless browser (Playwright already used by Python gallery): ground truth for CSS/fonts/DOM,
     axe works only here; cost: Node dependency, slower, nondeterministic fonts/antialiasing across OS,
     heavy in CI; keep as the `web` renderer (already specified) and as truth tier T2/T3.
   - Embedded engine (Servo/Stylo or Blitz = Dioxus's taffy+stylo+vello renderer [verify]): near-browser fidelity
     in-process; large dependency, immature, build time.
   - Own mini-layout: reject (taffy exists).
   Recommendation: dual. T1 = taffy over the scene dialect restricted to features taffy supports
   (the dialect IS the restriction), T2/T3 = Playwright. A "parity test" renders the same scene both
   ways in CI and flags solver/browser disagreement > N px (this also measures how trustworthy T1 is).

2. Text shaping and measurement: taffy needs text size. Options: cosmic-text (shaping, fallback,
   layout; used by Bevy/COSMIC), parley (Linebender), rustybuzz + ttf-parser (raw), swash.
   Determinism needs bundled font files (no system fonts) pinned by hash; kerning/OpenType features
   differ per shaper vs browser (HarfBuzz is used by Chromium, rustybuzz is a HarfBuzz port, so
   widths should agree closely [verify]). Bidi/complex scripts: cosmic-text/parley handle; keep
   CJK/Arabic out of v1 scope or declare "approx".

3. Font licensing: fonts in design tokens are named, but renders need files. Inter is SIL OFL
   (bundle-able); SF Pro / Segoe / Apple system fonts are not redistributable; commercial faces
   need license records. Options: (a) `fonts.toml` manifest with license id + file hash, lint
   TYPE006 forbids committing files without an OFL/Apache/commercial-licensed marker; (b) render
   with metric-compatible open substitutes (Inter for SF, Liberation for Arial) and mark T1/T2
   results "approx"; (c) use project's real files from the repo (Unity project already has
   LiberationSans in TextMesh Pro; license file present). Always record the substitution.

4. Rasterization for T2 without a browser: resvg/tiny-skia (CPU, deterministic) via scene->SVG,
   or vello (GPU). Pixel parity with browsers is not achievable, so VIS001 baselines are per
   engine; use browser baselines for web release truth and solver baselines for fast PR checks.

5. Source of truth: DTCG JSON vs crunk.toml. DTCG pro: interop with Style Dictionary, Tokens Studio,
   Figma variable importers, Penpot; con: JSON ergonomics (no comments), resolver spec still draft,
   Style Dictionary v5 lacks full 2025.10 [verify], color objects verbose. Option: keep a TOML
   authoring dialect (comments, terse `ink = "#e6e8ef"`) that compiles to DTCG and exports DTCG;
   `crunk tokens` already follows this shape. Decision D1: TOML dialect authoring + DTCG
   canonical export/import, so no existing consumer (hullbreach) rewrites its palette.

6. Scene language: restricted HTML/CSS vs custom tree. HTML/CSS: highest agent prior, trivial
   browser parity, `gob-symbols` html/css adapters exist, TSX already parsed. Custom: simpler to
   validate, patch by id, round-trip to UXML. Decision D2 (proposed): scene = HTML-subset +
   `data-id` stable ids + component tags; UXML emitter is a target, not the source.

7. Game UI differences: no DOM, no CSS; uGUI prefabs are YAML serialized scenes with GUIDs,
   machine-written (here by an editor script), not human-authorable. Options: (a) treat prefabs
   as build output generated from crunk scenes via an editor script (hullbreach already does this
   with HudPrefabBuilder) and lint the generator's inputs; (b) adopt UI Toolkit (UXML+USS+TSS)
   for new UI, then crunk parses USS with the same declarations/token rules (USS has `--var`,
   `var()`, `@import`, `:root`, Unity docs UIE-USS-CustomProperties), no YAML parse needed; (c) lint
   prefab YAML directly (colors, font sizes, anchors) -- brittle across Unity versions. Recommend
   (a)+(b), (c) as read-only audit.

8. Pixel flakiness and determinism: keep the Python gallery's capture discipline (fonts.ready,
   animations off, fixed clock, networkidle, settle) as the T2/T3 contract; commit layout-solve
   baselines (stable) and keep PNGs in CI.

9. Scope creep (Figma parity): non-goals for v1: vector editing, boolean ops, plugin ecosystem,
   realtime multiplayer, prototype variable logic. A visual editor can always be Penpot/Figma via
   import/export.

10. Agent ergonomics: stable ids, patch-based edits returning targeted lint results (sub-second via
    cache), `--explain RULE` with a worked fix, JSON output only, deterministic ordering (already
    the crunk/gob convention).

---

## F. The design cycle end to end, and game UX

Legend for checks: M = mechanical/static, R = needs rendering, H = needs humans. "crunk text
artifact" = file crunk could hold and lint. Industry-practice content is from memory; tag
[verify] where I give a specific number.

### F1. UX/UI cycle
| Phase | Artifacts | Crunk-holdable text artifacts | Mechanical (M) | Needs render (R) | Needs human (H) | Agent authoring + verify |
|---|---|---|---|---|---|---|
| Discovery / research | research repo, interview notes, synthesis, personas, JTBD, journey maps, service blueprints, competitive audits | `research/*.md` with frontmatter (source, date, participants, tags); `personas/*.toml`; `journeys/*.toml` (stages x actions x pain/emotion); JTBD statements | frontmatter schema; every persona/journey references >= 1 evidence note; every requirement/screen cites persona/job id; stale (> N months); orphan insights | - | validity of synthesis, bias, sampling | Agent drafts from transcripts; verify = traceability graph complete (insight -> need -> requirement -> screen); humans confirm |
| Information architecture | sitemap, nav model, card-sort results, content model/taxonomy | `ia/sitemap.toml` (tree of routes + labels + nav placement), `content-model.toml` (types, fields, constraints), card-sort csv | route uniqueness; depth <= N; every route in sitemap has a screen and vice versa (GALLERY005 analog); nav reachability from home; label uniqueness; taxonomy single parent | rendered nav matches sitemap | card sort interpretation, findability testing (tree test) | Agent proposes sitemap; check = graph rules + routes in code vs sitemap |
| Ideation / wireframes / flows | low-fi frames, user flows, flow diagrams | `flows/*.flow.toml`, Mermaid, scenes using only primitives with `fidelity="wire"` | flow graph: reachable, no dead ends, every decision has all branches, error path present; wire scenes use no brand tokens | layout solve for overflow even at wireframe | concept quality | Agent writes flow + wire scene; verify with graph lints + T1 render for overlap; Figma `generate_diagram` (Mermaid->FigJam) is the same idea |
| UI design | design system, tokens, components, states, responsive, theming/dark mode, localization/RTL, content design, microcopy guidelines | tokens, components, screens, `content/*.toml`, `voice.toml` (tone, glossary, banned terms, length budgets) | all of E3 TOKEN/COLOR/TYPE/SPACE/COMP/STATE/I18N/CONTENT (S) | contrast over images, overflow with real fonts, RTL mirroring, pseudo-locale expansion, dark mode | brand taste, aesthetics, copy quality | Agent edits via patch verbs; verify with check --render; human approves gallery verdicts |
| Prototyping | clickable prototype, interaction spec, motion spec | flow files with triggers/actions, `motion.tokens.json`, component transition tables | trigger/action vocab valid; targets exist; timing in token bounds; reduced-motion twin; smart-animate id matching | animate in browser; frame-sequence flash check; jank | feel, delight | Agent wires flows; verify by executing the flow headlessly (Playwright steps = existing `actions`) and asserting expected state ids |
| Usability testing and design QA | usability sessions, heuristic evaluation (Nielsen's 10 [verify count/names: visibility of status, match real world, user control, consistency, error prevention, recognition, flexibility, minimalist, error recovery, help]), cognitive walkthrough, a11y audit, design-vs-build visual QA | `qa/heuristics/<screen>.toml` (heuristic id, finding, severity, evidence, status); `qa/walkthrough/<task>.toml` (task steps: does user know what to do / see control / link action to goal / see progress); test plans/results | evidence refs exist; every severity>=major has owner/ticket; every task has steps and success criterion; heuristic coverage per screen; a11y static subset (A11Y lints); known-state coverage (STATE) | axe-core live, VIS004 design-vs-build, task replay | actual usability observation, SUS, interviews, judgement of walkthrough answers | Agent runs the mechanical heuristics (status/loading present, destructive confirm, error recovery paths, consistency via component reuse) and drafts walkthrough; humans run sessions; results stored as files so regressions are diffable |
| Handoff / design ops | specs, redlines, tokens export, versioning, critique/review, ready-for-dev | `status`, `changelog`, `review/*.toml` (comments with anchors), `handoff.toml` (acceptance criteria, linked tickets), code mapping | ready gate: all lints green, no open blocking comments, tokens exported & fresh (EXPORT001), component-code mapping exists (COMP005), acceptance criteria present, changed-since-ready detection (hash) | redlines auto-generated from layout-solve (`measure`) | critique decisions | `crunk status ready` is the gate; frob already provides the ticket/evidence mechanism and crunk stays ticket-agnostic (opaque `ticket=` rule) |
| Post-launch | analytics, A/B experiments, UX metrics (HEART: happiness, engagement, adoption, retention, task success [verify]; SUS; task success/time; Core Web Vitals) | `metrics/*.toml` (metric definitions: event, formula, target), `experiments/*.toml` (hypothesis, variants -> component variants, guardrails, primary metric, MDE, status) | every flow step has an analytics event name defined; events unique and documented; experiment variants exist as declared variants; guardrails declared; a stale experiment (> N days) flagged; metric targets present for each shipped screen | CWV lab run (Lighthouse) per screen | interpreting results, SUS/NPS surveys, qualitative synthesis | Agent adds event contracts and variant scaffolding; verify = static coverage; numbers flow back as data files from analytics, human decides |

### F2. GX (game UX)
| Topic | What it is | Text-checkable artifact | Mechanical | Render | Human |
|---|---|---|---|---|---|
| HUD and diegetic UI | HUD overlays vs UI inside game world (ship console) ; screen-space vs world-space canvases | `hud/<profile>.toml`: elements, anchors, scale, priority, visibility rules | anchors within safe area; no overlap among always-visible elements (L); token-only colors | contrast on sample frames; occlusion of play area (% screen covered) | feel, immersion |
| Menus and front-end flows | title, settings, pause, lobby, builder panel | flows as in F1 with `gamepad` triggers | reachability, back-stack, pause available everywhere, confirm for destructive | focus ring visible | feel |
| Input / gamepad navigation and focus | focus graph, default selection, nav wrap, mouse/pad parity | `input.toml` actions x devices; focus graph from scenes | GX001-003; each action has glyph per device family; no keyboard-only controls | focus indicator contrast | pad feel |
| Remapping | rebindable controls, conflicts | bindings schema | conflict detection, reserved keys, required unbound-safe defaults | - | - |
| Readability / distance / safe areas | 10-foot UI, TV overscan, small screens/handheld | `targets.toml` profiles | GX004/005 via solver | text legibility renders at downscaled sizes (simulate distance by scale) | real display test |
| Onboarding / FTUE | tutorials, hints, first-time user experience | `ftue.toml` steps per mechanic, triggers, skip/replay | every mechanic has FTUE or declared "none"; no FTUE blocks input without skip | step visibility | pacing, comprehension |
| Feedback / juice | hit flashes, screen shake, audio cues, haptics | `feedback.toml` event -> {vfx, sfx, haptic, ui} | coverage; intensity within bounds; shake/flash has accessibility toggle | flashing detection | feel |
| Game accessibility | Game Accessibility Guidelines (gameaccessibilityguidelines.com, basic/intermediate/advanced across motor, cognitive, vision, hearing, speech, general; read), Xbox Accessibility Guidelines (XAG, learn.microsoft.com; page 404'd on fetch -> [verify]), AbleGamers APX (accessible player experiences patterns) [verify], CVAA (US law: communications and accessibility for in-game chat/UI, voice/text chat accessibility) [verify] | `gx-a11y.toml` checklist keyed to GAG item ids with evidence | GAG-derived coverage checks: remap exists; hold-alternatives; UI scalable; subtitles on and sized; colorblind modes; difficulty/speed options; no timing-only | render for contrast, subtitle size | accessibility playtesting with players with disabilities |
| Platform cert UI | console TRC/XR (Sony TRC, Xbox XR, Nintendo guidelines): mostly NDA, public themes: standard button glyphs & confirm/cancel, user-sign-in UI, error messages, safe areas, loading indicators, suspend/resume, account names, parental/age rating screens | per-platform `cert.toml` checklist | checklist coverage only | - | cert authority |
| Unity: UI Toolkit | UXML tree + USS (CSS-like) + TSS themes; USS has `:root`, `--var`, `var()`, `@import` (docs.unity3d.com UIE-USS, -CustomProperties, -tss) | .uxml/.uss/.tss files | crunk's declaration + token rules apply to USS with a USS dialect (properties differ: `-unity-font`, `-unity-text-align`, `flex-grow` etc.) | needs Unity (batch mode) | - |
| Unity: uGUI | Canvas/RectTransform prefabs (YAML, GUID refs), TextMeshPro, Canvas Scaler (reference res 1920x1080 here) | .prefab / .unity YAML; here generated by HudPrefabBuilder.cs | read-only audit: Color literals, font sizes, anchors; better: lint generator script literals (C# adapter exists in gob) | Unity render via `command` renderer | - |
| Unity: TSS | Theme Style Sheet = USS container that imports sheets per platform/language | .tss | per-theme token completeness | - | - |
| Shared design system web + Unity | one token source | `design/tokens` -> `crunk export tailwind` + `crunk export uss` + `crunk export csharp` | EXPORT002 parity; GX014 | - | - |

Hullbreach-specific application: bring HudColor and the web palette under one token file
(stress-ok/warn/fail, thrust red, panel alpha 0.55); export `HudTokens.cs` (engine-free floats, preserving
the D3 "no engine reference" rule) and `tokens.uss`; define a `hud` platform profile (1920x1080
reference, match 0.5) and a `tv` profile; model the colorblind toggle as a MODE in the resolver
(`stress.default`, `stress.cb-safe`) so every lint runs in both modes.

---

## G. Gaps (ranked) -- capability gaps of Rust crunk against the proposed crunk

1. No renderer or layout solve at all (no taffy tier, no Playwright wrapper, no scene format).
2. 29 of 30 Python rules unported (only COLOR001 live); hullbreach cannot switch.
3. No `tokens` verb/exporters/TOKENS001 -> generated tokens.css/tailwind theme cannot be produced.
4. No `fix` (and no tiered applicability) -> agent loop is check-only.
5. Tokens model is flat (no modes, aliasing, composites, scopes); no DTCG import/export.
6. No component model (props, variants, slots, states) -> no STATE/COMP lints.
7. Gallery pipeline (enumerate/render/triage/check, manifest v3) unported; config tables only.
8. No a11y lint beyond contrast roles (no axe integration, no keyboard/focus/target-size).
9. No responsive/layout lints beyond BP (no overflow/overlap/safe-area/target size).
10. No flow/prototype/motion model; no reduced-motion/flash lints.
11. No content/i18n/RTL model; no copy deck.
12. No structured edit verb (patch), no `crunk new`, `rename`, `extract-token`; no MCP surface.
13. No Unity/game support (USS/UXML parsing, C#/USS exports, GX lints, gamepad/focus model); hullbreach palette already drifts.
14. No process gates: ready-for-dev status, review files, research/IA/QA traceability artifacts.
15. Visual regression is human-hash only: no pixel/perceptual/layout diff thresholds, no design-vs-build comparison; config.md also omits `[layers]`.

## 8. Decisions proposed (owner to confirm; not made)
D1 TOML authoring dialect + DTCG canonical interchange. D2 scene = restricted HTML/CSS with
stable ids, taffy for T1 and Playwright for T2/T3. D3 tier model T0-T4 with per-lint declared
tier. D4 game: generate prefabs from crunk, adopt USS for new UI. D5 rendered PNGs stay CI
artifacts; layout-solve JSON baselines committed. D6 start order: tokens verb + CONTRAST/TOKENS
ports (unblocks hullbreach), then component/state model, then scene+solve, then render/gallery,
then GX pack.

## 9. Phase-2 coverage verdict
- A: 78/78 rows written for 16/16 brief groups; 0 pending; UI-only features with no
  developer-docs page are tagged [verify] (slots, grid layout, new effects, accessibility in Figma).
- B: 30/30 tools covered; 9 of them backed by fetched primary pages (DTCG format/resolver, Style
  Dictionary, Penpot data model, Storybook docs source, axe rule list, pa11y, Unity USS/TSS, taffy,
  GAG), the rest from memory.
- C: 25/25 verb forms, 30/30 rules, 21/21 config headings (+ layers), gallery features
  enumerated and each marked; Rust coverage = 1/30 rules, 0/25 verbs fully (2 partial).
- D: web/src fully listed (12 files); game UI inventory complete for UXML/USS/uGUI (UXML/USS: none found).
- Not done: no live Unity run, no Python crunk run, no prototype of taffy parity.
- Blocked: help.figma.com pages and the XAG page (learn.microsoft.com) returned 404/shell; marked [verify].
Sources fetched 2026-10-08: designtokens.org (home, format, resolver, color), styledictionary.com/info/dtcg,
developers.figma.com (rest-api, variables, variables-endpoints, rate-limits, plugins Variable,
figma-mcp-server + write-to-canvas + tools-and-prompts, code-connect quickstart),
help.penpot.app data-model, penpot.app/dev-tools, storybook docs source (raw GitHub),
github.com/dequelabs/axe-core rule-descriptions, pa11y.org, playwright.dev test-snapshots,
github.com/garris/BackstopJS, docs.unity3d.com 6000.0 UIE-USS*/UIE-tss, gameaccessibilityguidelines.com,
github.com/DioxusLabs/taffy, github.com/BuilderIO/mitosis, tldraw.dev/docs/shapes.


---

## Sourcing pass


Subject: sources for scratchpad/staged/crunk-design-2026-10-08.md (the research note, 748 lines, 0 URLs, 37 verify tags)
and the design draft scratchpad/staged/crunk.md (read, not edited). No repository was changed.

## 0. Honest status (read first)

- Fetched and read this session: 391 distinct sources (table (c)); 109 are help.figma.com articles, 24 developers.figma.com pages,
  27 figma.com blog posts. Of these, 24 are GitHub API metadata pulls (licence, last push, latest release) and 5 are crates.io
  or Crossref JSON; all others are documents.
- Tooling caveat: WebSearch, WebFetch and the playwright MCP were NOT available in this session (ToolSearch returned no match).
  Everything was fetched over HTTP from Bash with a small stdlib script (browser User-Agent, HTML stripped to text). Discovery
  used site search/sitemaps instead of a search engine: the Zendesk search API of help.figma.com, figma.com/sitemaps, nngroup.com/sitemap.xml,
  api.github.com, crates.io, the npm registry, Crossref, Federal Register API. No JavaScript was executed.
- BLOCKED (not read, not dropped; claims depending on them are marked UNVERIFIED): m3.material.io (JS shell; Material 3 not cited),
  stitch.withgoogle.com (JS shell), fcc.gov (403; FCC CVAA game-waiver end date unverified), designopsassembly.com and designops.org
  (TLS handshake error from this host), eur-lex.europa.eu (403), congress.gov (403), taylorfrancis.com (403), Figma State of the Designer 2026 body
  (gated form; only the landing blurb was read, so no numbers cited), GDC Vault talk content (login wall; only titles read),
  Nintendo and Sony/Microsoft console certification documents (NDA; no public copy exists), Apple HIG HTML (JS shell; the HIG JSON
  feed was read instead), Polaris docs (redirect shell; GitHub README read), the Figma MCP "Rate limits and access" page (redirect;
  figures taken from the Schema 2025 help article instead), figma.com sections/groups/frames help article (329-char video stub).
- INVALID source: gameuxmasterguide.com now serves an unrelated gambling spam page; excluded.
- Discarded fetch: a guessed Routledge URL returned a different book; removed.
- Pending: 0 of the enumerated rows. Denominators: A = 78 rows (59 confirmed unchanged, 17 corrected or extended, 2 unverified: A3 groups, A23
  tidy-up dropped); B = 30 comparables (the note's table had 23; 7 added); F = 8 UX phases + 12 GX topics, plus 6 added process frames; state of
  practice = 7 new items. Row coverage is complete; evidence strength varies (see the strength words in each row).
- Dates: help.figma.com dates are the article's last-updated stamp, NOT the feature ship date. Ship dates come from the Figma blog and release
  notes only where shown.

## How to read the citations

[HC:ID] = help.figma.com/hc/en-us/articles/ID ; [DEV:path] = developers.figma.com/docs/path ; [FB:slug] = figma.com/blog/slug ; [FR:slug] = figma.com/reports/slug ;
[NNG:slug] = nngroup.com/articles/slug ; [GH:org/repo] = github.com/org/repo (+ API metadata) ; other keys are host:path. The full URL for every key is in table (c).

## (a1) Section A, Figma, row-by-row (78 rows)

Legend: OK = claim confirmed by the cited page; FIX = claim changed; NEW = detail added. Dates are the
date of the cited page or release note, not a guess. "[KEY]" resolves in the sources table (c).
HC = help.figma.com article id, DEV = developers.figma.com/docs path, FB = figma.com/blog slug.

### A1. Document model
A1 | OK. File holds pages; REST returns the node tree [DEV:rest-api/file-endpoints]. Layer types overview [HC:26620239826199].
A2 | OK. Frame is the container that owns size, clip, auto layout, constraints, components and prototyping; frame presets exist [HC:26620239826199].
A3 | UNVERIFIED (semantics only). Figma's sections/groups/frames comparison page is a 329-char video stub; group behaviour was not confirmed from text. The 'avoid groups' advice is crunk's own design choice, not a Figma statement. Frames give access to components, auto layout and prototyping [HC:26620239826199].
A4 | OK with NEW. Sections organise the canvas and are the unit that carries a Ready for dev status [HC:9771500257687] [HC:23918228264855].
A5 | OK. Vector networks are a documented Figma concept [HC:360040450213]; Figma Draw added illustration tools (Config 2025, 2025-05-07) [FB:config-2025-press-release].
A6 | OK. Boolean operations documented [HC:360039957534].
A7 | OK. Masks documented [HC:360040450253].
A8 | OK, NEW. Corner radius per shape and per vector point; "smoothing" is its own control [HC:360050986854]. Shape tools [HC:360040450133].
A9 | OK. Text properties include truncation, vertical trim, paragraph spacing and indent, case, decoration, lists [HC:360039956634]; text-to-vector [HC:360047239073].
A10 | FIX wording. Images and videos are a FILL type, not a layer type; they can sit on frames, shapes and text [HC:26620239826199]; image adjustments [HC:360041098433]. Patterns can also be a fill or stroke (2025) [HC:31616030150167].
A11 | OK. Layer naming is free text [HC:360039958934]; "rename layers with AI" exists [HC:24004711129879]. Lint on naming remains a crunk-only value-add (Figma agent can bulk-rename, see S4).
A12 | OK. Lock/unlock [HC:360041596573]; blend modes [HC:360040667874].
A13 | OK. Rotation/position/dimension controls [HC:360039956914]; proportional scale tool vs aspect-ratio lock [HC:360040451453].

### A2. Layout
A14 | OK. Auto layout has THREE flows now: horizontal, vertical, grid; hug/fill/fixed sizing; min/max width/height [HC:360040451373].
A15 | FIX. Wrap exists for horizontal AND vertical flows; vertical wrap shipped 2026-09-25 (release note) and is documented as flex-direction column + flex-wrap wrap; "not masonry" [HC:31289464393751] [figma:release-notes].
A16 | OK. Minimum/maximum width/height are auto-layout resizing options [HC:360040451373]; number variables can bind to min/max dimensions [HC:14506821864087].
A17 | FIX (name). The feature is now called "Ignore auto layout" (formerly "absolute position"); behaves like CSS absolute positioning inside the parent [HC:360040451373]; constraints [HC:360039957734].
A18 | OK. Constraints for non-auto-layout frames [HC:360039957734]; combine with layout guides [HC:360039957934].
A19 | OK. Layout guides (columns, rows, grids) [HC:360040450513]. Note the docs say the "uniform grid" layout guide is a DIFFERENT feature from grid auto layout [HC:31289469907863].
A20 | FIX (remove (verify tag)). Grid auto layout is shipped: announced at Config 2025 (2025-05-07) as "Grid ... generate CSS code in Dev Mode" [FB:config-2025-press-release]; help article states available on all plans, cells/tracks/spans, bento/dashboard use [HC:31289469907863]; combining flows [HC:31441443713047].
A21 | OK. Responsive resize = constraints + auto layout [HC:360039957734]; text styles can vary per breakpoint (2025) [HC:31242838116119].
A22 | OK. Aspect-ratio lock exists ("lock and unlock aspect ratio") [HC:360040451453].
A23 | UNVERIFIED, DROP. "Tidy up" did not surface in help search; it is an editor helper with no model impact. Removed from the denominator.

### A3. Components
A24 | OK. Main components/instances [HC:39719619313047].
A25 | OK. Overrides via component properties [HC:5579474826519].
A26 | OK. Variants and interactive variants [HC:360061175334].
A27-A30 | OK. Component property types are: boolean, instance swap (with preferred instances), text, variant, and SLOT [HC:5579474826519] [HC:39636407507735].
A31 | FIX (remove (verify tag)). Slots are shipped: beta announced at Schema 2025 (2025-10-28) rolling out to all plans [HC:35794667554839]; help article (created 2026-02-06, updated 2026-10-05) says all plans, Full seat to edit; you can set preferred instances and a MIN and MAX layer count; cannot bind to the top-level layer; can span variants of one set [HC:38231200344599]; difference vs instance swap vs variants [HC:38741465279895]; migrating libraries: Figma lists the old workarounds as placeholder frames labelled Content/Swap/Insert here and nested instances exposed through instance-swap properties [HC:38607529833751] (a ready-made lint pattern: placeholder-slot detection on import).
A32 | OK. Descriptions can be added to styles, components and variables [HC:7938814091287]; Dev Mode links designs to tickets, documentation and code components [HC:15023124644247].
A33 | OK. Swap and detach documented [HC:360039150413] [HC:360038665754]; components fundamentals [HC:39635555294743]; edit instances through component properties [HC:8883757553943].
A34 | OK. Interactive components [HC:360061175334] [HC:20953528101783] [HC:39747190144023].
A35 | OK. Libraries: publish, update prompts, swap libraries [HC:360041051154] [HC:360025508373] [HC:4404856784663].

### A4. Variables and styles
A36 | FIX. The editor UI now has SIX variable types: Color, Number, String, Boolean, TIMING (ms) and EASING (curve or spring) [HC:14506821864087]. The REST and Plugin APIs still document only BOOLEAN, FLOAT, STRING, COLOR as resolvedType [DEV:rest-api/variables-types] [DEV:plugins/api/Variable]. Consequence: timing/easing variables are not round-trippable through the Variables REST API today.
A37 | OK. Collections; Variables REST types: VariableCollection with modes, defaultModeId, hiddenFromPublishing [DEV:rest-api/variables-types].
A38 | FIX (add limits). Modes per collection depend on plan: Professional up to 10, Organization up to 20 (limit increase announced Schema 2025), Enterprise unlimited via extended collections [HC:35794667554839] [HC:360040328273] [HC:15343816063383]. Variable modes also drive prototypes [HC:15253268379799].
A39 | OK. Aliasing documented; color variables can alias while keeping separate opacity [HC:14506821864087].
A40 | FIX. Extended collections are Enterprise-only, announced Schema 2025, and in the extension you CANNOT add variables or modes or change description/scope - open the parent [HC:36346281624471]. The APIs expose isExtension, parentVariableCollectionId, rootVariableCollectionId, inheritedVariableIds, localVariableIds, variableOverrides [DEV:plugins/api/VariableCollection] [DEV:rest-api/variables-types]; Plugin API has VariableCollection.extend(name) for local collections [DEV:plugins/api/VariableCollection]. (Help text says no new variables; REST exposes localVariableIds: treat extension-local variables as unverified.)
A41 | FIX (important). Scopes only limit which variables are SHOWN in the UI pickers; they do not stop binding through the Plugin API [DEV:rest-api/variables-types]. Scoping is documented per type [HC:15343816063383]. Lint consequence: a scope-violation rule is meaningful precisely because Figma does not enforce it.
A42 | OK. codeSyntax stores platform names and shows in Dev Mode snippets [DEV:rest-api/variables-types] [DEV:plugins/api/Variable]; Dev Mode shows variables [HC:27882809912471].
A43 | OK. hiddenFromPublishing is per variable AND per collection; both must be true to publish [DEV:rest-api/variables-types].
A44 | OK. boundVariables on nodes; number variables bind to many properties (corner radius, min/max, padding, gap, stroke weight, font props, layout guides, text content, effect values, Motion presets) [HC:14506821864087] [HC:15343107263511].
A45 | OK. Variables in prototypes (set variable, conditionals, expressions) on paid plans [HC:14506587589399] [HC:15253194385943].
A46 | OK. Paint styles [HC:360039238753]; variables vs styles comparison [HC:15871097384471].
A47 | OK. Text styles; per-breakpoint text styles (2025) [HC:360039957034] [HC:31242838116119].
A48 | OK. Effect styles [HC:360039238753].
A49 | OK. Grid styles [HC:360039238753].
A50 | OK with NEW numbers. Variables REST: GET local/published and POST; Enterprise plan, Full seat, edit access for POST; scopes file_variables:read/write [DEV:rest-api/variables]. Rate tier: GET variables = Tier 2 (Dev/Full 25/50/100 per min on Pro/Org/Enterprise), POST variables = Tier 3 (50/100/150 per min); effective 2025-11-17 [DEV:rest-api/rate-limits]. Endpoint reference [DEV:rest-api/variables-endpoints]. Import/export JSON per mode exists in the UI (used in the extended-collection migration) [HC:36346281624471]; Create/manage variables [HC:15145852043927].

### A5. Typography, effects, images
A51 | OK, remove (verify tag). OpenType features [HC:4913951097367]; variable fonts and axes [HC:5579502031511]; vertical trim, truncation, paragraph controls [HC:360039956634].
A52 | OK. Missing-font alert is documented [HC:360039956994]; browse/apply fonts [HC:360041308034].
A53 | FIX (remove (verify tag)). Effects now: drop shadow (max 8), inner shadow (max 8), layer blur (1), background blur (1), noise (max 2), texture (1), GLASS (1; not supported in SVG export; invisible on 100% opaque fills) [HC:360041488473]. Config 2026 added agent-built SHADER fills and effects with parameters [FB:config-2026-recap] [HC:41175721167767]. Portability lint: noise/texture/glass/shader have no USS/CSS equivalent.
A54 | OK. Gradients [HC:34208860210199]; strokes (align, dash, caps, joins) [HC:360049283914]; patterns [HC:31616030150167].
A55 | OK. Image properties and filters [HC:360041098433].
A56 | OK. Export settings and formats [HC:13402894554519]; MCP download_assets caps ~4096px longest edge, up to 20 nodes per call [DEV:figma-mcp-server/tools-and-prompts].

### A6. Prototyping
A57 | OK. Flows [HC:360039823894]; guide [HC:360040314193].
A58 | FIX/NEW. Triggers: click/tap, drag, hover, press, KEYBOARD/GAMEPAD (officially Xbox One, PS4, Switch Pro controllers), mouse enter/leave (semantics changed 2023-11-16), mouse down/up, after delay, video hits [HC:360040035834].
A59 | OK. Actions incl. navigate, overlays, scroll, set variable, conditional [HC:360040035874] [HC:15253220891799].
A60 | OK. Prototype animations [HC:360040522373].
A61 | FIX. Smart animate matches by layer NAME AND POSITION IN THE HIERARCHY, not name alone [HC:360039818874].
A62 | OK. Expressions and conditionals shipped (paid plans) [HC:15253194385943] [HC:15253220891799] [HC:14506587589399].
A63 | OK. Scroll/overflow/fixed [HC:360039818734].
A64 | OK. Mobile device preview [HC:360040321093]; accessible prototypes with screen reader and keyboard (Skip to content) [HC:7810391964695].
A65 | FIX/NEW. Figma Motion: timeline, keyframes, presets, launched 2026-06-24; Dev Mode shows the full timeline and copies CSS, JSON or React; MCP-compatible; export MP4/WebM/animated SVG/GIF [FB:config-2026-recap] [FB:introducing-figma-motion] [HC:41274629073303]. MCP get_motion_context [DEV:figma-mcp-server/tools-and-prompts]. Timing/easing variable types back it [HC:14506821864087].

### A7. Dev Mode
A66 | OK. Inspect, code snippets in several languages [HC:22012921621015] [HC:15023202277399].
A67 | OK. Measurements [HC:360039956974] [HC:20774752502935].
A68 | OK. Annotations (Full seat to add; Full or Dev to view) shipped 2024-01-25 [HC:20774752502935] [FB:dev-mode-ga].
A69 | FIX. Statuses: "Ready for dev" on all paid plans; "Completed" and the Ready-for-dev VIEW on Organization/Enterprise only; a CHANGED state is set automatically and is NOT set when a library instance updates, or the value of an attached variable or style changes [HC:26781702258583] [HC:23918228264855]. Compare changes [HC:15023193382935]. Dev Mode left free beta 2024-01-31 [FB:dev-mode-ga]. Design implication: Figma's "changed" ignores token value changes; crunk's content-hash (HUMAN001 inputs) deliberately includes them - document as intentional.
A70 | FIX. Code Connect has two modes: Code Connect UI (GA at Schema 2025; Org/Enterprise; GitHub optional; multiple code connections per component; AI-suggested mappings; MCP usage instructions) and Code Connect CLI (framework-agnostic template files; connections made by CLI can only be edited via CLI). Org/Enterprise, Full or Dev seat [HC:23920389749655] [HC:35794667554839] [DEV:code-connect] [DEV:code-connect/quickstart-guide] [GH:figma/code-connect]. CLI latest v2.0.1 (2026-09-10).
A71 | OK. Dev resources link a layer to external URLs; REST endpoints exist [HC:15023231995927] [DEV:rest-api/dev-resources-endpoints].
A72 | FIX (much larger). MCP: first announced 2025-06-04 as "Dev Mode MCP server"; GA at Schema 2025; remote server (all seats/plans) and desktop server (Dev or Full seat, paid) [FB:introducing-figma-mcp-server] [HC:35794667554839] [HC:35280968300439] [DEV:figma-mcp-server/remote-server-installation]. Tool inventory now: read = download_assets, get_code_connect_map, get_code_connect_suggestions, get_context_for_code_connect, get_design_context, get_figjam, get_generative_plugin, get_libraries, get_metadata (sparse XML outline; no nodeId returns the page list), get_motion_context, get_screenshot, get_shader, get_variable_defs, list_file_shaders, list_generative_plugins, list_shaders, search_design_system, whoami; write = add_code_connect_map, create_generative_plugin, create_new_file, create_shader, generate_diagram (Mermaid -> FigJam), generate_figma_design, generate_image, send_code_connect_mappings, update_generative_plugin, update_shader, upload_assets, use_figma [DEV:figma-mcp-server/tools-and-prompts]. Default output of get_design_context is React + Tailwind, steerable by prompt. Limits: Starter plan or View/Collab seats get up to 6 tool calls per month; Dev/Full seats follow Tier 1 REST per-minute limits [HC:35794667554839]. Skills for the MCP server [HC:39287396773399]. Code to canvas (capture live UI into editable frames) [DEV:figma-mcp-server/code-to-canvas]. Generative plugins and shaders [DEV:figma-mcp-server/generative-plugins-and-shaders].

### A8. Libraries, versioning, collaboration
A73 | OK. Libraries, publish, swap libraries, analytics [HC:360041051154] [HC:360025508373] [HC:4404856784663] [HC:360039238353] [DEV:rest-api/library-analytics-endpoints].
A74 | OK with NEW. Starter and Drafts see only 30 days of history; paid plans full history [HC:360038006754]; REST version-history endpoint [DEV:rest-api/version-history-endpoints].
A75 | OK. Branching and merging, Organization/Enterprise; branch review requests [HC:360063144053] [HC:5691414603543].
A76 | OK. Comments on any plan; REST comments endpoints; Webhooks V2 [HC:360039825314] [DEV:rest-api/comments-endpoints] [DEV:rest-api/webhooks].
A77 | OK with NEW. Plugin API runs in the editor [DEV:plugins]; agent-built "generative plugins" need no plugin-API knowledge (Config 2026) [FB:config-2026-recap] [HC:43028920030743]. MCP use_figma executes Plugin API JavaScript [DEV:figma-mcp-server/write-to-canvas].
A78 | FIX (add numbers). REST rate limits changed 2025-11-17: tiered per endpoint, per seat, per plan; Tier 1 (GET file, file nodes, images): View/Collab up to 20/month, Dev/Full 10/15/20 per minute on Pro/Org/Enterprise; leaky bucket, 429 with Retry-After and X-Figma-Plan-Tier headers [DEV:rest-api/rate-limits]. File endpoints [DEV:rest-api/file-endpoints]; scopes [DEV:rest-api/scopes].

### A-summary paragraph of the note (agent read/write, accessibility)
A-sum1 | OK/FIX. use_figma needs a Full seat; Dev seats are read-only; edit permission required on the file; limitations listed by Figma: 20kb output per call, no image/asset support "yet", no custom fonts "yet", components must be published before Code Connect completes [DEV:figma-mcp-server/write-to-canvas]. BUT the tool list also has upload_assets (images into a file) [DEV:figma-mcp-server/tools-and-prompts]; the two pages disagree - treat asset import as in-flux.
A-sum2 | FIX (WRONG in the note). "Figma itself has contrast in the color picker, no built-in lint (verify tag)": contrast IS built in (WCAG ratios, AA/AAA, color-blindness simulation on the web checker) [HC:360041003774] [figma:color-contrast-checker]; prototypes have screen-reader mode [HC:7810391964695]; and a built-in design lint now exists: CHECK DESIGNS (Org/Enterprise, Figma Design; announced as early access at Schema 2025, documented 2026-04). It finds hard-coded colors, text styles, corner radius, spacing and padding, and components/variables/styles from wrong libraries; suggests variables; does NOT use LLMs; ranks by similarity, naming and usage frequency; limits: one page at a time, 25K layers, cannot swap color styles [HC:39592284074263] [HC:35794667554839]. The Figma agent can also audit a screen against the library and bulk-replace tokens [FB:figma-agent-and-design-systems]. The "wedge" statement must be narrowed (see section b, W2).

## (a2) Section B, comparables (the note's table has 23 rows, not the 30 it claims; 7 added here to reach 30)

B-Penpot | FIX/NEW. Licence MPL-2.0 confirmed; latest release 2.18.3 (2026-10-06); ~60.8k stars [GH:penpot/penpot]. Design tokens are native and "adhere to the DTCG format module"; sets, themes, import/export; composite tokens (typography, shadow); row-gap tokens for wrap flex boards [help.penpot:user-guide/design-systems/design-tokens]. Data model page documents files > pages > shapes [help.penpot:technical-guide/developer/data-model]. MCP server EXISTS and is documented: remote and local variants, needs the Penpot tab to stay active and an MCP plugin, one personal MCP key per user, always operates on the focused page; use cases include creating tokens, auditing naming/redundancy, design-to-code [help.penpot:mcp]. The note's cited penpot.app/dev-tools URL 404s now.
B-DTCG-format | FIX (WRONG status). Format Module 2025.10 is a "Final Community Group Report", 28 October 2025, published as a Candidate Recommendation by DTCG process, "considered stable"; still not a W3C Standard [DTCG:tr/2025.10/format]. `$extends` on groups is in the spec (group inheritance, may not reference a token) [DTCG:tr/2025.10/format]. Home: "First stable version 2025.10 now available" [DTCG:home]. Color module is a separate 2025.10 document [DTCG:tr/2025.10/color]. Repo licence field NOASSERTION (spec licensed under W3C CG FSA) [GH:design-tokens/community-group].
B-DTCG-resolver | FIX (WRONG status). Resolver Module is ALSO 2025.10 Final Community Group Report (28 Oct 2025), with sets, modifiers and `resolutionOrder`; not "draft, not yet stable" [DTCG:tr/2025.10/resolver]. The /tr/drafts/resolver page is now the same text [DTCG:tr/drafts/resolver].
B-StyleDictionary | FIX. Current line is v5 (v5.6.0, 2026-10-03; Apache-2.0) [GH:style-dictionary/style-dictionary]. DTCG 2025.10 support is PARTIAL: v5.4.0 (2026-03-22) added the 2025.10 dimension-object value; the docs page still says full 2025.10 support is work in progress in v5 [styledictionary:info/dtcg]. Recent releases are mostly security fixes (prototype pollution in convertTokenData) - pin >= 5.5.5.
B-TokensStudio | FIX. Plugin MIT, latest 2.13.0 (2026-10-06) [GH:tokens-studio/figma-plugin]. DEFAULT token format is still "legacy"; W3C DTCG is an opt-in setting, `$value`-prefixed, with convertToDTCG in Style Dictionary v4 utils; Git sync providers GitHub/GitLab/Bitbucket/Azure DevOps; multi-file sync and themes are Pro [docs.tokens:manage-settings/token-format] [docs.tokens:home].
B-Storybook | FIX/NEW. v10.6.1 (2026-09-29), MIT [GH:storybookjs/storybook]. Testing: interaction (play), a11y, visual, snapshot, coverage [storybook.js:docs/writing-tests]. A11y addon is built on axe-core which "catches up to 57% of WCAG issues"; results = Violations/Passes/Incomplete; DEFAULT config disables the `region` rule; params a11y.context/config/options/test; integrates with the Vitest addon [storybook.js:docs/writing-tests/accessibility-testing] [storybook.js:docs/writing-tests/integrations/vitest-addon]. Visual tests = Chromatic [storybook.js:docs/writing-tests/visual-testing]. CSF [storybook.js:docs/api/csf]. NEW: Storybook ships an MCP server (dev, testing, docs toolsets; docs toolset reads a components manifest) and AGENTS.md guidance [storybook.js:docs/ai/mcp/overview] [storybook.js:docs/ai] [storybook.js:docs/ai/best-practices].
B-tldraw | FIX (licence). Not open source in the OSS sense: tldraw licence permits dev use; PRODUCTION use needs a licence key [raw.githubusercontent:tldraw/tldraw/main/LICENSE.md] [tldraw:community/license]; v5.5.2 [GH:tldraw/tldraw]; shape records [tldraw:docs/shapes]. Do not plan to embed it as crunk's future canvas without that cost.
B-Excalidraw | OK. MIT, v0.18.1 [GH:excalidraw/excalidraw]; documented JSON schema for scenes [docs.excalidraw:docs/codebase/json-schema].
B-Framer | OK/thin. Developers page: plugins, Server API, code components, Property Controls, overrides, Fetch [framer:developers]. No public lint (absence claim is about the docs fetched, not proof).
B-Plasmic | FIX/NEW. MIT [GH:plasmicapp/plasmic]; docs list a "Plasmic MCP" [docs.plasmic:learn]. Codegen CLI claim stays unverified (docs landing only).
B-Builder | OK/thin. Developer docs and Visual Editor [builder:c/docs/developers]; Visual Copilot 1.0 (Figma-to-code AI) [builder:blog/visual-copilot].
B-Mitosis | OK. Compiles to React/Vue/Angular/Svelte/Solid/Qwik; MIT; 0.14.1 (2026-09-29) [GH:BuilderIO/mitosis].
B-CodeConnect | FIX. See A70: two modes (UI, CLI) [HC:23920389749655] [DEV:code-connect]; CLI v2.0.1 [GH:figma/code-connect].
B-DesignLint | FIX (stale). destefanis/design-lint last pushed 2024-01-12, MIT; flags layers missing styles [GH:destefanis/design-lint]. Largely superseded by Figma's own Check designs (A-sum2) [HC:39592284074263].
B-Stark | OK/thin. Stark markets Figma, Sketch, browser and GitHub integrations and team reporting of design files, code repositories and live sites; CI claim not verifiable from the homepage [getstark:home].
B-axe-core | OK. v4.14.0 (2026-10-05), MPL-2.0 [GH:dequelabs/axe-core]; rule table with WCAG 2.2 tags, `target-size`, `color-contrast-enhanced` [github:dequelabs/axe-core/blob/develop/doc/rule-descriptions.md].
B-pa11y | OK. pa11y 10.0.0 (2026-08-28), LGPL-3.0 [GH:pa11y/pa11y]; site [pa11y:home].
B-Lighthouse | OK. v13.5.0 (2026-09-18); the accessibility score is a weighted average using axe user-impact weights [GH:GoogleChrome/lighthouse] [developer.chrome:docs/lighthouse/accessibility/scoring].
B-BackstopJS | FIX. Scenarios, viewports, Playwright or Puppeteer scripts [GH:garris/BackstopJS]; the GitHub "latest release" is v3.8.8 from 2019 and npm latest is 6.3.25 published 2024-09-07 (npm registry API, fetched) - low release cadence; prefer Playwright for new work.
B-Playwright | OK (remove (verify)). `expect(page).toHaveScreenshot()` with per-browser/platform baselines [playwright:docs/test-snapshots]; `toMatchAriaSnapshot` is real and documented as "Snapshot testing" of the accessibility tree [playwright:docs/aria-snapshots]; v1.64.0 [GH:microsoft/playwright].
B-Chromatic | OK. Review model: all assigned reviewers must approve; states Pending/Passed; default reviewers [chromatic:docs/review] [chromatic:docs]; CLI v18.11.0 [GH:chromaui/chromatic-cli]. This matches crunk's accept/reject gallery idea and its multi-approver rule maps onto the review reviewers list.
B-taffy | FIX. v0.14.0 (2026-08-24), MIT; CSS Block, Flexbox, Grid; text is integrated via measure functions with per-node context (compute_layout_with_measure) [GH:DioxusLabs/taffy] [docs:taffy/latest/taffy] [docs:taffy/latest/taffy/tree/struct.TaffyTree.html] [crates:api/v1/crates/taffy].
B-UnityUIToolkit | FIX/NEW. UXML, USS and TSS are all documented; TSS "files are regular USS files" with @import, treated as a distinct asset type, used for per-platform/device/language themes [UNITY:6000.7/UIE-tss] [UNITY:6000.0/UIE-tss] [UNITY:6000.0/UIE-UXML] [UNITY:6000.0/UIE-USS]. USS variables: `--name`, `var(--name, default)`, `:root`; NOT supported: var() inside other functions (e.g. rgb(var(--r),0,0)) and any math on variables [UNITY:6000.7/UIE-USS-CustomProperties]. Docs exist through Unity 6000.7 (labelled Beta) [UNITY:6000.7/UIE-USS-SupportedProperties] [UNITY:6000.7/UIE-USS-WritingStyleSheets].
B-cosmic-text (added) | cosmic-text 0.19.0 (2026-04-22), Apache-2.0: shaping via HarfRust (not rustybuzz), rendering via swash, custom bidi layout and font fallback [GH:pop-os/cosmic-text] [crates:api/v1/crates/cosmic-text].
B-parley (added) | parley 0.11.1 (2026-08-16), Apache-2.0, rich text layout; used by Blitz [GH:linebender/parley] [crates:api/v1/crates/parley].
B-Blitz (added) | Blitz is BETA: HTML/CSS engine built on Stylo (CSS), Taffy (layout), Parley (text), Vello renderer; "blitz" crate renders an HTML string; no JS; accessibility via AccessKit [GH:DioxusLabs/blitz]. It is the closest existing Rust implementation of the "restricted HTML/CSS scene" idea and a candidate T1.5 engine for parity tests.
B-resvg (added) | resvg 0.48.1 (2026-08-02), Apache-2.0, SVG renderer usable as deterministic raster for icon assets [GH:linebender/resvg] [crates:api/v1/crates/resvg].
B-TailwindTheme (added) | Tailwind v4 stores design tokens as theme variables via `@theme`, which also emits regular CSS variables [tailwindcss:docs/theme] [tailwindcss:docs/adding-custom-styles]. This is the exporter target the crunk design calls "the Tailwind theme".
B-shadcn (added) | shadcn/ui ships a component registry and an MCP server so agents install components from registries [ui.shadcn:docs/mcp] [ui.shadcn:docs/registry]. Evidence that "design system as MCP" is mainstream.
B-Figma-AI-lint (not in note) | Figma Check designs: see A-sum2 [HC:39592284074263].

## (a3) Section F, design cycle and game UX, with real sources

### F1. UX/UI cycle (8 phases of the note)
F1-research | Sourced. GOV.UK discovery: no fixed length, typically 4 to 8 weeks; purpose-led [GOVUK:sm/agile-delivery/how-the-discovery-phase-works]; user research is a Service Manual discipline with its own guidance [GOVUK:sm/user-research]; Service Standard point set [GOVUK:sm/service-standard]. Personas/journeys: NN/g journey mapping (map = actor, scenario, phases, actions, mindsets, opportunities) [NNG:journey-mapping-101]; service blueprints [NNG:service-blueprints-definition]. Jobs to be done has two non-equivalent schools: Christensen (progress a customer seeks) [hbr:2016/09/know-your-customers-jobs-to-be-done] [christenseninstitute:jobs-to-be-done] and Ulwick's outcome-driven JTBD with job statements [strategyn:jobs-to-be-done]. Lint design: JTBD statement fields should not be forced into one format.
F1-ia | Sourced. Card sorting: open/closed/hybrid; recommends 30 to 50 cards; qualitative >= 15 participants, quantitative 30 to 50 [NNG:card-sorting-definition]. Tree testing validates findability of an existing or proposed hierarchy and computes per-task success [NNG:tree-testing]. Both are human-tier (T4) activities; crunk only checks that results are filed.
F1-wireframes | Sourced. NN/g now describes "promptframes" (wireframes for the AI era) [NNG:promptframes]. The Double Diamond is explicitly non-linear and iterative; "making and testing very early stage ideas can be part of discovery" [designcouncil.org:our-resources/framework-for-innovation].
F1-ui-design | Sourced. Atomic Design (atoms, molecules, organisms, templates, pages) [atomicdesign.bradfrost:chapter-2]; Design Systems by Kholmatova (book page only, no body text read) [smashingmagazine:design-systems-book]; Inclusive Components patterns (menus, tooltips/toggletips, theme switcher) [inclusive-components:home] [inclusive-components:menus-menu-buttons] [inclusive-components:tooltips-toggletips] [inclusive-components:a-theme-switcher]. Content design: GOV.UK content design and writing for user interfaces [GOVUK:guidance/content-design/what-is-content-design] [GOVUK:sm/design/writing-for-user-interfaces]. Design-system maturity framework (6 dimensions) [NNG:design-system-maturity]; design systems vs style guides [NNG:design-systems-vs-style-guides].
F1-prototyping | Sourced. Figma prototype semantics (A57-A65). GOV.UK alpha: build prototypes to test hypotheses, typically 6 to 8 weeks, book the alpha assessment within a fortnight of starting [GOVUK:sm/agile-delivery/how-the-alpha-phase-works].
F1-usability-QA | FIX/Sourced. Nielsen's 10 heuristics (1994; last reviewed 2024-01-30; developed 1990 with Molich): Visibility of system status; Match between system and the real world; User control and freedom; Consistency and standards; Error prevention; Recognition rather than recall; Flexibility and efficiency of use; Aesthetic and minimalist design; Help users recognize, diagnose and recover from errors; Help and documentation [NNG:ten-usability-heuristics]. How to run a heuristic evaluation [NNG:how-to-conduct-a-heuristic-evaluation]. Cognitive walkthrough has FOUR analysis questions and each step passes or fails (any "No" fails the step) [NNG:cognitive-walkthroughs]. Test 5 users for qualitative usability (2 to 8 depending on project) [NNG:how-many-test-users]. Success rate as the simplest metric [NNG:success-rate-the-simplest-usability-metric]. SUS: 10-item questionnaire, 5-point responses, created by John Brooke in 1986, chapter text "SUS - a quick and dirty usability scale" [hell.meiert:core/pdf/sus.pdf] [measuringu:sus] [usability:how-to-and-tools/methods/system-usability-scale.html]. Design critiques: NN/g guidance on culture and structure [NNG:design-critiques].
F1-handoff | Sourced. Figma Dev Mode: ready-for-dev statuses, Changed state, compare changes, annotations (see A68, A69) [HC:26781702258583] [HC:23918228264855] [HC:15023124644247] [HC:15023193382935]; Figma's own ROI case study for Dev Mode (Forrester TEI, gated landing page only) [FR:forrester-tei-dev-mode]. Governance: NN/g "Your design system needs an enforcer" (2026-02-06) - an owner who ensures usage, rolls changes back into the system, mediates conflicts, runs recurring reviews, needs executive and engineering support [NNG:design-system-enforcer]. Contribution lifecycles: Carbon Product Development Lifecycle = discovery, delivery, launch and scale, with a definition of done and a component checklist (updated 2026-10-01) [carbondesignsystem:contributing/product-development-lifecycle] [carbondesignsystem:contributing/component-checklist] [carbondesignsystem:contributing/get-started]; GOV.UK Design System contribution criteria and propose-a-component flow [GOVUKDS:community/contribution-criteria] [GOVUKDS:community/propose-a-component-or-pattern] [GOVUKDS:community]; Atlassian contribution overview [atlassian:contribution]. Shopify Polaris React is ARCHIVED; Polaris Web Components released 2025-10-01 [raw.githubusercontent:Shopify/polaris/main/README.md] [GH:Shopify/polaris] [shopify:docs/api/polaris] - do not use Polaris React as a process model. DesignOps: NN/g study guide, five team structures [NNG:design-ops-study-guide] [NNG:designops-team-structures]; UX maturity has 6 stages: Absent, Limited, Emergent, Structured, Integrated, User-Driven [NNG:ux-maturity-model]. DesignOps Assembly and designops.org could not be fetched (TLS error from this host): BLOCKED.
F1-post-launch | FIX (HEART verified). Rodden, Hutchinson and Fu, "Measuring the User Experience on a Large Scale: User-Centered Metrics for Web Applications", CHI 2010: HEART = Happiness, Engagement, Adoption, Retention, Task success, plus a Goals-Signals-Metrics process for mapping product goals to metrics [static.googleusercontent:media/research.google.com/en//pubs/archive/36299.pdf] [research:pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications]. The paper says not every category fits every product. Lint implication: `metrics/*.toml` should carry goal, signal, metric and a HEART category, with categories optional.

### F1b. Process frames the note lacked
F1b-govuk | GOV.UK phases are discovery, alpha, beta (private then public), live; each ends in a service assessment against the Service Standard [GOVUK:sm/agile-delivery] [GOVUK:sm/agile-delivery/how-the-beta-phase-works] [GOVUK:sm/agile-delivery/how-the-live-phase-works] [GOVUK:sm/service-assessments] [GOVUK:sm/service-standard] [GOVUK:sm/design].
F1b-dd | Double Diamond: Discover, Define, Develop, Deliver; CC BY 4.0; origin 2003/2004 (Design Council history); the Framework for Innovation wraps it with four principles (put people first; communicate visually and inclusively; collaborate and co-create; iterate, iterate, iterate), a methods bank (explore, shape, build) and culture. The "2019" date the brief mentions is not on the fetched pages; treat as unverified [designcouncil.org:our-resources/the-double-diamond] [designcouncil.org:our-resources/framework-for-innovation].
F1b-wcag | WCAG 2.2 is a W3C Recommendation (current text dated 12 December 2024); it removes 4.1.1 Parsing; adds 2.5.8 Target Size (Minimum) AA = 24 by 24 CSS px, 2.4.11 Focus Not Obscured, 2.5.7 Dragging Movements, 3.3.8 Accessible Authentication, 3.2.6 Consistent Help [W3C:TR/WCAG22] [W3C:WAI/standards-guidelines/wcag/new-in-22] [W3C:WAI/standards-guidelines/wcag] [W3C:WAI/WCAG22/Understanding/target-size-minimum.html] [W3C:WAI/WCAG22/Understanding/focus-appearance.html] [W3C:WAI/WCAG22/Understanding/contrast-minimum.html] [W3C:WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html].
F1b-wcag3 | WCAG 3.0 is a W3C WORKING DRAFT dated 10 September 2026; its text-contrast requirement says the contrast measure is "to be determined" and "the contrast algorithm used in WCAG 3 is yet to be determined" [W3C:TR/wcag-3.0]. APCA (Myndex, Lc values) is an independent project proposed for WCAG 3 but not adopted [git.apcacontrast:documentation/WhyAPCA] [git.apcacontrast:documentation/APCA_in_a_Nutshell.html] [W3C:WAI/GL/task-forces/silver/wiki/Visual_Contrast_of_Text_Subgroup]. Apple's HIG mentions APCA as an alternative measure next to WCAG ratios [HIG:accessibility].
F1b-targets | Touch target numbers differ by platform: WCAG 2.2 AA 24x24 CSS px [W3C:WAI/WCAG22/Understanding/target-size-minimum.html]; Apple 44x44 pt [HIG:accessibility]; Android 48x48 dp with 8 dp spacing [support.google:accessibility/android/answer/7101858] [developer.android:develop/ui/compose/accessibility/api-defaults] [developer.android:guide/topics/ui/accessibility/apps]. Material Design 3 (m3.material.io) is a JavaScript shell and could not be read here; only its web components repo was read [GH:material-components/material-web] [raw.githubusercontent:material-components/material-web/main/docs/theming/color.md].
F1b-systems | Design-system doc/process sources actually read: GOV.UK Design System [GOVUKDS:home] [GOVUKDS:accessibility], Carbon [carbondesignsystem:elements/color/usage], Atlassian [atlassian:foundations/accessibility] [atlassian:home] [atlassian:get-started], USWDS [designsystem.digital:about] [designsystem.digital:home], Adobe Spectrum [spectrum.adobe:home], Primer [primer:home], Goldman Sachs Design [design.gs:home], Apple HIG [HIG:color] [HIG:layout] [HIG:typography] [HIG:inclusion].

### F2. GX (game UX), 12 topics
F2-hud | Sourced. Apple HIG for games: support controller AND default interactions, place virtual controls away from system UI [HIG:designing-for-games] [HIG:game-controls]; Game UI Database as a reference corpus of real HUD/menu screens [gameuidatabase:home]. Hodent: "The Gamer's Brain" (CRC Press, 2017; Crossref lists the book chapters) and GDC 2015 talk "The Gamer's Brain: How Neuroscience and UX can impact Design"; UX heuristics grounded in brain limits (attention, memory) [celiahodent:the-gamers-brain] [celiahodent:home] [api.crossref:works?query.bibliographic=The+Gamers+Brain+Hodent&rows=2&select=title,author,publisher,issued,DOI,ISBN].
F2-menus | Sourced. XAG 112 UI navigation, 113 UI focus handling (focus indicator always visible, must not move to hidden/offscreen elements, dialogs must pull focus to the first control), 114 UI context [XAG:xbox-accessibility-guidelines/112] [XAG:xbox-accessibility-guidelines/113] [XAG:xbox-accessibility-guidelines/114].
F2-input | Sourced. XAG 107 Input [XAG:xbox-accessibility-guidelines/107]; Unity Input System 1.18.0 (current docs): interactive rebinding, saving/loading rebinds, control schemes; UI Toolkit consumes the project-wide UI actions directly since Unity 2023.2 (no UI Input Module component) [UNITY:pkg/inputsystem@1.18/manual/index] [UNITY:pkg/inputsystem@1.18/manual/ActionBindings] [UNITY:pkg/inputsystem@1.18/manual/UISupport] [UNITY:pkg/inputsystem@1.14/manual/HowDoI]. Steam: on-screen glyphs must match the active input device; text entry must use the on-screen keyboard API or a built-in entry [partner.steamgames:doc/steamdeck/compat]. Figma prototypes support Keyboard/Gamepad triggers (A58).
F2-remap | Sourced. GAG motor basic: allow controls to be remapped; adjust sensitivity; haptics toggle; resizable and rearrangeable interface (intermediate) [gameaccessibilityguidelines:full-list]. APX patterns "Flexible Controllers", "Same Controls But Different", "Improved Precision" [accessible:accessible-player-experiences]. Unity rebinding API above.
F2-readability | FIX with numbers. XAG 101 text display minimums by BODY HEIGHT (descender+x-height+ascender pixels, measured on the rendered glyphs, not CSS font-size): console 26 px at 1080p and 52 px at 4K; PC/VR 18 px at 1080p and 36 px at 4K; mobile/streaming 18 px at 100 DPI, 36 at 200, 72 at 400, scaling linearly; players must be able to scale to 200 percent; icon/glyph text meets the same minimum [XAG:xbox-accessibility-guidelines/101]. XAG 102 contrast: text >= 4.5:1, large text and inactive-element text >= 3:1, high-contrast mode >= 7:1 [XAG:xbox-accessibility-guidelines/102]. Steam Deck: smallest on-screen font must not be below 9 px height at 1280x800 [partner.steamgames:doc/steamdeck/compat]. Hullbreach reference 1920x1080 maps onto the console row.
F2-ftue | Sourced (weak). Hodent's Fortnite UX write-up: tutorials only for mechanics playtests showed players did not discover [celiahodent:the-gamers-brain]. APX "Training Ground", "Helping Hand", "Total Recall" [accessible:accessible-player-experiences]. No quantitative FTUE standard found.
F2-feedback | FIX. XAG 117 visual distractions and motion settings; XAG 118 photosensitivity: a flash is a 10 percent luminance change with the darker value below 0.8; failure when more than about 3 per second, covering about 20 percent or more of the screen, or lower-intensity flashing sustained [XAG:xbox-accessibility-guidelines/117] [XAG:xbox-accessibility-guidelines/118]; WCAG 2.3.1 Three Flashes [W3C:WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html]. XAG states ~1 in 4,000 people can have seizures from such images.
F2-gamea11y | FIX. GAG: Basic / Intermediate / Advanced levels across motor, cognitive, vision, hearing, speech, general [gameaccessibilityguidelines:full-list]. The note says the XAG page 404'd: the working URL is /gaming/accessibility/guidelines; XAG V3.2 (published 2023-06-08; page updated 2026-08-14) has 23 guidelines numbered 101 to 123, each with Goal, Overview, Scoping questions, Key areas, Implementation guidelines, Potential player impact; stated NOT to be a compliance checklist [XAG:guidelines] [XAG:home]. APX = 21 patterns in two groups: Access patterns (11) and Challenge patterns (10) [accessible:accessible-player-experiences] [accessible:home]. CVAA: the rule text is 47 CFR Part 14 (Access to Advanced Communications Services and Equipment by People with Disabilities); "electronic messaging service" = real-time text messages, which is the likely hook for in-game text chat (my inference; not confirmed by FCC game guidance) [ecfr:current/title-47/chapter-I/subchapter-B/part-14] [govinfo:content/pkg/CFR-2023-title47-vol1/xml/CFR-2023-title47-vol1-part14.xml] [law.cornell:cfr/text/47/part-14]. The FCC's 2011 order records requests for class waivers for gaming equipment, services and software and found the record insufficient at that time; the later waiver end date is NOT verified (fcc.gov returned 403) [federalregister:documents/2011/12/30/2011-31162/implementing-the-provisions-of-the-communications-act-of-1934-as-enacted-by-the-twenty-first-century]. ESA accessibility policy page fetched [theesa:policy-advocacy/accessibility]. Sony accessibility feature list (system-level) [playstation:en-us/accessibility].
F2-cert | Sourced (public only). Console TRC/XR/Nintendo requirements are NDA; no public copies were found. Public equivalents read: Steam Deck/Steam Machine Verified criteria (controller glyph match, text input, default config 30 fps at 800p, text legibility) [partner.steamgames:doc/steamdeck/compat]; Apple HIG [HIG:going-full-screen]; XAG as Microsoft's public baseline.
F2-unity-uitk | FIX. See B-UnityUIToolkit; also runtime UI getting-started and selectors [UNITY:6000.0/UIE-get-started-with-runtime-ui] [UNITY:6000.0/UIE-USS-Selectors] [UNITY:6000.0/UIE-USS-CustomProperties].
F2-unity-ugui | UNVERIFIED. No uGUI page was fetched; the claim stays from memory.
F2-unity-tss | OK. TSS is a USS file used as an asset type [UNITY:6000.7/UIE-tss].
F2-shared | Sourced as design only; Tailwind @theme and USS variables both express tokens as CSS-like variables, but USS forbids var() inside functions and math on variables [tailwindcss:docs/theme] [UNITY:6000.7/UIE-USS-CustomProperties].
F2-gameuxmasterguide | BLOCKED/INVALID. The brief lists "Game UX Master Guide". gameuxmasterguide.com now serves an unrelated gambling spam page; it cannot be cited. Nothing replaced it except the sources above.

## (a4) Current state of practice, 2025-2026 (new; the note had none)

Credibility legend: V = vendor survey or vendor blog (interested party); I = independent practitioner body; P = primary product documentation.

S4-figma-agent | P/V. The Figma agent works on the canvas: attach designs/files/skills/connected apps as context; run multiple prompts in parallel; Full seat + edit access to make edits, other seats chat only; available on all plans [HC:37998629035799]. Launched to everyone around 2026-06-23 (Config 2026 recap: "launched to everyone yesterday"); Oct 2026 posts call it generally available [FB:config-2026-recap] [FB:figma-agent] [FB:3-ways-product-designers-use-the-figma-agent]. Skills = reusable instructions you author in Figma, from team or community; connectors (Notion, Slack, Granola, Hex, GitHub, Atlassian...) ; chats visible to teammates by default [HC:40283639496599] [FB:agent-custom-tools-context-skills] [HC:39287396773399]. Design-system use: audit a screen for hard-coded values and duplicate components, bulk replace components/tokens, standardise names, draft component docs/API specs (Uber's /create-api and /create-color skills), and "add guidelines to a published library" so rules travel with the library [FB:figma-agent-and-design-systems]. Workflow lab: moving between design and code with agents [FB:workflow-lab-moving-between-design-and-code-with-agents].
S4-make | P/V. Figma Make (prompt to working prototype/app) launched 2025-05-07 [FB:introducing-figma-make] [FB:config-2025-press-release]; npm packages and Make kits import a library's components, styles and variables into Make (Schema 2025) [HC:35794667554839] [FB:introducing-make-kits-and-make-attachments]; Make on local code with PR creation in limited beta (2026-05-28) [FB:figma-make-now-on-your-local-code]; Make to canvas [FB:bringing-figma-make-to-the-canvas]; explore/guidelines pages [HC:31304412302231]. Config 2026 added CODE LAYERS (waitlist, rollout from July 2026), Motion, shaders, generative plugins, Weave tools [FB:config-2026-recap] [FB:the-future-of-design-is-code-and-canvas].
S4-others | P. v0 (Vercel) positions itself as an agent that makes full-stack apps from prompts or Figma imports, with design systems and MCP integrations [v0:docs]; Lovable prompt-to-app builder [docs.lovable:introduction/welcome]; Google Stitch (Google Labs, 2025-05-20, Gemini 2.5 Pro; prompt/image to UI and frontend code; paste to Figma) [developers.googleblog:en/stitch-a-new-way-to-design-uis]; Builder.io Visual Copilot 1.0 [builder:blog/visual-copilot]; UXPin Merge (design with real React components) [uxpin:merge]. Galileo AI as Stitch's origin: NOT verified from any fetched source. stitch.withgoogle.com is a JS shell (not readable).
S4-mcp-everywhere | P. MCP is the common integration layer: Figma [DEV:figma-mcp-server], Penpot [help.penpot:mcp], Storybook [storybook.js:docs/ai/mcp/overview], shadcn [ui.shadcn:docs/mcp], Plasmic [docs.plasmic:learn], Carbon (MCP section in its nav, page not read) [carbondesignsystem:contributing/get-started], GitHub Copilot [docs.github:en/copilot/concepts/context/mcp]; protocol [modelcontextprotocol:specification/2025-06-18] [modelcontextprotocol:docs/getting-started/intro]. Figma frames the benefit as "better code, fewer tokens" when Code Connect is present [FB:the-benefits-of-code-connect-in-mcp] and "design systems and AI: why MCP servers are the unlock" [FB:design-systems-ai-mcp].
S4-surveys | Figma 2025 AI report (V; April 2025; n=2,500 Figma users): 78 percent say AI significantly enhances efficiency but only 32 percent say they can rely on the output; developers 82 percent satisfied vs designers 69 percent; 59 percent of developers vs 31 percent of designers use AI for core work; 51 percent of AI builders build agents (21 percent last year); only 20 percent say most projects are AI powered [FB:figma-2025-ai-report-perspectives] [FR:ai-2025]. Figma shifting-roles report (V; 2025-09-10) [FB:2025-shifting-roles-report]. Figma State of the Designer 2026 exists but only a gated landing page was readable, so NO numbers are cited [FR:state-of-the-designer-2026] [FR:index] [FR:ai-native-organization] [FR:uphill-battle-to-make-magical-products]. Maze Future of User Research 2026 (V): 69 percent use AI in at least some research projects (+19 points); research essential to all levels of business strategy 8 percent (2025) to 22 percent (2026); humans still essential for judgement [maze:resources/user-research-report]. Stack Overflow 2025 developer survey (I-ish, large n): 84 percent use or plan to use AI tools (76 percent prior year); positive sentiment fell from 70 percent+ to 60 percent [survey.stackoverflow:2025/ai].
S4-nng | I. NN/g State of UX 2026 (2026-01-16): job market stabilising, "2026 is shaping up to be the year of AI fatigue", UI is no longer a differentiator, trust is a major design problem for AI features [NNG:state-of-ux-2026]. AI design tools: usefulness improved by May 2025 but "nowhere near" the promise [NNG:ai-design-tools-update-2] [NNG:ai-design-tools-not-ready]. "The custodial era of UX" (2026-08-28): AI builds faster than UX can evaluate, creating UX debt; UX arrives later, deciding what to keep [NNG:ai-ux-debt]. GenUI vs vibe coding (2026-03-27) [NNG:genui-vs-vibe] [NNG:generative-ui]. Design system enforcer (2026-02-06) [NNG:design-system-enforcer]. Figma's own craft framing: "24 artifacts that define craft" [FB:craft-artifacts].
S4-trends | Design-to-code trends supported by primary docs: (1) tokens-first: DTCG 2025.10 final [DTCG:home], Style Dictionary v5 [GH:style-dictionary/style-dictionary], Tailwind v4 `@theme` variables [tailwindcss:docs/theme], Penpot native DTCG tokens [help.penpot:user-guide/design-systems/design-tokens]; (2) component-to-code mapping: Code Connect UI+CLI [HC:23920389749655], shadcn registry [ui.shadcn:docs/registry], Storybook components manifest [storybook.js:docs/ai/mcp/overview]; (3) design system as agent context: Figma library guidelines, skills, MCP search_design_system [FB:figma-agent-and-design-systems] [DEV:figma-mcp-server/tools-and-prompts]; (4) the round trip: code to canvas capture [DEV:figma-mcp-server/code-to-canvas], code layers [FB:config-2026-recap], Make on local code [FB:figma-make-now-on-your-local-code]; (5) in-editor design lint is now a product feature (Check designs) [HC:39592284074263]; (6) measure design-system value (Figma's own guidance) [FB:measuring-the-value-of-design-systems] [FB:the-future-of-design-systems-is-automated].


## (b) Claims that were wrong or outdated, and what changes for the crunk design

Files: note = scratchpad/staged/crunk-design-2026-10-08.md; design = scratchpad/staged/crunk.md (read only).
"Impact" cites crunk.md section numbers.

### b1. Wrong or outdated claims in the note

W1 | Note section 0/A: "help.figma.com pages returned 404 or shell pages". Cause: the help center is a Zendesk site whose article bodies are available as JSON at help.figma.com/api/v2/help_center/en-us/articles/ID.json and whose search is /api/v2/help_center/articles/search.json?query=. All 109 Figma help articles needed were readable. Every "(verify)" in section A that depended on them is now resolved (A20, A31, A53, A-sum2). [HC:360040328273]
W2 | Note section A summary: "Figma ... remains a closed, binary, seat-priced source of truth with no batch lint; that is crunk's wedge." Outdated. Figma ships Check designs (Org/Enterprise, non-LLM design-system adherence lint, suggests variables), a built-in contrast checker, screen-reader prototype mode, and an agent that audits adherence and bulk-fixes. Still true: it is editor-bound, plan-gated, one page at a time, 25K-layer cap, no custom rules, no CI/headless, no cross-target (USS/C#) drift check. [HC:39592284074263] [HC:360041003774] [FB:figma-agent-and-design-systems]
W3 | Note B (DTCG format): "Draft Community Group Report". Wrong: Final Community Group Report, 28 Oct 2025, "considered stable" (not a W3C Standard). [DTCG:tr/2025.10/format]
W4 | Note B (DTCG resolver): "Draft status, not yet 2025.10 stable". Wrong: Resolver Module 2025.10 is also a Final Community Group Report of 28 Oct 2025. [DTCG:tr/2025.10/resolver]
W5 | Note B (DTCG): `$extends` groups flagged unverified. `$extends` exists on groups. [DTCG:tr/2025.10/format]
W6 | Note A36: variable types listed as four (COLOR/FLOAT/STRING/BOOLEAN). In the editor there are six (Timing, Easing added); the REST and Plugin APIs still list four. [HC:14506821864087] [DEV:rest-api/variables-types]
W7 | Note A41: scoping described as restricting binding. Scopes only filter pickers in the Figma UI; Plugin API binding is not blocked. [DEV:rest-api/variables-types]
W8 | Note A20, A31, A53 carried (verify) for grid auto layout, slots, new effects. All three shipped and are documented (grid May 2025; slots beta Oct 2025, all plans; glass/noise/texture/shaders). [HC:31289469907863] [HC:38231200344599] [HC:360041488473]
W9 | Note A72: MCP tool list was 11 names. Now 18 read tools and 12 write tools; GA at Schema 2025 (Oct 2025); Starter/View/Collab capped at 6 tool calls per month; write needs a Full seat. [DEV:figma-mcp-server/tools-and-prompts] [HC:35794667554839]
W10 | Note A69: "Ready for dev" implied universal. The Ready-for-dev VIEW and the Completed status are Org/Enterprise only; Changed ignores library, variable-value and style-value updates. [HC:23918228264855] [HC:26781702258583]
W11 | Note A70: Code Connect described as CLI template files. There are two products: Code Connect UI (GA Oct 2025, Org/Enterprise) and CLI; UI supports multiple code connections per component. [HC:23920389749655] [HC:35794667554839]
W12 | Note B: "Design Lint plugin" listed as a live lint. Last commit 2024-01-12; Figma's Check designs supersedes it. [GH:destefanis/design-lint]
W13 | Note B: tldraw presented as a neutral open canvas SDK. Its licence requires a key for production use. [raw.githubusercontent:tldraw/tldraw/main/LICENSE.md]
W14 | Note B: Style Dictionary "v5 in progress". v5.6.0 shipped 2026-10-03; DTCG 2025.10 support is partial (5.4.0 added dimension objects). [GH:style-dictionary/style-dictionary] [styledictionary:info/dtcg]
W15 | Note B: Tokens Studio "moving toward DTCG". Its default is still the legacy format; DTCG is opt-in. [docs.tokens:manage-settings/token-format]
W16 | Note B: BackstopJS treated as healthy. npm latest 6.3.25 published 2024-09-07; GitHub "latest release" tag is 2019. [GH:garris/BackstopJS]
W17 | Note B: 30 comparables claimed; the table has 23 rows. Fixed by adding 7 (above).
W18 | Note F: XAG "page 404'd on fetch -> (verify)". Correct URL is learn.microsoft.com/en-us/gaming/accessibility/guidelines; XAG V3.2, 23 guidelines (101-123). [XAG:guidelines]
W19 | Note F: HEART "(verify)" resolved: Happiness, Engagement, Adoption, Retention, Task success, with Goals-Signals-Metrics. [static.googleusercontent:media/research.google.com/en//pubs/archive/36299.pdf]
W20 | Note F: Game UX Master Guide cited by the brief; its domain is now a gambling spam site. Remove from any list. (the fetched copy is deliberately excluded from the sources table)
W21 | Note F: CVAA as "(verify)". Rule text is 47 CFR Part 14; the games-specific waiver timeline is still unverified because fcc.gov blocks this host (403).  [ecfr:current/title-47/chapter-I/subchapter-B/part-14]
W22 | Note F: Shopify Polaris listed as a process reference. Polaris React is archived; Polaris Web Components replaced it on 2025-10-01. [raw.githubusercontent:Shopify/polaris/main/README.md]
W23 | Note A78: REST rate limiting "by seat/plan tier since 2025-11-17" was right but gave no numbers; numbers now in A50/A78. [DEV:rest-api/rate-limits]
W24 | Note B (cosmic-text): shaping assumed rustybuzz. Current README says HarfRust. [GH:pop-os/cosmic-text]
W25 | Note A: "REST write to canvas has no asset import yet": Figma's own pages disagree (upload_assets tool exists vs write-to-canvas limitations list). Treat as unstable. [DEV:figma-mcp-server/write-to-canvas] [DEV:figma-mcp-server/tools-and-prompts]

### b2. Recommended changes to crunk.md (design draft), in priority order

C1 (section 1 Principle, wedge statement) | Rewrite the "why not Figma" paragraph around what is still uncovered: headless/CI, user-authored rules, text diff, cross-target (CSS/Tailwind/USS/C#) drift, and a human-ack lock. Add one sentence that Figma Check designs exists (Org/Enterprise) and that crunk should import its findings model (hard-coded value -> suggested variable) rather than compete on in-editor UX. Evidence W2.
C2 (section 2 tokens, D109) | State DTCG 2025.10 as Final Community Group Report (28 Oct 2025), resolver included, `$extends` available; pin by version. Add `timing` and `easing` token types (DTCG duration/cubicBezier; Figma Timing/Easing) and record that the Figma REST variables API cannot carry them (four types only); `crunk export figma-variables` must either skip them with a warning (EXPORT finding) or emit a Plugin-API script. Evidence W3, W4, W6.
C3 (section 2 tokens, scopes) | Make scope violation a real T0 lint (TOKEN family): Figma does not enforce scopes outside its pickers, so crunk is the enforcement point. Round-trip `scopes`, `codeSyntax` (WEB/ANDROID/iOS names) and `hiddenFromPublishing` on import/export. Evidence W7, A41-A43.
C4 (section 2 tokens, modes) | Add a a `figma` plan setting (`professional|organization|enterprise`); `crunk export figma-variables` fails when modes per collection exceed 10 / 20 (Enterprise unlimited with extended collections). Model brand layers as extended collections (parent defines variables/modes/scope; child only overrides). Evidence A38, A40.
C5 (section 2 components) | Slot prop: add `accepts` (preferred instances), `min`, `max` layers (Figma slot settings). Replace single `code = {path, export}` with a list keyed by framework label (a TOML array of tables, one per framework label (React, SwiftUI, ...)) because Code Connect UI and the MCP clientFrameworks parameter are multi-framework; add `agent_notes` (Code Connect UI "MCP usage instructions"). Evidence A31, A70, A72.
C6 (section 2 screens / section 5 status) | Status set: `draft | ready | changed | completed` (Figma has Completed on Org/Enterprise). Keep crunk's hash stricter than Figma's (include resolved token values) and say so; Figma deliberately does not flag changes from library/variable/style updates. Evidence A69.
C7 (section 3 scenes) | Add grid flow (cells/tracks/spans) and wrap for both flows to the dialect list, and a PORT lint family flagging Figma-only effects (glass, noise, texture, shader) and blend modes with no USS/CSS equivalent. Evidence A15, A20, A53.
C8 (section 3 layout engine) | Keep taffy (v0.14.0, Block/Flex/Grid, measure callback). Text spike candidates: cosmic-text 0.19 (HarfRust) vs parley 0.11. Add Blitz (beta; Stylo+Taffy+Parley+Vello) as an extra parity oracle between taffy-only and Chromium. Add `resvg` for deterministic SVG icon rasterisation at T2. Evidence B-taffy, B-cosmic-text, B-parley, B-Blitz, B-resvg.
C9 (section 6 CONTRAST/COLOR) | Contrast gate = WCAG 2.2 ratio (1.4.3 etc.); APCA is advisory only and opt-in (`contrast_model = "wcag"|"apca"`), because WCAG 3.0 (Working Draft, 2026-09-10) still says its contrast algorithm is to be determined. Apple's HIG names APCA only as an alternative. Evidence F1b-wcag3.
C10 (section 2 profiles; section 6 LAYOUT/A11Y) | Target-size thresholds must be per profile and named by standard: WCAG 2.2 AA 24x24 CSS px, Apple 44x44 pt, Android/Material 48x48 dp plus 8 dp spacing. Change "mobile targets (44/48 px)" to units dp/pt/css-px. Evidence F1b-targets.
C11 (section 6 GX, section 7) | Give GX lints numbers: min text body height console 26 px at 1080p (52 at 4K), PC 18 px at 1080p, handheld Steam Deck 9 px at 1280x800, scalable to 200 percent; text contrast 4.5:1 (3:1 large/inactive), high-contrast mode 7:1; focus indicator always visible and never offscreen/hidden; flash rule (10 percent luminance change, more than 3 per second, about 20 percent of screen). Measure glyph BODY HEIGHT from font metrics at T1, not CSS font-size. Evidence F2-readability, F2-menus, F2-feedback.
C12 (section 7 Unity) | USS exporter must pre-resolve anything USS lacks: no var() inside functions (so no rgba(var(--c), a)), no math on variables; emit separate alpha tokens. TSS is plain USS with @import; use it for platform/language variants. Check `input.toml` against Unity Input System project-wide actions (UI Toolkit reads them directly since 2023.2; current package 1.18.0). Evidence B-UnityUIToolkit, F2-input.
C13 (section 5 serve / MCP) | Mirror Figma's token-economy pattern: `get_metadata`-style sparse outline first, then drill (Figma documents a 20kb per-call output cap and warns about large frames); also `whoami`, `search_design_system`, `get_code_map`, and a library-level `design/guidelines.md` that the server attaches automatically (Figma "add guidelines to a published library"). Treat "design system as MCP server" as table stakes (Figma, Penpot, Storybook, shadcn, Carbon, Plasmic). Evidence A72, S4-mcp-everywhere.
C14 (section 8 design cycle) | Add an optional `phase = "discovery|alpha|beta|live"` project setting (GOV.UK phases, each ending in an assessment) that selects a lint profile: alpha = structure lints only, beta = full A11Y + HUMAN001, live = metrics/experiments required. Use Carbon's discovery/delivery/launch-and-scale plus definition of done and a component checklist as the model for component status (`experimental|stable|deprecated`). Evidence F1b-govuk, F1-handoff.
C15 (section 8 research/QA) | Metrics file: add `goal`, `signal`, `metric`, `heart` (optional enum) per HEART's Goals-Signals-Metrics. Heuristic file: use the exact ten NN/g names as the enum. Walkthrough file: four fixed questions, a step fails if any answer is No. Advisory sample-size defaults: usability 5 per group, card sort qualitative >= 15 and quantitative 30-50, 30-50 cards. Evidence F1-usability-QA, F1-ia, F1-post-launch.
C16 (section 4.1 human lock; PROC rules) | Strengthened by NN/g "custodial era" (AI generates faster than UX can evaluate) and "design system needs an enforcer" (an owner with veto, recurring reviews). Add `provenance = "human|agent"` to specs so agent-authored screens default to `review = "human"`, and make `crunk review` the recurring-review queue. Evidence S4-nng.
C17 (build order, section 9) | Move into phase 1/2: scope-enforcement lint and timing/easing tokens (cheap, T0); plan-limit check in the figma-variables exporter. Move `crunk serve` read tools (sparse outline, search, guidelines) from phase 3 to phase 2 because every comparable now ships one. Keep scene/solver order. Evidence C3, C4, C13.
C18 (non-goals / deps) | Do not take tldraw as the future GUI canvas (licence key for production); Excalidraw (MIT) or Penpot (MPL-2.0, native DTCG tokens, MCP) are the safer interop targets. Add Penpot MCP/file format to `crunk import penpot` priority. Evidence B-tldraw, B-Penpot.
C19 (docs hygiene) | Replace "Draft" DTCG language; drop Game UX Master Guide, Polaris React and Design Lint from any reference list.

### b3. What stayed true

T1 The Variables REST API write path is Enterprise + Full seat only [DEV:rest-api/variables]; Starter/View seats are tightly rate limited [DEV:rest-api/rate-limits]. The argument for a text source of truth survives.
T2 Figma MCP can now write to the canvas (use_figma, Full seat) and read design context; Figma remains read-mostly for variables via REST outside Enterprise [DEV:figma-mcp-server/write-to-canvas].
T3 axe-core catches only a fraction of WCAG issues (Storybook docs: up to 57 percent) so T4 human review stays necessary [storybook.js:docs/writing-tests/accessibility-testing].
T4 Storybook+axe+Chromatic remains the nearest analogue of screens/states/accessibility/visual-review [storybook.js:docs/writing-tests].


## (d) Unverified or open items (carry forward as tickets, do not treat as facts)

O1 | Whether Figma extended-collection children can hold local variables (help text says no; REST exposes localVariableIds). Needs a live Enterprise file.
O2 | Whether Figma MCP write-to-canvas supports image assets (limitations list says no; upload_assets tool exists).
O3 | FCC game accessibility waiver end date and current CVAA obligations for in-game chat (fcc.gov blocked).
O4 | Stark CI/API capabilities (homepage claims only integrations).
O5 | Plasmic codegen CLI and Framer lint capabilities (docs landing pages only).
O6 | Material Design 3 accessibility numbers (site is JS-only); Android 48dp and Apple 44pt were verified via platform docs instead.
O7 | Figma State of the Designer 2026 findings (gated).
O8 | Whether the Double Diamond expansion is dated 2019 (not on the fetched Design Council pages).
O9 | Galileo AI to Stitch lineage (no fetched source).
O10 | uGUI/Canvas Scaler claims in the note (no uGUI page fetched).

## (c) Sources table

Columns: key | URL | title | author or org | date | fetched | rows it supports (A=Figma row, B=comparable, F=design cycle/GX, S4=state of practice, W/C/T=sections b).
Date 'n/d' = not extracted from the page. 'updated' dates for help.figma.com are last-updated stamps.

| key | URL | title | author or org | date | fetched | supports |
|---|---|---|---|---|---|---|
| DEV:code-connect | https://developers.figma.com/docs/code-connect/ | Introduction / Developer Docs | Figma Developer Docs | n/d | yes | A70, B-CodeConnect |
| DEV:code-connect/quickstart-guide | https://developers.figma.com/docs/code-connect/quickstart-guide/ | Getting started with Code Connect CLI / Developer Docs | Figma Developer Docs | n/d | yes | A70 |
| DEV:figma-mcp-server | https://developers.figma.com/docs/figma-mcp-server/ | Introduction / Developer Docs | Figma Developer Docs | n/d | yes | S4-mcp-everywhere |
| DEV:figma-mcp-server/code-connect-integration | https://developers.figma.com/docs/figma-mcp-server/code-connect-integration/ | Code Connect integration / Developer Docs | Figma Developer Docs | n/d | yes | context only (read, not cited per row) |
| DEV:figma-mcp-server/code-to-canvas | https://developers.figma.com/docs/figma-mcp-server/code-to-canvas/ | Code to canvas / Developer Docs | Figma Developer Docs | n/d | yes | A72, S4-trends |
| DEV:figma-mcp-server/generative-plugins-and-shaders | https://developers.figma.com/docs/figma-mcp-server/generative-plugins-and-shaders/ | Generative plugins and shaders / Developer Docs | Figma Developer Docs | n/d | yes | A72 |
| DEV:figma-mcp-server/remote-server-installation | https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/ | Set up the remote server (recommended) / Developer Docs | Figma Developer Docs | n/d | yes | A72 |
| DEV:figma-mcp-server/tools-and-prompts | https://developers.figma.com/docs/figma-mcp-server/tools-and-prompts/ | Tools and prompts / Developer Docs | Figma Developer Docs | n/d | yes | A56, A65, A72, A-sum1, S4-trends, W9, W25 |
| DEV:figma-mcp-server/write-to-canvas | https://developers.figma.com/docs/figma-mcp-server/write-to-canvas/ | Write to canvas / Developer Docs | Figma Developer Docs | n/d | yes | A77, A-sum1, W25 |
| DEV:plugins | https://developers.figma.com/docs/plugins/ | Introduction / Developer Docs | Figma Developer Docs | n/d | yes | A77 |
| DEV:plugins/api/Variable | https://developers.figma.com/docs/plugins/api/Variable/ | Variable / Developer Docs | Figma Developer Docs | n/d | yes | A36, A42 |
| DEV:plugins/api/VariableCollection | https://developers.figma.com/docs/plugins/api/VariableCollection/ | VariableCollection / Developer Docs | Figma Developer Docs | n/d | yes | A40 |
| DEV:rest-api | https://developers.figma.com/docs/rest-api/ | Introduction / Developer Docs | Figma Developer Docs | n/d | yes | context only (read, not cited per row) |
| DEV:rest-api/comments-endpoints | https://developers.figma.com/docs/rest-api/comments-endpoints/ | Endpoints / Developer Docs | Figma Developer Docs | n/d | yes | A76 |
| DEV:rest-api/dev-resources-endpoints | https://developers.figma.com/docs/rest-api/dev-resources-endpoints/ | Endpoints / Developer Docs | Figma Developer Docs | n/d | yes | A71 |
| DEV:rest-api/file-endpoints | https://developers.figma.com/docs/rest-api/file-endpoints/ | Endpoints / Developer Docs | Figma Developer Docs | n/d | yes | A1, A78 |
| DEV:rest-api/library-analytics-endpoints | https://developers.figma.com/docs/rest-api/library-analytics-endpoints/ | Endpoints / Developer Docs | Figma Developer Docs | n/d | yes | A73 |
| DEV:rest-api/rate-limits | https://developers.figma.com/docs/rest-api/rate-limits/ | Rate Limits / Developer Docs | Figma Developer Docs | effective 2025-11-17 | yes | A50, A78, W23 |
| DEV:rest-api/scopes | https://developers.figma.com/docs/rest-api/scopes/ | Scopes / Developer Docs | Figma Developer Docs | n/d | yes | A78 |
| DEV:rest-api/variables | https://developers.figma.com/docs/rest-api/variables/ | Variables / Developer Docs | Figma Developer Docs | n/d | yes | A50 |
| DEV:rest-api/variables-endpoints | https://developers.figma.com/docs/rest-api/variables-endpoints/ | Endpoints / Developer Docs | Figma Developer Docs | n/d | yes | A50 |
| DEV:rest-api/variables-types | https://developers.figma.com/docs/rest-api/variables-types/ | Types / Developer Docs | Figma Developer Docs | n/d | yes | A36, A37, A40, A41, A42, A43, W6, W7 |
| DEV:rest-api/version-history-endpoints | https://developers.figma.com/docs/rest-api/version-history-endpoints/ | Endpoints / Developer Docs | Figma Developer Docs | n/d | yes | A74 |
| DEV:rest-api/webhooks | https://developers.figma.com/docs/rest-api/webhooks/ | Webhooks V2 / Developer Docs | Figma Developer Docs | n/d | yes | A76 |
| DTCG:home | https://www.designtokens.org/ | Design Tokens Community Group | W3C Design Tokens Community Group | n/d | yes | B-DTCG-format, S4-trends |
| DTCG:tr/2025.10/color | https://www.designtokens.org/tr/2025.10/color/ | Design Tokens Color Module 2025.10 | W3C Design Tokens Community Group | 2025-10-28 | yes | B-DTCG-format |
| DTCG:tr/2025.10/format | https://www.designtokens.org/tr/2025.10/format/ | Design Tokens Format Module 2025.10 | W3C Design Tokens Community Group | 2025-10-28 | yes | B-DTCG-format, W3, W5 |
| DTCG:tr/2025.10/resolver | https://www.designtokens.org/tr/2025.10/resolver/ | Design Tokens Resolver Module 2025.10 | W3C Design Tokens Community Group | 2025-10-28 | yes | B-DTCG-resolver, W4 |
| DTCG:tr/drafts/resolver | https://www.designtokens.org/tr/drafts/resolver/ | Design Tokens Resolver Module 2025.10 | W3C Design Tokens Community Group | 2025-10-28 | yes | B-DTCG-resolver |
| FB:2025-shifting-roles-report | https://www.figma.com/blog/2025-shifting-roles-report/ | Are Roles and Responsibilities a Thing of the Past? / Figma Blog | Figma Blog | 2025-09-10 | yes | S4-surveys |
| FB:3-ways-product-designers-use-the-figma-agent | https://www.figma.com/blog/3-ways-product-designers-use-the-figma-agent/ | 3 Ways Product Designers Use the Figma agent / Figma Blog | Figma Blog | 2026-10-06 | yes | S4-figma-agent |
| FB:agent-custom-tools-context-skills | https://www.figma.com/blog/agent-custom-tools-context-skills/ | Figma?s Design Agent, Now With Custom Tools and Greater Context / Figma Blog | Figma Blog | 2026-06-24 | yes | S4-figma-agent |
| FB:bringing-figma-make-to-the-canvas | https://www.figma.com/blog/bringing-figma-make-to-the-canvas/ | Bringing Figma Make to the Canvas / Figma Blog | Figma Blog | n/d | yes | S4-make |
| FB:building-accessibility-into-a-canvas-based-product | https://www.figma.com/blog/building-accessibility-into-a-canvas-based-product/ | Building Accessibility Into a Canvas-Based Product / Figma Blog | Figma Blog | n/d | yes | context only (read, not cited per row) |
| FB:config-2025-press-release | https://www.figma.com/blog/config-2025-press-release/ | Config 2025 Launches Deepen Figma's Design Capabilities As Its Platform Expands / Figma Blog | Figma Blog | 2025-05-07 | yes | A5, A20, S4-make |
| FB:config-2026-recap | https://www.figma.com/blog/config-2026-recap/ | Config 2026: New Materials, New Tools and a More Expressive Canvas / Figma Blog | Figma Blog | 2026-06-24 | yes | A53, A65, A77, S4-figma-agent, S4-make, S4-trends |
| FB:craft-artifacts | https://www.figma.com/blog/craft-artifacts/ | 24 Artifacts That Define Craft / Figma Blog | Figma Blog | n/d | yes | S4-nng |
| FB:design-systems-ai-mcp | https://www.figma.com/blog/design-systems-ai-mcp/ | Design Systems And AI: Why MCP Servers Are The Unlock / Figma Blog | Figma Blog | n/d | yes | S4-mcp-everywhere |
| FB:dev-mode-ga | https://www.figma.com/blog/dev-mode-ga/ | What?s next for Dev Mode: Annotations, Compare Changes, Plugins, and More / Figma Blog | Figma Blog | 2024-01-25 | yes | A68, A69 |
| FB:figjam-your-coding-agents-whiteboard | https://www.figma.com/blog/figjam-your-coding-agents-whiteboard/ | FigJam Is Now Your Coding Agent?s Whiteboard Too / Figma Blog | Figma Blog | n/d | yes | context only (read, not cited per row) |
| FB:figma-2025-ai-report-perspectives | https://www.figma.com/blog/figma-2025-ai-report-perspectives/ | Figma's 2025 AI report: Perspectives From Designers and Developers / Figma Blog | Figma Blog | 2025-04-24 | yes | S4-surveys |
| FB:figma-agent | https://www.figma.com/blog/figma-agent/ | Tag: Figma Agent / Figma Blog | Figma Blog | n/d | yes | S4-figma-agent |
| FB:figma-agent-and-design-systems | https://www.figma.com/blog/figma-agent-and-design-systems/ | How to Lighten Design System Upkeep With the Figma Agent / Figma Blog | Figma Blog | 2026-10-06 | yes | A-sum2, S4-figma-agent, S4-trends, W2 |
| FB:figma-make-now-on-your-local-code | https://www.figma.com/blog/figma-make-now-on-your-local-code/ | Figma Make, Now on Your Local Code / Figma Blog | Figma Blog | 2026-05-28 | yes | S4-make, S4-trends |
| FB:figma-weave | https://www.figma.com/blog/figma-weave/ | Tag: Figma Weave / Figma Blog | Figma Blog | tag page | yes | context only (read, not cited per row) |
| FB:introducing-figma-make | https://www.figma.com/blog/introducing-figma-make/ | Introducing Figma Make: A New Way to Test, Edit, and Prompt Designs / Figma Blog | Figma Blog | 2025-05-07 | yes | S4-make |
| FB:introducing-figma-mcp-server | https://www.figma.com/blog/introducing-figma-mcp-server/ | Introducing our Dev Mode MCP server: Bringing Figma into your workflow / Figma Blog | Figma Blog | 2025-06-04 | yes | A72 |
| FB:introducing-figma-motion | https://www.figma.com/blog/introducing-figma-motion/ | Introducing Figma Motion: Your Canvas Now Has a Timeline / Figma Blog | Figma Blog | 2026-06-24 | yes | A65 |
| FB:introducing-make-kits-and-make-attachments | https://www.figma.com/blog/introducing-make-kits-and-make-attachments/ | Build With More Context and More Control in Figma Make / Figma Blog | Figma Blog | 2026-04-02 | yes | S4-make |
| FB:measuring-the-value-of-design-systems | https://www.figma.com/blog/measuring-the-value-of-design-systems/ | Measuring the value of design systems / Figma Blog | Figma Blog | n/d | yes | S4-trends |
| FB:schema-2025-design-systems-recap | https://www.figma.com/blog/schema-2025-design-systems-recap/ | Schema 2025: Design Systems For A New Era / Figma Blog | Figma Blog | 2025-10-28 | yes | context only (read, not cited per row) |
| FB:the-benefits-of-code-connect-in-mcp | https://www.figma.com/blog/the-benefits-of-code-connect-in-mcp/ | Better Code, Fewer Tokens: The Benefits of Code Connect in MCP / Figma Blog | Figma Blog | n/d | yes | S4-mcp-everywhere |
| FB:the-future-of-design-is-code-and-canvas | https://www.figma.com/blog/the-future-of-design-is-code-and-canvas/ | The Future of Design Is Code and Canvas / Figma Blog | Figma Blog | n/d | yes | S4-make |
| FB:the-future-of-design-systems-is-automated | https://www.figma.com/blog/the-future-of-design-systems-is-automated/ | The Future of Design Systems is Automated / Figma Blog | Figma Blog | 2023-03-02 | yes | S4-trends |
| FB:the-state-of-design | https://www.figma.com/blog/the-state-of-design/ | Issue no.15: The State of Design / Figma Blog | Figma Blog | n/d | yes | context only (read, not cited per row) |
| FB:workflow-lab-moving-between-design-and-code-with-agents | https://www.figma.com/blog/workflow-lab-moving-between-design-and-code-with-agents/ | Workflow Lab: Moving Between Design and Code With Agents / Figma Blog | Figma Blog | n/d | yes | S4-figma-agent |
| FR:ai-2025 | https://www.figma.com/reports/ai-2025/ | Figma?s 2025 AI report / Figma | Figma Reports | n/d | yes | S4-surveys |
| FR:ai-native-organization | https://www.figma.com/reports/ai-native-organization/ | The guide to building an AI-native organization | Figma Reports | n/d | yes | S4-surveys |
| FR:forrester-tei-dev-mode | https://www.figma.com/reports/forrester-tei-dev-mode/ | The ROI of Dev Mode: Built for design-dev efficiency | Figma Reports | n/d | yes | F1-handoff |
| FR:index | https://www.figma.com/reports/ | Reports & Insights / Figma | Figma Reports | n/d | yes | S4-surveys |
| FR:state-of-the-designer-2026 | https://www.figma.com/reports/state-of-the-designer-2026/ | State of the Designer 2026 / Figma | Figma Reports | n/d | yes | S4-surveys |
| FR:uphill-battle-to-make-magical-products | https://www.figma.com/reports/uphill-battle-to-make-magical-products/ | The uphill battle to make magical products / Figma | Figma Reports | n/d | yes | S4-surveys |
| GH:BuilderIO/mitosis | https://github.com/BuilderIO/mitosis | GitHub - BuilderIO/mitosis: Write components once, run everywhere. Compiles to React, Vue, Qwik, Solid, Angula | GitHub repo (README and/or API metadata) | n/d | yes | B-Mitosis |
| GH:DioxusLabs/blitz | https://github.com/DioxusLabs/blitz | GitHub - DioxusLabs/blitz: A radically modular HTML/CSS rendering engine ? GitHub | GitHub repo (README and/or API metadata) | n/d | yes | B-Blitz (added) |
| GH:DioxusLabs/taffy | https://github.com/DioxusLabs/taffy | GitHub - DioxusLabs/taffy: A high performance rust-powered UI layout library ? GitHub | GitHub repo (README and/or API metadata) | n/d | yes | B-taffy |
| GH:GoogleChrome/lighthouse | https://github.com/GoogleChrome/lighthouse | GitHub repo metadata GoogleChrome/lighthouse (api: lic Apache-2.0, pushed 2026-10-08, latest v13.5.0) | GitHub repo (README and/or API metadata) | pushed 2026-10-08 | yes | B-Lighthouse |
| GH:Shopify/polaris | https://github.com/Shopify/polaris | GitHub - Shopify/polaris-react-archive: Shopify's Polaris Design System - React implementation (Deprecated) ?  | GitHub repo (README and/or API metadata) | n/d | yes | F1-handoff |
| GH:chromaui/chromatic-cli | https://github.com/chromaui/chromatic-cli | GitHub repo metadata chromaui/chromatic-cli (api: lic MIT, pushed 2026-10-07, latest v18.11.0) | GitHub repo (README and/or API metadata) | pushed 2026-10-07 | yes | B-Chromatic |
| GH:dequelabs/axe-core | https://github.com/dequelabs/axe-core | GitHub repo metadata dequelabs/axe-core (api: lic MPL-2.0, pushed 2026-10-07, latest v4.14.0) | GitHub repo (README and/or API metadata) | pushed 2026-10-07 | yes | B-axe-core |
| GH:design-tokens/community-group | https://github.com/design-tokens/community-group | GitHub repo metadata design-tokens/community-group (api: lic NOASSERTION, pushed 2026-09-08, latest None) | GitHub repo (README and/or API metadata) | pushed 2026-09-08 | yes | B-DTCG-format |
| GH:destefanis/design-lint | https://github.com/destefanis/design-lint | GitHub - destefanis/design-lint: A design linting plugin for Figma. ? GitHub | GitHub repo (README and/or API metadata) | n/d | yes | B-DesignLint, W12 |
| GH:excalidraw/excalidraw | https://github.com/excalidraw/excalidraw | GitHub repo metadata excalidraw/excalidraw (api: lic MIT, pushed 2026-10-07, latest v0.18.1) | GitHub repo (README and/or API metadata) | pushed 2026-10-07 | yes | B-Excalidraw |
| GH:figma/code-connect | https://github.com/figma/code-connect | GitHub repo metadata figma/code-connect (api: lic MIT, pushed 2026-09-23, latest v2.0.1) | GitHub repo (README and/or API metadata) | pushed 2026-09-23 | yes | A70, B-CodeConnect |
| GH:garris/BackstopJS | https://github.com/garris/BackstopJS | GitHub - garris/BackstopJS: Catch CSS curve balls. ? GitHub | GitHub repo (README and/or API metadata) | n/d | yes | B-BackstopJS, W16 |
| GH:linebender/parley | https://github.com/linebender/parley | GitHub - linebender/parley: Rich text layout library ? GitHub | GitHub repo (README and/or API metadata) | n/d | yes | B-parley (added) |
| GH:linebender/resvg | https://github.com/linebender/resvg | GitHub - linebender/resvg: An SVG rendering library. ? GitHub | GitHub repo (README and/or API metadata) | n/d | yes | B-resvg (added) |
| GH:material-components/material-web | https://github.com/material-components/material-web | GitHub - material-components/material-web: Material Design Web Components ? GitHub | GitHub repo (README and/or API metadata) | n/d | yes | F1b-targets |
| GH:microsoft/playwright | https://github.com/microsoft/playwright | GitHub repo metadata microsoft/playwright (api: lic Apache-2.0, pushed 2026-10-08, latest v1.64.0) | GitHub repo (README and/or API metadata) | pushed 2026-10-08 | yes | B-Playwright |
| GH:pa11y/pa11y | https://github.com/pa11y/pa11y | GitHub repo metadata pa11y/pa11y (api: lic LGPL-3.0, pushed 2026-09-28, latest 10.0.0) | GitHub repo (README and/or API metadata) | pushed 2026-09-28 | yes | B-pa11y |
| GH:penpot/penpot | https://github.com/penpot/penpot | GitHub repo metadata penpot/penpot (api: lic MPL-2.0, pushed 2026-10-07, latest 2.18.3) | GitHub repo (README and/or API metadata) | pushed 2026-10-07 | yes | B-Penpot |
| GH:plasmicapp/plasmic | https://github.com/plasmicapp/plasmic | GitHub repo metadata plasmicapp/plasmic (api: lic MIT, pushed 2026-10-07, latest None) | GitHub repo (README and/or API metadata) | pushed 2026-10-07 | yes | B-Plasmic |
| GH:pop-os/cosmic-text | https://github.com/pop-os/cosmic-text | GitHub - pop-os/cosmic-text: Pure Rust multi-line text handling ? GitHub | GitHub repo (README and/or API metadata) | n/d | yes | B-cosmic-text (added), W24 |
| GH:storybookjs/storybook | https://github.com/storybookjs/storybook | GitHub repo metadata storybookjs/storybook (api: lic MIT, pushed 2026-10-08, latest v10.6.1) | GitHub repo (README and/or API metadata) | pushed 2026-10-08 | yes | B-Storybook |
| GH:style-dictionary/style-dictionary | https://github.com/style-dictionary/style-dictionary | GitHub repo metadata style-dictionary/style-dictionary (api: lic Apache-2.0, pushed 2026-10-03, latest v5.6.0) | GitHub repo (README and/or API metadata) | pushed 2026-10-03 | yes | B-StyleDictionary, S4-trends, W14 |
| GH:tldraw/tldraw | https://github.com/tldraw/tldraw | GitHub repo metadata tldraw/tldraw (api: lic NOASSERTION, pushed 2026-10-07, latest v5.5.2) | GitHub repo (README and/or API metadata) | pushed 2026-10-07 | yes | B-tldraw |
| GH:tokens-studio/figma-plugin | https://github.com/tokens-studio/figma-plugin | GitHub repo metadata tokens-studio/figma-plugin (api: lic MIT, pushed 2026-10-07, latest 2.13.0) | GitHub repo (README and/or API metadata) | pushed 2026-10-07 | yes | B-TokensStudio |
| GOVUK:guidance/content-design/what-is-content-design | https://www.gov.uk/guidance/content-design/what-is-content-design | Understand content design - GOV.UK content and publishing guidanceGOV.UK | UK Government Digital Service | n/d | yes | F1-ui-design |
| GOVUK:sm/agile-delivery | https://www.gov.uk/service-manual/agile-delivery | Agile delivery - Service Manual - GOV.UKGOV.UK | UK Government Digital Service | n/d | yes | F1b-govuk |
| GOVUK:sm/agile-delivery/how-the-alpha-phase-works | https://www.gov.uk/service-manual/agile-delivery/how-the-alpha-phase-works | How the alpha phase works - Service Manual - GOV.UKGOV.UK | UK Government Digital Service | n/d | yes | F1-prototyping |
| GOVUK:sm/agile-delivery/how-the-beta-phase-works | https://www.gov.uk/service-manual/agile-delivery/how-the-beta-phase-works | How the beta phase works - Service Manual - GOV.UKGOV.UK | UK Government Digital Service | n/d | yes | F1b-govuk |
| GOVUK:sm/agile-delivery/how-the-discovery-phase-works | https://www.gov.uk/service-manual/agile-delivery/how-the-discovery-phase-works | How the discovery phase works - Service Manual - GOV.UKGOV.UK | UK Government Digital Service | n/d | yes | F1-research |
| GOVUK:sm/agile-delivery/how-the-live-phase-works | https://www.gov.uk/service-manual/agile-delivery/how-the-live-phase-works | How the live phase works - Service Manual - GOV.UKGOV.UK | UK Government Digital Service | n/d | yes | F1b-govuk |
| GOVUK:sm/design | https://www.gov.uk/service-manual/design | Design - Service Manual - GOV.UKGOV.UK | UK Government Digital Service | n/d | yes | F1b-govuk |
| GOVUK:sm/design/writing-for-user-interfaces | https://www.gov.uk/service-manual/design/writing-for-user-interfaces | Writing for user interfaces - Service Manual - GOV.UKGOV.UK | UK Government Digital Service | n/d | yes | F1-ui-design |
| GOVUK:sm/service-assessments | https://www.gov.uk/service-manual/service-assessments | Service assessments and applying the Service Standard - Service Manual - GOV.UKGOV.UK | UK Government Digital Service | n/d | yes | F1b-govuk |
| GOVUK:sm/service-standard | https://www.gov.uk/service-manual/service-standard | Service Standard - Service Manual - GOV.UKGOV.UK | UK Government Digital Service | n/d | yes | F1-research, F1b-govuk |
| GOVUK:sm/user-research | https://www.gov.uk/service-manual/user-research | User research - Service Manual - GOV.UKGOV.UK | UK Government Digital Service | n/d | yes | F1-research |
| GOVUKDS:accessibility | https://design-system.service.gov.uk/accessibility/ | Accessibility ? GOV.UK Design SystemGOV.UK | UK Government Digital Service | n/d | yes | F1b-systems |
| GOVUKDS:community | https://design-system.service.gov.uk/community/ | Community ? GOV.UK Design SystemGOV.UK | UK Government Digital Service | n/d | yes | F1-handoff |
| GOVUKDS:community/contribution-criteria | https://design-system.service.gov.uk/community/contribution-criteria/ | Contribution criteria ? GOV.UK Design SystemGOV.UK | UK Government Digital Service | n/d | yes | F1-handoff |
| GOVUKDS:community/propose-a-component-or-pattern | https://design-system.service.gov.uk/community/propose-a-component-or-pattern/ | Propose a component or pattern ? GOV.UK Design SystemGOV.UK | UK Government Digital Service | n/d | yes | F1-handoff |
| GOVUKDS:home | https://design-system.service.gov.uk/ | Home ? GOV.UK Design SystemGOV.UK | UK Government Digital Service | n/d | yes | F1b-systems |
| HC:13402894554519 | https://help.figma.com/hc/en-us/articles/13402894554519 | Export formats and settings for static designs (upd 2026-10-01) | Figma Help Center | updated 2026-10-01 | yes | A56 |
| HC:14506587589399 | https://help.figma.com/hc/en-us/articles/14506587589399 | Use variables in prototypes (upd 2026-08-18) | Figma Help Center | updated 2026-08-18 | yes | A45, A62 |
| HC:14506821864087 | https://help.figma.com/hc/en-us/articles/14506821864087 | Overview of variables, collections, and modes (upd 2026-10-05) | Figma Help Center | updated 2026-10-05 | yes | A16, A36, A39, A44, A65, W6 |
| HC:14552804059927 | https://help.figma.com/hc/en-us/articles/14552804059927 | Lesson 4: Document and manage your system (upd 2026-09-22) | Figma Help Center | updated 2026-09-22 | yes | context only (read, not cited per row) |
| HC:14552901442839 | https://help.figma.com/hc/en-us/articles/14552901442839 | Overview: Introduction to design systems (upd 2026-10-07) | Figma Help Center | updated 2026-10-07 | yes | context only (read, not cited per row) |
| HC:15023124644247 | https://help.figma.com/hc/en-us/articles/15023124644247 | Guide to Dev Mode in Figma (upd 2026-10-08) | Figma Help Center | updated 2026-10-08 | yes | A32, F1-handoff |
| HC:15023193382935 | https://help.figma.com/hc/en-us/articles/15023193382935 | Compare changes in Dev Mode (upd 2026-10-02) | Figma Help Center | updated 2026-10-02 | yes | A69, F1-handoff |
| HC:15023202277399 | https://help.figma.com/hc/en-us/articles/15023202277399 | Use code snippets in Dev Mode (upd 2026-10-08) | Figma Help Center | updated 2026-10-08 | yes | A66 |
| HC:15023231995927 | https://help.figma.com/hc/en-us/articles/15023231995927 | Link Dev resources to layers in Dev Mode (upd 2026-08-20) | Figma Help Center | updated 2026-08-20 | yes | A71 |
| HC:15145852043927 | https://help.figma.com/hc/en-us/articles/15145852043927 | Create and manage variables and collections (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A50 |
| HC:15253194385943 | https://help.figma.com/hc/en-us/articles/15253194385943 | Use expressions in prototypes (upd 2026-09-04) | Figma Help Center | updated 2026-09-04 | yes | A45, A62 |
| HC:15253220891799 | https://help.figma.com/hc/en-us/articles/15253220891799 | Multiple actions and conditionals (upd 2026-09-05) | Figma Help Center | updated 2026-09-05 | yes | A59, A62 |
| HC:15253268379799 | https://help.figma.com/hc/en-us/articles/15253268379799 | Variable modes in prototypes (upd 2026-06-15) | Figma Help Center | updated 2026-06-15 | yes | A38 |
| HC:15339657135383 | https://help.figma.com/hc/en-us/articles/15339657135383 | Guide to variables in Figma (upd 2026-10-05) | Figma Help Center | updated 2026-10-05 | yes | context only (read, not cited per row) |
| HC:15343107263511 | https://help.figma.com/hc/en-us/articles/15343107263511 | Apply variables to designs (upd 2026-09-29) | Figma Help Center | updated 2026-09-29 | yes | A44 |
| HC:15343816063383 | https://help.figma.com/hc/en-us/articles/15343816063383 | Modes for variables (upd 2026-10-07) | Figma Help Center | updated 2026-10-07 | yes | A38, A41 |
| HC:15871097384471 | https://help.figma.com/hc/en-us/articles/15871097384471 | The difference between variables and styles (upd 2026-09-23) | Figma Help Center | updated 2026-09-23 | yes | A46 |
| HC:20774752502935 | https://help.figma.com/hc/en-us/articles/20774752502935 | Add measurements and annotate designs (upd 2026-10-08) | Figma Help Center | updated 2026-10-08 | yes | A67, A68 |
| HC:20953528101783 | https://help.figma.com/hc/en-us/articles/20953528101783 | Design an interactive button component (upd 2026-10-07) | Figma Help Center | updated 2026-10-07 | yes | A34 |
| HC:22012921621015 | https://help.figma.com/hc/en-us/articles/22012921621015 | Guide to inspecting (upd 2026-10-08) | Figma Help Center | updated 2026-10-08 | yes | A66 |
| HC:23870272542231 | https://help.figma.com/hc/en-us/articles/23870272542231 | Use AI tools in Figma Design (upd 2026-10-08) | Figma Help Center | updated 2026-10-08 | yes | context only (read, not cited per row) |
| HC:23918228264855 | https://help.figma.com/hc/en-us/articles/23918228264855 | Dev Mode ready for dev view (upd 2026-08-26) | Figma Help Center | updated 2026-08-26 | yes | A4, A69, F1-handoff, W10 |
| HC:23920389749655 | https://help.figma.com/hc/en-us/articles/23920389749655 | Code Connect (upd 2026-10-05) | Figma Help Center | updated 2026-10-05 | yes | A70, B-CodeConnect, S4-trends, W11 |
| HC:23955143044247 | https://help.figma.com/hc/en-us/articles/23955143044247 | Use First Draft with Figma AI (upd 2026-10-04) | Figma Help Center | updated 2026-10-04 | yes | context only (read, not cited per row) |
| HC:24004711129879 | https://help.figma.com/hc/en-us/articles/24004711129879 | Rename layers with AI (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A11 |
| HC:26620239826199 | https://help.figma.com/hc/en-us/articles/26620239826199 | Layers 101: Explore layer types (upd 2026-10-07) | Figma Help Center | updated 2026-10-07 | yes | A1, A2, A3, A10 |
| HC:26781702258583 | https://help.figma.com/hc/en-us/articles/26781702258583 | Dev Mode statuses and notifications (upd 2026-09-17) | Figma Help Center | updated 2026-09-17 | yes | A69, F1-handoff, W10 |
| HC:27882809912471 | https://help.figma.com/hc/en-us/articles/27882809912471 | Variables in Dev Mode (upd 2026-08-25) | Figma Help Center | updated 2026-08-25 | yes | A42 |
| HC:31242838116119 | https://help.figma.com/hc/en-us/articles/31242838116119 | Customize a text style for multiple breakpoints (upd 2026-09-16) | Figma Help Center | updated 2026-09-16 | yes | A21, A47 |
| HC:31289464393751 | https://help.figma.com/hc/en-us/articles/31289464393751 | Use the horizontal and vertical flows in auto layout (upd 2026-10-07) | Figma Help Center | updated 2026-10-07 | yes | A15 |
| HC:31289469907863 | https://help.figma.com/hc/en-us/articles/31289469907863 | Use the grid auto layout flow (upd 2026-10-04) | Figma Help Center | updated 2026-10-04 | yes | A19, A20, W8 |
| HC:31304412302231 | https://help.figma.com/hc/en-us/articles/31304412302231 | Explore Figma Make (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | S4-make |
| HC:31441443713047 | https://help.figma.com/hc/en-us/articles/31441443713047 | Combine vertical, horizontal, and grid auto layout flows (upd 2026-10-03) | Figma Help Center | updated 2026-10-03 | yes | A20 |
| HC:31616030150167 | https://help.figma.com/hc/en-us/articles/31616030150167 | Use patterns as a fill or stroke (upd 2026-08-24) | Figma Help Center | updated 2026-08-24 | yes | A10, A54 |
| HC:32596943880599 | https://help.figma.com/hc/en-us/articles/32596943880599 | Edit a code layer (upd 2025-09-18) | Figma Help Center | updated 2025-09-18 | yes | context only (read, not cited per row) |
| HC:34208860210199 | https://help.figma.com/hc/en-us/articles/34208860210199 | Use gradients as a fill or stroke (upd 2026-09-07) | Figma Help Center | updated 2026-09-07 | yes | A54 |
| HC:35280968300439 | https://help.figma.com/hc/en-us/articles/35280968300439 | Figma MCP collection: What is the Figma MCP server? (upd 2026-10-04) | Figma Help Center | updated 2026-10-04 | yes | A72 |
| HC:35498295267991 | https://help.figma.com/hc/en-us/articles/35498295267991 | Figma MCP collection: Improve code generation with Figma?s Code Connect UI (upd 2026-08-03) | Figma Help Center | updated 2026-08-03 | yes | context only (read, not cited per row) |
| HC:35794667554839 | https://help.figma.com/hc/en-us/articles/35794667554839 | What's new from Schema 2025 (upd 2026-09-09) | Figma Help Center | updated 2026-09-09 | yes | A31, A38, A70, A72, A-sum2, S4-make, W9, W11 |
| HC:360025508373 | https://help.figma.com/hc/en-us/articles/360025508373 | Publish a library (upd 2026-09-15) | Figma Help Center | updated 2026-09-15 | yes | A35, A73 |
| HC:360038006754 | https://help.figma.com/hc/en-us/articles/360038006754 | View a file's version history (upd 2026-10-01) | Figma Help Center | updated 2026-10-01 | yes | A74 |
| HC:360038665754 | https://help.figma.com/hc/en-us/articles/360038665754 | Detach an instance from the component (upd 2026-09-19) | Figma Help Center | updated 2026-09-19 | yes | A33 |
| HC:360039150413 | https://help.figma.com/hc/en-us/articles/360039150413 | Swap components and instances (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A33 |
| HC:360039238353 | https://help.figma.com/hc/en-us/articles/360039238353 | View and explore library analytics (upd 2026-08-27) | Figma Help Center | updated 2026-08-27 | yes | A73 |
| HC:360039238753 | https://help.figma.com/hc/en-us/articles/360039238753 | Guide to styles in Figma (upd 2026-09-30) | Figma Help Center | updated 2026-09-30 | yes | A46, A48, A49 |
| HC:360039818734 | https://help.figma.com/hc/en-us/articles/360039818734 | Prototype scroll and overflow behavior (upd 2026-10-01) | Figma Help Center | updated 2026-10-01 | yes | A63 |
| HC:360039818874 | https://help.figma.com/hc/en-us/articles/360039818874 | Smart animate layers between frames (upd 2026-10-07) | Figma Help Center | updated 2026-10-07 | yes | A61 |
| HC:360039823894 | https://help.figma.com/hc/en-us/articles/360039823894 | Create and manage prototype flows (upd 2026-10-07) | Figma Help Center | updated 2026-10-07 | yes | A57 |
| HC:360039825314 | https://help.figma.com/hc/en-us/articles/360039825314 | Guide to comments in Figma (upd 2026-08-31) | Figma Help Center | updated 2026-08-31 | yes | A76 |
| HC:360039956634 | https://help.figma.com/hc/en-us/articles/360039956634 | Explore text properties (upd 2026-10-07) | Figma Help Center | updated 2026-10-07 | yes | A9, A51 |
| HC:360039956914 | https://help.figma.com/hc/en-us/articles/360039956914 | Adjust alignment, rotation, position, and dimensions (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A13 |
| HC:360039956974 | https://help.figma.com/hc/en-us/articles/360039956974 | Measure distances between layers (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A67 |
| HC:360039956994 | https://help.figma.com/hc/en-us/articles/360039956994 | Missing font alert in Figma Design (upd 2026-10-02) | Figma Help Center | updated 2026-10-02 | yes | A52 |
| HC:360039957034 | https://help.figma.com/hc/en-us/articles/360039957034 | Create and apply text styles (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A47 |
| HC:360039957534 | https://help.figma.com/hc/en-us/articles/360039957534 | Boolean operations (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A6 |
| HC:360039957734 | https://help.figma.com/hc/en-us/articles/360039957734 | Apply constraints to define how layers resize (upd 2026-10-07) | Figma Help Center | updated 2026-10-07 | yes | A17, A18, A21 |
| HC:360039957934 | https://help.figma.com/hc/en-us/articles/360039957934 | Combine layout guides and constraints (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A18 |
| HC:360039958934 | https://help.figma.com/hc/en-us/articles/360039958934 | Rename Layers (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A11 |
| HC:360040035834 | https://help.figma.com/hc/en-us/articles/360040035834 | Prototype triggers (upd 2026-09-28) | Figma Help Center | updated 2026-09-28 | yes | A58 |
| HC:360040035874 | https://help.figma.com/hc/en-us/articles/360040035874 | Prototype actions (upd 2026-09-23) | Figma Help Center | updated 2026-09-23 | yes | A59 |
| HC:360040314193 | https://help.figma.com/hc/en-us/articles/360040314193 | Guide to prototyping in Figma (upd 2026-09-29) | Figma Help Center | updated 2026-09-29 | yes | A57 |
| HC:360040321093 | https://help.figma.com/hc/en-us/articles/360040321093 | View prototypes on a mobile device (upd 2026-09-27) | Figma Help Center | updated 2026-09-27 | yes | A64 |
| HC:360040328273 | https://help.figma.com/hc/en-us/articles/360040328273 | Compare Figma plans and features ? Figma Learn - Help Center | Figma Help Center | n/d | yes | A38, W1 |
| HC:360040450133 | https://help.figma.com/hc/en-us/articles/360040450133 | Shape tools (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A8 |
| HC:360040450213 | https://help.figma.com/hc/en-us/articles/360040450213 | Vector networks (upd 2026-10-07) | Figma Help Center | updated 2026-10-07 | yes | A5 |
| HC:360040450253 | https://help.figma.com/hc/en-us/articles/360040450253 | Masks (upd 2026-10-04) | Figma Help Center | updated 2026-10-04 | yes | A7 |
| HC:360040450513 | https://help.figma.com/hc/en-us/articles/360040450513 | Create layout guides (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A19 |
| HC:360040451373 | https://help.figma.com/hc/en-us/articles/360040451373 | Guide to auto layout in Figma (upd 2026-10-07) | Figma Help Center | updated 2026-10-07 | yes | A14, A16, A17 |
| HC:360040451453 | https://help.figma.com/hc/en-us/articles/360040451453 | Scale layers while maintaining proportions (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A13, A22 |
| HC:360040522373 | https://help.figma.com/hc/en-us/articles/360040522373 | Prototype animations (upd 2026-09-30) | Figma Help Center | updated 2026-09-30 | yes | A60 |
| HC:360040667874 | https://help.figma.com/hc/en-us/articles/360040667874 | Apply blend modes to layers, fills, and effects (upd 2026-09-10) | Figma Help Center | updated 2026-09-10 | yes | A12 |
| HC:360041003774 | https://help.figma.com/hc/en-us/articles/360041003774 | Update fills using the color picker (upd 2026-08-25) | Figma Help Center | updated 2026-08-25 | yes | A-sum2, W2 |
| HC:360041051154 | https://help.figma.com/hc/en-us/articles/360041051154 | Guide to libraries in Figma (upd 2026-10-04) | Figma Help Center | updated 2026-10-04 | yes | A35, A73 |
| HC:360041098433 | https://help.figma.com/hc/en-us/articles/360041098433 | Adjust the properties of an image (upd 2026-09-28) | Figma Help Center | updated 2026-09-28 | yes | A10, A55 |
| HC:360041308034 | https://help.figma.com/hc/en-us/articles/360041308034 | Browse and apply fonts (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A52 |
| HC:360041488473 | https://help.figma.com/hc/en-us/articles/360041488473 | Apply effects to layers (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A53, W8 |
| HC:360041596573 | https://help.figma.com/hc/en-us/articles/360041596573 | Lock and unlock layers (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A12 |
| HC:360047239073 | https://help.figma.com/hc/en-us/articles/360047239073 | Convert text to vector paths (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A9 |
| HC:360049283914 | https://help.figma.com/hc/en-us/articles/360049283914 | Apply and adjust stroke properties (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A54 |
| HC:360050986854 | https://help.figma.com/hc/en-us/articles/360050986854 | Adjust corner radius and smoothing (upd 2026-08-19) | Figma Help Center | updated 2026-08-19 | yes | A8 |
| HC:360061175334 | https://help.figma.com/hc/en-us/articles/360061175334 | Create interactive components with variants (upd 2026-09-19) | Figma Help Center | updated 2026-09-19 | yes | A26, A34 |
| HC:360063144053 | https://help.figma.com/hc/en-us/articles/360063144053 | Guide to branching (upd 2026-10-07) | Figma Help Center | updated 2026-10-07 | yes | A75 |
| HC:36346281624471 | https://help.figma.com/hc/en-us/articles/36346281624471 | Extend a variable collection (upd 2026-09-21) | Figma Help Center | updated 2026-09-21 | yes | A40, A50 |
| HC:37998629035799 | https://help.figma.com/hc/en-us/articles/37998629035799 | Work with the Figma agent in design files (upd 2026-10-08) | Figma Help Center | updated 2026-10-08 | yes | S4-figma-agent |
| HC:38231200344599 | https://help.figma.com/hc/en-us/articles/38231200344599 | Create and use slots to build flexible components in Figma Design (upd 2026-10-05) | Figma Help Center | updated 2026-10-05 | yes | A31, W8 |
| HC:38607529833751 | https://help.figma.com/hc/en-us/articles/38607529833751 | Migrate a library to using slots (upd 2026-09-29) | Figma Help Center | updated 2026-09-29 | yes | A31 |
| HC:38741465279895 | https://help.figma.com/hc/en-us/articles/38741465279895 | The difference between slots, instance swaps, and variants (upd 2026-10-02) | Figma Help Center | updated 2026-10-02 | yes | A31 |
| HC:38978644498199 | https://help.figma.com/hc/en-us/articles/38978644498199 | AI workflows collection: Refine your components and variables for the Figma agent (upd 2026-10-05) | Figma Help Center | updated 2026-10-05 | yes | context only (read, not cited per row) |
| HC:39287396773399 | https://help.figma.com/hc/en-us/articles/39287396773399 | Use skills with the Figma MCP server (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A72, S4-figma-agent |
| HC:39592284074263 | https://help.figma.com/hc/en-us/articles/39592284074263 | Check designs in Figma (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A-sum2, B-DesignLint, B-Figma-AI-lint (not in note), S4-trends, W2 |
| HC:39635555294743 | https://help.figma.com/hc/en-us/articles/39635555294743 | Components collection: Components fundamentals (upd 2026-10-07) | Figma Help Center | updated 2026-10-07 | yes | A33 |
| HC:39636407507735 | https://help.figma.com/hc/en-us/articles/39636407507735 | Components collection: Component property fundamentals (upd 2026-10-04) | Figma Help Center | updated 2026-10-04 | yes | A27-A30 |
| HC:39719619313047 | https://help.figma.com/hc/en-us/articles/39719619313047 | Components collection: Overview (upd 2026-10-08) | Figma Help Center | updated 2026-10-08 | yes | A24 |
| HC:39747190144023 | https://help.figma.com/hc/en-us/articles/39747190144023 | Components collection: Interactive components fundamentals (upd 2026-09-09) | Figma Help Center | updated 2026-09-09 | yes | A34 |
| HC:40283639496599 | https://help.figma.com/hc/en-us/articles/40283639496599 | Create and manage custom skills in Figma (upd 2026-10-07) | Figma Help Center | updated 2026-10-07 | yes | S4-figma-agent |
| HC:41159752541719 | https://help.figma.com/hc/en-us/articles/41159752541719 | AI workflows collection: Get sharper feedback (upd 2026-10-05) | Figma Help Center | updated 2026-10-05 | yes | context only (read, not cited per row) |
| HC:41175721167767 | https://help.figma.com/hc/en-us/articles/41175721167767 | Find and use shaders (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A53 |
| HC:41274629073303 | https://help.figma.com/hc/en-us/articles/41274629073303 | Explore Figma Motion (upd 2026-10-07) | Figma Help Center | updated 2026-10-07 | yes | A65 |
| HC:43028920030743 | https://help.figma.com/hc/en-us/articles/43028920030743 | Generate plugins with the Figma agent (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A77 |
| HC:4404856784663 | https://help.figma.com/hc/en-us/articles/4404856784663 | Swap libraries (upd 2026-09-13) | Figma Help Center | updated 2026-09-13 | yes | A35, A73 |
| HC:4913951097367 | https://help.figma.com/hc/en-us/articles/4913951097367 | Use OpenType features (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A51 |
| HC:5576781786647 | https://help.figma.com/hc/en-us/articles/5576781786647 | Change themes in Figma (upd 2026-09-30) | Figma Help Center | updated 2026-09-30 | yes | context only (read, not cited per row) |
| HC:5579474826519 | https://help.figma.com/hc/en-us/articles/5579474826519 | Explore component properties (upd 2026-09-29) | Figma Help Center | updated 2026-09-29 | yes | A25, A27-A30 |
| HC:5579502031511 | https://help.figma.com/hc/en-us/articles/5579502031511 | Use variable fonts (upd 2026-09-07) | Figma Help Center | updated 2026-09-07 | yes | A51 |
| HC:5691414603543 | https://help.figma.com/hc/en-us/articles/5691414603543 | Request a branch review (upd 2026-10-02) | Figma Help Center | updated 2026-10-02 | yes | A75 |
| HC:7810391964695 | https://help.figma.com/hc/en-us/articles/7810391964695 | Accessible prototypes in Figma (upd 2026-08-27) | Figma Help Center | updated 2026-08-27 | yes | A64, A-sum2 |
| HC:7938814091287 | https://help.figma.com/hc/en-us/articles/7938814091287 | Add descriptions to styles, components, and variables (upd 2026-07-17) | Figma Help Center | updated 2026-07-17 | yes | A32 |
| HC:8883757553943 | https://help.figma.com/hc/en-us/articles/8883757553943 | Edit instances with component properties (upd 2026-09-03) | Figma Help Center | updated 2026-09-03 | yes | A33 |
| HC:9771500257687 | https://help.figma.com/hc/en-us/articles/9771500257687 | Organize your canvas with sections (upd 2026-10-06) | Figma Help Center | updated 2026-10-06 | yes | A4 |
| HIG:accessibility | https://developer.apple.com/tutorials/data/design/human-interface-guidelines/accessibility.json | Accessibility | Apple | n/d | yes | F1b-wcag3, F1b-targets |
| HIG:color | https://developer.apple.com/tutorials/data/design/human-interface-guidelines/color.json | Color | Apple | n/d | yes | F1b-systems |
| HIG:designing-for-games | https://developer.apple.com/tutorials/data/design/human-interface-guidelines/designing-for-games.json | Designing for games | Apple | n/d | yes | F2-hud |
| HIG:designing-for-visionos | https://developer.apple.com/tutorials/data/design/human-interface-guidelines/designing-for-visionos.json | Designing for visionOS | Apple | n/d | yes | context only (read, not cited per row) |
| HIG:game-controls | https://developer.apple.com/tutorials/data/design/human-interface-guidelines/game-controls.json | Game controls | Apple | n/d | yes | F2-hud |
| HIG:going-full-screen | https://developer.apple.com/tutorials/data/design/human-interface-guidelines/going-full-screen.json | Going full screen | Apple | n/d | yes | F2-cert |
| HIG:inclusion | https://developer.apple.com/tutorials/data/design/human-interface-guidelines/inclusion.json | Inclusion | Apple | n/d | yes | F1b-systems |
| HIG:layout | https://developer.apple.com/tutorials/data/design/human-interface-guidelines/layout.json | Layout | Apple | n/d | yes | F1b-systems |
| HIG:typography | https://developer.apple.com/tutorials/data/design/human-interface-guidelines/typography.json | Typography | Apple | n/d | yes | F1b-systems |
| NNG:ai-design-tools-not-ready | https://www.nngroup.com/articles/ai-design-tools-not-ready/ | Status Update: AI UX-Design Tools Are Not Ready for Primetime - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | n/d | yes | S4-nng |
| NNG:ai-design-tools-update-2 | https://www.nngroup.com/articles/ai-design-tools-update-2/ | AI Design Tools Are Marginally Better: Status Update - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | 2025-05-09 | yes | S4-nng |
| NNG:ai-ux-debt | https://www.nngroup.com/articles/ai-ux-debt/ | The Custodial Era of UX: Cleaning Up After AI - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | 2026-08-28 | yes | S4-nng |
| NNG:card-sorting-definition | https://www.nngroup.com/articles/card-sorting-definition/ | Card Sorting: Uncover Users' Mental Models - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | n/d | yes | F1-ia |
| NNG:cognitive-walkthroughs | https://www.nngroup.com/articles/cognitive-walkthroughs/ | Evaluate Interface Learnability with Cognitive Walkthroughs - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | n/d | yes | F1-usability-QA |
| NNG:design-critiques | https://www.nngroup.com/articles/design-critiques/ | Design Critiques: Encourage a Positive Culture to Improve Products - NN/GNielsen Norman GroupNielsen Norman Gr | Nielsen Norman Group | n/d | yes | F1-usability-QA |
| NNG:design-ops-study-guide | https://www.nngroup.com/articles/design-ops-study-guide/ | DesignOps: Study Guide - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | n/d | yes | F1-handoff |
| NNG:design-system-enforcer | https://www.nngroup.com/articles/design-system-enforcer/ | Your Design System Needs an Enforcer - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | 2026-02-06 | yes | F1-handoff, S4-nng |
| NNG:design-system-maturity | https://www.nngroup.com/articles/design-system-maturity/ | Design-System Maturity: A 6-Dimension Framework - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | n/d | yes | F1-ui-design |
| NNG:design-systems-vs-style-guides | https://www.nngroup.com/articles/design-systems-vs-style-guides/ | Design Systems vs. Style Guides - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | n/d | yes | F1-ui-design |
| NNG:designops-team-structures | https://www.nngroup.com/articles/designops-team-structures/ | 5 DesignOps Team Structures - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | n/d | yes | F1-handoff |
| NNG:generative-ui | https://www.nngroup.com/articles/generative-ui/ | Generative UI and Outcome-Oriented Design - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | n/d | yes | S4-nng |
| NNG:genui-vs-vibe | https://www.nngroup.com/articles/genui-vs-vibe/ | GenUI vs. Vibe Coding: Who?s Designing? - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | 2026-03-27 | yes | S4-nng |
| NNG:how-many-test-users | https://www.nngroup.com/articles/how-many-test-users/ | How Many Test Users in a Usability Study? - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | n/d | yes | F1-usability-QA |
| NNG:how-to-conduct-a-heuristic-evaluation | https://www.nngroup.com/articles/how-to-conduct-a-heuristic-evaluation/ | Heuristic Evaluations: How to Conduct - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | n/d | yes | F1-usability-QA |
| NNG:journey-mapping-101 | https://www.nngroup.com/articles/journey-mapping-101/ | Journey Mapping 101 - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | n/d | yes | F1-research |
| NNG:promptframes | https://www.nngroup.com/articles/promptframes/ | Promptframes: Evolving the Wireframe for the Age of AI - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | n/d | yes | F1-wireframes |
| NNG:service-blueprints-definition | https://www.nngroup.com/articles/service-blueprints-definition/ | Service Blueprints: Definition - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | n/d | yes | F1-research |
| NNG:state-of-ux-2026 | https://www.nngroup.com/articles/state-of-ux-2026/ | State of UX in 2026 - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | 2026-01-16 | yes | S4-nng |
| NNG:success-rate-the-simplest-usability-metric | https://www.nngroup.com/articles/success-rate-the-simplest-usability-metric/ | Success Rate: The Simplest Usability Metric - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | n/d | yes | F1-usability-QA |
| NNG:ten-usability-heuristics | https://www.nngroup.com/articles/ten-usability-heuristics/ | 10 Usability Heuristics for User Interface Design - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | 1994 (reviewed 2024-01-30) | yes | F1-usability-QA |
| NNG:tree-testing | https://www.nngroup.com/articles/tree-testing/ | Tree Testing: Evaluate Menu Labels and Categories - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | n/d | yes | F1-ia |
| NNG:ux-maturity-model | https://www.nngroup.com/articles/ux-maturity-model/ | The 6 Levels of UX Maturity - NN/GNielsen Norman GroupNielsen Norman Group | Nielsen Norman Group | n/d | yes | F1-handoff |
| UNITY:6000.0/UIE-USS | https://docs.unity3d.com/6000.0/Documentation/Manual/UIE-USS.html | Unity - Manual: Style UI | Unity Technologies | n/d | yes | B-UnityUIToolkit |
| UNITY:6000.0/UIE-USS-CustomProperties | https://docs.unity3d.com/6000.0/Documentation/Manual/UIE-USS-CustomProperties.html | Unity - Manual: Create USS variables | Unity Technologies | n/d | yes | F2-unity-uitk |
| UNITY:6000.0/UIE-USS-Selectors | https://docs.unity3d.com/6000.0/Documentation/Manual/UIE-USS-Selectors.html | Unity - Manual: USS selectors | Unity Technologies | n/d | yes | F2-unity-uitk |
| UNITY:6000.0/UIE-UXML | https://docs.unity3d.com/6000.0/Documentation/Manual/UIE-UXML.html | Unity - Manual: Structure UI with UXML | Unity Technologies | n/d | yes | B-UnityUIToolkit |
| UNITY:6000.0/UIE-get-started-with-runtime-ui | https://docs.unity3d.com/6000.0/Documentation/Manual/UIE-get-started-with-runtime-ui.html | Unity - Manual: Get started with runtime UI | Unity Technologies | n/d | yes | F2-unity-uitk |
| UNITY:6000.0/UIE-tss | https://docs.unity3d.com/6000.0/Documentation/Manual/UIE-tss.html | Unity - Manual: Theme Style Sheet (TSS) | Unity Technologies | n/d | yes | B-UnityUIToolkit |
| UNITY:6000.7/UIE-USS-CustomProperties | https://docs.unity3d.com/6000.7/Documentation/Manual/UIE-USS-CustomProperties.html | Unity - Manual: Create USS variables | Unity Technologies | n/d | yes | B-UnityUIToolkit, F2-shared |
| UNITY:6000.7/UIE-USS-SupportedProperties | https://docs.unity3d.com/6000.7/Documentation/Manual/UIE-USS-SupportedProperties.html | Unity - Manual: USS common properties | Unity Technologies | n/d | yes | B-UnityUIToolkit |
| UNITY:6000.7/UIE-USS-WritingStyleSheets | https://docs.unity3d.com/6000.7/Documentation/Manual/UIE-USS-WritingStyleSheets.html | Unity - Manual: Best practices for USS | Unity Technologies | n/d | yes | B-UnityUIToolkit |
| UNITY:6000.7/UIE-tss | https://docs.unity3d.com/6000.7/Documentation/Manual/UIE-tss.html | Unity - Manual: Theme Style Sheet (TSS) | Unity Technologies | n/d | yes | B-UnityUIToolkit, F2-unity-tss |
| UNITY:pkg/inputsystem@1.14/manual/ActionBindings | https://docs.unity3d.com/Packages/com.unity.inputsystem@1.14/manual/ActionBindings.html | Input Bindings / Input System / 1.14.2 | Unity Technologies | n/d | yes | context only (read, not cited per row) |
| UNITY:pkg/inputsystem@1.14/manual/HowDoI | https://docs.unity3d.com/Packages/com.unity.inputsystem@1.14/manual/HowDoI.html | How do I?? / Input System / 1.14.2 | Unity Technologies | n/d | yes | F2-input |
| UNITY:pkg/inputsystem@1.14/manual/UISupport | https://docs.unity3d.com/Packages/com.unity.inputsystem@1.14/manual/UISupport.html | UI support / Input System / 1.14.2 | Unity Technologies | n/d | yes | context only (read, not cited per row) |
| UNITY:pkg/inputsystem@1.14/manual/index | https://docs.unity3d.com/Packages/com.unity.inputsystem@1.14/manual/index.html | Input System / Input System / 1.14.2 | Unity Technologies | n/d | yes | context only (read, not cited per row) |
| UNITY:pkg/inputsystem@1.18/manual/ActionBindings | https://docs.unity3d.com/Packages/com.unity.inputsystem@1.18/manual/ActionBindings.html | Input bindings / Input System / 1.18.0 | Unity Technologies | n/d | yes | F2-input |
| UNITY:pkg/inputsystem@1.18/manual/UISupport | https://docs.unity3d.com/Packages/com.unity.inputsystem@1.18/manual/UISupport.html | UI support / Input System / 1.18.0 | Unity Technologies | n/d | yes | F2-input |
| UNITY:pkg/inputsystem@1.18/manual/index | https://docs.unity3d.com/Packages/com.unity.inputsystem@1.18/manual/index.html | Input System / Input System / 1.18.0 | Unity Technologies | n/d | yes | F2-input |
| W3C:TR/WCAG22 | https://www.w3.org/TR/WCAG22/ | Web Content Accessibility Guidelines (WCAG) 2.2 | W3C | 2024-12-12 (REC) | yes | F1b-wcag |
| W3C:TR/wcag-3.0 | https://www.w3.org/TR/wcag-3.0/ | W3C Accessibility Guidelines (WCAG) 3.0 | W3C | 2026-09-10 (WD) | yes | F1b-wcag3 |
| W3C:WAI/GL/task-forces/silver/wiki/Visual_Contrast_of_Text_Subgroup | https://www.w3.org/WAI/GL/task-forces/silver/wiki/Visual_Contrast_of_Text_Subgroup | Visual Contrast of Text Subgroup - Silver | W3C | n/d | yes | F1b-wcag3 |
| W3C:WAI/WCAG22/Understanding/contrast-minimum.html | https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html | Understanding Success Criterion 1.4.3: Contrast (Minimum) / WAI / W3CW3C homepageWeb Accessibility Initiative  | W3C | n/d | yes | F1b-wcag |
| W3C:WAI/WCAG22/Understanding/focus-appearance.html | https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html | Understanding Success Criterion 2.4.13: Focus Appearance / WAI / W3CW3C homepageWeb Accessibility Initiative ( | W3C | n/d | yes | F1b-wcag |
| W3C:WAI/WCAG22/Understanding/target-size-minimum.html | https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html | Understanding Success Criterion 2.5.8: Target Size (Minimum) / WAI / W3CW3C homepageWeb Accessibility Initiati | W3C | n/d | yes | F1b-wcag, F1b-targets |
| W3C:WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html | https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html | Understanding Success Criterion 2.3.1: Three Flashes or Below Threshold / WAI / W3CW3C homepageWeb Accessibili | W3C | n/d | yes | F1b-wcag, F2-feedback |
| W3C:WAI/standards-guidelines/wcag | https://www.w3.org/WAI/standards-guidelines/wcag/ | WCAG 2 Overview / Web Accessibility Initiative (WAI) / W3CW3C homepageWeb Accessibility Initiative (WAI) homep | W3C | n/d | yes | F1b-wcag |
| W3C:WAI/standards-guidelines/wcag/new-in-22 | https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/ | What's New in WCAG 2.2 / Web Accessibility Initiative (WAI) / W3CW3C homepageWeb Accessibility Initiative (WAI | W3C | n/d | yes | F1b-wcag |
| XAG:guidelines | https://learn.microsoft.com/en-us/gaming/accessibility/guidelines | Xbox Accessibility Guidelines - Microsoft Game Dev / Microsoft Learn | Microsoft | v3.2 2023-06-08; page 2026-08-14 | yes | F2-gamea11y, W18 |
| XAG:home | https://learn.microsoft.com/en-us/gaming/accessibility/ | Xbox Accessibility - Microsoft Game Dev / Microsoft Learn | Microsoft | n/d | yes | F2-gamea11y |
| XAG:xbox-accessibility-guidelines/101 | https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/101 | Xbox Accessibility Guideline 101 - Microsoft Game Dev / Microsoft Learn | Microsoft | n/d | yes | F2-readability |
| XAG:xbox-accessibility-guidelines/102 | https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/102 | Xbox Accessibility Guideline 102 - Microsoft Game Dev / Microsoft Learn | Microsoft | n/d | yes | F2-readability |
| XAG:xbox-accessibility-guidelines/107 | https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/107 | Xbox Accessibility Guideline 107 - Microsoft Game Dev / Microsoft Learn | Microsoft | n/d | yes | F2-input |
| XAG:xbox-accessibility-guidelines/112 | https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/112 | Xbox Accessibility Guideline 112 - Microsoft Game Dev / Microsoft Learn | Microsoft | n/d | yes | F2-menus |
| XAG:xbox-accessibility-guidelines/113 | https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/113 | Xbox Accessibility Guideline 113 - Microsoft Game Dev / Microsoft Learn | Microsoft | n/d | yes | F2-menus |
| XAG:xbox-accessibility-guidelines/114 | https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/114 | Xbox Accessibility Guideline 114 - Microsoft Game Dev / Microsoft Learn | Microsoft | n/d | yes | F2-menus |
| XAG:xbox-accessibility-guidelines/117 | https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/117 | Xbox Accessibility Guideline 117 - Microsoft Game Dev / Microsoft Learn | Microsoft | n/d | yes | F2-feedback |
| XAG:xbox-accessibility-guidelines/118 | https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/118 | Xbox Accessibility Guideline 118 - Microsoft Game Dev / Microsoft Learn | Microsoft | n/d | yes | F2-feedback |
| accessible:accessible-player-experiences | https://accessible.games/accessible-player-experiences/ | Accessible Player Experiences (APX) - Accessible Games | AbleGamers | n/d | yes | F2-remap, F2-ftue, F2-gamea11y |
| accessible:home | https://accessible.games/ | Home - Accessible Games | AbleGamers | n/d | yes | F2-gamea11y |
| api.crossref:works?query.bibliographic=The+Gamers+Brain+Hodent&rows=2&select=title,author,publisher,issued,DOI,ISBN | https://api.crossref.org/works?query.bibliographic=The+Gamers+Brain+Hodent&rows=2&select=title,author,publisher,issued,DOI,ISBN |  | n/d | n/d | yes | F2-hud |
| atlassian:contribution | https://atlassian.design/contribution | Overview - Contribution - Atlassian Design | Atlassian | n/d | yes | F1-handoff |
| atlassian:foundations/accessibility | https://atlassian.design/foundations/accessibility | Overview - Accessibility - Atlassian Design | Atlassian | n/d | yes | F1b-systems |
| atlassian:get-started | https://atlassian.design/get-started | Overview - Get started - Atlassian Design | Atlassian | n/d | yes | F1b-systems |
| atlassian:home | https://atlassian.design/ | Atlassian Design | Atlassian | n/d | yes | F1b-systems |
| atomicdesign.bradfrost:chapter-2 | https://atomicdesign.bradfrost.com/chapter-2/ | Atomic Design Methodology / Atomic Design by Brad Frost | Brad Frost | n/d | yes | F1-ui-design |
| builder:blog/visual-copilot | https://www.builder.io/blog/visual-copilot | Announcing Visual Copilot 1.0 | Builder.io | n/d | yes | B-Builder, S4-others |
| builder:c/docs/developers | https://www.builder.io/c/docs/developers | Builder Developer Docs | Builder.io | n/d | yes | B-Builder |
| carbondesignsystem:contributing/component-checklist | https://carbondesignsystem.com/contributing/component-checklist/ | Component checklist / Carbon Design SystemIBM logo | IBM Carbon | n/d | yes | F1-handoff |
| carbondesignsystem:contributing/component-lifecycle | https://carbondesignsystem.com/contributing/component-lifecycle/ | Overview / Carbon Design SystemIBM logo | IBM Carbon | n/d | yes | context only (read, not cited per row) |
| carbondesignsystem:contributing/get-started | https://carbondesignsystem.com/contributing/get-started/ | Overview / Carbon Design SystemIBM logo | IBM Carbon | n/d | yes | F1-handoff, S4-mcp-everywhere |
| carbondesignsystem:contributing/product-development-lifecycle | https://carbondesignsystem.com/contributing/product-development-lifecycle/ | Product Development Lifecycle / Carbon Design SystemIBM logo | IBM Carbon | 2026-10-01 | yes | F1-handoff |
| carbondesignsystem:elements/color/usage | https://carbondesignsystem.com/elements/color/usage/ | Color / Carbon Design Systeminfo iconIBM logo | IBM Carbon | n/d | yes | F1b-systems |
| celiahodent:home | https://www.celiahodent.com/ | Celia Hodent - Brains, UX, and Games! | Celia Hodent | n/d | yes | F2-hud |
| celiahodent:the-gamers-brain | https://www.celiahodent.com/the-gamers-brain/ | Gamer's Brain: Neuroscience, UX & Design by Celia Hodent | Celia Hodent | n/d | yes | F2-hud, F2-ftue |
| christenseninstitute:jobs-to-be-done | https://www.christenseninstitute.org/jobs-to-be-done/ | Jobs to Be Done Theory - Christensen InstituteSearchPublicationFormatFormatBlogFormatFormatBlogFormatFormatPub | Christensen Institute | n/d | yes | F1-research |
| chromatic:docs | https://www.chromatic.com/docs/ | Why Chromatic? ? Chromatic docsChromatic | Chromatic | n/d | yes | B-Chromatic |
| chromatic:docs/review | https://www.chromatic.com/docs/review/ | Review ? Chromatic docsChromatic | Chromatic | n/d | yes | B-Chromatic |
| crates:api/v1/crates/cosmic-text | https://crates.io/api/v1/crates/cosmic-text |  | crates.io API | n/d | yes | B-cosmic-text (added) |
| crates:api/v1/crates/parley | https://crates.io/api/v1/crates/parley |  | crates.io API | n/d | yes | B-parley (added) |
| crates:api/v1/crates/resvg | https://crates.io/api/v1/crates/resvg |  | crates.io API | n/d | yes | B-resvg (added) |
| crates:api/v1/crates/taffy | https://crates.io/api/v1/crates/taffy |  | crates.io API | n/d | yes | B-taffy |
| design.gs:home | https://design.gs.com/ | Home / Goldman Sachs | Goldman Sachs | n/d | yes | F1b-systems |
| designcouncil.org:our-resources/framework-for-innovation | https://www.designcouncil.org.uk/our-resources/framework-for-innovation/ | Framework for Innovation - Design Council | Design Council (UK) | n/d | yes | F1-wireframes, F1b-dd |
| designcouncil.org:our-resources/the-double-diamond | https://www.designcouncil.org.uk/our-resources/the-double-diamond/ | The Double Diamond - Design Council | Design Council (UK) | n/d | yes | F1b-dd |
| designsystem.digital:about | https://designsystem.digital.gov/about/ | About / U.S. Web Design System (USWDS)LockGithub logo | US Web Design System | n/d | yes | F1b-systems |
| designsystem.digital:home | https://designsystem.digital.gov/ | USWDS: The United States Web Design System / U.S. Web Design System (USWDS)LockGithub logo | US Web Design System | n/d | yes | F1b-systems |
| developer.android:design/ui/mobile | https://developer.android.com/design/ui/mobile | Mobile / UI Design / Android Developers | Google (Android) | n/d | yes | context only (read, not cited per row) |
| developer.android:develop/ui/compose/accessibility/api-defaults | https://developer.android.com/develop/ui/compose/accessibility/api-defaults | API defaults / Jetpack Compose / Android Developers | Google (Android) | n/d | yes | F1b-targets |
| developer.android:guide/topics/ui/accessibility/apps | https://developer.android.com/guide/topics/ui/accessibility/apps | Make apps more accessible / App quality / Android Developers | Google (Android) | n/d | yes | F1b-targets |
| developer.android:guide/topics/ui/accessibility/principles | https://developer.android.com/guide/topics/ui/accessibility/principles | Principles for improving app accessibility / App quality / Android Developers | Google (Android) | n/d | yes | context only (read, not cited per row) |
| developer.chrome:docs/lighthouse/accessibility/scoring | https://developer.chrome.com/docs/lighthouse/accessibility/scoring | Lighthouse accessibility score / Chrome for Developers | Google Chrome | n/d | yes | B-Lighthouse |
| developers.googleblog:en/stitch-a-new-way-to-design-uis | https://developers.googleblog.com/en/stitch-a-new-way-to-design-uis/ | From idea to app: Introducing Stitch, a new way to design UIs - Google Developers Blog | Google | 2025-05-20 | yes | S4-others |
| docs.excalidraw:docs/codebase/json-schema | https://docs.excalidraw.com/docs/codebase/json-schema | JSON Schema / Excalidraw developer docs | Excalidraw | n/d | yes | B-Excalidraw |
| docs.github:en/copilot/concepts/context/mcp | https://docs.github.com/en/copilot/concepts/context/mcp | About Model Context Protocol (MCP) - GitHub Docs | GitHub repo (README and/or API metadata) | n/d | yes | S4-mcp-everywhere |
| docs.lovable:introduction/welcome | https://docs.lovable.dev/introduction/welcome | Welcome to Lovable - Lovable Documentation | Lovable | n/d | yes | S4-others |
| docs.plasmic:learn | https://docs.plasmic.app/learn/ | Welcome to Plasmic / Learn Plasmic | Plasmic | n/d | yes | B-Plasmic, S4-mcp-everywhere |
| docs.tokens:home | https://docs.tokens.studio/ | Tokens Studio Plugin for Figma / Tokens Studio for Figma | Tokens Studio | n/d | yes | B-TokensStudio |
| docs.tokens:manage-settings/token-format | https://docs.tokens.studio/manage-settings/token-format | Token Format - W3C DTCG vs Legacy / Tokens Studio for Figma | Tokens Studio | n/d | yes | B-TokensStudio, W15 |
| docs:taffy/latest/taffy | https://docs.rs/taffy/latest/taffy/ | taffy - Rust | docs.rs | n/d | yes | B-taffy |
| docs:taffy/latest/taffy/tree/struct.TaffyTree.html | https://docs.rs/taffy/latest/taffy/tree/struct.TaffyTree.html | TaffyTree in taffy::tree - Rust | docs.rs | n/d | yes | B-taffy |
| ecfr:current/title-47/chapter-I/subchapter-B/part-14 | https://www.ecfr.gov/current/title-47/chapter-I/subchapter-B/part-14 | eCFR :: 47 CFR Part 14 -- Access to Advanced Communications Services and Equipment by People with Disabilities | US eCFR | n/d | yes | F2-gamea11y, W21 |
| federalregister:documents/2011/12/30/2011-31162/implementing-the-provisions-of-the-communications-act-of-1934-as-enacted-by-the-twenty-first-century | https://www.federalregister.gov/documents/2011/12/30/2011-31162/implementing-the-provisions-of-the-communications-act-of-1934-as-enacted-by-the-twenty-first-century | Federal Register :: Implementing the Provisions of the Communications Act of 1934, as Enacted by the Twenty-Fi | US Federal Register | n/d | yes | F2-gamea11y |
| figma:color-contrast-checker | https://www.figma.com/color-contrast-checker/ | Color Contrast Checker & Accessibility Checker / Figma | Figma | n/d | yes | A-sum2 |
| figma:release-notes | https://www.figma.com/release-notes/ | Figma product news and release notes | Figma | rolling (2026-09-30 latest seen) | yes | A15 |
| framer:developers | https://www.framer.com/developers/ | Framer Developers: APIs, React, plugins, and Fetch | Framer | n/d | yes | B-Framer |
| gamasutra:home | https://www.gamasutra.com/ | Game Industry News, Deep Dives, and Interviews / Game Developer | Game Developer | n/d | yes | context only (read, not cited per row) |
| gameaccessibilityguidelines:full-list | https://gameaccessibilityguidelines.com/full-list/ | Full list ? Game Accessibility Guidelines | Game Accessibility Guidelines | n/d | yes | F2-remap, F2-gamea11y |
| gameuidatabase:home | https://www.gameuidatabase.com/ | Game UI Database 2.0 / Welcome | Game UI Database | n/d | yes | F2-hud |
| gdcvault:browse/gdc-23/play/1028799 | https://www.gdcvault.com/browse/gdc-23/play/1028799 | GDC Vault - Implementing Accessibility Across a Studio: Year One | GDC Vault (Informa) | n/d | yes | context only (read, not cited per row) |
| gdcvault:browse/gdc-24 | https://www.gdcvault.com/browse/gdc-24 | GDC Vault | GDC Vault (Informa) | n/d | yes | context only (read, not cited per row) |
| getstark:home | https://www.getstark.co/ | Stark: The suite of integrated accessibility tools | Stark | n/d | yes | B-Stark |
| git.apcacontrast:documentation/APCA_in_a_Nutshell.html | https://git.apcacontrast.com/documentation/APCA_in_a_Nutshell.html | APCA in a Nutshell / APCA | Myndex (APCA) | n/d | yes | F1b-wcag3 |
| git.apcacontrast:documentation/WhyAPCA | https://git.apcacontrast.com/documentation/WhyAPCA | Why APCA as a New Contrast Method? / APCA | Myndex (APCA) | n/d | yes | F1b-wcag3 |
| github:dequelabs/axe-core/blob/develop/doc/rule-descriptions.md | https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md | axe-core/doc/rule-descriptions.md at develop ? dequelabs/axe-core ? GitHub | GitHub repo (README and/or API metadata) | n/d | yes | B-axe-core |
| govinfo:content/pkg/CFR-2023-title47-vol1/xml/CFR-2023-title47-vol1-part14.xml | https://www.govinfo.gov/content/pkg/CFR-2023-title47-vol1/xml/CFR-2023-title47-vol1-part14.xml | ACCESS TO ADVANCED COMMUNICATIONS SERVICES AND EQUIPMENT BY PEOPLE WITH DISABILITIES | US GPO | n/d | yes | F2-gamea11y |
| hbr:2016/09/know-your-customers-jobs-to-be-done | https://hbr.org/2016/09/know-your-customers-jobs-to-be-done | Know Your Customers? ?Jobs to Be Done?Harvard Business Review LogoHarvard Business Review LogoHarvard Business | Harvard Business Review | n/d | yes | F1-research |
| hell.meiert:core/pdf/sus.pdf | https://hell.meiert.org/core/pdf/sus.pdf |  | mirror of Brooke 1996 PDF | 1986/1996 | yes | F1-usability-QA |
| help.figma:api/v2/help_center/en-us/articles/360040328273.json | https://help.figma.com/api/v2/help_center/en-us/articles/360040328273.json |  | Figma Help Center | n/d | yes | context only (read, not cited per row) |
| help.penpot:mcp | https://help.penpot.app/mcp/ | Penpot MCP server | Penpot | n/d | yes | B-Penpot, S4-mcp-everywhere |
| help.penpot:technical-guide/developer/data-model | https://help.penpot.app/technical-guide/developer/data-model/ | 3.02. Data model | Penpot | n/d | yes | B-Penpot |
| help.penpot:user-guide/design-systems/design-tokens | https://help.penpot.app/user-guide/design-systems/design-tokens/ | Design Tokens | Penpot | n/d | yes | B-Penpot, S4-trends |
| inclusive-components:a-theme-switcher | https://inclusive-components.design/a-theme-switcher/ | A Theme Switcher | Heydon Pickering | n/d | yes | F1-ui-design |
| inclusive-components:home | https://inclusive-components.design/ | Inclusive Components | Heydon Pickering | n/d | yes | F1-ui-design |
| inclusive-components:menus-menu-buttons | https://inclusive-components.design/menus-menu-buttons/ | Menus & Menu Buttons | Heydon Pickering | n/d | yes | F1-ui-design |
| inclusive-components:tooltips-toggletips | https://inclusive-components.design/tooltips-toggletips/ | Tooltips & Toggletips | Heydon Pickering | n/d | yes | F1-ui-design |
| law.cornell:cfr/text/47/part-14 | https://www.law.cornell.edu/cfr/text/47/part-14 | 47 CFR Part 14 - ACCESS TO ADVANCED COMMUNICATIONS SERVICES AND EQUIPMENT BY PEOPLE WITH DISABILITIES / Electr | Cornell LII | n/d | yes | F2-gamea11y |
| maze:resources/user-research-report | https://maze.co/resources/user-research-report/ | The Future of User Research Report 2026 / Maze | Maze | 2026 | yes | S4-surveys |
| measuringu:sus | https://measuringu.com/sus/ | Measuring Usability with the System Usability Scale (SUS) ? MeasuringUAccessibility ToolsHigh ContrastNegative | MeasuringU | n/d | yes | F1-usability-QA |
| modelcontextprotocol:docs/getting-started/intro | https://modelcontextprotocol.io/docs/getting-started/intro | What is the Model Context Protocol (MCP)? - Model Context Protocol | Model Context Protocol | n/d | yes | S4-mcp-everywhere |
| modelcontextprotocol:specification/2025-06-18 | https://modelcontextprotocol.io/specification/2025-06-18 | Specification - Model Context Protocol | Model Context Protocol | n/d | yes | S4-mcp-everywhere |
| pa11y:home | https://pa11y.org/ | Pa11y | Pa11y | n/d | yes | B-pa11y |
| partner.steamgames:doc/steamdeck/compat | https://partner.steamgames.com/doc/steamdeck/compat | Steam Deck and Steam Machine Compatibility Review (Steamworks Documentation) | Valve | n/d | yes | F2-input, F2-readability, F2-cert |
| playstation:en-us/accessibility | https://www.playstation.com/en-us/accessibility/ | Accessibility features on PS5 and PS4 / PlayStation (US) Sony Interactive Entertainment | Sony Interactive Entertainment | n/d | yes | F2-gamea11y |
| playwright:docs/aria-snapshots | https://playwright.dev/docs/aria-snapshots | Snapshot testing / Playwright | Microsoft Playwright | n/d | yes | B-Playwright |
| playwright:docs/test-snapshots | https://playwright.dev/docs/test-snapshots | Visual comparisons / Playwright | Microsoft Playwright | n/d | yes | B-Playwright |
| polaris-react.shopify:contributing | https://polaris-react.shopify.com/contributing | Polaris references | Shopify | n/d | yes | context only (read, not cited per row) |
| polaris.shopify:home | https://polaris.shopify.com/ | Polaris references | Shopify | n/d | yes | context only (read, not cited per row) |
| primer:home | https://primer.style/ | Primer | GitHub Primer | n/d | yes | F1b-systems |
| raw.githubusercontent:Shopify/polaris/main/README.md | https://raw.githubusercontent.com/Shopify/polaris/main/README.md |  | GitHub raw file | n/d | yes | F1-handoff, W22 |
| raw.githubusercontent:material-components/material-web/main/docs/theming/README.md | https://raw.githubusercontent.com/material-components/material-web/main/docs/theming/README.md |  | GitHub raw file | n/d | yes | context only (read, not cited per row) |
| raw.githubusercontent:material-components/material-web/main/docs/theming/color.md | https://raw.githubusercontent.com/material-components/material-web/main/docs/theming/color.md |  | GitHub raw file | n/d | yes | F1b-targets |
| raw.githubusercontent:tldraw/tldraw/main/LICENSE.md | https://raw.githubusercontent.com/tldraw/tldraw/main/LICENSE.md |  | GitHub raw file | n/d | yes | B-tldraw, W13 |
| research:pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications | https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/ | Measuring the User Experience on a Large Scale: User-Centered Metrics for Web Applications | Google Research | n/d | yes | F1-post-launch |
| shopify:docs/api/polaris | https://shopify.dev/docs/api/polaris |  | Shopify | n/d | yes | F1-handoff |
| smashingmagazine:design-systems-book | https://www.smashingmagazine.com/design-systems-book/ | Meet ?Design Systems?, A New Smashing Book ? Smashing MagazineClear SearchBack to top | Smashing Magazine | n/d | yes | F1-ui-design |
| spectrum.adobe:home | https://spectrum.adobe.com/ | Start with Spectrum | Adobe | n/d | yes | F1b-systems |
| static.googleusercontent:media/research.google.com/en//pubs/archive/36299.pdf | https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/36299.pdf | HEART paper PDF Rodden Hutchinson Fu CHI 2010 Measuring the User Experience on a Large Scale | Google (Rodden, Hutchinson, Fu) | 2010 (CHI) | yes | F1-post-launch, W19 |
| storybook.js:docs/ai | https://storybook.js.org/docs/ai | Using Storybook with AI / Storybook docsChromatic | Storybook | n/d | yes | B-Storybook |
| storybook.js:docs/ai/best-practices | https://storybook.js.org/docs/ai/best-practices | Best practices for using Storybook with AI / Storybook docsChromatic | Storybook | n/d | yes | B-Storybook |
| storybook.js:docs/ai/mcp/overview | https://storybook.js.org/docs/ai/mcp/overview | MCP server / Storybook docsChromatic | Storybook | n/d | yes | B-Storybook, S4-mcp-everywhere, S4-trends |
| storybook.js:docs/api/csf | https://storybook.js.org/docs/api/csf | Component Story Format (CSF) / Storybook docsChromatic | Storybook | n/d | yes | B-Storybook |
| storybook.js:docs/writing-tests | https://storybook.js.org/docs/writing-tests | How to test UIs with Storybook / Storybook docsChromatic | Storybook | n/d | yes | B-Storybook |
| storybook.js:docs/writing-tests/accessibility-testing | https://storybook.js.org/docs/writing-tests/accessibility-testing | Accessibility tests / Storybook docsChromatic | Storybook | n/d | yes | B-Storybook |
| storybook.js:docs/writing-tests/integrations/vitest-addon | https://storybook.js.org/docs/writing-tests/integrations/vitest-addon | Vitest addon / Storybook docsChromatic | Storybook | n/d | yes | B-Storybook |
| storybook.js:docs/writing-tests/visual-testing | https://storybook.js.org/docs/writing-tests/visual-testing | Visual tests / Storybook docsChromatic | Storybook | n/d | yes | B-Storybook |
| strategyn:jobs-to-be-done | https://strategyn.com/jobs-to-be-done/ | Jobs to Be Done (JTBD): The Original Framework by Tony Ulwick | Strategyn (Ulwick) | n/d | yes | F1-research |
| styledictionary:info/dtcg | https://styledictionary.com/info/dtcg/ | Design Tokens Community Group / Style Dictionary | Style Dictionary | n/d | yes | B-StyleDictionary, W14 |
| support.google:accessibility/android/answer/7101858 | https://support.google.com/accessibility/android/answer/7101858 | Touch target size - Android Accessibility Help | Google | n/d | yes | F1b-targets |
| survey.stackoverflow:2025/ai | https://survey.stackoverflow.co/2025/ai | AI / 2025 Stack Overflow Developer SurveyAll RespondentsProfessional DevelopersLearning to CodeEarly Career De | Stack Overflow | 2025 | yes | S4-surveys |
| tailwindcss:docs/adding-custom-styles | https://tailwindcss.com/docs/adding-custom-styles | Adding custom styles - Core concepts - Tailwind CSS | Tailwind Labs | n/d | yes | B-TailwindTheme (added) |
| tailwindcss:docs/theme | https://tailwindcss.com/docs/theme | Theme variables - Core concepts - Tailwind CSS | Tailwind Labs | n/d | yes | B-TailwindTheme (added), F2-shared, S4-trends |
| theesa:policy-advocacy/accessibility | https://www.theesa.com/policy-advocacy/accessibility/ |  | Entertainment Software Association | n/d | yes | F2-gamea11y |
| tldraw:community/license | https://tldraw.dev/community/license | License ? tldraw Docs | tldraw | n/d | yes | B-tldraw |
| tldraw:docs/shapes | https://tldraw.dev/docs/shapes | Shapes ? tldraw Docs | tldraw | n/d | yes | B-tldraw |
| ui.shadcn:docs/mcp | https://ui.shadcn.com/docs/mcp | MCP Server - shadcn/ui | shadcn/ui | n/d | yes | B-shadcn (added), S4-mcp-everywhere |
| ui.shadcn:docs/registry | https://ui.shadcn.com/docs/registry | Introduction - shadcn/ui | shadcn/ui | n/d | yes | B-shadcn (added), S4-trends |
| usability:how-to-and-tools/methods/system-usability-scale.html | https://www.usability.gov/how-to-and-tools/methods/system-usability-scale.html | Usability / Digital.govLock | Digital.gov / usability.gov | n/d | yes | F1-usability-QA |
| uxpin:merge | https://www.uxpin.com/merge | UXPin Merge / Design with React components. Visually. | UXPin | n/d | yes | S4-others |
| v0:docs | https://v0.app/docs | What is v0? / v0 Docs | Vercel | n/d | yes | S4-others |

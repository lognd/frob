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
crunk-testbed README, frob-v2 crates/crunk*, docs/crunk/*, notes/crunk.md.
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

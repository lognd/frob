# crunk: an agent-first design tool where every interface is batch-checkable (D108-D117)

Status: accepted direction, owner request 2026-10-08: "crunk needs to
mirror modern graphic design tools like Figma, but in a manner easy to
use for an agent, and every design/user interface needs to be
batch-checkable and lintable"; "not just Figma, the modern UX/UI/GX
design cycle". Evidence: notes/research/crunk-design-2026-10-08.md
(Figma inventory of 78 capabilities, 30 comparable tools and specs, the
Python crunk port matrix, the hullbreach consumer, the design cycle and
game UX). The owner delegated the decisions; they are recorded here and
in the README decision log.

Scope of this file: what crunk models, its files, verbs, check tiers,
lint families, game and Unity support, the design-cycle artifacts, and
the build order. products.md section 1 (crunk judges the front-end
design system; it never knows what a ticket is) and boundaries.md stay
authoritative for placement. Parsing of TS/TSX/CSS/HTML and USS is a
gob fact (language-engines.md, D96); crunk holds design judgements.

## 1. Principle (D108)

Mirror Figma's concepts, not its canvas. Everything a designer or an
agent edits is a text file that diffs, merges, validates against a JSON
Schema and addresses every node by a stable id; everything visual is
derived (rendered, solved, exported). A design is therefore a program
crunk can check in batch, like code: `crunk check` over the whole
`design/` tree and every implementation file (TSX, CSS, USS, generated
C#) in one run, with JSON output, stable exit codes and per-file cache.

Consequences:

- One source of truth per fact. Tokens, component specs, screens,
  flows, copy and platform profiles live under `design/`; Tailwind
  themes, CSS variables, USS sheets, C# token classes and Figma
  variables are generated and checked for drift (TOKENS001, EXPORT).
- Design-versus-build is a lint, not a review step: the implementation
  (TSX className, CSS, USS, prefab generator inputs) is checked against
  the design files, so drift such as hullbreach's HUD `ThrustRed`
  (#e63326) against the web `stress-fail` (#ff4d4f), which the config
  claims mirror each other, fires a finding.
- Agents edit by patch, never by pixel: structured edits return the
  diff and the findings for the touched nodes only.
- Visual tools stay usable: Figma and Penpot are import/export targets
  (variables, components as data), not the source of truth.

Non-goals (v1): vector path editing, boolean operations, a plugin
ecosystem of its own, real-time multiplayer, prototype variable logic,
a visual canvas editor. A human who wants a canvas uses Figma or Penpot
through `crunk import` and `crunk export`; a stateless GUI over the
verbs is products.md's later GUI work.

## 2. Source files (D109, D110)

All under `design/` (root configurable in `crunk.toml`, which keeps
policy: scales, tolerances, rule configuration). Every file kind has a
JSON Schema generated through gob-config (the ConfigTable derive), so
editors and agents validate before crunk runs.

| Kind | File | Holds | Figma analogue |
|---|---|---|---|
| tokens | `design/tokens/*.toml` | primitives, semantic and component tiers; aliases; composites (typography, shadow, border, transition); modes (light/dark, density, brand, platform, colour-blind safe); scopes (which property kinds a token may bind) | variables, collections, modes, styles |
| components | `design/components/<name>.component.toml` | anatomy (a scene subtree), props (bool, enum/variant, text, slot, instance swap), the variant matrix, states (default, hover, focus-visible, active, disabled, loading, error, empty), token bindings, an a11y contract (role, accessible-name source, keyboard map, minimum target), responsive rules, the code mapping (`code = { path, export }`), status | components, variants, component properties, Code Connect |
| scenes | `design/scenes/*.scene.html` | layout in a restricted HTML and CSS dialect (section 3) | frames, auto layout, constraints |
| screens | `design/screens/<id>.screen.toml` | today's `[[screen]]` model extended: entry route or scene root, states with overrides and mock or session ids, platforms, expected landmarks and headings, copy keys, status and content hash | pages, frames marked ready |
| flows | `design/flows/*.flow.toml` | nodes are `screen:state`, edges are trigger (click, key, `gamepad:south`, timeout) plus action; transitions reference motion tokens | prototype connections, flows |
| content | `design/content/*.toml` | copy keys with length budgets, tone rules, glossary, locales; scenes reference keys, never literals | text, (no real analogue) |
| profiles | `design/profiles.toml` | platform profiles: web viewports and breakpoints, mobile targets (44/48 px), TV or console (safe area, minimum text at distance, focus rules), game HUD (reference resolution, scaler match) | device frames |
| fonts | `design/fonts.toml` | font files by hash with licence ids; metric-compatible substitutes recorded when a face cannot be bundled | fonts |

Tokens (D109): authored in a TOML dialect (comments, terse values such
as `ink = "#e6e8ef"`, existing `crunk.toml` `[palette]`/`[scales]`
tables keep working as a view), compiled to the W3C Design Tokens
Community Group format (DTCG 2025.10 with the resolver module for
modes) as the canonical interchange. `crunk import dtcg` and `crunk
export dtcg` round-trip; `crunk export` also targets CSS custom
properties, the Tailwind theme, USS custom properties, a C# token class
(engine-free floats so a Unity assembly with no engine reference can
use it) and Figma-variables JSON. One token source serves the web
platform and the Unity game.

## 3. Scenes and the layout engine (D111, D113)

The scene format is a restricted HTML and CSS dialect: elements carry
a stable `data-id`, component instances are tags (`<Button
variant="primary">`), styles reference tokens only (`var(--space-4)`),
and the allowed CSS is the subset the layout solver implements
(block, flex, grid, absolute positioning, gap, padding, min and max
sizes, aspect ratio). Reasons: agents are fluent in HTML and CSS; the
browser renders it unchanged; it maps directly to Tailwind classes and
to UXML/USS; gob already parses HTML and CSS (D96). The dialect is the
restriction: an unsupported property is a finding (SCENE001), not a
silent approximation. UXML is an export target, not a source.

Layout (D113): two engines with a parity test.

- T1 solve: taffy (block, flexbox, grid) in-process, with text measured
  by a shaping library over the bundled fonts (cosmic-text by default;
  the first scene ticket spikes cosmic-text against parley and records
  the measurement). Output is a layout-solve JSON: boxes, text runs and
  overflow, tab and focus order, computed token bindings. It is fast,
  deterministic and needs no browser, so most layout lints run in batch
  in CI on every PR.
- T2/T3 render: Playwright through gob-exec (the gallery renderer the
  Python crunk already has: fonts ready, animations off, fixed clock,
  network idle, settle) for pixels, rendered contrast over images, live
  DOM accessibility (axe-core) and real focus behaviour.
- Parity: CI renders a corpus of scenes both ways and fails when the
  solver and the browser disagree by more than a configured number of
  pixels, which also measures how far T1 can be trusted.
- Baselines: layout-solve JSON baselines are committed (small, diffable);
  PNGs stay CI artifacts by default, as in the Python crunk.

## 4. Check tiers (D112)

Every lint declares the minimum tier that can decide it; `crunk check`
runs up to a configured tier (`--tier`, default T1 locally and in PR
CI) and reports anything above it as not run, never as clean
(universal-model.md: undecidable is Unresolved, not green).

| Tier | Needs | Decides |
|---|---|---|
| T0 static | the files | tokens, schema, naming, references, contrast of declared pairs, component and state coverage, copy budgets, flow graphs, design-vs-build literal drift |
| T1 solve | layout solver and fonts | overflow, overlap, clipping, safe areas, touch target size, focus order, responsive breakpoints, text fit per locale |
| T2 render | pixels | visual regression, rendered contrast over images and gradients, flashing frames |
| T3 live | a browser or the Unity editor | axe-core, real keyboard and gamepad focus, real fonts |
| T4 human | a person | taste, soul, usability observation; a person's ack is recorded in `crunk.lock` against the subject's content hash (section 4.1); a subject changed since its ack is Advisory in check and CI and blocks only the release gate |

### 4.1 Human review lock (owner requirement 2026-10-08)

The human tier is enforced the way `frob ack` enforces symbol review
(D28), with the same shared crate (gob-lock) and a new entry kind, not a
second mechanism. `crunk.lock` (TOML, sorted, byte-stable) holds one
`[[review]]` entry per human-reviewed subject: a screen state on a
platform, a component variant, a flow, a copy deck, a token mode.

- Subject digest: a hash over everything that can change what a person
  would see: the subject's source files, the resolved tokens it uses (per
  mode), the fonts manifest entries, the scene and component specs it
  instantiates, and, when the subject has a T2 render, the render digest
  under the pinned renderer version. The inputs are listed in the entry
  so a reviewer sees what the ack covered.
- Entry fields: subject id, digest, verdict (`approved`, `rejected`
  with a reason), reviewer identity, timestamp, optional note, and the
  render artifact reference that was looked at.
- HUMAN001 (for subjects marked `review = "human"` in their spec or by
  `[review]` policy in `crunk.toml`): the live digest differs from the
  acked one, or no ack exists. The finding names the
  inputs that changed, so a token tweak that touches forty screens
  lists forty subjects with the token as the cause. HUMAN002: a
  `rejected` verdict is still current.
- Severity by gate (owner decision 2026-10-08): HUMAN001 and HUMAN002
  are Advisory in `crunk check`, `frob check`, local runs and CI, so
  design work and agents are never blocked waiting for a person; they
  are Error at release. The mechanism is general, not crunk-specific: a
  rule may declare a `release_severity` (rules.md registry field) that
  applies only when the release gate evaluates it. `frob release status`
  gains a readiness item "release-tier findings clean" that runs the
  products' checks with release severities (siblings through
  `--gate release`), and `frob release cut` refuses while any is open,
  like every other readiness item (`--override --reason` records an
  event). A project without frob gets the same gate from `crunk check
  --gate release` in its release job.
- `crunk ack SUBJECT... --verdict approved|rejected [--note]` shows the
  diff of inputs (and the before and after renders when available) and
  writes the entries; `crunk review` lists the stale subjects in a
  queue, which is the gallery triage view of the Python crunk.
- A person, not an agent: an ack is recorded with the git identity of
  the commit that adds it, and `[review] reviewers` lists who may ack.
  `crunk ack` refuses without an interactive terminal unless
  `--non-interactive` is given, and in that case the entry is marked as
  such. The enforceable guarantee is `[review] require_signed = true`:
  HUMAN001 then also fires for an entry whose introducing commit is not
  signed by a key listed for a reviewer (gob-trust holds the keys).
  Agents may prepare the review queue and the renders, never the ack;
  the agent briefs and the PROC rules say so.
- Mass changes stay reviewable: a re-ack may cover many subjects at once
  (`crunk ack --all-changed-by TOKEN`), each still recorded with its own
  digest.

## 5. Verbs (D114)

All verbs have `--json` with the shared envelope and stable exit codes.

| Group | Verbs |
|---|---|
| author | `crunk new component|screen|flow|token NAME [--from ...]`, `crunk edit FILE --patch PATCH.json` (RFC 6902 operations addressed by stable id, validated against the schema, returns the diff and the findings of the touched nodes), `crunk rename ID NEW` (rewrites every reference), `crunk extract-token LITERAL` (promote a literal to a token and rewrite its uses) |
| render | `crunk render` (screen, state, platform or component, variant; `--engine solve|browser`) writes PNG and layout-solve JSON; `crunk snapshot [--update]`; `crunk diff --visual|--layout|--tokens|--a11y A B` |
| check | `crunk check [--family F] [--tier T] [--changed]`, `crunk fix [--dry-run]` on gob-fix with tiered applicability, `crunk explain RULE`, `crunk measure A B`, `crunk query` |
| interop | `crunk export css|tailwind|uss|csharp|dtcg|figma-variables`, `crunk import dtcg|figma-variables|penpot|css`, `crunk serve` (MCP: read tools for design context, variables and search, and the patch tool; same generated-from-verb-metadata mechanism as frob serve, ~MQ1NM4Q) |
| review | `crunk review` (the queue of subjects whose digest moved since their ack), `crunk ack SUBJECT... --verdict` (person only, section 4.1) |
| process | `crunk status ID ready` (refuses unless the screen's lints are green at its tier; records the content hash so a later change marks it `changed`), `crunk gallery ...` (enumerate, render, triage, check; the Python gallery, ported) |

## 6. Lint families (D115)

Family names and the tier of each proposal; the full proposed catalogue
(about 120 ids, with the 30 Python ids marked) is section E3 of the
research note. Rule ids follow rules.md and are authored per
rule-authoring.md (D107); new families ship as GRL where GRL can express
them (D76).

| Family | Examples | Tiers |
|---|---|---|
| TOKEN, TOKENS | schema, alias cycles, unused, naming tiers, mode completeness, scope violation, near-duplicates, deprecated, generated output drift | T0 |
| COLOR, CONTRAST | literal colour not a token, palette distance, WCAG and APCA contrast for declared pairs in every mode, colour-only meaning | T0, T2 |
| TYPE, SPACE, RADIUS, SIZE, LAYER, ORG | scale steps, type ramp, z-index layers, organisation (the Python families, ported) | T0 |
| LAYOUT, RESP | overflow, overlap, clipping, safe area, target size, breakpoint coverage | T1 |
| COMP, STATE | every variant combination renders, required states present, props bound to tokens, code mapping exists and matches the exported props | T0, T1 |
| A11Y | names, roles, landmarks, heading order, focus order and visibility, keyboard map, target size, reduced-motion twin | T0, T1, T3 |
| MOTION | durations and easings from tokens, reduced-motion alternative, flash threshold | T0, T2 |
| CONTENT, I18N | literal copy in scenes, length budgets, pseudo-locale expansion fits, RTL mirroring | T0, T1 |
| VIS, THEME, EXPORT | visual regression thresholds, theme completeness, export parity across targets (Tailwind against USS against C#) | T0, T2 |
| GX | gamepad focus graph complete (every focusable reachable, no traps, default selection), glyph per device family, remap conflicts, HUD in safe area at every profile, minimum text at distance, colour-blind mode coverage, subtitle size, hold alternatives | T0, T1 |
| UX, PROC | design-cycle traceability (section 8), ready gate, flows without dead ends or missing error paths | T0 |
| web pack (D88/D89) | A11Y, SEO, LAUNCH, WEBPERF over markup and assets (crunk-web, existing tickets) | T0 |

## 7. Game UI and Unity (D116)

- Unity UI Toolkit: USS, UXML and TSS are parsed in gob as a CSS dialect
  and a markup language (the `style` and `markup` capabilities of D96),
  so every token and declaration rule applies to USS unchanged; USS-only
  properties (`-unity-font`, `-unity-text-align`) are known to the
  dialect. `crunk export uss` writes the token sheet.
- uGUI prefabs (machine-written YAML with GUIDs) are not a source. When
  a project generates its prefabs from code (hullbreach's
  `HudPrefabBuilder.cs`), crunk checks the generator's inputs through the
  C# adapter (literals must be generated token constants) and audits the
  prefab YAML read-only for colour and font-size literals.
- New game UI should use UI Toolkit; crunk's game profile and GX family
  apply to both.
- The gamepad focus graph comes from scenes and flows (directional
  neighbours, default selection, wrap), so GX checks run at T0/T1
  without the editor; T3 runs the Unity editor in batch mode through the
  unity evidence provider (dotnet-unity.md).
- Colour-blind support is a token mode (`stress.default`,
  `stress.cb-safe`), so every colour and contrast lint runs in both.

## 8. The design cycle as checkable artifacts (D117)

crunk stays ticket-agnostic (products.md); frob tracks the work. What
crunk adds is that each phase of the UX/UI/GX cycle can leave a text
artifact whose mechanical properties are lintable, all optional and
enabled per project:

| Phase | Artifact | Mechanical checks |
|---|---|---|
| research | `design/research/*.md` with front matter, `personas/*.toml`, `journeys/*.toml` | schema; every persona and journey cites evidence; every screen cites a persona or job; stale research flagged |
| information architecture | `design/ia/sitemap.toml`, `content-model.toml` | every route has a screen and every screen a route (checked against gob-frameworks routes in code); depth; label uniqueness; reachability from home |
| flows and wireframes | flow files, scenes at `fidelity = "wire"` | reachability, dead ends, error paths, every decision branch present; wire scenes use no brand tokens |
| UI design | tokens, components, screens, content | sections 2 to 6 |
| prototyping | flows with triggers, motion tokens | targets exist, timing within token bounds, reduced-motion twins; flows replay headlessly at T3 and assert the reached state |
| usability and design QA | `design/qa/heuristics/*.toml` (Nielsen heuristics), `qa/walkthrough/*.toml` | evidence present, every major finding has an owner reference, heuristic coverage per screen; design-vs-build parity (VIS) |
| handoff | `crunk status ready`, `design/review/*.toml` anchored comments | ready refuses with open blocking comments, stale exports, missing code mapping or red lints; a change after ready marks the screen changed |
| post-launch | `design/metrics/*.toml`, `experiments/*.toml` | every flow step has a defined analytics event; experiment variants exist as declared component variants; guardrail metrics declared; stale experiments flagged |
| game (GX) | `hud/*.toml`, `input.toml`, `ftue.toml`, `feedback.toml`, `gx-a11y.toml` keyed to Game Accessibility Guidelines items | HUD in safe area, input glyph and remap coverage, every mechanic has onboarding or an explicit none, feedback events with accessibility toggles, guideline coverage with evidence |

Human judgement (taste, usability sessions, playtests) is recorded as
acks in `crunk.lock` (section 4.1) that crunk checks for currency
against content hashes, never simulated.

## 9. Build order

Hullbreach is the first consumer (its platform runs the Python crunk in
CI today; its game shares a palette with the web that has drifted).

1. Parity with the Python crunk for hullbreach: crunk-ingest (CSS,
   JSX className, Tailwind), the token model and `crunk tokens` with
   exporters and TOKENS001, the rule registry, CONTRAST/COLOR/TYPE/
   SPACE/TW/BP/LAYER/ORG ports, `crunk check` end to end, `crunk fix`,
   the parity harness. Exit: hullbreach platform CI switches from
   `uv run crunk` to the Rust crunk with a reasoned divergence list.
2. DTCG and modes: the TOML dialect compiles to DTCG with the resolver;
   modes (dark, colour-blind safe); USS and C# exporters; EXPORT parity.
   Exit: one token source drives hullbreach web and the Unity HUD, and
   the ThrustRed drift fires until resolved.
3. Component and screen specs, content keys, `crunk new`, `edit
   --patch`, `rename`, `extract-token`, `crunk serve`; COMP, STATE,
   CONTENT lints at T0.
4. Scenes and the T1 solver (taffy plus the text spike), layout-solve
   JSON and baselines; LAYOUT, RESP, A11Y-T1, GX focus graph.
5. Render and gallery (Playwright), T2/T3 lints, the solver-browser
   parity test, visual regression.
6. GX pack and Unity UI Toolkit (USS/UXML in gob), uGUI audit; design
   cycle artifacts (section 8) as an opt-in pack.

Phase 1 is the existing epic ~X0SN72M; phases 2 to 6 are filed as
epics under it with this file as their design reference.

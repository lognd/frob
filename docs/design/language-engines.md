# Language engines: what lives in gob, what lives in a product (D96)

Status: current
Owner: gob
Decisions: D96
Audience: contributor

Provenance: accepted, coordinator decision 2026-10-06 under the owner's
delegation; owner prompt: "Make sure the language engines make sense
(for example, what from JSX/TSX goes in gob or crunk? Don't we need it
for grimble as well?). We want both universal capabilities and
whatnot." Extends code-model.md section 3, universal-model.md sections
4.4 and 5, and monorepo.md section 3; supersedes the crunk-local
placement of JSX extraction and framework discovery in notes/crunk.md
section 4.

## 1. The placement rule

One test decides every case:

- A fact about **what is written** (syntax, names, scopes, imports,
  calls, elements, attributes, style declarations, constant values,
  project and package layout, framework entry points) is a language or
  repository fact. It lives in `gob-*`, is answered through a
  capability with Must/May/Unknown honesty (universal-model.md 4.4),
  and is visible to every product and to GRL.
- A judgement about **what it means for one product's domain** (a
  ticket obligation, an architecture violation, a palette or spacing
  scale, a Tailwind utility's theme value, a WCAG contrast ratio) lives
  in that product's crates.

Corollaries:

1. No product crate parses a language or walks a syntax tree. A product
   that needs a new fact asks for a capability in gob.
2. A product vocabulary that is itself a small language used by only
   that product (Tailwind utility candidates, the crunk.toml spec, .grmb)
   stays in the product until a second product needs it; then it moves
   down without changing its API.
3. Every capability is reachable from GRL through the relation catalog
   (grl-spec.md section 6), so a rule in any product's pack uses the same
   words: an A11Y rule in crunk-web and an XSS rule in grimble-websec both
   say `element(.tag = "img")` and `attribute(.name = "alt")`.

## 2. Universal capabilities added by this decision

universal-model.md 4.4 lists the structural capabilities. Four more are
needed for web, UI and project facts. Each is an answer type and query
set in `gob-ir`, implemented per language by an adapter in
`gob-symbols` (or `gob-frameworks`, section 4), with a capability-matrix
cell `Implemented`, `NotApplicable(reason)` or `Gap(ticket)` per
language.

| Capability | What it answers | Lowering into U | Languages (first adapters, later ones) |
|---|---|---|---|
| `markup` | element tree: element (tag, kind intrinsic / component / unknown), attributes (name, value as a `const_value` answer, spread), children, text | JSX/HTML element = `apply(kind=element)`; a component tag (capitalised or member expression) has a `ref` head resolved through the scope graph, so component usage is a call edge for grimble; attributes are named args; a spread is an attribute set with status May | TSX, JSX, HTML; later Vue and Svelte templates (as `region` islands), Unity UXML, XAML, Razor |
| `style` | rules (selector), declarations (property, raw value, component values), at-rules, custom property definitions and `var()` references, layers | rule = `unit(kind=style-rule)`, declaration = `bind(kind=property)`, custom property = `unit(kind=custom-property)`, `var(--x)` = `ref` with status May (the cascade decides at runtime); SCSS variables and mixins are `phase` | CSS, SCSS, inline JSX `style={{...}}` objects, CSS-in-JS template literals as `region` islands tagged css; later Unity USS, Less |
| `const_value` | bounded static value of an expression: `Known(v)`, `OneOf(set)`, `Fragments(known parts, Unknown rest)`, `Unknown` | evaluates `lit`, `ref` to a const binding, concatenation, template literals, conditional and object/array literals within a step budget; anything else is Unknown | TS/JS first (className strings, style objects, route paths), then Python, Rust, C# |
| `project_model` | packages and their files, package dependencies, path aliases, entry files | packages are `unit(kind=package)`; aliases feed `imports` resolution | Cargo, pyproject, .sln/.csproj (~ECEBCQ1), package.json workspaces, tsconfig paths and baseUrl; later Unity .asmdef (~C8HB0GQ) |

`const_value` reaches beyond one file through an `ExternalRefs` hook
(~C2F4ZMQ): a name the scope graph cannot resolve is followed through
the module graph when it answers Must with one `const` unit, in that
file's own term, charging the same step budget; a reference cycle or an
exhausted budget leaves `Unknown` and the evaluation says which
(`Unresolved`), with the origin span of every constant consulted. A
call is read only when its callee is a class-name joiner (`clsx`,
`classnames`, or a repository function whose body calls one, such as a
`cn` wrapper; a `twMerge` wrapper is read as the plain join, a superset).

Class tokens are a derived query over `markup` and `const_value`, not a
capability of their own: `class_tokens(attr)` returns the Known tokens
of a `class`/`className` attribute (through `clsx`, `cn`,
`classnames` and template literals by name, May) and says Unknown for
the rest. crunk's Tailwind rules read them; grimble does not need them.

## 3. Placement of every web item

| Item | Layer | Crate | Consumers |
|---|---|---|---|
| TS, TSX, JS, JSX, CSS, SCSS, HTML grammars and comment scanners | language | gob-languages | all |
| TS/JS adapter: units, exports, imports (ESM, CJS, dynamic import as May), calls, tests (vitest, jest, playwright) | language | gob-symbols | frob (COV, AFFECT, touched tests), grimble (graph, layering) |
| CSS adapter: rules, declarations, custom properties, at-rules, waivers | language | gob-symbols | crunk, grimble (WEBPERF assets) |
| `markup`, `style`, `const_value` answer types and queries | model | gob-ir | all, through GRL |
| JSX `markup` and inline `style` lowering | language | gob-symbols | crunk (tokens, A11Y), grimble (WEBSEC sinks such as `dangerouslySetInnerHTML`, `href="javascript:"`, `target=_blank` without `rel`) |
| package.json workspaces, tsconfig paths | repository | gob-symbols (`project_model`) | all |
| Framework discovery and routes (react-router, Next.js app and pages dirs, later Express, FastAPI, ASP.NET) | repository | gob-frameworks (new, above gob-symbols) | crunk (pages for SEO, LAUNCH, gallery), grimble (ROUTE, WEBSEC authorization) |
| ProjectStyles, bucket and organization model | domain | crunk-ingest, a thin mapping from `style` and `markup` answers | crunk |
| CSS value math (colour, length, contrast, palette distance) | domain | crunk-values | crunk |
| Tailwind candidates and theme mapping, node runtime bridge | domain | crunk-tailwind | crunk |
| Token model and export | domain | crunk-tokens | crunk |

## 4. gob-frameworks

Frameworks are not languages, so their discovery does not belong in an
adapter, but the facts (this file is a page at `/settings`, this
function handles `POST /api/orders`) are repository facts both crunk
and grimble consume. `gob-frameworks` sits above `gob-symbols` and
below every product:

- `Framework` is an open inventory registry (like `Language`); a
  framework adapter declares detection (package.json dependency,
  config file, directory convention), searched per workspace member,
  never the repository root only (the v1 lesson ~5E0V6W3).
- Answers: `routes` (path pattern, method, handler unit, page
  component, layout chain, each with status), `entrypoints` (Q-table
  `entrypoints`), and per-framework conventions (Next.js `use client`
  boundaries as an attribute on the unit).
- The capability matrix gains framework rows, generated into the same
  languages page.
- Implemented in `crates/gob-frameworks` (~AVXTRHX): `detect` walks every
  `package.json`, `analyze` folds the TypeScript sources over the module
  graph and runs each detected framework. Route patterns use `:name`,
  `:name+` and `:name*`; a path that `const_value` cannot resolve gives
  a route with no pattern and status Unknown, a `OneOf` path or a
  conditional or mapped `<Route>` gives May. react-router reads route
  objects handed to `createBrowserRouter`-style calls (also through a
  named constant or an import, with `basename`) and `<Route>` elements;
  Next.js reads `app` and `pages` (also under `src/`).

## 5. Consequences

- Tickets ~17ZVW3R, ~6KKJF80, ~C2F4ZMQ and ~Z8V73JM (grammars, TS
  adapter, constant evaluation, CSS adapter) move from the crunk epic to
  the shared web-engine epic; their crate placement was already right.
- ~8JGRZY3 (crunk-ingest JSX style and className) is rescoped to a thin
  mapping over `markup`, `style` and `class_tokens`; the extraction
  itself is the gob work.
- ~XPMQ50D (crunk-adapters FrameworkAdapter) moves to gob-frameworks; the
  crunk-adapters crate is not created.
- The GRL relation catalog gains `element`, `attribute`, `style_rule`,
  `declaration`, `custom_property`, `route` and `package` kinds with
  their fields, each naming its query and the languages that answer it.
- Unity: UXML and USS ride on `markup` and `style` once the C#
  epic (~GJVPDC0) lands; no Unity-specific style engine is designed.
- The owner's platform repository (Python, TS/TSX, CSS, crunk.toml) is
  the first real consumer, so the web engine is scheduled before the
  crunk rule tickets that need it.

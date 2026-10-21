# crunk-web pack

The `crunk-web` std pack holds crunk's web markup and asset rules in GRL (design D89). It is
opt-in: the `[packs] crunk_web` switch is off by default, and `crunk_check::packs::PacksSwitch`
is read from `crunk.toml` by `crunk_spec` (`DesignSpec::packs`) and listed by `crunk rule catalog`.

## Families

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

Each family ships worked rules; more land under the same prefixes. WEBPERF1xx covers markup and
assets only (server-side WEBPERF lives in grimble-websec, 2xx). A file type with no adapter (for
example markdown) is reported NotApplicable by each rule's `notapplicable` example, never clean.

## Layout

- `packs/crunk-web/pack.toml`: the manifest (name, version, families, rule globs).
- `packs/crunk-web/rules/*.grl`, `rules/a11y/*.grl`, `rules/seo/*.grl` and `rules/webperf-assets/*.grl`: one rule per file, each with a firing, a clean and a
  not-applicable example. A rule without a firing and a clean example fails to compile (GRL011).

## Embedding and lock

`crates/crunk-check/src/packs.rs` embeds the manifest and rules with `include_str!`.
`packs::plans()` compiles them, `packs::catalog()` yields the `crunk rule catalog` rows
(pack, family, rule; empty when the switch is off), and `packs::locked(root)` returns the lock
entry after `verify_tree(root)` confirms the tree on disk equals the embedded sources. The lock
digest is the gob-packs tree digest of `packs/crunk-web`.

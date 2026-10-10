//! Tailwind config ingest: the project's theme as a flat `{name: value}` map, whatever the
//! Tailwind version.
//!
//! Two source shapes converge on one mapping, so rules never branch on version:
//!
//! - **Tailwind 3**: a JS or TS config's `theme` / `theme.extend`;
//! - **Tailwind 4**: the CSS-first `@theme` / `@theme inline` blocks, with `@config "x.js"`
//!   bridging back to a v3 config.
//!
//! The primary truth is the project's own Tailwind run through the node runtime
//! ([`crunk_tailwind::runtime`]): `resolveConfig` for v3 (presets, plugins, `require()`), the v4
//! design system for CSS-first. Without node, without an install, in static mode or when the
//! helper fails, the static readers ([`read_v3`], [`read_v4`]) take over: syntax-tree walks that
//! leave out, and report as unresolved, whatever they cannot prove. Nothing is guessed.
//!
//! A project with neither `[tailwind] config` nor `css_entry` ingests nothing and spawns nothing.
//!
//! # Known divergences from the Python crunk
//!
//! - Numeric theme values (`zIndex: { base: 0 }`) are kept as their text; Python dropped them.
//! - A spread of a same-file constant (`...base`) and a member access (`palette.brand`) are
//!   evaluated; Python dropped the spread.
//! - `[tailwind] config` naming a `.css` file is the v4 entry when `css_entry` is unset (Python
//!   passed it on as the entry too); the root-relative auto-detection of the entry is unchanged
//!   (`src/index.css`, `src/main.css`, ...), so an entry in a subdirectory (`web/src/index.css`)
//!   needs `[tailwind] css_entry`.
//! - Collisions with a Tailwind default key are facts of the result with their waivers
//!   ([`ThemeCollision`]); Python only logged a warning (v1 T-0179: it could not be silenced
//!   short of renaming every class).
//! - Relative imports other than `.json` (a `.ts` palette module) are not followed.

// frob:ticket 01M43ARZ3VCNDX20C9BZZCCYHY

mod collisions;
mod ingest;
mod v3;
mod v4;

pub use collisions::{COLLISION_RULE, ThemeCollision};
pub use ingest::{
    Engine, Source, TailwindTheme, Version, detect_version, ingest_tailwind, parse_tailwind_config,
    runtime_sources,
};
pub use v3::{Entry, V3Read, Val, read_v3};
pub use v4::{V4Read, read_v4, split_namespace};

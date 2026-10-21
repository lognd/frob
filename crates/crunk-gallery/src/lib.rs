//! The crunk gallery (opt-in): the screen approval pipeline's data side.
//!
//! The gallery is the Python crunk's `enumerate -> render -> triage -> check` pipeline. This crate
//! holds the parts that need no browser: the manifest (versions 1 to 3, each with a shipped JSON
//! Schema under `docs/schemas/`), the cell enumeration over `[[platform]]` and `[[screen]]`, the
//! rules GALLERY001 to GALLERY005 and the `check` report. Rendering goes through `gob-exec` ([`render`]); triage is a local contact sheet ([`triage`]).
//!
//! # Overview
//!
//! - [`manifest`]: [`manifest::parse`] validates a manifest against its version's schema, with a
//!   JSON-pointer location per error, and normalizes v1, v2 and v3 into one [`manifest::Manifest`].
//! - [`schema`]: the embedded schemas and [`schema::validate`].
//! - [`cells`]: [`cells::enumerate`] lists every `(screen, state, platform)` cell; [`cells::cells`]
//!   narrows that list with a [`cells::CellFilter`].
//! - [`rules`]: GALLERY001 to GALLERY004 over the cells and the manifest, GALLERY005 over the
//!   routes a router declares. GALLERY has its own dispatch (its input is a manifest, not a
//!   file), so these are plain functions rather than `#[rule]` declarations.
//! - [`render`]: [`render::render`] turns cells into hashed PNGs via Playwright (`web`) or the
//!   platform's own command (`command`), with a timeout per cell.
//! - [`report`]: [`report::check_report`] runs every rule and counts the result; the shape is
//!   `docs/schemas/crunk-gallery-check-v1.json`.
//! - [`triage`]: a blocking loopback HTTP contact sheet with keyboard verdicts, saved to the
//!   manifest; no async runtime.

// frob:ticket 01M43ATDG0RG5DP9PVFAKETJJH

pub mod cells;
pub mod manifest;
pub mod render;
pub mod report;
pub mod rules;
pub mod schema;
pub mod triage;

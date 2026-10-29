//! The generated artifacts: the JSON Schema of `crunk.toml` and its reference page.
//!
//! Both come from the `crunk` product of the [`gob_config`] registry: every table in
//! [`crate::table`] declares itself with `#[derive(ConfigTable)]`, so a new key needs no edit
//! here. `cargo dev gen` writes `docs/schemas/crunk.json` and `docs/crunk/config.md`.

// frob:ticket 01M43MPG53JR8TP0E15394FZ5T

use serde_json::Value;

/// The product name crunk's tables register under.
pub const PRODUCT: &str = "crunk";

/// Intro of the reference page: scope, error behavior and the path-base law.
const INTRO: &str = "Every table of `crunk.toml`. Unknown keys are errors that name the key, its line and the nearest valid key. Tables owned by shared crates (`[check]`, `[perf]`, ...) are documented in the frob config reference. The machine-readable form is `docs/schemas/crunk.json`.\n\nPath-base law: `[project] tokens_file` resolves against `css_root`; every other `*_file` key (`[tailwind] tokens_file`, `[tokens] json_file`) and `[tailwind] config` resolve against the project root.";

gob_config::inventory::submit! {
    gob_config::ProductEntry {
        product: PRODUCT,
        title: "crunk.toml",
        intro: INTRO,
        open_top_level: true,
        required_tables: &["project", "palette", "scales", "typography", "org"],
    }
}

/// The JSON Schema (draft 2020-12) of `crunk.toml`.
pub fn schema() -> Value {
    gob_config::product_config_schema(PRODUCT)
}

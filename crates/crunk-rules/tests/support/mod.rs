//! A throwaway crunk project for rule tests: the default preset (or a case's own `crunk.toml`),
//! the case file, an empty generated tokens sheet, and the real ingest over them.
//!
//! The case's `config=no-tokens` leaves the tokens sheet out, so the definition set is incomplete.

// frob:ticket 01M43ATB4X0B56W8T0G8MQFYVM

#![allow(
    dead_code,
    reason = "each test binary uses a different part of the support module"
)]

use std::path::Path;

use crunk_ingest::{ProjectStyles, ingest_tree};
use crunk_rules::CrunkHost;
use crunk_spec::DesignSpec;
use gob_cache::Cache;
use gob_rules::{Emitted, Finding, RepoRule, run_repo};
use gob_text::FileInterner;

/// The spec and ingested styles of one test project; keeps the temp directory alive.
pub struct Project {
    pub spec: DesignSpec,
    pub styles: ProjectStyles,
    _dir: tempfile::TempDir,
}

impl CrunkHost for Project {
    fn spec(&self) -> Option<&DesignSpec> {
        Some(&self.spec)
    }
    fn styles(&self) -> Option<&ProjectStyles> {
        Some(&self.styles)
    }
}

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

/// The default preset's `crunk.toml`, for tests that tweak a table.
pub const DEFAULT_SPEC: &str = include_str!("../../../crunk-spec/src/presets/default.toml");

/// Build a project holding `file` with `text` under the default preset.
pub fn project_with_spec(spec_text: &str, file: &str, text: &str) -> Project {
    build(spec_text.to_owned(), file, text, None)
}

/// Build a project holding `file` with `text`; `crunk.toml` as `file` replaces the preset.
pub fn project(file: &str, text: &str, config: Option<&str>) -> Project {
    let spec_text = if file == "crunk.toml" {
        text.to_owned()
    } else {
        DEFAULT_SPEC.to_owned()
    };
    build(spec_text, file, text, config)
}

fn build(mut spec_text: String, file: &str, text: &str, config: Option<&str>) -> Project {
    let dir = tempfile::tempdir().expect("tempdir");
    if [".tsx", ".jsx", ".ts"].iter().any(|e| file.ends_with(e)) {
        spec_text.push_str("\n[jsx]\nglobs = [\"src/**/*\"]\n");
    }
    write(dir.path(), "crunk.toml", &spec_text);
    if file != "crunk.toml" {
        write(dir.path(), file, text);
    }
    if config != Some("no-tokens") && file != "styles/tokens.css" {
        write(dir.path(), "styles/tokens.css", ":root {}\n");
    }
    let spec = crunk_spec::parse_spec(&spec_text, &dir.path().join("crunk.toml"), dir.path())
        .expect("spec parses");
    let styles = ingest_tree(&spec, &Cache::null()).expect("ingest").styles;
    Project {
        spec,
        styles,
        _dir: dir,
    }
}

/// Run the repo rule `R` over `host` and anchor the emissions the way the pipeline does.
pub fn run<R: RepoRule<Project> + Default>(host: &Project) -> Vec<Finding> {
    let emitted: Vec<Emitted> = run_repo::<R, Project>(&R::default(), host);
    let mut files = FileInterner::new();
    emitted
        .into_iter()
        .map(|e| e.into_located_finding(R::DEF, &mut files))
        .collect()
}

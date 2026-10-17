//! A throwaway crunk project for rule tests: the default preset (or a case's own `crunk.toml`),
//! the case file, an empty generated tokens sheet, and the real ingest over them.
//!
//! A case's `config=` is a comma-separated list of flags:
//! - `no-tokens` leaves the tokens sheet out, so the definition set is incomplete.
//! - `stale-tokens` supplies an expected tokens sheet that differs from the one on disk.
//! - `breakpoints` declares sm/md/lg (640/768/1024px) with a `base_required` list so BP rules apply.
//! - `theme-brand`, `theme-alpha`, `theme-unknown` add a Tailwind config whose `brand` colour maps
//!   to `var(--color-ink)`, to an `<alpha-value>` rgb triplet, or to the unexported `var(--color-nope)`.

// frob:ticket 01M43ATB4X0B56W8T0G8MQFYVM

#![allow(
    dead_code,
    reason = "each test binary uses a different part of the support module"
)]

use std::path::Path;

use crunk_ingest::TailwindTheme;
use crunk_ingest::{ProjectStyles, ingest_tree};
use crunk_rules::{CrunkHost, GeneratedFile};
use crunk_spec::DesignSpec;
use crunk_tailwind::runtime::Options;
use crunk_tokens::export::Target;
use gob_cache::Cache;
use gob_rules::{Emitted, Finding, RepoRule, run_repo};
use gob_text::FileInterner;

/// The spec and ingested styles of one test project; keeps the temp directory alive.
pub struct Project {
    pub spec: DesignSpec,
    pub styles: ProjectStyles,
    pub generated: Option<Vec<GeneratedFile>>,
    pub theme: Option<TailwindTheme>,
    _dir: tempfile::TempDir,
}

impl CrunkHost for Project {
    fn spec(&self) -> Option<&DesignSpec> {
        Some(&self.spec)
    }
    fn styles(&self) -> Option<&ProjectStyles> {
        Some(&self.styles)
    }
    fn generated_files(&self) -> Option<&[GeneratedFile]> {
        self.generated.as_deref()
    }
    fn tailwind_theme(&self) -> Option<&TailwindTheme> {
        self.theme.as_ref()
    }
}

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

/// What a project adds to the default preset: extra TOML, a Tailwind config body, tokens flags.
#[derive(Default)]
pub struct Setup<'a> {
    pub extra_toml: String,
    pub tailwind_config: Option<&'a str>,
    pub no_tokens: bool,
    pub stale_tokens: bool,
    /// Replaces the default preset as the base `crunk.toml` text.
    pub base_toml: Option<&'a str>,
}

/// The `Setup` a case's comma-separated `config=` flags describe.
pub fn setup(config: Option<&str>) -> Setup<'static> {
    let mut out = Setup::default();
    for flag in config.unwrap_or("").split(',').filter(|f| !f.is_empty()) {
        match flag {
            "no-tokens" => out.no_tokens = true,
            "stale-tokens" => out.stale_tokens = true,
            "breakpoints" => out.extra_toml.push_str(
                "\n[breakpoints]\nsm = 640\nmd = 768\nlg = 1024\nbase_required = [\"flex\", \"grid\", \"block\", \"hidden\", \"w-\", \"h-\"]\n",
            ),
            "theme-brand" => out.tailwind_config = Some(THEME_BRAND),
            "theme-alpha" => out.tailwind_config = Some(THEME_ALPHA),
            "theme-unknown" => out.tailwind_config = Some(THEME_UNKNOWN),
            other => panic!("unknown config flag `{other}`"),
        }
    }
    out
}

const THEME_BRAND: &str =
    "module.exports = { theme: { extend: { colors: { brand: \"var(--color-ink)\" } } } };\n";
const THEME_ALPHA: &str = "module.exports = { theme: { extend: { colors: { brand: \"rgb(var(--color-ink-rgb) / <alpha-value>)\" } } } };\n";
const THEME_UNKNOWN: &str =
    "module.exports = { theme: { extend: { colors: { brand: \"var(--color-nope)\" } } } };\n";

/// Build a project holding `file` with `text`; `crunk.toml` as `file` replaces the preset.
pub fn project(file: &str, text: &str, config: Option<&str>) -> Project {
    build(file, text, &setup(config))
}

/// Build a project holding `file` with `text` under an explicit `Setup`.
pub fn build(file: &str, text: &str, setup: &Setup<'_>) -> Project {
    let dir = tempfile::tempdir().expect("tempdir");
    let preset = crunk_spec::presets::preset("default").expect("default preset");
    let mut spec_text = if file == "crunk.toml" {
        text.to_owned()
    } else {
        setup.base_toml.unwrap_or(preset).to_owned()
    };
    if [".tsx", ".jsx", ".ts"].iter().any(|e| file.ends_with(e)) {
        spec_text.push_str("\n[jsx]\nglobs = [\"src/**/*\"]\n");
    }
    spec_text.push_str(&setup.extra_toml);
    if setup.tailwind_config.is_some() {
        spec_text.push_str("\n[tailwind]\nconfig = \"tailwind.config.js\"\n");
    }
    write(dir.path(), "crunk.toml", &spec_text);
    if file != "crunk.toml" {
        write(dir.path(), file, text);
    }
    if let Some(body) = setup.tailwind_config {
        write(dir.path(), "tailwind.config.js", body);
    }
    if !setup.no_tokens && file != "styles/tokens.css" {
        write(dir.path(), "styles/tokens.css", ":root {}\n");
    }
    let spec = crunk_spec::parse_spec(&spec_text, &dir.path().join("crunk.toml"), dir.path())
        .expect("spec parses");
    let dir_path = dir.path().to_path_buf();
    let styles = ingest_tree(&spec, &Cache::null()).expect("ingest").styles;
    let theme = setup.tailwind_config.and_then(|_| {
        crunk_ingest::ingest_tailwind(
            &spec,
            Options {
                static_mode: true,
                quiet_notice: true,
                ..Options::default()
            },
            Cache::null(),
        )
    });
    Project {
        spec,
        styles,
        theme,
        generated: setup.stale_tokens.then(|| {
            vec![GeneratedFile {
                target: Target::Css,
                path: dir_path.join("styles/tokens.css"),
                content: ":root { --a: 1; }\n".to_owned(),
            }]
        }),
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

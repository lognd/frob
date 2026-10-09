//! A throwaway crunk project for rule tests: the default preset (or a case's own `crunk.toml`),
//! the case file, an empty generated tokens sheet, and the real ingest over them.
//!
//! The case's `config=no-tokens` leaves the tokens sheet out, so the definition set is incomplete;
//! `config=breakpoints` adds a `[breakpoints]` table; `config=tw-theme-*` declares a Tailwind config and a stand-in theme; `config=tokens-current` writes the generated token
//! files the spec renders, so TOKENS001 finds no drift.

// frob:ticket 01M43ATB4X0B56W8T0G8MQFYVM

#![allow(
    dead_code,
    reason = "each test binary uses a different part of the support module"
)]

use std::path::Path;

use crunk_ingest::{ProjectStyles, ingest_tree};
use crunk_rules::CrunkHost;
use crunk_rules::tailwind::TailwindFacts;
use crunk_spec::DesignSpec;
use crunk_tailwind::runtime::{ClassDeclaration, ClassResult, ClassStatus};
use gob_cache::Cache;
use gob_rules::{Emitted, Finding, RepoRule, run_repo};
use gob_text::FileInterner;
use indexmap::IndexMap;

/// The spec and ingested styles of one test project; keeps the temp directory alive.
pub struct Project {
    pub spec: DesignSpec,
    pub styles: ProjectStyles,
    pub tailwind: TailwindFacts,
    _dir: tempfile::TempDir,
}

impl CrunkHost for Project {
    fn spec(&self) -> Option<&DesignSpec> {
        Some(&self.spec)
    }
    fn styles(&self) -> Option<&ProjectStyles> {
        Some(&self.styles)
    }
    fn tailwind(&self) -> Option<&TailwindFacts> {
        Some(&self.tailwind)
    }
}

/// What the stand-in compiler knows about one utility: the declarations Tailwind v3 would emit for
/// the shapes the tests use (arbitrary values, a few default scale keys and colours), or `None`
/// for anything else, which reads as "not Tailwind syntax". No node is involved.
fn stub_compile(name: &str) -> Option<Vec<(&'static str, String)>> {
    let stem = name.rsplit_once('/').map_or(name, |(stem, _)| stem);
    if let Some((prefix, value)) = stem.strip_suffix(']').and_then(|b| b.split_once("-[")) {
        let value = value.replace('_', " ");
        let value = value
            .strip_prefix("color:")
            .or_else(|| value.strip_prefix("length:"))
            .unwrap_or(&value)
            .to_owned();
        let prop = match prefix {
            "p" => "padding",
            "m" => "margin",
            "gap" => "gap",
            "inset" => "inset",
            "rounded" => "border-radius",
            "w" => "width",
            "h" => "height",
            "min-w" => "min-width",
            "min-h" => "min-height",
            "max-h" => "max-height",
            "z" | "-z" => "z-index",
            "bg" => "background-color",
            "text" if value.starts_with('#') => "color",
            "text" => "font-size",
            _ => return None,
        };
        return Some(vec![(prop, value)]);
    }
    let (prefix, key) = stem.split_once('-')?;
    let spacing = |prop: &'static str| -> Option<Vec<(&'static str, String)>> {
        let n: f64 = key.parse().ok()?;
        let value = if n == 0.0 {
            "0px".to_owned()
        } else {
            format!("{}rem", n / 4.0)
        };
        Some(vec![(prop, value)])
    };
    match prefix {
        "p" => spacing("padding"),
        "m" => spacing("margin"),
        "inset" => spacing("inset"),
        "z" => Some(vec![("z-index", key.to_owned())]),
        "rounded" if key == "lg" => Some(vec![("border-radius", "0.5rem".to_owned())]),
        "bg" | "text" => {
            let hex = crunk_tailwind::defaults::V3_COLOR_HEXES
                .iter()
                .find_map(|(n, hex)| (*n == key).then_some(*hex))?;
            let prop = if prefix == "bg" {
                "background-color"
            } else {
                "color"
            };
            Some(vec![(prop, hex.to_owned())])
        }
        _ => None,
    }
}

/// The facts for `styles`: every utility compiled by [`stub_compile`], and the theme a case selects
/// with `config=tw-theme-broken` (`brand` maps to an undefined token), `tw-theme-plain` (`brand` is a
/// literal colour) or `tw-theme-alpha` (`brand` carries an `<alpha-value>` placeholder).
fn tailwind_facts(
    spec: &DesignSpec,
    styles: &ProjectStyles,
    config: Option<&str>,
) -> TailwindFacts {
    let mut theme = IndexMap::new();
    match config {
        Some("tw-theme-broken") => {
            theme.insert("brand".to_owned(), "var(--color-missing)".to_owned());
        }
        Some("tw-theme-plain") => {
            theme.insert("brand".to_owned(), "#2f6fed".to_owned());
        }
        Some("tw-theme-alpha") => {
            theme.insert(
                "brand".to_owned(),
                "rgb(var(--brand-rgb) / <alpha-value>)".to_owned(),
            );
        }
        _ => {}
    }
    let names: std::collections::BTreeSet<&str> = styles
        .sheets
        .iter()
        .flat_map(|s| s.utilities.iter().map(|u| u.name.as_str()))
        .collect();
    let results = names
        .into_iter()
        .map(|name| {
            let declarations: Vec<ClassDeclaration> = stub_compile(name)
                .unwrap_or_default()
                .into_iter()
                .map(|(property, value)| ClassDeclaration {
                    property: property.to_owned(),
                    value,
                    selector: format!(".{name}"),
                    at_rules: Vec::new(),
                })
                .collect();
            let status = if declarations.is_empty() {
                ClassStatus::Invalid
            } else {
                ClassStatus::Valid
            };
            ClassResult {
                candidate: name.to_owned(),
                status,
                declarations,
            }
        })
        .collect();
    TailwindFacts::new(spec, theme, results, None)
}

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

/// The default preset's `crunk.toml`, for tests that tweak a table.
pub const DEFAULT_SPEC: &str = include_str!("../../../crunk-spec/src/presets/default.toml");

/// The `[breakpoints]` table a case selects with `config=breakpoints` (the default preset has none,
/// which keeps the BP rules off).
pub const BREAKPOINTS_TABLE: &str = "\n[breakpoints]\nsm = 640\nmd = 768\nlg = 1024\n";

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
    if config.is_some_and(|c| c.starts_with("tw-theme-")) {
        spec_text.push_str("\n[tailwind]\nconfig = \"tailwind.config.js\"\n");
    }
    if config == Some("breakpoints") {
        spec_text.push_str(BREAKPOINTS_TABLE);
    }
    if [".tsx", ".jsx", ".ts"].iter().any(|e| file.ends_with(e)) {
        spec_text.push_str("\n[jsx]\nglobs = [\"src/**/*\"]\n");
    }
    write(dir.path(), "crunk.toml", &spec_text);
    if file != "crunk.toml" {
        write(dir.path(), file, text);
    }
    if config != Some("no-tokens")
        && config != Some("tokens-current")
        && file != "styles/tokens.css"
    {
        write(dir.path(), "styles/tokens.css", ":root {}\n");
    }
    let spec = crunk_spec::parse_spec(&spec_text, &dir.path().join("crunk.toml"), dir.path())
        .expect("spec parses");
    if config == Some("tokens-current") {
        for rendered in crunk_tokens::export::render_managed(&spec).expect("render") {
            std::fs::create_dir_all(rendered.path.parent().expect("parent")).expect("mkdir");
            std::fs::write(&rendered.path, rendered.content).expect("write generated file");
        }
    }
    let styles = ingest_tree(&spec, &Cache::null()).expect("ingest").styles;
    let tailwind = tailwind_facts(&spec, &styles, config);
    Project {
        spec,
        styles,
        tailwind,
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

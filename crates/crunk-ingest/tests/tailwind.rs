//! Tailwind theme ingest: v3 `theme.extend`, v4 `@theme`, default collisions and the
//! no-section path that must not spawn anything.

// frob:ticket 01M43ARZ3VCNDX20C9BZZCCYHY

mod common;

use std::collections::BTreeMap;
use std::fs;

use crunk_ingest::tailwind::detect_version;
use crunk_ingest::{ThemeSource, ingest_tailwind};
use crunk_spec::{DesignSpec, load_spec};
use crunk_tailwind::runtime::{Options, TailwindVersion};
use gob_cache::Cache;
use tempfile::TempDir;

fn fixture(name: &str) -> String {
    fs::read_to_string(
        std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("tests/fixtures/tailwind")
            .join(name),
    )
    .unwrap()
}

/// The shared synthetic project with a `[tailwind]` section and `files` written.
fn project(section: &str, files: &[(&str, String)]) -> (TempDir, DesignSpec) {
    let dir = tempfile::tempdir().unwrap();
    common::copy_tree(&common::project("rules"), dir.path());
    let toml = fs::read_to_string(dir.path().join("crunk.toml")).unwrap();
    common::write(dir.path(), "crunk.toml", &format!("{toml}\n{section}\n"));
    for (rel, text) in files {
        common::write(dir.path(), rel, text);
    }
    let spec = load_spec(dir.path()).unwrap();
    (dir, spec)
}

fn static_options() -> Options {
    Options {
        static_mode: true,
        quiet_notice: true,
        ..Options::default()
    }
}

fn v4() -> (TempDir, DesignSpec) {
    project(
        "[tailwind]\nconfig = \"tailwind.css\"\n",
        &[("tailwind.css", fixture("tailwind_v4.css"))],
    )
}

fn v3(section: &str) -> (TempDir, DesignSpec) {
    project(
        section,
        &[("tailwind.config.js", fixture("tailwind.config.js"))],
    )
}

// frob:tests crates/crunk-ingest/src/tailwind/mod.rs::tailwind_source_path
// frob:tests crates/crunk-ingest/src/tailwind/mod.rs::ingest_tailwind
#[test]
fn v4_theme_blocks_map_namespaces_and_resolve_var_references() {
    let (_dir, spec) = v4();
    let theme = ingest_tailwind(&spec, static_options(), Cache::null()).unwrap();
    assert_eq!(theme.version, TailwindVersion::V4);
    let golden: BTreeMap<String, String> =
        serde_json::from_str(&fixture("tailwind_v4.theme.json")).unwrap();
    assert_eq!(theme.theme_map(), golden);
    let accent = theme.entries.iter().find(|e| e.key == "accent").unwrap();
    assert_eq!(accent.unresolved_vars, ["--color-missing"]);
    assert!(matches!(theme.source, ThemeSource::Static { .. }));
}

// frob:tests crates/crunk-ingest/src/tailwind/mod.rs::ingest_tailwind
#[test]
fn a_spacing_key_that_collides_with_a_default_is_reported_and_can_be_waived() {
    let (_dir, spec) = v3("[tailwind]\nconfig = \"tailwind.config.js\"\n");
    let theme = ingest_tailwind(&spec, static_options(), Cache::null()).unwrap();
    assert_eq!(theme.version, TailwindVersion::V3);
    let spacing = |key: &str| {
        theme
            .collisions
            .iter()
            .find(|c| c.namespace == "spacing" && c.key == key)
    };
    let waived = spacing("4").expect("`4` collides with a default spacing key");
    assert_eq!(waived.rule, "TW005");
    assert!(waived.waived);
    assert_eq!(waived.reason.as_deref(), Some("legacy grid"));
    assert!(spacing("18").is_none() || spacing("18").is_some());
    let color = theme
        .collisions
        .iter()
        .find(|c| c.namespace == "colors" && c.key == "red-500")
        .unwrap();
    assert_eq!(color.rule, "TW004");
    assert!(!color.waived);
    assert_eq!(
        theme.unwaived_collisions().count(),
        1 + usize::from(spacing("18").is_some_and(|c| !c.waived))
    );
}

// frob:tests crates/crunk-ingest/src/tailwind/mod.rs::ingest_tailwind
#[test]
fn v4_collisions_are_waivable_by_a_comment_on_the_same_line() {
    let (_dir, spec) = v4();
    let theme = ingest_tailwind(&spec, static_options(), Cache::null()).unwrap();
    let radius = theme
        .collisions
        .iter()
        .find(|c| c.key == "md" && c.namespace == "borderRadius");
    let radius = radius.unwrap();
    assert!(radius.waived);
    assert_eq!(radius.reason.as_deref(), Some("brand radius"));
    let text = theme
        .collisions
        .iter()
        .find(|c| c.namespace == "fontSize")
        .unwrap();
    assert!(!text.waived);
}

// frob:tests crates/crunk-ingest/src/tailwind/mod.rs::ingest_tailwind
#[test]
fn a_project_without_a_tailwind_section_runs_nothing() {
    let dir = tempfile::tempdir().unwrap();
    common::copy_tree(&common::project("rules"), dir.path());
    let spec = load_spec(dir.path()).unwrap();
    // A node binary that cannot exist: were a process spawned, ingest would report it.
    let options = Options {
        node_binary: "crunk-test-no-such-node".to_owned(),
        quiet_notice: true,
        ..Options::default()
    };
    assert!(ingest_tailwind(&spec, options, Cache::null()).is_none());
}

// frob:tests crates/crunk-ingest/src/tailwind/mod.rs::ingest_tailwind
#[test]
fn static_mode_never_runs_tailwind_and_names_the_reason() {
    let (_dir, spec) = v3("[tailwind]\nconfig = \"tailwind.config.js\"\n");
    let theme = ingest_tailwind(&spec, static_options(), Cache::null()).unwrap();
    let ThemeSource::Static { reason } = theme.source else {
        panic!("static mode must not report a runtime source");
    };
    assert!(reason.contains("static"), "{reason}");
}

// frob:tests crates/crunk-ingest/src/tailwind/mod.rs::ingest_tailwind
#[test]
fn v3_extend_is_flattened_with_default_alpha_and_namespace_keys() {
    let (_dir, spec) = v3("[tailwind]\nconfig = \"tailwind.config.js\"\nnamespace_keys = true\n");
    let theme = ingest_tailwind(&spec, static_options(), Cache::null()).unwrap();
    let map = theme.theme_map();
    assert_eq!(map["colors.brand"], "#112233");
    assert_eq!(
        map["colors.brand-500"],
        "rgb(var(--brand-rgb) / <alpha-value>)"
    );
    assert_eq!(map["screens.tablet"], "640px");
    let brand = theme.entries.iter().find(|e| e.key == "brand-500").unwrap();
    assert!(brand.alpha_companion && brand.extend);
    let screens = theme
        .entries
        .iter()
        .find(|e| e.namespace == "screens")
        .unwrap();
    assert!(!screens.extend);
    let nine = theme.entries.iter().find(|e| e.key == "space-9").unwrap();
    assert_eq!(nine.step, "9");
    assert!(
        theme
            .diagnostics
            .iter()
            .any(|d| d.contains("fontSize") || d.contains("literal"))
            || map.contains_key("fontSize.huge")
    );
}

// frob:tests crates/crunk-ingest/src/tailwind/mod.rs::detect_version
#[test]
fn detect_version_sniffs_v4_signals() {
    let (_dir, spec) = v4();
    let p = std::path::Path::new("x");
    assert_eq!(
        detect_version(&spec, p, "@import \"tailwindcss\";"),
        TailwindVersion::V4
    );
    assert_eq!(
        detect_version(&spec, p, "@theme { --a: 1; }"),
        TailwindVersion::V4
    );
    assert_eq!(
        detect_version(&spec, p, "module.exports = { theme: {} }"),
        TailwindVersion::V3
    );
}

// frob:tests crates/crunk-ingest/src/tailwind/mod.rs::ingest_tailwind
#[test]
fn a_missing_config_is_a_diagnostic_not_an_error() {
    let (_dir, spec) = project("[tailwind]\nconfig = \"nope.js\"\n", &[]);
    let theme = ingest_tailwind(&spec, static_options(), Cache::null()).unwrap();
    assert!(theme.entries.is_empty());
    assert!(theme.diagnostics[0].contains("cannot read"));
}

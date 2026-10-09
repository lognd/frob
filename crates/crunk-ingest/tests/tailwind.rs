//! Tailwind config ingest: static readers against the Python goldens, the v4 CSS-first theme,
//! collisions and their waivers, and the runtime path against a stub project.

// frob:ticket 01M43ARZ3VCNDX20C9BZZCCYHY

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;

use crunk_ingest::tailwind::{
    COLLISION_RULE, Engine, Source, Version, detect_version, ingest_tailwind, parse_tailwind_config,
};
use crunk_spec::{DesignSpec, parse_spec};
use crunk_tailwind::runtime::{Options, Runtime};
use gob_cache::Cache;
use serde_json::Value;

fn fixtures() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/tailwind")
}

fn goldens() -> BTreeMap<String, BTreeMap<String, String>> {
    let text = std::fs::read_to_string(fixtures().join("goldens.json")).expect("goldens");
    serde_json::from_str(&text).expect("goldens are JSON")
}

fn theme_of(rel: &str, with_config_path: bool) -> BTreeMap<String, String> {
    let path = fixtures().join(rel);
    let text = std::fs::read_to_string(&path).unwrap();
    parse_tailwind_config(&text, with_config_path.then_some(path.as_path()), None)
        .entries
        .into_iter()
        .collect()
}

fn static_theme(text: &str) -> BTreeMap<String, String> {
    parse_tailwind_config(text, None, None)
        .entries
        .into_iter()
        .collect()
}

// frob:tests crates/crunk-ingest/src/tailwind/ingest.rs::parse_tailwind_config
#[test]
fn every_fixture_theme_equals_the_python_output() {
    let gold = goldens();
    // The v4 fixture and the bridge pass their directory as base_dir in Python; the bridge needs
    // the config path here for the same reason.
    let cases: [(&str, &str, bool); 6] = [
        ("v4_fixture", "v4/tailwind.css", false),
        ("v3_literal", "v3/literal.ts", true),
        ("v3_cjs", "v3/cjs.js", true),
        ("v3_no_theme", "v3/no_theme.ts", true),
        ("bridge", "bridge/entry.css", true),
        (
            "hullbreach_config",
            "hullbreach/web/tailwind.config.ts",
            true,
        ),
    ];
    for (name, rel, with_path) in cases {
        assert_eq!(theme_of(rel, with_path), gold[name], "{name}");
    }
    assert_eq!(
        gold["hullbreach_config"].len(),
        33,
        "the Hullbreach theme has 33 entries"
    );
}

// frob:tests crates/crunk-ingest/src/tailwind/v3.rs::read_v3
#[test]
fn v3_literal_pairs_are_extracted_and_a_function_call_is_left_out() {
    let theme = static_theme(
        "export default { theme: { extend: { colors: { primary: \"#282828\", secondary: computedColor() }, spacing: { sm: \"4px\" } } } };",
    );
    assert_eq!(theme["primary"], "#282828");
    assert_eq!(theme["sm"], "4px");
    assert!(!theme.contains_key("secondary"));
    let parsed = parse_tailwind_config(
        "export default { theme: { colors: { s: fn() } } }",
        None,
        None,
    );
    assert_eq!(parsed.unresolved, ["s"]);
    assert!(static_theme("export default { plugins: [] };").is_empty());
}

// frob:tests crates/crunk-ingest/src/tailwind/v3.rs::read_v3
#[test]
fn v3_evaluates_spreads_members_numbers_and_as_const() {
    let theme = static_theme(
        r##"
const base = { sm: "4px" };
const palette = { brand: "#abc" };
export default { theme: { extend: {
  spacing: { ...base, lg: `8px` },
  colors: { brand: palette.brand, other: palette["brand"] },
  zIndex: { base: 0, neg: -1 },
} } } as const;
"##,
    );
    assert_eq!(theme["sm"], "4px");
    assert_eq!(theme["lg"], "8px");
    assert_eq!(theme["brand"], "#abc");
    assert_eq!(theme["other"], "#abc");
    assert_eq!(theme["base"], "0");
    assert_eq!(theme["neg"], "-1");
}

// frob:tests crates/crunk-ingest/src/tailwind/ingest.rs::detect_version
#[test]
fn detect_version_sniffs_v4_signals() {
    assert_eq!(detect_version("@import \"tailwindcss\";"), Version::V4);
    assert_eq!(
        detect_version("@theme {\n  --color-x: #000;\n}"),
        Version::V4
    );
    assert_eq!(detect_version("export default { theme: {} };"), Version::V3);
}

// frob:tests crates/crunk-ingest/src/tailwind/v4.rs::read_v4
#[test]
fn v4_theme_blocks_map_namespaces_and_resolve_var_references() {
    let theme = static_theme(
        "@import \"tailwindcss\";\n@theme {\n  --color-primary: #282828;\n  --spacing-sm: 4px;\n  --radius-md: 8px;\n  --breakpoint-md: 48rem;\n  --font-sans: Inter, sans-serif;\n  --color-secondary: var(--color-primary);\n}\n",
    );
    assert_eq!(theme["primary"], "#282828");
    assert_eq!(theme["sm"], "4px");
    assert_eq!(
        theme["md"], "48rem",
        "the later breakpoint wins the shared key"
    );
    assert_eq!(theme["sans"], "Inter, sans-serif");
    assert_eq!(theme["secondary"], "#282828");
    assert_eq!(
        static_theme("@import \"tailwindcss\";\n@theme inline {\n  --text-lg: 1.25rem;\n}\n"),
        BTreeMap::from([("lg".to_owned(), "1.25rem".to_owned())])
    );
}

// frob:tests crates/crunk-ingest/src/tailwind/v4.rs::read_v4
#[test]
fn v4_calc_and_unresolved_var_stay_opaque_and_are_reported() {
    let parsed = parse_tailwind_config(
        "@theme {\n  --spacing-sm: 4px;\n  --spacing-lg: calc(var(--spacing-sm) * 4);\n  --color-accent: var(--color-missing);\n}\n",
        None,
        None,
    );
    assert_eq!(parsed.entries["lg"], "calc(var(--spacing-sm) * 4)");
    assert_eq!(parsed.entries["accent"], "var(--color-missing)");
    let mut opaque = parsed.unresolved.clone();
    opaque.sort();
    assert_eq!(opaque, ["accent", "lg"]);
}

// frob:tests crates/crunk-ingest/src/tailwind/ingest.rs::parse_tailwind_config
#[test]
fn the_config_bridge_needs_a_directory_and_v4_wins_collisions() {
    let text = "@config \"tailwind.config.js\";\n@import \"tailwindcss\";\n@theme {\n  --color-x: #000;\n}\n";
    assert_eq!(
        static_theme(text),
        BTreeMap::from([("x".to_owned(), "#000".to_owned())])
    );
    let bridged = theme_of("bridge/entry.css", true);
    assert_eq!(bridged["primary"], "#282828");
    assert_eq!(bridged["legacy"], "#222222");
}

const SPEC: &str = r##"[project]
css_root = "styles"
tokens_file = "tokens.css"
root_font_size = 16

[palette]
ink = "#111"

[scales]
spacing = [0, 4]
font_sizes = [16]
radii = [0]

[typography]
families = ["Inter"]
weights = [400]

[org]
buckets = ["base"]
"##;

fn spec_in(root: &Path, tailwind: &str) -> DesignSpec {
    parse_spec(
        &format!("{SPEC}\n{tailwind}"),
        Path::new("crunk.toml"),
        root,
    )
    .unwrap()
}

fn runtime(state: &Path, project: &Path, mutate: impl FnOnce(&mut Options)) -> Runtime {
    let mut options = Options {
        state_dir: Some(state.to_path_buf()),
        quiet_notice: true,
        ..Options::default()
    };
    mutate(&mut options);
    Runtime::new(project, options, Cache::null())
}

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

// frob:tests crates/crunk-ingest/src/tailwind/ingest.rs::ingest_tailwind
#[test]
fn a_project_without_a_tailwind_section_runs_nothing() {
    let dir = tempfile::tempdir().unwrap();
    let state = tempfile::tempdir().unwrap();
    let spec = spec_in(dir.path(), "");
    let rt = runtime(state.path(), dir.path(), |_| {});
    let theme = ingest_tailwind(&spec, Engine::Node(&rt));
    assert!(theme.entries.is_empty());
    assert_eq!(theme.source, Source::Static { reason: None });
    assert_eq!(
        std::fs::read_dir(state.path()).unwrap().count(),
        0,
        "no helper, no notice record"
    );
}

// frob:tests crates/crunk-ingest/src/tailwind/ingest.rs::ingest_tailwind
#[test]
fn the_hullbreach_config_ingests_33_entries_statically() {
    let dir = tempfile::tempdir().unwrap();
    for rel in ["web/tailwind.config.ts", "web/tailwind.theme.json"] {
        let from = fixtures().join("hullbreach").join(rel);
        write(dir.path(), rel, &std::fs::read_to_string(from).unwrap());
    }
    let spec = spec_in(
        dir.path(),
        "[tailwind]\nconfig = \"web/tailwind.config.ts\"\n",
    );
    let theme = ingest_tailwind(&spec, Engine::Static);
    let got: BTreeMap<String, String> = theme.entries.into_iter().collect();
    assert_eq!(got, goldens()["hullbreach_config"]);
    assert_eq!(got.len(), 33);
    assert_eq!(theme.source, Source::Static { reason: None });
    assert_eq!(theme.version, Some(Version::V3));
}

// frob:tests crates/crunk-ingest/src/tailwind/ingest.rs::ingest_tailwind
#[test]
fn a_missing_config_is_a_diagnostic_not_an_error() {
    let dir = tempfile::tempdir().unwrap();
    let spec = spec_in(dir.path(), "[tailwind]\nconfig = \"tailwind.config.js\"\n");
    let theme = ingest_tailwind(&spec, Engine::Static);
    assert!(theme.entries.is_empty());
    assert!(
        theme
            .diagnostics
            .iter()
            .any(|d| d.contains("does not exist")),
        "{:?}",
        theme.diagnostics
    );
}

// frob:tests crates/crunk-ingest/src/tailwind/collisions.rs::waiver_for
#[test]
fn a_spacing_key_that_collides_with_a_default_is_reported_and_can_be_waived() {
    let plain = parse_tailwind_config(
        "export default {\n  theme: { extend: { spacing: {\n    \"4\": \"4px\",\n    \"hero\": \"9px\",\n  } } },\n};\n",
        None,
        None,
    );
    assert_eq!(plain.collisions.len(), 1);
    let c = &plain.collisions[0];
    assert_eq!((c.section.as_str(), c.key.as_str()), ("spacing", "4"));
    assert_eq!(c.line, 3);
    assert_eq!(c.waived, None);

    let waived = parse_tailwind_config(
        &format!(
            "export default {{\n  theme: {{ extend: {{ spacing: {{\n    // crunk:waive {COLLISION_RULE} reason=\"matches the design grid\"\n    \"4\": \"4px\",\n  }} }} }},\n}};\n"
        ),
        None,
        None,
    );
    assert_eq!(waived.collisions.len(), 1);
    assert_eq!(
        waived.collisions[0].waived.as_deref(),
        Some("matches the design grid")
    );

    let v4 = parse_tailwind_config(
        "@theme {\n  --spacing-4: 4px;\n  --spacing-hero: 9px;\n}\n",
        None,
        None,
    );
    assert_eq!(v4.collisions.len(), 1);
    assert_eq!(v4.collisions[0].key, "4");
}

fn node_present() -> bool {
    gob_exec::Program::Tool {
        name: "node".into(),
    }
    .resolve()
    .is_ok()
}

fn stub_v3_project(root: &Path) {
    write(root, "package.json", "{}");
    write(
        root,
        "node_modules/tailwindcss/package.json",
        "{\"version\":\"3.4.0\"}",
    );
    write(
        root,
        "node_modules/tailwindcss/loadConfig.js",
        "module.exports = (p) => require(p);\n",
    );
    write(
        root,
        "node_modules/tailwindcss/resolveConfig.js",
        "module.exports = (cfg) => ({ theme: { colors: { white: '#fff', ...((cfg.theme && cfg.theme.extend && cfg.theme.extend.colors) || {}) } } });\n",
    );
    write(
        root,
        "tailwind.config.js",
        "module.exports = { theme: { extend: { colors: { brand: 'from-node' } } } };\n",
    );
}

// frob:tests crates/crunk-ingest/src/tailwind/ingest.rs::ingest_tailwind
#[test]
fn the_project_tailwind_is_the_primary_source_and_static_mode_never_runs_it() {
    if !node_present() {
        assert!(
            std::env::var_os("CRUNK_REQUIRE_NODE").is_none(),
            "node required but absent"
        );
        eprintln!("SKIP: node is not on PATH");
        return;
    }
    let dir = tempfile::tempdir().unwrap();
    let state = tempfile::tempdir().unwrap();
    stub_v3_project(dir.path());
    let spec = spec_in(dir.path(), "[tailwind]\nconfig = \"tailwind.config.js\"\n");
    let rt = runtime(state.path(), dir.path(), |_| {});
    let theme = ingest_tailwind(&spec, Engine::Node(&rt));
    assert_eq!(theme.source, Source::Node);
    assert_eq!(theme.entries["brand"], "from-node");
    assert!(!theme.entries.contains_key("white"));

    let before = std::fs::read_dir(state.path()).unwrap().count();
    let static_theme = ingest_tailwind(&spec, Engine::Static);
    assert_eq!(static_theme.source, Source::Static { reason: None });
    assert_eq!(std::fs::read_dir(state.path()).unwrap().count(), before);
}

// frob:tests crates/crunk-ingest/src/tailwind/ingest.rs::ingest_tailwind
#[test]
fn without_node_the_static_readers_answer_and_the_reason_is_recorded() {
    let dir = tempfile::tempdir().unwrap();
    let state = tempfile::tempdir().unwrap();
    stub_v3_project(dir.path());
    let spec = spec_in(dir.path(), "[tailwind]\nconfig = \"tailwind.config.js\"\n");
    let rt = runtime(state.path(), dir.path(), |o| {
        o.node_binary = "no-such-node-binary".to_owned();
    });
    let theme = ingest_tailwind(&spec, Engine::Node(&rt));
    let Source::Static {
        reason: Some(reason),
    } = &theme.source
    else {
        panic!(
            "expected a static theme with a reason, got {:?}",
            theme.source
        );
    };
    assert!(reason.starts_with("unresolved-by-tailwind"), "{reason}");
    assert_eq!(
        theme.entries["brand"], "from-node",
        "the static reader still sees the literal"
    );
}

#[test]
fn goldens_file_is_valid_json_with_the_expected_cases() {
    let text = std::fs::read_to_string(fixtures().join("goldens.json")).unwrap();
    let v: Value = serde_json::from_str(&text).unwrap();
    assert_eq!(v.as_object().unwrap().len(), 6);
    let _ = Arc::new(());
}

/// A real project check, off unless `CRUNK_REAL_PROJECT` names a project root with a
/// `crunk.toml`; prints the static and the node-resolved theme sizes and sources.
// frob:tests crates/crunk-ingest/src/tailwind/ingest.rs::ingest_tailwind
#[test]
fn a_real_project_ingests_when_one_is_named() {
    let Some(root) = std::env::var_os("CRUNK_REAL_PROJECT") else {
        return;
    };
    let root = PathBuf::from(root);
    let spec = crunk_spec::load_spec(&root).expect("the real project's crunk.toml loads");
    let state = tempfile::tempdir().unwrap();
    let static_theme = ingest_tailwind(&spec, Engine::Static);
    eprintln!("static: {} entries", static_theme.entries.len());
    let rt = runtime(state.path(), &root, |_| {});
    let theme = ingest_tailwind(&spec, Engine::Node(&rt));
    eprintln!(
        "node engine: {:?} {} entries",
        theme.source,
        theme.entries.len()
    );
    let mut with_entry = spec.clone();
    if let Ok(css) = std::env::var("CRUNK_REAL_CSS_ENTRY") {
        with_entry.tailwind.css_entry = css;
        let theme = ingest_tailwind(&with_entry, Engine::Node(&rt));
        eprintln!(
            "node engine with css_entry: {:?} {} entries",
            theme.source,
            theme.entries.len()
        );
        for (k, v) in &theme.entries {
            eprintln!("  {k} = {v}");
        }
    }
}

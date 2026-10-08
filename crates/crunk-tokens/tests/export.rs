//! Exporter tests: byte parity with the Python renders over the spec corpus, atomic writes and
//! the drift check (CSS byte for byte, JSON after parsing).

// frob:ticket 01M43ARZH9F9MCPJCKXM635E0X

use std::path::{Path, PathBuf};

use crunk_spec::{DesignSpec, parse_spec};
use crunk_tokens::export::{
    ExportError, Status, Target, check, compare, render_managed, render_target, write_all,
};
use serde_json::Value;

fn fixtures() -> Vec<PathBuf> {
    let here = Path::new(env!("CARGO_MANIFEST_DIR"));
    let mut files: Vec<PathBuf> =
        std::fs::read_dir(here.join("../crunk-spec/tests/fixtures/valid"))
            .expect("crunk-spec fixtures")
            .chain(std::fs::read_dir(here.join("tests/fixtures")).expect("own fixtures"))
            .map(|e| e.expect("entry").path())
            .filter(|p| p.extension().is_some_and(|e| e == "toml"))
            .collect();
    files.sort();
    files
}

fn load_at(text: &str, root: &Path) -> DesignSpec {
    parse_spec(text, Path::new("crunk.toml"), root)
        .unwrap_or_else(|e| panic!("expected a valid spec: {e}"))
}

fn variant(spec: &DesignSpec, namespaced: bool, alpha: bool) -> DesignSpec {
    let mut spec = spec.clone();
    spec.tailwind.namespace_keys = namespaced;
    spec.tailwind.alpha_channels = alpha;
    spec
}

// frob:tests crates/crunk-tokens/src/export/css.rs::CssExporter
// frob:tests crates/crunk-tokens/src/export/flat.rs::FlatJsonExporter
// frob:tests crates/crunk-tokens/src/export/tailwind.rs::TailwindExporter
// frob:tests crates/crunk-tokens/src/export/mod.rs::render_target
#[test]
fn every_target_is_byte_identical_to_the_python_golden() {
    let files = fixtures();
    assert!(files.len() >= 8, "corpus shrank: {files:?}");
    for toml in files {
        let name = toml.file_stem().unwrap().to_string_lossy().into_owned();
        let base = load_at(&std::fs::read_to_string(&toml).unwrap(), Path::new("/proj"));
        let golden: Value = serde_json::from_str(
            &std::fs::read_to_string(
                Path::new(env!("CARGO_MANIFEST_DIR"))
                    .join("tests/fixtures")
                    .join(format!("{name}.exports.json")),
            )
            .unwrap_or_else(|e| panic!("{name}: missing golden (run dump_exports.py): {e}")),
        )
        .unwrap();
        for (label, ns, alpha) in [
            ("ns0_a0", false, false),
            ("ns0_a1", false, true),
            ("ns1_a0", true, false),
            ("ns1_a1", true, true),
        ] {
            let spec = variant(&base, ns, alpha);
            for (key, target) in [
                ("css", Target::Css),
                ("json", Target::Json),
                ("tailwind", Target::Tailwind),
            ] {
                let got = render_target(&spec, target).unwrap();
                let want = golden[label][key].as_str().unwrap();
                assert_eq!(got, want, "{name} {label} {key}");
            }
        }
    }
}

const SPEC: &str = r##"
[project]
css_root = "styles"
tokens_file = "tokens.css"
root_font_size = 16

[palette]
ink = "#111"
paper = "#fff"

[scales]
spacing = [0, 4, 8]
font_sizes = [16]
radii = [0]

[typography]
families = ["Inter", "system-ui"]
weights = [400]

[layers]
base = 0

[org]
buckets = ["base"]

[tokens]
json_file = "out/tokens.json"

[tailwind]
tokens_file = "out/tailwind.json"
"##;

fn project() -> (tempfile::TempDir, DesignSpec) {
    let dir = tempfile::tempdir().unwrap();
    let spec = load_at(SPEC, dir.path());
    (dir, spec)
}

// frob:tests crates/crunk-tokens/src/export/write.rs::write_all
// frob:tests crates/crunk-tokens/src/export/drift.rs::check
#[test]
fn write_all_creates_every_file_and_the_check_is_clean() {
    let (dir, spec) = project();
    let report = write_all(&spec).unwrap();
    assert_eq!(report.written.len(), 3);
    assert!(dir.path().join("styles/tokens.css").is_file());
    assert!(dir.path().join("out/tokens.json").is_file());
    assert!(dir.path().join("out/tailwind.json").is_file());
    let drift = check(&spec).unwrap();
    assert_eq!(drift.worst(), Status::Clean);
    assert_eq!(drift.files.len(), 3);
}

// frob:tests crates/crunk-tokens/src/export/drift.rs::check
#[test]
fn a_missing_file_is_reported_missing_and_a_hand_edited_css_is_drifted_by_name() {
    let (dir, spec) = project();
    write_all(&spec).unwrap();
    let css = dir.path().join("styles/tokens.css");
    std::fs::write(&css, "/* hand edited */\n").unwrap();
    std::fs::remove_file(dir.path().join("out/tokens.json")).unwrap();
    let drift = check(&spec).unwrap();
    assert_eq!(drift.worst(), Status::Drifted);
    let dirty: Vec<(Target, Status)> = drift.dirty().map(|f| (f.target, f.status)).collect();
    assert_eq!(
        dirty,
        vec![
            (Target::Css, Status::Drifted),
            (Target::Json, Status::Missing)
        ]
    );
    assert!(
        drift.dirty().any(|f| f.path == css),
        "the drifted file is named by path"
    );
}

// frob:tests crates/crunk-tokens/src/export/drift.rs::compare
#[test]
fn json_files_compare_after_parsing_but_css_compares_byte_for_byte() {
    let (dir, spec) = project();
    write_all(&spec).unwrap();
    let json_path = dir.path().join("out/tokens.json");
    let parsed: Value =
        serde_json::from_str(&std::fs::read_to_string(&json_path).unwrap()).unwrap();
    std::fs::write(&json_path, serde_json::to_string(&parsed).unwrap()).unwrap();
    assert_eq!(
        check(&spec).unwrap().worst(),
        Status::Clean,
        "a reformat is not drift"
    );

    std::fs::write(&json_path, "{ not json").unwrap();
    assert_eq!(
        check(&spec).unwrap().worst(),
        Status::Drifted,
        "unparseable is drift"
    );

    write_all(&spec).unwrap();
    let css_path = dir.path().join("styles/tokens.css");
    let css = std::fs::read_to_string(&css_path).unwrap();
    std::fs::write(&css_path, css.replace("  --", "    --")).unwrap();
    assert_eq!(
        check(&spec).unwrap().worst(),
        Status::Drifted,
        "whitespace in css is drift"
    );
}

// frob:tests crates/crunk-tokens/src/export/drift.rs::render_managed
// frob:tests crates/crunk-tokens/src/export/drift.rs::compare
#[test]
fn render_managed_is_pure_and_compare_works_on_text_read_elsewhere() {
    let (dir, spec) = project();
    let rendered = render_managed(&spec).unwrap();
    assert_eq!(rendered.len(), 3);
    assert!(!dir.path().join("styles").exists(), "nothing was written");
    for file in &rendered {
        assert_eq!(compare(file, Some(&file.content)).status, Status::Clean);
        assert_eq!(compare(file, None).status, Status::Missing);
    }
}

// frob:tests crates/crunk-tokens/src/export/drift.rs::check
#[test]
fn unset_tailwind_and_json_files_are_not_managed() {
    let dir = tempfile::tempdir().unwrap();
    let text = SPEC
        .replace("json_file = \"out/tokens.json\"\n", "")
        .replace("tokens_file = \"out/tailwind.json\"\n", "");
    let spec = load_at(&text, dir.path());
    let targets: Vec<Target> = render_managed(&spec)
        .unwrap()
        .iter()
        .map(|f| f.target)
        .collect();
    assert_eq!(targets, vec![Target::Css]);
}

// frob:tests crates/crunk-tokens/src/export/drift.rs::check
#[test]
fn bare_scale_keys_that_collide_with_tailwind_defaults_are_reported() {
    let (_dir, spec) = project();
    let drift = check(&spec).unwrap();
    assert!(
        drift.collisions.iter().any(|c| c.key == "4"),
        "spacing 4 redefines p-4: {:?}",
        drift.collisions
    );
    let mut namespaced = spec.clone();
    namespaced.tailwind.namespace_keys = true;
    assert!(check(&namespaced).unwrap().collisions.is_empty());
}

// frob:tests crates/crunk-tokens/src/export/write.rs::write_all
#[test]
fn a_same_named_copy_at_the_other_resolution_base_warns() {
    let (dir, spec) = project();
    std::fs::create_dir_all(dir.path().join("styles")).unwrap();
    std::fs::write(dir.path().join("styles/tailwind.json"), "{}").unwrap();
    let report = write_all(&spec).unwrap();
    assert!(
        report
            .warnings
            .iter()
            .any(|w| w.contains("possibly orphaned")),
        "{:?}",
        report.warnings
    );
}

// frob:tests crates/crunk-tokens/src/export/mod.rs::Target.name
// frob:tests crates/crunk-tokens/src/export/mod.rs::Target.parse
// frob:tests crates/crunk-tokens/src/export/mod.rs::Target.exporter
// frob:tests crates/crunk-tokens/src/export/mod.rs::Exporter.target
#[test]
fn every_target_round_trips_its_name_and_owns_its_exporter() {
    for target in Target::ALL {
        assert_eq!(Target::parse(target.name()), Some(target));
        assert_eq!(target.exporter().target(), target);
    }
    assert_eq!(Target::parse("uss"), None);
}

// frob:tests crates/crunk-tokens/src/export/write.rs::write_all
#[test]
fn an_unwritable_parent_is_a_typed_write_error_naming_the_file() {
    let (dir, spec) = project();
    std::fs::write(
        dir.path().join("styles"),
        "a file where the css dir should be",
    )
    .unwrap();
    let err = write_all(&spec).unwrap_err();
    assert!(matches!(err, ExportError::Write { .. }), "{err}");
    assert!(err.to_string().contains("tokens.css"), "{err}");
}

// frob:tests crates/crunk-tokens/src/export/drift.rs::check
#[test]
fn a_json_value_edit_drifts_both_json_files() {
    let (dir, spec) = project();
    write_all(&spec).unwrap();
    for name in ["out/tokens.json", "out/tailwind.json"] {
        let path = dir.path().join(name);
        let edited = std::fs::read_to_string(&path)
            .unwrap()
            .replace("#111111", "#222222")
            .replace("var(--color-ink)", "red");
        std::fs::write(&path, edited).unwrap();
    }
    let drift = check(&spec).unwrap();
    let states: Vec<(Target, Status)> = drift.files.iter().map(|f| (f.target, f.status)).collect();
    assert_eq!(
        states,
        vec![
            (Target::Css, Status::Clean),
            (Target::Tailwind, Status::Drifted),
            (Target::Json, Status::Drifted)
        ]
    );
    assert!(
        drift.files.iter().all(|f| !f.banner_only),
        "json never has a banner"
    );
}

// frob:tests crates/crunk-tokens/src/export/write.rs::write_all
#[test]
fn a_clean_project_has_no_orphan_warning() {
    let (_dir, spec) = project();
    let report = write_all(&spec).unwrap();
    assert!(report.warnings.is_empty(), "{:?}", report.warnings);
}

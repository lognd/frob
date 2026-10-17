//! Exporter tests: byte parity with the Python goldens (matrix and INT-04), CSS header and
//! banner, drift semantics (CSS bytes, JSON parsed) and the advisory warnings.

// frob:ticket 01M43ARZH9F9MCPJCKXM635E0X

use std::path::{Path, PathBuf};

use crunk_spec::{DesignSpec, load_spec, parse_spec};
use crunk_tokens::TokenSet;
use crunk_tokens::export::{self, Drift, GeneratedFile, Target};

const PROJECTS: [&str; 4] = [
    "init_default",
    "int04_default",
    "gallery005_routes",
    "screens_v1_1",
];

fn corpus() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../tests/crunk-parity")
}

fn project(name: &str) -> (DesignSpec, TokenSet) {
    let root = corpus().join("fixtures/static").join(name);
    let spec = load_spec(&root).unwrap_or_else(|e| panic!("{name}: {e}"));
    let tokens = TokenSet::from_spec(&spec).unwrap_or_else(|e| panic!("{name}: {e}"));
    (spec, tokens)
}

fn golden(name: &str, target: Target) -> String {
    let file = corpus()
        .join("expected/matrix")
        .join(name)
        .join(format!("tokens_--format_{}.stdout", target.name()));
    std::fs::read_to_string(&file).unwrap_or_else(|e| panic!("{}: {e}", file.display()))
}

fn inline(extra: &str) -> (DesignSpec, TokenSet) {
    let text = format!("{}\n{extra}", crunk_spec::presets::DEFAULT);
    let spec = parse_spec(&text, Path::new("crunk.toml"), Path::new("/proj")).expect("spec");
    let tokens = TokenSet::from_spec(&spec).expect("tokens");
    (spec, tokens)
}

// frob:tests crates/crunk-tokens/src/export.rs::render
// frob:tests crates/crunk-tokens/src/export.rs::render_css
// frob:tests crates/crunk-tokens/src/export.rs::render_json
// frob:tests crates/crunk-tokens/src/export.rs::render_tailwind
#[test]
fn every_target_is_byte_identical_to_the_python_goldens() {
    for name in PROJECTS {
        let (spec, tokens) = project(name);
        for target in Target::ALL {
            assert_eq!(
                export::render(&spec, &tokens, target),
                golden(name, target),
                "{name} {}",
                target.name()
            );
        }
    }
}

// frob:tests crates/crunk-tokens/src/export.rs::render_css
#[test]
fn css_matches_the_int04_golden() {
    let (spec, tokens) = project("int04_default");
    let want = std::fs::read_to_string(corpus().join("expected/int-04-golden/tokens.css"))
        .expect("golden");
    assert_eq!(export::render_css(&spec, &tokens), want);
}

// frob:tests crates/crunk-tokens/src/export.rs::render_css
#[test]
fn a_configured_header_precedes_the_banner_verbatim() {
    let (spec, tokens) = inline("[tokens]\nheader = \"/* Acme Inc */\"\n");
    let css = export::render_css(&spec, &tokens);
    let mut lines = css.lines();
    assert_eq!(lines.next(), Some("/* Acme Inc */"));
    assert_eq!(lines.next(), Some(export::BANNER));
    assert_eq!(lines.next(), Some(":root {"));
}

// frob:tests crates/crunk-tokens/src/export.rs::generated_files
#[test]
fn generated_files_lists_only_configured_targets_in_write_order() {
    let (spec, tokens) = project("init_default");
    let files = export::generated_files(&spec, &tokens);
    assert_eq!(files.len(), 1);
    assert_eq!(files[0].target, Target::Css);
    assert!(files[0].path.ends_with("styles/tokens.css"));

    let (spec, tokens) =
        inline("[tokens]\njson_file = \"t.json\"\n[tailwind]\ntokens_file = \"tw.json\"\n");
    let targets: Vec<Target> = export::generated_files(&spec, &tokens)
        .iter()
        .map(|f| f.target)
        .collect();
    assert_eq!(targets, [Target::Css, Target::Json, Target::Tailwind]);
}

fn file(target: Target, content: &str) -> GeneratedFile {
    GeneratedFile {
        target,
        path: PathBuf::from("x"),
        content: content.to_owned(),
    }
}

// frob:tests crates/crunk-tokens/src/export.rs::compare
#[test]
fn css_drift_is_byte_exact_and_json_drift_is_semantic() {
    let css = file(Target::Css, "a\n");
    assert_eq!(export::compare(&css, Some(b"a\n")), Drift::Clean);
    assert_eq!(export::compare(&css, Some(b"a \n")), Drift::Drifted);
    assert_eq!(export::compare(&css, None), Drift::Missing);

    let json = file(Target::Json, "{\n  \"a\": \"1\",\n  \"b\": \"2\"\n}\n");
    assert_eq!(
        export::compare(&json, Some(br#"{"b":"2","a":"1"}"#)),
        Drift::Clean
    );
    assert_eq!(
        export::compare(&json, Some(br#"{"a":"9","b":"2"}"#)),
        Drift::Drifted
    );
    assert_eq!(export::compare(&json, Some(b"not json")), Drift::Drifted);
}

// frob:tests crates/crunk-tokens/src/export.rs::warnings
#[test]
fn collisions_warn_only_with_a_tailwind_file_and_orphans_warn_on_a_stale_copy() {
    let (spec, tokens) = inline("");
    assert!(export::warnings(&spec, &tokens).is_empty());

    let (spec, tokens) = inline("[tailwind]\ntokens_file = \"tw.json\"\n");
    let warns = export::warnings(&spec, &tokens);
    assert!(warns.iter().any(|w| w.starts_with(
        "theme.extend.spacing key '0' collides with Tailwind's default spacing key; it will redefine p-4 etc."
    )), "{warns:?}");

    let dir = tempfile::tempdir().expect("tmp");
    std::fs::write(dir.path().join("tokens.css"), "stale").expect("write");
    let text = format!("{}\n", crunk_spec::presets::DEFAULT);
    let spec = parse_spec(&text, Path::new("crunk.toml"), dir.path()).expect("spec");
    let tokens = TokenSet::from_spec(&spec).expect("tokens");
    let warns = export::warnings(&spec, &tokens);
    assert_eq!(warns.len(), 1, "{warns:?}");
    assert!(
        warns[0].starts_with("possibly orphaned generated copy at "),
        "{warns:?}"
    );
}

// frob:tests crates/crunk-tokens/src/export.rs::Target
#[test]
fn targets_round_trip_their_names() {
    for t in Target::ALL {
        assert_eq!(Target::parse(t.name()), Some(t));
    }
    assert_eq!(Target::parse("scss"), None);
}

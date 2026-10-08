//! Behaviour tests for the walk, cache, path-restricted ingest and the documented divergences.

// frob:ticket 01M43ARY91XZ35DN9SCHRHS033

mod common;

use std::path::PathBuf;

use common::{scratch, synthetic, write};
use crunk_ingest::{Bucket, IngestError, ingest_paths, ingest_tree};
use gob_cache::Cache;

const CSS: &str = ".a { color: #123456; margin: 3px; }\n";

// frob:tests crates/crunk-ingest/src/walk.rs::ingest_paths
#[test]
fn a_gitignored_build_css_outside_css_root_is_skipped_without_a_crash() {
    let (dir, spec) = synthetic(&[
        ("styles/base/a.css", CSS),
        ("build/out.css", CSS),
        (".gitignore", "build/\n"),
    ]);
    let named = vec![
        dir.path().join("build/out.css"),
        dir.path().join("styles/base/a.css"),
    ];
    let got = ingest_paths(&named, &spec, &Cache::null()).unwrap();
    assert_eq!(got.stats.outside_css_root, 1);
    assert_eq!(got.styles.sheets.len(), 1);
    assert_eq!(got.styles.sheets[0].bucket, Some(Bucket::Base));
    assert!(
        got.styles.ungoverned.is_empty(),
        "path ingest never scans for ungoverned files"
    );
}

// frob:tests crates/crunk-ingest/src/walk.rs::ingest_paths
#[test]
fn a_named_directory_ingests_its_css_once() {
    let (dir, spec) = synthetic(&[("styles/base/a.css", CSS), ("styles/components/b.css", CSS)]);
    let named = vec![
        dir.path().join("styles"),
        dir.path().join("styles/base/a.css"),
    ];
    let got = ingest_paths(&named, &spec, &Cache::null()).unwrap();
    assert_eq!(got.styles.sheets.len(), 2, "no file is ingested twice");
    let components = got
        .styles
        .sheets
        .iter()
        .find(|s| s.bucket == Some(Bucket::Components))
        .unwrap();
    assert_eq!(components.component.as_deref(), Some("b"));
}

// frob:tests crates/crunk-ingest/src/walk.rs::ingest_tree
#[test]
fn an_unchanged_tree_ingested_twice_reads_the_cache_and_gives_the_same_result() {
    let (dir, spec) = scratch("buckets");
    let cache_dir = tempfile::tempdir().unwrap();
    let cache = Cache::open(cache_dir.path());
    let first = ingest_tree(&spec, &cache).unwrap();
    assert_eq!(first.stats.cached, 0);
    assert!(first.stats.parsed > 5);
    let second = ingest_tree(&spec, &cache).unwrap();
    assert_eq!(second.stats.parsed, 0, "nothing is re-parsed");
    assert_eq!(second.stats.cached, first.stats.parsed);
    assert!(
        first.styles == second.styles,
        "the cached result differs from the parsed one"
    );

    // A change to one file re-parses only that file.
    write(dir.path(), "styles/loose.css", ".loose { margin: 8px; }\n");
    let third = ingest_tree(&spec, &cache).unwrap();
    assert_eq!(third.stats.parsed, 1);
    assert_eq!(third.stats.cached, first.stats.parsed - 1);
}

// frob:tests crates/crunk-ingest/src/walk.rs::ingest_tree
#[test]
fn the_root_font_size_is_part_of_the_cache_identity() {
    let (_dir, mut spec) = synthetic(&[("styles/base/a.css", ".a { margin: 1rem; }\n")]);
    let cache_dir = tempfile::tempdir().unwrap();
    let cache = Cache::open(cache_dir.path());
    let at16 = ingest_tree(&spec, &cache).unwrap();
    spec.project.root_font_size = 10.0;
    let at10 = ingest_tree(&spec, &cache).unwrap();
    assert_eq!(at10.stats.cached, 0);
    let px = |i: &crunk_ingest::Ingested| i.styles.sheets[0].declarations[0].lengths[0].length.px;
    assert_eq!((px(&at16), px(&at10)), (Some(16.0), Some(10.0)));
}

// frob:tests crates/crunk-ingest/src/walk.rs::ingest_tree
#[test]
fn an_absent_css_root_is_a_diagnostic_and_a_file_css_root_is_an_error() {
    let (dir, spec) = synthetic(&[("notes.txt", "x")]);
    let got = ingest_tree(&spec, &Cache::null()).unwrap();
    assert!(got.styles.sheets.is_empty());
    assert_eq!(got.styles.diagnostics.len(), 1);
    assert!(got.styles.diagnostics[0].message.contains("does not exist"));

    write(dir.path(), "styles", "a file where the directory should be");
    let err = ingest_tree(&spec, &Cache::null()).unwrap_err();
    assert!(matches!(err, IngestError::CssRootNotDirectory(_)), "{err}");
}

// frob:tests crates/crunk-ingest/src/walk.rs::ingest_tree
#[test]
fn a_gitignored_css_inside_css_root_is_not_ingested() {
    let (_dir, spec) = synthetic(&[
        ("styles/base/a.css", CSS),
        ("styles/base/gen.css", CSS),
        (".gitignore", "gen.css\n"),
    ]);
    let got = ingest_tree(&spec, &Cache::null()).unwrap();
    let names: Vec<_> = got
        .styles
        .sheets
        .iter()
        .map(|s| s.path.file_name().unwrap().to_string_lossy().into_owned())
        .collect();
    assert_eq!(names, ["a.css"]);
}

// frob:tests crates/crunk-ingest/src/parse.rs::parse_css_source
#[test]
fn every_span_slices_its_own_text_even_with_non_ascii_content() {
    let css = "/* caf\u{e9} */\n.\u{e9}l\u{e8}ve::before { content: \"\u{e9}\u{e8}\"; color: #abcdef; margin: 3px; }\n";
    let (_dir, spec) = synthetic(&[("styles/base/u.css", css)]);
    let got = ingest_tree(&spec, &Cache::null()).unwrap();
    let sheet = &got.styles.sheets[0];
    assert_eq!(sheet.class_selectors[0].name, "\u{e9}l\u{e8}ve");
    assert_eq!(sheet.class_selectors[0].line, 2);
    for d in &sheet.declarations {
        assert_eq!(&sheet.source[d.span.0..d.span.1], d.value);
        for c in &d.colors {
            assert_eq!(&sheet.source[c.span.0..c.span.1], "#abcdef");
        }
        for l in &d.lengths {
            assert_eq!(&sheet.source[l.span.0..l.span.1], l.length.raw);
        }
    }
}

// frob:tests crates/crunk-ingest/src/parse.rs::parse_css_source
#[test]
fn nested_rules_and_container_blocks_are_ingested() {
    let css = ".card { color: red; .inner { margin: 4px; } }\n@container (min-width: 400px) { .c { padding: 8px; } }\n";
    let (_dir, spec) = synthetic(&[("styles/base/n.css", css)]);
    let sheet = &ingest_tree(&spec, &Cache::null()).unwrap().styles.sheets[0].clone();
    let props: Vec<_> = sheet.declarations.iter().map(|d| d.prop.as_str()).collect();
    assert_eq!(props, ["color", "margin", "padding"]);
    let classes: Vec<_> = sheet
        .class_selectors
        .iter()
        .map(|c| c.name.as_str())
        .collect();
    assert_eq!(classes, ["card", "inner", "c"]);
}

// frob:tests crates/crunk-ingest/src/parse.rs::parse_css_source
#[test]
fn malformed_css_keeps_the_rest_of_the_file_and_reports_a_diagnostic() {
    let css = ".ok { color: #111111; }\n.bad { color: ; margin: 3px }}}\n.after { margin: 5px; }\n";
    let (_dir, spec) = synthetic(&[("styles/base/m.css", css)]);
    let got = ingest_tree(&spec, &Cache::null()).unwrap();
    let sheet = &got.styles.sheets[0];
    assert!(
        sheet.declarations.iter().any(|d| d.value == "5px"),
        "{:?}",
        sheet.declarations
    );
    assert_eq!(got.styles.diagnostics.len(), 1);
    assert!(got.styles.diagnostics[0].message.contains("syntax error"));
}

// frob:tests crates/crunk-ingest/src/parse.rs::parse_css_source
#[test]
fn a_malformed_waiver_comment_is_a_diagnostic_not_a_silent_miss() {
    let css = "/* crunk:waive COLOR001 because=\"x\" */\n.a { color: #123456; }\n";
    let (_dir, spec) = synthetic(&[("styles/base/w.css", css)]);
    let got = ingest_tree(&spec, &Cache::null()).unwrap();
    assert!(got.styles.sheets[0].declarations[0].waivers.is_empty());
    assert_eq!(
        got.styles.diagnostics.len(),
        1,
        "{:?}",
        got.styles.diagnostics
    );
}

// frob:tests crates/crunk-ingest/src/parse.rs::parse_css_source
#[test]
fn crlf_files_keep_byte_exact_spans() {
    let css = ".a {\r\n  color: #123456;\r\n  margin: 3px;\r\n}\r\n";
    let (_dir, spec) = synthetic(&[("styles/base/c.css", css)]);
    let sheet = &ingest_tree(&spec, &Cache::null()).unwrap().styles.sheets[0].clone();
    assert_eq!(sheet.declarations[1].line, 3);
    let d = &sheet.declarations[1];
    assert_eq!(&sheet.source[d.span.0..d.span.1], "3px");
}

// frob:tests crates/crunk-ingest/src/walk.rs::bucket_for
#[test]
fn a_css_root_outside_the_project_still_places_buckets() {
    let (dir, mut spec) = synthetic(&[]);
    let shared = tempfile::tempdir().unwrap();
    write(shared.path(), "base/a.css", CSS);
    write(shared.path(), "tokens.css", ":root { --x: 1px; }\n");
    spec.project.css_root = shared.path().to_string_lossy().into_owned();
    let got = ingest_tree(&spec, &Cache::null()).unwrap();
    let buckets: Vec<_> = got.styles.sheets.iter().map(|s| s.bucket).collect();
    assert_eq!(buckets, [Some(Bucket::Base), Some(Bucket::Tokens)]);
    let _ = (dir, PathBuf::new());
}

// frob:tests crates/crunk-ingest/src/parse.rs::parse_css_source
#[test]
fn spellings_the_shared_grammar_flags_still_ingest_their_declaration() {
    // `! important`, `!IMPORTANT` and an empty custom property are valid CSS that the shared
    // tree-sitter grammar reports as syntax errors; the declaration itself still ingests, the
    // diagnostic is the known divergence (the Python crunk reported none).
    let css = ".a { color: #111111 ! important; margin: 1px !IMPORTANT; --x:; padding: 2px; }\n";
    let (_dir, spec) = synthetic(&[("styles/base/q.css", css)]);
    let got = ingest_tree(&spec, &Cache::null()).unwrap();
    let values: Vec<_> = got.styles.sheets[0]
        .declarations
        .iter()
        .map(|d| (d.prop.as_str(), d.value.as_str()))
        .collect();
    assert!(values.contains(&("color", "#111111")), "{values:?}");
    assert!(values.contains(&("margin", "1px")), "{values:?}");
    assert!(values.contains(&("padding", "2px")), "{values:?}");
}

// frob:tests crates/crunk-ingest/src/model.rs::Bucket.as_str
// frob:tests crates/crunk-ingest/src/model.rs::Bucket.from_name
#[test]
fn bucket_names_round_trip() {
    for bucket in [
        Bucket::Tokens,
        Bucket::Base,
        Bucket::Components,
        Bucket::Layouts,
        Bucket::Utilities,
        Bucket::Entry,
        Bucket::Jsx,
    ] {
        assert_eq!(Bucket::from_name(bucket.as_str()), Some(bucket));
    }
    assert_eq!(Bucket::from_name("nope"), None);
}

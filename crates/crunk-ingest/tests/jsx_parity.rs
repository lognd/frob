//! Corpus parity: the JSX sheets of the corpus projects equal what the Python crunk dumps.
//!
//! The reference files are `<name>.jsx.json` next to `projects/`, produced by `dump_jsx.py`
//! from the Python `ingest_tree` (JSX part only). Spans are compared as code-point offsets.
//! `jsx` is a corpus of every shape the Python unit tests cover; `hullbreach_jsx` is the
//! platform's own React tree (7 sheets, 126 utilities).

// frob:ticket 01M43ARYFVG86PAGGM78JGRZY3

mod common;

use std::path::Path;

use common::{same_json, scratch};
use crunk_ingest::{Bucket, Declaration, ProjectStyles, ingest_tree};
use gob_cache::Cache;
use serde_json::{Value, json};

fn rel(root: &Path, p: &Path) -> String {
    p.strip_prefix(root)
        .unwrap()
        .components()
        .map(|c| c.as_os_str().to_string_lossy())
        .collect::<Vec<_>>()
        .join("/")
}

fn chars(source: &str, span: (usize, usize)) -> Value {
    let c = |b: usize| source[..b].chars().count();
    json!([c(span.0), c(span.1)])
}

fn decl(source: &str, d: &Declaration) -> Value {
    json!({
        "prop": d.prop,
        "value": d.value,
        "line": d.line,
        "span": chars(source, d.span),
        "colors": d.colors.iter().map(|c| json!({"hex": c.color.to_hex(), "span": chars(source, c.span)})).collect::<Vec<_>>(),
        "lengths": d.lengths.iter().map(|l| json!({"raw": l.length.raw, "px": l.length.px, "kind": l.length.kind.as_str(), "span": chars(source, l.span)})).collect::<Vec<_>>(),
        "var_refs": d.var_refs.iter().map(|v| json!({"name": v.name, "span": chars(source, v.span)})).collect::<Vec<_>>(),
    })
}

/// The JSX sheets in the shape `dump_jsx.py` writes.
fn dump(root: &Path, styles: &ProjectStyles) -> Value {
    json!({
        "sheets": styles.sheets.iter().filter(|s| s.bucket == Some(Bucket::Jsx)).map(|s| json!({
            "path": rel(root, &s.path),
            "component": s.component,
            "declarations": s.declarations.iter().map(|d| decl(&s.source, d)).collect::<Vec<_>>(),
            "utilities": s.utilities.iter().map(|u| json!({"name": u.name, "line": u.line, "variants": u.variants})).collect::<Vec<_>>(),
        })).collect::<Vec<_>>(),
        "diagnostics": styles.diagnostics.iter()
            .filter(|d| d.path.extension().is_some_and(|e| e == "tsx" || e == "ts" || e == "jsx"))
            .map(|d| json!({"path": rel(root, &d.path)})).collect::<Vec<_>>(),
    })
}

fn reference(name: &str) -> Value {
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures")
        .join(format!("{name}.jsx.json"));
    let mut v: Value = serde_json::from_str(
        &std::fs::read_to_string(&path)
            .unwrap_or_else(|e| panic!("{name}: missing reference (run dump_jsx.py): {e}")),
    )
    .unwrap();
    for d in v["diagnostics"].as_array_mut().unwrap() {
        d.as_object_mut().unwrap().remove("message");
    }
    v
}

/// The differences between Rust's JSX sheets of fixture project `name` and Python's dump.
fn diffs_of(name: &str) -> Vec<String> {
    let (dir, spec) = scratch(name);
    let got = ingest_tree(&spec, &Cache::null()).unwrap();
    let mut diffs = Vec::new();
    same_json(
        "$",
        &dump(dir.path(), &got.styles),
        &reference(name),
        &mut diffs,
    );
    diffs
}

// frob:tests crates/crunk-ingest/src/jsx/project.rs::ingest
#[test]
fn the_platform_react_tree_equals_the_python_dump() {
    let diffs = diffs_of("hullbreach_jsx");
    assert!(diffs.is_empty(), "{}", diffs.join("\n"));
}

// frob:tests crates/crunk-ingest/src/jsx/project.rs::ingest
#[test]
fn the_unit_test_corpus_equals_the_python_dump() {
    let diffs = diffs_of("jsx");
    assert!(diffs.is_empty(), "{}", diffs.join("\n"));
}

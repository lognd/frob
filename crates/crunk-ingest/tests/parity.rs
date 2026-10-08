//! Corpus parity: every fixture project ingests to the facts the Python crunk dumps.
//!
//! The reference files are `<name>.styles.json` next to `projects/`, produced by
//! `dump_ingest.py` from the Python `ingest_tree` (CSS part only). Spans are compared as
//! code-point offsets (the fixtures are ASCII, where they equal byte offsets).

// frob:ticket 01M43ARY91XZ35DN9SCHRHS033

mod common;

use std::path::Path;

use common::{scratch, write};
use crunk_ingest::{Declaration, ProjectStyles, ingest_tree};
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

/// Python read files with universal newlines, so its offsets and values are in LF-normalized
/// text; map byte spans of the byte-exact Rust source into that text.
fn chars(source: &str, span: (usize, usize)) -> Value {
    let c = |b: usize| source[..b].replace("\r\n", "\n").chars().count();
    json!([c(span.0), c(span.1)])
}

fn decl(source: &str, d: &Declaration) -> Value {
    json!({
        "prop": d.prop,
        "value": d.value.replace("\r\n", "\n"),
        "line": d.line,
        "span": chars(source, d.span),
        "waivers": d.waivers.iter().map(|w| json!({"rule": w.rule, "reason": w.reason, "line": w.line})).collect::<Vec<_>>(),
        "colors": d.colors.iter().map(|c| json!({"hex": c.color.to_hex(), "span": chars(source, c.span)})).collect::<Vec<_>>(),
        "lengths": d.lengths.iter().map(|l| json!({"raw": l.length.raw, "px": l.length.px, "kind": l.length.kind.as_str(), "span": chars(source, l.span)})).collect::<Vec<_>>(),
        "var_refs": d.var_refs.iter().map(|v| json!({"name": v.name, "span": chars(source, v.span)})).collect::<Vec<_>>(),
    })
}

/// The Rust styles in the shape `dump_ingest.py` writes.
fn dump(root: &Path, styles: &ProjectStyles) -> Value {
    json!({
        "sheets": styles.sheets.iter().map(|s| json!({
            "path": rel(root, &s.path),
            "bucket": s.bucket.map(crunk_ingest::Bucket::as_str),
            "component": s.component,
            "declarations": s.declarations.iter().map(|d| decl(&s.source, d)).collect::<Vec<_>>(),
            "class_selectors": s.class_selectors.iter().map(|c| json!({"name": c.name, "line": c.line})).collect::<Vec<_>>(),
            "custom_props": s.custom_props.iter().map(|c| json!({"name": c.name, "line": c.line})).collect::<Vec<_>>(),
            "orphan_waivers": s.orphan_waivers.iter().map(|w| json!({"rule": w.rule, "reason": w.reason, "line": w.line})).collect::<Vec<_>>(),
            "media_queries": s.media_queries.iter().map(|m| json!({"prelude": m.prelude, "min_px": m.min_px, "max_px": m.max_px, "line": m.line})).collect::<Vec<_>>(),
        })).collect::<Vec<_>>(),
        "strays": styles.strays.iter().map(|p| rel(root, p)).collect::<Vec<_>>(),
        "diagnostics": styles.diagnostics.iter().map(|d| json!({"path": rel(root, &d.path)})).collect::<Vec<_>>(),
        "ungoverned": styles.ungoverned.iter().map(|p| rel(root, p)).collect::<Vec<_>>(),
    })
}

/// Compare two JSON values, numbers by value with a tolerance.
fn same(path: &str, rust: &Value, python: &Value, diffs: &mut Vec<String>) {
    match (rust, python) {
        (Value::Number(a), Value::Number(b)) => {
            let (a, b) = (a.as_f64().unwrap(), b.as_f64().unwrap());
            if (a - b).abs() > 1e-9 * a.abs().max(1.0) {
                diffs.push(format!("{path}: rust {a} != python {b}"));
            }
        }
        (Value::Object(a), Value::Object(b)) => {
            for key in a.keys().chain(b.keys()) {
                match (a.get(key), b.get(key)) {
                    (Some(x), Some(y)) => same(&format!("{path}.{key}"), x, y, diffs),
                    (Some(x), None) => diffs.push(format!("{path}.{key}: only in rust: {x}")),
                    (None, Some(y)) => diffs.push(format!("{path}.{key}: only in python: {y}")),
                    (None, None) => {}
                }
            }
        }
        (Value::Array(a), Value::Array(b)) => {
            if a.len() != b.len() {
                diffs.push(format!(
                    "{path}: rust len {} != python len {}",
                    a.len(),
                    b.len()
                ));
                return;
            }
            for (i, (x, y)) in a.iter().zip(b).enumerate() {
                same(&format!("{path}[{i}]"), x, y, diffs);
            }
        }
        (a, b) if a == b => {}
        (a, b) => diffs.push(format!("{path}: rust {a} != python {b}")),
    }
}

/// Python's reference output with only the diagnostic paths kept (messages differ by design).
fn reference(name: &str) -> Value {
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures")
        .join(format!("{name}.styles.json"));
    let mut v: Value = serde_json::from_str(
        &std::fs::read_to_string(&path)
            .unwrap_or_else(|e| panic!("{name}: missing reference (run dump_ingest.py): {e}")),
    )
    .unwrap();
    for d in v["diagnostics"].as_array_mut().unwrap() {
        d.as_object_mut().unwrap().remove("message");
    }
    v
}

// frob:tests crates/crunk-ingest/src/walk.rs::ingest_tree
// frob:tests crates/crunk-ingest/src/parse.rs::parse_css_source
// frob:tests crates/crunk-ingest/src/walk.rs::bucket_for
#[test]
fn every_corpus_project_equals_the_python_projectstyles_dump() {
    for name in ["hullbreach", "buckets", "values", "rules", "waivers"] {
        let (dir, spec) = scratch(name);
        if name == "buckets" {
            // Noise the ungoverned walk must skip; kept out of the repo (ignored names).
            write(dir.path(), "node_modules/x/n.css", ".nm { color: red; }");
            write(dir.path(), ".hidden/h.css", ".hid { color: red; }");
            write(dir.path(), "dist/built.css", ".built { color: red; }");
        }
        let got = ingest_tree(&spec, &Cache::null()).unwrap();
        let mut diffs = Vec::new();
        same(
            "$",
            &dump(dir.path(), &got.styles),
            &reference(name),
            &mut diffs,
        );
        assert!(
            diffs.is_empty(),
            "{name} differs from the Python ProjectStyles:\n{}\ndiagnostics: {:?}",
            diffs.join("\n"),
            got.styles.diagnostics
        );
    }
}

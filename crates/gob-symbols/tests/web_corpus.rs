//! The web conformance corpus: one fixture directory per web language (`ts`, `tsx`, `js`, `jsx`,
//! `css`, `html`) with expected symbols, imports, markup, style and digests, plus the capability
//! matrix rows and the generated languages page (language-engines.md section 5, code-model.md
//! section 3, D96, D101). Regenerate expectations with `WEB_CORPUS_UPDATE=1`.

// frob:ticket 01M47QKW1R6KY7K1H6N4M1BX5H

use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use gob_ir::const_value::{ConstValue, Value};
use gob_ir::{Model, markup, style};
use gob_symbols::{SymbolGraph, adapter_for_path, fidelity_report, fold_file, languages_page};
use gob_walk::{Digest, FileEntry, LanguageHint};

/// Web language directory, an extension it holds, and the adapter language that must claim it.
const WEB: [(&str, &str, &str); 6] = [
    ("ts", "ts", "typescript"),
    ("tsx", "tsx", "typescript"),
    ("js", "js", "typescript"),
    ("jsx", "jsx", "typescript"),
    ("css", "css", "css"),
    ("html", "html", "html"),
];

fn corpus() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/corpus/web")
}

fn entry(path: &str, text: &str) -> FileEntry {
    FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    }
}

/// Compares `actual` with the expectation file, rewriting it when `WEB_CORPUS_UPDATE` is set.
fn expect_file(path: &Path, actual: &str) {
    if std::env::var_os("WEB_CORPUS_UPDATE").is_some() {
        std::fs::write(path, actual).expect("write expectation");
        // Also echoed so a remote run (goway) can be copied back by hand.
        println!("@@@FILE {}\n{actual}@@@END", path.display());
        return;
    }
    let want = std::fs::read_to_string(path).unwrap_or_default();
    assert!(
        want == actual,
        "{} differs; actual output follows\n-----\n{actual}\n-----",
        path.display()
    );
}

fn show_value(v: &ConstValue) -> String {
    match v {
        ConstValue::Known(Value::Str(s)) => format!("{s:?}"),
        ConstValue::Known(Value::Bool(b)) => b.to_string(),
        ConstValue::Unknown => "?".to_owned(),
        other => format!("{other:?}"),
    }
}

fn render_markup(model: &Model, out: &mut String) {
    for e in markup::elements(model) {
        let attrs: Vec<String> = e
            .attributes
            .iter()
            .map(|a| match &a.name {
                Some(n) => format!("{n}={}", show_value(&markup::attribute_value(model, a))),
                None => "...spread".to_owned(),
            })
            .collect();
        let _ = writeln!(
            out,
            "element {} {:?} [{}] children={}",
            e.tag.as_deref().unwrap_or("?"),
            e.kind,
            attrs.join(" "),
            e.children.len()
        );
    }
}

fn render_style(model: &Model, out: &mut String) {
    for r in style::style_rules(model) {
        let _ = writeln!(out, "rule {}", r.selector);
    }
    for a in style::at_rules(model) {
        let _ = writeln!(out, "at-rule @{} {}", a.name, a.prelude);
    }
    for d in style::declarations(model) {
        let _ = writeln!(out, "declaration {}: {}", d.property, d.raw);
    }
    for c in style::custom_properties(model) {
        let _ = writeln!(out, "custom-property {}: {}", c.name, c.raw);
    }
    for v in style::var_refs(model) {
        let _ = writeln!(out, "var {} {:?}", v.name, v.status);
    }
}

/// Renders every source file of one fixture directory: file facts, symbols, edges, markup, style.
fn render_dir(lang_dir: &str) -> String {
    let dir = corpus().join(lang_dir);
    let mut names: Vec<String> = std::fs::read_dir(&dir)
        .expect("fixture dir")
        .flatten()
        .map(|e| e.file_name().to_string_lossy().into_owned())
        .filter(|n| n != "expected.txt")
        .collect();
    names.sort();
    assert!(!names.is_empty(), "{lang_dir} has no fixtures");
    let mut folded = Vec::new();
    for n in &names {
        let text = std::fs::read_to_string(dir.join(n)).expect("read fixture");
        let path = format!("web/{lang_dir}/{n}");
        folded.push((
            path.clone(),
            fold_file(&entry(&path, &text), &text).expect("fold"),
        ));
    }
    let models: Vec<Model> = folded
        .iter()
        .map(|(_, f)| Model::new(f.term.clone(), f.scopes.clone()))
        .collect();
    let graph = SymbolGraph::from_files(folded.iter().map(|(_, f)| f.file.clone()).collect());
    let mut out = String::new();
    for ((path, f), model) in folded.iter().zip(&models) {
        let _ = writeln!(
            out,
            "== {path} ==\nlanguage {} fidelity {} status {:?} digest {}",
            f.file.language, f.file.fidelity, f.file.parse_status, f.file.file_digest
        );
        let _ = writeln!(out, "-- symbols --");
        for s in &f.file.symbols {
            let _ = writeln!(out, "{} {:?} {:?}", s.symref, s.kind, s.visibility);
        }
        let _ = writeln!(out, "-- edges --");
        for e in graph
            .edges_with_status()
            .iter()
            .filter(|e| e.from.path() == path.as_str())
        {
            let to =
                e.to.as_ref()
                    .map_or_else(|| "?".to_owned(), ToString::to_string);
            let _ = writeln!(
                out,
                "{:?} {} -> {to} {:?} {:?} {:?}",
                e.kind, e.from, e.status, e.reason, e.name
            );
        }
        let _ = writeln!(out, "-- markup --");
        render_markup(model, &mut out);
        let _ = writeln!(out, "-- style --");
        render_style(model, &mut out);
    }
    out
}

// frob:tests crates/gob-symbols/src/registry.rs::fidelity_report
#[test]
fn every_web_language_has_a_conformance_fixture_directory_matching_its_snapshot() {
    for (dir, ext, language) in WEB {
        let sample = format!("web/{dir}/x.{ext}");
        assert_eq!(
            adapter_for_path(&sample).map(gob_symbols::Adapter::language),
            Some(language),
            "{ext} is claimed by {language}"
        );
        expect_file(&corpus().join(dir).join("expected.txt"), &render_dir(dir));
    }
}

/// The matrix rows of the six web extensions: language, fidelity and every capability cell.
fn render_matrix() -> String {
    let report = fidelity_report();
    let mut out = String::new();
    for (_, ext, language) in WEB {
        let row = report
            .iter()
            .find(|r| r.language == language && r.extensions.contains(&ext))
            .unwrap_or_else(|| panic!("no matrix row claims .{ext}"));
        let cells: Vec<String> = row
            .capabilities
            .iter()
            .map(|(c, p)| format!("{}={}({})", c.name(), p.cell(), p.label()))
            .collect();
        let _ = writeln!(
            out,
            ".{ext} {language} {} {}",
            row.fidelity,
            cells.join(" ")
        );
    }
    out
}

// frob:tests crates/gob-caps/src/capability.rs::Precision.cell
#[test]
fn the_capability_matrix_cells_of_every_web_extension_match_the_snapshot() {
    expect_file(&corpus().join("matrix.txt"), &render_matrix());
}

// frob:tests crates/gob-symbols/src/languages_page.rs::languages_page
#[test]
fn the_generated_languages_page_lists_every_web_extension_and_matches_the_docs_file() {
    let page = languages_page();
    for (_, ext, language) in WEB {
        assert!(
            page.contains(&format!("| `.{ext}` | {language} |")),
            ".{ext} row missing"
        );
    }
    let file = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../docs/reference/languages.md");
    expect_file(&file, &page);
}

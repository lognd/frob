//! The fidelity corpus: one case per universal operator an adapter claims, with
//! the expected U term, scope graph, symrefs and statused edges as insta snapshots
//! (universal-model.md 3.3). Regenerate with `INSTA_UPDATE=always`.

use std::collections::BTreeSet;
use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use gob_symbols::{
    Adapter, Fidelity, MarkdownAdapter, PythonAdapter, RustAdapter, SymbolGraph, fold_file,
};
use gob_walk::{Digest, FileEntry, LanguageHint};

/// Operators the Rust adapter claims at F3; `opaque` is covered by `rust_depth_limit`.
const RUST_CLAIMS: [&str; 12] = [
    "unit", "anon", "ref", "apply", "bind", "group", "lit", "attr", "comment", "region", "phase",
    "hole",
];

/// Operators the Python adapter claims at F2 (binders are unit and `anon` abstractors, not `bind` nodes).
const PYTHON_CLAIMS: [&str; 9] = [
    "unit", "anon", "ref", "apply", "group", "lit", "attr", "comment", "hole",
];

/// Operators the markdown adapter claims at F4.
const MARKDOWN_CLAIMS: [&str; 5] = ["unit", "ref", "apply", "group", "lit"];

fn dir(lang: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/corpus")
        .join(lang)
        .join("ops")
}

fn entry(path: &str, text: &str) -> FileEntry {
    FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    }
}

/// Every markdown file under the corpus `ops` dir, as (repo-style path, text).
fn markdown_siblings() -> Vec<(String, String)> {
    let mut out = Vec::new();
    let mut stack = vec![dir("markdown")];
    while let Some(d) = stack.pop() {
        for e in std::fs::read_dir(&d).expect("read_dir").flatten() {
            let p = e.path();
            if p.is_dir() {
                stack.push(p);
            } else if p.extension().is_some_and(|x| x == "md") {
                let rel = p
                    .strip_prefix(env!("CARGO_MANIFEST_DIR"))
                    .expect("under manifest dir")
                    .to_string_lossy()
                    .replace('\\', "/");
                out.push((rel, std::fs::read_to_string(&p).expect("read")));
            }
        }
    }
    out.sort();
    out
}

/// Renders the term, scope graph, symbols and edges of one corpus source; the
/// graph also holds `siblings` so cross-file links resolve.
fn render(path: &str, text: &str, siblings: &[(String, String)]) -> (String, BTreeSet<String>) {
    let folded = fold_file(&entry(path, text), text).expect("fold");
    let mut tags = BTreeSet::new();
    for id in folded.term.ids() {
        tags.insert(folded.term.operator(id).tag());
    }
    let mut out = String::new();
    let _ = writeln!(
        out,
        "== term ==\n{}",
        folded.term.print_alpha(folded.term.root())
    );
    let _ = writeln!(
        out,
        "== scope graph ==\n{}",
        folded.scopes.canonical_stream()
    );
    let _ = writeln!(
        out,
        "== file ==\nfidelity {} status {:?}",
        folded.file.fidelity, folded.file.parse_status
    );
    let _ = writeln!(out, "== symbols ==");
    for s in &folded.file.symbols {
        let parent = s
            .parent
            .as_ref()
            .map_or_else(String::new, ToString::to_string);
        let _ = writeln!(
            out,
            "{} {:?} {:?} parent={parent}",
            s.symref, s.kind, s.visibility
        );
    }
    let mut all = vec![folded.file];
    for (p, t) in siblings.iter().filter(|(p, _)| p != path) {
        all.push(gob_symbols::extract_file(&entry(p, t), t));
    }
    let g = SymbolGraph::from_files(all);
    let _ = writeln!(out, "== edges ==");
    for e in g
        .edges_with_status()
        .iter()
        .filter(|e| e.from.path() == path)
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
    (out, tags)
}

fn run_corpus(lang: &str, ext: &str, claims: &[&str]) {
    let mut covered = BTreeSet::new();
    for op in claims {
        let src = dir(lang).join(format!("{op}.{ext}"));
        let text = std::fs::read_to_string(&src).unwrap_or_else(|_| {
            panic!("missing corpus case for operator `{op}`: {}", src.display())
        });
        let rel = format!("tests/corpus/{lang}/ops/{op}.{ext}");
        let siblings = if lang == "markdown" {
            markdown_siblings()
        } else {
            Vec::new()
        };
        let (out, tags) = render(&rel, &text, &siblings);
        assert!(
            tags.contains(*op) || tags.iter().any(|t| t.ends_with(&format!(".{op}"))),
            "case `{op}` does not exercise its operator; found {tags:?}"
        );
        insta::assert_snapshot!(format!("{lang}_{op}"), out);
        covered.insert((*op).to_owned());
    }
    assert_eq!(covered.len(), claims.len());
}

// frob:tests crates/gob-symbols/src/adapter.rs::Adapter.fidelity
#[test]
fn rust_corpus_covers_every_claimed_operator() {
    assert_eq!(RustAdapter.fidelity(), Fidelity::F3);
    run_corpus("rust", "rs", &RUST_CLAIMS);
}

// frob:tests crates/gob-symbols/src/adapter.rs::Adapter.fidelity
#[test]
fn python_corpus_covers_every_claimed_operator() {
    assert_eq!(PythonAdapter.fidelity(), Fidelity::F2);
    run_corpus("python", "py", &PYTHON_CLAIMS);
}

#[test]
fn markdown_corpus_covers_every_claimed_operator() {
    assert_eq!(MarkdownAdapter.fidelity(), Fidelity::F4);
    run_corpus("markdown", "md", &MARKDOWN_CLAIMS);
}

#[test]
fn rust_depth_limit_collapses_into_opaque_and_keeps_calls() {
    let depth = RustAdapter::MAX_DEPTH + 40;
    let mut src = String::from("fn deep() { ");
    for _ in 0..depth {
        src.push_str("{ ");
    }
    src.push_str("callee();");
    for _ in 0..depth {
        src.push_str(" }");
    }
    src.push_str(" }\nfn callee() {}\n");
    let folded = fold_file(&entry("d.rs", &src), &src).expect("fold");
    let opaque = folded
        .term
        .ids()
        .filter(|&n| folded.term.operator(n).is_opaque())
        .count();
    assert_eq!(opaque, 1, "one subtree collapses at the depth limit");
    let g = SymbolGraph::from_files(vec![folded.file]);
    assert!(
        g.reach(
            &gob_symbols::Symref::parse("d.rs::deep").unwrap(),
            gob_symbols::EdgeKind::Calls
        )
        .iter()
        .any(|s| s.to_string() == "d.rs::callee"),
        "calls inside a collapsed subtree still become edges"
    );
}

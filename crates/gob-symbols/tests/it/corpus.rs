//! The fidelity corpus: one case per universal operator an adapter claims, with
//! the expected U term, scope graph, symrefs and statused edges as insta snapshots
//! (universal-model.md 3.3). Regenerate with `INSTA_UPDATE=always`.

use std::collections::BTreeSet;
use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use gob_ir::Resolution;
use gob_symbols::{
    Adapter, CSharpAdapter, Fidelity, MarkdownAdapter, PythonAdapter, RustAdapter, SymbolGraph,
    fold_file,
};
use gob_walk::{Digest, FileEntry, LanguageHint};

/// Operators the Rust adapter claims at F3; `opaque` is covered by `rust_depth_limit`.
pub(crate) const RUST_CLAIMS: [&str; 12] = [
    "unit", "anon", "ref", "apply", "bind", "group", "lit", "attr", "comment", "region", "phase",
    "hole",
];

/// Operators the Python adapter claims at F2 (binders are unit and `anon` abstractors, not `bind` nodes).
pub(crate) const PYTHON_CLAIMS: [&str; 9] = [
    "unit", "anon", "ref", "apply", "group", "lit", "attr", "comment", "hole",
];

/// Operators the C# adapter claims at F1 (units, tokens, attributes, comments and holes; no references or calls yet).
pub(crate) const CSHARP_CLAIMS: [&str; 6] = ["unit", "group", "lit", "attr", "comment", "hole"];

/// Operators the markdown adapter claims at F4.
pub(crate) const MARKDOWN_CLAIMS: [&str; 5] = ["unit", "ref", "apply", "group", "lit"];

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

// frob:tests crates/gob-symbols/src/adapter.rs::Adapter.fidelity
#[test]
fn csharp_corpus_covers_every_claimed_operator() {
    assert_eq!(CSharpAdapter.fidelity(), Fidelity::F1);
    run_corpus("csharp", "cs", &CSHARP_CLAIMS);
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

// frob:ticket 01M3ZTAV8SXD9C6G4A42WY14K9
// frob:tests crates/gob-symbols/src/rust.rs::fold_tree
#[test]
fn rust_five_thousand_levels_lower_on_a_small_caller_stack_without_depth_limit() {
    let depth = 5000;
    let mut src = String::from("fn deep() { ");
    for _ in 0..depth {
        src.push_str("{ ");
    }
    src.push_str("callee();");
    for _ in 0..depth {
        src.push_str(" }");
    }
    src.push_str(" }\nfn callee() {}\n");
    let run = std::thread::Builder::new()
        .stack_size(2 << 20)
        .spawn(move || {
            let folded = fold_file(&entry("d.rs", &src), &src).expect("fold");
            let opaque = folded
                .term
                .ids()
                .filter(|&n| folded.term.operator(n).is_opaque())
                .count();
            let segs: usize = folded
                .file
                .symbols
                .iter()
                .map(|s| s.symref.segments().len())
                .sum();
            (opaque, segs, folded.file.symbols.len())
        })
        .unwrap();
    let (opaque, segs, syms) = run.join().expect("no stack overflow");
    assert_eq!(opaque, 0, "no depth-limit collapse at 5000 levels");
    assert!(
        segs <= 2 * syms,
        "symref storage stays flat: {segs} segs for {syms} symbols"
    );
}

/// One oracle site: the `nth` reference spelled `name` (graph order) truly denotes the
/// `decl_nth` declaration spelled `decl` (graph order), or lies outside the file (`None`).
struct Oracle {
    name: &'static str,
    nth: usize,
    truth: Option<(&'static str, usize)>,
}

/// Hypothesis check: every oracle referent lies inside the emitted May set, equals the Must
/// declaration, or the site is Unknown (an external referent must be Unknown).
fn check_oracle(path: &str, text: &str, oracle: &[Oracle]) -> usize {
    let f = fold_file(&entry(path, text), text).expect("fold");
    let decl_of = |name: &str, nth: usize| {
        f.scopes
            .decls()
            .iter()
            .enumerate()
            .filter(|(_, d)| d.name == name)
            .nth(nth)
            .map_or_else(
                || panic!("{path}: no declaration `{name}` #{nth}"),
                |(i, _)| i,
            )
    };
    let mut proven = 0;
    for o in oracle {
        let r = f
            .scopes
            .refs()
            .iter()
            .filter(|r| r.name == o.name)
            .nth(o.nth)
            .unwrap_or_else(|| panic!("{path}: no reference `{}` #{}", o.name, o.nth));
        let id = f
            .scopes
            .ref_at(r.node.expect("term reference has a node"))
            .expect("ref id");
        let res = f.scopes.resolve(id);
        match (&res, o.truth) {
            (Resolution::Unknown, _) => {}
            (_, None) => panic!("{path}: external `{}` resolved to {res:?}", o.name),
            (Resolution::Must(d), Some((dn, dnth))) => {
                assert_eq!(
                    d.index(),
                    decl_of(dn, dnth),
                    "{path}: Must `{}` wrong",
                    o.name
                );
                proven += 1;
            }
            (Resolution::May(set), Some((dn, dnth))) => {
                assert!(
                    set.iter().any(|d| d.index() == decl_of(dn, dnth)),
                    "{path}: May set for `{}` omits the true referent: {set:?}",
                    o.name
                );
                proven += 1;
            }
        }
    }
    proven
}

const fn site(name: &'static str, nth: usize, truth: Option<(&'static str, usize)>) -> Oracle {
    Oracle { name, nth, truth }
}

// frob:tests crates/gob-ir/src/scope.rs::ScopeGraph.resolve
#[test]
fn rust_may_sets_contain_the_true_referent() {
    let src = "pub fn pick(a: u32, b: u32) -> u32 { let c = a + b; let c = c + 1; free_name + c }\n\
               fn g(a: u32) -> u32 { if a > 1 { pick(a, a) } else { a } }";
    let oracle = [
        site("free_name", 0, None),
        site("c", 0, Some(("c", 1))),
        site("c", 1, Some(("c", 0))),
        site("a", 0, Some(("a", 0))),
        site("b", 0, Some(("b", 0))),
        site("a", 1, Some(("a", 1))),
        site("pick", 0, Some(("pick", 0))),
    ];
    assert!(
        check_oracle("o.rs", src, &oracle) >= 5,
        "adapter must not go vacuously Unknown"
    );
}

// frob:tests crates/gob-ir/src/scope.rs::ScopeGraph.resolve
#[test]
fn python_may_sets_contain_the_true_referent() {
    let src = "def f(a):\n    return a\ndef g(a, b):\n    if a:\n        x = f(b)\n    else:\n        x = 2\n    return x + missing\n";
    let oracle = [
        site("a", 0, Some(("a", 0))),
        site("a", 1, Some(("a", 1))),
        site("x", 0, Some(("x", 0))),
        site("f", 0, Some(("f", 0))),
        site("b", 0, Some(("b", 0))),
        site("missing", 0, None),
    ];
    assert!(
        check_oracle("o.py", src, &oracle) >= 4,
        "adapter must not go vacuously Unknown"
    );
}

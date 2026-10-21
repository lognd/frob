//! Measured fidelity (testing.md 5): each adapter's level is derived from what its conformance
// frob:ticket 01M48Q4E637KNAGPTCZQKJ78C2
//! corpus actually exhibits and must equal the declared one, in both directions.

use std::collections::BTreeSet;
use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use gob_ir::Resolution;
use gob_symbols::{Fidelity, SymbolGraph, adapters, fold_file};
use gob_walk::{Digest, FileEntry, LanguageHint};

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/corpus")
}

fn entry(path: &str, text: &str) -> FileEntry {
    FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    }
}

/// Every file under `dir` with one of `exts`, as (repo-style path, text), sorted.
fn files_under(dir: &Path, exts: &[&str]) -> Vec<(String, String)> {
    let mut out = Vec::new();
    let mut stack = vec![dir.to_path_buf()];
    while let Some(d) = stack.pop() {
        let Ok(rd) = std::fs::read_dir(&d) else {
            continue;
        };
        for e in rd.flatten() {
            let p = e.path();
            if p.is_dir() {
                stack.push(p);
            } else if p
                .extension()
                .and_then(gob_path::exact_text)
                .is_some_and(|x| exts.contains(&x))
            {
                let rel = gob_path::Shown::with_home(
                    p.strip_prefix(env!("CARGO_MANIFEST_DIR"))
                        .expect("under manifest dir"),
                    None,
                )
                .to_string()
                .replace('\\', "/");
                out.push((rel, std::fs::read_to_string(&p).expect("read")));
            }
        }
    }
    out.sort();
    out
}

/// The conformance corpus of `lang`: the `ops` cases, or the web fixtures.
fn corpus_of(lang: &str) -> Vec<(String, String)> {
    let r = root();
    match lang {
        "rust" => files_under(&r.join("rust/ops"), &["rs"]),
        "python" => files_under(&r.join("python/ops"), &["py"]),
        "csharp" => files_under(&r.join("csharp/ops"), &["cs"]),
        "markdown" => files_under(&r.join("markdown/ops"), &["md"]),
        "typescript" => files_under(&r.join("web"), &["ts", "tsx", "js", "jsx"]),
        "css" => files_under(&r.join("web/css"), &["css"]),
        "html" => files_under(&r.join("web"), &["html"]),
        "yaml" => vec![(
            "tests/corpus/yaml/a.yaml".to_owned(),
            "# top\nouter:\n  inner: 1\n  other: 2\n".to_owned(),
        )],
        "github-actions" => vec![(
            ".github/workflows/ci.yml".to_owned(),
            "# ci\njobs:\n  build:\n    steps:\n      - uses: actions/checkout@v4\n  test:\n    needs: build\n    steps:\n      - uses: actions/cache@v4\n".to_owned(),
        )],
        "dockerfile" => vec![(
            "Dockerfile".to_owned(),
            "# image\nFROM rust:1.80 AS build\nRUN cargo build\nFROM build AS final\n".to_owned(),
        )],
        _ => Vec::new(),
    }
}

/// What a corpus exhibits, level by level (universal-model.md 3.3).
#[derive(Default)]
#[expect(clippy::struct_excessive_bools, reason = "one flag per evidence kind")]
struct Evidence {
    units: bool,
    containment: bool,
    refs: bool,
    status_edge: bool,
    attrs: bool,
    comments: bool,
    regions: bool,
    phases: bool,
}

impl Evidence {
    /// The highest level whose evidence, and that of every level below it, is present.
    fn level(&self) -> Fidelity {
        let f4 = self.attrs && self.comments && self.regions && self.phases;
        if !self.units || !self.containment {
            Fidelity::F0
        } else if !self.refs {
            Fidelity::F1
        } else if !self.status_edge {
            Fidelity::F2
        } else if !f4 {
            Fidelity::F3
        } else {
            Fidelity::F4
        }
    }
}

/// Folds every corpus file and gathers the evidence of each level.
fn measure(files: &[(String, String)]) -> Evidence {
    let mut ev = Evidence::default();
    let mut all = Vec::new();
    for (p, t) in files {
        let folded = fold_file(&entry(p, t), t).expect("fold");
        let tags: BTreeSet<String> = folded
            .term
            .ids()
            .map(|id| folded.term.operator(id).tag())
            .collect();
        let has = |n: &str| tags.iter().any(|t| t == n || t.ends_with(&format!(".{n}")));
        ev.units |= has("unit");
        ev.attrs |= has("attr");
        ev.comments |= has("comment");
        ev.regions |= has("region");
        ev.phases |= has("phase");
        ev.containment |= folded.term.ids().any(|id| {
            folded.term.node(id).op().is_unit_like()
                && std::iter::successors(folded.term.node(id).parent(), |&p| {
                    folded.term.node(p).parent()
                })
                .any(|p| folded.term.node(p).op().is_unit_like())
        });
        ev.refs |= has("ref")
            || folded
                .scopes
                .refs()
                .iter()
                .filter_map(|r| r.node.and_then(|n| folded.scopes.ref_at(n)))
                .any(|rid| !matches!(folded.scopes.resolve(rid), Resolution::Unknown));
        all.push(folded.file);
    }
    let g = SymbolGraph::from_files(all);
    ev.status_edge = !g.edges_with_status().is_empty();
    ev
}

/// Declared-vs-measured disagreements that predate this gate: (language, declared, measured, ticket).
/// A pin holds only while both levels stay exactly as recorded; the list may only shrink.
const PINNED: [(&str, Fidelity, Fidelity, &str); 2] = [
    ("github-actions", Fidelity::F2, Fidelity::F1, "~DPWJ77V"),
    ("dockerfile", Fidelity::F2, Fidelity::F1, "~DPWJ77V"),
];

/// Errs when `declared` differs from `measured` in either direction, unless pinned exactly.
fn check_declared(lang: &str, declared: Fidelity, measured: Fidelity) -> Result<(), String> {
    if declared == measured {
        if PINNED.iter().any(|p| p.0 == lang) {
            return Err(format!(
                "{lang}: pinned divergence is resolved; remove its pin"
            ));
        }
        return Ok(());
    }
    match PINNED.iter().find(|p| p.0 == lang) {
        Some(&(_, d, m, _)) if d == declared && m == measured => Ok(()),
        _ => Err(format!(
            "{lang}: declared {declared} but the corpus measures {measured}"
        )),
    }
}

// frob:tests crates/gob-symbols/src/adapter.rs::Adapter.fidelity
#[test]
fn every_adapter_declares_the_fidelity_its_corpus_measures() {
    for a in adapters() {
        let measured = measure(&corpus_of(a.language())).level();
        if let Err(e) = check_declared(a.language(), a.fidelity(), measured) {
            panic!("{e}");
        }
    }
}

#[test]
fn promoting_a_declared_fidelity_without_corpus_support_fails() {
    let ev = measure(&corpus_of("csharp"));
    assert_eq!(ev.level(), Fidelity::F1);
    assert!(check_declared("csharp", Fidelity::F2, ev.level()).is_err());
    assert!(check_declared("csharp", Fidelity::F4, ev.level()).is_err());
    assert!(check_declared("csharp", Fidelity::F1, ev.level()).is_ok());
}

#[test]
fn demoting_below_the_measured_level_fails_too() {
    let ev = measure(&corpus_of("css"));
    assert!(check_declared("css", Fidelity::F1, ev.level()).is_err());
}

#[test]
fn a_pin_that_no_longer_matches_fails() {
    // A pin only holds at its exact levels: with none left, any divergence errs.
    assert!(check_declared("html", Fidelity::F3, Fidelity::F0).is_err());
    assert!(check_declared("html", Fidelity::F2, Fidelity::F0).is_err());
}

#[test]
fn dropping_a_corpus_operator_case_lowers_the_measured_level() {
    let full = corpus_of("rust");
    assert_eq!(measure(&full).level(), Fidelity::F4);
    for drop in ["phase", "region"] {
        let kept: Vec<_> = full
            .iter()
            .filter(|(p, _)| !p.ends_with(&format!("/{drop}.rs")))
            .cloned()
            .collect();
        assert!(kept.len() < full.len(), "case `{drop}` exists");
        assert!(
            measure(&kept).level() < Fidelity::F4,
            "dropping `{drop}` must lower the measured level"
        );
    }
}

#[test]
#[should_panic(expected = "has no corpus case")]
fn a_claim_without_its_corpus_case_fails() {
    assert_claims_match_disk("csharp", "cs", &["unit", "no_such_operator"]);
}

/// The ops files on disk and the claim list must name the same operators, so neither a dropped
/// case nor an unclaimed one goes unnoticed.
fn assert_claims_match_disk(lang: &str, ext: &str, claims: &[&str]) {
    let on_disk: BTreeSet<String> = files_under(&root().join(lang).join("ops"), &[ext])
        .into_iter()
        .filter_map(|(p, _)| {
            let rest = p.strip_prefix(&format!("tests/corpus/{lang}/ops/"))?;
            (!rest.contains('/')).then(|| rest.trim_end_matches(&format!(".{ext}")).to_owned())
        })
        .collect();
    let claimed: BTreeSet<String> = claims.iter().map(|c| (*c).to_owned()).collect();
    for c in &claimed {
        assert!(
            on_disk.contains(c),
            "{lang}: claimed operator `{c}` has no corpus case"
        );
    }
    let extra: Vec<_> = on_disk.difference(&claimed).collect();
    // markdown keeps link-target siblings (b.md) next to its cases.
    if lang != "markdown" {
        assert!(extra.is_empty(), "{lang}: unclaimed corpus cases {extra:?}");
    }
}

#[test]
fn corpus_cases_on_disk_match_the_claimed_operators() {
    use super::corpus::{CSHARP_CLAIMS, MARKDOWN_CLAIMS, PYTHON_CLAIMS, RUST_CLAIMS};
    assert_claims_match_disk("rust", "rs", &RUST_CLAIMS);
    assert_claims_match_disk("python", "py", &PYTHON_CLAIMS);
    assert_claims_match_disk("csharp", "cs", &CSHARP_CLAIMS);
    assert_claims_match_disk("markdown", "md", &MARKDOWN_CLAIMS);
}

/// Per-adapter probe inputs: (language, path, a truncated source, garbage source).
const PROBES: [(&str, &str, &str, &str); 10] = [
    (
        "rust",
        "p.rs",
        "fn f( { let x = ;",
        "\u{0}\u{1}}}}{{((( \u{7f} fn ::",
    ),
    (
        "markdown",
        "p.md",
        "# t\n[broken](",
        "\u{0}\u{1}]]]((( ``` \u{7f}",
    ),
    (
        "yaml",
        "p.yaml",
        "a:\n  b: [1, 2\n",
        "\u{0}\u{1}: : [ { \u{7f}",
    ),
    (
        "github-actions",
        ".github/workflows/p.yml",
        "jobs:\n  a:\n    needs: [",
        "\u{0}\u{1}: : [ { \u{7f}",
    ),
    (
        "dockerfile",
        "Dockerfile",
        "FROM rust AS \\\n",
        "\u{0}\u{1} FROM \u{7f} AS",
    ),
    (
        "python",
        "p.py",
        "def f(:\n    return (",
        "\u{0}\u{1})))((( \u{7f} def",
    ),
    (
        "csharp",
        "p.cs",
        "class A { void M( {",
        "\u{0}\u{1}}}}{{((( \u{7f} class",
    ),
    (
        "typescript",
        "p.ts",
        "function f( { const x = ;",
        "\u{0}\u{1}}}}{{((( \u{7f} =>",
    ),
    ("css", "p.css", "a { color: ", "\u{0}\u{1}}}}{{((( \u{7f} @"),
    (
        "html",
        "p.html",
        "<div><span class=",
        "\u{0}\u{1}<<<>>> \u{7f} </",
    ),
];

fn probe(lang: &str) -> (&'static str, &'static str, &'static str) {
    let Some(p) = PROBES.iter().find(|p| p.0 == lang) else {
        panic!("no probe case for adapter `{lang}`")
    };
    (p.1, p.2, p.3)
}

#[test]
fn every_adapter_has_matrix_garbage_and_partial_parse_cases() {
    for a in adapters() {
        let (path, partial, garbage) = probe(a.language());
        for (kind, text) in [("garbage", garbage), ("partial", partial)] {
            let folded = fold_file(&entry(path, text), text)
                .unwrap_or_else(|e| panic!("{} {kind}: fold failed: {e}", a.language()));
            assert!(
                folded.file.fidelity <= a.fidelity(),
                "{} {kind}: never claims more than declared",
                a.language()
            );
            assert!(
                !folded.term.is_empty(),
                "{} {kind}: a term is always produced",
                a.language()
            );
        }
        insta::assert_snapshot!(format!("matrix_{}", a.language()), matrix_of(a));
    }
}

/// The adapter's capability matrix as a stable text block.
fn matrix_of(a: &dyn gob_symbols::Adapter) -> String {
    let mut out = format!("{} {}\n", a.language(), a.fidelity());
    for (c, p) in a.capabilities().rows() {
        let _ = writeln!(out, "{} {} {}", c.name(), p.cell(), p.label());
    }
    out
}

#[test]
fn tree_sitter_adapters_report_a_truncated_source_as_not_complete() {
    for lang in ["rust", "python", "csharp", "typescript"] {
        let (path, partial, _) = probe(lang);
        let f = fold_file(&entry(path, partial), partial).expect("fold");
        assert!(
            !f.file.parse_status.is_complete(),
            "{lang}: truncated source parsed as Complete: {:?}",
            f.file.parse_status
        );
    }
}

#[test]
fn an_adapterless_file_is_f0_and_not_parsed() {
    let text = "key = 1\n";
    let f = fold_file(&entry("a.toml", text), text).expect("fold");
    assert_eq!(f.file.fidelity, Fidelity::F0);
    assert_eq!(f.file.parse_status, gob_symbols::ParseStatus::NotParsed);
    assert_eq!(gob_symbols::opaque_adapter().fidelity(), Fidelity::F0);
}

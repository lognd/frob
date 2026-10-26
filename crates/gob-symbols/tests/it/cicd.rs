//! GitHub Actions and Dockerfile adapters: instantiate and dependency edges (cicd.md section 4).

// frob:ticket 01M3Z71542Y6NZG3G8A83EFRF2

use gob_symbols::{EdgeKind, Fidelity, GapReason, Status, StatusEdge, SymbolGraph, Symref};
use gob_walk::{Digest, FileEntry, LanguageHint};

fn entry(path: &str, text: &str) -> FileEntry {
    FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    }
}

fn graph_of(path: &str, text: &str) -> SymbolGraph {
    SymbolGraph::from_files(vec![gob_symbols::extract_file(&entry(path, text), text)])
}

fn edges(g: &SymbolGraph, kind: EdgeKind) -> Vec<StatusEdge> {
    g.edges_with_status()
        .iter()
        .filter(|e| e.kind == kind)
        .cloned()
        .collect()
}

const SHA: &str = "11bd71901bbe5b1630ceea73d27597364c9af683";

fn workflow() -> String {
    format!(
        "name: ci\non: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      \
         - uses: actions/checkout@v4\n      - uses: actions/cache@{SHA} # v4.2.2\n      \
         - uses: ./local-action\n      - run: |\n          uses: not/a-ref@v1\n  \
         test:\n    needs: build\n    runs-on: ubuntu-latest\n    steps:\n      \
         - uses: actions/setup-node\n  deploy:\n    needs: [build, test, gone]\n    \
         uses: org/repo/.github/workflows/d.yml@main\n"
    )
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.edges_with_status
#[test]
fn tag_pinned_action_is_may_and_sha_pinned_is_must() {
    let g = graph_of(".github/workflows/ci.yml", &workflow());
    let inst = edges(&g, EdgeKind::Instantiates);
    let status_of = |name: &str| {
        inst.iter()
            .find(|e| e.name.as_deref() == Some(name))
            .unwrap_or_else(|| panic!("no instantiate edge for {name}"))
            .status
    };
    assert_eq!(status_of("actions/checkout@v4"), Status::May);
    assert_eq!(status_of(&format!("actions/cache@{SHA}")), Status::Must);
    assert_eq!(status_of("actions/setup-node"), Status::Unknown);
    assert_eq!(
        status_of("org/repo/.github/workflows/d.yml@main"),
        Status::May
    );
    assert_eq!(
        inst.len(),
        4,
        "local actions and block scalars make no edge"
    );
    let floating = inst
        .iter()
        .find(|e| e.status == Status::Unknown)
        .expect("floating edge");
    assert_eq!(floating.reason, Some(GapReason::Floating));
    let checkout = inst
        .iter()
        .find(|e| e.name.as_deref() == Some("actions/checkout@v4"))
        .unwrap();
    assert_eq!(
        checkout.from,
        Symref::parse(".github/workflows/ci.yml::jobs.build").unwrap()
    );
}

// frob:tests crates/gob-symbols/src/actions.rs::ActionsAdapter
#[test]
fn needs_are_dependency_edges_between_jobs() {
    let g = graph_of(".github/workflows/ci.yml", &workflow());
    let deps = edges(&g, EdgeKind::Depends);
    let job = |n: &str| Symref::parse(&format!(".github/workflows/ci.yml::jobs.{n}")).unwrap();
    let resolved: Vec<_> = deps
        .iter()
        .filter(|e| e.status == Status::Must)
        .map(|e| (e.from.clone(), e.to.clone().unwrap()))
        .collect();
    assert!(resolved.contains(&(job("test"), job("build"))));
    assert!(resolved.contains(&(job("deploy"), job("build"))));
    assert!(resolved.contains(&(job("deploy"), job("test"))));
    let gone = deps
        .iter()
        .find(|e| e.status == Status::Unknown)
        .expect("unresolved need");
    assert_eq!(gone.reason, Some(GapReason::Unbound));
}

// frob:tests crates/gob-symbols/src/actions.rs::ActionsAdapter
#[test]
fn workflow_fidelity_is_f2_and_plain_yaml_is_unchanged() {
    let w = gob_symbols::extract_file(&entry(".github/workflows/ci.yml", &workflow()), &workflow());
    assert_eq!(w.fidelity, Fidelity::F2);
    let t = "jobs:\n  a:\n    uses: x/y@v1\n";
    let plain = gob_symbols::extract_file(&entry("other.yml", t), t);
    assert_eq!(plain.fidelity, Fidelity::F1);
    assert!(plain.refs.is_empty());
}

const DOCKERFILE: &str = "ARG V=1\nFROM rust:1.80 AS build\nRUN cargo build \\\n  --release\n\
FROM rust@sha256:abcdef AS pinned\nFROM debian:latest AS rt\n\
COPY --from=build /out /out\nCOPY --from=0 /a /a\nCOPY --from=ghcr.io/x/y:2 /b /b\n\
FROM rt AS final\nFROM scratch\n";

// frob:tests crates/gob-symbols/src/docker_image.rs::DockerfileAdapter
#[test]
fn dockerfile_stages_from_and_copy_edges() {
    let g = graph_of("Dockerfile", DOCKERFILE);
    let stage = |n: &str| Symref::parse(&format!("Dockerfile::{n}")).unwrap();
    for n in ["build", "pinned", "rt", "final", "stage-4"] {
        assert!(g.get(&stage(n)).is_some(), "missing stage {n}");
    }
    let inst = edges(&g, EdgeKind::Instantiates);
    let st = |name: &str| {
        inst.iter()
            .find(|e| e.name.as_deref() == Some(name))
            .unwrap_or_else(|| panic!("no edge {name}"))
            .status
    };
    assert_eq!(st("rust:1.80"), Status::May);
    assert_eq!(st("rust@sha256:abcdef"), Status::Must);
    assert_eq!(st("debian:latest"), Status::Unknown);
    assert_eq!(st("ghcr.io/x/y:2"), Status::May);
    let deps: Vec<_> = edges(&g, EdgeKind::Depends)
        .into_iter()
        .map(|e| (e.from, e.to.unwrap()))
        .collect();
    assert!(deps.contains(&(stage("rt"), stage("build"))));
    assert!(
        deps.contains(&(stage("rt"), stage("build"))),
        "copy by index 0 is build"
    );
    assert!(deps.contains(&(stage("final"), stage("rt"))));
}

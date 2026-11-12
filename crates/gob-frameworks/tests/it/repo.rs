//! The `Repo` reader over a small TypeScript tree: files, texts, exports, name binding and constants.

// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

use std::path::Path;

use gob_frameworks::{Repo, Status};
use gob_ir::const_value::const_value_node;
use gob_symbols::{SymbolGraph, extract_file};
use gob_walk::{Digest, FileEntry, LanguageHint};

const A: &str = "export const PATH = \"/x\";\nexport function handler() {}\n";
const B: &str =
    "import { PATH } from \"./a\";\nconst LOCAL = PATH;\nexport default function main() {}\n";
const INDEX: &str = "export * from \"./a\";\nexport { default } from \"./b\";\n";

fn entry(root: &Path, rel: &str, text: &str) -> FileEntry {
    std::fs::write(root.join(rel), text).expect("write");
    FileEntry {
        language: LanguageHint::from_path(rel),
        path: rel.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
    }
}

fn tree() -> (tempfile::TempDir, Vec<FileEntry>, SymbolGraph) {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    std::fs::write(root.join("package.json"), "{}").expect("manifest");
    let files = vec![
        entry(root, "a.ts", A),
        entry(root, "b.ts", B),
        entry(root, "index.ts", INDEX),
    ];
    let graph = SymbolGraph::from_files(
        files
            .iter()
            .map(|f| extract_file(f, &std::fs::read_to_string(root.join(&f.path)).unwrap()))
            .collect(),
    );
    (dir, files, graph)
}

#[test]
// frob:tests crates/gob-frameworks/src/repo.rs::Repo.files
// frob:tests crates/gob-frameworks/src/repo.rs::Repo.text
// frob:tests crates/gob-frameworks/src/repo.rs::Repo.folded
// frob:tests crates/gob-frameworks/src/repo.rs::Repo.model
// frob:tests crates/gob-frameworks/src/repo.rs::Repo.graph
// frob:tests crates/gob-frameworks/src/repo.rs::Repo.member_sources
fn repo_exposes_what_it_loaded() {
    let (dir, files, graph) = tree();
    let repo = Repo::load(dir.path(), &files, &graph);
    assert!(repo.problems().is_empty());
    assert_eq!(repo.files(), ["a.ts", "b.ts", "index.ts"]);
    assert_eq!(repo.text("a.ts"), Some(A));
    assert!(repo.text("missing.ts").is_none());
    assert!(repo.folded("a.ts").is_some() && repo.folded("missing.ts").is_none());
    assert!(repo.model("a.ts").is_some());
    assert!(repo.graph().files().any(|(f, _)| f == "a.ts"));
    let owned: Vec<&str> = repo.member_sources("package.json").collect();
    assert_eq!(owned, ["a.ts", "b.ts", "index.ts"]);
    assert_eq!(repo.member_sources("other/package.json").count(), 0);
}

#[test]
// frob:tests crates/gob-frameworks/src/repo.rs::Repo.name_ref
// frob:tests crates/gob-frameworks/src/repo.rs::Repo.bound_unit
// frob:tests crates/gob-frameworks/src/repo.rs::Repo.resolve_module
// frob:tests crates/gob-frameworks/src/repo.rs::Repo.export_targets
fn names_bind_to_units_and_exports_follow_reexports() {
    let (dir, files, graph) = tree();
    let repo = Repo::load(dir.path(), &files, &graph);
    assert_eq!(repo.name_ref("a.ts", "handler"), "a.ts::handler");
    assert_eq!(repo.name_ref("a.ts", "nope"), "nope");
    assert_eq!(
        repo.bound_unit("b.ts", "PATH").as_deref(),
        Some("a.ts::PATH")
    );
    assert!(repo.bound_unit("b.ts", "nope").is_none());
    assert_eq!(repo.resolve_module("b.ts", "./a").as_deref(), Some("a.ts"));
    assert!(repo.resolve_module("b.ts", "./zzz").is_none());
    assert_eq!(
        repo.export_targets("index.ts", "handler", 0),
        [("a.ts::handler".to_owned(), Status::Must)]
    );
    assert_eq!(
        repo.export_targets("index.ts", "default", 0),
        [("b.ts::main".to_owned(), Status::Must)]
    );
    assert!(repo.export_targets("index.ts", "handler", 99).is_empty());
}

#[test]
// frob:tests crates/gob-frameworks/src/repo.rs::Repo.line
// frob:tests crates/gob-frameworks/src/repo.rs::Repo.follow
// frob:tests crates/gob-frameworks/src/repo.rs::Repo.strings
fn constants_are_followed_across_files_and_lines_are_one_based() {
    let (dir, files, graph) = tree();
    let repo = Repo::load(dir.path(), &files, &graph);
    let model = repo.model("b.ts").expect("model");
    let local = model
        .term()
        .units()
        .into_iter()
        .find(|u| u.symref.to_string() == "b.ts::LOCAL")
        .expect("LOCAL unit");
    let value = const_value_node(model, local.node).expect("value node");
    let (file, node) = repo.follow("b.ts", value).expect("followed");
    assert_eq!(file, "a.ts");
    assert_eq!(
        repo.strings(&file, node),
        Some((vec!["/x".to_owned()], Status::Must))
    );
    assert_eq!(repo.line("b.ts", value), 2);
    assert_eq!(repo.line("missing.ts", value), 1);
}

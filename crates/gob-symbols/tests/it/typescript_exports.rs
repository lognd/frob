//! The public TypeScript export resolver: own declarations, named and star re-exports, and the documented limits.

// frob:ticket 01M5GGJXDV139FW9WX0JR8RKNQ

use gob_symbols::{Status, SymbolGraph, extract_file};
use gob_walk::{Digest, FileEntry, LanguageHint};

fn graph(files: &[(&str, &str)]) -> SymbolGraph {
    SymbolGraph::from_files(
        files
            .iter()
            .map(|(p, s)| {
                let e = FileEntry {
                    path: (*p).to_owned(),
                    size: s.len() as u64,
                    digest: Digest::of(s.as_bytes()),
                    language: LanguageHint::from_path(p),
                };
                extract_file(&e, s)
            })
            .collect(),
    )
}

fn targets(g: &SymbolGraph, path: &str, name: &str) -> Vec<(String, Status)> {
    g.ts_export_targets(path, name)
        .into_iter()
        .map(|(s, st)| (s.to_string(), st))
        .collect()
}

#[test]
// frob:tests crates/gob-symbols/src/graph/typescript.rs::SymbolGraph.ts_export_targets
fn exports_resolve_through_named_and_star_reexports() {
    let g = graph(&[
        ("a.ts", "export function GET() {}\n"),
        ("mid.ts", "export { GET as READ } from \"./a\";\n"),
        ("all.ts", "export * from \"./a\";\n"),
        ("pkg.ts", "export { x } from \"some-pkg\";\n"),
    ]);
    assert_eq!(
        targets(&g, "a.ts", "GET"),
        [("a.ts::GET".to_owned(), Status::Must)]
    );
    assert_eq!(
        targets(&g, "mid.ts", "READ"),
        [("a.ts::GET".to_owned(), Status::Must)]
    );
    let star = targets(&g, "all.ts", "GET");
    assert_eq!(star.len(), 1);
    assert_eq!(star[0].0, "a.ts::GET");
    assert!(targets(&g, "pkg.ts", "x").is_empty());
    assert!(targets(&g, "a.ts", "nope").is_empty());
    assert!(targets(&g, "missing.ts", "GET").is_empty());
}

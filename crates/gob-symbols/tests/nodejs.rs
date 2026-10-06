//! The Node project model end to end: workspaces, tsconfig aliases and externals resolve TypeScript imports
//! (language-engines.md section 2, `project_model`, D96).

// frob:ticket 01M47QKTN549397AFFSC3DEAQX

use std::path::Path;

use gob_symbols::{
    Capability, CrateDeps, EdgeKind, FileSymbols, GapReason, Precision, Status, StatusEdge,
    SymbolGraph, extract_file, fidelity_report, is_typescript_path,
};
use gob_walk::{Digest, FileEntry, LanguageHint};

fn write(root: &Path, files: &[(&str, &str)]) {
    for (path, text) in files {
        let full = root.join(path);
        std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
        std::fs::write(full, text).expect("write");
    }
}

fn fold(path: &str, src: &str) -> FileSymbols {
    extract_file(
        &FileEntry {
            path: path.to_owned(),
            size: src.len() as u64,
            digest: Digest::of(src.as_bytes()),
            language: LanguageHint::from_path(path),
        },
        src,
    )
}

/// Writes `files`, folds every source file and builds the graph with the project model.
fn build(files: &[(&str, &str)]) -> (SymbolGraph, tempfile::TempDir) {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), files);
    let folded: Vec<FileSymbols> = files
        .iter()
        .filter(|(p, _)| is_typescript_path(p))
        .map(|(p, s)| fold(p, s))
        .collect();
    let mut deps = CrateDeps::new(dir.path());
    (SymbolGraph::from_files_with_deps(folded, &mut deps), dir)
}

fn import_edges<'g>(g: &'g SymbolGraph, from: &str, spec: &str) -> Vec<&'g StatusEdge> {
    g.edges_with_status()
        .iter()
        .filter(|e| {
            e.kind == EdgeKind::Imports && e.from.path() == from && e.name.as_deref() == Some(spec)
        })
        .collect()
}

fn module_target(g: &SymbolGraph, from: &str, spec: &str) -> Option<String> {
    import_edges(g, from, spec)
        .iter()
        .find_map(|e| e.to.as_ref().map(|t| t.path().to_owned()))
}

const MONOREPO: [(&str, &str); 12] = [
    (
        "package.json",
        r#"{ "name": "root", "private": true, "workspaces": ["packages/*"], "devDependencies": { "typescript": "5" } }"#,
    ),
    (
        "tsconfig.base.json",
        r#"{ "compilerOptions": { "baseUrl": ".", "paths": { "@lib/*": ["packages/lib/src/*"], "~/*": ["packages/app/src/*"] } } }"#,
    ),
    (
        "packages/lib/package.json",
        r#"{ "name": "@acme/lib", "main": "dist/index.js", "types": "dist/index.d.ts", "dependencies": { "lodash": "4" } }"#,
    ),
    (
        "packages/lib/src/index.ts",
        "export function greet(): string { return 'hi'; }\n",
    ),
    (
        "packages/lib/src/util/strings.ts",
        "export function up(s: string): string { return s; }\n",
    ),
    (
        "packages/app/package.json",
        r#"{ "name": "@acme/app", "dependencies": { "@acme/lib": "*", "react": "18" } }"#,
    ),
    (
        "packages/app/tsconfig.json",
        r#"{
  // comments and trailing commas are legal here
  "extends": "../../tsconfig.base.json",
  "include": ["src"],
}"#,
    ),
    (
        "packages/app/src/main.ts",
        "import { greet } from '@acme/lib';\nimport { up } from '@lib/util/strings';\nimport { local } from '~/local';\nimport React from 'react';\nimport fs from 'node:fs';\nimport path from 'path';\nimport { nope } from 'not-declared';\nexport function main() { greet(); up('x'); local(); }\n",
    ),
    (
        "packages/app/src/local.ts",
        "export function local(): void {}\n",
    ),
    (
        "packages/lib/src/deep.ts",
        "import { local } from '@lib/missing';\nimport { g } from '@acme/app';\nexport const x = 1;\n",
    ),
    ("packages/app/src/extra.ts", "export {};\n"),
    ("packages/app/README.md", "x\n"),
];

// frob:tests crates/gob-symbols/src/graph/typescript.rs::SymbolGraph.link_typescript_imports
#[test]
fn monorepo_workspace_alias_and_external_imports_resolve() {
    let (g, _dir) = build(&MONOREPO);
    let main = "packages/app/src/main.ts";
    // The workspace package resolves through `main`/`types` in `dist`, found under `src`.
    assert_eq!(
        module_target(&g, main, "@acme/lib").as_deref(),
        Some("packages/lib/src/index.ts")
    );
    // A `paths` alias inherited through `extends` (baseUrl is the repo root).
    assert_eq!(
        module_target(&g, main, "@lib/util/strings").as_deref(),
        Some("packages/lib/src/util/strings.ts")
    );
    assert_eq!(
        module_target(&g, main, "~/local").as_deref(),
        Some("packages/app/src/local.ts")
    );
    // Dependencies, installed-or-declared packages and builtins are external, never dropped.
    for ext in ["react", "node:fs", "path"] {
        let e = import_edges(&g, main, ext);
        assert_eq!(e.len(), 1, "{ext}: {e:?}");
        assert_eq!(
            (e[0].status, e[0].reason),
            (Status::Unknown, Some(GapReason::External))
        );
    }
    // Symbol-level edges follow the alias to the declaring unit.
    assert_eq!(
        import_edges(&g, main, "greet")
            .iter()
            .map(|e| e.status)
            .collect::<Vec<_>>(),
        [Status::Must]
    );
    // Calls through the resolved imports are Must.
    assert!(g.edges_with_status().iter().any(|e| {
        e.kind == EdgeKind::Calls
            && e.to
                .as_ref()
                .is_some_and(|t| t.to_string() == "packages/lib/src/index.ts::greet")
            && e.status == Status::Must
    }));
}

// frob:tests crates/gob-symbols/src/graph/typescript.rs::SymbolGraph.link_typescript_imports
#[test]
fn unresolvable_specifiers_stay_unknown_and_unbound() {
    let (g, _dir) = build(&MONOREPO);
    let main = "packages/app/src/main.ts";
    let undeclared = import_edges(&g, main, "not-declared");
    assert_eq!(undeclared.len(), 1);
    assert_eq!(
        (undeclared[0].status, undeclared[0].reason),
        (Status::Unknown, Some(GapReason::Unbound))
    );
    // An alias that matches no file, and a workspace package the lib does not declare a dependency on
    // (it still resolves: a monorepo links every member), are accounted for.
    let deep = "packages/lib/src/deep.ts";
    let missing = import_edges(&g, deep, "@lib/missing");
    assert_eq!(
        missing
            .iter()
            .map(|e| (e.status, e.reason))
            .collect::<Vec<_>>(),
        [(Status::Unknown, Some(GapReason::Unbound))]
    );
    assert_eq!(import_edges(&g, deep, "@acme/app").len(), 1);
    // Every import of every file has an edge: nothing is dropped.
    let (graph, _) = build(&MONOREPO);
    for f in ["packages/app/src/main.ts", deep] {
        let n = graph
            .edges_with_status()
            .iter()
            .filter(|e| e.kind == EdgeKind::Imports && e.from.path() == f)
            .count();
        assert!(n >= 2, "{f} has {n} import edges");
    }
}

// frob:tests crates/gob-symbols/src/nodejs.rs::NodeProjects.resolve
#[test]
fn exports_maps_imports_maps_and_package_edges() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        &[
            (
                "pnpm-workspace.yaml",
                "packages:\n  - 'libs/*'\n  - '!libs/skip'\n",
            ),
            ("package.json", r#"{ "name": "root" }"#),
            (
                "libs/a/package.json",
                r##"{ "name": "a", "dependencies": { "b": "*" }, "imports": { "#int/*": "./src/int/*.ts" } }"##,
            ),
            ("libs/a/src/x.ts", "export {};\n"),
            (
                "libs/b/package.json",
                r#"{ "name": "b", "exports": { ".": { "types": "./src/main.ts", "default": "./dist/main.js" }, "./feat/*": "./src/feat/*.ts", "./hidden": null } }"#,
            ),
            ("libs/b/src/main.ts", "export {};\n"),
            ("libs/skip/package.json", r#"{ "name": "skip" }"#),
            ("libs/bad/package.json", "{ not json"),
        ],
    );
    let mut deps = CrateDeps::new(dir.path());
    assert_eq!(
        deps.crate_of("libs/a/src/x.ts").as_deref(),
        Some("libs/a/package.json")
    );
    assert_eq!(
        deps.package_name("libs/a/package.json").as_deref(),
        Some("a")
    );
    assert_eq!(
        deps.transitive_deps("libs/a/package.json"),
        ["libs/b/package.json"]
    );
    assert!(deps.can_reach("libs/a/package.json", "libs/b/package.json"));
    assert!(!deps.can_reach("libs/b/package.json", "libs/a/package.json"));
    let root = deps.js_resolve("libs/a/src/x.ts", "b");
    assert_eq!(root.candidates[0], "libs/b/src/main.ts");
    let feat = deps.js_resolve("libs/a/src/x.ts", "b/feat/one");
    assert_eq!(feat.candidates, ["libs/b/src/feat/one.ts"]);
    assert!(
        deps.js_resolve("libs/a/src/x.ts", "b/hidden")
            .candidates
            .is_empty()
    );
    let alias = deps.js_resolve("libs/a/src/x.ts", "#int/y");
    assert_eq!(alias.candidates, ["libs/a/src/int/y.ts"]);
    // A negated workspace pattern removes the member; it is not a package of the workspace.
    let skip = deps.js_resolve("libs/a/src/x.ts", "skip");
    assert!(skip.candidates.is_empty() && !skip.external);
    // A malformed package.json is reported and keeps its package Unresolved.
    let bad = deps.malformed_projects(&["libs/bad/package.json", "libs/a/package.json"]);
    assert_eq!(bad.len(), 1);
    assert_eq!(bad[0].path, "libs/bad/package.json");
    assert!(deps.can_reach("libs/bad/package.json", "libs/a/package.json"));
}

// frob:tests crates/gob-symbols/src/nodejs.rs::NodeProjects.config_for
#[test]
fn solution_style_tsconfig_references_and_paths_replace_inherited_ones() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        &[
            ("package.json", r#"{ "name": "web" }"#),
            (
                "tsconfig.json",
                r#"{ "files": [], "references": [{ "path": "./tsconfig.app.json" }] }"#,
            ),
            (
                "tsconfig.app.json",
                r#"{ "extends": "./tsconfig.shared.json", "compilerOptions": { "paths": { "@/*": ["./src/*"] } }, "include": ["src"] }"#,
            ),
            (
                "tsconfig.shared.json",
                r#"{ "compilerOptions": { "paths": { "old/*": ["./old/*"] } } }"#,
            ),
            ("src/a.ts", "export {};\n"),
            ("scripts/b.ts", "export {};\n"),
        ],
    );
    let mut deps = CrateDeps::new(dir.path());
    assert_eq!(
        deps.js_resolve("src/a.ts", "@/lib/x").candidates,
        ["src/lib/x"]
    );
    assert!(deps.js_resolve("src/a.ts", "old/x").candidates.is_empty());
    // `scripts/` is not in any config's include, so no alias applies there.
    assert!(
        deps.js_resolve("scripts/b.ts", "@/lib/x")
            .candidates
            .is_empty()
    );
}

// frob:tests crates/gob-caps/src/capability.rs::Capability.name
#[test]
fn doctor_reports_the_project_model_rows() {
    let report = fidelity_report();
    for lang in ["rust", "csharp", "typescript"] {
        let row = report.iter().find(|a| a.language == lang).expect(lang);
        assert!(
            row.capabilities
                .contains(&(Capability::ProjectModel, Precision::Manifest)),
            "{lang}: {:?}",
            row.capabilities
        );
    }
    assert_eq!(Capability::ProjectModel.name(), "project_model");
    assert_eq!(Precision::Manifest.label(), "manifest");
}

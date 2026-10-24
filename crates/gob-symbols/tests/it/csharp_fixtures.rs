//! The .NET solution and Unity-shaped C# fixtures: symbols, imports, calls and test ids against snapshots.

// frob:ticket 01M44YQVN6PMK0D8NJ801ENJEW

use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use gob_symbols::{
    CrateDeps, FileSymbols, UnityAssignment, UnityProjects, csharp_test, extract_file,
};
use gob_walk::{Digest, FileEntry, LanguageHint};

fn fixture_dir(name: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/corpus/csharp")
        .join(name)
}

fn entry(path: &str, text: &str) -> FileEntry {
    FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    }
}

// frob:ticket 01M5PC8M49F53YSPKKT7XXMDFH
/// Every `.cs` file under one fixture root as (repo-relative path, text), sorted.
fn sources(name: &str) -> Vec<(String, String)> {
    let root = fixture_dir(name);
    let mut out = Vec::new();
    let mut stack = vec![root.clone()];
    while let Some(d) = stack.pop() {
        for e in std::fs::read_dir(&d).expect("read_dir").flatten() {
            let p = e.path();
            if p.is_dir() {
                stack.push(p);
            } else if p.extension().is_some_and(|x| x == "cs") {
                let rel = gob_path::exact_text(p.strip_prefix(&root).expect("under fixture"))
                    .expect("utf8 fixture path")
                    // Snapshots are `/`-separated; a Windows host path would use `\\`.
                    .replace('\\', "/");
                out.push((rel, std::fs::read_to_string(&p).expect("read")));
            }
        }
    }
    out.sort();
    out
}

/// A stable text rendering of symbols, imports, calls and test ids for every file of a fixture.
fn render(name: &str) -> String {
    let mut out = String::new();
    for (path, text) in sources(name) {
        let fs: FileSymbols = extract_file(&entry(&path, &text), &text);
        let _ = writeln!(out, "== {path} ({:?})", fs.parse_status);
        for s in &fs.symbols {
            let _ = writeln!(out, "symbol {:?} {}", s.kind, s.symref);
        }
        for i in &fs.imports {
            let _ = writeln!(out, "import {}", i.target);
        }
        for c in &fs.calls {
            let _ = writeln!(
                out,
                "call {} -> {}{}",
                c.caller,
                c.qualifier
                    .as_deref()
                    .map_or(String::new(), |q| format!("{q}.")),
                c.callee
            );
        }
        for s in &fs.symbols {
            if let Some(t) = csharp_test(s, &text) {
                let _ = writeln!(
                    out,
                    "test {} {:?} play_mode={}",
                    t.id, t.framework, t.play_mode_capable
                );
            }
        }
    }
    out
}

#[test]
// frob:tests crates/gob-symbols/src/csharp.rs::fold_tree
fn the_dotnet_solution_fixture_matches_its_snapshot() {
    insta::assert_snapshot!(render("solution"));
}

#[test]
// frob:tests crates/gob-symbols/src/csharp.rs::fold_tree
fn the_unity_fixture_matches_its_snapshot() {
    insta::assert_snapshot!(render("unity"));
}

#[test]
// frob:tests crates/gob-symbols/src/csharp.rs::csharp_test
fn the_fixture_tests_carry_nunit_xunit_and_unity_ids() {
    let text = render("solution") + &render("unity");
    for id in [
        "test Acme.NUnitTests.WidgetTests.Describe_ShoutsTheName NUnit",
        "test Acme.XUnitTests.StringsTests.Shout_AppendsBang XUnit",
        "test Game.PlayTests.MoverTests.Mover_AdvancesOverFrames NUnit play_mode=true",
    ] {
        assert!(text.contains(id), "missing {id}\n{text}");
    }
}

// frob:tests crates/gob-symbols/src/crates.rs::CrateDeps.transitive_deps
#[test]
fn the_solution_fixture_has_two_projects_and_a_reference_edge() {
    let mut deps = CrateDeps::new(&fixture_dir("solution"));
    assert_eq!(
        deps.solution_packages("Acme.sln"),
        ["src/App/App.csproj", "src/Lib/Lib.csproj"]
    );
    assert_eq!(
        deps.transitive_deps("src/App/App.csproj"),
        ["src/Lib/Lib.csproj"]
    );
}

// frob:tests crates/gob-symbols/src/unity_project.rs::UnityProjects.assign
#[test]
fn the_unity_fixture_has_an_asmdef_pair() {
    let mut p = UnityProjects::new(&fixture_dir("unity"));
    assert_eq!(
        p.assign("Assets/Scripts/Mover.cs"),
        UnityAssignment::Assembly("Assets/Scripts/Game.Runtime.asmdef".to_owned())
    );
    assert_eq!(
        p.assign("Assets/Tests/PlayMode/MoverTests.cs"),
        UnityAssignment::Assembly("Assets/Tests/PlayMode/Game.PlayTests.asmdef".to_owned())
    );
}

//! The Unity project model end to end: asmdef packages, GUID references, asmref folders and the implicit assemblies.

// frob:ticket 01M44YQWGP5553K61QKC8HB0GQ

use std::path::Path;

use gob_symbols::{CrateDeps, UnityAssignment, UnityProjects, UnityTestMode};

fn write(root: &Path, files: &[(&str, &str)]) {
    for (path, text) in files {
        let full = root.join(path);
        std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
        std::fs::write(full, text).expect("write");
    }
}

/// The strings of `ids` as a sorted vector.
fn sorted<const N: usize>(ids: [&str; N]) -> Vec<String> {
    let mut v: Vec<String> = ids.iter().map(|s| (*s).to_owned()).collect();
    v.sort();
    v
}

fn meta(guid: &str) -> String {
    format!(
        "fileFormatVersion: 2\nguid: {guid}\nAssemblyDefinitionImporter:\n  externalObjects: {{}}\n"
    )
}

const CORE_GUID: &str = "11111111111111111111111111111111";
const CORE: &str =
    r#"{ "name": "Game.Core", "references": ["Unity.Mathematics"], "autoReferenced": true }"#;
const RUNTIME: &str = r#"{ "name": "Game.Runtime", "references": ["Game.Core"], "defineConstraints": [], "allowUnsafeCode": true }"#;
const EDITOR: &str = r#"{ "name": "Game.Editor", "references": ["GUID:11111111111111111111111111111111", "Game.Runtime"], "includePlatforms": ["Editor"] }"#;
const EDIT_TESTS: &str = r#"{ "name": "Game.Tests", "references": ["Game.Runtime", "Game.Editor", "UnityEngine.TestRunner", "UnityEditor.TestRunner"], "includePlatforms": ["Editor"], "overrideReferences": true, "precompiledReferences": ["nunit.framework.dll"], "autoReferenced": false, "defineConstraints": ["UNITY_INCLUDE_TESTS"] }"#;
const PLAY_TESTS: &str = r#"{ "name": "Game.PlayTests", "references": ["Game.Runtime", "UnityEngine.TestRunner"], "autoReferenced": false, "defineConstraints": ["UNITY_INCLUDE_TESTS"] }"#;

fn project(root: &Path) {
    write(
        root,
        &[
            (
                "ProjectSettings/ProjectVersion.txt",
                "m_EditorVersion: 6000.0.43f1\n",
            ),
            ("Assets/Scripts/Core/Game.Core.asmdef", CORE),
            (
                "Assets/Scripts/Core/Game.Core.asmdef.meta",
                &meta(CORE_GUID),
            ),
            ("Assets/Scripts/Core/Math.cs", "class M {}"),
            ("Assets/Scripts/Core/Deep/Deeper.cs", "class D {}"),
            ("Assets/Scripts/Runtime/Game.Runtime.asmdef", RUNTIME),
            (
                "Assets/Scripts/Runtime/Game.Runtime.asmdef.meta",
                &meta("22222222222222222222222222222222"),
            ),
            ("Assets/Scripts/Runtime/Hero.cs", "class H {}"),
            ("Assets/Editor/Tools/Game.Editor.asmdef", EDITOR),
            ("Assets/Editor/Tools/Window.cs", "class W {}"),
            (
                "Assets/Tests/EditMode/Game.Tests/Game.Tests.asmdef",
                EDIT_TESTS,
            ),
            (
                "Assets/Tests/EditMode/Game.Tests/HeroTests.cs",
                "class T {}",
            ),
            (
                "Assets/Tests/PlayMode/Game.PlayTests/Game.PlayTests.asmdef",
                PLAY_TESTS,
            ),
            ("Assets/Tests/PlayMode/Game.PlayTests/Loop.cs", "class L {}"),
            ("Assets/Loose/Free.cs", "class F {}"),
            ("Assets/Loose/Editor/Menu.cs", "class E {}"),
            ("Assets/Plugins/Lib.cs", "class P {}"),
            ("Assets/Plugins/Editor/Ext.cs", "class X {}"),
            ("Assets/.Hidden/Skip.cs", "class S {}"),
            ("Assets/Cache~/Skip.cs", "class S {}"),
            ("tools/vendor/Vendored.asmdef", r#"{ "name": "Vendored" }"#),
            ("tools/.deps/Hidden.asmdef", r#"{ "name": "Hidden" }"#),
            ("Library/Bee/Gen.cs", "class G {}"),
            ("Temp/Gen.cs", "class G {}"),
        ],
    );
}

const CORE_ID: &str = "Assets/Scripts/Core/Game.Core.asmdef";
const RUNTIME_ID: &str = "Assets/Scripts/Runtime/Game.Runtime.asmdef";
const EDITOR_ID: &str = "Assets/Editor/Tools/Game.Editor.asmdef";
const EDIT_ID: &str = "Assets/Tests/EditMode/Game.Tests/Game.Tests.asmdef";
const PLAY_ID: &str = "Assets/Tests/PlayMode/Game.PlayTests/Game.PlayTests.asmdef";

// frob:tests crates/gob-symbols/src/unity_project.rs::UnityProjects.references
#[test]
fn each_asmdef_is_a_package_with_referenced_by_edges_and_test_modes() {
    let dir = tempfile::tempdir().expect("tempdir");
    project(dir.path());
    let mut u = UnityProjects::new(dir.path());
    assert!(u.is_unity_project());
    assert_eq!(
        u.assemblies(),
        sorted([EDITOR_ID, CORE_ID, RUNTIME_ID, EDIT_ID, PLAY_ID])
    );
    assert_eq!(u.references(RUNTIME_ID), [CORE_ID]);
    assert_eq!(u.references(EDITOR_ID), [CORE_ID, RUNTIME_ID]);
    assert_eq!(u.referenced_by(CORE_ID), [EDITOR_ID, RUNTIME_ID]);
    assert_eq!(u.referenced_by(RUNTIME_ID), [EDITOR_ID, EDIT_ID, PLAY_ID]);
    let core = u.assembly(CORE_ID).expect("known").expect("parsed");
    assert_eq!(core.external, ["Unity.Mathematics"]);
    assert_eq!(core.guid.as_deref(), Some(CORE_GUID));
    let runtime = u.assembly(RUNTIME_ID).expect("known").expect("parsed");
    assert!(runtime.allow_unsafe_code && runtime.auto_referenced && !runtime.is_test());
    let editor = u.assembly(EDITOR_ID).expect("known").expect("parsed");
    assert!(editor.editor_only());
    assert_eq!(editor.test_mode(), None);
    let edit = u.assembly(EDIT_ID).expect("known").expect("parsed");
    assert!(edit.is_test() && edit.override_references && !edit.auto_referenced);
    assert_eq!(edit.precompiled_references, ["nunit.framework.dll"]);
    assert_eq!(edit.test_mode(), Some(UnityTestMode::EditMode));
    let play = u.assembly(PLAY_ID).expect("known").expect("parsed");
    assert_eq!(play.test_mode(), Some(UnityTestMode::PlayMode));
    assert!(u.findings(&[CORE_ID, RUNTIME_ID, EDITOR_ID]).is_empty());
    let mut deps = CrateDeps::new(dir.path());
    assert_eq!(deps.transitive_deps(EDITOR_ID), [CORE_ID, RUNTIME_ID]);
    assert!(deps.file_can_reach(
        "Assets/Editor/Tools/Window.cs",
        "Assets/Scripts/Core/Math.cs"
    ));
    assert!(!deps.file_can_reach(
        "Assets/Scripts/Core/Math.cs",
        "Assets/Scripts/Runtime/Hero.cs"
    ));
}

// frob:tests crates/gob-symbols/src/unity_project.rs::UnityProjects.findings
#[test]
fn a_guid_reference_resolves_through_the_meta_and_an_unknown_guid_is_a_finding() {
    let dir = tempfile::tempdir().expect("tempdir");
    project(dir.path());
    write(
        dir.path(),
        &[
            (
                "Assets/Bad/Game.Bad.asmdef",
                r#"{ "name": "Game.Bad", "references": ["GUID:deadbeef", "guid:11111111111111111111111111111111"] }"#,
            ),
            ("Assets/Bad/X.cs", "class X {}"),
            ("Assets/Broken/Broken.asmdef", "{ not json"),
        ],
    );
    let mut deps = CrateDeps::new(dir.path());
    let bad = "Assets/Bad/Game.Bad.asmdef";
    assert_eq!(deps.unity().references(bad), [CORE_ID]);
    let found = deps.malformed_projects(&[bad, "Assets/Broken/Broken.asmdef", CORE_ID]);
    assert_eq!(found.len(), 2, "{found:?}");
    assert_eq!(found[0].path, bad);
    assert!(
        found[0].reason.contains("GUID:deadbeef"),
        "{}",
        found[0].reason
    );
    assert_eq!(found[1].path, "Assets/Broken/Broken.asmdef");
    assert!(found[1].reason.contains("malformed"));
    // Unresolved packages are never ruled out of reach.
    assert!(deps.file_can_reach("Assets/Bad/X.cs", "Assets/Scripts/Runtime/Hero.cs"));
    assert!(deps.file_can_reach("Assets/Scripts/Runtime/Hero.cs", "Assets/Bad/X.cs"));
    assert!(deps.file_can_reach("Assets/Broken/Broken.cs", "Assets/Scripts/Core/Math.cs"));
}

// frob:tests crates/gob-symbols/src/unity_project.rs::UnityProjects.assign
#[test]
fn an_asmref_adds_its_folder_to_the_assembly() {
    let dir = tempfile::tempdir().expect("tempdir");
    project(dir.path());
    write(
        dir.path(),
        &[
            (
                "Assets/Extra/Part.asmref",
                r#"{ "reference": "Game.Runtime" }"#,
            ),
            ("Assets/Extra/Part.cs", "class P {}"),
            ("Assets/Extra/Sub/Part2.cs", "class P2 {}"),
            (
                "Assets/ByGuid/Part.asmref",
                r#"{ "reference": "GUID:11111111111111111111111111111111" }"#,
            ),
            ("Assets/ByGuid/G.cs", "class G {}"),
            ("Assets/Dangling/Part.asmref", r#"{ "reference": "Nope" }"#),
            ("Assets/Dangling/D.cs", "class D {}"),
        ],
    );
    let mut u = UnityProjects::new(dir.path());
    let id = |s: &str| UnityAssignment::Assembly(s.to_owned());
    assert_eq!(u.assign("Assets/Extra/Part.cs"), id(RUNTIME_ID));
    assert_eq!(u.assign("Assets/Extra/Sub/Part2.cs"), id(RUNTIME_ID));
    assert_eq!(u.assign("Assets/ByGuid/G.cs"), id(CORE_ID));
    assert_eq!(u.assign("Assets/Dangling/D.cs"), UnityAssignment::None);
    let found = u.findings(&["Assets/Dangling/Part.asmref", "Assets/Extra/Part.asmref"]);
    assert_eq!(found.len(), 1);
    assert!(found[0].reason.contains("unresolved asmref target Nope"));
}

// frob:tests crates/gob-symbols/src/unity_project.rs::UnityProjects.assign
#[test]
fn files_outside_any_asmdef_belong_to_the_assembly_csharp_family() {
    let dir = tempfile::tempdir().expect("tempdir");
    project(dir.path());
    let mut u = UnityProjects::new(dir.path());
    let id = |s: &str| UnityAssignment::Assembly(format!("unity:{s}"));
    assert_eq!(u.assign("Assets/Loose/Free.cs"), id("Assembly-CSharp"));
    assert_eq!(
        u.assign("Assets/Loose/Editor/Menu.cs"),
        id("Assembly-CSharp-Editor")
    );
    assert_eq!(
        u.assign("Assets/Plugins/Lib.cs"),
        id("Assembly-CSharp-firstpass")
    );
    assert_eq!(
        u.assign("Assets/Plugins/Editor/Ext.cs"),
        id("Assembly-CSharp-Editor-firstpass")
    );
    assert_eq!(
        u.assign("Assets/Scripts/Core/Deep/Deeper.cs"),
        UnityAssignment::Assembly(CORE_ID.to_owned())
    );
    for ignored in [
        "Library/Bee/Gen.cs",
        "Temp/Gen.cs",
        "Assets/.Hidden/Skip.cs",
        "Assets/Cache~/Skip.cs",
    ] {
        assert_eq!(u.assign(ignored), UnityAssignment::Ignored, "{ignored}");
    }
    assert_eq!(u.assign("tools/other/x.cs"), UnityAssignment::None);
    let mut deps = CrateDeps::new(dir.path());
    assert_eq!(
        deps.crate_of("Assets/Loose/Free.cs").as_deref(),
        Some("unity:Assembly-CSharp")
    );
    assert_eq!(
        deps.package_name("unity:Assembly-CSharp").as_deref(),
        Some("Assembly-CSharp")
    );
    // Assembly-CSharp sees every auto-referenced asmdef, not the test assemblies.
    let mut seen = deps.transitive_deps("unity:Assembly-CSharp");
    seen.sort();
    assert_eq!(
        seen,
        sorted([
            EDITOR_ID,
            CORE_ID,
            RUNTIME_ID,
            "unity:Assembly-CSharp-firstpass"
        ])
    );
    assert_eq!(deps.crate_of("Library/Bee/Gen.cs"), None);
    assert!(deps.file_can_reach("Library/Bee/Gen.cs", "Assets/Loose/Free.cs"));
}

#[test]
fn a_plain_dotnet_repository_is_untouched() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        &[
            ("App.csproj", "<Project Sdk=\"Microsoft.NET.Sdk\"/>"),
            ("Program.cs", "class P {}"),
        ],
    );
    let mut deps = CrateDeps::new(dir.path());
    assert_eq!(deps.crate_of("Program.cs").as_deref(), Some("App.csproj"));
    assert!(!deps.unity().is_unity_project());
}

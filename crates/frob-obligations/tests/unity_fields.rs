//! The opt-in `unity` pack: serialized fields have an external writer (~9QK3N9A).

mod common;

use frob_obligations::{collect, never_written_fields};

// frob:ticket 01M44YQY6KR3NCCNGKJ9QK3N9A
const ENABLED: &str = "[[packs.enable]]\nname = \"unity\"\n";
const GATED: &str = "[[packs.enable]]\nname = \"unity\"\npaths = [\"Assets/Game/**\"]\n";

/// Names of the never-written fields of a tree holding `files` (plus `config` as frob.toml).
fn never_written(config: Option<&str>, files: &[(&str, &str)]) -> Vec<String> {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(dir.path(), files);
    if let Some(c) = config {
        common::write_tree(dir.path(), &[("frob.toml", c)]);
    }
    let collected = collect(dir.path()).expect("collect");
    never_written_fields(dir.path(), &collected.graph)
        .iter()
        .map(ToString::to_string)
        .collect()
}

fn has(found: &[String], name: &str) -> bool {
    found.iter().any(|s| s.ends_with(name))
}

const SERIALIZED: &str = "using UnityEngine;\npublic class Hero : MonoBehaviour\n{\n    [SerializeField] private int speed;\n    [NonSerialized] public int cache;\n    private int plain;\n}\n";

#[test]
fn serialize_field_has_an_external_writer_when_enabled() {
    // frob:tests never_written_fields
    // frob:tests engine_derived_types
    let found = never_written(Some(ENABLED), &[("Assets/Game/Hero.cs", SERIALIZED)]);
    assert!(!has(&found, "Hero.speed"), "{found:?}");
}

#[test]
fn non_serialized_public_field_is_still_reported() {
    // frob:tests never_written_fields
    let found = never_written(Some(ENABLED), &[("Assets/Game/Hero.cs", SERIALIZED)]);
    assert!(has(&found, "Hero.cache"), "{found:?}");
    assert!(has(&found, "Hero.plain"), "{found:?}");
}

#[test]
fn disabled_pack_reports_serialize_field() {
    // frob:tests never_written_fields
    for config in [None, Some("[project]\nname = \"x\"\n")] {
        let found = never_written(config, &[("Assets/Game/Hero.cs", SERIALIZED)]);
        assert!(has(&found, "Hero.speed"), "{found:?}");
    }
}

#[test]
fn public_fields_of_engine_types_are_written_transitively() {
    // frob:tests never_written_fields
    let src = "public class Base : MonoBehaviour { }\npublic class Mid : Base { public int a; }\npublic partial class Split { public int c; }\npublic class Plain { public int b; }\npublic class Host : MonoBehaviour { public class Inner { public int d; } }\n";
    let found = never_written(
        Some(ENABLED),
        &[
            ("Assets/Game/T.cs", src),
            (
                "Assets/Game/Split2.cs",
                "public partial class Split : ScriptableObject { }\n",
            ),
        ],
    );
    assert!(!has(&found, "Mid.a"), "{found:?}");
    assert!(!has(&found, "Split.c"), "partial parts merge: {found:?}");
    assert!(has(&found, "Plain.b"), "{found:?}");
    assert!(has(&found, "Inner.d"), "nested does not inherit: {found:?}");
}

#[test]
fn field_targeted_serialize_field_on_auto_property() {
    // frob:tests never_written_fields
    let src = "public class Hero : MonoBehaviour\n{\n    [field: SerializeField] public int Hp { get; private set; }\n    public int Mp { get; set; }\n}\n";
    let found = never_written(Some(ENABLED), &[("Assets/Game/Hero.cs", src)]);
    assert!(!has(&found, "Hero.Hp"), "{found:?}");
    assert!(
        !has(&found, "Hero.Mp"),
        "plain properties are not candidates: {found:?}"
    );
}

#[test]
fn static_const_and_readonly_are_not_serialized() {
    // frob:tests never_written_fields
    let src = "public class Hero : MonoBehaviour\n{\n    [SerializeField] static int s;\n    [SerializeField] readonly int r;\n    public static int t;\n}\n";
    let found = never_written(Some(ENABLED), &[("Assets/Game/Hero.cs", src)]);
    for n in ["Hero.s", "Hero.r", "Hero.t"] {
        assert!(has(&found, n), "{n} in {found:?}");
    }
}

#[test]
fn assigned_fields_are_not_reported_even_when_disabled() {
    // frob:tests never_written_fields
    let src = "public class Hero\n{\n    int a;\n    int b;\n    int c = 3;\n    int d;\n    void Go() { a = 1; b++; }\n}\n";
    let found = never_written(None, &[("Assets/Game/Hero.cs", src)]);
    assert!(
        !has(&found, "Hero.a") && !has(&found, "Hero.b") && !has(&found, "Hero.c"),
        "{found:?}"
    );
    assert!(has(&found, "Hero.d"), "{found:?}");
}

#[test]
fn paths_outside_the_pack_globs_are_still_reported() {
    // frob:tests never_written_fields
    let found = never_written(
        Some(GATED),
        &[
            ("Assets/Game/Hero.cs", SERIALIZED),
            ("Assets/Other/Foe.cs", &SERIALIZED.replace("Hero", "Foe")),
        ],
    );
    assert!(!has(&found, "Hero.speed"), "{found:?}");
    assert!(has(&found, "Foe.speed"), "{found:?}");
}

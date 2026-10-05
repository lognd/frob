//! The C# adapter end to end: a small Unity-shaped repo folded and linked into the graph.

use std::path::{Path, PathBuf};

use gob_symbols::{
    Adapter, CSharpAdapter, EdgeKind, Fidelity, FileSymbols, ParseStatus, SymbolGraph, SymbolKind,
    Symref, Visibility, adapter_for_path, extract_file,
};
use gob_walk::{Digest, FileEntry, LanguageHint};

fn repo_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/corpus/csharp/repo")
}

fn entry(path: &str, text: &str) -> FileEntry {
    FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    }
}

/// Every fixture file extracted under its repo-relative path.
fn files() -> Vec<FileSymbols> {
    let mut out = Vec::new();
    let mut stack = vec![repo_dir()];
    while let Some(d) = stack.pop() {
        for e in std::fs::read_dir(&d).expect("read_dir").flatten() {
            let p = e.path();
            if p.is_dir() {
                stack.push(p);
                continue;
            }
            let rel = p
                .strip_prefix(repo_dir())
                .expect("under repo")
                .to_string_lossy()
                .replace('\\', "/");
            let text = std::fs::read_to_string(&p).expect("read");
            out.push(extract_file(&entry(&rel, &text), &text));
        }
    }
    out.sort_by(|a, b| a.path.cmp(&b.path));
    out
}

fn graph() -> SymbolGraph {
    SymbolGraph::from_files(files())
}

fn sym(s: &str) -> Symref {
    Symref::parse(s).expect("symref")
}

fn extract(path: &str, text: &str) -> FileSymbols {
    extract_file(&entry(path, text), text)
}

fn file<'a>(fs: &'a [FileSymbols], path: &str) -> &'a FileSymbols {
    fs.iter().find(|f| f.path == path).expect("fixture file")
}

const KINDS: &str = "Assets/Scripts/Kinds.cs";
const SHIP: &str = "Assets/Scripts/ShipController.cs";
const EDITOR: &str = "Assets/Editor/HudPrefabBuilder.cs";
const GAPS: &str = "Assets/Scripts/Gaps.cs";

#[test]
// frob:tests crates/gob-symbols/src/csharp.rs::fold_tree
fn namespaces_types_and_members_are_units_with_kinds() {
    let fs = files();
    let got: Vec<(String, SymbolKind)> = file(&fs, KINDS)
        .symbols
        .iter()
        .map(|s| {
            (
                s.symref.to_string().replace(&format!("{KINDS}::"), ""),
                s.kind,
            )
        })
        .collect();
    let want: Vec<(&str, SymbolKind)> = vec![
        ("Hullbreach", SymbolKind::Namespace),
        ("Hullbreach.Core", SymbolKind::Namespace),
        ("Hullbreach.Core.BlockKey", SymbolKind::Record),
        ("Hullbreach.Core.IShip", SymbolKind::Interface),
        ("Hullbreach.Core.IShip.Hull", SymbolKind::Property),
        ("Hullbreach.Core.IShip.Repair", SymbolKind::Method),
        ("Hullbreach.Core.BlockType", SymbolKind::Enum),
        ("Hullbreach.Core.BlockType.Core", SymbolKind::Variant),
        ("Hullbreach.Core.BlockType.Hull", SymbolKind::Variant),
        ("Hullbreach.Core.BlockType.Debug", SymbolKind::Variant),
        ("Hullbreach.Core.Hit", SymbolKind::Delegate),
        ("Hullbreach.Core.Grid", SymbolKind::Class),
        ("Hullbreach.Core.Grid.Size", SymbolKind::Const),
        ("Hullbreach.Core.Grid.this", SymbolKind::Indexer),
        ("Hullbreach.Core.Grid.operator+", SymbolKind::Operator),
        (
            "Hullbreach.Core.Grid.operator-implicit[int]",
            SymbolKind::Operator,
        ),
        ("Hullbreach.Core.Grid.~Grid", SymbolKind::Method),
        ("Hullbreach.Core.Grid.$cctor", SymbolKind::Constructor),
        ("Hullbreach.Core.Grid.Grid", SymbolKind::Constructor),
        ("Hullbreach.Core.Grid.Dispose", SymbolKind::Method),
        ("Hullbreach.Core.Grid.Total", SymbolKind::Method),
        ("Hullbreach.Core.Grid.Total.Sum", SymbolKind::Function),
    ];
    let want: Vec<(String, SymbolKind)> =
        want.into_iter().map(|(n, k)| (n.to_owned(), k)).collect();
    assert_eq!(got, want);
    assert!(file(&fs, KINDS).parse_status.is_complete());
}

#[test]
// frob:tests crates/gob-symbols/src/csharp.rs::fold_tree
fn fields_events_and_properties_carry_visibility_and_declarators() {
    let fs = files();
    let ship = file(&fs, SHIP);
    let vis = |n: &str| {
        ship.symbols
            .iter()
            .find(|s| s.symref.to_string() == format!("{SHIP}::Hullbreach.Game.{n}"))
            .unwrap_or_else(|| panic!("no unit {n}"))
    };
    assert_eq!(vis("AuthoredBlock.typeId").kind, SymbolKind::Field);
    assert_eq!(vis("AuthoredBlock.modifiers").kind, SymbolKind::Field);
    assert_eq!(vis("ShipController.body").visibility, Visibility::Private);
    assert_eq!(vis("ShipController.Lives").kind, SymbolKind::Property);
    assert_eq!(vis("ShipController.Destroyed").kind, SymbolKind::Event);
    assert_eq!(vis("ShipController.Awake").visibility, Visibility::Private);
    assert_eq!(vis("ShipController.Thrust").visibility, Visibility::Public);
    assert_eq!(
        vis("ShipController.Thrust.Scale").kind,
        SymbolKind::Function
    );
    assert_eq!(
        vis("ShipController")
            .parent
            .as_ref()
            .map(ToString::to_string),
        Some(format!("{SHIP}::Hullbreach.Game"))
    );
}

#[test]
// frob:tests crates/gob-symbols/src/model.rs::merge_partials
fn a_partial_class_over_two_files_is_one_unit_with_two_spans() {
    let g = graph();
    let kept = sym("Assets/Scripts/Ship.Part1.cs::Hullbreach.Game.Ship");
    let dropped = sym("Assets/Scripts/Ship.Part2.cs::Hullbreach.Game.Ship");
    assert!(g.get(&kept).is_some());
    assert!(
        g.get(&dropped).is_none(),
        "the later part is not a unit of its own"
    );
    let facts = &g.extras(&kept).expect("extras").facts;
    let spans: Vec<&str> = facts.spans.iter().map(|s| s.path.as_str()).collect();
    assert_eq!(
        spans,
        [
            "Assets/Scripts/Ship.Part1.cs",
            "Assets/Scripts/Ship.Part2.cs"
        ]
    );
    assert_eq!(facts.bases, ["IShip", "Component"]);
    let attrs: Vec<&str> = facts.attributes.iter().map(|a| a.name.as_str()).collect();
    assert_eq!(attrs, ["Serializable", "Obsolete"]);
    // The member declared in the second file hangs under the merged unit.
    let damage = g
        .get(&sym(
            "Assets/Scripts/Ship.Part2.cs::Hullbreach.Game.Ship.Damage",
        ))
        .expect("member of part two");
    assert_eq!(damage.parent.as_ref(), Some(&kept));
    assert!(
        g.reach(&kept, EdgeKind::Contains)
            .iter()
            .any(|s| s.to_string().ends_with("Ship.Damage"))
    );
    assert!(
        g.reach(&kept, EdgeKind::Contains)
            .iter()
            .any(|s| s.to_string().ends_with("Ship.Repair"))
    );
}

#[test]
// frob:tests crates/gob-symbols/src/model.rs::merge_partials
fn a_change_in_any_part_changes_the_merged_digest() {
    let part1 =
        std::fs::read_to_string(repo_dir().join("Assets/Scripts/Ship.Part1.cs")).expect("read");
    let part2 =
        std::fs::read_to_string(repo_dir().join("Assets/Scripts/Ship.Part2.cs")).expect("read");
    let digest = |p2: &str| {
        let g = SymbolGraph::from_files(vec![
            extract("a/Ship.Part1.cs", &part1),
            extract("a/Ship.Part2.cs", p2),
        ]);
        g.get(&sym("a/Ship.Part1.cs::Hullbreach.Game.Ship"))
            .expect("merged")
            .digests
            .body
    };
    let base = digest(&part2);
    assert_eq!(base, digest(&part2), "stable");
    assert_ne!(
        base,
        digest(&part2.replace("Hull -= amount;", "Hull -= amount * 2;"))
    );
}

#[test]
// frob:tests crates/gob-symbols/src/csharp.rs::Fold.attributes
fn attributes_keep_names_arguments_and_targets() {
    let fs = files();
    let attrs = |path: &str, tail: &str| {
        let f = file(&fs, path);
        let i = f
            .symbols
            .iter()
            .position(|s| s.symref.to_string().ends_with(tail))
            .unwrap_or_else(|| panic!("no unit {tail}"));
        f.extras[i]
            .facts
            .attributes
            .iter()
            .map(|a| (a.name.clone(), a.args.clone(), a.target.clone()))
            .collect::<Vec<_>>()
    };
    assert_eq!(
        attrs(EDITOR, "RebuildDefaultHudPrefabsMenuItem"),
        [(
            "MenuItem".to_owned(),
            "\"Hullbreach/UI/Rebuild default HUD prefabs\"".to_owned(),
            None
        )]
    );
    let field = attrs(SHIP, "ShipController.thrustPerBlock");
    assert_eq!(
        field.iter().map(|a| a.0.as_str()).collect::<Vec<_>>(),
        ["Header", "Tooltip", "SerializeField"]
    );
    assert_eq!(field[0].1, "\"Tuning\"");
    assert_eq!(
        attrs(SHIP, "ShipController.Lives"),
        [(
            "SerializeField".to_owned(),
            String::new(),
            Some("field".to_owned())
        )]
    );
    assert_eq!(
        attrs(
            "Assets/Tests/UndoStackTests.cs",
            "UndoStackTests.Undo_TenDeep_RestoresExactBlocks"
        ),
        [("Test".to_owned(), String::new(), None)]
    );
    assert_eq!(
        attrs(SHIP, "Hullbreach.Game.ShipController")[1],
        (
            "RequireComponent".to_owned(),
            "typeof(Rigidbody2D)".to_owned(),
            None
        )
    );
}

#[test]
// frob:tests crates/gob-symbols/src/csharp.rs::Fold.make_unit
fn an_attribute_change_changes_only_the_attr_and_sig_digests() {
    let a = extract("A.cs", "class C { [Obsolete] void M() { } }");
    let b = extract("A.cs", "class C { [Obsolete(\"x\")] void M() { } }");
    let (ma, mb) = (&a.symbols[1], &b.symbols[1]);
    assert_ne!(ma.digests.attr, mb.digests.attr);
    assert_ne!(ma.digests.sig, mb.digests.sig);
    assert_eq!(ma.digests.body, mb.digests.body);
}

#[test]
// frob:tests crates/gob-symbols/src/csharp.rs::Fold.conditional
fn both_branches_of_an_if_yield_units_and_carry_their_condition() {
    let fs = files();
    let f = file(&fs, EDITOR);
    let cond = |sym_tail: &str| {
        let i = f
            .symbols
            .iter()
            .position(|s| s.symref.to_string().ends_with(sym_tail))
            .unwrap_or_else(|| panic!("no unit {sym_tail}"));
        f.extras[i].facts.conditions.clone()
    };
    assert_eq!(cond("Editor.HudPrefabBuilder"), ["UNITY_EDITOR"]);
    assert_eq!(cond("HudPrefabBuilder.Run"), ["UNITY_EDITOR"]);
    assert_eq!(cond("Editor.HudPrefabBuilder[dup2]"), ["!(UNITY_EDITOR)"]);
    assert_eq!(cond("HudPrefabBuilder.Build[dup2]"), ["!(UNITY_EDITOR)"]);
    // A conditional member list keeps its units: the enum member under `#if` is still there.
    let kinds = file(&fs, KINDS);
    let i = kinds
        .symbols
        .iter()
        .position(|s| s.symref.to_string().ends_with("BlockType.Debug"))
        .expect("conditional variant");
    assert_eq!(kinds.extras[i].facts.conditions, ["UNITY_EDITOR"]);
    assert!(f.parse_status.is_complete());
}

#[test]
// frob:tests crates/gob-symbols/src/csharp.rs::Fold.conditional
fn elif_and_else_branches_negate_the_earlier_conditions() {
    let f = extract(
        "A.cs",
        "class C {\n#if A\n void One() {}\n#elif B\n void Two() {}\n#else\n void Three() {}\n#endif\n}\n",
    );
    let conds: Vec<(String, Vec<String>)> = f
        .symbols
        .iter()
        .zip(&f.extras)
        .map(|(s, e)| (s.symref.to_string(), e.facts.conditions.clone()))
        .collect();
    assert_eq!(conds[1], ("A.cs::C.One".to_owned(), vec!["A".to_owned()]));
    assert_eq!(
        conds[2],
        (
            "A.cs::C.Two".to_owned(),
            vec!["!(A)".to_owned(), "B".to_owned()]
        )
    );
    assert_eq!(
        conds[3],
        (
            "A.cs::C.Three".to_owned(),
            vec!["!(A)".to_owned(), "!(B)".to_owned()]
        )
    );
}

#[test]
// frob:tests crates/gob-symbols/src/csharp.rs::Fold.tr
fn a_conditional_inside_a_member_body_is_unresolved_for_that_member_only() {
    let fs = files();
    let f = file(&fs, GAPS);
    assert!(matches!(f.parse_status, ParseStatus::Partial { .. }));
    let unknown = |tail: &str| {
        let i = f
            .symbols
            .iter()
            .position(|s| s.symref.to_string().ends_with(tail))
            .expect("unit");
        f.extras[i].unknown.clone()
    };
    assert!(unknown("WithConditional.Pick").contains(&"body".to_owned()));
    assert!(unknown("WithConditional.Stable").is_empty());
    // Pick still exists as a unit: nothing is dropped.
    assert_eq!(f.symbols.len(), 3);
}

#[test]
// frob:tests crates/gob-symbols/src/csharp.rs::Fold.members
fn top_level_statements_are_unmodelled_and_the_gate_reads_partial() {
    let g = graph();
    let info = g.file_info(GAPS).expect("file info");
    assert!(!info.parse_status.is_complete());
    assert_eq!(info.fidelity, Fidelity::F1);
    assert!(matches!(
        info.parse_status,
        ParseStatus::Partial { holes: 2 }
    ));
    let clean = g.file_info(SHIP).expect("file info");
    assert!(clean.parse_status.is_complete());
}

#[test]
// frob:tests crates/gob-symbols/src/csharp.rs::Fold.hole
fn a_syntax_error_is_a_hole_never_a_clean_file() {
    let f = extract("A.cs", "class C { void M( { } }\nclass D { }\n");
    assert!(matches!(f.parse_status, ParseStatus::Partial { .. }));
    assert!(f.symbols.iter().any(|s| s.symref.to_string() == "A.cs::D"));
}

#[test]
// frob:tests crates/gob-symbols/src/csharp.rs::fold_tree
fn comments_and_layout_never_change_digests() {
    let a = extract("A.cs", "class C {\n  void M() { var x = 1; }\n}\n");
    let b = extract(
        "A.cs",
        "class C {\n  // note\n  void M()\n  {\n    var   x = 1; // trailing\n  }\n}\n",
    );
    let c = extract("A.cs", "class C { void M() { var x = 2; } }");
    assert_eq!(a.symbols[1].digests.body, b.symbols[1].digests.body);
    assert_eq!(a.symbols[1].digests.sig, b.symbols[1].digests.sig);
    assert_ne!(a.symbols[1].digests.body, c.symbols[1].digests.body);
}

#[test]
// frob:tests crates/gob-symbols/src/csharp.rs::Fold.namespace_chain
fn block_namespaces_nest_and_siblings_share_no_parent() {
    let f = extract(
        "A.cs",
        "namespace A.B { class X {} }\nnamespace C { class Y {} }\n",
    );
    let names: Vec<String> = f.symbols.iter().map(|s| s.symref.to_string()).collect();
    assert_eq!(
        names,
        [
            "A.cs::A",
            "A.cs::A.B",
            "A.cs::A.B.X",
            "A.cs::C",
            "A.cs::C.Y"
        ]
    );
    assert_eq!(
        f.symbols[2]
            .parent
            .as_ref()
            .map(ToString::to_string)
            .as_deref(),
        Some("A.cs::A.B")
    );
}

#[test]
// frob:tests crates/gob-symbols/src/csharp.rs::Fold.type_unit
fn base_types_are_facts_on_the_type_unit() {
    let f = extract(
        "A.cs",
        "class C<T> : Base, IFoo<int> where T : class { }\nrecord R(int X) : Base(X);\n",
    );
    assert_eq!(f.extras[0].facts.bases, ["Base", "IFoo<int>"]);
    assert_eq!(f.extras[1].facts.bases, ["Base"]);
}

#[test]
// frob:tests crates/gob-symbols/src/csharp.rs::visibility_of
fn accessibility_follows_keywords_and_container_defaults() {
    let f = extract(
        "A.cs",
        "class A { int a; public int b; protected int c; internal int d; private protected int e; }\ninterface I { void M(); }\npublic class P { }\n",
    );
    let v: Vec<(String, Visibility)> = f
        .symbols
        .iter()
        .map(|s| (s.symref.to_string().replace("A.cs::", ""), s.visibility))
        .collect();
    assert_eq!(v[0], ("A".to_owned(), Visibility::Crate));
    assert_eq!(v[1].1, Visibility::Private);
    assert_eq!(v[2].1, Visibility::Public);
    assert_eq!(v[3].1, Visibility::Public);
    assert_eq!(v[4].1, Visibility::Crate);
    assert_eq!(v[5].1, Visibility::Crate);
    assert_eq!(v[6], ("I".to_owned(), Visibility::Crate));
    assert_eq!(v[7].1, Visibility::Public);
    assert_eq!(v[8].1, Visibility::Public);
}

#[test]
// frob:tests crates/gob-symbols/src/registry.rs::adapter_for_path
fn cs_files_are_claimed_by_the_csharp_adapter() {
    let a = adapter_for_path("Assets/Scripts/Player.CS").expect("adapter");
    assert_eq!(a.language(), "csharp");
    assert_eq!(a.fidelity(), Fidelity::F1);
    assert_eq!(CSharpAdapter.language(), "csharp");
    assert!(gob_symbols::is_csharp_path("x/Y.cs"));
    assert!(!gob_symbols::is_csharp_path("x/Y.csx"));
}

#[test]
// frob:tests crates/gob-symbols/src/csharp.rs::Fold.collapse
fn deep_nesting_collapses_and_loses_no_unit_silently() {
    let depth = 400;
    let mut src = String::from("class C { void M() { ");
    src.push_str(&"{ ".repeat(depth));
    src.push_str("void Local() {}");
    src.push_str(&" }".repeat(depth));
    src.push_str(" } }\n");
    let f = extract("A.cs", &src);
    assert!(
        matches!(f.parse_status, ParseStatus::Partial { .. }),
        "a unit under the cap is reported"
    );
    let plain = format!(
        "class C {{ void M() {{ {} int x; {} }} }}\n",
        "{ ".repeat(depth),
        " }".repeat(depth)
    );
    let g = extract("A.cs", &plain);
    assert!(
        g.parse_status.is_complete(),
        "units-free depth collapses cleanly"
    );
}

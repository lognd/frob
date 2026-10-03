//! Model-level behaviour: include order, glob expansion, extension identity, the gob-symbols adapter.

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3

use gob_languages::ParseLimits;
use gob_symbols::{Adapter, Capability, Fidelity, FileInput, ParseStatus, Precision};
use grimble_model::adapter::{GrmbAdapter, fold_text};
use grimble_model::fold::fold_file;
use grimble_model::model::{ModelFiles, load_roots};
use grimble_model::parse::parse_file;
use grimble_model::rules::check_model;

const H: &str = "grimble = \"2\";\nmodule m;\n";
const P: &str = "grimble = \"2\";\npart of m;\n";

fn messages(mf: &ModelFiles) -> Vec<(String, String)> {
    let mut v: Vec<(String, String)> = check_model(mf)
        .into_iter()
        .map(|f| (f.rule.to_string(), f.message))
        .collect();
    v.sort();
    v
}

#[test]
// frob:tests crates/grimble-model/src/model.rs::ModelFiles.new
fn duplicate_entities_are_reported_independent_of_include_order() {
    let a = format!("{P}node dup : trusted {{\n}}\n");
    let b = format!("{P}node dup : trusted {{\n}}\n");
    let ab = ModelFiles::new()
        .with_file(
            "root.grmb",
            format!("{H}include \"a.grmb\";\ninclude \"b.grmb\";\n"),
        )
        .with_file("a.grmb", a.clone())
        .with_file("b.grmb", b.clone());
    let ba = ModelFiles::new()
        .with_file(
            "root.grmb",
            format!("{H}include \"b.grmb\";\ninclude \"a.grmb\";\n"),
        )
        .with_file("a.grmb", a)
        .with_file("b.grmb", b);
    let first = messages(&ab);
    assert_eq!(first.len(), 1, "{first:?}");
    assert_eq!(first[0].0, "MDL001");
    assert_eq!(
        first,
        messages(&ba),
        "the first in (path, byte) order is kept whatever the include order"
    );
}

#[test]
fn glob_includes_expand_in_byte_order_and_the_diamond_loads_once() {
    let mf = ModelFiles::new()
        .with_file("root.grmb", format!("{H}include \"parts/*.grmb\";\n"))
        .with_file("parts/z.grmb", format!("{P}include \"../shared.grmb\";\n"))
        .with_file("parts/a.grmb", format!("{P}include \"../shared.grmb\";\n"))
        .with_file("shared.grmb", P);
    let root = load_roots(&mf).remove(0);
    let order: Vec<&str> = root.files.iter().map(|f| f.parsed.path.as_str()).collect();
    assert_eq!(
        order,
        ["root.grmb", "parts/a.grmb", "shared.grmb", "parts/z.grmb"],
        "depth first, glob in byte order, shared read once"
    );
    assert!(root.diags.is_empty(), "{:?}", root.diags);
}

#[test]
fn an_extension_is_one_identity_with_two_parts() {
    let text = format!("{H}node cli : trusted {{\n}}\nextend node cli {{\n  owns \"x/**\";\n}}\n");
    let parsed = parse_file("m.grmb", text.as_bytes());
    let f = fold_file(&parsed, "").expect("fold");
    let cli: Vec<_> = f
        .term
        .units()
        .into_iter()
        .filter(|u| u.symref.to_string() == "m.grmb::cli")
        .collect();
    assert_eq!(cli.len(), 2, "declaration and extension parts");
    let decls: Vec<_> = f
        .scopes
        .decls()
        .iter()
        .filter(|d| d.name == "cli")
        .collect();
    assert_eq!(decls.len(), 1, "one declaration, two nodes");
    assert_eq!(decls[0].nodes.len(), 2);
}

#[test]
fn mounting_prefixes_anchors_and_the_term_binds_the_prefix() {
    let mf = ModelFiles::new()
        .with_file("root.grmb", format!("{H}include \"api.grmb\" as api;\n"))
        .with_file("api.grmb", format!("{P}node handlers : trusted {{\n}}\n"));
    let root = load_roots(&mf).remove(0);
    assert_eq!(root.files[1].mount, "api");
    let f = fold_file(&root.files[1].parsed, "api").expect("fold");
    let dumped = grimble_model::dump::dump(&f);
    assert!(dumped.contains("anchor=node/api.handlers"), "{dumped}");
    let root_term = fold_file(&root.files[0].parsed, "").expect("fold");
    let d = grimble_model::dump::dump(&root_term);
    assert!(d.contains("bind kind=mount mode=prefix"), "{d}");
}

#[test]
// frob:tests crates/grimble-model/src/adapter.rs::grammar_identity
fn the_adapter_is_f4_and_folds_through_the_gob_symbols_contract() {
    let a = GrmbAdapter;
    assert_eq!(a.fidelity(), Fidelity::F4);
    assert_eq!(a.language(), "grmb");
    assert!(a.identity().contains("grimble-model"), "{}", a.identity());
    let caps = a.capabilities();
    assert_eq!(caps.precision(Capability::ResolveRef), Precision::Lexical);
    assert_eq!(caps.precision(Capability::Expand), Precision::NotApplicable);
    let text = format!("{H}// frob:doc docs/a.md#n\nnode n : trusted {{\n}}\n");
    let input = FileInput {
        path: "design/m.grmb",
        digest: "00",
        size: u32::try_from(text.len()).expect("small"),
    };
    let tree = a.parse(&text, &ParseLimits::default());
    let folded = a.fold(&tree, &input).expect("fold");
    assert_eq!(folded.file.fidelity, Fidelity::F4);
    assert_eq!(folded.file.parse_status, ParseStatus::Complete);
    assert_eq!(folded.term.locator(), "design/m.grmb");
    let direct = fold_text(text.as_bytes(), &input, "").expect("fold");
    assert_eq!(
        folded.term.print_alpha(folded.term.root()),
        direct.term.print_alpha(direct.term.root())
    );

    let holey = "grimble = \"2\";\nmodule m;\nnode n : trusted {\n  owns ;\n}\n";
    let input = FileInput {
        path: "h.grmb",
        digest: "00",
        size: u32::try_from(holey.len()).expect("small"),
    };
    let tree = a.parse(holey, &ParseLimits::default());
    let folded = a.fold(&tree, &input).expect("fold");
    assert_eq!(folded.file.parse_status, ParseStatus::Partial { holes: 1 });

    let tiny = ParseLimits {
        max_bytes: 4,
        ..ParseLimits::default()
    };
    let tree = a.parse(&text, &tiny);
    let folded = a.fold(&tree, &input).expect("fold");
    assert!(matches!(
        folded.file.parse_status,
        ParseStatus::Failed { .. }
    ));
}

#[test]
fn the_registry_knows_the_mdl_family() {
    let reg = gob_rules::Registry::global();
    for n in 0..=17 {
        let id = format!("MDL{n:03}");
        assert!(reg.by_id(&id).is_some(), "{id} is registered");
    }
    assert!(reg.verify_unique().is_ok());
    assert_eq!(
        reg.by_id("MDL015").map(|m| m.severity),
        Some(gob_rules::Severity::Advisory)
    );
    assert_eq!(
        reg.by_id("MDL005").map(|m| m.severity),
        Some(gob_rules::Severity::Warn)
    );
}

#[test]
// frob:tests crates/grimble-model/src/text.rs::atom_text
fn an_exception_edit_changes_only_the_attr_facet() {
    use gob_ir::Facet;
    let digests = |src: &str| {
        let parsed = parse_file("f.grmb", src.as_bytes());
        let folded = fold_file(&parsed, "").expect("fold");
        let unit = folded
            .term
            .units()
            .into_iter()
            .find(|u| u.symref.to_string() == "f.grmb::n")
            .expect("unit n");
        folded
            .term
            .facet_digests(unit.node)
            .map(|(f, d)| (f, format!("{d:?}")))
    };
    let base = digests(&format!(
        "{H}/// Doc.\nnode n : trusted {{\n  kind component;\n}}\n"
    ));
    let with_exc = digests(&format!(
        "{H}/// Doc.\nnode n : trusted {{\n  kind component;\n  accept CAP003 because=\"by design\";\n}}\n"
    ));
    let changed: Vec<Facet> = base
        .iter()
        .zip(&with_exc)
        .filter(|(a, b)| a.1 != b.1)
        .map(|(a, _)| a.0)
        .collect();
    assert_eq!(
        changed,
        [Facet::Attr],
        "adding an accept never makes its own entity changed"
    );
    let doc_edit = digests(&format!(
        "{H}/// Other.\nnode n : trusted {{\n  kind component;\n}}\n"
    ));
    let changed: Vec<Facet> = base
        .iter()
        .zip(&doc_edit)
        .filter(|(a, b)| a.1 != b.1)
        .map(|(a, _)| a.0)
        .collect();
    assert_eq!(changed, [Facet::Doc]);
    let trust_edit = digests(&format!(
        "{H}/// Doc.\nnode n : foreign {{\n  kind component;\n}}\n"
    ));
    assert!(
        base.iter()
            .zip(&trust_edit)
            .any(|(a, b)| a.0 == Facet::Sig && a.1 != b.1)
    );
    let reformatted = digests(&format!(
        "{H}\n\n/// Doc.\nnode   n:trusted{{kind component;}}\n"
    ));
    assert_eq!(base, reformatted, "reformatting never changes a digest");
}

#[test]
// frob:ticket 01M3ZEH3S0PG61C2AEBM691F69
// frob:tests crates/grimble-model/src/adapter.rs::GrmbAdapter
fn a_binary_linking_grimble_model_sees_grmb_at_f4_in_the_report() {
    let report = gob_symbols::fidelity_report();
    let row = report
        .iter()
        .find(|r| r.language == "grmb")
        .expect("grmb registered");
    assert_eq!(row.fidelity, Fidelity::F4);
    assert_eq!(row.extensions, vec!["grmb"]);
    let order = row
        .capabilities
        .iter()
        .find(|(c, _)| *c == Capability::Order)
        .map(|(_, p)| *p);
    assert_eq!(order, Some(Precision::Declared));
    assert_eq!(report.last().expect("rows").language, "opaque");
    assert!(gob_symbols::adapter_for_path("design/m.grmb").is_some());
    assert!(gob_symbols::registry_conflicts().is_empty());
}

#[test]
// frob:ticket 01M3ZEH3S0PG61C2AEBM691F69
// frob:tests crates/grimble-model/src/adapter.rs::fold_text
fn the_file_symbols_of_a_grmb_file_list_its_entities() {
    let text = format!("{H}node n : trusted {{\n}}\nnode k : trusted {{\n}}\n");
    let input = FileInput {
        path: "design/m.grmb",
        digest: "00",
        size: u32::try_from(text.len()).expect("small"),
    };
    let a = GrmbAdapter;
    let tree = a.parse(&text, &ParseLimits::default());
    let folded = a.fold(&tree, &input).expect("fold");
    let got: Vec<(gob_symbols::SymbolKind, String)> = folded
        .file
        .symbols
        .iter()
        .map(|s| (s.kind, s.symref.to_string()))
        .collect();
    assert!(
        got.contains(&(gob_symbols::SymbolKind::Node, "design/m.grmb::n".to_owned())),
        "{got:?}"
    );
    assert!(
        got.contains(&(gob_symbols::SymbolKind::Node, "design/m.grmb::k".to_owned())),
        "{got:?}"
    );
    assert_eq!(folded.file.extras.len(), folded.file.symbols.len());
}

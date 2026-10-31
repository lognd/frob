//! `GLOSSARY.md` follows this repository's configuration and the schema (`navigation.md` 3.1, 3.3).
// frob:ticket 01M3ZX86CE8WDE9PJHNS90ZNMR

use frob_ledger::r#gen::{GENERATORS, glossary};
use frob_ledger::reindex::{ReindexOptions, Tree, reindex};
use frob_ledger::schema::{
    FrontmatterSchema, TicketFieldDescription, TicketFieldKind, TicketSchema,
    TicketSchemaDescription,
};

fn glossary_for(handle_min_len: usize) -> String {
    let opts = ReindexOptions {
        version: "9.9.9",
        handle_min_len,
        generators: GENERATORS,
    };
    let out = reindex(&Tree::new(), &opts).expect("reindex").tree;
    String::from_utf8(out.get(glossary::PATH).expect("GLOSSARY.md").clone()).expect("utf8")
}

#[test]
fn the_glossary_states_the_configured_handle_min_len() {
    let nine = glossary_for(9);
    assert!(nine.contains("`handle_min_len` is 9"), "{nine}");
    assert!(!nine.contains("is 7"), "{nine}");
    assert!(glossary_for(7).contains("`handle_min_len` is 7"));
}

// frob:tests crates/frob-ledger/src/gen/glossary.rs::GlossaryDrift.rule
#[test]
fn a_schema_field_with_no_glossary_entry_is_reported_as_gen001() {
    let page = glossary_for(7);
    let real = FrontmatterSchema::describe();
    assert!(glossary::check(&page, real).is_empty());

    let mut fields: Vec<TicketFieldDescription> = real.fields.to_vec();
    fields.push(TicketFieldDescription {
        key: "brand_new_field",
        doc: "added to the schema only",
        type_name: "Option<String>",
        kind: TicketFieldKind::Scalar,
        required: false,
        settable: true,
        default_toml: None,
        since: None,
    });
    let extended = TicketSchemaDescription {
        name: real.name,
        doc: real.doc,
        fields: Box::leak(fields.into_boxed_slice()),
    };
    let drift = glossary::check(&page, &extended);
    assert_eq!(
        drift,
        vec![glossary::GlossaryDrift::MissingField(
            "brand_new_field".into()
        )]
    );
    assert_eq!(drift[0].rule(), "GEN001");
}

#[test]
fn an_entry_for_a_removed_field_is_reported_as_gen001() {
    let page = glossary_for(7);
    let real = FrontmatterSchema::describe();
    let fewer = TicketSchemaDescription {
        name: real.name,
        doc: real.doc,
        fields: &real.fields[1..],
    };
    let drift = glossary::check(&page, &fewer);
    assert_eq!(
        drift,
        vec![glossary::GlossaryDrift::UnknownField(
            real.fields[0].key.into()
        )]
    );
}

// frob:tests crates/frob-ledger/src/gen/glossary.rs::render_for
#[test]
fn render_for_names_the_version_and_event_in_the_header() {
    use frob_ledger::reindex::GenInput;
    let tree = Tree::new();
    let paths = std::collections::BTreeMap::new();
    let input = GenInput {
        tree: &tree,
        version: "9.9.9",
        handle_min_len: 7,
        as_of: Some("01EVENT"),
        paths: &paths,
    };
    let page = glossary::render_for(FrontmatterSchema::describe(), &input);
    assert!(page.contains("v9.9.9"), "{page}");
    assert!(page.contains("As of event 01EVENT."), "{page}");
    assert!(page.contains("## Fields"), "{page}");
}

//! COMP001 to COMP009 and the STATE rules over component files beyond the rule pages: the
//! acceptance case, boundaries, duplicates, empty sets, unicode and the inapplicable path.

// frob:ticket 01M4CXR7CHD30VMWHMRD6TTN3F

mod support;

use crunk_rules::CrunkHost;
use crunk_rules::host::{component_subjects, missing_component_inputs};
use crunk_rules::rules::{
    comp001::Comp001, comp002::Comp002, comp003::Comp003, comp004::Comp004, comp005::Comp005,
    comp006::Comp006, comp007::Comp007, comp008::Comp008, comp009::Comp009, state001::State001,
};
use gob_rules::{Finding, Measured, RepoRule};

const FILE: &str = "design/components/button.component.toml";

fn project(text: &str) -> support::Project {
    support::project(FILE, text, None)
}

fn messages<R: RepoRule<support::Project> + Default>(text: &str) -> Vec<String> {
    let findings: Vec<Finding> = support::run::<R>(&project(text));
    findings.into_iter().map(|f| f.message).collect()
}

const A11Y: &str =
    "[a11y]\nrole = \"button\"\nname_source = \"label\"\nkeyboard = { Enter = \"go\" }\n";

// frob:tests crates/crunk-rules/src/rules/state001.rs::State001
// frob:tests crates/crunk-rules/src/rules/comp004.rs::Comp004
#[test]
fn a_spec_missing_a_state_and_binding_a_literal_fires_with_the_node_id() {
    let text = "name = \"button\"\nkinds = [\"interactive\"]\n[[states]]\nid = \"default\"\n[anatomy]\nnodes = [\"label\"]\n[[bindings]]\nnode = \"label\"\nproperty = \"color\"\nvalue = \"#f00\"\n";
    let state = messages::<State001>(text);
    assert_eq!(state.len(), 1, "{state:?}");
    assert!(state[0].contains("button"), "{state:?}");
    assert!(state[0].contains("hover"), "{state:?}");
    let comp = messages::<Comp004>(text);
    assert_eq!(comp.len(), 1, "{comp:?}");
    assert!(comp[0].contains("button/label"), "{comp:?}");
}

// frob:tests crates/crunk-rules/src/rules/comp001.rs::Comp001
#[test]
fn a_duplicate_prop_and_an_empty_enum_each_fire() {
    let text = "name = \"b\"\n[[props]]\nname = \"p\"\nkind = \"bool\"\n[[props]]\nname = \"p\"\nkind = \"enum\"\n";
    let m = messages::<Comp001>(text);
    assert!(m.iter().any(|x| x.contains("more than once")), "{m:?}");
    assert!(m.iter().any(|x| x.contains("no values")), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/comp001.rs::Comp001
#[test]
fn a_slot_with_min_above_max_fires_and_equal_bounds_do_not() {
    let bad = "name = \"b\"\n[[props]]\nname = \"s\"\nkind = \"slot\"\nmin = 3\nmax = 2\n";
    assert_eq!(messages::<Comp001>(bad).len(), 1);
    let ok = "name = \"b\"\n[[props]]\nname = \"s\"\nkind = \"slot\"\nmin = 2\nmax = 2\n";
    assert!(messages::<Comp001>(ok).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/comp001.rs::Comp001
#[test]
fn values_on_a_non_enum_prop_fire() {
    let text = "name = \"b\"\n[[props]]\nname = \"t\"\nkind = \"text\"\nvalues = [\"a\"]\n";
    assert_eq!(messages::<Comp001>(text).len(), 1);
}

// frob:tests crates/crunk-rules/src/rules/comp002.rs::Comp002
#[test]
fn a_cross_product_matrix_counts_its_holes() {
    let head = "name = \"b\"\n[[props]]\nname = \"size\"\nkind = \"enum\"\nvalues = [\"sm\", \"lg\"]\naxis = true\n[[props]]\nname = \"tone\"\nkind = \"enum\"\nvalues = [\"a\", \"b\"]\naxis = true\n";
    let cell =
        |s: &str, t: &str| format!("[[variants]]\naxes = {{ size = \"{s}\", tone = \"{t}\" }}\n");
    let three = format!(
        "{head}{}{}{}",
        cell("sm", "a"),
        cell("sm", "b"),
        cell("lg", "a")
    );
    let m = messages::<Comp002>(&three);
    assert!(m.iter().any(|x| x.contains("3 of 4")), "{m:?}");
    let four = format!("{three}{}", cell("lg", "b"));
    assert!(messages::<Comp002>(&four).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/comp002.rs::Comp002
#[test]
fn a_repeated_cell_and_an_unknown_value_fire() {
    let head = "name = \"b\"\n[[props]]\nname = \"size\"\nkind = \"enum\"\nvalues = [\"sm\"]\naxis = true\n";
    let dup = format!(
        "{head}[[variants]]\naxes = {{ size = \"sm\" }}\n[[variants]]\naxes = {{ size = \"sm\" }}\n"
    );
    assert!(
        messages::<Comp002>(&dup)
            .iter()
            .any(|x| x.contains("repeats"))
    );
    let unk = format!("{head}[[variants]]\naxes = {{ size = \"xl\" }}\n");
    assert!(
        messages::<Comp002>(&unk)
            .iter()
            .any(|x| x.contains("unknown value 'xl'"))
    );
}

// frob:tests crates/crunk-rules/src/rules/comp002.rs::Comp002
#[test]
fn variants_without_an_axis_prop_fire_and_no_variants_is_clean() {
    assert_eq!(
        messages::<Comp002>("name = \"b\"\n[[variants]]\naxes = { a = \"b\" }\n").len(),
        1
    );
    assert!(messages::<Comp002>("name = \"b\"\n").is_empty());
}

// frob:tests crates/crunk-rules/src/rules/comp003.rs::Comp003
#[test]
fn blank_and_repeated_state_ids_fire() {
    let m = messages::<Comp003>(
        "name = \"b\"\n[[states]]\nid = \"\"\n[[states]]\nid = \"x\"\n[[states]]\nid = \"x\"\n",
    );
    assert_eq!(m.len(), 2, "{m:?}");
    assert_eq!(messages::<Comp003>("name = \"b\"\n").len(), 1);
}

// frob:tests crates/crunk-rules/src/rules/comp004.rs::Comp004
#[test]
fn a_binding_with_both_neither_or_a_blank_property_fires() {
    let both = "name = \"b\"\n[[bindings]]\nnode = \"b\"\nproperty = \"c\"\ntoken = \"--t\"\nvalue = \"1\"\n";
    let neither = "name = \"b\"\n[[bindings]]\nnode = \"b\"\nproperty = \"c\"\n";
    let blank = "name = \"b\"\n[[bindings]]\nnode = \"b\"\nproperty = \" \"\ntoken = \"--t\"\n";
    for text in [both, neither, blank] {
        assert_eq!(messages::<Comp004>(text).len(), 1, "{text}");
    }
}

// frob:tests crates/crunk-rules/src/rules/comp004.rs::Comp004
#[test]
fn a_unicode_node_name_is_reported_whole() {
    let text = "name = \"bouton\"\n[anatomy]\nnodes = [\"\u{00e9}tiquette\"]\n[[bindings]]\nnode = \"\u{00e9}tiquette\"\nproperty = \"c\"\nvalue = \"red\"\n";
    let m = messages::<Comp004>(text);
    assert!(m[0].contains("bouton/\u{00e9}tiquette"), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/comp005.rs::Comp005
#[test]
fn an_unknown_node_state_and_token_each_fire() {
    let text = "name = \"b\"\n[[states]]\nid = \"default\"\n[[bindings]]\nnode = \"ghost\"\nproperty = \"c\"\nstate = \"nope\"\ntoken = \"--missing\"\n";
    let m = messages::<Comp005>(text);
    assert_eq!(m.len(), 3, "{m:?}");
    assert!(m.iter().all(|x| x.contains("b/ghost")), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/comp005.rs::Comp005
#[test]
fn the_component_itself_and_a_known_token_resolve() {
    let text =
        "name = \"b\"\n[[bindings]]\nnode = \"b\"\nproperty = \"c\"\ntoken = \"--color-ink\"\n";
    assert!(messages::<Comp005>(text).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/comp006.rs::Comp006
#[test]
fn the_minimum_target_boundary_is_24() {
    for (px, fires) in [(23, true), (24, false)] {
        let text = format!("name = \"b\"\nkinds = [\"interactive\"]\n{A11Y}min_target = {px}\n");
        assert_eq!(messages::<Comp006>(&text).len(), usize::from(fires), "{px}");
    }
}

// frob:tests crates/crunk-rules/src/rules/comp006.rs::Comp006
#[test]
fn a_non_interactive_component_needs_no_contract() {
    assert!(messages::<Comp006>("name = \"b\"\nkinds = [\"form\"]\n").is_empty());
}

// frob:tests crates/crunk-rules/src/rules/comp007.rs::Comp007
#[test]
fn a_draft_needs_no_mapping_but_a_blank_field_still_fires() {
    assert!(messages::<Comp007>("name = \"b\"\n").is_empty());
    let blank = "name = \"b\"\n[[code]]\nframework = \"react\"\npath = \"\"\nexport = \"B\"\n";
    assert_eq!(messages::<Comp007>(blank).len(), 1);
    assert_eq!(
        messages::<Comp007>("name = \"b\"\nstatus = \"completed\"\n").len(),
        1
    );
}

// frob:tests crates/crunk-rules/src/rules/comp008.rs::Comp008
#[test]
fn a_code_mapping_without_a_props_list_is_not_judged_and_a_missing_prop_fires() {
    let head = "name = \"b\"\n[[props]]\nname = \"a\"\nkind = \"bool\"\n[[code]]\nframework = \"react\"\npath = \"p\"\nexport = \"B\"\n";
    assert!(messages::<Comp008>(head).is_empty());
    let m = messages::<Comp008>(&format!("{head}props = []\n"));
    assert!(m[0].contains("lacks a"), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/comp009.rs::Comp009
#[test]
fn a_matching_hash_is_clean_and_a_wrong_one_is_stale() {
    let text = "name = \"b\"\nstatus = \"ready\"\n";
    let want = messages::<Comp009>(text);
    let hash = want[0]
        .rsplit("expected ")
        .next()
        .expect("hash")
        .trim_end_matches(')')
        .to_owned();
    let ok = format!("{text}content_hash = \"{hash}\"\n");
    assert!(messages::<Comp009>(&ok).is_empty(), "{hash}");
    let stale = format!("{text}content_hash = \"deadbeef\"\n");
    assert!(messages::<Comp009>(&stale)[0].contains("changed"));
}

// frob:tests crates/crunk-rules/src/host.rs::component_subjects
// frob:tests crates/crunk-rules/src/host.rs::state_subjects
// frob:tests crates/crunk-rules/src/host.rs::missing_component_inputs
// frob:tests crates/crunk-rules/src/host.rs::CrunkHost.components
#[test]
fn the_component_accessors_count_files_and_name_the_missing_input() {
    let host = project("name = \"b\"\n");
    assert!(host.components().is_some());
    assert_eq!(component_subjects(&host), 1);
    assert_eq!(crunk_rules::host::state_subjects(&host), 1);
    assert_eq!(missing_component_inputs(&host), None);
    let none = support::project("styles/app.css", "a { color: red; }\n", None);
    assert_eq!(component_subjects(&none), 0);
    assert!(missing_component_inputs(&none).is_some());
    assert_eq!(
        <Comp001 as Measured<support::Project>>::subjects(&Comp001, &none),
        0
    );
}

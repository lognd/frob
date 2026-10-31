//! The SCSS adapter end to end: variables and mixins as `phase` terms with their expansion, the symbolic
//! scope graph (not text matching), and syntax errors confined to their file (D96, language-engines.md
//! sections 2 and 3).

// frob:ticket 01M487BKN1FE92BQ72KQWGBG11

use gob_ir::{Model, NodeId, Operator, Resolution, Universal, style};
use gob_symbols::{ParseStatus, adapter_for_path, extract_file, fold_file, is_scss_path};
use gob_walk::{Digest, FileEntry, LanguageHint};

fn entry(path: &str, text: &str) -> FileEntry {
    FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    }
}

fn model_of(src: &str) -> Model {
    let folded = fold_file(&entry("site.scss", src), src).expect("fold");
    Model::new(folded.term, folded.scopes)
}

/// Every phase node of `kind`, in id order.
fn phases(model: &Model, kind: &str) -> Vec<NodeId> {
    let term = model.term();
    term.ids()
        .filter(|&id| {
            matches!(term.node(id).op(), Operator::Universal(Universal::Phase { kind: k }) if k == kind)
        })
        .collect()
}

/// The `raw` text of every declaration, in order.
fn raws(model: &Model) -> Vec<(String, String)> {
    style::declarations(model)
        .into_iter()
        .map(|d| (d.property, d.raw))
        .collect()
}

#[test]
// frob:tests crates/gob-symbols/src/scss/mod.rs::declaration
fn a_known_variable_use_is_a_phase_with_its_expansion() {
    let model = model_of("$gap: 4px 8px;\n.a { margin: $gap; }\n");
    let uses = phases(&model, "variable");
    assert_eq!(uses.len(), 1);
    let kids = model.term().node(uses[0]).children();
    assert_eq!(kids.len(), 2, "reference plus expansion");
    let expansion = model.term().node(kids[1]).children();
    assert_eq!(expansion.len(), 2, "4px and 8px");
}

#[test]
// frob:tests crates/gob-symbols/src/scss/mod.rs::variable_use
fn an_unknown_variable_use_is_an_unexpanded_phase() {
    let model = model_of(".a { margin: $nowhere; }\n");
    let uses = phases(&model, "variable");
    assert_eq!(uses.len(), 1);
    assert_eq!(model.term().node(uses[0]).children().len(), 1);
    // The reference does not resolve to anything.
    let r = model.term().node(uses[0]).children()[0];
    assert_eq!(model.resolve_node(r), Resolution::Unknown);
}

#[test]
// frob:tests crates/gob-symbols/src/scss/mod.rs::bind_variable
fn variable_references_resolve_through_the_scope_graph() {
    let model = model_of("$c: red;\n.a { $c: blue; color: $c; }\n.b { color: $c; }\n");
    let uses = phases(&model, "variable");
    assert_eq!(uses.len(), 2);
    let resolve = |p: NodeId| {
        let r = model.term().node(p).children()[0];
        model.resolve_node(r)
    };
    let (Resolution::Must(inner), Resolution::Must(outer)) = (resolve(uses[0]), resolve(uses[1]))
    else {
        panic!("both resolve at Must");
    };
    assert_ne!(inner, outer, "the nested definition shadows the file one");
}

#[test]
// frob:tests crates/gob-symbols/src/scss/mod.rs::bind_variable
fn default_and_global_flags_are_modelled() {
    let src = "$a: 1px !default;\n$a: 2px !default;\n.x { $b: 3px !global; width: $b; }\n.y { height: $b; }\n";
    let model = model_of(src);
    let uses = phases(&model, "variable");
    // `$a` keeps its first value; `$b` global is visible from `.y`.
    let y = model.term().node(uses[1]).children();
    assert_eq!(y.len(), 2, "global variable is known outside its rule");
    let r = model.term().node(uses[1]).children()[0];
    assert!(matches!(model.resolve_node(r), Resolution::Must(_)));
    assert!(raws(&model).iter().all(|(_, raw)| !raw.contains('!')));
    let a_defs = model
        .term()
        .ids()
        .filter(|&i| model.term().node(i).name() == Some("$a"))
        .count();
    assert_eq!(a_defs, 2);
}

#[test]
// frob:tests crates/gob-symbols/src/scss/mod.rs::include
fn an_include_expands_the_mixin_body_with_arguments_substituted() {
    let src = "@mixin pad($v, $h: 2px) { padding: $v $h; }\n.a { @include pad(1px); }\n.b { @include pad($h: 9px, $v: 3px); }\n";
    let model = model_of(src);
    let incs = phases(&model, "mixin");
    assert_eq!(incs.len(), 2);
    for i in &incs {
        assert_eq!(
            model.term().node(*i).children().len(),
            2,
            "call plus expansion"
        );
    }
    // The expansion holds a declaration whose variable uses are expanded with the arguments.
    let expanded: Vec<usize> = phases(&model, "variable")
        .into_iter()
        .map(|p| model.term().node(p).children().len())
        .collect();
    // Four uses inside the definition (unknown parameters) are single-child; the expansions are two-child.
    assert_eq!(expanded.iter().filter(|&&n| n == 2).count(), 4);
    assert_eq!(expanded.iter().filter(|&&n| n == 1).count(), 2);
}

#[test]
// frob:tests crates/gob-symbols/src/scss/mod.rs::expansion
fn an_include_of_an_unknown_or_recursive_mixin_stays_unexpanded() {
    let src = "@mixin r { @include r; }\n.a { @include elsewhere; @include r; }\n";
    let model = model_of(src);
    let incs = phases(&model, "mixin");
    assert!(incs.len() >= 2);
    let unexpanded = incs
        .iter()
        .filter(|&&i| model.term().node(i).children().len() == 1)
        .count();
    assert!(
        unexpanded >= 2,
        "unknown and recursive includes stay unexpanded"
    );
}

#[test]
// frob:tests crates/gob-symbols/src/scss/mod.rs::lexical_scopes
fn mixin_names_resolve_symbolically() {
    let model = model_of("@mixin m { color: red; }\n.a { @include m; @include absent; }\n");
    let resolved: Vec<Resolution> = phases(&model, "mixin")
        .into_iter()
        .map(|p| {
            let call = model.term().node(p).children()[0];
            let r = model.term().node(call).children()[0];
            model.resolve_node(r)
        })
        .collect();
    assert!(matches!(resolved[0], Resolution::Must(_)));
    assert_eq!(resolved[1], Resolution::Unknown);
}

#[test]
// frob:tests crates/gob-symbols/src/scss/mod.rs::rule_set
fn nested_rules_and_class_selectors_fold_like_css() {
    let model = model_of(".card { color: red; &:hover { color: blue; } .title { margin: 0; } }\n");
    let rules = style::style_rules(&model);
    assert_eq!(rules.len(), 3);
    assert_eq!(style::class_selectors(&model).len(), 2);
    assert_eq!(raws(&model).len(), 3);
}

#[test]
// frob:tests crates/gob-symbols/src/scss/mod.rs::at_rule
fn control_directives_are_at_rules_and_branch_assignments_become_unknown() {
    let src = "$w: 1px;\n@if true { $w: 2px; }\n.a { width: $w; }\n@each $i in 1, 2 { .c-#{$i} { order: $i; } }\n";
    let model = model_of(src);
    let names: Vec<String> = style::at_rules(&model)
        .into_iter()
        .map(|a| a.name)
        .collect();
    assert!(names.contains(&"if".to_owned()) && names.contains(&"each".to_owned()));
    // `$w` was assigned in a branch: used afterwards it is unexpanded.
    let uses = phases(&model, "variable");
    assert_eq!(model.term().node(uses[0]).children().len(), 1);
}

#[test]
// frob:tests crates/gob-symbols/src/scss/mod.rs::hole
fn a_syntax_error_is_a_partial_parse_and_other_files_are_unaffected() {
    let bad = ".a { color: ;; { \n";
    let good = "$x: 1px;\n.b { margin: $x; }\n";
    let bad_out = extract_file(&entry("bad.scss", bad), bad);
    let good_out = extract_file(&entry("good.scss", good), good);
    assert!(matches!(bad_out.parse_status, ParseStatus::Partial { holes } if holes > 0));
    assert_eq!(good_out.parse_status, ParseStatus::Complete);
}

#[test]
// frob:tests crates/gob-symbols/src/scss/mod.rs::is_scss_path
fn the_adapter_is_registered_for_scss_paths() {
    assert!(is_scss_path("a/b/site.SCSS"));
    assert!(!is_scss_path("site.css"));
    let adapter = adapter_for_path("x/site.scss").expect("scss adapter");
    assert_eq!(adapter.language(), "scss");
}

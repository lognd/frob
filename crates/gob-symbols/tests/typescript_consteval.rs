//! Bounded constant evaluation of TypeScript across files (D96, language-engines.md section 2,
//! `const_value`), including the ported vectors of the v1 `test_semantic_ts_consteval.py`.

// frob:ticket 01M43ARXVD5PXP6ZBVFC2F4ZMQ

use gob_ir::const_value::{Budget, ConstValue, Fragment, Value};
use gob_ir::markup;
use gob_symbols::{ConstProject, Evaluated, SymbolGraph, Unresolved, extract_file, fold_file};
use gob_walk::{Digest, FileEntry, LanguageHint};

fn entry(path: &str, text: &str) -> FileEntry {
    FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    }
}

/// The folded files as a project over their module graph, and the graph.
fn load(files: &[(&str, &str)]) -> (SymbolGraph, Vec<(String, gob_symbols::Folded)>) {
    let graph = SymbolGraph::from_files(
        files
            .iter()
            .map(|(p, s)| extract_file(&entry(p, s), s))
            .collect(),
    );
    let folded = files
        .iter()
        .map(|(p, s)| ((*p).to_owned(), fold_file(&entry(p, s), s).expect("fold")))
        .collect();
    (graph, folded)
}

/// Evaluates the `className` attribute (or `attr`) of the first element of `main` over `files`.
fn eval_attr_with(files: &[(&str, &str)], main: &str, attr: &str, budget: Budget) -> Evaluated {
    let (graph, folded) = load(files);
    let mut project = ConstProject::new(&graph);
    for (p, f) in &folded {
        project.add_file(p, f);
    }
    let model = project.model(main).expect("main file");
    let els = markup::elements(model);
    let a = els[0].attribute(attr).expect("attribute");
    let node = a.value.expect("attribute value");
    project.evaluate(main, node, budget)
}

fn eval_attr(files: &[(&str, &str)], attr: &str) -> Evaluated {
    eval_attr_with(files, files[0].0, attr, Budget::default())
}

/// Evaluates one expression `expr` in a tsx file after `prelude`, with `others` as sibling files.
fn eval_expr(prelude: &str, expr: &str, others: &[(&str, &str)]) -> Evaluated {
    let main = format!("{prelude}\nexport const X = <div className={{{expr}}} />;\n");
    let mut files = vec![("main.tsx", main.as_str())];
    files.extend_from_slice(others);
    eval_attr(&files, "className")
}

fn s(text: &str) -> Value {
    Value::Str(text.to_owned())
}

fn strs(values: &[&str]) -> ConstValue {
    ConstValue::OneOf(values.iter().map(|v| s(v)).collect())
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/consteval.rs::ConstProject
fn an_imported_const_resolves_with_its_origin_span() {
    let a = "export const gap = 8;\n";
    let main = "import { gap } from './a';\nexport const X = <div style={{ margin: gap }} />;\n";
    let got = eval_attr_with(
        &[("main.tsx", main), ("a.ts", a)],
        "main.tsx",
        "style",
        Budget::default(),
    );
    let ConstValue::Known(Value::Object(o)) = &got.value else {
        panic!("style object should be Known: {:?}", got.value);
    };
    assert_eq!(o["margin"], Value::Int(8));
    assert_eq!(got.unresolved, None);
    let start = u32::try_from(a.find('8').expect("literal")).expect("small");
    assert_eq!(
        got.origins
            .iter()
            .map(|o| (o.path.as_str(), o.start, o.end))
            .collect::<Vec<_>>(),
        [("a.ts", start, start + 1)]
    );
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/consteval.rs::Unresolved
fn a_cycle_across_files_is_unresolved_with_the_reason() {
    let a = "import { B } from './b';\nexport const A = B;\n";
    let b = "import { A } from './a';\nexport const B = A;\n";
    let main = "import { A } from './a';\nexport const X = <div className={A} />;\n";
    let got = eval_attr(&[("main.tsx", main), ("a.ts", a), ("b.ts", b)], "className");
    assert_eq!(got.value, ConstValue::Unknown);
    assert_eq!(got.unresolved, Some(Unresolved::Cycle));
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/consteval.rs::Unresolved
fn a_cycle_in_one_file_is_unresolved_with_the_reason() {
    let got = eval_expr("const a = b;\nconst b = a;", "a", &[]);
    assert_eq!(got.value, ConstValue::Unknown);
    assert_eq!(got.unresolved, Some(Unresolved::Cycle));
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/consteval.rs::Unresolved
fn an_over_budget_chain_is_unresolved_with_the_reason() {
    let main = "import { C } from './c';\nexport const X = <div className={C} />;\n";
    let files = [
        ("main.tsx", main),
        (
            "c.ts",
            "import { B } from './b';\nexport const C = B + 'c';\n",
        ),
        (
            "b.ts",
            "import { A } from './a';\nexport const B = A + 'b';\n",
        ),
        ("a.ts", "export const A = 'a';\n"),
    ];
    let ok = eval_attr_with(&files, "main.tsx", "className", Budget::default());
    assert_eq!(ok.value.known_str(), Some("abc"));
    assert_eq!(ok.origins.len(), 3);
    let got = eval_attr_with(&files, "main.tsx", "className", Budget(4));
    assert_eq!(got.unresolved, Some(Unresolved::Budget));
    assert!(got.value.known().is_none());
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/consteval.rs::ConstProject::evaluate
fn same_file_constants_and_literals_evaluate() {
    let got = eval_expr("const base = 'btn';", "base + ' ' + `${base}-lg`", &[]);
    assert_eq!(got.value.known_str(), Some("btn btn-lg"));
    assert_eq!(got.origins.len(), 1);
}

// ---- the v1 vectors ----

#[test]
// frob:tests crates/gob-symbols/src/typescript/consteval.rs::ConstProject::evaluate
fn v1_literals_concatenation_ternary_and_or() {
    assert_eq!(
        eval_expr("", "\"hello\"", &[]).value.known_str(),
        Some("hello")
    );
    assert_eq!(
        eval_expr("", "\"a\" + \"b\" + \"c\"", &[])
            .value
            .known_str(),
        Some("abc")
    );
    assert_eq!(
        eval_expr("", "cond ? \"yes\" : \"no\"", &[]).value,
        strs(&["no", "yes"])
    );
    // `||` follows JavaScript: a truthy left operand is the whole value (v1 over-approximated with both).
    assert_eq!(
        eval_expr("", "\"left\" || \"right\"", &[])
            .value
            .known_str(),
        Some("left")
    );
    assert_eq!(
        eval_expr("", "\"\" || \"right\"", &[]).value.known_str(),
        Some("right")
    );
    assert_eq!(
        eval_expr("", "\"x\" as const", &[]).value.known_str(),
        Some("x")
    );
    assert_eq!(
        eval_expr("", "\"y\" satisfies string", &[])
            .value
            .known_str(),
        Some("y")
    );
    assert_eq!(
        eval_expr("", "`x-${\"mid\"}-y`", &[]).value.known_str(),
        Some("x-mid-y")
    );
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/consteval.rs::ConstProject::evaluate
fn v1_unfoldable_values_are_never_guessed() {
    let call = eval_expr("", "someFunc()", &[]);
    assert_eq!(call.value, ConstValue::Unknown);
    assert_eq!(call.unresolved, Some(Unresolved::Dynamic));
    let partial = eval_expr("", "\"prefix-\" + someFunc()", &[]);
    assert_eq!(
        partial.value,
        ConstValue::Fragments(vec![Fragment::Known("prefix-".into()), Fragment::Unknown])
    );
    assert_eq!(partial.unresolved, Some(Unresolved::Dynamic));
    let half = eval_expr("", "cond ? \"yes\" : someFunc()", &[]);
    assert_eq!(half.value, ConstValue::Unknown);
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/consteval.rs::ConstProject::evaluate
fn v1_arrays_objects_and_spreads() {
    assert_eq!(
        eval_expr("", "[\"a\", \"b\", \"c\"]", &[]).value,
        ConstValue::Known(Value::Array(vec![s("a"), s("b"), s("c")]))
    );
    let ConstValue::Known(Value::Object(o)) = eval_expr("", "{a: \"1\", b: \"2\"}", &[]).value
    else {
        panic!("object");
    };
    assert_eq!((o["a"].clone(), o["b"].clone()), (s("1"), s("2")));
    let ConstValue::Known(Value::Object(o)) = eval_expr("", "{...{a: \"1\"}, b: \"2\"}", &[]).value
    else {
        panic!("object spread");
    };
    assert_eq!((o["a"].clone(), o["b"].clone()), (s("1"), s("2")));
    let base = ("consts.ts", "export const BASE = [\"a\", \"b\"];\n");
    let got = eval_expr(
        "import { BASE } from './consts';",
        "[...BASE, \"c\"]",
        &[base],
    );
    assert_eq!(
        got.value,
        ConstValue::Known(Value::Array(vec![s("a"), s("b"), s("c")]))
    );
    // A spread of something unknown is not dropped silently: the whole array is Unknown.
    let rest = eval_expr("", "[...rest, \"a\"]", &[]);
    assert_eq!(rest.value, ConstValue::Unknown);
    assert_eq!(rest.unresolved, Some(Unresolved::Dynamic));
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/consteval.rs::ConstProject::evaluate
fn v1_cross_module_constants_and_templates() {
    let labels = ("labels.ts", "export const LABEL = \"shared-label\";\n");
    let got = eval_expr("import { LABEL } from './labels';", "LABEL", &[labels]);
    assert_eq!(got.value.known_str(), Some("shared-label"));
    let prefix = ("prefix.ts", "export const PREFIX = \"app\";\n");
    let got = eval_expr(
        "import { PREFIX } from './prefix';",
        "`${PREFIX}-${cond ? \"a\" : \"b\"}`",
        &[prefix],
    );
    assert_eq!(got.value, strs(&["app-a", "app-b"]));
    assert_eq!(got.unresolved, None);
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/consteval.rs::ConstProject::evaluate
fn route_path_constants_evaluate_across_files() {
    let routes = (
        "routes.ts",
        "export const ROOT = '/app';\nexport const USERS = ROOT + '/users';\n",
    );
    let got = eval_expr(
        "import { USERS } from './routes';",
        "`${USERS}/new`",
        &[routes],
    );
    assert_eq!(got.value.known_str(), Some("/app/users/new"));
}

// ---- class-name joiners ----

const CLSX: &str = "import { clsx } from 'clsx';\n";

#[test]
// frob:tests crates/gob-symbols/src/typescript/consteval.rs::ConstProject::evaluate
fn clsx_joins_strings_conditions_objects_and_arrays() {
    let got = eval_expr(
        CLSX,
        "clsx('a', on && 'b', { c: flag, d: true, e: false }, ['f', 0])",
        &[],
    );
    assert_eq!(
        got.value,
        strs(&["a b c d f", "a b d f", "a c d f", "a d f"])
    );
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/consteval.rs::ConstProject::evaluate
fn a_renamed_clsx_import_and_a_default_import_are_joiners() {
    let renamed = eval_expr("import { clsx as cx } from 'clsx';", "cx('a', 'b')", &[]);
    assert_eq!(renamed.value.known_str(), Some("a b"));
    let default = eval_expr(
        "import classNames from 'classnames';",
        "classNames('a', 'b')",
        &[],
    );
    assert_eq!(default.value.known_str(), Some("a b"));
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/consteval.rs::ConstProject::evaluate
fn a_dynamic_argument_leaves_fragments() {
    let got = eval_expr(CLSX, "clsx('btn', size)", &[]);
    assert_eq!(
        got.value,
        ConstValue::Fragments(vec![Fragment::Known("btn ".into()), Fragment::Unknown])
    );
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/consteval.rs::ConstProject::evaluate
fn a_local_wrapper_that_forwards_to_clsx_is_a_joiner() {
    let got = eval_expr(
        &format!("{CLSX}const cn = (...a) => clsx(...a);"),
        "cn('a', on && 'b')",
        &[],
    );
    assert_eq!(got.value, strs(&["a", "a b"]));
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/consteval.rs::ConstProject::evaluate
fn an_imported_wrapper_that_forwards_to_clsx_is_a_joiner() {
    let util = (
        "util.ts",
        "import { clsx } from 'clsx';\nexport function cn(...inputs) { return clsx(inputs); }\n",
    );
    let got = eval_expr(
        "import { cn } from './util';\nconst base = 'p-2';",
        "cn(base, 'rounded')",
        &[util],
    );
    assert_eq!(got.value.known_str(), Some("p-2 rounded"));
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/consteval.rs::ConstProject::evaluate
fn a_wrapper_that_does_not_forward_is_not_a_joiner() {
    let got = eval_expr(
        "const cn = (...a) => a.filter(Boolean).join(' ');",
        "cn('a', 'b')",
        &[],
    );
    assert_eq!(got.value, ConstValue::Unknown);
    let unbound = eval_expr("", "cn('a', 'b')", &[]);
    assert_eq!(unbound.value, ConstValue::Unknown);
}

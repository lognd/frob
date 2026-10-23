//! COH002 decides effects from the language's effects capability, not from a callee-name list.

// frob:ticket 01M5HJ07DTC2JQT9MP5T0TGDAS

#![allow(unused_crate_dependencies)]

use gob_ir::{NodeId, Operator, Universal};
use gob_languages::Language;
use gob_symbols::{Folded, def_use_of, fold_file};
use gob_walk::{Digest, FileEntry, LanguageHint};
use grimble_check::coh_pass::{CohPassOptions, analyze};
use grimble_check::coh002::{Coh002, Coh002Options, Coh002Unresolved, UnitRole, coh002, judge};
use grimble_check::effects::{EffectClass, effects_for};
use grimble_lints::pass::PathFile;

fn fold(path: &str, text: &str) -> Folded {
    let entry = FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    };
    fold_file(&entry, text).expect("fold")
}

fn unit_f(folded: &Folded) -> NodeId {
    folded
        .term
        .ids()
        .find(|&i| {
            matches!(folded.term.node(i).op(), Operator::Universal(Universal::Unit { kind, .. }) if kind == "function")
                && folded.term.node(i).name() == Some("f")
        })
        .expect("function f")
}

fn verdict(path: &str, lang: &str, text: &str) -> Coh002 {
    let folded = fold(path, text);
    let unit = unit_f(&folded);
    coh002(
        &folded,
        lang,
        unit,
        UnitRole::None,
        &Coh002Options::default(),
    )
    .expect("supported")
}

fn py(call: &str) -> String {
    format!("def f(a, sink):\n    x = compute(a)\n    if x > 3:\n        {call}\n    return x\n")
}

fn rs(call: &str) -> String {
    format!(
        "pub fn f(a: u32, sink: &S) -> u32 {{\n    let x = compute(a);\n    if x > 3 {{\n        {call};\n    }}\n    x\n}}\n"
    )
}

fn ts(call: &str) -> String {
    format!(
        "function f(a: number, sink: S) {{\n  const x = compute(a);\n  if (x > 3) {{\n    {call};\n  }}\n  return x;\n}}\n"
    )
}

fn is_fire(v: &Coh002) -> bool {
    matches!(v, Coh002::Fire { .. })
}

fn unknown(v: &Coh002) -> Option<&Vec<String>> {
    match v {
        Coh002::Unresolved(Coh002Unresolved::UnknownCallees { callees }) => Some(callees),
        _ => None,
    }
}

// frob:tests crates/grimble-check/src/coh002.rs::coh002
// frob:tests crates/grimble-check/src/effects.rs::EffectsCapability.classify
#[test]
fn module_qualified_io_fires_in_python_rust_and_typescript() {
    assert!(is_fire(&verdict("a.py", "python", &py("os.remove(x)"))));
    assert!(is_fire(&verdict("a.rs", "rust", &rs("fs::write(x, x)"))));
    assert!(is_fire(&verdict(
        "a.ts",
        "typescript",
        &ts("fs.writeFileSync(x, x)")
    )));
}

// frob:tests crates/grimble-check/src/coh002.rs::coh002
// frob:tests crates/grimble-check/src/effects.rs::EffectsCapability.classify
#[test]
fn logging_is_trivial_and_clean_in_python_rust_and_typescript() {
    assert_eq!(
        verdict("a.py", "python", &py("logging.info(x)")),
        Coh002::Clean
    );
    assert_eq!(
        verdict("a.rs", "rust", &rs("logger.info(x)")),
        Coh002::Clean
    );
    assert_eq!(
        verdict("a.ts", "typescript", &ts("console.log(x)")),
        Coh002::Clean
    );
}

// frob:tests crates/grimble-check/src/effects.rs::EffectsCapability.classify
#[test]
fn builtin_io_is_an_effect_only_unqualified() {
    assert!(is_fire(&verdict("a.py", "python", &py("open(x)"))));
    assert!(is_fire(&verdict("a.ts", "typescript", &ts("fetch(x)"))));
    let cap = effects_for("python").unwrap();
    assert_eq!(cap.classify(&["open".to_owned()]), EffectClass::Effect);
    assert_eq!(
        cap.classify(&["items".to_owned(), "open".to_owned()]),
        EffectClass::Unknown
    );
    assert_eq!(cap.classify(&[]), EffectClass::Unknown);
}

// frob:tests crates/grimble-check/src/coh002.rs::coh002
#[test]
fn nested_calls_are_classified_through_their_heads() {
    // A call chained on another call: the effect is the chained method.
    assert!(is_fire(&verdict("a.py", "python", &py("make(x).send(x)"))));
    // Logging that wraps an effect still performs the effect.
    assert!(is_fire(&verdict(
        "a.ts",
        "typescript",
        &ts("console.log(fs.readFileSync(x))")
    )));
    // An argument call of a trivial call is judged on its own head.
    assert_eq!(
        verdict("a.py", "python", &py("logging.info(str(x))")).clone(),
        Coh002::Unresolved(Coh002Unresolved::UnknownCallees {
            callees: vec!["str".to_owned()]
        })
    );
}

// frob:tests crates/grimble-check/src/coh002.rs::coh002
#[test]
fn aliases_and_in_memory_methods_stay_unresolved() {
    let aliased = verdict("a.py", "python", &py("remove(x)"));
    assert_eq!(unknown(&aliased), Some(&vec!["remove".to_owned()]));
    let renamed = verdict("a.py", "python", &py("o.remove(x)"));
    assert_eq!(unknown(&renamed), Some(&vec!["remove".to_owned()]));
    let items = verdict("a.ts", "typescript", &ts("items.delete(x)"));
    assert_eq!(unknown(&items), Some(&vec!["delete".to_owned()]));
}

// frob:tests crates/grimble-check/src/coh002.rs::judge
#[test]
fn a_language_without_a_capability_is_unresolved() {
    let text = py("sink.send(x)");
    let folded = fold("a.py", &text);
    let unit = unit_f(&folded);
    let edges = def_use_of(&folded, "python", unit).expect("python def-use");
    let none = judge(
        &folded.term,
        "python",
        unit,
        &edges,
        UnitRole::None,
        None,
        &Coh002Options::default(),
    );
    assert_eq!(
        none,
        Coh002::Unresolved(Coh002Unresolved::NoEffectsCapability {
            lang: "python".to_owned()
        })
    );
    assert!(effects_for("go").is_none());
    assert!(effects_for("csharp").is_none());
    let unlisted = judge(
        &folded.term,
        "go",
        unit,
        &edges,
        UnitRole::None,
        None,
        &Coh002Options::default(),
    );
    assert!(matches!(
        unlisted,
        Coh002::Unresolved(Coh002Unresolved::NoEffectsCapability { .. })
    ));
}

// frob:tests crates/grimble-check/src/coh002.rs::judge
#[test]
fn a_missing_capability_is_clean_when_nothing_needs_classifying() {
    let text = "def f(a, sink):\n    sink.send(a)\n    return a\n";
    let folded = fold("a.py", text);
    let unit = unit_f(&folded);
    let edges = def_use_of(&folded, "python", unit).expect("python def-use");
    let v = judge(
        &folded.term,
        "python",
        unit,
        &edges,
        UnitRole::None,
        None,
        &Coh002Options::default(),
    );
    assert_eq!(v, Coh002::Clean);
}

// frob:tests crates/grimble-check/src/coh_pass.rs::analyze
#[test]
fn empty_and_mixed_language_files_are_judged_per_file() {
    let fire_py = py("os.remove(x)");
    let clean_ts = ts("console.log(x)");
    let fire_rs = rs("fs::write(x, x)");
    let files = [
        PathFile {
            path: "empty.py",
            language: Language::Python,
            text: "",
        },
        PathFile {
            path: "a.py",
            language: Language::Python,
            text: &fire_py,
        },
        PathFile {
            path: "b.ts",
            language: Language::TypeScript,
            text: &clean_ts,
        },
        PathFile {
            path: "c.rs",
            language: Language::Rust,
            text: &fire_rs,
        },
    ];
    let report = analyze(&files, &CohPassOptions::default());
    let mut hit: Vec<&str> = report
        .findings
        .iter()
        .filter(|f| f.rule == "COH002")
        .map(|f| f.file.as_str())
        .collect();
    hit.sort_unstable();
    assert_eq!(hit, ["a.py", "c.rs"], "{:?}", report.findings);
}

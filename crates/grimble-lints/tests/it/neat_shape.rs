//! Corpus tests for the shape NEAT rules: each bug fires its rule, each fix is quiet.

// frob:ticket 01M59QKE60PDB1GDWTDEBAQ4JG

use gob_languages::Language;
use grimble_lints::neat::{Options, Report, Rule, scan, scan_at};

fn opts() -> Options {
    Options::from_config(&[
        ("max_fn_lines", "4"),
        ("max_cognitive", "3"),
        ("raw_loop_statements", "2"),
        ("magic_values", "true"),
        ("require_effects", "true"),
    ])
    .expect("valid table")
}

fn run(src: &str) -> Report {
    scan(Language::Rust, src, &opts()).expect("corpus file parses")
}

fn fires(r: &Report, rule: Rule) -> bool {
    r.findings.iter().any(|f| f.rule == rule)
}

macro_rules! pair {
    ($name:ident, $rule:expr, $stem:literal) => {
        // frob:tests crates/grimble-lints/src/neat/mod.rs::scan
        #[test]
        fn $name() {
            let bug = run(include_str!(concat!(
                "../corpus/neat/shape/",
                $stem,
                "_bug.rs"
            )));
            assert!(fires(&bug, $rule), "{bug:?}");
            let fixed = run(include_str!(concat!(
                "../corpus/neat/shape/",
                $stem,
                "_fixed.rs"
            )));
            assert!(!fires(&fixed, $rule), "{fixed:?}");
        }
    };
}

pair!(neat001_long_function, Rule::FunctionTooLong, "neat001");
pair!(neat002_param_count, Rule::TooManyParams, "neat002");
pair!(neat003_bool_flag, Rule::BooleanFlagParam, "neat003");
pair!(neat004_nesting, Rule::NestingTooDeep, "neat004");
pair!(neat005_cognitive, Rule::CognitiveComplexity, "neat005");
pair!(neat006_raw_loop, Rule::RawLoop, "neat006");
pair!(neat007_section_comment, Rule::SectionComment, "neat007");
pair!(neat008_param_object, Rule::ParamObjectCandidate, "neat008");
pair!(neat009_magic_value, Rule::MagicValue, "neat009");
pair!(
    neat011_effects_undeclared,
    Rule::EffectsUndeclared,
    "neat011"
);
pair!(neat012_hidden_state, Rule::HiddenStateRead, "neat012");
pair!(neat013_ambient_call, Rule::AmbientSourceCall, "neat013");
pair!(neat030_thin_hook, Rule::ThinHook, "neat030");

// frob:tests crates/grimble-lints/src/neat/mod.rs::scan_at
#[test]
fn core_paths_make_unclaimed_units_honest() {
    let src = "fn f() { let _ = std::env::var(\"X\"); }\n";
    let o = Options::from_config(&[("core_paths", "src/core/")]).expect("valid");
    let core = scan_at(Language::Rust, "crates/x/src/core/a.rs", src, &o).expect("parses");
    assert!(fires(&core, Rule::EffectCeilingExceeded), "{core:?}");
    let other = scan_at(Language::Rust, "crates/x/src/shell/a.rs", src, &o).expect("parses");
    assert!(!fires(&other, Rule::EffectCeilingExceeded), "{other:?}");
}

// frob:tests crates/grimble-lints/src/neat/mod.rs::scan
#[test]
fn defaults_keep_the_off_rules_quiet() {
    let bug = scan(
        Language::Rust,
        include_str!("../corpus/neat/shape/neat009_bug.rs"),
        &Options::default(),
    )
    .expect("parses");
    assert!(!fires(&bug, Rule::MagicValue));
}

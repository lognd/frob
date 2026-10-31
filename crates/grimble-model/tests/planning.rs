//! Planning items (grmb-planning 3, 8.3, 12, 13): parsing, contextual words, fmt fixed point.

// frob:ticket 01M4FDBAAEX7HMVM8H6VKN98M6

use grimble_model::dump::u_signature;
use grimble_model::fmt::format_file;
use grimble_model::fold::fold_file;
use grimble_model::parse::parse_file;

const H: &str = "grimble = \"2\";\nmodule m;\n";

fn parse(src: &str) -> grimble_model::ast::ParsedFile {
    parse_file("m.grmb", src.as_bytes())
}

fn diag_rules(src: &str) -> Vec<String> {
    parse(src)
        .diags
        .iter()
        .map(|d| d.rule.to_string())
        .collect()
}

fn example(path: &str) -> String {
    let p = format!("{}/tests/corpus/plan/{path}", env!("CARGO_MANIFEST_DIR"));
    std::fs::read_to_string(p).expect("corpus example")
}

#[test]
// frob:tests crates/grimble-model/src/parse.rs::parse_file
fn major_two_models_may_name_nodes_system_and_page() {
    let src = format!(
        "{H}\nnode page : trusted {{\n  owns \"b/**\";\n}}\n\nnode system : trusted {{\n  owns \"a/**\";\n}}\n\nflow step : system -> page {{\n  label Internal;\n}}\n"
    );
    let f = parse(&src);
    assert!(f.diags.is_empty(), "{:?}", f.diags);
    assert_eq!(f.holes, 0);
    let out = format_file(&f).expect("fmt");
    assert_eq!(
        out, src,
        "a major-2 model is already canonical and unchanged"
    );
}

#[test]
// frob:tests crates/grimble-model/src/parse.rs::parse_file
fn planning_words_are_only_heads_at_item_position() {
    // `goal`, `actor`, `scenario` are ordinary names after a kind keyword.
    let src = format!(
        "{H}node goal : trusted {{\n}}\n\nnode actor : trusted {{\n}}\n\nnode scenario : trusted {{\n}}\n"
    );
    assert!(diag_rules(&src).is_empty());
}

#[test]
// frob:tests crates/grimble-model/src/parse.rs::parse_file
fn worked_examples_parse_without_diagnostics() {
    for p in [
        "web_app/model.grmb",
        "web_app/web_app/goals.grmb",
        "web_app/web_app/customer_flow.grmb",
        "thermostat/model.grmb",
        "thermostat/fw/thermostat.grmb",
    ] {
        let f = parse(&example(p));
        assert!(f.diags.is_empty(), "{p}: {:?}", f.diags);
        assert_eq!(f.holes, 0, "{p}");
    }
}

#[test]
// frob:tests crates/grimble-model/src/fmt.rs::format_file
fn worked_examples_format_to_a_fixed_point_preserving_u() {
    for p in [
        "web_app/model.grmb",
        "web_app/web_app/goals.grmb",
        "web_app/web_app/customer_flow.grmb",
        "thermostat/fw/thermostat.grmb",
    ] {
        let f = parse(&example(p));
        let once = format_file(&f).expect("fmt");
        let g = parse(&once);
        assert!(
            g.diags.is_empty(),
            "{p}: formatted output reparses: {:?}",
            g.diags
        );
        let twice = format_file(&g).expect("fmt again");
        assert_eq!(once, twice, "{p}: fmt is a fixed point");
        let a = fold_file(&f, "").expect("fold");
        let b = fold_file(&g, "").expect("fold");
        assert_eq!(
            u_signature(&a),
            u_signature(&b),
            "{p}: fmt preserves the term"
        );
    }
}

#[test]
// frob:tests crates/grimble-model/src/parse/plan.rs::Parser.chain
fn chain_errors_are_syntax_diagnostics() {
    for bad in [
        "step ;\n",
        "step a.b -> ;\n",
        "scenario s {\n  a.b -> ;\n}\n",
        "actor x;\n",
    ] {
        let src = format!("{H}{bad}");
        assert!(
            diag_rules(&src).iter().any(|r| r == "MDL000"),
            "expected a syntax diagnostic for {bad:?}"
        );
    }
}

#[test]
// frob:tests crates/grimble-model/src/lex.rs::Lexer.number
fn retry_bound_before_else_is_a_number_not_a_quantity() {
    let src = format!(
        "{H}system s {{\n  scenario c {{\n    a.b -> retry a.b max 2 else end ok;\n  }}\n}}\n"
    );
    assert!(diag_rules(&src).is_empty(), "{:?}", diag_rules(&src));
}

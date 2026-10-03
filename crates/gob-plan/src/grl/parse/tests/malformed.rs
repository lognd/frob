//! Malformed inputs: each produces the expected message at the expected span.

use super::{parsed, slice, wrap};

/// A malformed case: source, the first error's message, and the text its span covers.
struct Case {
    name: &'static str,
    src: String,
    message: &'static str,
    span_text: &'static str,
}

fn case(name: &'static str, body: &str, message: &'static str, span_text: &'static str) -> Case {
    Case {
        name,
        src: wrap(body),
        message,
        span_text,
    }
}

fn raw(name: &'static str, src: &str, message: &'static str, span_text: &'static str) -> Case {
    Case {
        name,
        src: src.to_owned(),
        message,
        span_text,
    }
}

const EXPLAIN: &str = "explain \"\"\"\n    ## Remedy\n  \"\"\"";

fn cases() -> Vec<Case> {
    vec![
        case(
            "find without a name",
            "find : function",
            "expected a variable name after `find`, found `:`",
            ":",
        ),
        case(
            "find without a colon",
            "find f function",
            "expected `:` after the variable name, found `function`",
            "function",
        ),
        case(
            "find without a source",
            "find f:\n  report f \"x\"",
            "expected a kind such as `function`, a snippet, or `(` shapes `)`, found `report`",
            "report",
        ),
        case(
            "where without a condition",
            "where\n  report f \"x\"",
            "expected a value: a name such as `f.name`, a number, a string, `knob.NAME` or `count(...)`, found `report`",
            "report",
        ),
        case(
            "is without a test",
            "where f is\n  report f \"x\"",
            "expected a kind or boolean field after `is`, found `report`",
            "report",
        ),
        case(
            "inside without an object",
            "where f inside\n  report f \"x\"",
            "expected a value: a name such as `f.name`, a number, a string, `knob.NAME` or `count(...)`, found `report`",
            "report",
        ),
        case(
            "report without a message",
            "report f",
            "expected the message in quotes after the variable, found `explain`",
            "explain",
        ),
        case(
            "report when without a condition",
            "report f \"x\" when",
            "expected a value: a name such as `f.name`, a number, a string, `knob.NAME` or `count(...)`, found `explain`",
            "explain",
        ),
        case(
            "fix replacement is not a snippet",
            "fix f -> \"text\" [machine]",
            "expected the replacement snippet in backticks after `->`, found a string",
            "\"text\"",
        ),
        case(
            "fix applicability misspelt",
            "fix f -> `x` [mashine]",
            "`mashine` is not a fix applicability; the choices are `machine`, `maybe-incorrect` and `has-placeholders`",
            "mashine",
        ),
        case(
            "fix delete without a target",
            "fix delete",
            "expected the variable to delete, after `fix delete`, found `explain`",
            "explain",
        ),
        case(
            "def without parameters",
            "def f = x",
            "expected `(` and the parameters after the def name, found `=`",
            "=",
        ),
        case(
            "unresolved without because",
            "unresolved when f is public",
            "expected `because \"reason\"` after the condition, found `explain`",
            "explain",
        ),
        case(
            "knob with an unknown type",
            "knob d: integer = 1 \"x\"",
            "`integer` is not a knob type; the choices are `int`, `float`, `string`, `bool`, `glob`, `regex`, `vocab` and `list<T>`",
            "integer",
        ),
        case(
            "knob without a description",
            "knob d: int = 1",
            "expected the knob's description in quotes after its value, found `explain`",
            "explain",
        ),
        case(
            "list type glued to equals",
            "knob d: list<int>= [1] \"x\"",
            "expected `>` to close `list<...>`, found `>=`",
            ">=",
        ),
        case(
            "interpolation in a knob value",
            "knob d: string = \"a{b}\" \"x\"",
            "`{...}` is not allowed in a knob value",
            "{b}",
        ),
        case(
            "interpolation in a glob",
            "where p matches \"src/{a,b}/*\"",
            "`{...}` is not allowed in a comparison, glob or path",
            "{a,b}",
        ),
        case(
            "interpolation in a shape path",
            "find k: key(path = \"/a/{x}\")",
            "`{...}` is not allowed in a field value (a path or glob)",
            "{x}",
        ),
        case(
            "interpolation holding an expression",
            "report f \"{f.name + 1}\"",
            "an interpolation holds a field, knob or witness such as `{x.name}`, not this",
            "f.name + 1",
        ),
        case(
            "severity not in the set",
            "severity fatal",
            "`fatal` is not a severity; the choices are `error`, `warn` and `advisory`",
            "fatal",
        ),
        case(
            "polarity not in the set",
            "polarity plus",
            "expected a polarity: `P+`, `P-`, `P0`, `Pn` or `Pc`, found `plus`",
            "plus",
        ),
        case(
            "scope not in the set",
            "scope everywhere",
            "`everywhere` is not a scope; the choices are `file` and `repo`",
            "everywhere",
        ),
        case(
            "quoted language",
            "lang \"rust\"",
            "expected a language id such as `rust`, `*`, `-` or `[rust, python]`, found a string",
            "\"rust\"",
        ),
        case(
            "unclosed language list",
            "lang [rust\n  severity error",
            "expected `,` or `]` in the language list, found `severity`",
            "severity",
        ),
        case(
            "example without a body",
            "example fire rust",
            "expected `{` or a triple-quoted block holding the example's source, found `explain`",
            "explain",
        ),
        case(
            "example outcome not in the set",
            "example maybe rust \"\"\"\n    x\n  \"\"\"",
            "`maybe` is not an example outcome; the choices are `fire`, `clean`, `unresolved`, `notapplicable` and `known-gap`",
            "maybe",
        ),
        case(
            "example file text is not a block",
            "example fire { file \"a\" \"text\" }",
            "expected the file's text as a triple-quoted block, found a string",
            "\"text\"",
        ),
        case(
            "unknown example input",
            "example fire { bogus }",
            "expected an input (`file`, `config`, `model`, `diff`, `lease`, `expect` or `fixed`) or `}`, found `bogus`",
            "bogus",
        ),
        case(
            "empty any",
            "where any {}",
            "`any` needs at least one condition inside its braces",
            "any {}",
        ),
        case(
            "count without a colon",
            "where count(f function) > 1",
            "expected `:` after the variable name, found `function`",
            "function",
        ),
        case(
            "reaches without via",
            "where a reaches b calls",
            "expected `via` and the verbs to follow, as in `reaches f via calls within 6`, found `calls`",
            "calls",
        ),
        case(
            "not without an operand",
            "where not",
            "expected a value: a name such as `f.name`, a number, a string, `knob.NAME` or `count(...)`, found `explain`",
            "explain",
        ),
        case(
            "empty alternative",
            "find f: (function | )",
            "expected a kind such as `function`, a snippet, or `(` shapes `)`, found `)`",
            ")",
        ),
        case(
            "unclosed parenthesis",
            "where (a == 1",
            "expected `)` to close the condition, found `explain`",
            "explain",
        ),
        case(
            "stray word after a condition",
            "where f has attr x",
            "expected a header, a clause, an `example` or `explain`, found `x`",
            "x",
        ),
        case(
            "header after a clause",
            "find f: function\n  severity error",
            "a header (`severity`) must come before the clauses in a rule",
            "severity",
        ),
        case(
            "clause after an example",
            "example clean \"\"\"\n    x\n  \"\"\"\n  find f: function",
            "a clause (`find`) must come before the examples in a rule",
            "find",
        ),
        case(
            "unterminated string is a lexical error",
            "report f \"oops",
            "this string is never closed",
            "\"oops",
        ),
        raw(
            "top level junk",
            "find x: y\n",
            "expected `rule` to start a rule, found `find`",
            "find",
        ),
        raw(
            "rule id missing",
            "rule \"x\" {\n}\n",
            "expected a rule id such as `TODO001` after `rule`, found a string",
            "\"x\"",
        ),
        raw(
            "rule slug missing",
            "rule ABC001 {\n}\n",
            "expected the rule's slug in quotes after its id, found `{`",
            "{",
        ),
        raw(
            "rule body never opened",
            "rule ABC001 \"a\" lang rust\n",
            "expected `{` to open the rule body, found `lang`",
            "lang",
        ),
        raw(
            "rule never closed",
            "rule ABC001 \"a\" {\n  lang rust\n  explain \"\"\"\n    ## Remedy\n  \"\"\"\n",
            "this rule is never closed",
            "{",
        ),
        raw(
            "rule without explain",
            "rule ABC001 \"a\" {\n  lang rust\n}\n",
            "rule `ABC001` has no `explain` block",
            "}",
        ),
        Case {
            name: "second explain",
            src: format!("rule ABC001 \"a\" {{\n  lang rust\n  {EXPLAIN}\n  {EXPLAIN}\n}}\n"),
            message: "a rule has exactly one `explain` block",
            span_text: "explain",
        },
    ]
}

// frob:tests crates/gob-plan/src/grl/parse/mod.rs::parse
#[test]
fn every_malformed_input_reports_its_message_at_its_span() {
    let cases = cases();
    assert!(cases.len() >= 25, "need at least 25 malformed inputs");
    let mut failures = Vec::new();
    for c in &cases {
        let p = parsed(&c.src);
        let Some(first) = p.errors.first() else {
            failures.push(format!("{}: no error", c.name));
            continue;
        };
        let got = first.to_string();
        let text = slice(&c.src, first.span);
        if got != c.message || text != c.span_text {
            failures.push(format!(
                "{}:\n  message {got:?}\n  expected {:?}\n  span {text:?} expected {:?}",
                c.name, c.message, c.span_text
            ));
        }
    }
    assert!(failures.is_empty(), "{}", failures.join("\n"));
}

// frob:tests crates/gob-plan/src/grl/parse/mod.rs::parse
#[test]
fn several_errors_in_one_file_are_all_reported() {
    let src = "rule ABC001 \"a\" {\n  lang rust\n  find : function\n  find ok: function\n  report ok\n  severity fatal\n  where ok is public\n  explain \"\"\"\n    ## Remedy\n  \"\"\"\n}\n\nrule DEF002 \"b\" {\n  lang \"rust\"\n  find g: function where\n  explain \"\"\"\n    ## Remedy\n  \"\"\"\n}\n";
    let p = parsed(src);
    let msgs: Vec<String> = p.errors.iter().map(ToString::to_string).collect();
    assert!(p.errors.len() >= 5, "{msgs:#?}");
    // Both rules survive, and the good clauses between the bad ones are kept.
    assert_eq!(p.file.rules.len(), 2);
    assert_eq!(
        p.file.rules[0].clauses.len(),
        2,
        "find ok and where ok survive"
    );
    // Errors arrive in source order.
    let starts: Vec<u32> = p
        .errors
        .iter()
        .map(|e| u32::from(e.span.range.start()))
        .collect();
    let mut sorted = starts.clone();
    sorted.sort_unstable();
    assert_eq!(starts, sorted);
}

#[test]
fn every_error_has_a_help_line_or_is_self_explanatory() {
    let p = parsed(&wrap("knob d: string = \"a{b}\" \"x\""));
    assert_eq!(
        p.errors[0].help().as_deref(),
        Some(
            "only report, note and fix messages interpolate; write `\\{` and `\\}` for literal braces"
        )
    );
    let p = parsed("find x: y\n");
    assert_eq!(
        p.errors[0].help().as_deref(),
        Some("a file holds rules: `rule ID \"slug\" { ... }`")
    );
}

#[test]
fn deeply_nested_input_is_an_error_not_a_crash() {
    let deep = format!("where {}a == 1{}", "(".repeat(500), ")".repeat(500));
    let p = parsed(&wrap(&deep));
    assert!(
        p.errors
            .iter()
            .any(|e| e.to_string().contains("nested too deeply"))
    );
}

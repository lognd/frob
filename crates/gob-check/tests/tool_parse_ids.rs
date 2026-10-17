//! Tool parsing names rules through their `#[rule]` declarations, never through id string literals.

// frob:ticket 01M48R03ZFTPSDD33HMJBD7STD

use std::path::Path;

/// Whether `s` has the shape of a rule id: 2-6 capitals then 3 digits.
fn is_rule_id(s: &str) -> bool {
    let letters = s.bytes().take_while(u8::is_ascii_uppercase).count();
    (2..=6).contains(&letters)
        && s.len() == letters + 3
        && s[letters..].bytes().all(|b| b.is_ascii_digit())
}

/// Every double-quoted literal in the non-test part of `file` that looks like a rule id.
fn id_literals(file: &str) -> Vec<String> {
    let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("src").join(file);
    let text = std::fs::read_to_string(&path).expect("read source");
    let code = text.split("#[cfg(test)]").next().unwrap_or_default();
    code.lines()
        .filter(|l| !l.trim_start().starts_with("//"))
        .flat_map(|l| {
            l.split('"')
                .skip(1)
                .step_by(2)
                .map(str::to_owned)
                .collect::<Vec<_>>()
        })
        .filter(|s| is_rule_id(s))
        .collect()
}

// frob:tests crates/gob-check/src/tool_parse.rs::classify
// frob:tests crates/gob-check/src/tool_parse.rs::default_id_map
#[test]
fn tool_parsing_has_no_rule_id_string_literal() {
    for file in [
        "tool_parse.rs",
        "tool_bind.rs",
        "tools.rs",
        "required.rs",
        "pipeline.rs",
        "repo.rs",
    ] {
        let found = id_literals(file);
        assert!(
            found.is_empty(),
            "{file} spells rule ids as literals: {found:?}"
        );
    }
}

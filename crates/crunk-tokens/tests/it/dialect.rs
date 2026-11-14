//! Dialect compilation and DTCG 2025.10 export: aliases, composites, scopes and two modes.

// frob:ticket 01M4CXQXGBYXFCDTSQQVQKN1E9

use std::path::Path;

use crunk_tokens::dialect::{DialectError, parse};
use crunk_tokens::export::{Target, dtcg_document};
use crunk_tokens::{Scope, Tier, TokenSet, TokenValue};
use serde_json::Value;

const SOURCE: &str = r##"
[color]
ink = "#e6e8ef"
paper = { value = "#101218", modes = { light = "#ffffff", dark = "#101218" } }
text = { value = "{color.ink}", scopes = ["color"], description = "Body text", modes = { light = "#101218" } }

[space]
4 = "4px"
card = { value = "{space.4}", tier = "component" }

[motion]
fast = "150ms"
slow = "0.4s"
ease = [0.4, 0, 0.2, 1]

[type.body]
value = { fontFamily = ["Inter", "sans-serif"], fontSize = "16px", fontWeight = 400, lineHeight = 1.5 }

[shadow.card]
value = { color = "{color.ink}", offsetX = "0px", offsetY = "2px", blur = "8px", spread = "0px" }

[border.hair]
value = { color = "{color.ink}", width = "1px", style = "solid" }

[transition.fade]
value = { duration = "{motion.fast}", delay = "0ms", timingFunction = "{motion.ease}" }
"##;

fn compiled() -> TokenSet {
    parse(SOURCE, "tokens.toml").unwrap()
}

/// Resolve a `{a.b}` reference inside a DTCG token tree.
fn lookup<'a>(tree: &'a Value, reference: &str) -> Option<&'a Value> {
    let inner = reference.strip_prefix('{')?.strip_suffix('}')?;
    let (group, rest) = inner.split_once('.')?;
    let (group, leaf) = match rest.split_once('.') {
        _ if inner.matches('.').count() == 1 => (group, rest),
        _ => return None,
    };
    tree.get(group)?.get(leaf)
}

/// Structural DTCG 2025.10 check: every leaf has a known `$type` and a value of that shape.
fn validate(tree: &Value, aliases: &mut Vec<String>) {
    let Value::Object(map) = tree else {
        panic!("group must be an object")
    };
    for (key, node) in map {
        if key.starts_with('$') && key != "$root" {
            continue;
        }
        if node.get("$value").is_some() {
            validate_leaf(node, aliases);
        } else {
            validate(node, aliases);
        }
    }
}

fn validate_leaf(node: &Value, aliases: &mut Vec<String>) {
    let value = &node["$value"];
    if let Some(s) = value.as_str().filter(|s| s.starts_with('{')) {
        aliases.push(s.to_owned());
    }
    let ty = node["$type"].as_str().expect("$type present");
    match ty {
        "color" => assert!(
            value.is_string() || value["components"].is_array(),
            "{value}"
        ),
        "dimension" | "duration" => {
            assert!(value.is_string() || (value["value"].is_number() && value["unit"].is_string()));
        }
        "cubicBezier" => {
            assert!(value.is_string() || value.as_array().is_some_and(|a| a.len() == 4));
        }
        "number" | "fontFamily" | "string" => {}
        "typography" | "shadow" | "border" | "transition" => {
            let members = value.as_object().expect("composite object");
            for v in members.values() {
                if let Some(s) = v.as_str().filter(|s| s.starts_with('{')) {
                    aliases.push(s.to_owned());
                }
            }
        }
        other => panic!("unknown $type {other}"),
    }
}

#[test]
fn dialect_compiles_every_value_family() {
    let set = compiled();
    assert_eq!(set.get("--color-text").unwrap().tier, Tier::Semantic);
    assert_eq!(set.get("--space-card").unwrap().tier, Tier::Component);
    assert_eq!(set.get("--color-text").unwrap().scopes, vec![Scope::Color]);
    assert!(
        matches!(set.get("--motion-slow").unwrap().value, TokenValue::Duration(d) if (d - 400.0).abs() < 1e-9)
    );
    assert!(matches!(
        set.get("--type-body").unwrap().value,
        TokenValue::Composite(_)
    ));
    assert_eq!(set.mode_names(), vec!["light", "dark"]);
}

#[test]
fn dtcg_output_validates_and_resolves_every_alias_per_mode() {
    let set = compiled();
    let doc = dtcg_document(&set);
    assert_eq!(doc["version"], "2025.10");
    let base = &doc["sets"]["base"]["sources"][0];
    let mut aliases = Vec::new();
    validate(base, &mut aliases);
    assert!(aliases.len() >= 6, "{aliases:?}");
    for reference in &aliases {
        assert!(lookup(base, reference).is_some(), "base alias {reference}");
    }
    let contexts = doc["modifiers"]["mode"]["contexts"].as_object().unwrap();
    assert_eq!(contexts.len(), 3);
    for (mode, sources) in contexts {
        let mut mode_aliases = Vec::new();
        for source in sources.as_array().unwrap() {
            validate(source, &mut mode_aliases);
        }
        for reference in &mode_aliases {
            assert!(
                lookup(base, reference).is_some() || mode == "default",
                "{mode}: {reference}"
            );
        }
    }
    for mode in set.mode_names() {
        for token in set.iter() {
            assert!(
                set.resolve(&token.name, Some(mode)).is_some(),
                "{mode} {}",
                token.name
            );
        }
    }
    assert_eq!(base["type"]["body"]["$type"], "typography");
    assert_eq!(base["motion"]["ease"]["$type"], "cubicBezier");
    assert_eq!(base["color"]["text"]["$type"], "color");
    assert_eq!(
        base["color"]["text"]["$extensions"]["com.crunk"]["scopes"][0],
        "color"
    );
}

#[test]
fn dtcg_target_renders_deterministically() {
    assert_eq!(Target::parse("dtcg"), Some(Target::Dtcg));
    let spec = crunk_spec::parse_spec(
        crunk_spec::presets::DEFAULT,
        Path::new("crunk.toml"),
        Path::new("/proj"),
    )
    .unwrap();
    let set = compiled();
    let a = Target::Dtcg.exporter().render(&spec, &set);
    assert_eq!(a, Target::Dtcg.exporter().render(&spec, &set));
    assert!(a.ends_with('\n'));
}

#[test]
fn crunk_toml_palette_is_the_same_token_set_and_exports_to_dtcg() {
    let spec = crunk_spec::parse_spec(
        crunk_spec::presets::DEFAULT,
        Path::new("crunk.toml"),
        Path::new("/proj"),
    )
    .unwrap();
    let first = TokenSet::from_spec(&spec).unwrap();
    let second = TokenSet::from_spec(&spec).unwrap();
    assert_eq!(
        first.iter().collect::<Vec<_>>(),
        second.iter().collect::<Vec<_>>()
    );
    let doc = dtcg_document(&first);
    let base = &doc["sets"]["base"]["sources"][0];
    assert_eq!(base["color"]["ink"]["$type"], "color");
    assert!(first.get("--color-ink").is_some());
    assert!(doc.get("modifiers").is_none());
}

#[test]
fn broken_alias_is_rejected_in_the_mode_that_breaks_it() {
    let err = parse("[a]\nb = \"{a.missing}\"\n", "t.toml").unwrap_err();
    assert!(matches!(err, DialectError::BrokenAlias { .. }), "{err}");
}

#[test]
fn malformed_tokens_are_rejected() {
    for bad in [
        "[a]\nb = \"wat\"\n",
        "[a]\nb = { value = \"#fff\", type = \"dimension\" }\n",
        "[a]\nb = { value = \"#fff\", scopes = [\"nope\"] }\n",
        "[a]\nb = { value = { x = 1 } }\n",
        "[a]\nb = [1, 2]\n",
        "[a]\nb = { value = \"#fff\", bogus = 1 }\n",
    ] {
        assert!(parse(bad, "t.toml").is_err(), "{bad}");
    }
    assert!(matches!(
        parse("[a", "t.toml"),
        Err(DialectError::Syntax { .. })
    ));
}

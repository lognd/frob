//! Token model tests: corpus parity with the Python token list and theme mapping, the alpha
//! companions, collision errors and the DTCG-shaped value types.

// frob:ticket 01M43ARZAJ8NJ3F38157ERAKR5

use std::path::{Path, PathBuf};

use crunk_spec::{DesignSpec, parse_spec};
use crunk_tokens::{
    ThemeSection, TokenError, TokenKind, TokenSet, TokenValue, Unit, model::Tier, naming,
};
use serde_json::Value;

fn spec_fixtures() -> Vec<PathBuf> {
    let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("../crunk-spec/tests/fixtures/valid");
    let mut files: Vec<PathBuf> = std::fs::read_dir(&dir)
        .expect("crunk-spec fixtures")
        .map(|e| e.expect("entry").path())
        .filter(|p| p.extension().is_some_and(|e| e == "toml"))
        .collect();
    files.sort();
    files
}

fn load(text: &str) -> DesignSpec {
    parse_spec(text, Path::new("crunk.toml"), Path::new("/proj"))
        .unwrap_or_else(|e| panic!("expected a valid spec: {e}"))
}

fn variant(spec: &DesignSpec, namespaced: bool, alpha: bool) -> DesignSpec {
    let mut spec = spec.clone();
    spec.tailwind.namespace_keys = namespaced;
    spec.tailwind.alpha_channels = alpha;
    spec
}

// frob:tests crates/crunk-tokens/src/model.rs::TokenSet
// frob:tests crates/crunk-tokens/src/model.rs::TokenSet.css_entries
// frob:tests crates/crunk-tokens/src/model.rs::TokenSet.theme_mapping
#[test]
fn every_fixture_equals_the_python_token_list_and_theme_mapping() {
    let files = spec_fixtures();
    assert!(files.len() >= 7, "corpus shrank: {files:?}");
    for toml in files {
        let name = toml.file_stem().unwrap().to_string_lossy().into_owned();
        let base = load(&std::fs::read_to_string(&toml).unwrap());
        let reference: Value = serde_json::from_str(
            &std::fs::read_to_string(
                Path::new(env!("CARGO_MANIFEST_DIR"))
                    .join("tests/fixtures")
                    .join(format!("{name}.tokens.json")),
            )
            .unwrap_or_else(|e| panic!("{name}: missing reference (run dump_tokens.py): {e}")),
        )
        .unwrap();
        for (label, ns, alpha) in [
            ("ns0_a0", false, false),
            ("ns0_a1", false, true),
            ("ns1_a0", true, false),
            ("ns1_a1", true, true),
        ] {
            let spec = variant(&base, ns, alpha);
            let tokens = TokenSet::from_spec(&spec).unwrap();
            let py = &reference[label];
            let want_entries: Vec<(String, String)> = py["entries"]
                .as_array()
                .unwrap()
                .iter()
                .map(|p| {
                    (
                        p[0].as_str().unwrap().to_owned(),
                        p[1].as_str().unwrap().to_owned(),
                    )
                })
                .collect();
            let got_entries: Vec<(String, String)> = tokens
                .css_entries()
                .into_iter()
                .map(|(n, v)| (n.to_owned(), v))
                .collect();
            assert_eq!(got_entries, want_entries, "{name} {label}: entries");
            // serde_json sorts object keys, so the mapping is compared as a sorted set; the
            // merge order only matters for collisions, which the values themselves reveal.
            let want_theme: Vec<(String, String)> = py["theme"]
                .as_object()
                .unwrap()
                .iter()
                .map(|(k, v)| (k.clone(), v.as_str().unwrap().to_owned()))
                .collect();
            let mut got_theme: Vec<(String, String)> =
                tokens.theme_mapping(ns, alpha).into_iter().collect();
            got_theme.sort();
            assert_eq!(got_theme, want_theme, "{name} {label}: theme mapping");
        }
    }
}

// frob:tests crates/crunk-tokens/src/model.rs::TokenSet.from_spec
#[test]
fn alpha_channels_gives_every_color_an_rgb_companion() {
    let spec = variant(&load(crunk_spec::presets::DEFAULT), false, true);
    let tokens = TokenSet::from_spec(&spec).unwrap();
    let colors: Vec<_> = tokens.of_kind(TokenKind::Color).collect();
    assert!(!colors.is_empty());
    for color in colors {
        let companion = tokens
            .get(&naming::channels_name(&color.name))
            .unwrap_or_else(|| panic!("no -rgb companion for {}", color.name));
        assert_eq!(companion.kind, TokenKind::ColorChannels);
        assert!(matches!(companion.value, TokenValue::Channels { .. }));
    }
    let off = TokenSet::from_spec(&variant(&spec, false, false)).unwrap();
    assert_eq!(off.of_kind(TokenKind::ColorChannels).count(), 0);
}

// frob:tests crates/crunk-tokens/src/model.rs::TokenSet.from_spec
#[test]
fn colliding_palette_names_are_a_typed_error_naming_both() {
    let text = format!(
        "{}\n",
        crunk_spec::presets::DEFAULT.replacen(
            "[palette]\n",
            "[palette]\n\"deep sky\" = \"#112233\"\n\"deep.sky\" = \"#445566\"\n",
            1
        )
    );
    let spec = load(&text);
    let err = TokenSet::from_spec(&spec).unwrap_err();
    let TokenError::Collision {
        name,
        first,
        second,
    } = &err;
    assert_eq!(name, "--color-deep-sky");
    assert_eq!(first, "[palette] deep sky");
    assert_eq!(second, "[palette] deep.sky");
    assert!(err.to_string().contains("[palette] deep sky"));
    assert!(err.to_string().contains("[palette] deep.sky"));
}

// frob:tests crates/crunk-tokens/src/model.rs::TokenSet.from_spec
#[test]
fn a_stack_named_base_collides_with_the_base_family() {
    let mut spec = load(crunk_spec::presets::DEFAULT);
    spec.typography
        .stacks
        .insert("base".to_owned(), spec.typography.families.clone());
    let TokenError::Collision {
        name,
        first,
        second,
    } = TokenSet::from_spec(&spec).unwrap_err();
    assert_eq!(name, "--font-family-base");
    assert_eq!(first, "[typography] families");
    assert_eq!(second, "[typography.stacks] base");
}

// frob:tests crates/crunk-tokens/src/model.rs::TokenSet.default_theme_collisions
#[test]
fn bare_keys_collide_with_tailwind_defaults_only_when_not_namespaced() {
    let spec = load(crunk_spec::presets::DEFAULT);
    let tokens = TokenSet::from_spec(&spec).unwrap();
    assert!(tokens.default_theme_collisions(true).is_empty());
    let collisions = tokens.default_theme_collisions(false);
    assert!(
        collisions
            .iter()
            .any(|c| c.section == ThemeSection::Spacing && c.key == "4"),
        "{collisions:?}"
    );
}

// frob:tests crates/crunk-tokens/src/model.rs::TokenValue.css
#[test]
fn value_types_render_css() {
    let px = |value| TokenValue::Dimension {
        value,
        unit: Unit::Px,
    };
    assert_eq!(px(16.0).css().unwrap(), "16px");
    assert_eq!(px(6.5).css().unwrap(), "6.5px");
    assert_eq!(px(-0.0).css().unwrap(), "0px");
    assert_eq!(TokenValue::Number(300).css().unwrap(), "300");
    assert_eq!(
        TokenValue::FontFamily(vec!["Inter".into(), "Segoe UI".into()])
            .css()
            .unwrap(),
        "Inter, \"Segoe UI\""
    );
    assert_eq!(TokenValue::Duration(200.0).css().unwrap(), "200ms");
    assert_eq!(
        TokenValue::CubicBezier([0.4, 0.0, 0.2, 1.0]).css().unwrap(),
        "cubic-bezier(0.4, 0, 0.2, 1)"
    );
    assert_eq!(
        TokenValue::Alias("--color-ink".into()).css().unwrap(),
        "var(--color-ink)"
    );
    assert_eq!(TokenValue::Composite(indexmap::IndexMap::new()).css(), None);
}

// frob:tests crates/crunk-tokens/src/model.rs::Token
#[test]
fn spec_tokens_are_unscoped_primitives_without_modes() {
    let tokens = TokenSet::from_spec(&load(crunk_spec::presets::DEFAULT)).unwrap();
    assert!(!tokens.is_empty());
    for token in tokens.iter() {
        assert_eq!(token.tier, Tier::Primitive);
        assert!(token.modes.is_empty() && token.scopes.is_empty());
    }
    assert_eq!(tokens.len(), tokens.names().len());
    assert!(tokens.json_keys().all(|k| !k.starts_with("--")));
}

// frob:tests crates/crunk-tokens/src/naming.rs::scale_key
// frob:tests crates/crunk-tokens/src/naming.rs::bare_name
// frob:tests crates/crunk-tokens/src/naming.rs::channels_name
// frob:tests crates/crunk-tokens/src/naming.rs::var_ref
#[test]
fn naming_helpers() {
    assert_eq!(naming::channels_name("--color-ink"), "--color-ink-rgb");
    assert_eq!(naming::bare_name("--space-8"), "space-8");
    assert_eq!(naming::bare_name("space-8"), "space-8");
    assert_eq!(naming::var_ref("--space-8"), "var(--space-8)");
    assert_eq!(naming::scale_key("8", "--space-8", true), "space-8");
    assert_eq!(naming::scale_key("8", "--space-8", false), "8");
}

// frob:tests crates/crunk-tokens/src/model.rs::ThemeSection.name
#[test]
fn theme_sections_carry_tailwind_names() {
    let names: Vec<&str> = crunk_tokens::THEME_SECTIONS
        .iter()
        .map(|s| s.name())
        .collect();
    assert_eq!(
        names,
        [
            "colors",
            "spacing",
            "fontSize",
            "borderRadius",
            "zIndex",
            "width",
            "height",
            "minWidth",
            "minHeight",
            "maxWidth",
            "maxHeight"
        ]
    );
}

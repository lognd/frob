//! USS and C# exporter tests: a two-mode token set renders deterministic files pinned by goldens.
//! Set `CRUNK_UPDATE_GOLDEN=1` to rewrite the goldens after an intended change.

// frob:ticket 01M4CXQZEYWB5WNCMFXYCNEE4J

use std::path::{Path, PathBuf};

use crunk_tokens::export::Target;
use crunk_tokens::{Tier, Token, TokenKind, TokenSet, TokenValue, Unit};
use crunk_values::Color;
use indexmap::IndexMap;

fn token(name: &str, kind: TokenKind, value: TokenValue, modes: &[(&str, TokenValue)]) -> Token {
    Token {
        name: name.to_owned(),
        kind,
        key: name.trim_start_matches("--").to_owned(),
        origin: format!("test {name}"),
        tier: Tier::Primitive,
        value,
        modes: modes
            .iter()
            .map(|(m, v)| ((*m).to_owned(), v.clone()))
            .collect::<IndexMap<_, _>>(),
        scopes: Vec::new(),
        description: None,
        deprecated: None,
    }
}

fn color(hex: &str) -> TokenValue {
    TokenValue::Color(Color::parse(hex).unwrap())
}

fn px(value: f64) -> TokenValue {
    TokenValue::Dimension {
        value,
        unit: Unit::Px,
    }
}

fn two_mode_set() -> TokenSet {
    TokenSet::from_tokens([
        token(
            "--color-ink",
            TokenKind::Color,
            color("#1a1a1a"),
            &[
                ("dark", color("#f5f5f5")),
                ("high-contrast", color("#000000")),
            ],
        ),
        token(
            "--color-paper",
            TokenKind::Color,
            color("#ffffff"),
            &[("dark", color("#101010"))],
        ),
        token(
            "--color-text",
            TokenKind::Color,
            TokenValue::Alias("--color-ink".into()),
            &[],
        ),
        token(
            "--space-6_5",
            TokenKind::Space,
            px(6.5),
            &[("high-contrast", px(8.0))],
        ),
        token("--space-8", TokenKind::Space, px(8.0), &[]),
        token(
            "--layer-modal",
            TokenKind::Layer,
            TokenValue::Number(40),
            &[],
        ),
        token(
            "--duration-fast",
            TokenKind::Space,
            TokenValue::Duration(150.0),
            &[],
        ),
        token(
            "--font-base",
            TokenKind::FontFamily,
            TokenValue::FontFamily(vec!["Inter".into(), "system-ui".into()]),
            &[],
        ),
    ])
    .unwrap()
}

fn spec() -> crunk_spec::DesignSpec {
    crunk_spec::parse_spec(
        crunk_spec::presets::DEFAULT,
        Path::new("crunk.toml"),
        Path::new("/proj"),
    )
    .unwrap()
}

fn golden(name: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures")
        .join(name)
}

fn pin(name: &str, got: &str) {
    let path = golden(name);
    if std::env::var_os("CRUNK_UPDATE_GOLDEN").is_some() {
        std::fs::write(&path, got).unwrap();
    }
    let want = std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("{name}: {e}"));
    assert_eq!(got, want, "{name} drifted from its golden");
}

// frob:tests crates/crunk-tokens/src/export/uss.rs::UssExporter
// frob:tests crates/crunk-tokens/src/export/csharp.rs::CsharpExporter
#[test]
fn two_modes_export_to_uss_and_csharp_deterministically() {
    let tokens = two_mode_set();
    let spec = spec();
    let uss = Target::Uss.exporter().render(&spec, &tokens);
    let cs = Target::Csharp.exporter().render(&spec, &tokens);
    assert_eq!(uss, Target::Uss.exporter().render(&spec, &tokens));
    assert_eq!(cs, Target::Csharp.exporter().render(&spec, &tokens));
    pin("two_modes.uss", &uss);
    pin("two_modes.cs", &cs);
}

// frob:tests crates/crunk-tokens/src/model.rs::TokenSet.resolve
#[test]
fn resolve_follows_aliases_per_mode_and_rejects_cycles() {
    let tokens = two_mode_set();
    assert_eq!(
        tokens.resolve("--color-text", Some("dark")),
        Some(&color("#f5f5f5"))
    );
    assert_eq!(
        tokens.resolve("--color-text", None),
        Some(&color("#1a1a1a"))
    );
    let cyc = TokenSet::from_tokens([
        token(
            "--a",
            TokenKind::Color,
            TokenValue::Alias("--b".into()),
            &[],
        ),
        token(
            "--b",
            TokenKind::Color,
            TokenValue::Alias("--a".into()),
            &[],
        ),
    ])
    .unwrap();
    assert_eq!(cyc.resolve("--a", None), None);
}

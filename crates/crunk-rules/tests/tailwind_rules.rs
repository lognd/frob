//! TW001-005 against throwaway projects, porting the Python crunk semantics: arbitrary values off
//! their scales, theme entries naming unexported tokens, alpha with no placeholder, and default
//! colours and scales leaking through.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

mod support;

use support::{Setup, build, setup};

use crunk_rules::rules::{tw001::Tw001, tw002::Tw002, tw003::Tw003, tw004::Tw004, tw005::Tw005};

/// The Python fixture: no layers, a small spacing scale, three palette colours.
const BASE: &str = "[project]\ncss_root = \"styles\"\ntokens_file = \"tokens.css\"\nroot_font_size = 16\n\n\
[palette]\nink = \"#1a1a1a\"\npaper = \"#fafaf7\"\naccent = \"#2f6fed\"\n\n\
[scales]\nspacing = [0, 4, 8, 12, 16]\nfont_sizes = [12, 16, 20]\nradii = [0, 4, 8]\n\n[typography]\nfamilies = [\"Inter\"]\nweights = [400]\n\n[org]\nbuckets = [\"base\", \"components\"]\nclass_case = \"kebab\"\n";

fn tsx(class: &str) -> String {
    format!("export const A = () => <div className=\"{class}\" />;")
}

fn custom(extra: &str, tailwind: Option<&'static str>) -> Setup<'static> {
    Setup {
        base_toml: Some(BASE),
        extra_toml: extra.to_owned(),
        tailwind_config: tailwind,
        ..Setup::default()
    }
}

fn messages<R: gob_rules::RepoRule<support::Project> + Default>(
    class: &str,
    s: &Setup<'_>,
) -> Vec<String> {
    let host = build("src/a.tsx", &tsx(class), s);
    support::run::<R>(&host)
        .into_iter()
        .map(|f| f.message)
        .collect()
}

const THEME_RED: &str =
    "module.exports = { theme: { extend: { colors: { \"red-500\": \"#ff0000\" } } } };\n";
const THEME_SPACING_4: &str =
    "module.exports = { theme: { extend: { spacing: { 4: \"1rem\" } } } };\n";
const THEME_WIDTH_64: &str =
    "module.exports = { theme: { extend: { width: { 64: \"16rem\" } } } };\n";

// frob:tests crates/crunk-rules/src/rules/tw001.rs::Tw001
#[test]
fn an_off_scale_arbitrary_length_fires_tw001() {
    let host = support::project("src/a.tsx", &tsx("p-[13px]"), None);
    let found = support::run::<Tw001>(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(
        found[0].message.contains("p-[13px]"),
        "{}",
        found[0].message
    );
}

// frob:tests crates/crunk-rules/src/rules/tw001.rs::Tw001
// frob:tests crates/crunk-rules/src/tailwind/mod.rs::scale_and_token
// frob:tests crates/crunk-rules/src/tailwind/mod.rs::sites
#[test]
fn tw001_names_the_bracketing_and_nearest_space_tokens() {
    let m = messages::<Tw001>("p-[13px]", &custom("", None));
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(
        m[0].contains("--space-12") && m[0].contains("--space-16"),
        "{}",
        m[0]
    );
    assert!(m[0].contains("nearest is --space-12"), "{}", m[0]);
}

// frob:tests crates/crunk-rules/src/rules/tw001.rs::Tw001
#[test]
fn tw001_on_scale_and_exempt_values_are_clean() {
    for class in [
        "p-[8px]",
        "opacity-[.5]",
        "max-w-[900px]",
        "p-4",
        "bg-[#2f6fed]",
    ] {
        assert!(
            messages::<Tw001>(class, &custom("", None)).is_empty(),
            "{class}"
        );
    }
}

// frob:tests crates/crunk-rules/src/rules/tw001.rs::Tw001
#[test]
fn tw001_judges_radius_font_size_and_size_families() {
    let m = messages::<Tw001>("rounded-[3px]", &custom("", None));
    assert!(m[0].contains("--radius-"), "{m:?}");
    let m = messages::<Tw001>("text-[13px]", &custom("", None));
    assert!(m[0].contains("--font-size-"), "{m:?}");
    let m = messages::<Tw001>("w-[45px]", &custom("", None));
    assert!(
        m[0].contains("--space-16") && m[0].contains("beyond"),
        "{m:?}"
    );
}

// frob:tests crates/crunk-rules/src/rules/tw001.rs::Tw001
#[test]
fn tw001_flags_a_non_px_unit_in_a_governed_family_without_a_token() {
    let m = messages::<Tw001>("max-h-[32dvh]", &custom("", None));
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(
        m[0].contains("cannot be compared") && !m[0].contains("--"),
        "{}",
        m[0]
    );
}

// frob:tests crates/crunk-rules/src/rules/tw001.rs::Tw001
#[test]
fn tw001_honours_a_custom_space_prefix() {
    let m = messages::<Tw001>(
        "p-[13px]",
        &custom("[tokens.prefixes]\nspace = \"sp\"\n", None),
    );
    assert!(
        m[0].contains("var(--sp-12)") && !m[0].contains("--space-"),
        "{m:?}"
    );
}

// frob:tests crates/crunk-rules/src/rules/tw001.rs::Tw001
#[test]
fn tw001_judges_arbitrary_z_index_against_declared_layers() {
    let layers = "[layers]\nbase = 0\n";
    let m = messages::<Tw001>("z-[999]", &custom(layers, None));
    assert!(
        m[0].contains("999") && m[0].contains("[0]") && m[0].contains("--layer-base"),
        "{m:?}"
    );
    let m = messages::<Tw001>("-z-[5]", &custom(layers, None));
    assert!(m[0].contains("-5"), "{m:?}");
    assert!(messages::<Tw001>("z-[0]", &custom(layers, None)).is_empty());
    assert!(messages::<Tw001>("z-[999]", &custom("", None)).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/tw001.rs::Tw001
#[test]
fn tw001_names_the_nearest_palette_token_for_an_off_palette_color() {
    let m = messages::<Tw001>("bg-[#2f6eec]", &custom("", None));
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].contains("--color-accent"), "{}", m[0]);
}

// frob:tests crates/crunk-rules/src/rules/tw002.rs::Tw002
// frob:tests crates/crunk-rules/src/rules/tw002.rs::bare_var
// frob:tests crates/crunk-rules/src/tailwind/mod.rs::theme_view
// frob:tests crates/crunk-rules/src/tailwind/mod.rs::tailwind_configured
// frob:tests crates/crunk-rules/src/host.rs::CrunkHost.tailwind_theme
#[test]
fn a_theme_entry_naming_an_unexported_token_fires_tw002() {
    let host = support::project("src/a.tsx", &tsx("p-4"), Some("theme-unknown"));
    let found = support::run::<Tw002>(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(
        found[0].message.contains("--color-nope"),
        "{}",
        found[0].message
    );
    let host = support::project("src/a.tsx", &tsx("p-4"), Some("theme-brand"));
    assert!(support::run::<Tw002>(&host).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/tw002.rs::Tw002
#[test]
fn tw002_is_silent_without_a_tailwind_section_and_for_literals() {
    let host = support::project("src/a.tsx", &tsx("p-4"), None);
    assert!(support::run::<Tw002>(&host).is_empty());
    let literal = "module.exports = { theme: { extend: { colors: { gray: \"#282828\" } } } };\n";
    assert!(messages::<Tw002>("p-4", &custom("", Some(literal))).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/tw003.rs::Tw003
#[test]
fn an_alpha_modifier_on_a_placeholderless_mapping_fires_tw003() {
    let host = support::project("src/a.tsx", &tsx("bg-brand/50"), Some("theme-brand"));
    let found = support::run::<Tw003>(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(
        found[0].message.contains("<alpha-value>"),
        "{}",
        found[0].message
    );
}

// frob:tests crates/crunk-rules/src/rules/tw003.rs::Tw003
#[test]
fn tw003_is_clean_with_a_placeholder_unmapped_keys_or_no_modifier() {
    for (class, cfg) in [
        ("bg-brand/50", "theme-alpha"),
        ("bg-unmapped/50", "theme-brand"),
        ("bg-brand", "theme-brand"),
    ] {
        let host = support::project("src/a.tsx", &tsx(class), Some(cfg));
        assert!(support::run::<Tw003>(&host).is_empty(), "{class} {cfg}");
    }
}

// frob:tests crates/crunk-rules/src/rules/tw004.rs::Tw004
#[test]
fn a_default_tailwind_color_fires_tw004() {
    let m = messages::<Tw004>("bg-black/10", &custom("", None));
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(
        m[0].contains("black") && m[0].contains("--color-ink"),
        "{}",
        m[0]
    );
    let m = messages::<Tw004>("text-red-500", &custom("", None));
    assert!(
        m[0].contains("red-500") && m[0].contains("--color-"),
        "{m:?}"
    );
}

// frob:tests crates/crunk-rules/src/rules/tw004.rs::Tw004
#[test]
fn tw004_exempts_transparent_and_theme_defined_colors() {
    assert!(messages::<Tw004>("bg-transparent", &custom("", None)).is_empty());
    assert!(messages::<Tw004>("text-red-500", &custom("", Some(THEME_RED))).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/tw005.rs::Tw005
#[test]
fn a_default_scale_key_fires_tw005() {
    let layers = "[layers]\nbase = 0\n";
    let m = messages::<Tw005>("z-10", &custom(layers, None));
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].contains("zIndex"), "{}", m[0]);
    assert!(messages::<Tw005>("z-10", &custom("", None)).is_empty());
    let m = messages::<Tw005>("p-5", &custom("", None));
    assert!(m[0].contains("spacing"), "{m:?}");
    assert_eq!(
        messages::<Tw005>("h-9 w-9 min-h-9", &custom("", None)).len(),
        3
    );
}

// frob:tests crates/crunk-rules/src/rules/tw005.rs::Tw005
#[test]
fn tw005_exempts_keywords_and_theme_defined_keys() {
    for class in ["h-full w-full", "max-w-64", "text-lg"] {
        assert!(
            messages::<Tw005>(class, &custom("", None)).is_empty(),
            "{class}"
        );
    }
    assert!(messages::<Tw005>("p-4", &custom("", Some(THEME_SPACING_4))).is_empty());
    assert!(messages::<Tw005>("w-64", &custom("", Some(THEME_WIDTH_64))).is_empty());
}

#[test]
fn flag_setup_is_parsed() {
    assert!(
        setup(Some("theme-brand,breakpoints"))
            .tailwind_config
            .is_some()
    );
}

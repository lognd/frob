//! What the I18N rules share: the pseudo-locale expansion a translation is budgeted against, which
//! locales read right to left, and which CSS properties and Tailwind utilities are physical
//! (left/right) rather than logical (start/end). All of it is T1: authored files and ingested
//! declarations, no render.

// frob:ticket 01M5H5P5H1CSMP9Q3NF4RY4M26

/// How much longer, in percent, a pseudo-locale renders text than the source language (the
/// common 40 percent allowance for German, Finnish and similar translations).
pub const PSEUDO_EXPANSION_PERCENT: usize = 40;

/// Locale base subtags written right to left.
const RTL_LANGUAGES: &[&str] = &["ar", "fa", "he", "iw", "ps", "sd", "ug", "ur", "yi", "dv"];

/// The length of `text` in characters once the pseudo-locale expansion is applied, rounded up.
#[must_use]
pub fn expanded_chars(text: &str) -> usize {
    let len = text.chars().count();
    (len * (100 + PSEUDO_EXPANSION_PERCENT)).div_ceil(100)
}

/// Whether `locale` (a BCP 47 tag such as `ar` or `he-IL`) is written right to left.
#[must_use]
pub fn is_rtl_locale(locale: &str) -> bool {
    let base = locale
        .split(['-', '_'])
        .next()
        .unwrap_or(locale)
        .to_ascii_lowercase();
    RTL_LANGUAGES.contains(&base.as_str())
}

/// CSS properties that name a side physically, with the logical property to use instead.
const PHYSICAL_PROPS: &[(&str, &str)] = &[
    ("margin-left", "margin-inline-start"),
    ("margin-right", "margin-inline-end"),
    ("padding-left", "padding-inline-start"),
    ("padding-right", "padding-inline-end"),
    ("border-left", "border-inline-start"),
    ("border-right", "border-inline-end"),
    ("left", "inset-inline-start"),
    ("right", "inset-inline-end"),
];

/// Tailwind utility prefixes that name a side physically, with the logical prefix to use instead.
const PHYSICAL_UTILITIES: &[(&str, &str)] = &[
    ("ml-", "ms-"),
    ("mr-", "me-"),
    ("pl-", "ps-"),
    ("pr-", "pe-"),
    ("left-", "start-"),
    ("right-", "end-"),
    ("border-l", "border-s"),
    ("border-r", "border-e"),
    ("rounded-l", "rounded-s"),
    ("rounded-r", "rounded-e"),
];

/// The logical replacement for the declaration `prop: value` when it is physical: a physical
/// property, or `text-align` / `float` / `clear` set to `left` or `right`.
#[must_use]
pub fn logical_for_declaration(prop: &str, value: &str) -> Option<String> {
    if let Some((_, logical)) = PHYSICAL_PROPS.iter().find(|(p, _)| *p == prop) {
        return Some((*logical).to_owned());
    }
    let value = value.trim().to_ascii_lowercase();
    match (prop, value.as_str()) {
        ("text-align" | "float" | "clear", "left") => Some(format!("{prop}: start")),
        ("text-align" | "float" | "clear", "right") => Some(format!("{prop}: end")),
        _ => None,
    }
}

/// The logical replacement for the Tailwind utility `name` when it is physical.
#[must_use]
pub fn logical_for_utility(name: &str) -> Option<String> {
    match name {
        "text-left" => return Some("text-start".to_owned()),
        "text-right" => return Some("text-end".to_owned()),
        "float-left" => return Some("float-start".to_owned()),
        "float-right" => return Some("float-end".to_owned()),
        _ => {}
    }
    PHYSICAL_UTILITIES.iter().find_map(|(physical, logical)| {
        let rest = name.strip_prefix(physical)?;
        // `border-l` and `rounded-l` end the prefix at the side letter; the rest is a width,
        // radius or nothing, never more letters of another utility (`rounded-lg` is not a side).
        let boundary = physical.ends_with('-') || rest.is_empty() || rest.starts_with('-');
        boundary.then(|| format!("{logical}{rest}"))
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-rules/src/i18n.rs::expanded_chars
    #[test]
    fn expansion_rounds_up_by_forty_percent() {
        assert_eq!(expanded_chars("Save"), 6);
        assert_eq!(expanded_chars("Welcome"), 10);
        assert_eq!(expanded_chars(""), 0);
    }

    // frob:tests crates/crunk-rules/src/i18n.rs::is_rtl_locale
    #[test]
    fn rtl_locales_are_recognised_by_base_subtag() {
        assert!(is_rtl_locale("ar"));
        assert!(is_rtl_locale("he-IL"));
        assert!(is_rtl_locale("FA_ir"));
        assert!(!is_rtl_locale("en-US"));
        assert!(!is_rtl_locale("default"));
    }

    // frob:tests crates/crunk-rules/src/i18n.rs::logical_for_declaration
    #[test]
    fn declarations_map_to_their_logical_form() {
        assert_eq!(
            logical_for_declaration("margin-left", "4px").as_deref(),
            Some("margin-inline-start")
        );
        assert_eq!(
            logical_for_declaration("text-align", " Right ").as_deref(),
            Some("text-align: end")
        );
        assert_eq!(logical_for_declaration("text-align", "center"), None);
        assert_eq!(logical_for_declaration("margin-inline-start", "4px"), None);
    }

    // frob:tests crates/crunk-rules/src/i18n.rs::logical_for_utility
    #[test]
    fn utilities_map_to_their_logical_form() {
        assert_eq!(logical_for_utility("ml-4").as_deref(), Some("ms-4"));
        assert_eq!(logical_for_utility("pr-2").as_deref(), Some("pe-2"));
        assert_eq!(
            logical_for_utility("text-left").as_deref(),
            Some("text-start")
        );
        assert_eq!(logical_for_utility("border-l").as_deref(), Some("border-s"));
        assert_eq!(
            logical_for_utility("border-l-2").as_deref(),
            Some("border-s-2")
        );
        assert_eq!(logical_for_utility("rounded-lg"), None);
        assert_eq!(logical_for_utility("ms-4"), None);
    }
}

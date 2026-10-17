//! What the ORG rules share: which sheets they skip, where a line starts, and the class-name
//! casing and component-prefix tests.

// frob:ticket 01M43ATBPPR5QCY0CSPPTNEDQ0

use std::path::Path;

use crunk_ingest::Stylesheet;
use crunk_ingest::glob::glob_match;
use crunk_spec::DesignSpec;
use crunk_spec::table::{ClassCase, OrgModel};

use crate::sheets::site_path;

/// True when `[org] ignore` covers `sheet` (globs are relative to the project root).
pub fn is_ignored(spec: &DesignSpec, sheet: &Stylesheet) -> bool {
    path_ignored(spec, &sheet.path)
}

/// True when `[org] ignore` covers the file at `path`.
pub fn path_ignored(spec: &DesignSpec, path: &Path) -> bool {
    let site = site_path(spec, path);
    spec.org.ignore.iter().any(|g| glob_match(&site, g))
}

/// True when the project places files in buckets (`[org] model = "buckets"`), the model ORG001 judges.
pub fn buckets_model(spec: &DesignSpec) -> bool {
    spec.org.model == OrgModel::Buckets
}

/// Byte offset of the start of 1-based `line` in `source` (the end of `source` past the last line).
pub fn line_offset(source: &str, line: u32) -> usize {
    if line <= 1 {
        return 0;
    }
    source
        .match_indices('\n')
        .nth(line as usize - 2)
        .map_or(source.len(), |(at, _)| at + 1)
}

/// True when `name` is written in `case`: kebab `a-b`, snake `a_b`, camel `aB`.
///
/// Digits are allowed anywhere after the first character; a leading digit, an empty name, or a
/// separator at either end or doubled is never well formed.
pub fn matches_case(name: &str, case: ClassCase) -> bool {
    let mut chars = name.chars();
    let Some(first) = chars.next() else {
        return false;
    };
    if !first.is_ascii_lowercase() {
        return false;
    }
    match case {
        ClassCase::Kebab => separated(name, '-'),
        ClassCase::Snake => separated(name, '_'),
        ClassCase::Camel => name.chars().all(|c| c.is_ascii_alphanumeric()),
    }
}

/// Lowercase alphanumeric words joined by single `sep`, none empty.
fn separated(name: &str, sep: char) -> bool {
    name.split(sep).all(|word| {
        !word.is_empty()
            && word
                .chars()
                .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit())
    })
}

/// True when class `class` carries `component` as its prefix, ignoring case and separators:
/// `card-title`, `card__title`, `cardTitle` and `Card` all carry `card`.
pub fn has_component_prefix(class: &str, component: &str) -> bool {
    let fold = |s: &str| -> String {
        s.chars()
            .filter(char::is_ascii_alphanumeric)
            .map(|c| c.to_ascii_lowercase())
            .collect()
    };
    let prefix = fold(component);
    !prefix.is_empty() && fold(class).starts_with(&prefix)
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-rules/src/org/mod.rs::matches_case
    #[test]
    fn casing_follows_the_configured_style() {
        assert!(matches_case("card-title", ClassCase::Kebab));
        assert!(!matches_case("Card_Title", ClassCase::Kebab));
        assert!(!matches_case("card_title", ClassCase::Kebab));
        assert!(!matches_case("card--title", ClassCase::Kebab));
        assert!(matches_case("card_title", ClassCase::Snake));
        assert!(!matches_case("card-title", ClassCase::Snake));
        assert!(matches_case("cardTitle", ClassCase::Camel));
        assert!(!matches_case("card-title", ClassCase::Camel));
        assert!(matches_case("card2", ClassCase::Kebab));
        assert!(!matches_case("2card", ClassCase::Kebab));
    }

    // frob:tests crates/crunk-rules/src/org/mod.rs::has_component_prefix
    #[test]
    fn the_prefix_ignores_case_and_separators() {
        assert!(has_component_prefix("card-title", "card"));
        assert!(has_component_prefix("cardTitle", "Card"));
        assert!(has_component_prefix("card", "card"));
        assert!(!has_component_prefix("title", "card"));
        assert!(!has_component_prefix("title", ""));
    }

    // frob:tests crates/crunk-rules/src/org/mod.rs::line_offset
    #[test]
    fn lines_map_to_byte_offsets() {
        let text = "ab\ncd\nef";
        assert_eq!(line_offset(text, 1), 0);
        assert_eq!(line_offset(text, 2), 3);
        assert_eq!(line_offset(text, 3), 6);
        assert_eq!(line_offset(text, 9), text.len());
    }
}

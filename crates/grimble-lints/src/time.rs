//! Clock and zone discipline sites: `TIME001` and `TIME002` (rules.md section 3.2, D93).
//!
//! [`scan`] reports a current-time read in the local zone or without a zone whose value is stored,
//! compared, serialized or sent rather than only displayed (`TIME001`), and arithmetic or a
//! comparison between a naive and a zone-aware datetime, or between naive values of different
//! zones (`TIME002`). Both need the clock roles of a language ([`has_clock_roles`], Rust and
//! Python); for any other code language the [`Report`] lists them as unresolved instead of
//! silently clean. Mapping a site to a severity belongs to the rule that consumes it.

// frob:ticket 01M44R5W4WJEXFM000S8KVQQN5

mod flow;

use gob_languages::{Language, ParseLimits, ParseResult, parse};
use gob_text::TextRange;

use crate::syntax::Lang;

/// Which clock shape a site is.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Kind {
    /// `TIME001`: a local-zone or zone-less clock read whose value is stored, compared or sent.
    LocalClockRead,
    /// `TIME002`: a naive and an aware datetime (or naive values of two zones) mixed.
    NaiveAwareMix,
}

impl Kind {
    /// The rule id this kind belongs to.
    pub fn rule_id(self) -> &'static str {
        match self {
            Self::LocalClockRead => "TIME001",
            Self::NaiveAwareMix => "TIME002",
        }
    }
}

/// One clock site.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Site {
    /// The shape found.
    pub kind: Kind,
    /// The call or expression, as byte offsets in the scanned text.
    pub range: TextRange,
    /// 1-based line where the site starts.
    pub line: usize,
}

/// The result of one scan: the sites, and the rules that could not be decided.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Report {
    /// Sites in source order.
    pub sites: Vec<Site>,
    /// Kinds the language has no clock roles for: Unresolved, never clean.
    pub unresolved: Vec<Kind>,
}

/// Why a file could not be scanned.
#[derive(Debug, thiserror::Error)]
pub enum ScanError {
    /// The file did not parse within the limits, or its grammar is not built in.
    #[error("E-TIME-PARSE: {0}")]
    Parse(String),
}

/// True when `language` has the clock-read roles `TIME001` and `TIME002` need.
pub fn has_clock_roles(language: Language) -> bool {
    Lang::of(language).is_some()
}

/// Every clock site of `text` parsed as `language`, in source order.
///
/// A language that is not code (or has no clock roles) yields no sites; the caller decides whether
/// that is Unresolved. A language with roles but a failed parse is a [`ScanError`].
///
/// # Errors
///
/// [`ScanError`] when the file does not parse.
pub fn scan(language: Language, text: &str) -> Result<Report, ScanError> {
    let Some(lang) = Lang::of(language) else {
        tracing::debug!(
            language = language.name(),
            "clock roles missing: unresolved"
        );
        return Ok(Report {
            sites: Vec::new(),
            unresolved: vec![Kind::LocalClockRead, Kind::NaiveAwareMix],
        });
    };
    let tree = match parse(language, text, &ParseLimits::default()) {
        ParseResult::Parsed(tree) => tree,
        ParseResult::Unresolved(u) => return Err(ScanError::Parse(u.reason.to_string())),
    };
    let mut sites: Vec<Site> = flow::scan(lang, tree.root(), text)
        .into_iter()
        .map(|r| Site {
            kind: r.kind,
            range: tree.node_range(&r.node),
            line: r.node.start_position().row + 1,
        })
        .collect();
    sites.sort_by_key(|s| (s.range.start(), s.kind));
    sites.dedup();
    tracing::debug!(
        language = language.name(),
        sites = sites.len(),
        "time sites scanned"
    );
    Ok(Report {
        sites,
        unresolved: Vec::new(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/grimble-lints/src/time.rs::Kind.rule_id
    #[test]
    fn rule_ids_follow_kinds() {
        assert_eq!(Kind::LocalClockRead.rule_id(), "TIME001");
        assert_eq!(Kind::NaiveAwareMix.rule_id(), "TIME002");
    }

    // frob:tests crates/grimble-lints/src/time.rs::has_clock_roles
    #[test]
    fn only_rust_and_python_have_roles() {
        assert!(has_clock_roles(Language::Rust));
        assert!(has_clock_roles(Language::Python));
        assert!(!has_clock_roles(Language::TypeScript));
    }

    // frob:tests crates/grimble-lints/src/time.rs::scan
    #[test]
    fn language_without_roles_is_unresolved_not_clean() {
        let r = scan(Language::TypeScript, "const t = new Date();").expect("ok");
        assert!(r.sites.is_empty());
        assert_eq!(r.unresolved, [Kind::LocalClockRead, Kind::NaiveAwareMix]);
    }
}

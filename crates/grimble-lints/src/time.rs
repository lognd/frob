//! Clock and zone discipline sites: `TIME001` and `TIME002` (docs/design/shared/rules.md section 3.2, D93).
//!
//! [`scan`] reports a current-time read in the local zone or without a zone whose value is stored,
//! compared, serialized or sent rather than only displayed (`TIME001`), and arithmetic or a
//! comparison between a naive and a zone-aware datetime, or between naive values of different
//! zones (`TIME002`). Both need the clock roles of a language ([`has_clock_roles`], Rust and
//! Python); for any other code language the [`Report`] lists them as unresolved instead of
//! silently clean. Mapping a site to a severity belongs to the rule that consumes it.
//!
//! Scope discovery runs through the universal model (`gob_symbols::model_of_source_at`): the
//! function and method scopes are the `unit(function|method)` nodes, read by byte span. The
//! name-based def-use flow, the import aliases and the callee vocabulary still read the tree (see
//! docs/design/grimble/lint-classification.md section 3).

// frob:ticket 01M44R5W4WJEXFM000S8KVQQN5

mod flow;

use gob_ir::{Location, Operator, Universal};
use gob_languages::{Language, ParseLimits, ParseResult, parse};
use gob_symbols::model_of_source_at;
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
    /// The universal model of the file could not be built (an adapter bug).
    #[error("E-TIME-MODEL: {0}")]
    Model(String),
}

/// The adapter path whose extension selects the universal-model fold for `language`.
fn model_path(language: Language) -> &'static str {
    match language {
        Language::Rust => "time.rs",
        _ => "time.py",
    }
}

/// Byte ranges of every function and method unit of `text`, from the universal model.
fn function_ranges(language: Language, text: &str) -> Result<Vec<(usize, usize)>, ScanError> {
    let model = model_of_source_at(model_path(language), text)
        .map_err(|e| ScanError::Model(e.to_string()))?;
    let term = model.term();
    let mut out = Vec::new();
    for id in term.ids() {
        let node = term.node(id);
        let Operator::Universal(Universal::Unit { kind, .. }) = node.op() else {
            continue;
        };
        if !matches!(kind.as_str(), "function" | "method") {
            continue;
        }
        let Location::Text { range, .. } = node.location() else {
            continue;
        };
        out.push((
            u32::from(range.start()) as usize,
            u32::from(range.end()) as usize,
        ));
    }
    tracing::debug!(
        language = language.name(),
        functions = out.len(),
        "time function scopes from model"
    );
    Ok(out)
}

/// True when `language` has the clock-read roles `TIME001` and `TIME002` need.
pub fn has_clock_roles(language: Language) -> bool {
    Lang::from_gob(language).is_some()
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
    let Some(lang) = Lang::from_gob(language) else {
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
    let fns = function_ranges(language, text)?;
    let mut sites: Vec<Site> = flow::scan_time(lang, tree.root(), text, &fns)
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
    fn every_adapter_language_scans_without_error() {
        for language in Language::ALL {
            scan(language, "x = 1\n").unwrap_or_else(|e| panic!("{}: {e}", language.name()));
        }
    }

    // frob:tests crates/grimble-lints/src/time.rs::scan
    #[test]
    fn python_function_scope_is_found_through_the_model() {
        let src =
            "from datetime import datetime\n@d\ndef f():\n    t = datetime.now()\n    save(t)\n";
        let r = scan(Language::Python, src).expect("parses");
        assert_eq!(r.sites.len(), 1);
        assert_eq!(r.sites[0].kind, Kind::LocalClockRead);
    }

    // frob:tests crates/grimble-lints/src/time.rs::scan
    #[test]
    fn rust_method_scope_is_found_through_the_model() {
        let src = "impl A { fn m(&self) { let t = Local::now(); save(t); } }\n";
        let r = scan(Language::Rust, src).expect("parses");
        assert_eq!(r.sites.len(), 1);
        assert_eq!(r.sites[0].kind, Kind::LocalClockRead);
    }

    // frob:tests crates/grimble-lints/src/time.rs::scan
    #[test]
    fn language_without_roles_is_unresolved_not_clean() {
        let r = scan(Language::TypeScript, "const t = new Date();").expect("ok");
        assert!(r.sites.is_empty());
        assert_eq!(r.unresolved, [Kind::LocalClockRead, Kind::NaiveAwareMix]);
    }
}

//! Subject status: what a rule may say about one file given the file's fidelity and parse state.
//!
//! The answer lattice (`universal-model.md` 4.1-4.2, 4.6) has `NotApplicable`
//! as a query answer only, never a finding; a rule that cannot examine a
//! subject it applies to yields `Unresolved`, never silence. The per-rule
//! needs live in [`need_of`] because `RuleMeta` is declared in `gob-rules`.

use std::collections::BTreeMap;

use gob_rules::{Finding, RuleId, RuleMeta, Severity};
use gob_symbols::{Fidelity, FileInfo, ParseStatus};
use gob_text::{FileId, Span, TextRange};
use schemars::JsonSchema;
use serde::Serialize;

/// What a rule may do with one file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SubjectStatus {
    /// Run the rule over the file.
    Examine,
    /// The file cannot hold this rule's subjects; counted, never a finding.
    NotApplicable(String),
    /// The rule applies but could not examine the file; one Unresolved finding.
    Unresolved(String),
}

/// What kind of subject a rule consumes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Need {
    /// Needs a capability only an adapter provides (public items, imports, links).
    Capability,
    /// Applies to every text artifact (comment markers, directives); an opaque text file hides subjects.
    EveryTextArtifact,
}

/// The declared needs of one rule.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RuleNeed {
    /// The subject kind.
    pub need: Need,
    /// Lowest fidelity at which the rule can examine a file (default F1).
    pub min_fidelity: Fidelity,
    /// True when the subjects are symbols, so a parse hole can hide some.
    pub symbol_subjects: bool,
}

impl RuleNeed {
    const fn capability(min_fidelity: Fidelity, symbol_subjects: bool) -> Self {
        Self {
            need: Need::Capability,
            min_fidelity,
            symbol_subjects,
        }
    }

    const fn text(min_fidelity: Fidelity) -> Self {
        Self {
            need: Need::EveryTextArtifact,
            min_fidelity,
            symbol_subjects: false,
        }
    }
}

/// The needs of rule `id`; unknown rules default to a capability rule at F1.
pub fn need_of(id: &str) -> RuleNeed {
    match id {
        "TODO001" | "REF001" | "TEST001" | "INV001" | "DRIFT001" | "DRIFT002" | "DRIFT003"
        | "DRIFT004" => RuleNeed::text(Fidelity::F1),
        "DOC001" | "INV002" => RuleNeed::capability(Fidelity::F1, true),
        "COV001" | "AFFECT001" => RuleNeed::capability(Fidelity::F2, true),
        _ => RuleNeed::capability(Fidelity::F1, false),
    }
}

/// [`subject_status_for`] for a text file.
pub fn subject_status(info: &FileInfo, meta: &RuleMeta) -> SubjectStatus {
    subject_status_for(info, meta, false)
}

/// What `meta` may do with the file described by `info`; `binary` marks a non-text opaque file.
///
/// Opaque F0: `NotApplicable` for capability rules and for binary files,
/// `Unresolved` for every-text-artifact rules. A failed parse is Unresolved
/// for every rule. A fidelity below the rule's minimum is Unresolved.
pub fn subject_status_for(info: &FileInfo, meta: &RuleMeta, binary: bool) -> SubjectStatus {
    let need = need_of(meta.id);
    let status = if info.is_opaque() {
        match need.need {
            Need::Capability => {
                SubjectStatus::NotApplicable("no adapter: the file has no parsed items".to_owned())
            }
            Need::EveryTextArtifact if binary => {
                SubjectStatus::NotApplicable("binary artifact holds no text".to_owned())
            }
            Need::EveryTextArtifact => SubjectStatus::Unresolved(
                "no adapter for this file (opaque F0): its comments and directives were not read"
                    .to_owned(),
            ),
        }
    } else if let ParseStatus::Failed { reason } = &info.parse_status {
        SubjectStatus::Unresolved(format!("the file failed to parse ({reason})"))
    } else if info.fidelity < need.min_fidelity {
        SubjectStatus::Unresolved(format!(
            "file fidelity {} is below the {} the rule needs",
            info.fidelity, need.min_fidelity
        ))
    } else {
        SubjectStatus::Examine
    };
    tracing::trace!(rule = meta.id, ?status, "subject status");
    status
}

/// For an examined file with parse holes: why subjects inside or across a hole stay Unresolved.
pub fn hole_caveat(info: &FileInfo, meta: &RuleMeta) -> Option<String> {
    match (&info.parse_status, need_of(meta.id).symbol_subjects) {
        (ParseStatus::Partial { holes }, true) => Some(format!(
            "the file parsed partially ({holes} hole(s)); subjects inside or across a hole cannot be decided"
        )),
        _ => None,
    }
}

/// One Unresolved finding of `meta` anchored at the start of `file` (or spanless).
pub fn unresolved_finding(
    meta: &RuleMeta,
    file: Option<FileId>,
    path: &str,
    reason: &str,
) -> Finding {
    let id: RuleId = meta
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"));
    Finding::new(
        id,
        Severity::Unresolved,
        file.map(|f| Span::new(f, TextRange::default())),
        format!("{}: {reason}: {path}", meta.id),
        &format!("fidelity:{path}"),
    )
}

/// Extensions that are binary regardless of content.
const BINARY_EXTENSIONS: &[&str] = &[
    "png", "jpg", "jpeg", "gif", "ico", "webp", "pdf", "zip", "gz", "xz", "zst", "tar", "woff",
    "woff2", "ttf", "otf", "wasm", "so", "dylib", "dll", "o", "a", "bin", "db", "sqlite",
];

/// True when `path` looks binary by extension or when `head` (file prefix) holds a NUL byte.
pub fn is_binary(path: &str, head: &[u8]) -> bool {
    let ext = std::path::Path::new(path)
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_ascii_lowercase();
    BINARY_EXTENSIONS.contains(&ext.as_str()) || head.contains(&0)
}

/// Fidelity accounting of one language (`opaque` for adapter-less files).
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, JsonSchema)]
pub struct LanguageFidelity {
    /// Fidelity the files were folded at (highest seen).
    pub fidelity: String,
    /// Files walked and checked.
    pub files: usize,
    /// Files at least one rule examined.
    pub files_examined: usize,
    /// Files with parse holes.
    pub partial_parse: usize,
    /// Files per rule family where every subject was NotApplicable.
    pub not_applicable: BTreeMap<String, usize>,
    /// Unresolved findings per rule id raised for this language's files.
    pub unresolved: BTreeMap<String, usize>,
}

/// The per-language fidelity report of one run.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, JsonSchema)]
pub struct FidelityReport {
    /// Language label to its counts.
    pub languages: BTreeMap<String, LanguageFidelity>,
}

impl FidelityReport {
    /// Language label of a file: its adapter tag or `opaque`.
    pub fn label(info: &FileInfo) -> String {
        if info.language.is_empty() {
            "opaque".to_owned()
        } else {
            info.language.clone()
        }
    }

    /// Count one file with the rule outcomes computed for it.
    pub fn record(
        &mut self,
        info: &FileInfo,
        examined: bool,
        not_applicable: &[&str],
        unresolved: &[&str],
    ) {
        let row = self.languages.entry(Self::label(info)).or_default();
        row.files += 1;
        row.files_examined += usize::from(examined);
        row.partial_parse += usize::from(matches!(info.parse_status, ParseStatus::Partial { .. }));
        let f = info.fidelity.to_string();
        if f > row.fidelity {
            row.fidelity = f;
        }
        for family in not_applicable {
            *row.not_applicable.entry((*family).to_owned()).or_default() += 1;
        }
        for rule in unresolved {
            *row.unresolved.entry((*rule).to_owned()).or_default() += 1;
        }
    }

    /// Add `n` Unresolved findings of `rule` to the language `label`.
    pub fn add_unresolved(&mut self, label: &str, rule: &str, n: usize) {
        let row = self.languages.entry(label.to_owned()).or_default();
        *row.unresolved.entry(rule.to_owned()).or_default() += n;
    }

    /// One text line per language, for `--timing --text`.
    pub fn lines(&self) -> Vec<String> {
        self.languages
            .iter()
            .map(|(lang, r)| {
                let na: Vec<String> = r
                    .not_applicable
                    .iter()
                    .map(|(f, n)| format!("{f}={n}"))
                    .collect();
                let un: usize = r.unresolved.values().sum();
                format!(
                    "fidelity {lang} ({}): {} files, {} examined, {} partial, not-applicable [{}], {un} unresolved",
                    r.fidelity,
                    r.files,
                    r.files_examined,
                    r.partial_parse,
                    na.join(" ")
                )
            })
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use gob_rules::{FixKind, Polarity, Scope, Tier};

    fn meta(id: &str) -> &'static RuleMeta {
        let id: &'static str = Box::leak(id.to_owned().into_boxed_str());
        Box::leak(Box::new(RuleMeta {
            id,
            slug: "t",
            family: "T",
            product: "frob",
            severity: Severity::Warn,
            summary: "s",
            explanation: "e",
            tier: Tier::Universal,
            scope: Scope::File,
            fix: FixKind::Manual,
            polarity: Polarity::Pplus,
            must_measure: false,
            version: 1,
            since: "2.0.0",
            module: "t",
        }))
    }

    fn opaque() -> FileInfo {
        FileInfo {
            language: String::new(),
            fidelity: Fidelity::F0,
            parse_status: ParseStatus::NotParsed,
            degraded: false,
        }
    }

    // frob:tests crates/gob-check/src/status.rs::subject_status_for
    #[test]
    fn opaque_files_split_by_need_and_binariness() {
        let i = opaque();
        assert!(matches!(
            subject_status_for(&i, meta("TODO001"), false),
            SubjectStatus::Unresolved(_)
        ));
        assert!(matches!(
            subject_status_for(&i, meta("TODO001"), true),
            SubjectStatus::NotApplicable(_)
        ));
        assert!(matches!(
            subject_status(&i, meta("TODO001")),
            SubjectStatus::Unresolved(_)
        ));
    }

    #[test]
    fn partial_files_are_examined_with_a_caveat() {
        let mut i = opaque();
        i.language = "rust".into();
        i.fidelity = Fidelity::F3;
        i.parse_status = ParseStatus::Partial { holes: 2 };
        assert_eq!(subject_status(&i, meta("DOC001")), SubjectStatus::Examine);
        assert!(hole_caveat(&i, meta("DOC001")).is_some());
        assert!(hole_caveat(&i, meta("TODO001")).is_none());
    }

    #[test]
    fn low_fidelity_is_unresolved() {
        let mut i = opaque();
        i.language = "x".into();
        i.fidelity = Fidelity::F1;
        assert!(matches!(
            subject_status(&i, meta("COV001")),
            SubjectStatus::Unresolved(_)
        ));
    }

    // frob:tests crates/gob-check/src/status.rs::is_binary
    #[test]
    fn binary_detection() {
        assert!(is_binary("a.png", b""));
        assert!(is_binary("a.dat", &[1, 0, 2]));
        assert!(!is_binary("a.py", b"print"));
    }
}

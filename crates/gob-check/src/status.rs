//! Subject status: what a rule may say about one file given the file's fidelity and parse state.
//!
//! The answer lattice (`universal-model.md` 4.1-4.2, 4.6) has `NotApplicable`
//! as a query answer only, never a finding; a rule that cannot examine a
//! subject it applies to yields `Unresolved`, never silence. The per-rule
//! applicability is decided by [`crate::applicability::resolve`].

use std::collections::BTreeMap;

use crate::applicability::{Applies, FileFacts, resolve, temporary_applies};
use gob_rules::{Finding, RequiredReason, RuleId, RuleMeta, Severity, UnresolvedReason};
use gob_symbols::{FileInfo, ParseStatus, SkipKind, SkippedFile};
use gob_text::{FileId, Span, TextRange, TextSize};
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

/// [`subject_status_for`] for an unscanned text file.
pub fn subject_status(info: &FileInfo, meta: &RuleMeta) -> SubjectStatus {
    subject_status_for(info, meta, false, false)
}

/// What `meta` may do with the file described by `info`.
///
/// `binary` marks a non-text opaque file; `scanned` marks an opaque file whose
/// comments and directives the scanner reads anyway (TOML). The answer is
/// [`resolve`] applied to the rule's declared applicability.
pub fn subject_status_for(
    info: &FileInfo,
    meta: &RuleMeta,
    binary: bool,
    scanned: bool,
) -> SubjectStatus {
    let status = resolve(
        &temporary_applies(meta),
        &FileFacts::of(info, binary, scanned),
    );
    tracing::trace!(rule = meta.id, ?status, "subject status");
    status
}

/// For an examined file with parse holes: why subjects inside or across a hole stay Unresolved.
pub fn hole_caveat(info: &FileInfo, meta: &RuleMeta) -> Option<String> {
    hole_caveat_of(info, &temporary_applies(meta))
}

/// [`hole_caveat`] for a rule that declares `applies`.
pub(crate) fn hole_caveat_of(info: &FileInfo, applies: &Applies) -> Option<String> {
    match (&info.parse_status, applies.symbol_subjects()) {
        (ParseStatus::Partial { holes }, true) => Some(format!(
            "the file parsed partially ({holes} hole(s)); subjects inside or across a hole cannot be decided"
        )),
        _ => None,
    }
}

// frob:ticket 01M4GKD8WNG2NW2VAR1MBP382J
/// Where a partial markdown parse most likely failed: a table row with an unescaped `|` in a code span.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HoleSite {
    /// Byte range of the offending line.
    pub range: TextRange,
    /// 1-based line number.
    pub line: usize,
    /// The likely cause, one sentence.
    pub cause: &'static str,
}

// frob:ticket 01M4GKD8WNG2NW2VAR1MBP382J
/// The first line of markdown `text` (`path` must be markdown) that likely broke the parse.
///
/// Only the table-row cause is recognised: a row starting with `|` whose code span holds an
/// unescaped `|`, which splits the row mid-span. `None` for other files or causes.
pub fn locate_hole(path: &str, text: &str) -> Option<HoleSite> {
    let ext = std::path::Path::new(path)
        .extension()
        .and_then(|e| e.to_str())?
        .to_ascii_lowercase();
    if ext != "md" && ext != "markdown" {
        return None;
    }
    let mut offset = 0usize;
    let mut first: Option<HoleSite> = None;
    for (i, raw) in text.split_inclusive('\n').enumerate() {
        let start = offset;
        offset += raw.len();
        let line = raw.trim_end_matches(['\n', '\r']);
        if !line.trim_start().starts_with('|') {
            continue;
        }
        let (mut in_code, mut prev) = (false, ' ');
        let (mut bad, mut doubled) = (false, false);
        for c in line.chars() {
            if c == '|' && in_code && prev != '\\' {
                bad = true;
                doubled |= prev == '|';
            }
            if c == '`' {
                in_code = !in_code;
            }
            prev = c;
        }
        if !bad {
            continue;
        }
        let range = TextRange::new(
            TextSize::new(u32::try_from(start).ok()?),
            TextSize::new(u32::try_from(start + line.len()).ok()?),
        );
        let site = HoleSite {
            range,
            line: i + 1,
            cause: "a table row has an unescaped `|` inside a code span; write it as `\\|`",
        };
        // A doubled `||` inside a span is the strongest sign: it reads as an empty cell.
        if doubled {
            return Some(site);
        }
        first.get_or_insert(site);
    }
    first
}

// frob:ticket 01M4GKD8WNG2NW2VAR1MBP382J
/// `unresolved_finding_for` anchored at `site` of `file` and naming its line and likely cause.
pub fn unresolved_finding_at(
    id: &str,
    file: FileId,
    path: &str,
    reason: &str,
    site: &HoleSite,
) -> Finding {
    let mut f = unresolved_finding_for(
        id,
        Some(file),
        path,
        &format!("{reason}; line {}: likely cause: {}", site.line, site.cause),
        UnresolvedReason::Partial,
    );
    f.span = Some(Span::new(file, site.range));
    f
}

/// One Unresolved finding of `meta` anchored at the start of `file` (or spanless), typed `fidelity`.
pub fn unresolved_finding(
    meta: &RuleMeta,
    file: Option<FileId>,
    path: &str,
    reason: &str,
) -> Finding {
    unresolved_finding_for(meta.id, file, path, reason, UnresolvedReason::Fidelity)
}

/// [`unresolved_finding`] for the rule `id` (a legacy meta or a `RuleDef`), with its typed `kind`.
pub(crate) fn unresolved_finding_for(
    id: &str,
    file: Option<FileId>,
    path: &str,
    reason: &str,
    kind: UnresolvedReason,
) -> Finding {
    let rule: RuleId = id
        .parse()
        .unwrap_or_else(|e| unreachable!("rule ids are validated at declaration: {e}"));
    Finding::new(
        rule,
        Severity::Unresolved,
        file.map(|f| Span::new(f, TextRange::default())),
        format!("{id}: {reason}: {path}"),
        &format!("fidelity:{path}"),
    )
    .with_reason(kind)
}

// frob:ticket 01M42M1KK02KFZG39CXKAD47SZ
/// The required Unresolved `READ001` finding for one unreadable `file`.
///
/// Required so the default `fail_on_unresolved = "required"` gate fails on it: a
/// file the gates never read must not read as clean. The reason is
/// `ZeroSubjects`, the gate's existing "measured nothing" class (a dedicated
/// variant is a follow-up).
pub fn unreadable_finding(meta: &RuleMeta, file: Option<FileId>, skipped: &SkippedFile) -> Finding {
    unresolved_finding(
        meta,
        file,
        &skipped.path,
        &format!(
            "file not read ({}: {}); no rule examined it",
            skipped.kind.as_str(),
            skipped.detail
        ),
    )
    .with_reason(UnresolvedReason::ParseFailed)
    .with_required(RequiredReason::ZeroSubjects {
        rule: meta.id.to_owned(),
    })
}

/// One Unresolved finding of `meta` for all opaque text files `files` (spanless, one per rule).
pub fn opaque_finding(meta: &RuleMeta, files: &[&str]) -> Finding {
    opaque_finding_for(meta.id, files)
}

/// [`opaque_finding`] for the rule `id`.
pub(crate) fn opaque_finding_for(id: &str, files: &[&str]) -> Finding {
    let first = files.first().copied().unwrap_or_default();
    unresolved_finding_for(
        id,
        None,
        "repository",
        &format!(
            "{} opaque text file(s) (no adapter, first `{first}`) were not read for comments or directives",
            files.len()
        ),
        UnresolvedReason::Fidelity,
    )
}

// frob:ticket 01M4FG5RCDA668CK81QT54E67N
/// Marker text shared by every per-rule opaque-files notice.
const OPAQUE_MARK: &str = " opaque text file(s) (no adapter, first `";

/// Collapse every per-rule opaque-files notice in `raw` into one run-wide notice.
///
/// The notice names the file count and the rules that could not read the
/// files, so a repository with many opaque files reports it once, not once
/// per rule. Other findings keep their order; the notice takes the place of
/// the first one it replaces.
pub(crate) fn merge_opaque_notices(raw: Vec<Finding>) -> Vec<Finding> {
    let is_notice = |f: &Finding| {
        f.severity == Severity::Unresolved
            && f.reason == Some(UnresolvedReason::Fidelity)
            && f.span.is_none()
            && f.message.contains(OPAQUE_MARK)
    };
    if raw.iter().filter(|f| is_notice(f)).count() < 2 {
        return raw;
    }
    let mut rules: Vec<String> = Vec::new();
    let mut count = 0usize;
    let mut first = "";
    for f in raw.iter().filter(|f| is_notice(f)) {
        let id = f.rule.to_string();
        if !rules.contains(&id) {
            rules.push(id);
        }
        let n = f
            .message
            .split(OPAQUE_MARK)
            .next()
            .and_then(|head| head.rsplit(' ').next())
            .and_then(|n| n.parse::<usize>().ok());
        if let Some(n) = n.filter(|n| *n > count) {
            count = n;
            first = f
                .message
                .split(OPAQUE_MARK)
                .nth(1)
                .and_then(|t| t.split('`').next())
                .unwrap_or_default();
        }
    }
    rules.sort();
    let merged = unresolved_finding_for(
        &rules[0],
        None,
        "repository",
        &format!(
            "{count} opaque text file(s) (no adapter, first `{first}`) were not read for comments or directives by {} rules ({})",
            rules.len(),
            rules.join(", ")
        ),
        UnresolvedReason::Fidelity,
    );
    let mut merged = Some(merged);
    raw.into_iter()
        .filter_map(|f| {
            if is_notice(&f) {
                merged.take()
            } else {
                Some(f)
            }
        })
        .collect()
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
    /// Files per rule family where every subject was `NotApplicable`.
    pub not_applicable: BTreeMap<String, usize>,
    /// Rule id to the reason it was not applicable to this language's files (the first seen).
    pub not_applicable_reasons: BTreeMap<String, String>,
    /// Unresolved findings per rule id raised for this language's files.
    pub unresolved: BTreeMap<String, usize>,
}

/// A second copy of a sibling in the other location (D87).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct OtherCopy {
    /// The executable of the copy not in use.
    pub path: String,
    /// First line of its `--version`, when it ran.
    pub version: Option<String>,
    /// True when its version differs from the copy in use.
    pub differs: bool,
}

/// One sibling product as discovered: beside the running executable first, then on `PATH` (D87).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct SiblingRow {
    /// Product (`grimble`, `crunk`).
    pub product: String,
    /// `beside-frob`, `path` or `absent`.
    pub location: String,
    /// The executable in use, when found.
    pub path: Option<String>,
    /// The version of the copy in use, when known.
    pub version: Option<String>,
    /// A different second copy, when one exists (`doctor` only).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub other: Option<OtherCopy>,
}

// frob:ticket 01M42M1KK02KFZG39CXKAD47SZ
/// Walked files no rule could read, counted by reason (`READ001`).
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, JsonSchema)]
pub struct SkippedReport {
    /// Files skipped in all.
    pub files: usize,
    /// Reason class (`encoding`, `permission`, `io`, `size`) to its file count.
    pub reasons: BTreeMap<String, usize>,
}

/// The per-language fidelity report of one run.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, JsonSchema)]
pub struct FidelityReport {
    /// Language label to its counts.
    pub languages: BTreeMap<String, LanguageFidelity>,
    /// Files that were walked but never read; they are in no language row and each has a `READ001` finding.
    pub skipped: SkippedReport,
    /// Rule id to why the rule does not apply to this product at all (`inapplicable()`), once per rule.
    #[serde(skip_serializing_if = "BTreeMap::is_empty")]
    pub inapplicable: BTreeMap<String, String>,
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

    /// Record why `rule` is not applicable to the files of language `label` (kept once per rule).
    pub fn add_not_applicable_reason(&mut self, label: &str, rule: &str, reason: &str) {
        let row = self.languages.entry(label.to_owned()).or_default();
        row.not_applicable_reasons
            .entry(rule.to_owned())
            .or_insert_with(|| reason.to_owned());
    }

    /// Record why `rule` does not apply to the product at all (kept once per rule).
    pub fn add_inapplicable(&mut self, rule: &str, reason: &str) {
        self.inapplicable
            .entry(rule.to_owned())
            .or_insert_with(|| reason.to_owned());
    }

    /// Count one unreadable file under its reason class.
    pub fn add_skipped(&mut self, kind: SkipKind) {
        self.skipped.files += 1;
        *self
            .skipped
            .reasons
            .entry(kind.as_str().to_owned())
            .or_default() += 1;
    }

    /// Add `n` Unresolved findings of `rule` to the language `label`.
    pub fn add_unresolved(&mut self, label: &str, rule: &str, n: usize) {
        let row = self.languages.entry(label.to_owned()).or_default();
        *row.unresolved.entry(rule.to_owned()).or_default() += n;
    }

    /// One text line per language, for `--timing --text`.
    pub fn lines(&self) -> Vec<String> {
        let inapplicable = self
            .inapplicable
            .iter()
            .map(|(rule, why)| format!("inapplicable {rule}: {why}"));
        self.languages
            .iter()
            .map(|(lang, r)| {
                let na: Vec<String> = r
                    .not_applicable
                    .iter()
                    .map(|(f, n)| format!("{f}={n}"))
                    .collect();
                let un: usize = r.unresolved.values().sum();
                let why: Vec<String> = r
                    .not_applicable_reasons
                    .iter()
                    .map(|(rule, reason)| format!("{rule}: {reason}"))
                    .collect();
                format!(
                    "fidelity {lang} ({}): {} files, {} examined, {} partial, not-applicable [{}] ({}), {un} unresolved",
                    r.fidelity,
                    r.files,
                    r.files_examined,
                    r.partial_parse,
                    na.join(" "),
                    why.join("; ")
                )
            })
            .chain(inapplicable)
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use gob_rules::{FixKind, Polarity, Scope, Tier};
    use gob_symbols::Fidelity;

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
            subject_status_for(&i, meta("TODO001"), false, false),
            SubjectStatus::Unresolved(_)
        ));
        assert!(matches!(
            subject_status_for(&i, meta("TODO001"), true, false),
            SubjectStatus::NotApplicable(_)
        ));
        assert!(matches!(
            subject_status(&i, meta("TODO001")),
            SubjectStatus::Unresolved(_)
        ));
    }

    #[test]
    fn scanned_opaque_text_is_examined() {
        assert_eq!(
            subject_status_for(&opaque(), meta("TODO001"), false, true),
            SubjectStatus::Examine
        );
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
    fn unknown_rules_are_always_examined() {
        assert_eq!(
            subject_status(&opaque(), meta("ZZZ001")),
            SubjectStatus::Examine
        );
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

    // frob:tests crates/gob-check/src/status.rs::FidelityReport.add_not_applicable_reason
    #[test]
    fn not_applicable_reasons_are_kept_once_and_printed() {
        let mut r = FidelityReport::default();
        r.add_not_applicable_reason("opaque", "DOC001", "no adapter");
        r.add_not_applicable_reason("opaque", "DOC001", "later reason");
        assert_eq!(
            r.languages["opaque"].not_applicable_reasons["DOC001"],
            "no adapter"
        );
        assert!(r.lines()[0].contains("DOC001: no adapter"));
    }

    // frob:tests crates/gob-check/src/status.rs::FidelityReport.add_inapplicable
    #[test]
    fn inapplicable_reasons_are_kept_once_and_printed() {
        let mut r = FidelityReport::default();
        r.add_inapplicable("REF001", "no ledger configured");
        r.add_inapplicable("REF001", "later reason");
        assert_eq!(r.inapplicable["REF001"], "no ledger configured");
        assert_eq!(r.lines(), ["inapplicable REF001: no ledger configured"]);
    }

    // frob:tests crates/gob-check/src/status.rs::is_binary
    #[test]
    fn binary_detection() {
        assert!(is_binary("a.png", b""));
        assert!(is_binary("a.dat", &[1, 0, 2]));
        assert!(!is_binary("a.py", b"print"));
    }

    // frob:ticket 01M4FG5RCDA668CK81QT54E67N
    #[test]
    fn opaque_notices_of_many_rules_merge_into_one_naming_count_and_rules() {
        let files: Vec<String> = (0..59).map(|i| format!("f{i}.txt")).collect();
        let refs: Vec<&str> = files.iter().map(String::as_str).collect();
        let other =
            unresolved_finding_for("DOC001", None, "a.rs", "hole", UnresolvedReason::Partial);
        let raw = vec![
            opaque_finding_for("TODO001", &refs),
            other,
            opaque_finding_for("DOC001", &refs),
            opaque_finding_for("REF001", &refs),
        ];
        let out = merge_opaque_notices(raw);
        let notices: Vec<&Finding> = out
            .iter()
            .filter(|f| f.message.contains(OPAQUE_MARK))
            .collect();
        assert_eq!(notices.len(), 1, "one notice per run, not per rule");
        assert_eq!(out.len(), 2, "unrelated findings are kept");
        let m = &notices[0].message;
        assert!(m.contains("59 opaque text file(s)"), "{m}");
        assert!(m.contains("`f0.txt`"), "{m}");
        for rule in ["DOC001", "REF001", "TODO001"] {
            assert!(m.contains(rule), "{m}");
        }
    }

    // frob:ticket 01M4FG5RCDA668CK81QT54E67N
    #[test]
    fn a_single_opaque_notice_is_left_untouched() {
        let raw = vec![opaque_finding_for("TODO001", &["a.txt"])];
        let out = merge_opaque_notices(raw.clone());
        assert_eq!(out, raw);
    }

    // frob:ticket 01M4GKD8WNG2NW2VAR1MBP382J
    #[test]
    fn locate_hole_points_at_the_table_row_with_the_pipe_in_a_code_span() {
        let text = "# T\n\n| a | b |\n|---|---|\n| `x|y` | ok |\n| `p||q` | bad |\n";
        let site = locate_hole("docs/t.md", text).expect("a site");
        assert_eq!(site.line, 6, "the doubled pipe is the strongest sign");
        assert_eq!(&text[site.range.to_usize_range()], "| `p||q` | bad |");
        assert!(site.cause.contains("unescaped `|`"));
        let only = locate_hole("t.md", "| `x|y` | ok |\n").expect("fallback");
        assert_eq!(only.line, 1);
        assert!(
            locate_hole("t.md", "| `x\\|y` | ok |\n").is_none(),
            "escaped"
        );
        assert!(
            locate_hole("t.rs", "| `x|y` |\n").is_none(),
            "markdown only"
        );
    }
}

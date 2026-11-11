//! The LOG pass: scan every supported file for direct output and report LOG001/LOG002.
//!
//! Scanning runs in rounds so a wrapper re-exported from one file (`say = print` in `util.py`)
//! is recognised where it is imported: each round feeds the module-level aliases of the previous
//! round back in as the project export table.

// frob:ticket 01M5XMR67K19SFAWNTDJKKJPTT

use std::collections::{BTreeMap, BTreeSet};

use gob_languages::{Language, ParseLimits, ParseResult, ParsedTree, parse};
use gob_rules::{Severity, UnresolvedReason};
use gob_walk::Glob;
use grimble_lints::pass::{PathFile, PathFinding, PathReport};

use super::catalogue::{Catalogue, Group};
use super::engine::{FileCtx, FileScan, Project, State, SymPath, logging_roots};
use super::universal::{UCall, mode_unresolved_calls, output_calls};
use super::{
    LOG001, LOG002, lang_bash, lang_c, lang_csharp, lang_java, lang_js, lang_python, lang_rust,
    lang_zig,
};

/// Most scan rounds: round 1 sees no exports, each further round sees the previous round's;
/// scanning stops early once the export table stops changing.
const MAX_ROUNDS: usize = 8;

/// What the LOG pass is told: the `[log]` table.
#[derive(Debug, Clone, Default)]
pub struct LogOptions {
    /// Globs of the logging module(s), where direct output is allowed.
    pub modules: Vec<String>,
    /// Globs of files that are never judged.
    pub exempt: Vec<String>,
    /// Extra logging crates or packages that count as a configured logging layer.
    pub extra_crates: Vec<String>,
}

/// The catalogue group a language is judged under, or `None` when unsupported.
fn group_of(language: Language) -> Option<&'static str> {
    match language {
        Language::Rust => Some("rust"),
        Language::Python => Some("python"),
        Language::JavaScript | Language::TypeScript | Language::Tsx | Language::Jsx => {
            Some("javascript")
        }
        Language::CSharp => Some("csharp"),
        Language::Java => Some("java"),
        Language::C | Language::Cpp | Language::Cuda => Some("c"),
        Language::Shell => Some("bash"),
        Language::Zig => Some("zig"),
        _ => None,
    }
}

/// A parsed, classified file.
struct Prepared<'a> {
    file: &'a PathFile<'a>,
    tree: ParsedTree,
    gid: &'static str,
    module: bool,
    exempt: bool,
}

fn compile(globs: &[String]) -> Vec<Glob> {
    globs
        .iter()
        .filter_map(|g| match Glob::parse(g) {
            Ok(g) => Some(g),
            Err(err) => {
                tracing::warn!(glob = %g, err = ?err, "ignoring an invalid [log] glob");
                None
            }
        })
        .collect()
}

/// The dotted module key a file registers its exports under.
fn module_key(path: &str, gid: &str) -> Option<String> {
    let stem = path.rsplit_once('.').map_or(path, |(s, _)| s);
    let mut parts: Vec<&str> = stem.split('/').collect();
    match gid {
        "python" => {
            if parts.last() == Some(&"__init__") {
                parts.pop();
            }
        }
        "javascript" => {
            if parts.last() == Some(&"index") {
                parts.pop();
            }
        }
        "rust" => {
            if parts.first() == Some(&"src") {
                parts.remove(0);
            }
            if matches!(parts.last(), Some(&("mod" | "lib" | "main"))) {
                parts.pop();
            }
        }
        _ => return None,
    }
    (!parts.is_empty()).then(|| parts.join("."))
}

fn scan_one(p: &Prepared<'_>, ctx: &FileCtx<'_>, cat: &Catalogue) -> Option<FileScan> {
    let group = cat.groups.get(p.gid)?;
    let st = State::new(group, ctx, p.file.text);
    let root = p.tree.root();
    Some(match p.gid {
        "rust" => lang_rust::scan(st, root),
        "python" => lang_python::scan(st, root),
        "javascript" => lang_js::scan(st, root),
        "java" => lang_java::scan(st, root),
        "c" => lang_c::scan(st, root),
        "bash" => lang_bash::scan(st, root),
        "zig" => lang_zig::scan(st, root),
        _ => lang_csharp::scan(st, root),
    })
}

/// True when the half-open byte range `[start, end)` overlaps any range in `covered`; a call with
/// no known span (`end <= start`) never counts as covered, so it is reported rather than hidden.
pub(crate) fn is_covered(covered: &[(usize, usize)], start: usize, end: usize) -> bool {
    end > start
        && covered
            .iter()
            .any(|&(a, b)| a < end && start < b.max(a + 1))
}

/// True when a call with no byte span (`end <= start`) sits on a line that any `covered` range
/// touches; the finest overlap available for an adapter that records lines but no spans.
pub(crate) fn line_covered(text: &str, covered: &[(usize, usize)], line: u32) -> bool {
    let line_of = |at: usize| {
        text.get(..at).map_or(0, |t| {
            u32::try_from(t.matches('\n').count())
                .unwrap_or(u32::MAX)
                .saturating_add(1)
        })
    };
    covered
        .iter()
        .any(|&(a, b)| (line_of(a)..=line_of(b.max(a))).contains(&line))
}

/// Cross-check a scanner against the universal model: a call `U` resolves to direct output at a
/// byte range the scanner neither hit nor flagged is reported Unresolved, never silently clean.
/// Matching is by byte overlap, so a second call on a line the scanner reported is still caught.
fn cross_check(p: &Prepared<'_>, scan: &FileScan, group: &Group, report: &mut PathReport) {
    let text = p.file.text;
    let covered: Vec<(usize, usize)> = scan
        .hits
        .iter()
        .map(|h| (h.start, h.end))
        .chain(scan.unresolved.iter().map(|u| (u.start, u.end)))
        .collect();
    for (i, u) in output_calls(p.gid, p.file.path, text, group)
        .into_iter()
        .filter(|u| {
            if u.end > u.start {
                !is_covered(&covered, u.start, u.end)
            } else {
                !line_covered(text, &covered, u.line)
            }
        })
        .enumerate()
    {
        let (start, end) = (u.start, u.end.min(text.len()));
        tracing::debug!(
            file = p.file.path,
            line = u.line,
            start,
            end,
            path = %u.path.join("."),
            "scanner and U disagree"
        );
        report.findings.push(PathFinding {
            rule: LOG001,
            severity: Severity::Unresolved,
            file: p.file.path.to_owned(),
            range: (start, end),
            message: format!(
                "the universal model resolves this call to `{}` ({}) but the scanner did not report it; \
                 Agents: route it through the logging layer or make the target explicit. \
                 Humans: waive with `frob:waive LOG001 <reason>`.",
                u.path.join("."),
                group.atoms[u.atom].id
            ),
            reason: Some(UnresolvedReason::Fidelity),
            anchor: format!("{}:universal:{i}", p.file.path),
        });
    }
    cross_check_modes(p, &covered, group, report);
}

/// True when the scanner already hit or flagged the model call `u` (by byte span, or by line
/// when the adapter records no span).
fn call_covered(text: &str, covered: &[(usize, usize)], u: &UCall) -> bool {
    if u.end > u.start {
        is_covered(covered, u.start, u.end)
    } else {
        line_covered(text, covered, u.line)
    }
}

/// Mode-aware calls with an undecidable mode that the scanner has neither hit nor flagged.
fn uncovered_mode_calls(
    gid: &str,
    path: &str,
    text: &str,
    group: &Group,
    covered: &[(usize, usize)],
) -> Vec<UCall> {
    mode_unresolved_calls(gid, path, text, group)
        .into_iter()
        .filter(|u| !call_covered(text, covered, u))
        .collect()
}

/// Report mode-aware calls whose mode argument `U` cannot decide as LOG001 Unresolved, unless the
/// scanner already accounts for them: whether they open for writing is unknown, never clean.
fn cross_check_modes(
    p: &Prepared<'_>,
    covered: &[(usize, usize)],
    group: &Group,
    report: &mut PathReport,
) {
    let text = p.file.text;
    for (i, u) in uncovered_mode_calls(p.gid, p.file.path, text, group, covered)
        .into_iter()
        .enumerate()
    {
        let (start, end) = (u.start, u.end.min(text.len()));
        tracing::debug!(
            file = p.file.path,
            line = u.line,
            path = %u.path.join("."),
            "mode argument undecidable"
        );
        report.findings.push(PathFinding {
            rule: LOG001,
            severity: Severity::Unresolved,
            file: p.file.path.to_owned(),
            range: (start, end),
            message: format!(
                "`{}` ({}) takes a mode argument the analysis cannot decide, so whether it opens \
                 for writing is unresolved; Agents: pass a literal mode or route output through \
                 the logging layer. Humans: waive with `frob:waive LOG001 <reason>`.",
                u.path.join("."),
                group.atoms[u.atom].id
            ),
            reason: Some(UnresolvedReason::Fidelity),
            anchor: format!("{}:universal-mode:{i}", p.file.path),
        });
    }
}

/// Run LOG001 and LOG002 over `files` with `opts`.
#[allow(
    clippy::too_many_lines,
    reason = "one linear pass: parse, scan rounds, then findings"
)]
pub fn analyze(files: &[PathFile<'_>], opts: &LogOptions) -> PathReport {
    let mut report = PathReport::default();
    let cat = match Catalogue::builtin() {
        Ok(c) => c,
        Err(err) => {
            tracing::error!(%err, "the output-atom catalogue failed to load");
            for id in [LOG001, LOG002] {
                report
                    .not_applicable
                    .insert(id, format!("the output-atom catalogue is invalid: {err}"));
            }
            return report;
        }
    };
    let modules = compile(&opts.modules);
    let exempt = compile(&opts.exempt);
    let limits = ParseLimits::default();
    let mut prepared: Vec<Prepared<'_>> = Vec::new();
    for f in files {
        let Some(gid) = group_of(f.language) else {
            continue;
        };
        let ParseResult::Parsed(tree) = parse(f.language, f.text, &limits) else {
            tracing::debug!(file = f.path, "log pass skipped an unparsable file");
            continue;
        };
        prepared.push(Prepared {
            file: f,
            tree,
            gid,
            module: modules.iter().any(|g| g.matches_path(f.path)),
            exempt: grimble_lints::path::is_test_path(f.path)
                || exempt.iter().any(|g| g.matches_path(f.path)),
        });
    }
    if prepared.is_empty() {
        let why =
            "no Rust, Python, JavaScript, TypeScript, C#, Java, C, C++, CUDA, Zig or shell file in the walk"
                .to_owned();
        report.not_applicable.insert(LOG001, why.clone());
        report.not_applicable.insert(LOG002, why);
        return report;
    }

    let roots: BTreeMap<&str, Vec<SymPath>> = [
        "rust",
        "python",
        "javascript",
        "csharp",
        "java",
        "c",
        "bash",
        "zig",
    ]
    .into_iter()
    .map(|g| (g, logging_roots(g, &opts.extra_crates)))
    .collect();
    let mut project = Project::default();
    for p in &prepared {
        if p.gid == "csharp" {
            project
                .globals
                .extend(lang_csharp::global_usings(p.file.text, p.tree.root()));
        }
    }
    let decls: Vec<_> = prepared
        .iter()
        .filter(|p| p.gid == "csharp")
        .map(|p| lang_csharp::declarations(p.file.text, p.tree.root(), &project.globals))
        .collect();
    lang_csharp::seed(&mut project, &decls);
    let seeded = project.clone();
    let mut scans: Vec<Option<FileScan>> = Vec::new();
    for _round in 0..MAX_ROUNDS {
        scans = prepared
            .iter()
            .map(|p| {
                let ctx = FileCtx {
                    path: p.file.path,
                    project: &project,
                    roots: &roots[p.gid],
                };
                scan_one(p, &ctx, cat)
            })
            .collect();
        let mut next = seeded.clone();
        for (p, s) in prepared.iter().zip(&scans) {
            if let (Some(key), Some(s)) = (module_key(p.file.path, p.gid), s) {
                next.register(&key, &s.exports);
            }
        }
        if next.modules == project.modules {
            break;
        }
        project = next;
    }

    let mut logging: BTreeSet<&str> = BTreeSet::new();
    let mut first_hit: BTreeMap<&str, (String, (usize, usize), String)> = BTreeMap::new();
    let mut examined = 0usize;
    for (p, s) in prepared.iter().zip(&scans) {
        let Some(s) = s else { continue };
        if s.logging_seen {
            logging.insert(p.gid);
        }
        if p.exempt {
            continue;
        }
        let group = &cat.groups[p.gid];
        if !p.module {
            examined += 1;
        }
        let mut seen: BTreeMap<String, usize> = BTreeMap::new();
        for h in &s.hits {
            let atom = &group.atoms[h.atom];
            let channels = format!("{} via `{}`", atom.ch, h.path);
            first_hit
                .entry(p.gid)
                .or_insert_with(|| (p.file.path.to_owned(), (h.start, h.end), channels.clone()));
            if p.module {
                continue;
            }
            let key = format!("{}:{}", atom.id, h.path);
            let nth = seen.entry(key.clone()).or_insert(0);
            let anchor = format!("{}:{key}:{nth}", p.file.path);
            *nth += 1;
            let replacement = if atom.use_.is_empty() {
                group.replacement.as_str()
            } else {
                atom.use_.as_str()
            };
            report.findings.push(PathFinding {
                rule: LOG001,
                severity: Severity::Error,
                file: p.file.path.to_owned(),
                range: (h.start, h.end),
                message: format!(
                    "direct output ({channels}): {}. Route it through the logging layer instead (use {replacement}). \
                     Agents: obey this and do not waive it yourself. Humans: if the direct output is intended, \
                     waive it with `frob:waive LOG001 <reason>` (the reason is required).",
                    atom.why
                ),
                reason: None,
                anchor,
            });
        }
        if p.module {
            continue;
        }
        cross_check(p, s, group, &mut report);
        for (i, u) in s.unresolved.iter().enumerate() {
            report.findings.push(PathFinding {
                rule: LOG001,
                severity: Severity::Unresolved,
                file: p.file.path.to_owned(),
                range: (u.start, u.end),
                message: format!(
                    "{}: the output target cannot be resolved statically; \
                     Agents: rewrite it with a literal name or route it through the logging layer. \
                     Humans: waive with `frob:waive LOG001 <reason>`.",
                    u.what
                ),
                reason: Some(UnresolvedReason::Fidelity),
                anchor: format!("{}:dynamic:{i}", p.file.path),
            });
        }
    }
    for (gid, (file, range, what)) in first_hit {
        if logging.contains(gid) {
            continue;
        }
        let group = &cat.groups[gid];
        report.findings.push(PathFinding {
            rule: LOG002,
            severity: Severity::Error,
            file,
            range,
            message: format!(
                "the {gid} program emits output ({what}) but configures no logging crate. \
                 Agents: add and configure one (use {}) in the logging module and route output through it. \
                 Humans: if no logging layer is wanted, waive with `frob:waive LOG002 <reason>` (the reason is required).",
                group.replacement
            ),
            reason: None,
            anchor: format!("LOG002:{gid}"),
        });
    }
    report.subjects.insert(LOG001, examined);
    report.subjects.insert(LOG002, examined);
    report
        .findings
        .sort_by(|a, b| (&a.file, a.rule, &a.anchor).cmp(&(&b.file, b.rule, &b.anchor)));
    tracing::debug!(findings = report.findings.len(), examined, "log pass done");
    report
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/grimble-check/src/log/pass.rs::is_covered
    #[test]
    fn coverage_is_by_byte_overlap_not_line() {
        // `print(1); print(2)`: the scanner hit only the first call, bytes 0..8.
        let covered = [(0, 8)];
        assert!(is_covered(&covered, 0, 8));
        assert!(!is_covered(&covered, 10, 18), "same line, other bytes");
        assert!(
            !is_covered(&covered, 8, 10),
            "touching ranges do not overlap"
        );
    }

    // frob:tests crates/grimble-check/src/log/pass.rs::line_covered
    #[test]
    fn spanless_calls_are_covered_by_line() {
        let text = "a\nbb\nccc\n";
        assert!(line_covered(text, &[(2, 4)], 2));
        assert!(!line_covered(text, &[(2, 4)], 3));
    }

    // frob:tests crates/grimble-check/src/log/pass.rs::analyze
    #[test]
    fn csharp_console_calls_are_not_double_reported_by_the_cross_check() {
        let text = "using System;\nclass A { void F() {\n Console.WriteLine(1);\n } }\n";
        let files = [PathFile {
            path: "A.cs",
            language: Language::CSharp,
            text,
        }];
        let r = analyze(&files, &LogOptions::default());
        let uni = r
            .findings
            .iter()
            .filter(|f| f.anchor.contains(":universal:"))
            .count();
        assert_eq!(uni, 0, "{:?}", r.findings);
        assert!(
            r.findings.iter().any(|f| f.rule == LOG001),
            "{:?}",
            r.findings
        );
    }

    // frob:tests crates/grimble-check/src/log/pass.rs::analyze
    #[test]
    fn csharp_second_call_on_a_line_is_byte_precise() {
        let text =
            "using System;\nclass A { void F() {\n Console.WriteLine(1); Console.Write(2);\n } }\n";
        let files = [PathFile {
            path: "A.cs",
            language: Language::CSharp,
            text,
        }];
        let r = analyze(&files, &LogOptions::default());
        let uni = r
            .findings
            .iter()
            .filter(|f| f.anchor.contains(":universal:"))
            .count();
        assert_eq!(uni, 0, "{:?}", r.findings);
    }

    // frob:tests crates/grimble-check/src/log/pass.rs::is_covered
    #[test]
    fn unknown_span_is_never_covered() {
        assert!(!is_covered(&[(0, 100)], 5, 5));
        assert!(!is_covered(&[(0, 100)], 0, 0));
    }

    // frob:tests crates/grimble-check/src/log/pass.rs::analyze
    #[test]
    fn analyze_runs_the_byte_precise_cross_check_without_panic() {
        let text = "def f():\n    print(1); print(2)\n";
        let files = [PathFile {
            path: "a.py",
            language: Language::Python,
            text,
        }];
        let r = analyze(&files, &LogOptions::default());
        let universal = r
            .findings
            .iter()
            .filter(|f| f.anchor.contains(":universal:"))
            .count();
        assert_eq!(universal, 0, "scanner reports both calls: {:?}", r.findings);
        let hits = r.findings.iter().filter(|f| f.rule == LOG001).count();
        assert!(hits >= 2, "{:?}", r.findings);
    }

    // frob:tests crates/grimble-check/src/log/pass.rs::uncovered_mode_calls
    #[test]
    fn undecidable_mode_is_listed_unless_scanner_covers_it() {
        let cat = Catalogue::builtin().expect("catalogue");
        let group = cat.groups.get("python").expect("python group");
        let text = "def f(p, m):\n    open(p, m)\n";
        let all = uncovered_mode_calls("python", "a.py", text, group, &[]);
        assert_eq!(all.len(), 1, "undecidable mode must be listed");
        let covered = [(all[0].start, all[0].end)];
        let none = uncovered_mode_calls("python", "a.py", text, group, &covered);
        assert!(none.is_empty(), "scanner-covered call is not duplicated");
    }

    // frob:tests crates/grimble-check/src/log/pass.rs::uncovered_mode_calls
    #[test]
    fn literal_mode_is_not_listed() {
        let cat = Catalogue::builtin().expect("catalogue");
        let group = cat.groups.get("python").expect("python group");
        let text = "def f(p):\n    open(p, \"r\")\n";
        assert!(uncovered_mode_calls("python", "a.py", text, group, &[]).is_empty());
    }
}

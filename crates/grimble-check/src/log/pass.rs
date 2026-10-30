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

use super::catalogue::Catalogue;
use super::engine::{FileCtx, FileScan, Project, State, SymPath, logging_roots};
use super::{LOG001, LOG002, lang_csharp, lang_js, lang_python, lang_rust};

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
        _ => lang_csharp::scan(st, root),
    })
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
        let why = "no Rust, Python, JavaScript, TypeScript or C# file in the walk".to_owned();
        report.not_applicable.insert(LOG001, why.clone());
        report.not_applicable.insert(LOG002, why);
        return report;
    }

    let roots: BTreeMap<&str, Vec<SymPath>> = ["rust", "python", "javascript", "csharp"]
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

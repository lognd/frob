//! The output-atom catalogue loader: reads the `toml output-atoms` and `toml output-languages`
//! fences of `docs/design/output-atoms.md` so a new atom is a new row, never a code change.

// frob:ticket 01M5XMR67K19SFAWNTDJKKJPTT

use std::collections::BTreeMap;
use std::sync::OnceLock;

use serde::Deserialize;

/// The catalogue document, embedded at build time; the file under `docs/` is the single source.
const BUILTIN: &str = include_str!("../../../../docs/design/output-atoms.md");

/// One segment of a symbol pattern: a literal name or `*` (any single segment).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Seg {
    /// A literal path segment.
    Lit(String),
    /// `*`: any one segment.
    Any,
}

/// The int, string and path facts about one call argument that `when` and `mode_arg` conditions read.
#[derive(Debug, Clone, Default)]
pub struct ArgInfo {
    /// The argument as an integer literal.
    pub int: Option<i64>,
    /// The argument as a string literal (quotes removed).
    pub text: Option<String>,
    /// The argument as a resolved symbol path (`sys.stdout.fileno`).
    pub path: Option<Vec<String>>,
}

/// The positional and keyword arguments of one call.
#[derive(Debug, Clone, Default)]
pub struct Args {
    /// Positional arguments in order.
    pub pos: Vec<ArgInfo>,
    /// Keyword arguments by name.
    pub kw: Vec<(String, ArgInfo)>,
}

/// One row of the catalogue: an output channel and the symbols that reach it.
#[derive(Debug, Clone)]
pub struct Atom {
    /// The unique atom id (`py.print`).
    pub id: String,
    /// The channel (`stdout`, `stderr`, `file`, ...).
    pub ch: String,
    /// The compiled symbol patterns (alternatives).
    pub patterns: Vec<Vec<Seg>>,
    /// The resolution classes that can hide the atom.
    pub via: Vec<String>,
    /// Why the atom counts as output.
    pub why: String,
    /// The sanctioned replacement at the call site.
    pub use_: String,
    /// The argument condition, when the atom is conditional.
    pub when: Option<String>,
    /// The 0-based index of the mode/flags argument, when the atom is mode-aware.
    pub mode_arg: Option<usize>,
    /// True for implicit or low-signal atoms that are loaded but not reported.
    pub advisory: bool,
}

/// The atoms of one language group and its sanctioned logging facade.
#[derive(Debug, Clone, Default)]
pub struct Group {
    /// The group id (`rust`, `python`, `javascript`, `csharp`, ...).
    pub language: String,
    /// True when the language row says `status = "supported"`.
    pub supported: bool,
    /// The sanctioned logging facade named in findings.
    pub replacement: String,
    /// The atoms in catalogue order.
    pub atoms: Vec<Atom>,
}

/// The parsed catalogue: groups by language id.
#[derive(Debug, Clone, Default)]
pub struct Catalogue {
    /// Groups by language id.
    pub groups: BTreeMap<String, Group>,
}

/// Why the catalogue could not be loaded.
#[derive(Debug, thiserror::Error)]
pub enum CatalogueError {
    /// A fence held invalid TOML or a wrong shape.
    #[error("output-atoms catalogue fence {fence} is invalid: {source}")]
    Toml {
        /// Which fence kind failed.
        fence: &'static str,
        /// The TOML error.
        source: toml::de::Error,
    },
    /// Two atoms share an id.
    #[error("output-atoms catalogue repeats atom id {0}")]
    DuplicateId(String),
}

#[derive(Deserialize)]
struct LangRow {
    id: String,
    status: String,
    #[serde(default)]
    replacement: String,
}

#[derive(Deserialize)]
struct LangFile {
    #[serde(default)]
    language: Vec<LangRow>,
}

#[derive(Deserialize)]
struct AtomRow {
    id: String,
    #[serde(default)]
    ch: String,
    sym: String,
    #[serde(default)]
    via: Vec<String>,
    #[serde(default)]
    why: String,
    #[serde(default, rename = "use")]
    use_: String,
    when: Option<String>,
    sev: Option<String>,
    mode_arg: Option<usize>,
}

#[derive(Deserialize)]
struct AtomFile {
    language: String,
    #[serde(default)]
    atoms: Vec<AtomRow>,
}

/// The std stream paths a `path-literal` condition accepts.
const STD_PATHS: &[&str] = &[
    "/dev/stdout",
    "/dev/stderr",
    "/dev/fd/1",
    "/dev/fd/2",
    "/proc/self/fd/1",
    "/proc/self/fd/2",
    "/dev/tty",
    "/dev/console",
    "CON",
    "CONOUT$",
];

/// The fenced TOML bodies of the document whose info string is exactly `toml <kind>`.
fn fences(text: &str, kind: &str) -> Vec<String> {
    let open = format!("```toml {kind}");
    let mut out = Vec::new();
    let mut cur: Option<String> = None;
    for line in text.lines() {
        match cur.as_mut() {
            Some(body) if line.trim_end() == "```" => {
                out.push(std::mem::take(body));
                cur = None;
            }
            Some(body) => {
                body.push_str(line);
                body.push('\n');
            }
            None if line.trim_end() == open => cur = Some(String::new()),
            None => {}
        }
    }
    out
}

/// Split `s` at top-level (brace depth 0) `,` and `|`.
fn split_top(s: &str) -> Vec<String> {
    let (mut depth, mut cur, mut out) = (0i32, String::new(), Vec::new());
    for c in s.chars() {
        match c {
            '{' => {
                depth += 1;
                cur.push(c);
            }
            '}' => {
                depth -= 1;
                cur.push(c);
            }
            ',' | '|' if depth == 0 => out.push(std::mem::take(&mut cur)),
            _ => cur.push(c),
        }
    }
    out.push(cur);
    out
}

/// Expand the first top-level `{a,b}` group of `s` recursively into plain alternatives.
fn expand_braces(s: &str) -> Vec<String> {
    let Some(open) = s.find('{') else {
        return vec![s.to_owned()];
    };
    let (mut depth, mut close) = (0i32, None);
    for (i, c) in s.char_indices().skip_while(|(i, _)| *i < open) {
        match c {
            '{' => depth += 1,
            '}' => {
                depth -= 1;
                if depth == 0 {
                    close = Some(i);
                    break;
                }
            }
            _ => {}
        }
    }
    let Some(close) = close else {
        return vec![s.to_owned()];
    };
    let (head, inner, tail) = (&s[..open], &s[open + 1..close], &s[close + 1..]);
    let mut out = Vec::new();
    for option in split_top(inner) {
        for e in expand_braces(&format!("{head}{}{tail}", option.trim())) {
            out.push(e);
        }
    }
    out
}

/// Compile a `sym` cell into patterns; prose alternatives (spaces, quotes, `<expr>`) are discarded.
#[must_use]
pub fn compile_sym(sym: &str) -> Vec<Vec<Seg>> {
    let mut patterns = Vec::new();
    for alt in split_top(sym) {
        for flat in expand_braces(alt.trim()) {
            let flat = flat.trim().replace("::", ".");
            let legal = !flat.is_empty()
                && flat
                    .chars()
                    .all(|c| c.is_alphanumeric() || matches!(c, '_' | '.' | '*' | '$' | '!'));
            if !legal || flat.split('.').any(str::is_empty) {
                tracing::debug!(sym = %sym, alt = %flat, "catalogue symbol alternative discarded as prose");
                continue;
            }
            patterns.push(
                flat.split('.')
                    .map(|s| {
                        if s == "*" {
                            Seg::Any
                        } else {
                            Seg::Lit(s.trim_end_matches('!').to_owned())
                        }
                    })
                    .collect(),
            );
        }
    }
    patterns
}

impl Atom {
    /// True when `path` starts with one of this atom's patterns (segment-prefix match).
    #[must_use]
    pub fn matches_path(&self, path: &[String]) -> bool {
        self.patterns.iter().any(|pat| {
            path.len() >= pat.len()
                && pat.iter().zip(path).all(|(seg, p)| match seg {
                    Seg::Any => true,
                    Seg::Lit(l) => l == p,
                })
        })
    }

    /// True when `path` is a proper leading part of one of this atom's symbol patterns.
    #[must_use]
    pub fn is_prefix(&self, path: &[String]) -> bool {
        self.patterns.iter().any(|pat| {
            path.len() < pat.len()
                && pat.iter().zip(path).all(|(seg, p)| match seg {
                    Seg::Any => true,
                    Seg::Lit(l) => l == p,
                })
        })
    }

    /// True when the call's arguments satisfy this atom's `when` / `mode_arg` conditions.
    #[must_use]
    pub fn conditions_hold(&self, args: &Args) -> bool {
        if let Some(i) = self.mode_arg {
            let arg = args.pos.get(i).or_else(|| {
                args.kw
                    .iter()
                    .find(|(k, _)| k == "mode" || k == "flags")
                    .map(|(_, v)| v)
            });
            let writes = arg
                .and_then(|a| a.text.as_deref())
                .is_some_and(|m| m.chars().any(|c| matches!(c, 'w' | 'a' | 'x' | '+')));
            if !writes {
                return false;
            }
        }
        if self.when.is_none() {
            return true;
        }
        let all = || args.pos.iter().chain(args.kw.iter().map(|(_, v)| v));
        if self.via.iter().any(|v| v == "fd-literal") {
            return all().any(|a| {
                matches!(a.int, Some(1 | 2)) || a.path.as_ref().is_some_and(|p| is_std_fd_path(p))
            });
        }
        if self.via.iter().any(|v| v == "path-literal") {
            return all().any(|a| a.text.as_deref().is_some_and(|t| STD_PATHS.contains(&t)));
        }
        false
    }
}

/// True when `path` is a std stream or its fileno/fd (`sys.stdout.fileno`, `process.stderr.fd`).
fn is_std_fd_path(p: &[String]) -> bool {
    let head = |a: &str, b: &str| p.len() >= 2 && p[0] == a && p[1] == b;
    head("sys", "stdout")
        || head("sys", "stderr")
        || head("process", "stdout")
        || head("process", "stderr")
        || p.last()
            .is_some_and(|l| l == "STDOUT_FILENO" || l == "STDERR_FILENO")
}

impl Group {
    /// The index of the first reportable atom matching `path` whose conditions hold for `args`.
    #[must_use]
    pub fn first_match(&self, path: &[String], args: &Args) -> Option<usize> {
        self.atoms
            .iter()
            .position(|a| !a.advisory && a.matches_path(path) && a.conditions_hold(args))
    }

    /// The index of the first reportable atom matching `path` as a bare reference (no call, no conditions).
    #[must_use]
    pub fn first_ref(&self, path: &[String]) -> Option<usize> {
        self.atoms.iter().position(|a| {
            !a.advisory && a.when.is_none() && a.mode_arg.is_none() && a.matches_path(path)
        })
    }

    /// True when any atom (advisory or not) matches `path`, or `path` is a leading part of one
    /// (so `System.Console` resolves a bare `Console` under `using System;`).
    #[must_use]
    pub fn any_atom(&self, path: &[String]) -> bool {
        self.atoms
            .iter()
            .any(|a| a.matches_path(path) || a.is_prefix(path))
    }
}

impl Catalogue {
    /// Parse the catalogue from a markdown document holding the two fence kinds.
    ///
    /// # Errors
    ///
    /// [`CatalogueError`] for a fence with invalid TOML or a repeated atom id.
    pub fn parse(text: &str) -> Result<Self, CatalogueError> {
        let mut cat = Self::default();
        let mut langs: BTreeMap<String, (bool, String)> = BTreeMap::new();
        for body in fences(text, "output-languages") {
            let file: LangFile = toml::from_str(&body).map_err(|source| CatalogueError::Toml {
                fence: "output-languages",
                source,
            })?;
            for row in file.language {
                langs.insert(row.id, (row.status == "supported", row.replacement));
            }
        }
        let mut seen = std::collections::BTreeSet::new();
        for body in fences(text, "output-atoms") {
            let file: AtomFile = toml::from_str(&body).map_err(|source| CatalogueError::Toml {
                fence: "output-atoms",
                source,
            })?;
            let (supported, replacement) = langs.get(&file.language).cloned().unwrap_or_default();
            let group = cat
                .groups
                .entry(file.language.clone())
                .or_insert_with(|| Group {
                    language: file.language.clone(),
                    supported,
                    replacement,
                    atoms: Vec::new(),
                });
            for row in file.atoms {
                if !seen.insert(row.id.clone()) {
                    return Err(CatalogueError::DuplicateId(row.id));
                }
                group.atoms.push(Atom {
                    patterns: compile_sym(&row.sym),
                    id: row.id,
                    ch: row.ch,
                    via: row.via,
                    why: row.why,
                    use_: row.use_,
                    when: row.when,
                    mode_arg: row.mode_arg,
                    advisory: row.sev.as_deref() == Some("advisory"),
                });
            }
        }
        tracing::info!(
            groups = cat.groups.len(),
            atoms = cat.groups.values().map(|g| g.atoms.len()).sum::<usize>(),
            "output-atom catalogue parsed"
        );
        Ok(cat)
    }

    /// The catalogue embedded from `docs/design/output-atoms.md`.
    ///
    /// # Errors
    ///
    /// The [`CatalogueError`] of the embedded document (a build-time bug a test catches).
    pub fn builtin() -> Result<&'static Self, &'static CatalogueError> {
        static CELL: OnceLock<Result<Catalogue, CatalogueError>> = OnceLock::new();
        CELL.get_or_init(|| Self::parse(BUILTIN)).as_ref()
    }

    /// The digest of the embedded document, for cache keys.
    #[must_use]
    pub fn builtin_digest() -> String {
        gob_walk::Digest::of(BUILTIN.as_bytes()).to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:ticket 01M5XMR67K19SFAWNTDJKKJPTT
    // frob:tests crates/grimble-check/src/log/catalogue.rs::Catalogue
    #[test]
    fn builtin_catalogue_parses_with_every_supported_language() {
        let cat = Catalogue::builtin().expect("builtin catalogue");
        for g in ["rust", "python", "javascript", "csharp"] {
            assert!(
                cat.groups.get(g).is_some_and(|g| !g.atoms.is_empty()),
                "{g}"
            );
        }
    }

    // frob:tests crates/grimble-check/src/log/catalogue.rs::Catalogue
    #[test]
    fn a_new_row_needs_no_code_change() {
        let text = "```toml output-languages\n[[language]]\nid = \"python\"\nstatus = \"supported\"\ngrammar = \"g\"\nresolution = []\nreplacement = \"logger\"\n```\n\n```toml output-atoms\nlanguage = \"python\"\natoms = [\n { id = \"py.custom\", ch = \"stdout\", sym = \"mylib.shout\", form = \"fn\", via = [], why = \"w\", use = \"u\" },\n]\n```\n";
        let cat = Catalogue::parse(text).expect("parse");
        let g = &cat.groups["python"];
        let path = vec!["mylib".to_owned(), "shout".to_owned()];
        assert_eq!(g.first_match(&path, &Args::default()), Some(0));
    }
}

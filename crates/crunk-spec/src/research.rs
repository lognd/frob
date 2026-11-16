//! Research artifacts of the design cycle: `design/research/*.md` (YAML-style front matter),
//! `design/personas/*.toml` and `design/journeys/*.toml`. Parsing is pure; [`load_research`] reads
//! a project and reports every unreadable or invalid file as a located [`ResearchProblem`].

// frob:ticket 01M5XCYCSXSPQP9A4DZKNX5RGS

use std::collections::BTreeSet;
use std::path::Path;

use serde::Deserialize;

/// Directory holding research notes, relative to the project root.
pub const RESEARCH_DIR: &str = "design/research";
/// Directory holding persona files, relative to the project root.
pub const PERSONAS_DIR: &str = "design/personas";
/// Directory holding journey files, relative to the project root.
pub const JOURNEYS_DIR: &str = "design/journeys";

/// A calendar date, `YYYY-MM-DD`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct Date {
    year: i64,
    month: u32,
    day: u32,
}

impl Date {
    /// Parse `YYYY-MM-DD`; `None` for any other shape or an impossible month or day.
    #[must_use]
    pub fn parse(text: &str) -> Option<Self> {
        let mut parts = text.trim().split('-');
        let year: i64 = parts.next()?.parse().ok()?;
        let month: u32 = parts.next()?.parse().ok()?;
        let day: u32 = parts.next()?.parse().ok()?;
        if parts.next().is_some() || !(1..=12).contains(&month) || !(1..=31).contains(&day) {
            return None;
        }
        Some(Self { year, month, day })
    }

    /// Days since 1970-01-01 (proleptic Gregorian), so two dates subtract to an age in days.
    #[must_use]
    pub fn days(self) -> i64 {
        let y = if self.month <= 2 {
            self.year - 1
        } else {
            self.year
        };
        let era = y.div_euclid(400);
        let yoe = y.rem_euclid(400);
        let mp = i64::from((self.month + 9) % 12);
        let doy = (153 * mp + 2) / 5 + i64::from(self.day) - 1;
        let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
        era * 146_097 + doe - 719_468
    }
}

/// Why a research artifact could not be read.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("{message}")]
pub struct ResearchError {
    /// The 1-based line the problem is on, when known.
    pub line: Option<usize>,
    /// What is wrong.
    pub message: String,
}

impl ResearchError {
    /// An error at `line`.
    fn at(line: usize, message: impl Into<String>) -> Self {
        Self {
            line: Some(line),
            message: message.into(),
        }
    }
}

/// One research note's front matter.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResearchDoc {
    /// The id other artifacts cite.
    pub id: String,
    /// When the research was done.
    pub date: Date,
}

/// A persona file (`design/personas/<id>.toml`).
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PersonaFile {
    /// The persona id screens cite.
    pub id: String,
    /// Display name.
    #[serde(default)]
    pub name: Option<String>,
    /// Research ids that back this persona.
    #[serde(default)]
    pub evidence: Vec<String>,
}

/// A journey file (`design/journeys/<id>.toml`).
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct JourneyFile {
    /// The journey id.
    pub id: String,
    /// The persona walking the journey.
    #[serde(default)]
    pub persona: Option<String>,
    /// Research ids that back this journey.
    #[serde(default)]
    pub evidence: Vec<String>,
}

/// Strip one pair of matching quotes.
fn unquote(v: &str) -> &str {
    let v = v.trim();
    for q in ['"', '\''] {
        if let Some(inner) = v.strip_prefix(q).and_then(|r| r.strip_suffix(q)) {
            return inner;
        }
    }
    v
}

/// Parse a research note's front matter (the block between the leading `---` lines).
///
/// # Errors
/// [`ResearchError`] at the offending line for a missing or unclosed block, a malformed line, or a
/// missing `id` or missing/invalid `date`.
pub fn parse_research(text: &str) -> Result<ResearchDoc, ResearchError> {
    let mut lines = text.lines().enumerate();
    match lines.next() {
        Some((_, l)) if l.trim_end() == "---" => {}
        _ => {
            return Err(ResearchError::at(
                1,
                "missing front matter (expected `---`)",
            ));
        }
    }
    let (mut id, mut date) = (None, None);
    let mut closed = false;
    for (i, raw) in lines {
        let n = i + 1;
        let line = raw.trim_end();
        if line == "---" {
            closed = true;
            break;
        }
        let t = line.trim_start();
        if t.is_empty() || t.starts_with('#') || t.starts_with("- ") || line.starts_with(' ') {
            continue;
        }
        let Some((key, value)) = line.split_once(':') else {
            return Err(ResearchError::at(
                n,
                format!("malformed front matter line `{line}`"),
            ));
        };
        match key.trim() {
            "id" => id = Some(unquote(value).to_owned()),
            "date" => {
                let d = Date::parse(unquote(value)).ok_or_else(|| {
                    ResearchError::at(n, format!("invalid date `{}`", value.trim()))
                })?;
                date = Some(d);
            }
            _ => {}
        }
    }
    if !closed {
        return Err(ResearchError::at(
            1,
            "front matter is not closed with `---`",
        ));
    }
    match (id.filter(|s| !s.is_empty()), date) {
        (Some(id), Some(date)) => Ok(ResearchDoc { id, date }),
        (None, _) => Err(ResearchError::at(1, "front matter needs an `id`")),
        (_, None) => Err(ResearchError::at(1, "front matter needs a `date`")),
    }
}

/// Parse a persona or journey TOML file into `T`.
///
/// # Errors
/// [`ResearchError`] for invalid TOML or the wrong schema.
pub fn parse_toml<T: serde::de::DeserializeOwned>(text: &str) -> Result<T, ResearchError> {
    toml_edit::de::from_str(text).map_err(|e| ResearchError {
        line: None,
        message: e.to_string(),
    })
}

/// A research file that could not be loaded.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResearchProblem {
    /// The file, relative to the project root.
    pub path: String,
    /// The 1-based line, when known.
    pub line: Option<usize>,
    /// What is wrong.
    pub message: String,
}

/// Everything loaded from a project's research artifacts; each list is sorted by path.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ResearchSet {
    /// Research notes with their paths.
    pub research: Vec<(String, ResearchDoc)>,
    /// Personas with their paths.
    pub personas: Vec<(String, PersonaFile)>,
    /// Journeys with their paths.
    pub journeys: Vec<(String, JourneyFile)>,
    /// Files that were unreadable, invalid or duplicated an id.
    pub problems: Vec<ResearchProblem>,
}

impl ResearchSet {
    /// True when no research, persona or journey file exists (problems aside).
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.research.is_empty() && self.personas.is_empty() && self.journeys.is_empty()
    }
}

/// Files in `<root>/<dir>` ending in `suffix`, as sorted `(relative path, text)`; problems collect.
fn read_dir_files(
    root: &Path,
    dir: &str,
    suffix: &str,
    problems: &mut Vec<ResearchProblem>,
) -> Vec<(String, String)> {
    let Ok(entries) = std::fs::read_dir(root.join(dir)) else {
        tracing::debug!(dir, "no research directory");
        return Vec::new();
    };
    let mut names: Vec<String> = entries
        .filter_map(Result::ok)
        .filter_map(|e| e.file_name().into_string().ok())
        .filter(|n| n.ends_with(suffix))
        .collect();
    names.sort();
    let mut out = Vec::new();
    for name in names {
        let rel = format!("{dir}/{name}");
        match std::fs::read_to_string(root.join(&rel)) {
            Ok(text) => out.push((rel, text)),
            Err(err) => {
                tracing::warn!(path = %rel, %err, "research file unreadable");
                problems.push(ResearchProblem {
                    path: rel,
                    line: None,
                    message: format!("unreadable: {err}"),
                });
            }
        }
    }
    out
}

/// Parse each file with `parse`, keep the valid ones and refuse a repeated id.
fn load_kind<T>(
    files: Vec<(String, String)>,
    parse: fn(&str) -> Result<T, ResearchError>,
    id_of: fn(&T) -> &str,
    kind: &str,
    problems: &mut Vec<ResearchProblem>,
) -> Vec<(String, T)> {
    let mut seen = BTreeSet::new();
    let mut out = Vec::new();
    for (path, text) in files {
        match parse(&text) {
            Ok(item) => {
                if seen.insert(id_of(&item).to_owned()) {
                    out.push((path, item));
                } else {
                    problems.push(ResearchProblem {
                        message: format!("duplicate {kind} id `{}`", id_of(&item)),
                        path,
                        line: None,
                    });
                }
            }
            Err(e) => {
                tracing::warn!(%path, err = %e, "research file invalid");
                problems.push(ResearchProblem {
                    path,
                    line: e.line,
                    message: e.message,
                });
            }
        }
    }
    out
}

/// Read every research note, persona and journey under `root`. A missing directory contributes
/// nothing; a bad file becomes a [`ResearchProblem`] and a repeated persona id is refused.
#[must_use]
pub fn load_research(root: &Path) -> ResearchSet {
    let mut problems = Vec::new();
    let notes = read_dir_files(root, RESEARCH_DIR, ".md", &mut problems);
    let personas = read_dir_files(root, PERSONAS_DIR, ".toml", &mut problems);
    let journeys = read_dir_files(root, JOURNEYS_DIR, ".toml", &mut problems);
    let set = ResearchSet {
        research: load_kind(notes, parse_research, |d| &d.id, "research", &mut problems),
        personas: load_kind(
            personas,
            parse_toml::<PersonaFile>,
            |p| &p.id,
            "persona",
            &mut problems,
        ),
        journeys: load_kind(
            journeys,
            parse_toml::<JourneyFile>,
            |j| &j.id,
            "journey",
            &mut problems,
        ),
        problems,
    };
    tracing::debug!(
        research = set.research.len(),
        personas = set.personas.len(),
        journeys = set.journeys.len(),
        problems = set.problems.len(),
        "loaded research"
    );
    set
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-spec/src/research.rs::parse_research
    #[test]
    fn front_matter_parses() {
        let ok =
            parse_research("---\nid: r1\ndate: 2026-01-02\ntags:\n  - a\n---\nbody\n").expect("ok");
        assert_eq!(ok.id, "r1");
    }

    // frob:tests crates/crunk-spec/src/research.rs::parse_research
    #[test]
    fn front_matter_errors_are_located() {
        let bad = parse_research("---\nid: r1\nnonsense\n---\n").expect_err("bad");
        assert_eq!(bad.line, Some(3));
        assert!(parse_research("no front matter").is_err());
        assert!(parse_research("---\nid: r1\ndate: nope\n---\n").is_err());
        assert!(parse_research("---\nid: r1\ndate: 2026-01-02\n").is_err());
    }

    // frob:tests crates/crunk-spec/src/research.rs::parse_toml
    #[test]
    fn parse_toml_reads_a_persona() {
        let p: PersonaFile = parse_toml("id = \"p1\"\n").expect("persona");
        assert_eq!(p.id, "p1");
    }

    // frob:tests crates/crunk-spec/src/research.rs::parse_toml
    #[test]
    fn parse_toml_rejects_a_malformed_persona() {
        assert!(parse_toml::<PersonaFile>("name = 3").is_err());
    }

    // frob:tests crates/crunk-spec/src/research.rs::Date
    #[test]
    fn dates_subtract_to_days() {
        let a = Date::parse("2026-03-01").expect("a");
        let b = Date::parse("2026-02-01").expect("b");
        assert_eq!(a.days() - b.days(), 28);
        assert_eq!(Date::parse("1970-01-01").expect("epoch").days(), 0);
    }

    // frob:tests crates/crunk-spec/src/research.rs::load_research
    #[test]
    fn load_refuses_duplicate_personas_and_tolerates_empty() {
        let dir = tempfile::tempdir().expect("tmp");
        assert!(load_research(dir.path()).is_empty());
        let p = dir.path().join(PERSONAS_DIR);
        std::fs::create_dir_all(&p).expect("mk");
        std::fs::write(p.join("a.toml"), "id = \"x\"\n").expect("w");
        std::fs::write(p.join("b.toml"), "id = \"x\"\n").expect("w");
        let set = load_research(dir.path());
        assert_eq!(set.personas.len(), 1);
        assert_eq!(set.problems.len(), 1);
    }
}

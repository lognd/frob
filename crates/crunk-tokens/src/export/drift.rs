//! Drift: the generated files on disk against what the spec renders now.
//!
//! [`render_managed`] and [`compare`] are pure; `TOKENS001` builds its findings from
//! [`check`]'s [`DriftReport`] (or from [`compare`] over text it read itself, for example from a
//! git blob). `tokens.css` compares byte for byte; the two JSON files compare after parsing, so a
//! formatter re-wrapping them never counts as drift.

// frob:ticket 01M43ARZH9F9MCPJCKXM635E0X

use std::path::{Path, PathBuf};

use crunk_spec::DesignSpec;
use serde::Serialize;

use super::css::BANNER;
use super::write::{ExportError, orphan_warnings};
use super::{Comparison, Target};
use crate::model::{ThemeCollision, TokenError, TokenSet};

/// The state of one generated file; ordered by severity so the worst of a set is its maximum.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Status {
    /// The file matches the render.
    Clean,
    /// The file does not exist.
    Missing,
    /// The file exists and differs.
    Drifted,
}

impl Status {
    /// The lowercase word `crunk tokens --check` prints (`clean`, `missing`, `drifted`).
    pub fn word(self) -> &'static str {
        match self {
            Self::Clean => "clean",
            Self::Missing => "missing",
            Self::Drifted => "drifted",
        }
    }
}

/// The expected text of one generated file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Rendered {
    /// Which export this is.
    pub target: Target,
    /// Where the file lives.
    pub path: PathBuf,
    /// The text a clean file holds.
    pub content: String,
    /// How a file on disk is compared with `content`.
    pub comparison: Comparison,
}

/// One managed file's drift result.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct FileDrift {
    /// Which export this is.
    pub target: Target,
    /// Where the file lives.
    pub path: PathBuf,
    /// Clean, missing or drifted.
    pub status: Status,
    /// True when the file differs only at the GENERATED banner line (a cosmetic rewrite).
    pub banner_only: bool,
}

/// Everything one drift check found.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct DriftReport {
    /// One row per configured file, in [`Target::ALL`] order.
    pub files: Vec<FileDrift>,
    /// Tailwind default theme keys the un-namespaced export would redefine (empty when the
    /// Tailwind file is unset or `namespace_keys` is on).
    pub collisions: Vec<ThemeCollision>,
    /// Non-fatal notes (a possibly orphaned copy of a generated file).
    pub warnings: Vec<String>,
}

impl DriftReport {
    /// The worst status across every file (`Clean` when there are none).
    pub fn worst(&self) -> Status {
        self.files
            .iter()
            .map(|f| f.status)
            .max()
            .unwrap_or(Status::Clean)
    }

    /// The files that are not clean.
    pub fn dirty(&self) -> impl Iterator<Item = &FileDrift> {
        self.files.iter().filter(|f| f.status != Status::Clean)
    }
}

/// The expected text of every file `spec` configures, in [`Target::ALL`] order (the CSS file is
/// always present). Pure: nothing is read from or written to disk.
///
/// # Errors
///
/// [`TokenError`] when the spec produces a colliding token name.
pub fn render_managed(spec: &DesignSpec) -> Result<Vec<Rendered>, TokenError> {
    let tokens = TokenSet::from_spec(spec)?;
    Ok(render_managed_with(spec, &tokens))
}

pub(super) fn render_managed_with(spec: &DesignSpec, tokens: &TokenSet) -> Vec<Rendered> {
    Target::ALL
        .into_iter()
        .filter_map(|target| {
            let exporter = target.exporter();
            let path = exporter.path(spec)?;
            Some(Rendered {
                target,
                path,
                content: exporter.render(spec, tokens),
                comparison: exporter.comparison(),
            })
        })
        .collect()
}

/// Python-style universal newlines: `\r\n` and lone `\r` read as `\n`, so a checkout that
/// converts line endings (autocrlf on Windows) is not drift.
fn universal_newlines(text: &str) -> String {
    text.replace("\r\n", "\n").replace('\r', "\n")
}

/// Compare one expected file with the text on disk (`None` when the file does not exist).
///
/// Line endings are normalized first, so CRLF on disk compares equal to the LF render.
pub fn compare(expected: &Rendered, on_disk: Option<&str>) -> FileDrift {
    let normalized = on_disk.map(universal_newlines);
    let (status, banner_only) = match normalized.as_deref() {
        None => (Status::Missing, false),
        Some(disk) => match expected.comparison {
            Comparison::Bytes if disk == expected.content => (Status::Clean, false),
            Comparison::Bytes => (Status::Drifted, banner_only_drift(disk, &expected.content)),
            Comparison::Json if json_equal(disk, &expected.content) => (Status::Clean, false),
            Comparison::Json => (Status::Drifted, false),
        },
    };
    tracing::debug!(
        target = %expected.target,
        path = %expected.path.display(),
        status = status.word(),
        banner_only,
        "tokens drift compared"
    );
    FileDrift {
        target: expected.target,
        path: expected.path.clone(),
        status,
        banner_only,
    }
}

/// Whether two JSON texts parse to the same value; unparseable text is never equal.
fn json_equal(disk: &str, expected: &str) -> bool {
    let parse_json = |text: &str| serde_json::from_str::<serde_json::Value>(text).ok();
    if let (Some(a), Some(b)) = (parse_json(disk), parse_json(expected)) {
        return a == b;
    }
    tracing::debug!("tokens drift: unparseable json counts as drifted");
    false
}

/// True iff `disk` and `expected` differ only at the line that is the GENERATED banner: found by
/// line identity in `expected`, every other line compared exactly.
fn banner_only_drift(disk: &str, expected: &str) -> bool {
    let expected_lines: Vec<&str> = expected.split('\n').collect();
    let Some(banner_index) = expected_lines.iter().position(|l| *l == BANNER) else {
        return false;
    };
    let disk_lines: Vec<&str> = disk.split('\n').collect();
    if disk_lines.len() != expected_lines.len() {
        return false;
    }
    disk_lines
        .iter()
        .zip(&expected_lines)
        .enumerate()
        .all(|(i, (d, e))| i == banner_index || d == e)
        && disk_lines[banner_index] != expected_lines[banner_index]
}

/// Read `path` as UTF-8; `Ok(None)` when it does not exist.
fn read_optional(path: &Path) -> Result<Option<String>, ExportError> {
    match std::fs::read_to_string(path) {
        Ok(text) => Ok(Some(text)),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(source) => {
            tracing::warn!(path = %path.display(), error = %source, "tokens check cannot read file");
            Err(ExportError::Read {
                path: path.to_owned(),
                source,
            })
        }
    }
}

/// Compare every configured generated file on disk with its render.
///
/// # Errors
///
/// [`ExportError::Token`] for a colliding token name, [`ExportError::Read`] when a file exists
/// but cannot be read. A missing file is a [`Status::Missing`] row, not an error.
pub fn check(spec: &DesignSpec) -> Result<DriftReport, ExportError> {
    let tokens = TokenSet::from_spec(spec)?;
    let rendered = render_managed_with(spec, &tokens);
    let mut files = Vec::with_capacity(rendered.len());
    for expected in &rendered {
        let on_disk = read_optional(&expected.path)?;
        files.push(compare(expected, on_disk.as_deref()));
    }
    let report = DriftReport {
        files,
        collisions: collisions(spec, &tokens),
        warnings: orphan_warnings(spec, &rendered),
    };
    tracing::info!(
        worst = report.worst().word(),
        files = report.files.len(),
        "tokens checked"
    );
    Ok(report)
}

/// The default-theme collisions that matter: only when the Tailwind file is configured.
pub(super) fn collisions(spec: &DesignSpec, tokens: &TokenSet) -> Vec<ThemeCollision> {
    if spec.tailwind_tokens_path().is_none() {
        return Vec::new();
    }
    let found = tokens.default_theme_collisions(spec.tailwind.namespace_keys);
    for c in &found {
        tracing::warn!(
            token = %c.token,
            section = c.section.name(),
            key = %c.key,
            "theme key collides with a Tailwind default; set namespace_keys = true or rename the step"
        );
    }
    found
}

#[cfg(test)]
mod tests {
    use super::*;

    fn css(content: &str) -> Rendered {
        Rendered {
            target: Target::Css,
            path: PathBuf::from("tokens.css"),
            content: content.to_owned(),
            comparison: Comparison::Bytes,
        }
    }

    // frob:tests crates/crunk-tokens/src/export/drift.rs::compare
    #[test]
    fn crlf_on_disk_is_not_drift() {
        let want = css(&format!("{BANNER}\n:root {{\n}}\n"));
        let crlf = want.content.replace('\n', "\r\n");
        assert_eq!(compare(&want, Some(&crlf)).status, Status::Clean);
    }

    // frob:tests crates/crunk-tokens/src/export/drift.rs::compare
    #[test]
    fn banner_only_difference_is_flagged_and_other_edits_are_not() {
        let want = css(&format!("{BANNER}\n:root {{\n  --a: 1;\n}}\n"));
        let rewritten = "/* GENERATED by crunk 9 */\n:root {\n  --a: 1;\n}\n";
        let d = compare(&want, Some(rewritten));
        assert_eq!((d.status, d.banner_only), (Status::Drifted, true));
        let edited = format!("{BANNER}\n:root {{\n  --a: 2;\n}}\n");
        let d = compare(&want, Some(&edited));
        assert_eq!((d.status, d.banner_only), (Status::Drifted, false));
        assert_eq!(compare(&want, None).status, Status::Missing);
        assert_eq!(compare(&want, Some(&want.content)).status, Status::Clean);
    }
}

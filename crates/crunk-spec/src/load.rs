//! Loading `crunk.toml`: parse, locate, deserialize, validate, assemble the [`DesignSpec`].

// frob:ticket 01M43ARX764095Q4VWABWXXV5H

use std::path::{Path, PathBuf};

use toml_edit::{Document, Item, TableLike};

use crate::error::{Location, SpecError};
use crate::model::DesignSpec;
use crate::table::RawSpec;
use crate::validate::{self, Problem, Seg, nearest};

/// The top-level tables crunk itself owns.
pub const OWN_TABLES: &[&str] = &[
    "project",
    "palette",
    "scales",
    "typography",
    "layers",
    "org",
    "lint",
    "tokens",
    "jsx",
    "tailwind",
    "breakpoints",
    "platform",
    "screen",
    "session",
    "mock_set",
];

/// The sections a valid file must declare.
const REQUIRED: &[&str] = &["project", "palette", "scales", "typography", "org"];

/// Read `<root>/crunk.toml` and validate it into a [`DesignSpec`].
///
/// # Errors
///
/// [`SpecError::Missing`] when the file is absent or unreadable, [`SpecError::Malformed`] for
/// invalid TOML and [`SpecError::Invalid`] for a schema violation, with a line and column.
pub fn load_spec(root: &Path) -> Result<DesignSpec, SpecError> {
    load_spec_file(&root.join("crunk.toml"), root)
}

/// Read an arbitrary `crunk.toml` at `path`, resolving relative paths against `root`.
///
/// # Errors
///
/// See [`load_spec`].
pub fn load_spec_file(path: &Path, root: &Path) -> Result<DesignSpec, SpecError> {
    let text = match std::fs::read_to_string(path) {
        Ok(text) => text,
        Err(e) => {
            tracing::info!(path = %path.display(), error = %e, "spec load reject: unreadable");
            let reason = (e.kind() != std::io::ErrorKind::NotFound).then(|| e.to_string());
            return Err(SpecError::Missing {
                path: path.to_owned(),
                reason,
            });
        }
    };
    parse_spec(&text, path, root)
}

/// Validate `text` (the content of the file at `source`) into a [`DesignSpec`] rooted at `root`.
///
/// # Errors
///
/// [`SpecError::Malformed`] for invalid TOML and [`SpecError::Invalid`] for a schema violation.
pub fn parse_spec(text: &str, source: &Path, root: &Path) -> Result<DesignSpec, SpecError> {
    let ctx = Ctx::new(text, source)?;
    let spec = ctx.build(root);
    match &spec {
        Ok(_) => tracing::debug!(path = %source.display(), "spec load ok"),
        Err(e) => tracing::info!(path = %source.display(), error = %e, "spec load reject"),
    }
    spec
}

/// Names a top-level key may take: crunk's own tables and every table a linked crate registered.
fn allowed_top_level() -> Vec<String> {
    let mut names: Vec<String> = OWN_TABLES.iter().map(|s| (*s).to_owned()).collect();
    for table in gob_config::all_tables() {
        let head = table.table.split('.').next().unwrap_or_default().to_owned();
        if !names.contains(&head) {
            names.push(head);
        }
    }
    names
}

struct Ctx<'a> {
    text: &'a str,
    source: PathBuf,
    doc: Document<String>,
}

impl<'a> Ctx<'a> {
    fn new(text: &'a str, source: &Path) -> Result<Self, SpecError> {
        match Document::parse(text.to_owned()) {
            Ok(doc) => Ok(Self {
                text,
                source: source.to_owned(),
                doc,
            }),
            Err(e) => Err(SpecError::Malformed {
                path: source.to_owned(),
                at: e.span().map(|s| location(text, s.start)),
                message: e.message().to_owned(),
            }),
        }
    }

    fn at_offset(&self, offset: usize) -> Location {
        location(self.text, offset)
    }

    fn invalid(&self, at: Option<Location>, detail: String) -> SpecError {
        SpecError::Invalid {
            path: self.source.clone(),
            at,
            detail,
            key: None,
            suggestion: None,
        }
    }

    /// Turn a validation [`Problem`] into a located error.
    fn problem(&self, p: Problem) -> SpecError {
        let at = self.locate(&p.path).map(|offset| self.at_offset(offset));
        SpecError::Invalid {
            path: self.source.clone(),
            at,
            detail: p.detail,
            key: p.key,
            suggestion: p.suggestion,
        }
    }

    /// Byte offset of the key (or table) at `path`.
    fn locate(&self, path: &[Seg]) -> Option<usize> {
        let mut item: &Item = self.doc.as_item();
        for (i, seg) in path.iter().enumerate() {
            let last = i + 1 == path.len();
            match seg {
                Seg::Key(k) => {
                    let table = item.as_table_like()?;
                    if last {
                        let (key, value) = table.get_key_value(k)?;
                        return key.span().or_else(|| value.span()).map(|s| s.start);
                    }
                    item = table.get(k)?;
                }
                Seg::Idx(n) => {
                    item = item.get(*n)?;
                    if last {
                        return item.span().map(|s| s.start);
                    }
                }
            }
        }
        item.span().map(|s| s.start)
    }

    /// Dotted path of the table that directly holds the key written at `offset`.
    fn section_at(&self, offset: usize) -> String {
        fn descend(table: &dyn TableLike, offset: usize, path: &mut Vec<String>) -> bool {
            for (key, child) in table.iter() {
                let key_hit = table
                    .get_key_value(key)
                    .and_then(|(k, _)| k.span())
                    .is_some_and(|s| s.contains(&offset));
                // A value that is itself the error (a table where an integer belongs) starts at
                // the offset: it is a problem of the table that holds it.
                let value_hit = child.span().is_some_and(|s| s.start == offset);
                if key_hit || value_hit {
                    return true;
                }
                let inners: Vec<&dyn TableLike> = match child {
                    Item::ArrayOfTables(aot) => aot.iter().map(|t| t as &dyn TableLike).collect(),
                    other => other.as_table_like().into_iter().collect(),
                };
                for inner in inners {
                    path.push(key.to_owned());
                    if descend(inner, offset, path) {
                        return true;
                    }
                    path.pop();
                }
            }
            false
        }
        let mut path = Vec::new();
        descend(self.doc.as_table(), offset, &mut path);
        path.join(".")
    }

    fn check_top_level(&self) -> Result<(), SpecError> {
        let allowed = allowed_top_level();
        for (name, _) in self.doc.as_table() {
            if allowed.iter().any(|a| a == name) {
                continue;
            }
            let at = self
                .locate(&[Seg::Key(name.to_owned())])
                .map(|o| self.at_offset(o));
            return Err(SpecError::Invalid {
                path: self.source.clone(),
                at,
                detail: format!("unknown top-level key `{name}`"),
                key: Some(name.to_owned()),
                suggestion: nearest(name, allowed.iter().map(String::as_str)),
            });
        }
        for name in REQUIRED {
            if !self.doc.as_table().contains_key(name) {
                return Err(self.invalid(None, format!("missing required section [{name}]")));
            }
        }
        Ok(())
    }

    /// Map a serde error from the typed pass to a located error, naming unknown keys.
    fn serde_error(&self, e: &toml_edit::de::Error) -> SpecError {
        let span = e.span().filter(|s| !(s.start == 0 && s.end == 0));
        let message = e.message().to_owned();
        let at = span.clone().map(|s| self.at_offset(s.start));
        let section = span.as_ref().map(|s| self.section_at(s.start));
        let in_section = |detail: String| match section.as_deref() {
            Some(sec) if !sec.is_empty() => format!("[{sec}]: {detail}"),
            _ => detail,
        };
        if let Some(rest) = message.strip_prefix("unknown field `") {
            let (unknown, tail) = rest.split_once('`').unwrap_or((rest, ""));
            let candidates: Vec<&str> = tail
                .split('`')
                .enumerate()
                .filter_map(|(i, s)| (i % 2 == 1).then_some(s))
                .collect();
            let suggestion = nearest(unknown, candidates.iter().copied());
            return SpecError::Invalid {
                path: self.source.clone(),
                at,
                detail: in_section(format!("unknown key `{unknown}`")),
                key: Some(unknown.to_owned()),
                suggestion,
            };
        }
        self.invalid(at, in_section(message))
    }

    fn build(&self, root: &Path) -> Result<DesignSpec, SpecError> {
        self.check_top_level()?;
        let raw: RawSpec = toml_edit::de::from_str(self.text).map_err(|e| self.serde_error(&e))?;
        Self::assemble(root, raw).map_err(|p| self.problem(p))
    }

    #[allow(
        clippy::too_many_lines,
        reason = "one linear pass over the sections, as in the format"
    )]
    fn assemble(root: &Path, raw: RawSpec) -> Result<DesignSpec, Problem> {
        let project = raw
            .project
            .unwrap_or_else(|| unreachable!("required sections are checked first"));
        let palette_raw = raw
            .palette
            .unwrap_or_else(|| unreachable!("required sections are checked first"));
        let scales = raw
            .scales
            .unwrap_or_else(|| unreachable!("required sections are checked first"));
        let typography = raw
            .typography
            .unwrap_or_else(|| unreachable!("required sections are checked first"));
        let org = raw
            .org
            .unwrap_or_else(|| unreachable!("required sections are checked first"));

        let (palette, roles_raw) = validate::palette(&palette_raw)?;
        let roles = validate::roles(&roles_raw, &palette)?;
        validate::scales(&scales)?;
        validate::typography(&typography)?;
        validate::org(&org)?;
        let lint = validate::lint(raw.lint.as_ref())?;
        let tokens = validate::tokens(&raw.tokens.unwrap_or_default())?;
        let tailwind = raw.tailwind.unwrap_or_default();
        let breakpoints =
            validate::breakpoints(raw.breakpoints.as_ref(), !tailwind.config.is_empty())?;
        let platforms = validate::platforms(&raw.platform.unwrap_or_default())?;
        let sessions = validate::rosters("session", &raw.session.unwrap_or_default())?;
        let mock_sets = validate::rosters("mock_set", &raw.mock_set.unwrap_or_default())?;
        let screens = validate::screens(
            &raw.screen.unwrap_or_default(),
            &validate::Platforms::new(&platforms),
            &sessions,
            &mock_sets,
        )?;
        Ok(DesignSpec {
            root: root.to_owned(),
            project,
            palette,
            roles,
            scales,
            typography,
            layers: raw.layers.unwrap_or_default(),
            org,
            lint,
            tokens,
            jsx: raw.jsx.unwrap_or_default(),
            tailwind,
            breakpoints,
            platforms,
            screens,
            sessions,
            mock_sets,
        })
    }
}

/// 1-based line and character column of byte `offset` in `text`.
fn location(text: &str, offset: usize) -> Location {
    let offset = offset.min(text.len());
    let before = &text[..offset];
    let line = before.matches('\n').count() + 1;
    let line_start = before.rfind('\n').map_or(0, |i| i + 1);
    Location {
        line,
        column: before[line_start..].chars().count() + 1,
    }
}

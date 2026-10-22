//! `rename ID NEW`: rename a design token and rewrite every reference to it.
//!
//! The definition in `crunk.toml` (a `[palette]`, `[palette.modes.*]` or `[layers]` key, plus the
//! names in `[palette.roles]`), the stylesheets under `css_root`, the `[jsx] globs` sources and the
//! `design/**/*.toml` spec files are rewritten together, and the generated token exports are
//! regenerated so `crunk check` and `crunk tokens --check` stay clean. All files are computed in
//! memory first and written all-or-nothing; `--dry-run` writes nothing.

// frob:ticket 01M4CXRB2DX0B0BW7YJPAN1YXT

use std::path::Path;

use crunk_spec::DesignSpec;
use crunk_spec::naming::sanitize_ident;
use crunk_tokens::{Token, TokenKind, TokenSet};
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};

use crate::PRODUCT;
use crate::rewrite::{
    Change, Lang, RenameMatcher, RewriteData, commit_atomic, generated_changes, header_of,
    reference_changes, scan, source_files,
};

/// Rename a token (`--color-ink`) and rewrite every reference in CSS, TSX and spec files.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "rename",
    product = "crunk",
    idempotent = false,
    dry_run,
    exits(ok, refused, usage, internal)
)]
pub struct Rename {
    id: String,
    new: String,
}

/// `Rename` arguments.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct RenameArgs {
    #[arg(
        value_name = "ID",
        allow_hyphen_values = true,
        help = "The token to rename, e.g. --color-ink"
    )]
    id: String,
    #[arg(
        value_name = "NEW",
        allow_hyphen_values = true,
        help = "Its new name, e.g. --color-text"
    )]
    new: String,
}

/// Why a rename or extraction was refused, with a stable code.
#[derive(Debug, thiserror::Error)]
pub enum PlanError {
    /// The new name is not a valid custom property name.
    #[error("{0:?} is not a valid token name (expected --name with letters, digits, - and _)")]
    InvalidName(String),
    /// The token to rename does not exist.
    #[error("no token named {0}")]
    Missing(String),
    /// Old and new name are the same.
    #[error("{0} already has that name")]
    Same(String),
    /// The new name belongs to an existing token.
    #[error("{0} is already a token")]
    Collision(String),
    /// The token is not defined by a renamable key.
    #[error("{0} cannot be renamed: {1}")]
    NotRenamable(String, String),
    /// The definition could not be located and rewritten in `crunk.toml`.
    #[error("cannot locate the definition of {0} in crunk.toml: {1}")]
    Definition(String, String),
    /// The project spec could not be read.
    #[error("{0}")]
    Spec(String),
}

impl PlanError {
    /// The stable refusal code.
    #[must_use]
    pub fn code(&self) -> &'static str {
        match self {
            Self::InvalidName(_) => "E-RENAME-NAME",
            Self::Missing(_) => "E-RENAME-MISSING",
            Self::Same(_) => "E-RENAME-SAME",
            Self::Collision(_) => "E-RENAME-EXISTS",
            Self::NotRenamable(..) => "E-RENAME-KIND",
            Self::Definition(..) => "E-RENAME-DEF",
            Self::Spec(_) => "E-RENAME-SPEC",
        }
    }
}

impl From<PlanError> for CliError {
    fn from(err: PlanError) -> Self {
        tracing::info!(code = err.code(), error = %err, "rename refused");
        Refusal::new(err.code(), RefusalClass::GuardNeedsAction, err.to_string())
            .with_remedy("fix the request as described, then rerun")
            .into()
    }
}

impl Command for Rename {
    type Data = RewriteData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<RenameArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<RenameArgs>(m)?;
        Ok(Self {
            id: a.id,
            new: a.new,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<RewriteData> {
        let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
        let changes = plan(&root, &self.id, &self.new)?;
        let data = RewriteData::new(&root, &self.id, &self.new, ctx.dry_run, &changes);
        if ctx.dry_run {
            tracing::info!(files = changes.len(), "rename: dry run, nothing written");
        } else {
            commit_atomic(&changes).map_err(|e| {
                Refusal::new(
                    "E-RENAME-WRITE",
                    RefusalClass::GuardNeedsAction,
                    e.to_string(),
                )
                .with_remedy("fix the file permissions; every earlier write was rolled back")
            })?;
            tracing::info!(files = changes.len(), old = %self.id, new = %self.new, "rename: written");
        }
        let lines = data.lines();
        Ok(Payload::new(data).with_rendered(lines))
    }
}

/// True for `--` followed by a letter or underscore, then identifier characters.
fn valid_name(name: &str) -> bool {
    let Some(rest) = name.strip_prefix("--") else {
        return false;
    };
    let mut chars = rest.chars();
    chars
        .next()
        .is_some_and(|c| c.is_ascii_alphabetic() || c == '_')
        && chars.all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
}

/// Load the spec and the tokens it defines.
pub(crate) fn load(root: &Path) -> Result<(DesignSpec, TokenSet), PlanError> {
    let spec = crunk_spec::load_spec(root).map_err(|e| PlanError::Spec(e.to_string()))?;
    let tokens = TokenSet::from_spec(&spec).map_err(|e| PlanError::Spec(e.to_string()))?;
    Ok((spec, tokens))
}

/// Compute every file change for renaming `old` to `new`, without writing anything.
///
/// # Errors
///
/// A [`PlanError`] for every refusal: bad or equal names, a missing token, a collision, a derived
/// token, or a definition that cannot be located.
pub fn plan(root: &Path, old: &str, new: &str) -> Result<Vec<Change>, PlanError> {
    if !valid_name(new) {
        return Err(PlanError::InvalidName(new.to_owned()));
    }
    let (spec, tokens) = load(root)?;
    let Some(token) = tokens.get(old) else {
        return Err(PlanError::Missing(old.to_owned()));
    };
    if old == new {
        return Err(PlanError::Same(old.to_owned()));
    }
    if tokens.get(new).is_some() {
        return Err(PlanError::Collision(new.to_owned()));
    }
    let new_key = new_key(token, new)?;
    let toml_path = root.join("crunk.toml");
    let toml_text = std::fs::read_to_string(&toml_path)
        .map_err(|e| PlanError::Spec(format!("cannot read crunk.toml: {e}")))?;
    let (edited, defs) = rename_definition(&toml_text, token.kind, &token.key, &new_key);
    let new_spec = crunk_spec::parse_spec(&edited, &toml_path, root)
        .map_err(|e| PlanError::Definition(old.to_owned(), e.to_string()))?;
    let new_tokens = TokenSet::from_spec(&new_spec)
        .map_err(|e| PlanError::Definition(old.to_owned(), e.to_string()))?;
    if defs == 0 || new_tokens.get(new).is_none() || new_tokens.get(old).is_some() {
        return Err(PlanError::Definition(
            old.to_owned(),
            "no [palette] or [layers] key renames it".to_owned(),
        ));
    }
    let pairs = name_pairs(&tokens, &new_tokens, token, &new_key);
    tracing::debug!(?pairs, "rename: name pairs");

    let generated = crunk_tokens::export::render_managed(&new_spec)
        .map_err(|e| PlanError::Spec(e.to_string()))?;
    let files = source_files(root, &spec, &generated);
    let mut changes = reference_changes(&files, |text, lang| rewrite_refs(text, lang, &pairs));
    let (after, refs) = rewrite_refs(&edited, Lang::Toml, &pairs);
    changes.insert(
        0,
        Change {
            path: toml_path,
            before: Some(toml_text),
            after,
            kind: "definition",
            replacements: defs + refs,
        },
    );
    changes.extend(generated_changes(&generated));
    Ok(changes)
}

/// Rewrite every reference for `pairs` in `text`.
fn rewrite_refs(text: &str, lang: Lang, pairs: &[(String, String)]) -> (String, usize) {
    let m = RenameMatcher::new(pairs.to_vec(), lang);
    scan(text, lang, |t, k, s| m.at(t, k, s))
}

/// The spec key the new name implies: the name minus the family prefix of the old token.
fn new_key(token: &Token, new: &str) -> Result<String, PlanError> {
    let name = &token.name;
    if !matches!(token.kind, TokenKind::Color | TokenKind::Layer) {
        return Err(PlanError::NotRenamable(
            name.clone(),
            "only [palette] colors and [layers] entries are renamable".to_owned(),
        ));
    }
    let ident = sanitize_ident(&token.key);
    let Some(prefix) = name.strip_suffix(ident.as_str()) else {
        return Err(PlanError::NotRenamable(
            name.clone(),
            "its name does not derive from its key".to_owned(),
        ));
    };
    match new.strip_prefix(prefix) {
        Some(key) if !key.is_empty() && sanitize_ident(key) == key => Ok(key.to_owned()),
        _ => Err(PlanError::NotRenamable(
            name.clone(),
            format!("the new name must start with {prefix:?} and end in a lowercase identifier"),
        )),
    }
}

/// The (old, new) names to rewrite: the token itself plus its companions (the `-rgb` channels).
fn name_pairs(
    old: &TokenSet,
    new: &TokenSet,
    token: &Token,
    new_key: &str,
) -> Vec<(String, String)> {
    old.iter()
        .filter(|t| t.key == token.key && family(t.kind) == family(token.kind))
        .filter_map(|t| {
            let renamed = new.iter().find(|n| n.key == new_key && n.kind == t.kind)?;
            Some((t.name.clone(), renamed.name.clone()))
        })
        .collect()
}

/// Colour tokens and their channel companions form one family.
fn family(kind: TokenKind) -> u8 {
    match kind {
        TokenKind::Color | TokenKind::ColorChannels => 0,
        other => other as u8 + 1,
    }
}

/// Rename key `old_key` to `new_key` in the definition tables of `text`; returns the new text and
/// the number of edits (keys and role references).
fn rename_definition(text: &str, kind: TokenKind, old_key: &str, new_key: &str) -> (String, usize) {
    let mut section = String::new();
    let mut out = String::with_capacity(text.len());
    let mut count = 0;
    for line in text.split_inclusive('\n') {
        if let Some(h) = header_of(line) {
            h.clone_into(&mut section);
            out.push_str(line);
            continue;
        }
        let is_key_table = match kind {
            TokenKind::Layer => section == "layers",
            _ => section == "palette" || section.starts_with("palette.modes."),
        };
        if is_key_table && let Some(edited) = rename_key_line(line, old_key, new_key) {
            out.push_str(&edited);
            count += 1;
        } else if kind == TokenKind::Color && section.starts_with("palette.roles") {
            let (edited, n) = rename_role_strings(line, old_key, new_key);
            out.push_str(&edited);
            count += n;
        } else {
            out.push_str(line);
        }
    }
    (out, count)
}

/// Rename the key of a `key = value` line when it is exactly `old_key`.
fn rename_key_line(line: &str, old_key: &str, new_key: &str) -> Option<String> {
    let indent = line.len() - line.trim_start().len();
    let body = &line[indent..];
    let (key_len, quoted) = match body.chars().next()? {
        q @ ('"' | '\'') => (body[1..].find(q)? + 2, true),
        _ => (body.find(|c: char| c.is_whitespace() || c == '=')?, false),
    };
    let key = if quoted {
        &body[1..key_len - 1]
    } else {
        &body[..key_len]
    };
    if key != old_key || !body[key_len..].trim_start().starts_with('=') {
        return None;
    }
    let bare = new_key
        .chars()
        .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-');
    let written = if bare {
        new_key.to_owned()
    } else {
        format!("\"{new_key}\"")
    };
    Some(format!("{}{written}{}", &line[..indent], &body[key_len..]))
}

/// Rewrite quoted strings equal to `old_key` on the right-hand side of a role line.
fn rename_role_strings(line: &str, old_key: &str, new_key: &str) -> (String, usize) {
    let Some(eq) = line.find('=') else {
        return (line.to_owned(), 0);
    };
    let (head, tail) = line.split_at(eq + 1);
    let mut count = 0;
    let rewritten = [("\"", '"'), ("'", '\'')]
        .iter()
        .fold(tail.to_owned(), |acc, (q, _)| {
            let needle = format!("{q}{old_key}{q}");
            count += acc.matches(&needle).count();
            acc.replace(&needle, &format!("{q}{new_key}{q}"))
        });
    (format!("{head}{rewritten}"), count)
}

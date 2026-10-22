//! `rename ID NEW`: rename a design token and rewrite every reference to it.
//!
//! The definition in `crunk.toml` (a `[palette]`, `[palette.modes.*]`, `[layers]` or
//! `[typography.stacks]` key, plus the names in `[palette.roles]`) or in a `design/tokens/*.toml`
//! file (a custom token, with its `{group.name}` aliases), the stylesheets under `css_root`, the
//! `[jsx] globs` sources, the `design/**/*.toml` spec files and the `design/**/*.html` scenes are
//! rewritten together, and the generated token exports are regenerated so `crunk check` and
//! `crunk tokens --check` stay clean. All files are computed in memory first and written
//! all-or-nothing; `--dry-run` writes nothing. Names that follow a value (scale steps, the `base`
//! font stack, the `-rgb` channels) are refused with `E-RENAME-DERIVED`.

// frob:ticket 01M4CXRB2DX0B0BW7YJPAN1YXT
// frob:ticket 01M5H3RXWHYH6MRJX6B2M35H0F

use std::ops::Range;
use std::path::{Path, PathBuf};

use crunk_rules::token_files::{TokenFacts, TokenFile};
use crunk_spec::DesignSpec;
use crunk_spec::naming::sanitize_ident;
use crunk_tokens::dialect;
use crunk_tokens::{Token, TokenKind, TokenSet};
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use toml_edit::{Document, Item, TableLike, Value};

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
    /// The token's name follows a value or another token, so it has no key of its own to change.
    #[error("{0} cannot be renamed: {1}")]
    Derived(String, String),
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
            Self::Derived(..) => "E-RENAME-DERIVED",
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

/// The renamed definition: the edited file and the names to rewrite everywhere else.
struct Definition {
    path: PathBuf,
    before: String,
    after: String,
    edits: usize,
    pairs: Vec<(String, String)>,
    /// The spec after the edit, when the definition lives in `crunk.toml`.
    spec: Option<DesignSpec>,
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
    let facts = TokenFacts::load(&spec);
    let owners: Vec<&TokenFile> = facts
        .ok_sets()
        .filter(|(_, set)| set.get(old).is_some())
        .map(|(file, _)| file)
        .collect();
    let token = tokens.get(old);
    if token.is_none() && owners.is_empty() {
        return Err(PlanError::Missing(old.to_owned()));
    }
    if old == new {
        return Err(PlanError::Same(old.to_owned()));
    }
    if tokens.get(new).is_some() || facts.ok_sets().any(|(_, set)| set.get(new).is_some()) {
        return Err(PlanError::Collision(new.to_owned()));
    }
    let def = match (token, owners.as_slice()) {
        (Some(token), _) => spec_definition(root, &tokens, token, new)?,
        (None, [file]) => custom_definition(root, file, old, new)?,
        (None, files) => {
            return Err(PlanError::Definition(
                old.to_owned(),
                format!(
                    "it is defined in {} token files; rename is ambiguous",
                    files.len()
                ),
            ));
        }
    };
    let pairs = &def.pairs;
    tracing::debug!(?pairs, "rename: name pairs");

    let generated = crunk_tokens::export::render_managed(def.spec.as_ref().unwrap_or(&spec))
        .map_err(|e| PlanError::Spec(e.to_string()))?;
    let files = source_files(root, &spec, &generated);
    let mut changes = reference_changes(&files, |text, lang| rewrite_refs(text, lang, pairs));
    changes.retain(|c| c.path != def.path);
    let scenes = html_files(root, &files);
    changes.extend(reference_changes(&scenes, |text, _| {
        rewrite_html(text, pairs)
    }));
    let (after, refs) = rewrite_refs(&def.after, Lang::Toml, pairs);
    changes.insert(
        0,
        Change {
            path: def.path,
            before: Some(def.before),
            after,
            kind: "definition",
            replacements: def.edits + refs,
        },
    );
    changes.extend(generated_changes(&generated));
    Ok(changes)
}

/// Plan the edit of a `crunk.toml` token (palette color, layer or font stack).
fn spec_definition(
    root: &Path,
    tokens: &TokenSet,
    token: &Token,
    new: &str,
) -> Result<Definition, PlanError> {
    let old = token.name.as_str();
    let new_key = new_key(token, new)?;
    let toml_path = root.join("crunk.toml");
    let toml_text = std::fs::read_to_string(&toml_path)
        .map_err(|e| PlanError::Spec(format!("cannot read crunk.toml: {e}")))?;
    let (edited, edits) = rename_definition(&toml_text, token.kind, &token.key, &new_key);
    let new_spec = crunk_spec::parse_spec(&edited, &toml_path, root)
        .map_err(|e| PlanError::Definition(old.to_owned(), e.to_string()))?;
    let new_tokens = TokenSet::from_spec(&new_spec)
        .map_err(|e| PlanError::Definition(old.to_owned(), e.to_string()))?;
    if edits == 0 || new_tokens.get(new).is_none() || new_tokens.get(old).is_some() {
        return Err(PlanError::Definition(
            old.to_owned(),
            "no [palette], [layers] or [typography.stacks] key renames it".to_owned(),
        ));
    }
    Ok(Definition {
        path: toml_path,
        before: toml_text,
        after: edited,
        edits,
        pairs: name_pairs(tokens, &new_tokens, token, &new_key),
        spec: Some(new_spec),
    })
}

/// Plan the edit of a custom token in its `design/tokens` file: the key, and every alias to it.
fn custom_definition(
    root: &Path,
    file: &TokenFile,
    old: &str,
    new: &str,
) -> Result<Definition, PlanError> {
    let set = file
        .set
        .as_ref()
        .map_err(|e| PlanError::Spec(e.to_string()))?;
    let token = set
        .get(old)
        .ok_or_else(|| PlanError::Missing(old.to_owned()))?;
    let (group, leaf) = token
        .key
        .rsplit_once('.')
        .unwrap_or(("", token.key.as_str()));
    let prefix = if group.is_empty() {
        "--".to_owned()
    } else {
        format!("{}-", dialect::name_of_path(group))
    };
    let new_leaf = match new.strip_prefix(prefix.as_str()) {
        Some(l) if !l.is_empty() => l,
        _ => {
            return Err(PlanError::NotRenamable(
                old.to_owned(),
                format!("the new name must start with {prefix:?} to stay in its group"),
            ));
        }
    };
    let new_path = if group.is_empty() {
        new_leaf.to_owned()
    } else {
        format!("{group}.{new_leaf}")
    };
    tracing::debug!(file = %file.path, old_path = %token.key, %new_path, leaf, "rename: custom token");
    let (edited, edits) = edit_token_file(&file.text, &token.key, old, &new_path, new)
        .map_err(|why| PlanError::Definition(old.to_owned(), format!("{}: {why}", file.path)))?;
    let reparsed = dialect::parse(&edited, &file.path)
        .map_err(|e| PlanError::Definition(old.to_owned(), e.to_string()))?;
    if reparsed.get(new).is_none() || reparsed.get(old).is_some() || reparsed.len() != set.len() {
        return Err(PlanError::Definition(
            old.to_owned(),
            format!("editing {} did not rename exactly that token", file.path),
        ));
    }
    Ok(Definition {
        path: root.join(&file.path),
        before: file.text.clone(),
        after: edited,
        edits,
        pairs: vec![(old.to_owned(), new.to_owned())],
        spec: None,
    })
}

/// One byte-range replacement in a token file.
struct TextEdit {
    range: Range<usize>,
    text: String,
}

/// Rename the key at dotted `old_path` to `new_path` in `text` and retarget every alias to it;
/// returns the new text and the edit count. Offsets come from the parser, so layout, comments and
/// line endings are untouched.
fn edit_token_file(
    text: &str,
    old_path: &str,
    old: &str,
    new_path: &str,
    new: &str,
) -> Result<(String, usize), String> {
    let doc = Document::parse(text.to_owned()).map_err(|e| e.to_string())?;
    let mut edits = Vec::new();
    let segments: Vec<&str> = old_path.split('.').collect();
    let (last, parents) = segments.split_last().ok_or("empty token path")?;
    let mut table: &dyn TableLike = doc.as_table();
    for seg in parents {
        table = table
            .get(seg)
            .and_then(Item::as_table_like)
            .ok_or_else(|| format!("no table `{seg}` on the way to {old_path}"))?;
    }
    let (key, _) = table
        .get_key_value(last)
        .ok_or_else(|| format!("no key `{last}`"))?;
    let range = key.span().ok_or("the key has no source position")?;
    let new_leaf = new_path.rsplit_once('.').map_or(new_path, |(_, l)| l);
    edits.push(TextEdit {
        range,
        text: if is_bare_key(new_leaf) {
            new_leaf.to_owned()
        } else {
            format!("\"{new_leaf}\"")
        },
    });
    let target = AliasTarget {
        old_path,
        old,
        new_path,
        new,
    };
    alias_edits_in_table(doc.as_table(), text, &target, &mut edits);
    edits.sort_by_key(|e| std::cmp::Reverse(e.range.start));
    let mut out = text.to_owned();
    for e in &edits {
        out.replace_range(e.range.clone(), &e.text);
    }
    Ok((out, edits.len()))
}

/// What an alias must name to be retargeted, and what it becomes.
struct AliasTarget<'a> {
    old_path: &'a str,
    old: &'a str,
    new_path: &'a str,
    new: &'a str,
}

impl AliasTarget<'_> {
    /// The replacement for alias body `path` (the text between the braces), when it names the token.
    fn retarget(&self, path: &str) -> Option<String> {
        if path == self.old_path {
            Some(self.new_path.to_owned())
        } else if dialect::name_of_path(path) == self.old {
            Some(self.new.trim_start_matches("--").to_owned())
        } else {
            None
        }
    }
}

/// True when `key` can be written as a bare TOML key.
fn is_bare_key(key: &str) -> bool {
    key.chars()
        .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
}

/// Collect alias edits from every value under `table`, skipping prose fields.
fn alias_edits_in_table(
    table: &dyn TableLike,
    text: &str,
    t: &AliasTarget<'_>,
    out: &mut Vec<TextEdit>,
) {
    for (key, item) in table.iter() {
        if matches!(key, "description" | "deprecated") {
            continue;
        }
        alias_edits_in_item(item, text, t, out);
    }
}

/// Collect alias edits from one item.
fn alias_edits_in_item(item: &Item, text: &str, t: &AliasTarget<'_>, out: &mut Vec<TextEdit>) {
    match item {
        Item::Value(v) => alias_edits_in_value(v, text, t, out),
        Item::ArrayOfTables(tables) => {
            for table in tables {
                alias_edits_in_table(table, text, t, out);
            }
        }
        other => {
            if let Some(table) = other.as_table_like() {
                alias_edits_in_table(table, text, t, out);
            }
        }
    }
}

/// Collect alias edits from one value, recursing into arrays and inline tables.
fn alias_edits_in_value(v: &Value, text: &str, t: &AliasTarget<'_>, out: &mut Vec<TextEdit>) {
    match v {
        Value::String(s) => {
            let Some(path) = s
                .value()
                .strip_prefix('{')
                .and_then(|r| r.strip_suffix('}'))
            else {
                return;
            };
            let (Some(new_body), Some(span)) = (t.retarget(path), v.span()) else {
                return;
            };
            let raw = &text[span.clone()];
            let quote = if raw.starts_with("\"\"\"") || raw.starts_with("'''") {
                3
            } else {
                1
            };
            let body = span.start + quote..span.end - quote;
            out.push(TextEdit {
                range: body,
                text: format!("{{{new_body}}}"),
            });
        }
        Value::Array(items) => {
            for item in items {
                alias_edits_in_value(item, text, t, out);
            }
        }
        Value::InlineTable(table) => alias_edits_in_table(table, text, t, out),
        _ => {}
    }
}

/// Scene and other `design/**/*.html` files not already scanned, (the language tag is unused: they are rewritten by [`rewrite_html`]).
fn html_files(root: &Path, scanned: &[(PathBuf, Lang)]) -> Vec<(PathBuf, Lang)> {
    let mut found = Vec::new();
    collect_html(&root.join("design"), &mut found);
    found.sort();
    found
        .into_iter()
        .filter(|p| !scanned.iter().any(|(s, _)| s == p))
        .map(|p| (p, Lang::Script))
        .collect()
}

/// Rewrite `var(--old)` uses in HTML (inline styles and `<style>` blocks), leaving `<!-- -->`
/// comments and longer names alone; returns the new text and the replacement count.
fn rewrite_html(text: &str, pairs: &[(String, String)]) -> (String, usize) {
    let mut out = String::with_capacity(text.len());
    let mut count = 0;
    let mut rest = text;
    while !rest.is_empty() {
        if let Some(body) = rest.strip_prefix("<!--") {
            let end = body.find("-->").map_or(rest.len(), |i| i + 7);
            out.push_str(&rest[..end]);
            rest = &rest[end..];
        } else if let Some(after) = rest.strip_prefix("var(") {
            let ws = after.len() - after.trim_start().len();
            let name_at = &after[ws..];
            let hit = pairs.iter().find(|(old, _)| {
                name_at.starts_with(old.as_str())
                    && !name_at[old.len()..]
                        .chars()
                        .next()
                        .is_some_and(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
            });
            if let Some((old, new)) = hit {
                out.push_str(&rest[..4 + ws]);
                out.push_str(new);
                rest = &name_at[old.len()..];
                count += 1;
            } else {
                out.push_str("var(");
                rest = after;
            }
        } else {
            let ch = rest.chars().next().unwrap_or_default();
            out.push(ch);
            rest = &rest[ch.len_utf8()..];
        }
    }
    (out, count)
}

/// Collect `.html` files under `dir`, skipping hidden directories.
fn collect_html(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in entries.filter_map(Result::ok) {
        let path = entry.path();
        let hidden = entry.file_name().to_string_lossy().starts_with('.');
        match entry.file_type() {
            Ok(kind) if kind.is_dir() && !hidden => collect_html(&path, out),
            Ok(kind) if kind.is_file() && path.extension().is_some_and(|e| e == "html") => {
                out.push(path);
            }
            _ => {}
        }
    }
}

/// Rewrite every reference for `pairs` in `text`.
fn rewrite_refs(text: &str, lang: Lang, pairs: &[(String, String)]) -> (String, usize) {
    let m = RenameMatcher::new(pairs.to_vec(), lang);
    scan(text, lang, |t, k, s| m.at(t, k, s))
}

/// The spec key the new name implies: the name minus the family prefix of the old token.
fn new_key(token: &Token, new: &str) -> Result<String, PlanError> {
    let name = &token.name;
    let stack =
        token.kind == TokenKind::FontFamily && token.origin.starts_with("[typography.stacks]");
    if !(matches!(token.kind, TokenKind::Color | TokenKind::Layer) || stack) {
        let why = match token.kind {
            TokenKind::ColorChannels => "it follows its color; rename the color instead",
            TokenKind::FontFamily => {
                "it is the base stack fixed by [typography] families; rename a [typography.stacks] entry instead"
            }
            _ => "its name follows its step value; change the step in crunk.toml instead",
        };
        return Err(PlanError::Derived(name.clone(), why.to_owned()));
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
            TokenKind::FontFamily => section == "typography.stacks",
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

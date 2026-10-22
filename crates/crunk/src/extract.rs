//! `extract-token LITERAL`: promote a hex colour literal to a `[palette]` token.
//!
//! The literal is added to `crunk.toml`, every use of it in stylesheets and `[jsx] globs` sources
//! becomes `var(--color-KEY)`, and the generated exports are regenerated. Files are written
//! all-or-nothing; `--dry-run` writes nothing.

// frob:ticket 01M4CXRB2DX0B0BW7YJPAN1YXT

use std::path::Path;

use crunk_spec::naming::{color_token, sanitize_ident};
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};

use crate::PRODUCT;
use crate::rename::load;
use crate::rewrite::{
    Change, HexMatcher, Lang, RewriteData, commit_atomic, generated_changes, header_of,
    normalize_hex, reference_changes, scan, source_files,
};

/// Promote a hex colour literal to a palette token and rewrite its uses.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "extract-token",
    product = "crunk",
    idempotent = false,
    dry_run,
    exits(ok, refused, usage, internal)
)]
pub struct ExtractToken {
    literal: String,
    name: Option<String>,
}

/// `ExtractToken` arguments.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct ExtractArgs {
    #[arg(
        value_name = "LITERAL",
        help = "The hex colour to promote, e.g. #1a2b3c"
    )]
    literal: String,
    #[arg(
        long,
        value_name = "KEY",
        help = "Palette key for the token (default c<hex>)"
    )]
    name: Option<String>,
}

fn refuse(code: &str, msg: String) -> CliError {
    tracing::info!(code, error = %msg, "extract-token refused");
    Refusal::new(code, RefusalClass::GuardNeedsAction, msg)
        .with_remedy("fix the request as described, then rerun")
        .into()
}

impl Command for ExtractToken {
    type Data = RewriteData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<ExtractArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<ExtractArgs>(m)?;
        Ok(Self {
            literal: a.literal,
            name: a.name,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<RewriteData> {
        let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
        let (name, changes) = plan(&root, &self.literal, self.name.as_deref())?;
        let data = RewriteData::new(&root, &self.literal, &name, ctx.dry_run, &changes);
        if ctx.dry_run {
            tracing::info!(
                files = changes.len(),
                "extract-token: dry run, nothing written"
            );
        } else {
            commit_atomic(&changes).map_err(|e| {
                Refusal::new(
                    "E-EXTRACT-WRITE",
                    RefusalClass::GuardNeedsAction,
                    e.to_string(),
                )
                .with_remedy("fix the file permissions; every earlier write was rolled back")
            })?;
            tracing::info!(files = changes.len(), token = %name, "extract-token: written");
        }
        let lines = data.lines();
        Ok(Payload::new(data).with_rendered(lines))
    }
}

/// Compute the new token name and every file change, without writing anything.
fn plan(root: &Path, literal: &str, key: Option<&str>) -> Result<(String, Vec<Change>), CliError> {
    let Some(hex) = normalize_hex(literal) else {
        return Err(refuse(
            "E-EXTRACT-LITERAL",
            format!("{literal:?} is not a hex colour (#rgb or #rrggbb)"),
        ));
    };
    let (spec, tokens) = load(root).map_err(|e| refuse("E-EXTRACT-SPEC", e.to_string()))?;
    let key = key.map_or_else(
        || format!("c{}", hex.trim_start_matches('#')),
        str::to_owned,
    );
    if key.is_empty() || sanitize_ident(&key) != key {
        return Err(refuse(
            "E-EXTRACT-NAME",
            format!("{key:?} is not a lowercase identifier key"),
        ));
    }
    let name = color_token(&spec.tokens, &key);
    if tokens.get(&name).is_some() {
        return Err(refuse(
            "E-EXTRACT-EXISTS",
            format!("{name} is already a token"),
        ));
    }
    let toml_path = root.join("crunk.toml");
    let toml_text = std::fs::read_to_string(&toml_path)
        .map_err(|e| refuse("E-EXTRACT-SPEC", format!("cannot read crunk.toml: {e}")))?;
    let Some(edited) = insert_palette_key(&toml_text, &key, &hex) else {
        return Err(refuse(
            "E-EXTRACT-DEF",
            "crunk.toml has no [palette] table".to_owned(),
        ));
    };
    let new_spec = crunk_spec::parse_spec(&edited, &toml_path, root)
        .map_err(|e| refuse("E-EXTRACT-DEF", e.to_string()))?;
    let generated = crunk_tokens::export::render_managed(&new_spec)
        .map_err(|e| refuse("E-EXTRACT-SPEC", e.to_string()))?;
    let files: Vec<_> = source_files(root, &spec, &generated)
        .into_iter()
        .filter(|(_, lang)| *lang != Lang::Toml)
        .collect();
    let matcher = HexMatcher::new(&hex, format!("var({name})")).ok_or_else(|| {
        refuse(
            "E-EXTRACT-LITERAL",
            format!("{literal:?} is not a hex colour"),
        )
    })?;
    let mut changes = reference_changes(&files, |text, lang| {
        scan(text, lang, |t, k, site| match site {
            crate::rewrite::Site::Code => matcher.at(t, k),
            crate::rewrite::Site::Str { .. } => None,
        })
    });
    changes.insert(
        0,
        Change {
            path: toml_path,
            before: Some(toml_text),
            after: edited,
            kind: "definition",
            replacements: 1,
        },
    );
    changes.extend(generated_changes(&generated));
    Ok((name, changes))
}

/// Insert `key = "hex"` after the last direct key line of `[palette]`.
fn insert_palette_key(text: &str, key: &str, hex: &str) -> Option<String> {
    let lines: Vec<&str> = text.split_inclusive('\n').collect();
    let mut in_palette = false;
    let mut insert_at = None;
    for (i, line) in lines.iter().enumerate() {
        if let Some(h) = header_of(line) {
            in_palette = h == "palette";
            if in_palette {
                insert_at = Some(i + 1);
            }
        } else if in_palette && line.contains('=') && !line.trim_start().starts_with('#') {
            insert_at = Some(i + 1);
        }
    }
    let at = insert_at?;
    let mut out = String::new();
    for (i, line) in lines.iter().enumerate() {
        out.push_str(line);
        if i + 1 == at {
            if !line.ends_with('\n') {
                out.push('\n');
            }
            out.push_str(key);
            out.push_str(" = \"");
            out.push_str(hex);
            out.push_str("\"\n");
        }
    }
    Some(out)
}

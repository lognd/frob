//! `extract-token LITERAL`: promote a hex colour or a px/rem length literal to a design token.
//!
//! A colour is added to `[palette]`, a length to a `[scales]` list (`--scale`, default `spacing`).
//! Every use of the literal in stylesheets and `[jsx] globs` sources becomes `var(--TOKEN)`, and
//! the generated exports are regenerated. Durations are refused: `crunk.toml` has no duration
//! table. Files are written all-or-nothing; `--dry-run` writes nothing.

// frob:ticket 01M4CXRB2DX0B0BW7YJPAN1YXT
// frob:ticket 01M5H3RXZHDEDM508R6K4DBBVJ

use std::path::Path;

use crunk_spec::DesignSpec;
use crunk_spec::naming::{color_token, font_size_token, radius_token, sanitize_ident, space_token};
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};

use crate::PRODUCT;
use crate::rename::load;
use crate::rewrite::{
    Change, HexMatcher, Hit, Lang, RewriteData, Site, commit_atomic, generated_changes, header_of,
    normalize_hex, reference_changes, scan, source_files,
};

/// Promote a hex colour or px/rem length literal to a token and rewrite its uses.
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
    scale: Option<String>,
}

/// `ExtractToken` arguments.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct ExtractArgs {
    #[arg(
        value_name = "LITERAL",
        allow_hyphen_values = true,
        help = "The hex colour or px/rem length to promote, e.g. #1a2b3c or 16px"
    )]
    literal: String,
    #[arg(
        long,
        value_name = "KEY",
        help = "Palette key for the token (default c<hex>)"
    )]
    name: Option<String>,
    #[arg(
        long,
        value_name = "SCALE",
        value_parser = ["spacing", "font-sizes", "radii"],
        help = "Scale a length joins (default spacing)"
    )]
    scale: Option<String>,
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
            scale: a.scale,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<RewriteData> {
        let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
        let (name, changes) = plan(
            &root,
            &self.literal,
            self.name.as_deref(),
            self.scale.as_deref(),
        )?;
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

/// The `[scales]` list a length literal joins.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Scale {
    Spacing,
    FontSizes,
    Radii,
}

impl Scale {
    /// Parse the `--scale` value (already restricted by clap); spacing when absent.
    fn parse(name: Option<&str>) -> Self {
        match name {
            Some("font-sizes") => Self::FontSizes,
            Some("radii") => Self::Radii,
            _ => Self::Spacing,
        }
    }

    /// The `[scales]` key.
    fn key(self) -> &'static str {
        match self {
            Self::Spacing => "spacing",
            Self::FontSizes => "font_sizes",
            Self::Radii => "radii",
        }
    }

    /// The custom property a step of this scale is exported as.
    fn token(self, spec: &DesignSpec, px: f64) -> String {
        match self {
            Self::Spacing => space_token(&spec.tokens, px),
            Self::FontSizes => font_size_token(&spec.tokens, px),
            Self::Radii => radius_token(&spec.tokens, px),
        }
    }
}

/// What a request promotes, validated but not yet checked against the project.
enum Request {
    Hex(String),
    Length { value: f64, unit: String },
}

/// Split a bare dimension (`16px`, `.5REM`, `-2px`) into its number and lowercase unit.
///
/// None when the text is not exactly one number followed by a unit of letters or `%`.
#[must_use]
pub fn parse_dimension(text: &str) -> Option<(f64, String)> {
    let t = text.trim();
    let body = t.strip_prefix(['-', '+']).unwrap_or(t);
    let (len, value) = number_at(body.as_bytes(), 0)?;
    let unit = &body[len..];
    let ok = unit == "%" || (!unit.is_empty() && unit.bytes().all(|b| b.is_ascii_alphabetic()));
    let value = if t.starts_with('-') { -value } else { value };
    ok.then(|| (value, unit.to_ascii_lowercase()))
}

/// Parse an unsigned decimal at `k` (`16`, `1.5`, `.5`): its byte length and value.
fn number_at(bytes: &[u8], k: usize) -> Option<(usize, f64)> {
    let mut i = k;
    while bytes.get(i).is_some_and(u8::is_ascii_digit) {
        i += 1;
    }
    let int_digits = i - k;
    let mut frac_digits = 0;
    if bytes.get(i) == Some(&b'.') && bytes.get(i + 1).is_some_and(u8::is_ascii_digit) {
        i += 1;
        while bytes.get(i).is_some_and(u8::is_ascii_digit) {
            i += 1;
            frac_digits += 1;
        }
    }
    if int_digits == 0 && frac_digits == 0 {
        return None;
    }
    let text = std::str::from_utf8(&bytes[k..i]).ok()?;
    Some((i - k, text.parse().ok()?))
}

/// True for bytes that continue a CSS identifier.
fn is_ident(b: u8) -> bool {
    b.is_ascii_alphanumeric() || b == b'_' || b == b'-'
}

/// Matches one px/rem length wherever it is written, in any case or number form.
pub struct LengthMatcher {
    value: f64,
    unit: String,
    replacement: String,
}

impl LengthMatcher {
    /// A matcher for `value` in `unit` (lowercase), replaced by `replacement`.
    #[must_use]
    pub fn new(value: f64, unit: &str, replacement: String) -> Self {
        Self {
            value,
            unit: unit.to_owned(),
            replacement,
        }
    }

    /// Offer position `k`: number form and case are normalised, but signed values, identifier
    /// fragments, `url(...)` and at-rule preludes (where `var()` is invalid) are never rewritten.
    #[must_use]
    pub fn at(&self, text: &str, k: usize) -> Option<Hit> {
        let bytes = text.as_bytes();
        if !(bytes[k].is_ascii_digit() || bytes[k] == b'.') {
            return None;
        }
        if k > 0
            && (is_ident(bytes[k - 1]) || matches!(bytes[k - 1], b'.' | b'+' | b'#' | b'\\' | b'&'))
        {
            return None;
        }
        let (len, value) = number_at(bytes, k)?;
        let unit_start = k + len;
        let unit_len = bytes[unit_start..]
            .iter()
            .take_while(|b| b.is_ascii_alphabetic())
            .count();
        let end = unit_start + unit_len;
        if bytes.get(end).is_some_and(|&b| is_ident(b) || b == b'%') {
            return None;
        }
        if !text[unit_start..end].eq_ignore_ascii_case(&self.unit)
            || (value - self.value).abs() > 1e-9
        {
            return None;
        }
        if in_url(text, k) || in_prelude(text, k) {
            tracing::debug!(
                at = k,
                "extract-token: length skipped in url() or at-rule prelude"
            );
            return None;
        }
        Some((end - k, self.replacement.clone()))
    }
}

/// True when `k` sits inside an unclosed `url(` on its line.
fn in_url(text: &str, k: usize) -> bool {
    let line = line_before(text, k).to_ascii_lowercase();
    line.rfind("url(")
        .is_some_and(|open| !line[open..].contains(')'))
}

/// True when `k` is in the prelude of an at-rule that cannot take `var()` (same line, before `{`).
fn in_prelude(text: &str, k: usize) -> bool {
    let line = line_before(text, k).to_ascii_lowercase();
    [
        "@media",
        "@container",
        "@supports",
        "@import",
        "@custom-media",
    ]
    .iter()
    .filter_map(|at| line.rfind(at))
    .max()
    .is_some_and(|open| !line[open..].contains('{'))
}

/// The part of `k`'s line that precedes it.
fn line_before(text: &str, k: usize) -> &str {
    let head = &text[..k];
    &head[head.rfind('\n').map_or(0, |i| i + 1)..]
}

/// Classify `literal`, refusing every kind that has no token table with a specific code.
fn classify(literal: &str) -> Result<Request, CliError> {
    if let Some(hex) = normalize_hex(literal) {
        return Ok(Request::Hex(hex));
    }
    let Some((value, unit)) = parse_dimension(literal) else {
        return Err(refuse(
            "E-EXTRACT-LITERAL",
            format!("{literal:?} is not a hex colour (#rgb or #rrggbb) or a px/rem length"),
        ));
    };
    if value < 0.0 {
        return Err(refuse(
            "E-EXTRACT-NEGATIVE",
            format!("{literal:?} is negative; scale steps are non-negative px values"),
        ));
    }
    match unit.as_str() {
        "px" | "rem" if value == 0.0 => Err(refuse(
            "E-EXTRACT-ZERO",
            format!("{literal:?} is zero, which needs no token and would rewrite every zero"),
        )),
        "px" | "rem" => Ok(Request::Length { value, unit }),
        "ms" | "s" => Err(refuse(
            "E-EXTRACT-DURATION",
            format!(
                "{literal:?} is a duration; crunk.toml has no duration table (design/tokens \
                 files are linted but never emitted as custom properties)"
            ),
        )),
        _ => Err(refuse(
            "E-EXTRACT-UNIT",
            format!(
                "{literal:?}: unit {unit:?} has no px value; only px and rem lengths join a scale"
            ),
        )),
    }
}

/// The edit a promotion makes to `crunk.toml`, and the token it creates.
struct Definition {
    name: String,
    edited: String,
    matcher: Matcher,
}

/// Finds the uses of the promoted literal.
enum Matcher {
    Hex(HexMatcher),
    Length(LengthMatcher),
}

impl Matcher {
    /// Offer position `k` to the wrapped matcher.
    fn at(&self, text: &str, k: usize) -> Option<Hit> {
        match self {
            Self::Hex(m) => m.at(text, k),
            Self::Length(m) => m.at(text, k),
        }
    }
}

/// Compute the new token name and every file change, without writing anything.
fn plan(
    root: &Path,
    literal: &str,
    key: Option<&str>,
    scale: Option<&str>,
) -> Result<(String, Vec<Change>), CliError> {
    let request = classify(literal)?;
    let (spec, tokens) = load(root).map_err(|e| refuse("E-EXTRACT-SPEC", e.to_string()))?;
    let toml_path = root.join("crunk.toml");
    let toml_text = std::fs::read_to_string(&toml_path)
        .map_err(|e| refuse("E-EXTRACT-SPEC", format!("cannot read crunk.toml: {e}")))?;
    let def = match request {
        Request::Hex(hex) => hex_definition(&spec, &toml_text, &hex, key, scale)?,
        Request::Length { value, unit } => {
            length_definition(&spec, &toml_text, value, &unit, key, scale)?
        }
    };
    let Definition {
        name,
        edited,
        matcher,
    } = def;
    if tokens.get(&name).is_some() {
        return Err(refuse(
            "E-EXTRACT-EXISTS",
            format!("{name} is already a token"),
        ));
    }
    let new_spec = crunk_spec::parse_spec(&edited, &toml_path, root)
        .map_err(|e| refuse("E-EXTRACT-DEF", e.to_string()))?;
    let generated = crunk_tokens::export::render_managed(&new_spec)
        .map_err(|e| refuse("E-EXTRACT-SPEC", e.to_string()))?;
    let files: Vec<_> = source_files(root, &spec, &generated)
        .into_iter()
        .filter(|(_, lang)| *lang != Lang::Toml)
        .collect();
    let mut changes = reference_changes(&files, |text, lang| {
        scan(text, lang, |t, k, site| match site {
            Site::Code => matcher.at(t, k),
            Site::Str { .. } => None,
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

/// The palette definition for a hex colour.
fn hex_definition(
    spec: &DesignSpec,
    toml_text: &str,
    hex: &str,
    key: Option<&str>,
    scale: Option<&str>,
) -> Result<Definition, CliError> {
    if scale.is_some() {
        return Err(refuse(
            "E-EXTRACT-SCALE",
            "--scale applies to lengths, not colours".to_owned(),
        ));
    }
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
    let Some(edited) = insert_palette_key(toml_text, &key, hex) else {
        return Err(refuse(
            "E-EXTRACT-DEF",
            "crunk.toml has no [palette] table".to_owned(),
        ));
    };
    let matcher = HexMatcher::new(hex, format!("var({name})"))
        .ok_or_else(|| refuse("E-EXTRACT-LITERAL", format!("{hex:?} is not a hex colour")))?;
    Ok(Definition {
        name,
        edited,
        matcher: Matcher::Hex(matcher),
    })
}

/// The scale-step definition for a px or rem length (stored in px).
fn length_definition(
    spec: &DesignSpec,
    toml_text: &str,
    value: f64,
    unit: &str,
    key: Option<&str>,
    scale: Option<&str>,
) -> Result<Definition, CliError> {
    if key.is_some() {
        return Err(refuse(
            "E-EXTRACT-NAME",
            "--name applies to colours; a scale step is named by its value".to_owned(),
        ));
    }
    let scale = Scale::parse(scale);
    let px = if unit == "rem" {
        round_px(value * spec.project.root_font_size)
    } else {
        value
    };
    let name = scale.token(spec, px);
    let edited = insert_scale_step(toml_text, scale.key(), px)
        .map_err(|why| refuse("E-EXTRACT-DEF", why))?;
    tracing::debug!(%name, px, scale = scale.key(), "extract-token: length step");
    Ok(Definition {
        name: name.clone(),
        edited,
        matcher: Matcher::Length(LengthMatcher::new(value, unit, format!("var({name})"))),
    })
}

/// Round a px value to micro-pixels so `0.4rem` at 16px is `6.4`, not `6.4000000000000004`.
fn round_px(px: f64) -> f64 {
    (px * 1e6).round() / 1e6
}

#[allow(clippy::cast_precision_loss, clippy::cast_possible_truncation)]
/// Insert `px` into the ascending `[scales] key` list, keeping the list's layout.
fn insert_scale_step(text: &str, key: &str, px: f64) -> Result<String, String> {
    use toml_edit::{Array, DocumentMut, Item, Value};
    let mut doc: DocumentMut = text
        .parse()
        .map_err(|e: toml_edit::TomlError| e.to_string())?;
    let Some(scales) = doc.get_mut("scales").and_then(Item::as_table_like_mut) else {
        return Err("crunk.toml has no [scales] table".to_owned());
    };
    if scales.get(key).is_none() {
        scales.insert(key, Item::Value(Value::Array(Array::new())));
    }
    let Some(array) = scales.get_mut(key).and_then(Item::as_array_mut) else {
        return Err(format!("[scales] {key} is not a list"));
    };
    let number = |v: &Value| v.as_float().or_else(|| v.as_integer().map(|i| i as f64));
    let at = array
        .iter()
        .position(|v| number(v).is_some_and(|n| n > px))
        .unwrap_or(array.len());
    let mut value = if px.fract() == 0.0 {
        Value::from(px as i64)
    } else {
        Value::from(px)
    };
    // Copy the layout of the neighbours: multi-line lists keep one item per line.
    let decor = array.iter().last().map(|v| v.decor().clone());
    let first_decor = array.iter().next().map(|v| v.decor().clone());
    if at == array.len() {
        if let Some(d) = decor {
            *value.decor_mut() = d;
        } else {
            value.decor_mut().set_prefix("");
        }
        if array.len() == 1 {
            value.decor_mut().set_prefix(" ");
        }
        array.insert(at, value);
        array.set_trailing_comma(array.trailing_comma() && array.len() > 1);
    } else {
        if let Some(d) = first_decor {
            *value.decor_mut() = d;
        }
        array.insert(at, value);
        if at == 0
            && let Some(old) = array.get_mut(1)
        {
            let multiline = old
                .decor()
                .prefix()
                .is_some_and(|p| p.as_str().is_some_and(|s| s.contains('\n')));
            old.decor_mut()
                .set_prefix(if multiline { "\n    " } else { " " });
        }
    }
    Ok(doc.to_string())
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
    let nl = if text.contains("\r\n") { "\r\n" } else { "\n" };
    let mut out = String::new();
    for (i, line) in lines.iter().enumerate() {
        out.push_str(line);
        if i + 1 == at {
            if !line.ends_with('\n') {
                out.push_str(nl);
            }
            out.push_str(key);
            out.push_str(" = \"");
            out.push_str(hex);
            out.push('"');
            out.push_str(nl);
        }
    }
    Some(out)
}

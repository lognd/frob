//! COLOR001: a colour literal that is not conformant to the palette (port of `crunk/rules/_color.py`
//! `color001`; design: `language-engines.md` sections 2 and 5, D96, D101, `notes/crunk.md`).
//!
//! Declarations come from the shared `style` capability ([`gob_ir::style`]) over the CSS adapter's
//! terms and over the TypeScript adapter's inline `style={{ ... }}` objects, so one rule reads CSS,
//! TSX and HTML alike and no crunk crate parses a language. The colour maths is `crunk-values`.
//!
//! A literal is conformant when its `to_hex()` matches a palette entry, or when it is translucent
//! and its `rgb_hex()` matches an opaque palette entry (a translucent variant of an opaque palette
//! colour is not a new colour). Otherwise the nearest palette entry (RGB distance) is named in the
//! message. The generated tokens sheet is skipped: the palette literals live there.
//!
//! Divergences from the Python rule: the fix payload is not attached here (the autofix ticket owns
//! it), so `fix = Manual`; an unparseable literal (`inherit`, `transparent`, a `calc()`) is not a
//! colour and is skipped; waivers are the pipeline's exceptions, not an in-rule lookup.

// frob:ticket 01M48FXB2PXX2FBXFKCFWSQYH1

use std::collections::BTreeSet;
use std::path::Path;

use crunk_spec::naming::color_token;
use crunk_spec::{DesignSpec, Severity as SpecSeverity};
use crunk_values::Color;
use gob_check::{RepoGroup, Snapshot};
use gob_ir::style::{self, ValuePart};
use gob_ir::{Model, NodeId};
use gob_rules::{Finding, RuleMeta, Severity};
use gob_symbols::fold_file;
use gob_text::{FileInterner, Span};
use gob_walk::FileEntry;

use crate::product::Crunk;

/// A colour literal that is not a palette colour (and not a translucent variant of an opaque one).
#[derive(Debug, Clone, Copy, Default, gob_rules::Rule)]
#[rule(
    id = "COLOR001",
    slug = "color-off-palette",
    family = "COLOR",
    product = "crunk",
    severity = Error,
    tier = Lang,
    scope = Repo,
    fix = Manual,
    polarity = Pplus,
    must_measure = false,
    version = 1,
    since = "0.532.0"
)]
pub struct Color001;

/// Language tags whose files can hold declarations (CSS, TS/TSX style props, HTML style attributes).
pub(crate) const STYLE_TAGS: [&str; 6] = ["css", "tsx", "jsx", "ts", "js", "html"];

/// The registered metadata of COLOR001.
fn meta() -> &'static RuleMeta {
    gob_rules::Registry::global()
        .by_id("COLOR001")
        .unwrap_or_else(|| unreachable!("COLOR001 is registered by the derive above"))
}

fn rule_id() -> gob_rules::RuleId {
    meta()
        .rule_id()
        .unwrap_or_else(|_| unreachable!("COLOR001 is a valid rule id"))
}

/// The COLOR001 repo group.
pub fn group() -> RepoGroup<Crunk> {
    RepoGroup::new("repo:color", vec![meta()], run).counting(|snap| {
        let n = if snap.inputs.spec.is_some() {
            style_files(&snap.core.entries).count()
        } else {
            0
        };
        vec![("COLOR001", n)]
    })
}

fn style_files(entries: &[FileEntry]) -> impl Iterator<Item = &FileEntry> {
    entries
        .iter()
        .filter(|e| STYLE_TAGS.contains(&e.language.tag()))
}

fn run(snap: &Snapshot<Crunk>, files: &mut FileInterner) -> Vec<Finding> {
    let Some(spec) = &snap.inputs.spec else {
        tracing::debug!("COLOR001 skipped: no valid crunk.toml");
        return Vec::new();
    };
    let severity = match spec.severity("COLOR001") {
        SpecSeverity::Off => {
            tracing::debug!("COLOR001 is off in [lint]");
            return Vec::new();
        }
        SpecSeverity::Warn => Severity::Warn,
        SpecSeverity::Error => Severity::Error,
    };
    let palette = Palette::of(spec);
    let tokens = relative(&snap.core.root, &spec.tokens_path());
    let mut out = Vec::new();
    for entry in style_files(&snap.core.entries) {
        if tokens.as_deref() == Some(entry.path.as_str()) {
            tracing::trace!(path = %entry.path, "COLOR001 skips the generated tokens sheet");
            continue;
        }
        let Ok(text) = std::fs::read_to_string(snap.core.root.join(&entry.path)) else {
            tracing::debug!(path = %entry.path, "COLOR001 cannot read file");
            continue;
        };
        let folded = match fold_file(entry, &text) {
            Ok(f) => f,
            Err(err) => {
                tracing::error!(path = %entry.path, %err, "adapter bug: fold failed");
                continue;
            }
        };
        let model = Model::new(folded.term, folded.scopes);
        let file = files.intern(&entry.path);
        for (owner, values) in sites(&model) {
            for color in colors_of(&values) {
                if palette.conforms(color) {
                    continue;
                }
                out.push(finding(
                    spec,
                    &palette,
                    &entry.path,
                    file,
                    &model,
                    owner,
                    color,
                    severity,
                ));
            }
        }
    }
    tracing::debug!(findings = out.len(), "COLOR001 evaluated");
    out
}

/// Every declaration and custom property value list with the node that owns it.
fn sites(model: &Model) -> Vec<(NodeId, Vec<ValuePart>)> {
    let mut out: Vec<(NodeId, Vec<ValuePart>)> = style::declarations(model)
        .into_iter()
        .map(|d| (d.node, d.values))
        .collect();
    out.extend(
        style::custom_properties(model)
            .into_iter()
            .map(|c| (c.node, c.values)),
    );
    out.sort_by_key(|(n, _)| *n);
    out
}

/// The colour literals among `values`.
fn colors_of(values: &[ValuePart]) -> Vec<Color> {
    values
        .iter()
        .filter_map(|v| match v {
            ValuePart::Lit { kind, text }
                if matches!(kind.as_str(), "color" | "function" | "ident") =>
            {
                Color::parse(text).ok()
            }
            _ => None,
        })
        .collect()
}

#[allow(clippy::too_many_arguments)]
fn finding(
    spec: &DesignSpec,
    palette: &Palette,
    path: &str,
    file: gob_text::FileId,
    model: &Model,
    node: NodeId,
    color: Color,
    severity: Severity,
) -> Finding {
    let (name, distance) = palette.nearest(color);
    let token = color_token(&spec.tokens, name);
    let hexed = color.to_hex();
    let message = if color.is_opaque() {
        format!("color {hexed} is not a palette color; nearest is {token} (distance {distance:.2})")
    } else {
        format!(
            "color {hexed} is not a palette color; nearest is {token} (rgb distance {distance:.2}); the fix preserves alpha"
        )
    };
    let span = model
        .term()
        .node(node)
        .location()
        .span()
        .map(|s| Span::new(file, s.range));
    let anchor = format!(
        "{path}::{}",
        model.term().node(node).name().unwrap_or_default()
    );
    Finding::new(rule_id(), severity, span, message, &anchor)
}

/// The palette's exact and opaque-rgb hex sets, kept with the entries for nearest lookups.
struct Palette<'a> {
    entries: Vec<(&'a str, Color)>,
    exact: BTreeSet<String>,
    opaque_rgb: BTreeSet<String>,
}

impl<'a> Palette<'a> {
    fn of(spec: &'a DesignSpec) -> Self {
        let entries: Vec<(&str, Color)> =
            spec.palette.iter().map(|(n, c)| (n.as_str(), *c)).collect();
        Self {
            exact: entries.iter().map(|(_, c)| c.to_hex()).collect(),
            opaque_rgb: entries
                .iter()
                .filter(|(_, c)| c.is_opaque())
                .map(|(_, c)| c.rgb_hex())
                .collect(),
            entries,
        }
    }

    /// True when `color` needs no violation (exact hex, or translucent over an opaque entry).
    fn conforms(&self, color: Color) -> bool {
        self.exact.contains(&color.to_hex())
            || (!color.is_opaque() && self.opaque_rgb.contains(&color.rgb_hex()))
    }

    /// The closest palette entry by [`Color::distance`], first on ties.
    fn nearest(&self, color: Color) -> (&'a str, f64) {
        self.entries
            .iter()
            .map(|(n, c)| (*n, color.distance(*c)))
            .fold(None, |best: Option<(&str, f64)>, cur| match best {
                Some(b) if b.1 <= cur.1 => Some(b),
                _ => Some(cur),
            })
            .unwrap_or(("", f64::INFINITY))
    }
}

/// `path` relative to `root`, forward-slash separated; `None` when it lies elsewhere.
fn relative(root: &Path, path: &Path) -> Option<String> {
    path.strip_prefix(root)
        .ok()
        .map(|p| p.to_string_lossy().replace('\\', "/"))
}

//! CRAFT004: web fonts are shipped properly. A stylesheet that names a custom family in
//! `font-family` or a `--font*` custom property (anything but a system or generic family) must
//! carry an `@font-face` for it. Each `@font-face` states `font-display` and `unicode-range`, and
//! at least one declares a metric override (`size-adjust`, `ascent-override` or
//! `descent-override`) so the fallback font does not shift the layout when the face loads. System
//! stacks need nothing, and comments and strings are ignored. Advisory.

// frob:ticket 01M5HM3WE0PDTYAJ31B2C2A8A0

use crunk_ingest::Stylesheet;
use gob_rules::{Out, RepoRule, rule};

use crate::craft::{blocks, body_props, mask};
use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::site_path;
use crate::slop::judged_sheets;

/// Families that need no `@font-face`: generics, system UI stacks and the fonts every platform has.
const SYSTEM_FAMILIES: &[&str] = &[
    "serif",
    "sans-serif",
    "monospace",
    "cursive",
    "fantasy",
    "system-ui",
    "ui-serif",
    "ui-sans-serif",
    "ui-monospace",
    "ui-rounded",
    "emoji",
    "math",
    "fangsong",
    "-apple-system",
    "blinkmacsystemfont",
    "segoe ui",
    "helvetica",
    "helvetica neue",
    "arial",
    "times new roman",
    "times",
    "georgia",
    "courier new",
    "courier",
    "menlo",
    "monaco",
    "consolas",
    "roboto",
    "inherit",
    "initial",
    "unset",
    "revert",
];

/// The properties that stand in for a metric-matched fallback.
const METRIC_OVERRIDES: &[&str] = &["size-adjust", "ascent-override", "descent-override"];

/// The custom families a `font-family` value names, lowercased and unquoted.
fn custom_families(value: &str) -> Vec<String> {
    if value.contains("var(") {
        return Vec::new();
    }
    value
        .split(',')
        .map(|f| {
            f.trim()
                .trim_matches(['"', '\''])
                .trim()
                .to_ascii_lowercase()
        })
        .filter(|f| !f.is_empty() && !SYSTEM_FAMILIES.contains(&f.as_str()))
        .collect()
}

/// One `@font-face` block: the sheet path, its offset and the properties it declares.
struct Face {
    path: String,
    offset: usize,
    props: Vec<String>,
}

/// Every `@font-face` block of `sheet`, comments and strings masked out.
fn faces(spec: &crunk_spec::DesignSpec, sheet: &Stylesheet) -> Vec<Face> {
    let masked = mask(&sheet.source);
    blocks(&masked)
        .into_iter()
        .filter(|b| {
            b.selector_text(&masked)
                .to_ascii_lowercase()
                .starts_with("@font-face")
        })
        .map(|b| Face {
            path: site_path(spec, &sheet.path),
            offset: b.selector.0,
            props: body_props(b.body_text(&masked)),
        })
        .collect()
}

/// A custom font family that is not shipped through a complete `@font-face`.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CRAFT004",
    slug = "fonts-shipped",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Craft004;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Craft004 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let used = judged_sheets(styles).find_map(|sheet| {
            sheet
                .declarations
                .iter()
                .filter(|d| d.prop == "font-family" || d.prop.starts_with("--font"))
                .find_map(|d| {
                    custom_families(&d.value)
                        .into_iter()
                        .next()
                        .map(|family| (sheet, d.span.0, family))
                })
        });
        let Some((sheet, offset, family)) = used else {
            tracing::debug!("CRAFT004: only system fonts in use");
            return;
        };
        let faces: Vec<Face> = styles.sheets.iter().flat_map(|s| faces(spec, s)).collect();
        if faces.is_empty() {
            tracing::debug!(family, "CRAFT004: no @font-face");
            out.fire_in(
                &site_path(spec, &sheet.path),
                offset,
                format!(
                    "font family `{family}` has no `@font-face`: ship the font file with an \
                     `@font-face` rule (with `font-display` and `unicode-range`)"
                ),
            );
            return;
        }
        for face in &faces {
            let missing: Vec<&str> = ["font-display", "unicode-range"]
                .into_iter()
                .filter(|need| !face.props.iter().any(|p| p == need))
                .collect();
            if !missing.is_empty() {
                tracing::debug!(path = %face.path, ?missing, "CRAFT004: incomplete @font-face");
                out.fire_in(
                    &face.path,
                    face.offset,
                    format!("`@font-face` declares no {}", missing.join(" and ")),
                );
            }
        }
        if !faces.iter().any(|f| {
            f.props
                .iter()
                .any(|p| METRIC_OVERRIDES.contains(&p.as_str()))
        }) {
            let first = &faces[0];
            tracing::debug!("CRAFT004: no metric-matched fallback");
            out.fire_in(
                &first.path,
                first.offset,
                "no `@font-face` declares `size-adjust`, `ascent-override` or `descent-override`: \
                 add a metric-matched fallback so the layout does not shift when the font loads",
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

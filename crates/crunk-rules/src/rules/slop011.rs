//! SLOP011: a font is declared but never shipped (research top-20 #11). A literal `font-family`
//! or `--font-*` whose first family is not a generic or system face, and that no `@font-face` in
//! any sheet defines, silently falls back to the system stack. A project that loads fonts through
//! a service or loader (Google Fonts, Bunny, `next/font`, `@fontsource`) is exempt, and so is a
//! `[decisions] fonts` project. Warn.

// frob:ticket 01M4CXT4Z45GR5QE71B10FRR8N

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::site_path;
use crate::slop;
use crate::typography::split_family_stack;

/// Substrings of a source that mean fonts are loaded by a service or build step.
const LOADERS: &[&str] = &[
    "fonts.googleapis.com",
    "fonts.bunny.net",
    "next/font",
    "@fontsource",
];

/// Generic and system faces that need no shipping (lowercase).
const SYSTEM_FONTS: &[&str] = &[
    "serif",
    "sans-serif",
    "monospace",
    "cursive",
    "fantasy",
    "system-ui",
    "ui-sans-serif",
    "ui-serif",
    "ui-monospace",
    "ui-rounded",
    "-apple-system",
    "blinkmacsystemfont",
    "segoe ui",
    "helvetica",
    "helvetica neue",
    "arial",
    "georgia",
    "times new roman",
    "courier new",
    "inherit",
    "initial",
    "unset",
];

/// A named font-family that no @font-face or font loader ships.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SLOP011",
    slug = "font-not-shipped",
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
pub struct Slop011;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Slop011 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        if slop::decided(spec, "fonts") {
            return;
        }
        let sheets: Vec<_> = slop::judged_sheets(styles).collect();
        if sheets
            .iter()
            .any(|s| LOADERS.iter().any(|l| s.source.contains(l)))
        {
            tracing::debug!("SLOP011: a font loader is present; the rule stands down");
            return;
        }
        let shipped: Vec<String> = sheets
            .iter()
            .flat_map(|s| font_face_families(&s.source))
            .collect();
        for sheet in sheets {
            let path = site_path(spec, &sheet.path);
            let faces = font_face_ranges(&sheet.source);
            let families = sheet
                .declarations
                .iter()
                .filter(|d| d.prop == "font-family" || d.prop.starts_with("--font"))
                .filter(|d| d.var_refs.is_empty())
                .filter(|d| {
                    !faces
                        .iter()
                        .any(|(from, to)| (*from..*to).contains(&d.span.0))
                });
            for decl in families {
                let Some(first) = split_family_stack(&decl.value).into_iter().next() else {
                    continue;
                };
                if SYSTEM_FONTS.contains(&first.as_str()) || shipped.contains(&first) {
                    continue;
                }
                tracing::debug!(%path, font = %first, "SLOP011: font is not shipped");
                out.fire_in(
                    &path,
                    decl.span.0,
                    format!("font `{first}` has no @font-face or loader, so it falls back to the system stack"),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

/// Byte ranges `(from, to)` of the `@font-face { ... }` blocks of `source`.
fn font_face_ranges(source: &str) -> Vec<(usize, usize)> {
    source
        .match_indices("@font-face")
        .filter_map(|(at, _)| {
            let open = source[at..].find('{')? + at;
            let close = source[open..].find('}')? + open;
            Some((open, close))
        })
        .collect()
}

/// The lowercased, unquoted families the `@font-face` blocks of `source` define.
fn font_face_families(source: &str) -> Vec<String> {
    font_face_ranges(source)
        .into_iter()
        .filter_map(|(from, to)| {
            let block = &source[from..to];
            let at = block.find("font-family")?;
            let rest = block[at..].split_once(':')?.1;
            let value = rest.split([';', '}']).next()?;
            split_family_stack(value).into_iter().next()
        })
        .collect()
}

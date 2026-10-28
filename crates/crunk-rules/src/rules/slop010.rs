//! SLOP010: the font was never chosen (research top-20 #10). A literal `font-family` whose first
//! family is Inter, Roboto, Arial, system-ui or a second-wave default (Space Grotesk, Geist,
//! Instrument Serif, Fraunces, Syne) fires; `[decisions] fonts` records the rationale and silences
//! it. Advisory: a chosen Inter is fine.

// frob:ticket 01M4CXT4Z45GR5QE71B10FRR8N

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::site_path;
use crate::slop;
use crate::typography::split_family_stack;

/// Lowercased first families that mark an unchosen font: the classic and the second-wave defaults.
const UNCHOSEN_FONTS: &[&str] = &[
    "inter",
    "roboto",
    "arial",
    "system-ui",
    "space grotesk",
    "geist",
    "instrument serif",
    "fraunces",
    "syne",
];

/// A font-family led by Inter, Roboto, Arial, system-ui or a second-wave default with no fonts decision.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SLOP010",
    slug = "font-unchosen",
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
pub struct Slop010;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Slop010 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        if slop::decided(spec, "fonts") {
            return;
        }
        for sheet in slop::judged_sheets(styles) {
            let path = site_path(spec, &sheet.path);
            let families = sheet
                .declarations
                .iter()
                .filter(|d| d.prop == "font-family" || d.prop.starts_with("--font"))
                .filter(|d| d.var_refs.is_empty());
            for decl in families {
                let stack = split_family_stack(&decl.value);
                if let Some(first) = stack.first()
                    && UNCHOSEN_FONTS.contains(&first.as_str())
                {
                    tracing::debug!(%path, font = %first, "SLOP010: unchosen font");
                    out.fire_in(
                        &path,
                        decl.span.0,
                        format!("font `{first}` is a default nobody chose; declare `[decisions] fonts` with the rationale"),
                    );
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

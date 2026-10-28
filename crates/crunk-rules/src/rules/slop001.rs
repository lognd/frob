//! SLOP001: the accent is a Tailwind default indigo, violet or purple stop nobody chose (research
//! top-20 #1). A palette entry or a colour literal within 2 `deltaE_OK` (x100) of one of the twelve
//! stops fires; `[decisions] accent` records that the purple is the brand and silences the rule.
//! Advisory: real purple brands exist.

// frob:ticket 01M4CXT4Z45GR5QE71B10FRR8N

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::site_path;
use crate::slop;

/// A palette or stylesheet colour that is a Tailwind indigo, violet or purple 400-700 stop with no declared accent decision.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SLOP001",
    slug = "default-palette-accent",
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
pub struct Slop001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Slop001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        if slop::decided(spec, "accent") {
            return;
        }
        let stops = slop::default_accent_stops();
        for (name, color) in &spec.palette {
            if let Some(stop) = slop::default_accent_of(*color, &stops) {
                tracing::debug!(%name, stop, "SLOP001: palette entry is a default accent");
                out.fire_in(
                    "crunk.toml",
                    0,
                    format!("palette colour `{name}` is Tailwind {stop}; declare `[decisions] accent` if it is the brand"),
                );
            }
        }
        for sheet in slop::judged_sheets(styles) {
            let path = site_path(spec, &sheet.path);
            for located in sheet.declarations.iter().flat_map(|d| &d.colors) {
                if let Some(stop) = slop::default_accent_of(located.color, &stops) {
                    tracing::debug!(%path, stop, "SLOP001: literal is a default accent");
                    out.fire_in(
                        &path,
                        located.span.0,
                        format!("colour {} is Tailwind {stop}; declare `[decisions] accent` if it is the brand", located.color.to_hex()),
                    );
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

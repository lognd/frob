//! SLOP014: eyebrow chrome (research top-20 #14). A short (at most four words) label in an
//! element marked `uppercase`, `eyebrow`, `kicker` or `overline`, immediately followed by an
//! `h1` or `h2`, in three or more places fires at each. `[decisions] eyebrows` silences it.
//! Advisory: section navigation labels are real.

// frob:ticket 01M4CXT4Z45GR5QE71B10FRR8N

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::site_path;
use crate::slop;

/// Three or more short uppercase kicker labels directly above h1 or h2 headings.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SLOP014",
    slug = "eyebrow-chrome",
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
pub struct Slop014;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Slop014 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        if slop::decided(spec, "eyebrows") {
            return;
        }
        let mut found: Vec<(String, usize)> = Vec::new();
        for sheet in slop::markup_sheets(styles) {
            let path = site_path(spec, &sheet.path);
            let tags = slop::tags(&sheet.source);
            for (i, tag) in tags.iter().enumerate() {
                if tag.closing
                    || !matches!(tag.name, "p" | "span" | "div" | "small")
                    || !slop::attrs_mention(tag, &["uppercase", "eyebrow", "kicker", "overline"])
                {
                    continue;
                }
                let Some((at, text)) = slop::text_after(&sheet.source, tag) else {
                    continue;
                };
                let (Some(close), Some(next)) = (tags.get(i + 1), tags.get(i + 2)) else {
                    continue;
                };
                if close.closing
                    && close.name == tag.name
                    && !next.closing
                    && matches!(next.name, "h1" | "h2")
                    && text.split_whitespace().count() <= 4
                {
                    found.push((path.clone(), at));
                }
            }
        }
        if found.len() >= 3 {
            for (path, at) in found {
                tracing::debug!(%path, "SLOP014: eyebrow above a heading");
                out.fire_in(
                    &path,
                    at,
                    "eyebrow label above a heading; three or more is a pattern",
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

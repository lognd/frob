//! SLOP040: emoji as bullet, icon or nav (research top-20 #40). A pictograph as the first
//! character of an `li`, heading, `button` or `a` text in a JSX source, or at the start of a CSS
//! `content` or `list-style` string, fires. `[decisions] emoji` (a chat app, user content)
//! silences it. Warn: the signal is high precision.

// frob:ticket 01M4CXT4Z45GR5QE71B10FRR8N

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::site_path;
use crate::slop;

/// An emoji at the start of a list item, heading, button or link label, or as a content or list marker.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SLOP040",
    slug = "emoji-as-icon",
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
pub struct Slop040;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Slop040 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        if slop::decided(spec, "emoji") {
            return;
        }
        for sheet in slop::markup_sheets(styles) {
            let path = site_path(spec, &sheet.path);
            for tag in slop::tags(&sheet.source).iter().filter(|t| {
                !t.closing
                    && matches!(
                        t.name,
                        "li" | "h1" | "h2" | "h3" | "h4" | "h5" | "h6" | "button" | "a"
                    )
            }) {
                if let Some((at, text)) = slop::text_after(&sheet.source, tag)
                    && slop::leading_char(text).is_some_and(slop::is_emoji)
                {
                    tracing::debug!(%path, tag = tag.name, "SLOP040: emoji label");
                    out.fire_in(
                        &path,
                        at,
                        format!(
                            "emoji at the start of a `{}` label; use an icon or text",
                            tag.name
                        ),
                    );
                }
            }
        }
        for sheet in slop::judged_sheets(styles) {
            let path = site_path(spec, &sheet.path);
            let marked = sheet.declarations.iter().filter(|d| {
                matches!(
                    d.prop.as_str(),
                    "content" | "list-style" | "list-style-type"
                )
            });
            for decl in marked {
                let lead = decl.value.trim().trim_start_matches(['"', '\'']);
                if slop::leading_char(lead).is_some_and(slop::is_emoji) {
                    tracing::debug!(%path, prop = %decl.prop, "SLOP040: emoji marker");
                    out.fire_in(
                        &path,
                        decl.span.0,
                        format!("emoji used as a `{}` marker", decl.prop),
                    );
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

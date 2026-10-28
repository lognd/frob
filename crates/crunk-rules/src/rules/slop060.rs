//! SLOP060: buzzword density (research top-20 #60). The literal text of a JSX source is scored
//! against the dated tell list `SLOP060.toml` (seamless, unlock, elevate, supercharge, world-class, ...); at least three
//! hits and at least three hits per 100 words (over 30 words or more) fires once per source,
//! never on a single hit. `[decisions] voice` (a tone file that allows them) silences it. Advisory.

// frob:ticket 01M4CXT4Z45GR5QE71B10FRR8N

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::site_path;
use crate::slop;
use crunk_spec::tells::TellList;

/// Fewest words of copy worth scoring.
const MIN_WORDS: usize = 30;
/// Fewest hits that count as density (one hit is never a finding).
const MIN_HITS: usize = 3;
/// Hits per 100 words at which the density fires.
const MIN_DENSITY: f64 = 3.0;

/// Marketing buzzwords at three or more per 100 words of a JSX source, with no voice decision.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SLOP060",
    slug = "buzzword-density",
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
pub struct Slop060;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Slop060 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        if slop::decided(spec, "voice") {
            return;
        }
        let lexicon = match TellList::load("SLOP060", &spec.root) {
            Ok(list) => list.terms(),
            Err(e) => {
                tracing::warn!(error = %e, "SLOP060: tell list unusable, rule skipped");
                return;
            }
        };
        for sheet in slop::markup_sheets(styles) {
            let path = site_path(spec, &sheet.path);
            let mut copy = String::new();
            let mut first = None;
            for tag in slop::tags(&sheet.source).iter().filter(|t| !t.closing) {
                if let Some((at, text)) = slop::text_after(&sheet.source, tag) {
                    first.get_or_insert(at);
                    copy.push_str(&text.to_lowercase());
                    copy.push(' ');
                }
            }
            let words = copy.split_whitespace().count();
            let hits: usize = lexicon
                .iter()
                .map(|w| copy.matches(w.as_str()).count())
                .sum();
            #[allow(clippy::cast_precision_loss, reason = "word counts of one file")]
            let density = hits as f64 * 100.0 / words.max(1) as f64;
            if words >= MIN_WORDS && hits >= MIN_HITS && density >= MIN_DENSITY {
                tracing::debug!(%path, words, hits, density, "SLOP060: buzzword density");
                out.fire_in(
                    &path,
                    first.unwrap_or(0),
                    format!("{hits} buzzwords in {words} words ({density:.1} per 100); say what the product does"),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

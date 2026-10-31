//! CRAFT003: a scene has one moment. A long scene that never says what the user should notice
//! first, or a scene that names several, has no focal point. A `data-moment` attribute (any value
//! but `false`) marks the element that is the scene's moment. More than one marked element fires
//! once at the second; a scene of at least 30 elements with none fires once at its first element.
//! Short scenes are quiet (a button needs no moment), as is a project with no scene documents.
//! Advisory.

// frob:ticket 01M5HM3WE0PDTYAJ31B2C2A8A0

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_scene_doc_inputs};

/// The attribute that marks a scene's moment.
pub const MOMENT_ATTR: &str = "data-moment";

/// How many elements make a scene long enough to need a declared moment.
pub const LONG_SCENE_ELEMENTS: usize = 30;

/// A scene with no declared moment, or with several.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CRAFT003",
    slug = "one-moment",
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
pub struct Craft003;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Craft003 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.scene_docs() else {
            return;
        };
        for file in &facts.files {
            let elements = &file.doc.elements;
            let moments: Vec<usize> = elements
                .iter()
                .filter(|el| {
                    el.attributes.iter().any(|(name, value)| {
                        name == MOMENT_ATTR && !value.eq_ignore_ascii_case("false")
                    })
                })
                .map(|el| el.offset)
                .collect();
            if let Some(&second) = moments.get(1) {
                tracing::debug!(path = %file.path, count = moments.len(), "CRAFT003: several moments");
                out.fire_in(
                    &file.path,
                    second,
                    format!(
                        "{} elements carry `{MOMENT_ATTR}`: a scene has one moment, so keep it on \
                         the element the eye should land on first",
                        moments.len()
                    ),
                );
            } else if moments.is_empty() && elements.len() >= LONG_SCENE_ELEMENTS {
                tracing::debug!(path = %file.path, elements = elements.len(), "CRAFT003: no moment");
                out.fire_in(
                    &file.path,
                    elements.first().map_or(0, |el| el.offset),
                    format!(
                        "a scene of {} elements declares no moment: mark the element the eye \
                         should land on first with `{MOMENT_ATTR}`",
                        elements.len()
                    ),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_doc_inputs(host)
    }
}

//! CRAFT009: a scene shows real content, not a stand-in. CONTENT001 and CONTENT003 judge whether
//! copy is referenced and whether the key exists; CRAFT009 judges what is behind the reference.
//! It fires for a `data-copy*` attribute with an empty key, for a defined content key whose text
//! is blank or placeholder (lorem ipsum, to-do, TBD, placeholder, xxx), for an `<img>` with no
//! `alt` text (or `data-copy-alt` key), and for an `<img>` with no `data-provenance` naming where
//! the picture came from. Unknown keys stay with CONTENT003 and literal copy with CONTENT001.
//! Advisory; a project with no scene documents is not judged.

// frob:ticket 01M5HM3WE0PDTYAJ31B2C2A8A0

use gob_rules::{Out, RepoRule, rule};

use crate::content_files::{COPY_ATTR, copy_refs};
use crate::craft::has_word;
use crate::host::{CrunkHost, missing_scene_doc_inputs};

/// The attribute that records where an image came from.
pub const PROVENANCE_ATTR: &str = "data-provenance";

/// The words that mark text as a stand-in.
const PLACEHOLDER_WORDS: &[&str] = &["lorem", "ipsum", "todo", "tbd", "placeholder", "xxx"];

/// Whether `text` is blank or a stand-in.
fn is_stand_in(text: &str) -> bool {
    let lower = text.to_ascii_lowercase();
    lower.trim().is_empty() || PLACEHOLDER_WORDS.iter().any(|w| has_word(&lower, w))
}

/// A scene referencing empty or placeholder content, or an image with no alt or provenance.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CRAFT009",
    slug = "real-content",
    severity = Advisory,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Craft009;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Craft009 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        if let Some(content) = host.content() {
            for file in &content.files {
                for key in &file.content.keys {
                    if is_stand_in(&key.text) {
                        tracing::debug!(path = %file.path, key = %key.id, "CRAFT009: stand-in copy");
                        out.fire_in(
                            &file.path,
                            file.offset_of_key(&key.id),
                            format!(
                                "content key `{}` is blank or placeholder text: write the real copy",
                                key.id
                            ),
                        );
                    }
                }
            }
        }
        let Some(facts) = host.scene_docs() else {
            return;
        };
        for file in &facts.files {
            for copy in copy_refs(file).iter().filter(|c| c.key.is_empty()) {
                tracing::debug!(path = %file.path, line = copy.line, "CRAFT009: empty copy key");
                out.fire_in(
                    &file.path,
                    copy.offset,
                    format!(
                        "an empty `{COPY_ATTR}` key on line {}: name the content key",
                        copy.line
                    ),
                );
            }
            for el in file
                .doc
                .elements
                .iter()
                .filter(|e| e.tag.eq_ignore_ascii_case("img"))
            {
                let attr = |name: &str| {
                    el.attributes
                        .iter()
                        .find(|(n, _)| n == name)
                        .map(|(_, v)| v.as_str())
                };
                if attr("alt").is_none() && attr("data-copy-alt").is_none() {
                    tracing::debug!(path = %file.path, line = el.line, "CRAFT009: image without alt");
                    out.fire_in(
                        &file.path,
                        el.offset,
                        format!("{} has no `alt`: describe the picture, or give `alt=\"\"` if decorative", file.element_label(el.offset)),
                    );
                }
                if attr(PROVENANCE_ATTR).is_none_or(|v| v.trim().is_empty()) {
                    tracing::debug!(path = %file.path, line = el.line, "CRAFT009: image without provenance");
                    out.fire_in(
                        &file.path,
                        el.offset,
                        format!(
                            "{} has no `{PROVENANCE_ATTR}`: say where the picture came from (a \
                             shot, a licence or a source), so a stand-in cannot ship",
                            file.element_label(el.offset)
                        ),
                    );
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_doc_inputs(host)
    }
}

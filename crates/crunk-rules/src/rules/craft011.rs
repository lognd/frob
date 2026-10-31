//! CRAFT011: an icon beside a label is aligned by its optics. In a scene, a container holding an
//! icon (an `svg` or `img`, a `data-icon` attribute or a class naming an icon) next to a label
//! (text or a `data-copy` key) that is laid out with flex but states no `align-items` (inline, or
//! an `items-*` utility class) lets the icon sit on the text baseline, a few pixels off centre.
//! Containers whose flex layout cannot be seen from the markup are not judged. Advisory.

// frob:ticket 01M5HM3WE0PDTYAJ31B2C2A8A0

use crunk_scene::SceneElement;
use gob_rules::{Out, RepoRule, rule};

use crate::content_files::COPY_ATTR;
use crate::host::{CrunkHost, missing_scene_doc_inputs};

/// The value of attribute `name` on `el`, lowercased.
fn attr(el: &SceneElement, name: &str) -> Option<String> {
    el.attributes
        .iter()
        .find(|(n, _)| n == name)
        .map(|(_, v)| v.to_ascii_lowercase())
}

/// Whether `el` is an icon.
fn is_icon(el: &SceneElement) -> bool {
    let tag = el.tag.to_ascii_lowercase();
    tag == "svg"
        || tag == "img"
        || attr(el, "data-icon").is_some()
        || attr(el, "class").is_some_and(|c| c.contains("icon"))
}

/// Whether `el` carries a label of its own.
fn has_label(el: &SceneElement) -> bool {
    !el.text.is_empty() || attr(el, COPY_ATTR).is_some()
}

/// An inline `style` with `property` set, whitespace ignored.
fn style_sets(el: &SceneElement, property: &str) -> Option<String> {
    let style: String = attr(el, "style")?.split_whitespace().collect();
    style
        .split(';')
        .find_map(|d| d.strip_prefix(&format!("{property}:")).map(str::to_owned))
}

/// Whether a flex layout shows on `el` (an inline style or a utility class).
fn is_flex(el: &SceneElement) -> bool {
    let inline = style_sets(el, "display").is_some_and(|v| v.ends_with("flex"));
    inline
        || attr(el, "class").is_some_and(|c| {
            c.split_whitespace()
                .any(|t| t == "flex" || t == "inline-flex")
        })
}

/// Whether `el` states how its children align on the cross axis.
fn is_aligned(el: &SceneElement) -> bool {
    style_sets(el, "align-items").is_some()
        || style_sets(el, "place-items").is_some()
        || attr(el, "class").is_some_and(|c| {
            c.split_whitespace()
                .any(|t| t.starts_with("items-") || t.starts_with("place-items-"))
        })
}

/// A flex container of an icon and a label with no cross-axis alignment.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CRAFT011",
    slug = "optical-alignment",
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
pub struct Craft011;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Craft011 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.scene_docs() else {
            return;
        };
        for file in &facts.files {
            let elements = &file.doc.elements;
            for (at, container) in elements.iter().enumerate() {
                if !is_flex(container) || is_aligned(container) {
                    continue;
                }
                let children: Vec<&SceneElement> =
                    elements.iter().filter(|e| e.parent == Some(at)).collect();
                let icon = children.iter().any(|c| is_icon(c));
                let label = !container.text.is_empty()
                    || children.iter().any(|c| !is_icon(c) && has_label(c));
                if icon && label {
                    tracing::debug!(path = %file.path, line = container.line, "CRAFT011: icon and label unaligned");
                    out.fire_in(
                        &file.path,
                        container.offset,
                        format!(
                            "{} lays an icon beside a label with flex but sets no `align-items`: \
                             add `align-items: center` (or `items-center`) so the icon sits on the \
                             label's optical centre",
                            file.element_label(container.offset)
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

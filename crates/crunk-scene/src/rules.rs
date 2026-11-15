//! Style-rule association: which scene elements each `<style>` rule selector matches, and which
//! `@media` at-rule a rule sits in. Supported selectors are the minimal subset type, class, id and
//! the descendant combinator (whitespace), plus selector lists (`a, b`) and `*`. Everything else
//! (child/sibling combinators, attribute selectors, pseudo-classes and pseudo-elements) is
//! unsupported: such a rule is exposed with `supported == false` and matches nothing.

// frob:ticket 01M5XDN67KE9HCKFSX3CDS3X1G

use crate::doc::SceneElement;

/// One compound selector: an optional type (`None` for `*` or absent), an optional id and classes.
#[derive(Debug, Default, PartialEq, Eq)]
struct Compound {
    tag: Option<String>,
    id: Option<String>,
    classes: Vec<String>,
}

/// Parse one compound such as `div.card#main`; `None` when it uses anything unsupported.
fn parse_compound(text: &str) -> Option<Compound> {
    let mut out = Compound::default();
    let mut rest = text;
    if !rest.starts_with(['.', '#']) {
        let end = rest.find(['.', '#']).unwrap_or(rest.len());
        let (tag, tail) = rest.split_at(end);
        if tag != "*" {
            if !is_ident(tag) {
                return None;
            }
            out.tag = Some(tag.to_owned());
        }
        rest = tail;
    }
    while let Some(sigil) = rest.chars().next() {
        let body = &rest[1..];
        let end = body.find(['.', '#']).unwrap_or(body.len());
        let (name, tail) = body.split_at(end);
        if !is_ident(name) {
            return None;
        }
        match sigil {
            '.' => out.classes.push(name.to_owned()),
            '#' if out.id.is_none() => out.id = Some(name.to_owned()),
            _ => return None,
        }
        rest = tail;
    }
    Some(out)
}

/// Whether `s` is a plain CSS identifier (letters, digits, `-`, `_`; not empty).
fn is_ident(s: &str) -> bool {
    !s.is_empty()
        && s.chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '-' | '_'))
}

/// Parse a descendant chain (`ul li.item`), outermost first; `None` when unsupported.
fn parse_chain(text: &str) -> Option<Vec<Compound>> {
    let chain: Option<Vec<Compound>> = text.split_whitespace().map(parse_compound).collect();
    chain.filter(|c| !c.is_empty())
}

/// An element's attribute value by name.
fn attr<'a>(el: &'a SceneElement, name: &str) -> Option<&'a str> {
    el.attributes
        .iter()
        .find(|(n, _)| n == name)
        .map(|(_, v)| v.as_str())
}

/// Whether `el` satisfies one compound.
fn compound_matches(el: &SceneElement, c: &Compound) -> bool {
    c.tag
        .as_deref()
        .is_none_or(|t| el.tag.eq_ignore_ascii_case(t))
        && c.id.as_deref().is_none_or(|i| attr(el, "id") == Some(i))
        && c.classes
            .iter()
            .all(|k| attr(el, "class").is_some_and(|v| v.split_whitespace().any(|w| w == k)))
}

/// Whether `elements[at]` matches the descendant chain (last compound on the element itself).
fn chain_matches(elements: &[SceneElement], at: usize, chain: &[Compound]) -> bool {
    let Some((last, outer)) = chain.split_last() else {
        return true;
    };
    if !compound_matches(&elements[at], last) {
        return false;
    }
    let mut need = outer.iter().rev();
    let mut want = need.next();
    let mut up = elements[at].parent;
    while let (Some(w), Some(p)) = (want, up) {
        if compound_matches(&elements[p], w) {
            want = need.next();
        }
        up = elements[p].parent;
    }
    want.is_none()
}

/// The element indices a selector list matches, ascending; `None` when any selector in the list
/// is outside the supported subset.
pub(crate) fn match_selector(elements: &[SceneElement], selector: &str) -> Option<Vec<usize>> {
    let chains: Option<Vec<Vec<Compound>>> =
        selector.split(',').map(|s| parse_chain(s.trim())).collect();
    let chains = chains?;
    Some(
        (0..elements.len())
            .filter(|&i| chains.iter().any(|c| chain_matches(elements, i, c)))
            .collect(),
    )
}

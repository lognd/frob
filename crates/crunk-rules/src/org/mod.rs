//! The class-name judgments ORG002 and ORG003 share (port of `crunk/rules/_org.py`): BEM segment
//! splitting, the three `class_case` grammars and the component prefix test.
//!
//! The grammars are hand-written character tests over an already extracted class name; nothing here
//! reads raw CSS, so no regular expression is needed.

// frob:ticket 01M43ATBPPR5QCY0CSPPTNEDQ0

use crunk_spec::table::ClassCase;

/// Split a BEM class name on its `__` and `--` separators into the parts that are judged on their
/// own (block, element, modifier); empty parts, left by a leading or doubled separator, are dropped.
pub fn bem_segments(name: &str) -> Vec<&str> {
    let mut segments = Vec::new();
    let mut start = 0;
    let mut chars = name.char_indices().peekable();
    while let Some((at, c)) = chars.next() {
        let separator = (c == '_' || c == '-') && chars.peek().is_some_and(|&(_, next)| next == c);
        if separator {
            segments.push(&name[start..at]);
            chars.next();
            start = at + 2;
        }
    }
    segments.push(&name[start..]);
    segments.retain(|s| !s.is_empty());
    segments
}

fn words_ok(segment: &str, joiner: char) -> bool {
    !segment.is_empty()
        && segment.split(joiner).all(|word| {
            !word.is_empty()
                && word
                    .chars()
                    .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit())
        })
}

fn camel_ok(segment: &str) -> bool {
    let mut chars = segment.chars();
    chars.next().is_some_and(|c| c.is_ascii_lowercase()) && chars.all(|c| c.is_ascii_alphanumeric())
}

/// True when `segment` (one BEM part) is written in `class_case`.
pub fn segment_case_ok(segment: &str, class_case: ClassCase) -> bool {
    match class_case {
        ClassCase::Kebab => words_ok(segment, '-'),
        ClassCase::Snake => words_ok(segment, '_'),
        ClassCase::Camel => camel_ok(segment),
    }
}

/// True when every BEM segment of the class `name` is written in `class_case`.
pub fn case_ok(name: &str, class_case: ClassCase) -> bool {
    bem_segments(name)
        .into_iter()
        .all(|segment| segment_case_ok(segment, class_case))
}

/// True when the class `name` is the component `component`, or one of its `component__element` or
/// `component--modifier` forms.
pub fn carries_prefix(name: &str, component: &str) -> bool {
    name == component
        || name
            .strip_prefix(component)
            .is_some_and(|rest| rest.starts_with("__") || rest.starts_with("--"))
}

/// The lowercase name of `class_case` as `crunk.toml` spells it.
pub const fn case_name(class_case: ClassCase) -> &'static str {
    match class_case {
        ClassCase::Kebab => "kebab",
        ClassCase::Snake => "snake",
        ClassCase::Camel => "camel",
    }
}

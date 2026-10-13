//! Minimal slash-aware glob: `*` within a segment, `**` across segments.

/// Match `path` against `pattern`.
pub(super) fn matches(pattern: &str, path: &str) -> bool {
    let p: Vec<&str> = pattern.split('/').collect();
    let s: Vec<&str> = path.split('/').collect();
    segs(&p, &s)
}

fn segs(p: &[&str], s: &[&str]) -> bool {
    match p.split_first() {
        None => s.is_empty(),
        Some((&"**", rest)) => (0..=s.len()).any(|i| segs(rest, &s[i..])),
        Some((seg, rest)) => s
            .split_first()
            .is_some_and(|(h, t)| seg_match(seg, h) && segs(rest, t)),
    }
}

fn seg_match(p: &str, s: &str) -> bool {
    let (p, s): (Vec<char>, Vec<char>) = (p.chars().collect(), s.chars().collect());
    go(&p, &s)
}

fn go(p: &[char], s: &[char]) -> bool {
    match p.split_first() {
        None => s.is_empty(),
        Some(('*', rest)) => (0..=s.len()).any(|i| go(rest, &s[i..])),
        Some((c, rest)) => s.split_first().is_some_and(|(h, t)| h == c && go(rest, t)),
    }
}

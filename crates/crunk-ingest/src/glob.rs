//! Python `fnmatch` semantics for `[org] entry`, `[org] ignore` and `[jsx] globs`.
//!
//! `*` crosses `/` (unlike a gitignore glob), and a `**/` segment also matches zero
//! directories, so the conventional `src/**/*.tsx` matches a flat `src/A.tsx`. Existing
//! `crunk.toml` files were written against these semantics, so they are kept.

// frob:ticket 01M43ARY91XZ35DN9SCHRHS033

/// Whether `name` matches the `fnmatch` pattern `pattern` (case-sensitive).
pub fn fnmatch(name: &str, pattern: &str) -> bool {
    let n: Vec<char> = name.chars().collect();
    let p: Vec<char> = pattern.chars().collect();
    matches_from(&n, &p)
}

fn matches_from(n: &[char], p: &[char]) -> bool {
    let Some((&head, rest)) = p.split_first() else {
        return n.is_empty();
    };
    match head {
        '*' => (0..=n.len()).any(|k| matches_from(&n[k..], rest)),
        '?' => !n.is_empty() && matches_from(&n[1..], rest),
        '[' => match class(p) {
            Some((negated, members, used)) => {
                let Some((&c, tail)) = n.split_first() else {
                    return false;
                };
                let hit = members.iter().any(|&(lo, hi)| lo <= c && c <= hi);
                hit != negated && matches_from(tail, &p[used..])
            }
            None => n.first() == Some(&'[') && matches_from(&n[1..], rest),
        },
        c => n.first() == Some(&c) && matches_from(&n[1..], rest),
    }
}

/// Parse a `[...]` class at the start of `p`: negation, `(lo, hi)` members and chars consumed.
#[allow(
    clippy::type_complexity,
    reason = "a private parse helper with one caller"
)]
fn class(p: &[char]) -> Option<(bool, Vec<(char, char)>, usize)> {
    let mut j = 1;
    let negated = p.get(j) == Some(&'!');
    if negated {
        j += 1;
    }
    let body_start = j;
    if p.get(j) == Some(&']') {
        j += 1;
    }
    while p.get(j).is_some_and(|&c| c != ']') {
        j += 1;
    }
    p.get(j)?;
    let body = &p[body_start..j];
    let mut members = Vec::new();
    let mut i = 0;
    while i < body.len() {
        if body.get(i + 1) == Some(&'-') && i + 2 < body.len() {
            members.push((body[i], body[i + 2]));
            i += 3;
        } else {
            members.push((body[i], body[i]));
            i += 1;
        }
    }
    Some((negated, members, j + 1))
}

/// `fnmatch` where each `**/` may also match zero directories.
pub fn glob_match(relative_posix: &str, pattern: &str) -> bool {
    if fnmatch(relative_posix, pattern) {
        return true;
    }
    let mut from = 0;
    while let Some(k) = pattern[from..].find("**/") {
        let idx = from + k;
        let elided = format!("{}{}", &pattern[..idx], &pattern[idx + 3..]);
        if glob_match(relative_posix, &elided) {
            return true;
        }
        from = idx + 1;
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-ingest/src/glob.rs::fnmatch
    #[test]
    fn fnmatch_matches_python() {
        assert!(fnmatch("a/b/c.css", "*.css"));
        assert!(fnmatch("abc", "a?c"));
        assert!(fnmatch("b", "[a-c]"));
        assert!(!fnmatch("d", "[a-c]"));
        assert!(fnmatch("d", "[!a-c]"));
        assert!(fnmatch("[", "["));
        assert!(!fnmatch("A.css", "a.css"));
    }

    // frob:tests crates/crunk-ingest/src/glob.rs::glob_match
    #[test]
    fn double_star_slash_matches_zero_directories() {
        assert!(glob_match("src/A.tsx", "src/**/*.tsx"));
        assert!(glob_match("src/x/y/A.tsx", "src/**/*.tsx"));
        assert!(!glob_match("lib/A.tsx", "src/**/*.tsx"));
    }
}

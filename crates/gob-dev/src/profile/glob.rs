//! The `--only` filter: `*` and `?` wildcards over a leaf command name.

/// Whether `text` matches `pattern`, where `*` matches any run of characters and `?` one.
pub fn matches(pattern: &str, text: &str) -> bool {
    let (p, t): (Vec<char>, Vec<char>) = (pattern.chars().collect(), text.chars().collect());
    let (mut pi, mut ti) = (0, 0);
    let mut star: Option<(usize, usize)> = None;
    while ti < t.len() {
        if pi < p.len() && (p[pi] == '?' || p[pi] == t[ti]) {
            pi += 1;
            ti += 1;
        } else if pi < p.len() && p[pi] == '*' {
            star = Some((pi, ti));
            pi += 1;
        } else if let Some((sp, st)) = star {
            pi = sp + 1;
            ti = st + 1;
            star = Some((sp, st + 1));
        } else {
            return false;
        }
    }
    p[pi..].iter().all(|c| *c == '*')
}

#[cfg(test)]
mod tests {
    use super::matches;

    // frob:tests crates/gob-dev/src/profile/glob.rs::matches
    #[test]
    fn wildcards() {
        assert!(matches("frob ticket *", "frob ticket show"));
        assert!(matches("*check", "grimble check"));
        assert!(matches("frob ?ck", "frob ack"));
        assert!(matches("*", ""));
        assert!(!matches("frob ticket", "frob ticket show"));
        assert!(!matches("frob t*w", "frob ticket list"));
    }
}

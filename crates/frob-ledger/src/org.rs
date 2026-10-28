//! Derived organisation of a ticket: the crates its scope touches and the products they belong to.
// frob:ticket 5E5N62X

/// True when `s` contains a glob metacharacter.
fn has_glob(s: &str) -> bool {
    s.contains(['*', '?', '[', ']', '{', '}'])
}

/// The crate names named by `scope` globs of the form `crates/<name>/...`, sorted and deduplicated.
pub fn crates_of(scope: &[String]) -> Vec<String> {
    let mut out: Vec<String> = scope
        .iter()
        .filter_map(|g| {
            let name = g.trim_start_matches("./").strip_prefix("crates/")?;
            let name = name.split('/').next()?;
            (!name.is_empty() && !has_glob(name)).then(|| name.to_owned())
        })
        .collect();
    out.sort();
    out.dedup();
    tracing::trace!(?scope, crates = ?out, "derived crates from scope");
    out
}

/// The product a crate belongs to: its name up to the first `-` (`frob-ledger` is `frob`).
pub fn product_of(krate: &str) -> &str {
    krate.split('-').next().unwrap_or(krate)
}

/// The sorted, deduplicated products of `crates`.
pub fn products_of(crates: &[String]) -> Vec<String> {
    let mut out: Vec<String> = crates.iter().map(|c| product_of(c).to_owned()).collect();
    out.sort();
    out.dedup();
    out
}

/// Join names into the comma-separated column form stored in the index.
pub(crate) fn join(names: &[String]) -> String {
    names.join(",")
}

/// Split the column form back into names.
pub(crate) fn split(col: &str) -> Vec<String> {
    col.split(',')
        .filter(|s| !s.is_empty())
        .map(str::to_owned)
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn v(xs: &[&str]) -> Vec<String> {
        xs.iter().map(|s| (*s).to_owned()).collect()
    }

    // frob:tests crates_of
    #[test]
    fn crates_come_from_crate_globs_only() {
        let got = crates_of(&v(&[
            "crates/frob-ledger/**",
            "crates/frob-ledger/src/a.rs",
            "crates/gob-*/**",
            "docs/**",
            "crates/crunk/x",
        ]));
        assert_eq!(got, v(&["crunk", "frob-ledger"]));
    }

    // frob:tests products_of
    #[test]
    fn products_are_the_name_prefix() {
        let got = products_of(&v(&["frob-ledger", "frob", "gob-path", "crunk"]));
        assert_eq!(got, v(&["crunk", "frob", "gob"]));
    }

    // frob:tests split
    #[test]
    fn column_round_trips() {
        let names = v(&["a", "b-c"]);
        assert_eq!(split(&join(&names)), names);
        assert!(split("").is_empty());
    }
}

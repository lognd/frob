//! The wire form of a TypeScript or JavaScript import target, shared by the folder (which writes it into
//! [`crate::ImportEdge`] and [`crate::UseBinding`]) and the module graph (which reads it back).
//!
//! `<spec>` is a static import, `may:<spec>` a literal dynamic `import("..")` or a conditional `require`,
//! `unknown:<text>` an import whose specifier is computed. A use binding appends `#<member>`: the imported
//! name, `default`, or `*` for a whole module (namespace import, `require`, `export *`). An empty
//! specifier names the file itself (`export { a as b }` is the binding `b` -> `#a`).

// frob:ticket 01M43ARXMH7RJ63G8096KKJF80

/// How certain an import is to run (the status of its module edge).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum ImportMode {
    /// An ESM `import`, a re-export or an unconditional top-level `require`: Must.
    Static,
    /// A dynamic `import("lit")` or a `require` under a condition or in a function: May.
    May,
    /// The specifier is computed: Unknown, never dropped.
    Unknown,
}

const MAY: &str = "may:";
const UNKNOWN: &str = "unknown:";

/// A decoded import target.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct ImportRef<'a> {
    /// How certain the import is.
    pub mode: ImportMode,
    /// The module specifier as written, or the expression text of an `Unknown` import.
    pub spec: &'a str,
    /// The imported member of a use binding; `None` for a bare edge.
    pub member: Option<&'a str>,
}

/// The wire string of an import edge to `spec`.
pub(crate) fn encode_edge(mode: ImportMode, spec: &str) -> String {
    match mode {
        ImportMode::Static => spec.to_owned(),
        ImportMode::May => format!("{MAY}{spec}"),
        ImportMode::Unknown => format!("{UNKNOWN}{spec}"),
    }
}

/// The wire string of a use binding of `member` from `spec`.
pub(crate) fn encode_use(mode: ImportMode, spec: &str, member: &str) -> String {
    format!("{}#{member}", encode_edge(mode, spec))
}

/// Decodes an edge target.
pub(crate) fn decode_edge(target: &str) -> ImportRef<'_> {
    if let Some(s) = target.strip_prefix(MAY) {
        ImportRef {
            mode: ImportMode::May,
            spec: s,
            member: None,
        }
    } else if let Some(s) = target.strip_prefix(UNKNOWN) {
        ImportRef {
            mode: ImportMode::Unknown,
            spec: s,
            member: None,
        }
    } else {
        ImportRef {
            mode: ImportMode::Static,
            spec: target,
            member: None,
        }
    }
}

/// Decodes a use-binding target; a target without `#` has no member.
pub(crate) fn decode_use(target: &str) -> ImportRef<'_> {
    let (head, member) = match target.rsplit_once('#') {
        Some((h, m)) => (h, Some(m)),
        None => (target, None),
    };
    ImportRef {
        member,
        ..decode_edge(head)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    // frob:tests crates/gob-symbols/src/typescript/imports.rs::decode_use
    fn use_targets_round_trip_with_hashes_in_the_specifier() {
        for (mode, spec, member) in [
            (ImportMode::Static, "./a", "default"),
            (ImportMode::May, "../b/c", "*"),
            (ImportMode::Static, "#internal/x", "run"),
            (ImportMode::Static, "", "local"),
        ] {
            let wire = encode_use(mode, spec, member);
            let r = decode_use(&wire);
            assert_eq!((r.mode, r.spec, r.member), (mode, spec, Some(member)));
        }
    }

    #[test]
    // frob:tests crates/gob-symbols/src/typescript/imports.rs::decode_edge
    fn edges_round_trip() {
        for (mode, spec) in [
            (ImportMode::Static, "react"),
            (ImportMode::May, "./lazy"),
            (ImportMode::Unknown, "`./p/${x}`"),
        ] {
            let wire = encode_edge(mode, spec);
            let r = decode_edge(&wire);
            assert_eq!((r.mode, r.spec, r.member), (mode, spec, None));
        }
    }
}

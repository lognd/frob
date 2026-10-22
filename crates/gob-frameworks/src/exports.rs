//! The export lists of a TypeScript or JavaScript module read from its text: `export { a as b }`,
//! `export { a } from "m"` and `export * from "m"`. The folder binds re-exports for the module graph but not
//! a local `export { a as b }`, and an adapter needs the exported names of both.

// frob:ticket 01M48EFBCF70PK5KGS0PDZD40N

use tracing::trace;

/// One exported name of an export list.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct ExportSpec {
    /// The name in the exporting module (the member of `from`), or `*` for a star re-export.
    pub local: String,
    /// The name it is exported as (`*` for `export * from`).
    pub exported: String,
    /// The module specifier of a re-export.
    pub from: Option<String>,
}

/// The string literal at the start of `s` (after whitespace), without quotes.
fn quoted(s: &str) -> Option<(String, &str)> {
    let s = s.trim_start();
    let q = s.chars().next().filter(|c| matches!(c, '"' | '\''))?;
    let body = &s[1..];
    let end = body.find(q)?;
    Some((body[..end].to_owned(), &body[end + 1..]))
}

/// A specifier name, unquoted.
fn name(s: &str) -> String {
    s.trim().trim_matches(['"', '\'']).to_owned()
}

/// The specifiers of the export list `list` (the text between the braces), type-only ones left out.
fn specifiers(list: &str, from: Option<&str>) -> Vec<ExportSpec> {
    list.split(',')
        .filter_map(|raw| {
            let raw = raw.trim();
            if raw.is_empty() || raw.starts_with("type ") {
                return None;
            }
            let (local, exported) = match raw.split_once(" as ") {
                Some((l, e)) => (name(l), name(e)),
                None => (name(raw), name(raw)),
            };
            Some(ExportSpec {
                local,
                exported,
                from: from.map(str::to_owned),
            })
        })
        .collect()
}

/// The export lists of `text`, in source order: only statements that start a line are read.
pub(crate) fn export_specs(text: &str) -> Vec<ExportSpec> {
    let mut out = Vec::new();
    for (at, line) in text
        .match_indices('\n')
        .map(|(i, _)| i + 1)
        .chain([0])
        .map(|i| (i, &text[i..]))
    {
        let _ = at;
        let Some(rest) = line.trim_start().strip_prefix("export") else {
            continue;
        };
        let rest = rest.trim_start();
        if let Some(body) = rest.strip_prefix('{') {
            let Some((list, after)) = body.split_once('}') else {
                continue;
            };
            let from = after
                .trim_start()
                .strip_prefix("from")
                .and_then(|t| quoted(t))
                .map(|(s, _)| s);
            out.extend(specifiers(list, from.as_deref()));
        } else if let Some(star) = rest.strip_prefix('*') {
            let star = star.trim_start();
            let (exported, star) = match star.strip_prefix("as ") {
                Some(r) => {
                    let r = r.trim_start();
                    let end = r.find(char::is_whitespace).unwrap_or(r.len());
                    (name(&r[..end]), &r[end..])
                }
                None => ("*".to_owned(), star),
            };
            if let Some((spec, _)) = star
                .trim_start()
                .strip_prefix("from")
                .and_then(|t| quoted(t))
            {
                out.push(ExportSpec {
                    local: "*".to_owned(),
                    exported,
                    from: Some(spec),
                });
            }
        }
    }
    trace!(specs = out.len(), "export lists read");
    out
}

/// Source extensions tried for a module specifier without one.
const MODULE_EXTENSIONS: [&str; 4] = ["ts", "tsx", "js", "jsx"];

/// `rel` (a relative path, `./` and `../` allowed) joined to the directory `dir` with dot segments removed.
///
/// `None` when `rel` climbs above the repository root.
pub(crate) fn normalize(dir: &str, rel: &str) -> Option<String> {
    let mut parts: Vec<&str> = dir.split('/').filter(|p| !p.is_empty()).collect();
    for seg in rel.split('/') {
        match seg {
            "" | "." => {}
            ".." => {
                parts.pop()?;
            }
            other => parts.push(other),
        }
    }
    Some(parts.join("/"))
}

/// The file paths a relative module specifier `spec` written in `from` may stand for, best first.
///
/// Empty for a bare specifier (a package). A `.js` ending also names the `.ts` file it compiles from.
pub(crate) fn module_candidates(from: &str, spec: &str) -> Vec<String> {
    if !spec.starts_with('.') {
        return Vec::new();
    }
    let dir = from.rsplit_once('/').map_or("", |(d, _)| d);
    let Some(base) = normalize(dir, spec) else {
        return Vec::new();
    };
    let mut out = vec![base.clone()];
    if let Some(stem) = base
        .strip_suffix(".js")
        .or_else(|| base.strip_suffix(".jsx"))
    {
        out.extend(MODULE_EXTENSIONS.iter().map(|e| format!("{stem}.{e}")));
    }
    out.extend(MODULE_EXTENSIONS.iter().map(|e| format!("{base}.{e}")));
    out.extend(
        MODULE_EXTENSIONS
            .iter()
            .map(|e| format!("{base}/index.{e}")),
    );
    out
}

#[cfg(test)]
mod tests {
    use super::{ExportSpec, export_specs, module_candidates, normalize};

    #[test]
    // frob:tests crates/gob-frameworks/src/exports.rs::normalize
    fn dot_segments_are_removed_and_the_root_cannot_be_left() {
        assert_eq!(
            normalize("apps/a/app", "./x.tsx").as_deref(),
            Some("apps/a/app/x.tsx")
        );
        assert_eq!(
            normalize("apps/a/app", "../b/./y").as_deref(),
            Some("apps/a/b/y")
        );
        assert_eq!(normalize("a", "../../x"), None);
    }

    #[test]
    // frob:tests crates/gob-frameworks/src/exports.rs::module_candidates
    fn a_specifier_expands_to_files_and_index_files_but_a_package_does_not() {
        let c = module_candidates("src/a/route.ts", "../h");
        assert_eq!(c[0], "src/h");
        assert!(c.contains(&"src/h.ts".to_owned()));
        assert!(c.contains(&"src/h/index.tsx".to_owned()));
        assert!(module_candidates("src/a.ts", "some-pkg").is_empty());
        assert!(module_candidates("src/a.ts", "./h.js").contains(&"src/h.ts".to_owned()));
    }

    fn spec(local: &str, exported: &str, from: Option<&str>) -> ExportSpec {
        ExportSpec {
            local: local.to_owned(),
            exported: exported.to_owned(),
            from: from.map(str::to_owned),
        }
    }

    #[test]
    // frob:tests crates/gob-frameworks/src/exports.rs::export_specs
    fn export_lists_are_read_with_aliases_and_sources() {
        let text = "const a = 1;\nexport { a as default, b };\nexport { GET, X as POST } from './h';\nexport type { T };\nexport { type U, c } from \"m\";\nexport * from './all';\nexport * as ns from './n';\n";
        assert_eq!(
            export_specs(text),
            [
                spec("a", "default", None),
                spec("b", "b", None),
                spec("GET", "GET", Some("./h")),
                spec("X", "POST", Some("./h")),
                spec("c", "c", Some("m")),
                spec("*", "*", Some("./all")),
                spec("*", "ns", Some("./n")),
            ]
        );
    }

    #[test]
    // frob:tests crates/gob-frameworks/src/exports.rs::export_specs
    fn a_statement_in_a_comment_or_a_declaration_is_not_an_export_list() {
        assert!(
            export_specs(
                "// export { a };\n * export { b };\nexport const c = 1;\nexport default x;\n"
            )
            .is_empty()
        );
    }
}

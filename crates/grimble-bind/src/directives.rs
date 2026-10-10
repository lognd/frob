//! Source (a), code side: `grimble:binds` directives in code comments (binding.md 2.1).

// frob:ticket 01M3Z71450ZE377RBK3EG1XSWC

use gob_directives::{Binding, ScanConfig, Scanner};
use gob_languages::Language;

use crate::code::Code;

/// A `grimble:binds` directive and the unit it attaches to.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CodeDirective {
    /// The file the comment is in.
    pub file: String,
    /// Byte range of the directive text.
    pub range: (usize, usize),
    /// The symref text of the target unit (the module unit when the directive binds to the file).
    pub target: String,
    /// The operand: `design:node/cli` or a symref.
    pub operand: String,
    /// The `role=` attribute.
    pub role: Option<String>,
    /// The `via=` attribute.
    pub via: Option<String>,
}

/// Scan every file that mentions `grimble:binds` for its directives.
///
/// Only the languages `gob-directives` can read comments in (Rust, Markdown, TOML) yield
/// directives; a file in another language that mentions one is reported at debug level.
pub fn scan(code: &Code) -> Vec<CodeDirective> {
    let scanner = Scanner::new(&ScanConfig {
        namespaces: vec!["grimble".to_owned()],
        product: "grimble".to_owned(),
    });
    let mut out = Vec::new();
    for f in &code.files {
        let (Some(text), Some(folded)) = (&f.text, f.symbols()) else {
            continue;
        };
        let Some(lang) = Language::detect(&f.path) else {
            tracing::debug!(path = %f.path, "grimble:binds in a language with no comment scanner");
            continue;
        };
        let result = scanner.scan(lang, text, folded);
        for finding in &result.findings {
            tracing::debug!(path = %f.path, message = %finding.message, "directive scan finding");
        }
        for d in result.directives {
            if d.namespace != "grimble" || d.verb != "binds" {
                continue;
            }
            let Some(operand) = d.args.positional.first().map(|t| t.value.clone()) else {
                continue;
            };
            let target = match &d.bound {
                Binding::Symbol(s) => s.to_string(),
                Binding::File => f.path.clone(),
            };
            let range = (
                u32::from(d.span.range.start()) as usize,
                u32::from(d.span.range.end()) as usize,
            );
            out.push(CodeDirective {
                file: f.path.clone(),
                range,
                target,
                operand,
                role: d.args.get("role").map(|t| t.value.clone()),
                via: d.args.get("via").map(|t| t.value.clone()),
            });
        }
    }
    tracing::info!(directives = out.len(), "grimble:binds directives found");
    out
}

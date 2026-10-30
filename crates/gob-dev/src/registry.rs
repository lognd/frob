//! Registry checks the generator and its tests share (~67J8R53).
//!
//! [`verify_linked`] compares the rules a binary actually linked against the reviewed
//! `gob_rules::PRODUCT_CRATES` list (so a dropped rule crate fails naming itself) and checks the
//! redirect table. [`scan_sources`] walks the workspace sources and fails for any
//! `#[derive(Rule)]` type whose crate its product does not list.

use std::path::{Path, PathBuf};

use gob_rules::{
    PRODUCT_CRATES, ProductCrates, ProductRegistryError, RedirectError, Registry, RuleIndex,
    check_registry, crate_of_module,
};

/// Crates that talk about `derive(Rule)` without declaring rules with it.
const SCAN_EXEMPT: &[&str] = &["gob-macros", "gob-rules"];

/// Why the registry is inconsistent.
#[derive(Debug, thiserror::Error)]
pub enum RegistryCheckError {
    /// The linked rules disagree with the reviewed product list.
    #[error("rule registry inconsistent: {}", join(.0))]
    Products(Vec<ProductRegistryError>),
    /// The redirect table disagrees with the live rules.
    #[error("rule redirects inconsistent: {}", join(.0))]
    Redirects(Vec<RedirectError>),
    /// A `#[derive(Rule)]` type sits in a crate its product does not list.
    #[error("unregistered rules: {}", join(.0))]
    Unregistered(Vec<UnregisteredRule>),
    /// A product's command root registered no verbs in the inventory.
    #[error(
        "product `{0}` builds a command root but registers no verbs (crate dropped from the build?)"
    )]
    NoVerbs(String),
    /// A source file could not be read.
    #[error("cannot read {path}: {source}")]
    Io {
        /// The unreadable path.
        path: PathBuf,
        /// The underlying error.
        source: std::io::Error,
    },
}

fn join<T: std::fmt::Display>(items: &[T]) -> String {
    items
        .iter()
        .map(ToString::to_string)
        .collect::<Vec<_>>()
        .join("; ")
}

/// A `#[derive(Rule)]` type outside its product's registry.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error(
    "`{ty}` at {file}:{line} (product `{product}`) is in crate `{krate}`, which the product registry does not list"
)]
pub struct UnregisteredRule {
    /// The type name.
    pub ty: String,
    /// Source file, relative to the workspace.
    pub file: String,
    /// One-based line of the `derive`.
    pub line: usize,
    /// Product the rule claims (`frob` unless `product = ".."` says otherwise).
    pub product: String,
    /// Owning crate.
    pub krate: String,
}

/// Check the linked rules against `declared` and the redirect table against the live rules.
///
/// `indexes` are the `#[rule]` indexes of the products being checked; only legacy rules whose
/// product appears in `declared` are considered, so a binary that links one product can check it.
///
/// # Errors
/// [`RegistryCheckError`] naming the crate, rule or declaring modules at fault.
pub fn verify_linked(
    declared: &[ProductCrates],
    indexes: &[&RuleIndex],
) -> Result<(), RegistryCheckError> {
    let registry = Registry::global();
    let metas: Vec<_> = registry
        .iter()
        .filter(|m| declared.iter().any(|p| p.product == m.product))
        .collect();
    check_registry(declared, &metas, indexes).map_err(RegistryCheckError::Products)?;
    let live = metas.iter().map(|m| (m.id, m.slug, m.module)).chain(
        indexes
            .iter()
            .flat_map(|ix| ix.metas.iter().map(|d| (d.id, d.slug, ix.krate))),
    );
    registry
        .redirects()
        .clone()
        .with_indexes(indexes)
        .check_live(live)
        .map_err(RegistryCheckError::Redirects)?;
    tracing::debug!(products = declared.len(), "linked rule registry verified");
    Ok(())
}

/// Build each product's command root and require its verbs in the command inventory.
///
/// Building the root is what links the product's verbs into the binary, so this replaces the old
/// link anchors with data the generator really consumes.
///
/// # Errors
/// [`RegistryCheckError::NoVerbs`] naming the product with no verbs.
pub fn verify_clis(clis: &[crate::products::ProductCli]) -> Result<(), RegistryCheckError> {
    for (product, build) in clis {
        let cli = build();
        let verbs = gob_cli::all_commands()
            .filter(|m| m.product == *product)
            .count();
        tracing::debug!(product, verbs, "command root verified");
        drop(cli);
        if verbs == 0 {
            return Err(RegistryCheckError::NoVerbs((*product).to_owned()));
        }
    }
    Ok(())
}

/// Scan `crates_dir/*/src` for `#[derive(Rule)]` types missing from their product's registry.
///
/// # Errors
/// [`RegistryCheckError::Unregistered`] listing every offender, or an I/O error.
pub fn scan_sources(crates_dir: &Path) -> Result<(), RegistryCheckError> {
    scan_with(crates_dir, PRODUCT_CRATES)
}

/// [`scan_sources`] against an explicit product list.
///
/// # Errors
/// As [`scan_sources`].
pub fn scan_with(crates_dir: &Path, declared: &[ProductCrates]) -> Result<(), RegistryCheckError> {
    let io = |path: &Path, source| RegistryCheckError::Io {
        path: path.to_owned(),
        source,
    };
    let mut bad = Vec::new();
    let mut crates: Vec<_> = std::fs::read_dir(crates_dir)
        .map_err(|e| io(crates_dir, e))?
        .filter_map(Result::ok)
        .map(|e| e.path())
        .collect();
    crates.sort();
    for dir in crates {
        let Some(name) = dir
            .file_name()
            .map(|n| gob_path::Shown::with_home(std::path::Path::new(n), None).to_string())
        else {
            continue;
        };
        if SCAN_EXEMPT.contains(&name.as_str()) || !dir.join("src").is_dir() {
            continue;
        }
        let mut files = Vec::new();
        collect_rs(&dir.join("src"), &mut files).map_err(|e| io(&dir, e))?;
        for file in files {
            let text = std::fs::read_to_string(&file).map_err(|e| io(&file, e))?;
            let rel =
                gob_path::Shown::with_home(file.strip_prefix(crates_dir).unwrap_or(&file), None)
                    .to_string();
            for (line, ty, product) in derived_rules(&text) {
                let listed = declared
                    .iter()
                    .any(|p| p.product == product && p.crates.contains(&name.as_str()));
                if !listed {
                    bad.push(UnregisteredRule {
                        ty,
                        file: rel.clone(),
                        line,
                        product,
                        krate: crate_of_module(&name),
                    });
                }
            }
        }
    }
    if bad.is_empty() {
        Ok(())
    } else {
        tracing::error!(count = bad.len(), "derive(Rule) types outside the registry");
        Err(RegistryCheckError::Unregistered(bad))
    }
}

fn collect_rs(dir: &Path, out: &mut Vec<PathBuf>) -> std::io::Result<()> {
    let mut entries: Vec<_> = std::fs::read_dir(dir)?
        .filter_map(Result::ok)
        .map(|e| e.path())
        .collect();
    entries.sort();
    for p in entries {
        if p.is_dir() {
            collect_rs(&p, out)?;
        } else if p.extension().is_some_and(|e| e == "rs") {
            out.push(p);
        }
    }
    Ok(())
}

/// `(line, type, product)` for every `derive(.. Rule ..)` in `text`, ignoring comments and strings.
fn derived_rules(text: &str) -> Vec<(usize, String, String)> {
    let lines: Vec<&str> = text.lines().collect();
    let mut out = Vec::new();
    for (i, raw) in lines.iter().enumerate() {
        let line = raw.trim_start();
        if line.starts_with("//") {
            continue;
        }
        let Some(at) = line.find("derive(") else {
            continue;
        };
        if line[..at].matches('"').count() % 2 == 1 || !line.trim_start().starts_with("#[") {
            continue;
        }
        let args = line[at + 7..].split(')').next().unwrap_or("");
        if !args
            .split(|c: char| !(c.is_alphanumeric() || c == '_'))
            .any(|w| w == "Rule")
        {
            continue;
        }
        let mut product = "frob".to_owned();
        let mut ty = String::new();
        for next in &lines[i..lines.len().min(i + 40)] {
            if let Some(p) = next.find("product = \"") {
                let rest = &next[p + 11..];
                rest.split('"')
                    .next()
                    .unwrap_or("frob")
                    .clone_into(&mut product);
            }
            let t = next.trim_start();
            let t = t.strip_prefix("pub ").unwrap_or(t);
            let t = t.strip_prefix("pub(crate) ").unwrap_or(t);
            if let Some(rest) = t
                .strip_prefix("struct ")
                .or_else(|| t.strip_prefix("enum "))
            {
                rest.split(|c: char| !(c.is_alphanumeric() || c == '_'))
                    .next()
                    .unwrap_or("")
                    .clone_into(&mut ty);
                break;
            }
        }
        out.push((i + 1, ty, product));
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn own_products() -> (Vec<ProductCrates>, Vec<&'static RuleIndex>) {
        let declared = PRODUCT_CRATES
            .iter()
            .filter(|p| p.product != "frob")
            .copied()
            .collect();
        let indexes = crate::products::OTHER_PRODUCTS
            .iter()
            .flat_map(|(_, ix)| ix.iter().copied())
            .collect();
        (declared, indexes)
    }

    // frob:tests verify_linked
    #[test]
    fn the_linked_grimble_and_crunk_rules_match_the_product_list() {
        let (declared, indexes) = own_products();
        verify_linked(&declared, &indexes).unwrap();
    }

    // frob:tests verify_linked
    #[test]
    fn a_product_crate_dropped_from_the_build_is_named() {
        let (mut declared, indexes) = own_products();
        declared.push(ProductCrates {
            product: "crunk",
            crates: &["crunk-vanished"],
        });
        let err = verify_linked(&declared, &indexes).unwrap_err().to_string();
        assert!(err.contains("crunk-vanished"), "{err}");
    }

    // frob:tests verify_linked
    #[test]
    fn no_live_id_or_slug_is_shadowed_by_a_redirect() {
        let (declared, indexes) = own_products();
        let table = Registry::global()
            .redirects()
            .clone()
            .with_indexes(&indexes);
        let live = Registry::global()
            .iter()
            .map(|m| (m.id, m.slug, m.module))
            .chain(
                indexes
                    .iter()
                    .flat_map(|ix| ix.metas.iter().map(|d| (d.id, d.slug, ix.krate))),
            );
        assert_eq!(table.check_live(live), Ok(()));
        assert!(!declared.is_empty());
    }

    // frob:tests verify_clis
    #[test]
    fn a_product_without_verbs_is_named() {
        fn empty() -> gob_cli::Cli {
            gob_cli::Cli::new("nothing", "0")
        }
        let err = verify_clis(&[("nothing", empty)]).unwrap_err().to_string();
        assert!(err.contains("`nothing`"), "{err}");
    }

    // frob:tests verify_clis
    #[test]
    fn grimble_and_crunk_register_their_verbs() {
        verify_clis(crate::products::OTHER_CLIS).unwrap();
    }

    // frob:tests derived_rules
    #[test]
    fn derived_rules_reads_type_and_product_and_skips_comments() {
        let src = "// #[derive(Rule)]\nlet s = \"derive(Rule)\";\n#[derive(Debug, gob_rules::Rule)]\n#[rule(id = \"X001\", product = \"crunk\")]\npub struct Foo;\n#[derive(Rule)]\nenum Bar {}\n";
        assert_eq!(
            derived_rules(src),
            vec![
                (3, "Foo".to_owned(), "crunk".to_owned()),
                (6, "Bar".to_owned(), "frob".to_owned())
            ]
        );
    }

    // frob:tests scan_with
    #[test]
    fn an_unregistered_derive_rule_type_is_named() {
        let dir = tempfile::tempdir().unwrap();
        let src = dir.path().join("stray-crate/src");
        std::fs::create_dir_all(&src).unwrap();
        std::fs::write(src.join("lib.rs"), "#[derive(Rule)]\npub struct Stray;\n").unwrap();
        let err = scan_with(dir.path(), PRODUCT_CRATES)
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("Stray") && err.contains("stray-crate") && err.contains("lib.rs:1"),
            "{err}"
        );
    }

    // frob:tests scan_sources
    #[test]
    fn every_derive_rule_type_in_the_workspace_is_registered() {
        let crates = Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
        scan_sources(&crates).unwrap();
    }
}

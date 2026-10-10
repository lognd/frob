//! The `[release]` table of `frob.toml`, and the products and tag pattern resolved from it.

// frob:ticket 01M4069WYA9D1EGVEBC4PT3KZB
// frob:ticket 01M413T4PVDKZ014X3WB5DF7DD
// frob:ticket 01M4FDQXEST75DK0NHDH4P5H15
use std::path::Path;

use gob_config::ConfigTable;

use crate::error::ReleaseError;

/// The product whose `frob.toml` holds the `[release]` table.
const PRODUCT: &str = "frob";

/// The tag pattern used when `[release] tag` is not set.
pub const DEFAULT_TAG: &str = "v{version}";

/// Release policy knobs read by `frob release status`, `release cut`, `release changelog` and REL001.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "release", materialize)]
pub struct ReleaseConfig {
    /// When true, a CI result that cannot be read (no checks, `gh` missing or unauthenticated, no network, non-GitHub remote) blocks the release like a red one; false reports it as Unresolved only. Unknown is never treated as green.
    #[config(default = true, enforcement)]
    pub require_ci: bool,
    /// Tag name pattern of a release: `{version}` is required, `{product}` is replaced by each product name (one tag per product).
    #[config(default = "v{version}".to_owned(), enforcement)]
    pub tag: String,
    /// Products a release ships, one tag each; empty means one product named after the repository.
    #[config(default = Vec::<String>::new(), enforcement)]
    pub products: Vec<String>,
    /// Text `frob ticket fragment` puts before the ticket title in the skeleton (for example `frob: `); empty adds nothing.
    #[config(default = String::new())]
    pub fragment_prefix: String,
    /// Products that ship as a preview: their tag message and changelog heading carry " (preview)".
    #[config(default = Vec::<String>::new(), enforcement)]
    pub preview: Vec<String>,
}

/// The products of a repository and the pattern naming their release tags.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProductTags {
    products: Vec<String>,
    pattern: String,
    preview: Vec<String>,
}

impl ProductTags {
    /// Build from explicit products and a pattern; `products` must not be empty.
    ///
    /// # Errors
    /// [`ReleaseError::Config`] when the pattern has no `{version}` or `products` is empty.
    pub fn new(products: Vec<String>, pattern: &str) -> Result<Self, ReleaseError> {
        if !pattern.contains("{version}") {
            return Err(ReleaseError::Config(format!(
                "[release] tag `{pattern}` has no `{{version}}`; use for example `v{{version}}`"
            )));
        }
        if products.is_empty() {
            return Err(ReleaseError::Config("no release products".to_owned()));
        }
        if products.len() > 1 && !pattern.contains("{product}") {
            return Err(ReleaseError::Config(format!(
                "[release] tag `{pattern}` has no `{{product}}` but {} products are configured, so their tags would collide; use for example `{{product}}-v{{version}}`",
                products.len()
            )));
        }
        Ok(Self {
            products,
            pattern: pattern.to_owned(),
            preview: Vec::new(),
        })
    }

    /// The same products with `preview` marked as preview releases.
    #[must_use]
    pub fn with_preview(mut self, preview: Vec<String>) -> Self {
        self.preview = preview;
        self
    }

    /// True when `product` ships as a preview.
    #[must_use]
    pub fn is_preview(&self, product: &str) -> bool {
        self.preview.iter().any(|p| p == product)
    }

    /// The changelog heading of `product`: `grimble (preview)` for a preview product, else the name.
    #[must_use]
    pub fn label(&self, product: &str) -> String {
        if self.is_preview(product) {
            format!("{product} (preview)")
        } else {
            product.to_owned()
        }
    }

    /// The annotated tag message of `product` at `version`: `grimble 0.532.0 (preview)` for a preview product, else `frob 0.532.0`.
    #[must_use]
    pub fn tag_message(&self, product: &str, version: &str) -> String {
        if self.is_preview(product) {
            format!("{product} {version} (preview)")
        } else {
            format!("{product} {version}")
        }
    }

    /// Resolve from `<root>/frob.toml`; with no `products` the one product is named after the repository.
    ///
    /// # Errors
    /// [`ReleaseError::Config`] when the file cannot be loaded or the values are unusable.
    pub fn load(root: &Path) -> Result<Self, ReleaseError> {
        let cfg = gob_config::load::<ReleaseConfig>(root, PRODUCT)
            .map_err(|e| ReleaseError::Config(e.to_string()))?
            .value;
        let products = if cfg.products.is_empty() {
            let name = repository_name(root);
            tracing::info!(product = %name, "no [release] products; using the repository name");
            vec![name]
        } else {
            cfg.products
        };
        Ok(Self::new(products, &cfg.tag)?.with_preview(cfg.preview))
    }

    /// The product names, in configured order.
    #[must_use]
    pub fn products(&self) -> &[String] {
        &self.products
    }

    /// True when more than one product is released (changelog sections then carry product headings).
    #[must_use]
    pub fn is_multi(&self) -> bool {
        self.products.len() > 1
    }

    /// The tag name of `product` at `version`.
    #[must_use]
    pub fn tag_name(&self, product: &str, version: &str) -> String {
        self.pattern
            .replace("{product}", product)
            .replace("{version}", version)
    }

    /// Every tag a release of `version` creates, in product order.
    #[must_use]
    pub fn tag_names(&self, version: &str) -> Vec<String> {
        self.products
            .iter()
            .map(|p| self.tag_name(p, version))
            .collect()
    }

    /// The version a release tag name carries, or `None` when the name is not a configured product tag.
    #[must_use]
    pub fn tag_version<'a>(&self, name: &'a str) -> Option<&'a str> {
        self.products
            .iter()
            .find_map(|p| {
                let concrete = self.pattern.replace("{product}", p);
                let (prefix, suffix) = concrete.split_once("{version}")?;
                name.strip_prefix(prefix)?.strip_suffix(suffix)
            })
            .filter(|v| semver::Version::parse(v).is_ok())
    }

    /// The pattern with `{product}` and `{version}` left in place, for messages.
    #[must_use]
    pub fn pattern(&self) -> &str {
        &self.pattern
    }
}

/// The repository's name: the `origin` URL's last segment, else the main checkout's directory name.
fn repository_name(root: &Path) -> String {
    let repo = gob_git::Repo::discover(root).ok();
    if let Some(url) = repo.as_ref().and_then(|r| r.remote_url("origin")) {
        let last = url
            .trim_end_matches('/')
            .rsplit(['/', ':'])
            .next()
            .unwrap_or("");
        let name = last.strip_suffix(".git").unwrap_or(last);
        if !name.is_empty() {
            return name.to_owned();
        }
    }
    let main = repo
        .as_ref()
        .map(|r| r.common_dir().to_path_buf())
        .and_then(|c| {
            if c.file_name().is_some_and(|n| n == ".git") {
                c.parent().map(Path::to_path_buf)
            } else {
                Some(c)
            }
        })
        .unwrap_or_else(|| root.to_path_buf());
    main.file_name().map_or_else(
        || "repository".to_owned(),
        |n| n.to_string_lossy().into_owned(),
    )
}

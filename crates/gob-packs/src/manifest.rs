//! The typed `pack.toml` manifest, its loader and the cross-pack checks.

use std::collections::{BTreeMap, BTreeSet};
use std::io::Read;
use std::path::Path;

use serde::Deserialize;

use crate::error::PackError;
use crate::limits::{
    MAX_EFFECTS, MAX_FAMILIES, MAX_FAMILY, MAX_GRANT, MAX_GRANTS, MAX_LIST, MAX_MANIFEST_BYTES,
    MAX_NAME, MAX_NEEDS, MAX_PATH, MAX_REQ, MAX_VERSION, Owner,
};
use crate::validate;

/// A validated `pack.toml`: the pack table, what it provides, what it may do.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Manifest {
    /// Identity, owned families and needs.
    pub pack: PackTable,
    /// Content files by tier.
    #[serde(default)]
    pub provides: Provides,
    /// Effects a tier-3 component may use (deny by default: empty).
    #[serde(default)]
    pub effects: BTreeMap<String, Vec<String>>,
}

/// The `[pack]` table.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PackTable {
    /// Kebab-case pack name, the registry prefix.
    pub name: String,
    /// Exact semver, no ranges.
    pub version: String,
    /// Rule id prefixes this pack owns.
    #[serde(default)]
    pub families: Vec<String>,
    /// Required tool versions by name, for example `grimble = ">=2.0"`.
    #[serde(default)]
    pub needs: BTreeMap<String, String>,
}

/// The `[provides]` table: pack-relative files by tier.
#[derive(Debug, Clone, Default, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Provides {
    /// Tier 1 atoms file.
    #[serde(default)]
    pub atoms: Option<String>,
    /// Tier 1 matrix-build excuse templates file.
    #[serde(default)]
    pub templates: Option<String>,
    /// Tier 2 rule globs.
    #[serde(default)]
    pub rules: Vec<String>,
    /// Tier 3 component files.
    #[serde(default)]
    pub wasm: Vec<String>,
    /// Tier 4 adapter directories or files.
    #[serde(default)]
    pub adapters: Vec<String>,
}

impl Manifest {
    /// Parses and validates manifest `text` read from `file` (a label for errors).
    ///
    /// # Errors
    /// PACK005 [`PackError::Malformed`] naming the file, key and line when the
    /// text is too large, non-ASCII, not TOML, has an unknown key or breaks a bound.
    pub fn parse(file: &str, text: &str) -> Result<Self, PackError> {
        if text.len() > MAX_MANIFEST_BYTES {
            return Err(PackError::malformed(
                file,
                "<file>",
                format!("is {} bytes, the limit is {MAX_MANIFEST_BYTES}", text.len()),
            ));
        }
        if !text.is_ascii() {
            return Err(PackError::malformed(file, "<file>", "must be ASCII only"));
        }
        let manifest: Self = toml::from_str(text).map_err(|e| locate(file, text, &e))?;
        manifest.validate(file)?;
        tracing::debug!(file, name = %manifest.pack.name, "manifest parsed");
        Ok(manifest)
    }

    fn validate(&self, file: &str) -> Result<(), PackError> {
        let bad = |key: &str, why: String| PackError::malformed(file, key, why);
        let p = &self.pack;
        validate::kebab(&p.name, MAX_NAME).map_err(|w| bad("pack.name", w))?;
        validate::semver(&p.version, MAX_VERSION).map_err(|w| bad("pack.version", w))?;
        if p.families.len() > MAX_FAMILIES {
            return Err(bad(
                "pack.families",
                format!("has more than {MAX_FAMILIES} entries"),
            ));
        }
        let mut seen = BTreeSet::new();
        for f in &p.families {
            validate::family(f, MAX_FAMILY)
                .map_err(|w| bad("pack.families", format!("`{f}` {w}")))?;
            if !seen.insert(f.as_str()) {
                return Err(bad("pack.families", format!("`{f}` is listed twice")));
            }
        }
        if p.needs.len() > MAX_NEEDS {
            return Err(bad(
                "pack.needs",
                format!("has more than {MAX_NEEDS} entries"),
            ));
        }
        for (k, v) in &p.needs {
            validate::kebab(k, MAX_NAME)
                .map_err(|w| bad(&format!("pack.needs.{k}"), format!("key {w}")))?;
            validate::requirement(v, MAX_REQ).map_err(|w| bad(&format!("pack.needs.{k}"), w))?;
        }
        self.validate_provides(file)?;
        self.validate_effects(file)
    }

    fn validate_provides(&self, file: &str) -> Result<(), PackError> {
        let pr = &self.provides;
        for (key, one) in [
            ("provides.atoms", &pr.atoms),
            ("provides.templates", &pr.templates),
        ] {
            if let Some(path) = one {
                validate::rel_path(path, MAX_PATH)
                    .map_err(|w| PackError::malformed(file, key, w))?;
            }
        }
        for (key, list) in [
            ("provides.rules", &pr.rules),
            ("provides.wasm", &pr.wasm),
            ("provides.adapters", &pr.adapters),
        ] {
            if list.len() > MAX_LIST {
                return Err(PackError::malformed(
                    file,
                    key,
                    format!("has more than {MAX_LIST} entries"),
                ));
            }
            for path in list {
                validate::rel_path(path, MAX_PATH)
                    .map_err(|w| PackError::malformed(file, key, format!("`{path}` {w}")))?;
            }
        }
        Ok(())
    }

    fn validate_effects(&self, file: &str) -> Result<(), PackError> {
        if self.effects.len() > MAX_EFFECTS {
            return Err(PackError::malformed(
                file,
                "effects",
                format!("has more than {MAX_EFFECTS} keys"),
            ));
        }
        for (k, grants) in &self.effects {
            let key = format!("effects.{k}");
            validate::effect_token(k, MAX_GRANT)
                .map_err(|w| PackError::malformed(file, &key, format!("key {w}")))?;
            if grants.len() > MAX_GRANTS {
                return Err(PackError::malformed(
                    file,
                    &key,
                    format!("has more than {MAX_GRANTS} grants"),
                ));
            }
            for g in grants {
                validate::effect_token(g, MAX_GRANT)
                    .map_err(|w| PackError::malformed(file, &key, format!("grant {w}")))?;
            }
        }
        Ok(())
    }
}

/// Maps a TOML error to PACK005, naming the offending key and line.
fn locate(file: &str, text: &str, e: &toml::de::Error) -> PackError {
    let msg = e.message();
    let line_start = e.span().map(|s| s.start.min(text.len()));
    let line = line_start.map(|o| text[..o].bytes().filter(|&b| b == b'\n').count() + 1);
    let key = msg
        .split('`')
        .nth(1)
        .map(str::to_owned)
        .or_else(|| {
            let o = line_start?;
            let ls = text[..o].rfind('\n').map_or(0, |i| i + 1);
            let l = text[ls..].lines().next()?;
            l.split_once('=').map(|(k, _)| k.trim().to_owned())
        })
        .unwrap_or_else(|| "<document>".to_owned());
    tracing::debug!(file, %key, "manifest rejected by parser");
    PackError::Malformed {
        file: file.to_owned(),
        key,
        line,
        reason: msg.to_owned(),
    }
}

/// Reads and validates the manifest at `path`, never reading past the size bound.
///
/// # Errors
/// PACK005 when the file cannot be read, is not UTF-8, or fails [`Manifest::parse`].
pub fn load(path: &Path) -> Result<Manifest, PackError> {
    let file = path.display().to_string();
    let io = |e: std::io::Error| PackError::malformed(&file, "<file>", format!("cannot read: {e}"));
    let mut buf = Vec::new();
    std::fs::File::open(path)
        .map_err(io)?
        .take(MAX_MANIFEST_BYTES as u64 + 1)
        .read_to_end(&mut buf)
        .map_err(io)?;
    let text = String::from_utf8(buf)
        .map_err(|_| PackError::malformed(&file, "<file>", "must be UTF-8"))?;
    Manifest::parse(&file, &text)
}

/// Checks that no two packs share a name or a family, in the order given.
///
/// # Errors
/// PACK004 naming both packs and both files for the first conflict found.
pub fn check_unique(packs: &[(&str, &Manifest)]) -> Result<(), PackError> {
    let mut names: BTreeMap<&str, Owner> = BTreeMap::new();
    let mut families: BTreeMap<&str, Owner> = BTreeMap::new();
    for (file, m) in packs {
        let me = Owner {
            file: (*file).to_owned(),
            name: m.pack.name.clone(),
        };
        if let Some(first) = names.insert(&m.pack.name, me.clone()) {
            return Err(PackError::DuplicateName { first, second: me });
        }
        for f in &m.pack.families {
            if let Some(first) = families.insert(f, me.clone()) {
                return Err(PackError::DuplicateFamily {
                    family: f.clone(),
                    first,
                    second: me,
                });
            }
        }
    }
    Ok(())
}

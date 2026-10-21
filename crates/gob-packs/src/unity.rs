//! The built-in `unity` pack: Unity engine vocabulary (engine entry points).
//!
//! The pack is opt-in. The root config enables it (`[[packs.enable]] name = "unity"` or
//! `[packs] enabled = ["unity"]`); an adapter never does. The manifest is a normal `pack.toml`
//! plus `[[vocab]]` tables, which are split off here so the manifest keeps its closed schema.

// frob:ticket 01M44YQXS4BXE0X07FBYR0STJ5

use gob_ir::engine::EngineVocab;
use serde::Deserialize;

use crate::{Activation, Manifest, PackError};

/// The pack name used in `[[packs.enable]]`.
pub const NAME: &str = "unity";

/// The built-in manifest text.
const MANIFEST: &str = include_str!("../../../packs/unity.toml");

/// The only language the pack's vocabulary covers.
const LANG: &str = "csharp";

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct VocabTable {
    lang: String,
    class: String,
    names: Vec<String>,
}

/// A parsed `unity` pack: its validated manifest and its engine vocabulary.
#[derive(Debug, Clone)]
pub struct UnityPack {
    /// The validated manifest (the `[[vocab]]` tables removed).
    pub manifest: Manifest,
    /// The C# engine entry-point vocabulary.
    pub vocab: EngineVocab,
}

impl UnityPack {
    /// Parses and validates a unity-shaped pack file named `file`.
    ///
    /// # Errors
    /// PACK005 when the manifest or a `[[vocab]]` table is malformed.
    pub fn parse(file: &str, text: &str) -> Result<Self, PackError> {
        let mut table: toml::Table = toml::from_str(text)
            .map_err(|e| PackError::malformed(file, "<file>", e.message().to_string()))?;
        let vocab_value = table.remove("vocab");
        let rest = toml::to_string(&table)
            .map_err(|e| PackError::malformed(file, "<file>", e.to_string()))?;
        let manifest = Manifest::parse(file, &rest)?;
        let mut vocab = EngineVocab::default();
        let tables: Vec<VocabTable> = match vocab_value {
            None => Vec::new(),
            Some(v) => v.try_into().map_err(|e: toml::de::Error| {
                PackError::malformed(file, "vocab", e.message().to_string())
            })?,
        };
        for t in tables {
            if t.lang != LANG {
                return Err(PackError::malformed(
                    file,
                    "vocab.lang",
                    format!("unsupported language `{}`", t.lang),
                ));
            }
            if !vocab.add_class(&t.class, t.names) {
                return Err(PackError::malformed(
                    file,
                    "vocab.class",
                    format!("unknown engine vocabulary class `{}`", t.class),
                ));
            }
        }
        tracing::debug!(file, "unity pack parsed");
        Ok(Self { manifest, vocab })
    }

    /// The built-in pack.
    ///
    /// # Errors
    /// PACK005 only if the shipped file is broken (a test guards against it).
    pub fn builtin() -> Result<Self, PackError> {
        Self::parse("packs/unity.toml", MANIFEST)
    }
}

/// Which paths the root config enables the unity pack for.
#[derive(Debug, Clone)]
pub struct UnityGate {
    activation: Activation,
}

impl UnityGate {
    /// Reads the `[packs]` table of the root config text `config`.
    ///
    /// # Errors
    /// PACK005 when the `[packs]` table is malformed.
    pub fn parse(file: &str, config: &str) -> Result<Self, PackError> {
        Ok(Self {
            activation: Activation::parse(file, config)?,
        })
    }

    /// True when the pack is enabled anywhere in the config.
    pub fn is_enabled(&self) -> bool {
        self.activation.entries().iter().any(|e| e.name == NAME)
    }

    /// True when the pack is active for the repo-relative `path`.
    pub fn is_active_for(&self, path: &str) -> bool {
        self.activation.resolve(path).iter().any(|a| a.name == NAME)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests UnityPack.builtin
    #[test]
    fn builtin_pack_raises_no_pack_finding() {
        let p = UnityPack::builtin().expect("builtin unity pack validates");
        assert_eq!(p.manifest.pack.name, NAME);
        assert!(p.vocab.is_message("Update"));
        assert!(p.vocab.is_message("OnTriggerEnter"));
        assert!(p.vocab.bases.contains("MonoBehaviour"));
        assert!(p.vocab.method_attributes.contains("MenuItem"));
        assert!(p.vocab.type_attributes.contains("InitializeOnLoad"));
    }

    // frob:tests UnityPack.parse
    #[test]
    fn bad_pack_raises_pack005() {
        let bad = "[pack]\nname = \"unity\"\nversion = \"0.1.0\"\n[[vocab]]\nlang = \"csharp\"\nclass = \"nope\"\nnames = [\"X\"]\n";
        let e = UnityPack::parse("u.toml", bad).unwrap_err();
        assert_eq!(e.code().as_str(), "PACK005");
        let bad = "[pack]\nname = \"unity\"\nversion = \"0.1.0\"\nbogus = 1\n";
        assert_eq!(
            UnityPack::parse("u.toml", bad).unwrap_err().code().as_str(),
            "PACK005"
        );
    }

    // frob:tests UnityGate.is_enabled
    #[test]
    fn gate_reads_both_enable_forms() {
        let a = UnityGate::parse("frob.toml", "[[packs.enable]]\nname = \"unity\"\n").unwrap();
        assert!(a.is_enabled() && a.is_active_for("Assets/A.cs"));
        let b = UnityGate::parse("frob.toml", "[packs]\nenabled = [\"unity\"]\n").unwrap();
        assert!(b.is_enabled());
        let c = UnityGate::parse("frob.toml", "[project]\nname = \"x\"\n").unwrap();
        assert!(!c.is_enabled() && !c.is_active_for("Assets/A.cs"));
    }
}

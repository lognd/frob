//! A standalone content file (`design/content/<name>.toml`): copy keys with their text and an
//! optional length budget. Scenes reference a key with `data-copy`, never a literal.

// frob:ticket 01M4CXR96GDDX460SZZVAAWD0R

use std::collections::HashSet;

use serde::{Deserialize, Serialize};

/// One copy key: an id scenes reference, the text it stands for and an optional length budget.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ContentKey {
    /// The key scenes reference, for example `home.title`.
    pub id: String,
    /// The copy itself.
    pub text: String,
    /// The most characters (Unicode scalar values) the text may have; absent means no budget.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub max_chars: Option<u32>,
}

/// A parsed content file.
#[derive(Debug, Clone, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ContentFile {
    /// The locale the text is written in (a BCP 47 tag); absent means the project default.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub locale: Option<String>,
    /// The keys, in file order.
    #[serde(default, rename = "key")]
    pub keys: Vec<ContentKey>,
}

/// Why a content file could not be read.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum ContentFileError {
    /// Not valid TOML, or not the content schema.
    #[error("invalid content file: {0}")]
    Parse(String),
    /// A key has an empty or whitespace-only id.
    #[error("content key at position {0} has an empty id")]
    EmptyId(usize),
    /// Two keys in the file share an id.
    #[error("content file repeats key `{0}`")]
    DuplicateKey(String),
}

/// Parse one content file's text, checking the rules that need no project context.
///
/// # Errors
/// [`ContentFileError`] on bad TOML, an empty key id or a key id repeated within the file.
pub fn parse_content_file(text: &str) -> Result<ContentFile, ContentFileError> {
    let file: ContentFile =
        toml_edit::de::from_str(text).map_err(|e| ContentFileError::Parse(e.to_string()))?;
    let mut seen: HashSet<&str> = HashSet::new();
    for (i, key) in file.keys.iter().enumerate() {
        if key.id.trim().is_empty() {
            return Err(ContentFileError::EmptyId(i));
        }
        if !seen.insert(key.id.as_str()) {
            return Err(ContentFileError::DuplicateKey(key.id.clone()));
        }
    }
    tracing::debug!(keys = file.keys.len(), "content file parsed");
    Ok(file)
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-spec/src/content_file.rs::parse_content_file
    #[test]
    fn parses_keys_with_locale_and_budget() {
        let f = parse_content_file(
            "locale = \"en\"\n[[key]]\nid = \"home.title\"\ntext = \"Hi\"\nmax_chars = 8\n[[key]]\nid = \"home.sub\"\ntext = \"\"\n",
        )
        .expect("parses");
        assert_eq!(f.locale.as_deref(), Some("en"));
        assert_eq!(f.keys.len(), 2);
        assert_eq!(f.keys[0].max_chars, Some(8));
        assert_eq!(f.keys[1].max_chars, None);
        assert!(parse_content_file("").expect("empty ok").keys.is_empty());
    }

    // frob:tests crates/crunk-spec/src/content_file.rs::parse_content_file
    #[test]
    fn rejects_empty_duplicate_and_unknown() {
        assert_eq!(
            parse_content_file("[[key]]\nid = \" \"\ntext = \"x\"\n"),
            Err(ContentFileError::EmptyId(0))
        );
        assert_eq!(
            parse_content_file(
                "[[key]]\nid = \"a\"\ntext = \"x\"\n[[key]]\nid = \"a\"\ntext = \"y\"\n"
            ),
            Err(ContentFileError::DuplicateKey("a".into()))
        );
        assert!(matches!(
            parse_content_file("[[key]]\nid = \"a\"\ntext = \"x\"\nbogus = 1\n"),
            Err(ContentFileError::Parse(_))
        ));
    }
}

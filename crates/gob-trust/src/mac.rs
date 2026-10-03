//! Domain-separated keyed-blake3 MACs and constant-time verification.

use std::fmt;

use crate::error::TrustError;
use crate::key::MachineKey;

/// A 32-byte MAC tag; equality is constant-time (it wraps `blake3::Hash`, whose `PartialEq` is).
#[derive(Clone, Copy, PartialEq, Eq)]
pub struct Tag(blake3::Hash);

impl Tag {
    /// The raw tag bytes.
    pub fn as_bytes(&self) -> &[u8; 32] {
        self.0.as_bytes()
    }

    /// Lowercase hex form for storage in text rows.
    pub fn to_hex(&self) -> String {
        self.0.to_hex().to_string()
    }

    /// Parse the hex form; `None` when malformed.
    pub fn from_hex(s: &str) -> Option<Self> {
        blake3::Hash::from_hex(s).ok().map(Self)
    }
}

impl From<[u8; 32]> for Tag {
    fn from(b: [u8; 32]) -> Self {
        Self(blake3::Hash::from_bytes(b))
    }
}

impl fmt::Debug for Tag {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Tag({})", self.0.to_hex())
    }
}

/// MAC `bytes` under `key`, separated by `context` (for example "gob-cache-row/v1").
///
/// The hashed input is `len(context) as u64 LE || context || bytes`, so no
/// (context, bytes) pair can collide with another.
pub fn mac(key: &MachineKey, context: &str, bytes: &[u8]) -> Tag {
    let mut h = blake3::Hasher::new_keyed(key.as_bytes());
    h.update(&(context.len() as u64).to_le_bytes());
    h.update(context.as_bytes());
    h.update(bytes);
    Tag(h.finalize())
}

/// Check `tag` against `bytes` under `key` and `context`, in constant time.
///
/// # Errors
/// [`TrustError::Mismatch`] when the tag is wrong.
pub fn verify(key: &MachineKey, context: &str, bytes: &[u8], tag: &Tag) -> Result<(), TrustError> {
    if mac(key, context, bytes) == *tag {
        Ok(())
    } else {
        tracing::warn!(context, "MAC verification failed");
        Err(TrustError::Mismatch)
    }
}

/// Appends a record's canonical bytes with length-prefixed fields (no ambiguity between fields).
#[derive(Debug, Default)]
pub struct CanonicalWriter(Vec<u8>);

impl CanonicalWriter {
    /// Append one field, prefixed by its u64 LE length.
    pub fn field(&mut self, bytes: &[u8]) -> &mut Self {
        self.0
            .extend_from_slice(&(bytes.len() as u64).to_le_bytes());
        self.0.extend_from_slice(bytes);
        self
    }

    /// Append a string field.
    pub fn str(&mut self, s: &str) -> &mut Self {
        self.field(s.as_bytes())
    }

    /// Append a u64 field.
    pub fn u64(&mut self, v: u64) -> &mut Self {
        self.field(&v.to_le_bytes())
    }
}

/// A record with one stable byte form, the only thing that gets MAC'd.
pub trait Canonical {
    /// Write every authenticated field, in a fixed order, into `w`.
    fn write_canonical(&self, w: &mut CanonicalWriter);
}

fn canonical_bytes(record: &impl Canonical) -> Vec<u8> {
    let mut w = CanonicalWriter::default();
    record.write_canonical(&mut w);
    w.0
}

/// MAC a structured record by its canonical bytes.
pub fn mac_record(key: &MachineKey, context: &str, record: &impl Canonical) -> Tag {
    mac(key, context, &canonical_bytes(record))
}

/// Verify a structured record's tag.
///
/// # Errors
/// [`TrustError::Mismatch`] when the tag is wrong.
pub fn verify_record(
    key: &MachineKey,
    context: &str,
    record: &impl Canonical,
    tag: &Tag,
) -> Result<(), TrustError> {
    verify(key, context, &canonical_bytes(record), tag)
}

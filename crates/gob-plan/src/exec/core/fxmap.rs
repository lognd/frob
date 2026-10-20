//! A fast non-cryptographic hash map for the evaluator's per-run caches.
//!
//! The caches key on small integers and short vectors of them, never on untrusted input, so
//! the default `SipHash` only costs time. This is the Fx multiply-rotate hash.

use std::collections::HashMap;
use std::hash::{BuildHasherDefault, Hasher};

const SEED: u64 = 0x51_7c_c1_b7_27_22_0a_95;

/// The Fx hasher state.
#[derive(Default, Clone, Copy)]
pub(crate) struct Fx(u64);

impl Fx {
    #[inline]
    fn add(&mut self, word: u64) {
        self.0 = (self.0.rotate_left(5) ^ word).wrapping_mul(SEED);
    }
}

impl Hasher for Fx {
    #[inline]
    fn write(&mut self, bytes: &[u8]) {
        let (chunks, rest) = bytes.as_chunks::<8>();
        for c in chunks {
            self.add(u64::from_le_bytes(*c));
        }
        for &b in rest {
            self.add(u64::from(b));
        }
    }
    #[inline]
    fn write_u8(&mut self, i: u8) {
        self.add(u64::from(i));
    }
    #[inline]
    fn write_u16(&mut self, i: u16) {
        self.add(u64::from(i));
    }
    #[inline]
    fn write_u32(&mut self, i: u32) {
        self.add(u64::from(i));
    }
    #[inline]
    fn write_u64(&mut self, i: u64) {
        self.add(i);
    }
    #[inline]
    fn write_usize(&mut self, i: usize) {
        self.add(i as u64);
    }
    #[inline]
    fn finish(&self) -> u64 {
        self.0
    }
}

/// A `HashMap` keyed with the Fx hash.
pub(crate) type FastMap<K, V> = HashMap<K, V, BuildHasherDefault<Fx>>;

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests FastMap
    #[test]
    fn fast_map_round_trips_keys() {
        let mut m: FastMap<(u16, Vec<u32>), u8> = FastMap::default();
        m.insert((1, vec![2, 3]), 7);
        m.insert((1, vec![3, 2]), 8);
        assert_eq!(m.get(&(1, vec![2, 3])), Some(&7));
        assert_eq!(m.get(&(1, vec![3, 2])), Some(&8));
        assert_eq!(m.get(&(2, vec![2, 3])), None);
    }
}

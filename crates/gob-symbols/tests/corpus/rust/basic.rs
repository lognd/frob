//! Crate docs.

use crate::util::helper;
use std::collections::{HashMap, HashSet};
use super::sibling::{self, Thing as T};

/// A public struct.
pub struct Point {
    pub x: i32,
    y: i32,
}

pub(crate) enum Color {
    Red,
    Green { shade: u8 },
}

pub trait Shape {
    fn area(&self) -> f64;
    fn name(&self) -> String {
        String::from("shape")
    }
}

impl Point {
    pub fn new(x: i32, y: i32) -> Self {
        Self { x, y }
    }

    fn secret(&self) -> i32 {
        self.y
    }
}

impl Shape for Point {
    fn area(&self) -> f64 {
        0.0
    }
}

impl std::fmt::Display for Point {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.x)
    }
}

impl std::fmt::Debug for Point {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "P")
    }
}

pub const MAX: u32 = 10;
static COUNT: u32 = 0;
pub type Alias = Vec<u8>;

#[macro_export]
macro_rules! shout {
    ($x:expr) => {
        $x
    };
}

pub mod inner {
    pub fn deep() {}
    fn hidden() {}
}

mod private_mod {
    pub fn not_api() {}
}

/// Free function.
pub fn free(a: u32) -> u32 {
    a + 1
}

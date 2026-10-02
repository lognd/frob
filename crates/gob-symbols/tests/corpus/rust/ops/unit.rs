//! Units with roles: items, impl members, variants, bodiless declarations.

pub mod shapes {
    pub struct Point {
        pub x: i32,
    }

    pub enum Color {
        Red,
        Green = 2,
    }

    pub trait Shape {
        fn area(&self) -> i32;
        fn name(&self) -> &str {
            "shape"
        }
    }

    impl Point {
        pub fn new(x: i32) -> Point {
            Point { x }
        }
    }

    impl Shape for Point {
        fn area(&self) -> i32 {
            self.x
        }
    }
}

pub const LIMIT: u32 = 3;
pub type Alias = u32;

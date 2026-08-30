const std = @import("std");

/// Adds two numbers.
pub fn add(a: i32, b: i32) i32 {
    // sum them
    return a + b;
}

fn hidden() void {}

pub fn mayFail() !i32 {
    return error.Oops;
}

pub const MAX: i32 = 10;

const Widget = struct {
    count: i32,

    /// Initializes a Widget.
    pub fn init() Widget {
        return Widget{ .count = 0 };
    }

    fn helper() void {}
};

pub const Color = enum {
    red,
    green,
    blue,
};

// A plain comment, not a doc comment.
pub fn afterPlainComment() void {}

comptime {
    const x = 1;
}

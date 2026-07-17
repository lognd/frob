/// Adds two numbers.
pub fn add(x: i32, y: i32) -> i32 {
    // sum them
    x + y
}

pub struct Widget {
    count: i32,
}

impl Widget {
    /// Renders the widget.
    pub fn render(&self, label: &str) -> String {
        label.to_string()
    }

    fn hidden(&self) {}
}

pub const MAX_WIDGETS: i32 = 10;

/// Adds two numbers.
int add(int x, int y) {
    // sum them
    return x + y;
}

class Widget {
public:
    /// Renders the widget.
    int render(int label) {
        return label;
    }

private:
    int hidden() {
        return 0;
    }
};

const int MAX_WIDGETS = 10;

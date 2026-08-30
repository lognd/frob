package com.frob.sample;

import java.util.List;

/**
 * Adds two numbers.
 */
public class Widget {

    public static final int MAX_WIDGETS = 10;

    private int hidden;

    /**
     * Renders the widget.
     */
    public String render(String label) {
        // sum them
        return add(label);
    }

    String packagePrivate() {
        return "default visibility";
    }

    private String add(String label) {
        return label;
    }

    class Inner {
        void innerMethod() {}
    }

    interface Thing {
        void doIt();

        default void doItDefault() {}
    }

    enum Color {
        RED,
        GREEN,
        BLUE
    }
}

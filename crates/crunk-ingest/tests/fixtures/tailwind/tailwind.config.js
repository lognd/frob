/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.tsx"],
  theme: {
    // replaces the whole namespace
    screens: { tablet: "640px" },
    extend: {
      colors: {
        brand: { DEFAULT: "#112233", 500: "rgb(var(--brand-rgb) / <alpha-value>)" },
        "red-500": "#ff0000",
      },
      spacing: {
        18: "4.5rem",
        4: "1rem", // crunk:waive TW005 reason=legacy grid
        "space-9": "2.25rem",
      },
      fontSize: { huge: ["4rem", { lineHeight: "1" }] },
      ...sharedTheme,
      [computed]: "x",
    },
  },
};

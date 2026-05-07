/** @type {import('tailwindcss').Config} */
//
// Tailwind theme mirrors the editorial/cinematic design tokens defined in
// src/styles/tokens.css so utility classes pick up the same warm-tinted
// near-black surfaces, champagne gold accent and Fraunces/Geist/JetBrains
// Mono pairing without each component re-declaring CSS vars.
//
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          base: "#0e0d0c",
          elevated: "#161513",
          overlay: "#1f1d1a",
          line: "rgba(243, 238, 229, 0.08)",
          "line-strong": "rgba(243, 238, 229, 0.18)",
        },
        text: {
          primary: "#f3eee5",
          secondary: "#a8a39a",
          tertiary: "#65605a",
          disabled: "#3a3733",
        },
        gold: {
          DEFAULT: "#c9a961",
          bright: "#e8c882",
          soft: "rgba(201, 169, 97, 0.18)",
        },
        status: {
          up: "#7fa583",
          down: "#c47474",
        },
      },
      fontFamily: {
        display: ['Fraunces', '"Times New Roman"', "serif"],
        body: ["Geist", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      letterSpacing: {
        kicker: "0.18em",
        "kicker-lg": "0.22em",
      },
      maxWidth: {
        page: "1180px",
        article: "880px",
      },
      transitionTimingFunction: {
        editorial: "cubic-bezier(0.32, 0.08, 0, 1)",
      },
    },
  },
  plugins: [],
};

import type { Config } from "tailwindcss";

export default {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "var(--ink)",
        forest: "var(--forest)",
        "forest-deep": "var(--forest-deep)",
        mist: "var(--mist)",
        sand: "var(--sand)",
        amber: "var(--amber)",
        background: "var(--background)",
        foreground: "var(--foreground)",
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        sans: ["Manrope", "sans-serif"],
      },
      boxShadow: {
        soft: "0 18px 50px rgba(18, 34, 31, 0.08)",
      },
    },
  },
  plugins: [],
} satisfies Config;

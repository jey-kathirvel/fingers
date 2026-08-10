import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#122033",
          soft: "#243447",
          mute: "#5b6b7c",
        },
        mist: {
          DEFAULT: "#f3f6f8",
          deep: "#e7eef3",
        },
        tide: {
          DEFAULT: "#0f766e",
          bright: "#14b8a6",
          soft: "#ccfbf1",
        },
        sand: "#f7f1e8",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        panel: "0 18px 50px rgba(18, 32, 51, 0.08)",
      },
      backgroundImage: {
        atmosphere:
          "radial-gradient(1200px 500px at 10% -10%, rgba(20,184,166,0.18), transparent 55%), radial-gradient(900px 400px at 100% 0%, rgba(29,78,216,0.10), transparent 50%), linear-gradient(180deg, #f7fafc 0%, #eef3f7 100%)",
      },
    },
  },
  plugins: [],
};
export default config;

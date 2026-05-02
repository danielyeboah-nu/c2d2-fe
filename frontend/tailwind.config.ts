import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        olive: {
          600: "#4a5c1a",
          700: "#3a4a12",
          800: "#2c3a0e",
          900: "#1e2808",
        },
        amber: {
          400: "#f59e0b",
          500: "#d97706",
        },
      },
    },
  },
  plugins: [],
};

export default config;

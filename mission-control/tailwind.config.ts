import type { Config } from "tailwindcss";

// ClawOps palette — "Webull terminal meets mission control".
// Deep navy base, maroon-red for risk/urgency, muted grays for structure.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#070b16",
          900: "#0a1020",
          850: "#0d1426",
          800: "#111a30",
          700: "#16223f",
          600: "#1d2c50",
        },
        maroon: {
          600: "#7f1d2e",
          500: "#9b2235",
          400: "#c02a44",
          300: "#e23a57",
        },
        edge: {
          DEFAULT: "#1c2740",
          soft: "#16203a",
        },
        signal: {
          live: "#3ddc97",
          warn: "#f2b84b",
          dim: "#5b6680",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(61,220,151,0.25), 0 0 24px -6px rgba(61,220,151,0.35)",
        risk: "0 0 0 1px rgba(192,42,68,0.35), 0 0 28px -6px rgba(192,42,68,0.45)",
      },
      keyframes: {
        pulseDot: {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.4", transform: "scale(0.85)" },
        },
        riskPulse: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(192,42,68,0.0)" },
          "50%": { boxShadow: "0 0 22px -4px rgba(192,42,68,0.55)" },
        },
      },
      animation: {
        pulseDot: "pulseDot 1.6s ease-in-out infinite",
        riskPulse: "riskPulse 2.2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
export default config;

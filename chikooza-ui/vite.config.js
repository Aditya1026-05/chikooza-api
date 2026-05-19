import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // U: OLD: CRA only exposed REACT_APP_* variables.
  // U: NEW: Vite uses VITE_*; keep REACT_APP_* temporarily for local setup compatibility.
  envPrefix: ["VITE_", "REACT_APP_"],
  build: {
    outDir: "build",
  },
});

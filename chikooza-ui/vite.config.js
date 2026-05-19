import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  // U: OLD: CRA only exposed REACT_APP_* variables.
  // U: NEW: Vite uses VITE_*; keep REACT_APP_* temporarily for local setup compatibility.
  envPrefix: ["VITE_", "REACT_APP_"],
  resolve: {
    alias: {
      // U: OLD: "reactstrap" resolved to the package, which still depends on a React 18-only react-popper peer.
      // U: NEW: keep existing imports but route them to a small Bootstrap 5 compatibility wrapper.
      reactstrap: path.resolve(projectRoot, "src/components/BootstrapCompat.jsx"),
    },
  },
  build: {
    outDir: "build",
  },
  css: {
    preprocessorOptions: {
      scss: {
        // U: OLD: Sass printed hundreds of known Bootstrap 5.3 deprecation warnings on every build.
        // U: NEW: keep warnings actionable while Bootstrap finishes its module-system migration.
        quietDeps: true,
        silenceDeprecations: ["import", "global-builtin", "color-functions", "if-function"],
      },
    },
  },
});

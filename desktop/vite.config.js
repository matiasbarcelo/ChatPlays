import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  root: __dirname,
  base: "./",
  resolve: {
    alias: {
      "@assets": path.resolve(__dirname, "../UI/assets"),
      "@fonts": path.resolve(__dirname, "../UI/fonts"),
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, "index.html"),
        setup: path.resolve(__dirname, "setup.html"),
        monitor: path.resolve(__dirname, "monitor.html"),
      },
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    fs: {
      allow: [__dirname, path.resolve(__dirname, "../UI")],
    },
  },
});

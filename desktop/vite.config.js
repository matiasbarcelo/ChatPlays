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
        controller: path.resolve(__dirname, "controller.html"),
        chat: path.resolve(__dirname, "chat.html"),
      },
    },
  },
  server: {
    // Bind IPv4 explicitly: the default resolves to ::1 only on this machine,
    // and electron/main.js plus `wait-on` both check 127.0.0.1.
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    fs: {
      allow: [__dirname, path.resolve(__dirname, "../UI")],
    },
  },
});

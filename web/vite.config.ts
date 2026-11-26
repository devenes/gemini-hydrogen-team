import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  build: {
    target: "esnext",
    outDir: path.resolve(__dirname, "../src/hydrogen_team/static"),
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8042",
        changeOrigin: true,
      },
    },
  },
});

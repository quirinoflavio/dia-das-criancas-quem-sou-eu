import { defineConfig } from "vite";
import preact from "@preact/preset-vite";

// Build vai para app/static (servido pelo FastAPI em produção).
// Em dev, proxy de /api e /ws para o backend em 8000.
export default defineConfig({
  plugins: [preact()],
  build: {
    outDir: "../app/static",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
    },
  },
});

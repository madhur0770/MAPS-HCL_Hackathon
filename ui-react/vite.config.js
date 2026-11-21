import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
const api = "http://localhost:8000";
export default defineConfig({
  plugins: [react()],
  build: { outDir: "../app/static", emptyOutDir: true },
  server: { port: 5173, proxy: { "/chat": api, "/actions": api, "/bookings": api, "/ingest": api, "/trace": api, "/health": api, "/demo": api, "/admin": api } },
});

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/unesp-odonto-pwa/",
  publicDir: "web/public",
  build: {
    outDir: "dist",
    emptyOutDir: true
  }
});

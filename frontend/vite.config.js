import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const desktop = mode === "desktop";

  return {
    base: desktop ? "/desktop/" : "/",
    plugins: [react(), tailwindcss()],
    server: { host: "0.0.0.0", port: 5173 },
    build: {
      outDir: desktop ? "../backend/desktop_frontend" : "dist",
      emptyOutDir: true,
      rollupOptions: {
        output: {
          manualChunks: {
            charts: ["recharts"],
            icons: ["lucide-react"],
            http: ["axios"],
          },
        },
      },
    },
  };
});

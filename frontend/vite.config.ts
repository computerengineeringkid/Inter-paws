import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const isProduction = mode === "production";
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: "http://localhost:5000",
          changeOrigin: true
        }
      }
    },
    build: {
      outDir: "../backend/app/static/app",
      emptyOutDir: true,
      manifest: false,
      rollupOptions: {
        input: "src/main.tsx",
        output: {
          entryFileNames: `assets/[name].js`,
          chunkFileNames: `assets/[name].js`,
          assetFileNames: `assets/[name][extname]`
        }
      }
    },
    define: {
      __DEV__: !isProduction
    }
  };
});

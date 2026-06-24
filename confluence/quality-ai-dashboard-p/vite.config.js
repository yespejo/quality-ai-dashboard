import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [
    react()
  ],
  // base: "./" makes Vite generate relative asset paths (./assets/...)
  // instead of absolute paths (/assets/...).
  // This is required for Forge Custom UI because the app is served
  // from within an iframe and absolute paths won't resolve correctly.
  base: "./",
  build: {
    // Output to static/dashboard so Forge picks it up via manifest.yml resource path
    outDir: 'static/dashboard',
    emptyOutDir: true
  }
})
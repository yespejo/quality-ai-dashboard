import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // base: "./" generates relative asset paths (./assets/...)
  // required for Forge Custom UI iframes.
  base: "./",
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
})

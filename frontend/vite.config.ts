import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { localFileSystemPlugin } from './vite-plugin-local-fs'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), localFileSystemPlugin()],
})

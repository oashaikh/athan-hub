import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  // The LG TV (webOS 5) runs Chromium 68.
  build: { target: 'chrome68', cssTarget: 'chrome68' },
  server: { proxy: { '/api': 'http://127.0.0.1:9000' } },
  test: { environment: 'jsdom', setupFiles: ['./src/test/setup.ts'] }
})

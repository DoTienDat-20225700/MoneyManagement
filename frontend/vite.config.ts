import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          mui: ['@mui/material', '@mui/icons-material', '@emotion/react', '@emotion/styled'],
          charts: ['apexcharts', 'react-apexcharts'],
          datagrid: ['@mui/x-data-grid', '@mui/x-date-pickers'],
        },
      },
    },
    chunkSizeWarningLimit: 1000,
  },
})


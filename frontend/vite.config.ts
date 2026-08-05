import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import tailwindcss from '@tailwindcss/vite'

// React handles JSX/Fast Refresh via oxc (Rust, fast).
// The babel plugin runs separately just to apply React Compiler's
// automatic memoization — this two-plugin split is required as of
// @vitejs/plugin-react v6, which removed its built-in Babel support.
export default defineConfig({
  plugins: [
    react(),
    babel({ plugins: ['babel-plugin-react-compiler'] }),
    tailwindcss(),
  ],
})
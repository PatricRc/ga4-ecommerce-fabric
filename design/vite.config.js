import { defineConfig } from 'vite';
import { resolve } from 'node:path';
export default defineConfig({server:{host:'0.0.0.0',allowedHosts:['terminal.local']},build:{rollupOptions:{input:Object.fromEntries(['index','pages/overview','pages/acquisition','pages/content','pages/funnel','components/index'].map(x=>[x,resolve(import.meta.dirname,x+'.html')]))}}});

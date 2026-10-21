import {defineConfig} from 'vite';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig({base:'/static/adm227/',plugins:[tailwindcss()],build:{outDir:'dist'}});

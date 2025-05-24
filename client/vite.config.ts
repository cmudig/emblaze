import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import anywidget from '@anywidget/vite';
import postcss from './postcss.config.js';

// https://vitejs.dev/config/
export default defineConfig({
  build: {
    outDir: '../emblaze/static',
    minify: false,
    lib: {
      entry: ['src/widget-main.js'],
      formats: ['es'],
    },
  },
  plugins: [
    svelte(),
    anywidget(),
    {
      name: 'asset-base-url',
      enforce: 'post',
      apply: 'serve',
      transform: (code, id) => {
        code = code.replace(
          /(from |import\()("|'|`)(\/src|~?@|\/@fs\/@)\/(.*?)\.(svg|png|mp3|mp4)/g,
          '$1$2http://localhost:5173/src/$4.$5?import='
        );
        code = code.replace(
          /(?<!local)(\/src|~?@|\/@fs\/@)\/(.*?)\.(svg|png|mp3|mp4)/g,
          'http://localhost:5173/src/$2.$3'
        );
        return {
          code,
          map: null,
        };
      },
    },
  ],
  css: { postcss },
});

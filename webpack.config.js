const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const path = require('path');
const version = require('./package.json').version;

module.exports = module.exports = (env, options) => {
  const prod = options.mode === 'production';

  // Custom webpack rules
  const rules = [
    {
      test: /\.svelte$/,
      use: {
        loader: 'svelte-loader',
        options: {
          compilerOptions: {
            dev: !prod,
          },
          emitCss: true,
        },
      },
    },
    { test: /\.ts$/, loader: 'ts-loader' },
    { test: /\.js$/, loader: 'source-map-loader' },
    {
      test: /\.m?js$/,
      exclude: /(node_modules|bower_components)/,
      use: {
        loader: 'babel-loader',
        options: {
          presets: ['@babel/preset-env'],
        },
      },
    },
  ];

  const standaloneCssRules = [
    { test: /\.css$/, use: [MiniCssExtractPlugin.loader, 'css-loader'] },
  ];

  const widgetCssRules = [
    { test: /\.css$/, use: ['style-loader', 'css-loader'] },
  ];

  // Packages that shouldn't be bundled but loaded at runtime
  const externals = ['@jupyter-widgets/base'];

  const resolve = {
    alias: {
      svelte: path.resolve('node_modules', 'svelte'),
    },
    // Add '.ts' and '.tsx' as resolvable extensions.
    extensions: ['.webpack.js', '.web.js', '.mjs', '.ts', '.js', '.svelte'],
    mainFields: ['svelte', 'browser', 'module', 'main'],
  };

  return [
    /** Standalone app */
    {
      entry: './src/standalone.ts',
      name: 'standalone',
      output: {
        filename: 'bundle.js',
        path: path.resolve(__dirname, 'emblaze', 'public', 'build'),
        chunkFilename: '[name].[id].js',
        publicPath: '/build',
      },
      module: {
        rules: [...rules, ...standaloneCssRules],
      },
      devtool: prod ? false : 'source-map',
      externals,
      resolve,
      plugins: [
        new MiniCssExtractPlugin({
          filename: 'bundle.css',
        }),
      ],
      devServer: {
        hot: true,
        contentBase: ['./src', './emblaze/public'], // both src and output dirs
        inline: true,
      },
    },

    /** Lib */
    {
      entry: {
        plugin: './src/plugin.ts',
      },
      output: {
        filename: 'index.js',
        path: path.resolve(__dirname, 'lib'),
        libraryTarget: 'amd',
      },
      module: {
        rules: [...rules, ...widgetCssRules],
      },
      name: 'lib',
      devtool: 'source-map',
      externals,
      resolve,
    },
    /**
     * Notebook extension
     *
     * This bundle only contains the part of the JavaScript that is run on load of
     * the notebook.
     */
    {
      entry: './src/extension.ts',
      output: {
        filename: 'index.js',
        path: path.resolve(__dirname, 'emblaze', 'nbextension', 'static'),
        libraryTarget: 'amd',
      },
      module: {
        rules: [...rules, ...widgetCssRules],
      },
      name: 'extension',
      devtool: 'source-map',
      externals,
      resolve,
    },

    /**
     * Embeddable emblaze bundle
     *
     * This bundle is almost identical to the notebook extension bundle. The only
     * difference is in the configuration of the webpack public path for the
     * static assets.
     *
     * The target bundle is always `dist/index.js`, which is the path required by
     * the custom widget embedder.
     */
    {
      entry: './src/index.ts',
      output: {
        filename: 'index.js',
        path: path.resolve(__dirname, 'dist'),
        libraryTarget: 'amd',
        library: 'emblaze',
        publicPath: 'https://unpkg.com/emblaze@' + version + '/dist/',
      },
      devtool: 'source-map',
      module: {
        rules: [...rules, ...widgetCssRules],
      },
      name: 'widget',
      externals,
      resolve,
    },

    /**
     * Documentation widget bundle
     *
     * This bundle is used to embed widgets in the package documentation.
     */
    {
      entry: './src/index.ts',
      output: {
        filename: 'embed-bundle.js',
        path: path.resolve(__dirname, 'docs', 'source', '_static'),
        library: 'emblaze',
        libraryTarget: 'amd',
      },
      module: {
        rules: [...rules, ...widgetCssRules],
      },
      name: 'docs',
      devtool: 'source-map',
      externals,
      resolve,
    },
  ];
};

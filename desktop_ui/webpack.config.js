const path = require('path');
const webpack = require('webpack');

// 判断当前是开发模式还是生产模式
const isDev = process.env.NODE_ENV !== 'production';

// 通用配置，主进程和渲染进程都会用到
const baseConfig = {
  mode: isDev ? 'development' : 'production',
  // 在开发模式下开启 source map
  devtool: isDev ? 'inline-source-map' : false,
  // 解析模块的方式
  resolve: {
    extensions: ['.ts', '.js'],
  },
  // 模块加载规则
  module: {
    rules: [
      {
        test: /\.ts$/,
        exclude: /node_modules/,
        use: 'ts-loader',
      },
    ],
  },
  // 插件
  plugins: [
    // 定义环境变量，可以在代码中访问
    new webpack.DefinePlugin({
      'process.env.NODE_ENV': JSON.stringify(isDev ? 'development' : 'production'),
    }),
  ],
  // 告诉 webpack 如何处理 Node.js 的内置模块
  node: {
    __dirname: false,
    __filename: false,
  },
};

// 主进程的特定配置
const mainConfig = {
  ...baseConfig, // 继承通用配置
  target: 'electron-main',
  entry: {
    main: './src/main.ts',
  },
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: '[name].js',
  },
};

// 预加载脚本的特定配置
const preloadConfig = {
  ...baseConfig,
  target: 'electron-preload',
  entry: {
    preload: './src/preload.ts',
    // capture.ts 也是一个预加载脚本，因为它需要访问 Node.js API
    capture: './src/capture.ts',
  },
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: '[name].js',
  },
};

// 渲染进程的特定配置
const rendererConfig = {
  ...baseConfig,
  target: 'electron-renderer',
  entry: {
    renderer: './src/renderer.ts',
  },
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: '[name].js',
  },
};

// 导出多配置数组
module.exports = [mainConfig, preloadConfig, rendererConfig];
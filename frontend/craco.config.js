module.exports = {
  webpack: {
    configure: (webpackConfig) => {
      // Disable CSS minification
      const miniCssExtractPlugin = webpackConfig.plugins.find(
        plugin => plugin.constructor.name === 'MiniCssExtractPlugin'
      );

      if (miniCssExtractPlugin) {
        miniCssExtractPlugin.options = {
          ...miniCssExtractPlugin.options,
          ignoreOrder: true
        };
      }

      // Find and modify CSS minimizer
      if (webpackConfig.optimization && webpackConfig.optimization.minimizer) {
        webpackConfig.optimization.minimizer = webpackConfig.optimization.minimizer.filter(
          minimizer => minimizer.constructor.name !== 'CssMinimizerPlugin'
        );
      }

      return webpackConfig;
    }
  },
  devServer: {
    allowedHosts: 'all',
    host: 'localhost',
    port: 3000,
    hot: true,
    client: {
      overlay: {
        warnings: false,
        errors: true
      }
    }
  }
};
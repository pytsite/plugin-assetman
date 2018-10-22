const path = require('path');
const fs = require('fs');
const webpackMerge = require('webpack-merge');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const UglifyJsPlugin = require("uglifyjs-webpack-plugin");
const OptimizeCSSAssetsPlugin = require("optimize-css-assets-webpack-plugin");

module.exports = env => {
    const devMode = env.NODE_ENV !== 'production';

    let config = {
        entry: [],
        output: {},
        optimization: {
            splitChunks: {
                chunks: 'all',
            }
        },
        plugins: [
            new MiniCssExtractPlugin(),
        ],
        module: {
            rules: [
                {
                    test: /\.m?js$/,
                    exclude: /(node_modules|bower_components)/,
                    use: {
                        loader: 'babel-loader',
                        options: {
                            presets: ['@babel/preset-env', '@babel/preset-react'],
                            plugins: [
                                '@babel/plugin-proposal-class-properties',
                                '@babel/plugin-transform-runtime',
                                '@babel/plugin-syntax-dynamic-import',
                            ],
                        }
                    }
                },
                {
                    test: /\.(jpg|jpeg|png|svg)$/,
                    loader: 'file-loader',
                    options: {
                        outputPath: 'img'
                    }
                },
                {
                    test: /\.(ttf|eot|woff|woff2)$/,
                    loader: 'file-loader',
                    options: {
                        outputPath: 'font'
                    }
                },
                {
                    test: /\.css$/,
                    use: [
                        {loader: MiniCssExtractPlugin.loader},
                        {loader: 'css-loader'},
                    ]
                },
                {
                    test: /\.less$/,
                    use: [
                        {loader: MiniCssExtractPlugin.loader},
                        {loader: 'css-loader'},
                        {loader: 'less-loader'},
                    ]
                },
                {
                    test: /\.scss$/,
                    use: [
                        {loader: MiniCssExtractPlugin.loader},
                        {loader: 'css-loader'},
                        {loader: 'sass-loader'},
                    ]
                },
            ]
        },
    };

    if (!devMode) {
        config = webpackMerge(config, {
            optimization: {
                minimizer: [
                    new UglifyJsPlugin({
                        cache: true,
                        parallel: true,
                        extractComments: true,
                    }),
                    new OptimizeCSSAssetsPlugin({
                        cssProcessorOptions: {
                            discardComments: {removeAll: true},
                        }
                    })
                ]
            },
        });
    }

    fs.readdirSync(env.plugins_dir).forEach((val) => {
        const configPart = path.join(env.plugins_dir, val, 'res', 'assets', 'webpack.part.js');
        if (fs.existsSync(configPart))
            config = webpackMerge(config, require(configPart));
    });

    return config;
};

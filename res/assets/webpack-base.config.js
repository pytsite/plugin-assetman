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
        output: {
            filename: "main.js"
        },
        // TODO
        // optimization: {
        //     splitChunks: {
        //         chunks: 'all'
        //     }
        // },
        plugins: [
            new MiniCssExtractPlugin({
                filename: "[name].css",
                chunkFilename: "[id].css"
            })
        ],
        module: {
            rules: [
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
            module: {
                rules: [
                    {
                        test: /\.m?js$/,
                        exclude: /(node_modules|bower_components)/,
                        use: {
                            loader: 'babel-loader',
                            options: {
                                presets: ['@babel/preset-env'],
                                plugins: ['@babel/plugin-transform-runtime'],
                            }
                        }
                    }
                ],
            },
            optimization: {
                minimizer: [
                    new UglifyJsPlugin({
                        cache: true,
                        parallel: true,
                    }),
                    new OptimizeCSSAssetsPlugin({})
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

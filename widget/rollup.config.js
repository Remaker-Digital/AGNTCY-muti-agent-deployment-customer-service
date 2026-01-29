/**
 * ============================================================================
 * Rollup Configuration - AGNTCY Chat Widget Build Pipeline
 * ============================================================================
 *
 * Purpose: Bundle the chat widget for CDN distribution
 *
 * Build Outputs:
 * - agntcy-chat.min.js - Minified IIFE for <script> tag embedding
 * - agntcy-chat.esm.js - ES Module for modern bundlers
 * - agntcy-chat.js - Unminified for debugging
 *
 * Why Rollup (not Webpack)?
 * - Better tree-shaking for library code
 * - Smaller bundle sizes for simple libraries
 * - Native ES module output support
 * - Simpler configuration for single-file libraries
 *
 * Related Documentation:
 * - Widget Source: widget/src/chat-widget.js
 * - CDN Deployment: terraform/phase4_prod/cdn.tf
 * ============================================================================
 */

import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import babel from '@rollup/plugin-babel';
import terser from '@rollup/plugin-terser';
import filesize from 'rollup-plugin-filesize';
import license from 'rollup-plugin-license';
import path from 'path';

const isDev = process.env.BUILD === 'development';
const pkg = require('./package.json');

// Banner for license header
const banner = `
/*!
 * AGNTCY Chat Widget v${pkg.version}
 * (c) ${new Date().getFullYear()} AGNTCY Team
 * Released under the MIT License
 */
`;

// Common plugins used across all builds
const commonPlugins = [
    resolve({
        browser: true,
    }),
    commonjs(),
    babel({
        babelHelpers: 'bundled',
        exclude: 'node_modules/**',
        presets: [
            ['@babel/preset-env', {
                targets: pkg.browserslist,
                modules: false,
            }]
        ]
    }),
    license({
        banner: {
            commentStyle: 'none',
            content: banner.trim(),
        },
    }),
    filesize(),
];

// Terser configuration for minification
const terserConfig = {
    compress: {
        pure_funcs: isDev ? [] : ['console.log', 'console.debug'],
        drop_debugger: !isDev,
    },
    format: {
        comments: /^!/,  // Preserve license comments
    },
};

export default [
    // ========================================================================
    // IIFE Build - For direct <script> tag embedding
    // ========================================================================
    // This is the primary distribution format for merchants
    // Exposes AGNTCYChat global variable
    {
        input: 'src/chat-widget.js',
        output: {
            file: 'dist/agntcy-chat.min.js',
            format: 'iife',
            name: 'AGNTCYChat',
            sourcemap: isDev,
            // Export the init function and public API
            exports: 'named',
        },
        plugins: [
            ...commonPlugins,
            !isDev && terser(terserConfig),
        ].filter(Boolean),
    },

    // ========================================================================
    // ES Module Build - For modern bundlers (Webpack, Vite, etc.)
    // ========================================================================
    // Allows tree-shaking when used with modern build tools
    {
        input: 'src/chat-widget.js',
        output: {
            file: 'dist/agntcy-chat.esm.js',
            format: 'es',
            sourcemap: isDev,
        },
        plugins: [
            ...commonPlugins,
            !isDev && terser(terserConfig),
        ].filter(Boolean),
    },

    // ========================================================================
    // Development Build - Unminified for debugging
    // ========================================================================
    {
        input: 'src/chat-widget.js',
        output: {
            file: 'dist/agntcy-chat.js',
            format: 'iife',
            name: 'AGNTCYChat',
            sourcemap: true,
        },
        plugins: commonPlugins,
    },
];

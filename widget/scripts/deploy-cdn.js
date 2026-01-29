#!/usr/bin/env node
/**
 * ============================================================================
 * CDN Deployment Script - AGNTCY Chat Widget
 * ============================================================================
 *
 * Purpose: Deploy built widget files to Azure Blob Storage with CDN
 *
 * Prerequisites:
 * - Azure CLI installed and authenticated (`az login`)
 * - Environment variables configured (see .env.example)
 * - Widget built (`npm run build`)
 *
 * Environment Variables:
 * - AZURE_STORAGE_ACCOUNT: Storage account name
 * - AZURE_STORAGE_CONTAINER: Container name (default: 'widget')
 * - AZURE_CDN_ENDPOINT: CDN endpoint name
 * - AZURE_CDN_PROFILE: CDN profile name
 * - AZURE_RESOURCE_GROUP: Resource group name
 *
 * Usage:
 *   npm run deploy                     # Deploy to production
 *   npm run deploy -- --env staging    # Deploy to staging
 *   npm run deploy -- --purge          # Deploy and purge CDN cache
 *
 * Related Documentation:
 * - Terraform CDN: terraform/phase4_prod/cdn.tf
 * - Azure Blob Storage: https://docs.microsoft.com/azure/storage/blobs/
 * ============================================================================
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// ============================================================================
// Configuration
// ============================================================================

const CONFIG = {
    storageAccount: process.env.AZURE_STORAGE_ACCOUNT || 'agntcywidgetstorage',
    container: process.env.AZURE_STORAGE_CONTAINER || 'widget',
    cdnEndpoint: process.env.AZURE_CDN_ENDPOINT || 'agntcy-widget-cdn',
    cdnProfile: process.env.AZURE_CDN_PROFILE || 'agntcy-cdn-profile',
    resourceGroup: process.env.AZURE_RESOURCE_GROUP || 'agntcy-prod-rg',
    distDir: path.resolve(__dirname, '../dist'),
};

// File content types for proper serving
const CONTENT_TYPES = {
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.map': 'application/json',
    '.html': 'text/html',
};

// Cache control headers
// Widget files are versioned, so we can cache aggressively
const CACHE_CONTROL = 'public, max-age=31536000, immutable';  // 1 year

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Execute shell command and return output
 */
function exec(command, options = {}) {
    console.log(`> ${command}`);
    try {
        return execSync(command, {
            encoding: 'utf-8',
            stdio: options.silent ? 'pipe' : 'inherit',
            ...options,
        });
    } catch (error) {
        if (options.ignoreError) {
            return null;
        }
        throw error;
    }
}

/**
 * Get content type for file
 */
function getContentType(filename) {
    const ext = path.extname(filename).toLowerCase();
    return CONTENT_TYPES[ext] || 'application/octet-stream';
}

/**
 * Get list of files to deploy
 */
function getFilesToDeploy() {
    if (!fs.existsSync(CONFIG.distDir)) {
        console.error('Error: dist/ directory not found. Run "npm run build" first.');
        process.exit(1);
    }

    return fs.readdirSync(CONFIG.distDir)
        .filter(file => !file.startsWith('.'))
        .map(file => ({
            name: file,
            path: path.join(CONFIG.distDir, file),
            contentType: getContentType(file),
        }));
}

/**
 * Parse command line arguments
 */
function parseArgs() {
    const args = process.argv.slice(2);
    return {
        env: args.includes('--staging') ? 'staging' : 'production',
        purge: args.includes('--purge'),
        dryRun: args.includes('--dry-run'),
        help: args.includes('--help') || args.includes('-h'),
    };
}

// ============================================================================
// Deployment Functions
// ============================================================================

/**
 * Upload files to Azure Blob Storage
 */
function uploadFiles(files, args) {
    console.log('\n=== Uploading files to Azure Blob Storage ===\n');

    const pkg = require('../package.json');
    const version = pkg.version;

    for (const file of files) {
        // Upload versioned file (e.g., agntcy-chat.1.0.0.min.js)
        const versionedName = file.name.replace(/(\.[^.]+)$/, `.${version}$1`);

        if (args.dryRun) {
            console.log(`[DRY RUN] Would upload: ${file.name} -> ${versionedName}`);
            console.log(`[DRY RUN] Would upload: ${file.name} -> ${file.name} (latest)`);
        } else {
            // Upload versioned copy
            exec(`az storage blob upload \
                --account-name ${CONFIG.storageAccount} \
                --container-name ${CONFIG.container} \
                --name "${versionedName}" \
                --file "${file.path}" \
                --content-type "${file.contentType}" \
                --content-cache-control "${CACHE_CONTROL}" \
                --overwrite`);

            // Upload as 'latest' (same filename, shorter cache)
            exec(`az storage blob upload \
                --account-name ${CONFIG.storageAccount} \
                --container-name ${CONFIG.container} \
                --name "${file.name}" \
                --file "${file.path}" \
                --content-type "${file.contentType}" \
                --content-cache-control "public, max-age=3600" \
                --overwrite`);

            console.log(`Uploaded: ${file.name} (versioned: ${versionedName})`);
        }
    }
}

/**
 * Purge CDN cache
 */
function purgeCDN(files, args) {
    console.log('\n=== Purging CDN cache ===\n');

    // Purge all uploaded file paths
    const paths = files.map(f => `/${f.name}`);

    if (args.dryRun) {
        console.log(`[DRY RUN] Would purge CDN paths: ${paths.join(', ')}`);
    } else {
        exec(`az cdn endpoint purge \
            --resource-group ${CONFIG.resourceGroup} \
            --profile-name ${CONFIG.cdnProfile} \
            --name ${CONFIG.cdnEndpoint} \
            --content-paths ${paths.map(p => `"${p}"`).join(' ')}`);

        console.log(`Purged CDN cache for: ${paths.join(', ')}`);
    }
}

/**
 * Display deployment summary
 */
function displaySummary(files, args) {
    const pkg = require('../package.json');

    console.log('\n=== Deployment Summary ===\n');
    console.log(`Version: ${pkg.version}`);
    console.log(`Environment: ${args.env}`);
    console.log(`Files deployed: ${files.length}`);
    console.log(`Storage account: ${CONFIG.storageAccount}`);
    console.log(`CDN endpoint: ${CONFIG.cdnEndpoint}`);
    console.log('\nCDN URLs:');

    for (const file of files) {
        if (file.name.endsWith('.min.js')) {
            console.log(`  https://${CONFIG.cdnEndpoint}.azureedge.net/${file.name}`);
            console.log(`  https://${CONFIG.cdnEndpoint}.azureedge.net/${file.name.replace(/(\.[^.]+)$/, `.${pkg.version}$1`)}`);
        }
    }
}

/**
 * Show help message
 */
function showHelp() {
    console.log(`
AGNTCY Chat Widget CDN Deployment Script

Usage: npm run deploy [options]

Options:
  --staging     Deploy to staging environment
  --purge       Purge CDN cache after deployment
  --dry-run     Show what would be deployed without actually deploying
  --help, -h    Show this help message

Environment Variables:
  AZURE_STORAGE_ACCOUNT   Storage account name (default: agntcywidgetstorage)
  AZURE_STORAGE_CONTAINER Container name (default: widget)
  AZURE_CDN_ENDPOINT      CDN endpoint name (default: agntcy-widget-cdn)
  AZURE_CDN_PROFILE       CDN profile name (default: agntcy-cdn-profile)
  AZURE_RESOURCE_GROUP    Resource group name (default: agntcy-prod-rg)

Examples:
  npm run deploy                  # Deploy to production
  npm run deploy -- --purge       # Deploy and purge CDN cache
  npm run deploy -- --dry-run     # Preview deployment
`);
}

// ============================================================================
// Main Execution
// ============================================================================

function main() {
    const args = parseArgs();

    if (args.help) {
        showHelp();
        process.exit(0);
    }

    console.log('=========================================');
    console.log(' AGNTCY Chat Widget CDN Deployment');
    console.log('=========================================');

    // Check Azure CLI authentication
    console.log('\nChecking Azure CLI authentication...');
    const accountInfo = exec('az account show --output json', { silent: true, ignoreError: true });
    if (!accountInfo) {
        console.error('Error: Not logged in to Azure CLI. Run "az login" first.');
        process.exit(1);
    }

    // Get files to deploy
    const files = getFilesToDeploy();
    console.log(`\nFound ${files.length} files to deploy:`);
    files.forEach(f => console.log(`  - ${f.name} (${f.contentType})`));

    // Upload files
    uploadFiles(files, args);

    // Purge CDN if requested
    if (args.purge) {
        purgeCDN(files, args);
    }

    // Display summary
    displaySummary(files, args);

    console.log('\nDeployment complete!');
}

main();

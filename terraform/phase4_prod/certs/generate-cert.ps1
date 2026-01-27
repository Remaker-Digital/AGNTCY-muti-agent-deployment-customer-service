# Generate Self-Signed Certificate for Application Gateway
# Run this script to create a PFX file for testing
# For production, replace with a certificate from Azure Key Vault or Let's Encrypt

param(
    [string]$CertPassword = "AgntcyAppGw2026!",
    [string]$OutputPath = $PSScriptRoot,
    [string]$DnsName = "agntcy-cs-prod.eastus2.cloudapp.azure.com"
)

Write-Host "Generating self-signed certificate for Application Gateway..." -ForegroundColor Cyan

# Create the certificate
$cert = New-SelfSignedCertificate `
    -DnsName $DnsName, "*.agntcy.local", "localhost" `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -KeyAlgorithm RSA `
    -KeyLength 2048 `
    -NotAfter (Get-Date).AddYears(1) `
    -KeyUsage DigitalSignature, KeyEncipherment `
    -Type SSLServerAuthentication `
    -Subject "CN=$DnsName"

Write-Host "Certificate created with thumbprint: $($cert.Thumbprint)" -ForegroundColor Green

# Export as PFX
$pfxPath = Join-Path $OutputPath "appgw-cert.pfx"
$securePassword = ConvertTo-SecureString -String $CertPassword -Force -AsPlainText

Export-PfxCertificate `
    -Cert "Cert:\CurrentUser\My\$($cert.Thumbprint)" `
    -FilePath $pfxPath `
    -Password $securePassword | Out-Null

Write-Host "Certificate exported to: $pfxPath" -ForegroundColor Green

# Export as CER (public key only, for reference)
$cerPath = Join-Path $OutputPath "appgw-cert.cer"
Export-Certificate `
    -Cert "Cert:\CurrentUser\My\$($cert.Thumbprint)" `
    -FilePath $cerPath | Out-Null

Write-Host "Public certificate exported to: $cerPath" -ForegroundColor Green

# Output password for Terraform
Write-Host ""
Write-Host "=== IMPORTANT ===" -ForegroundColor Yellow
Write-Host "Certificate password: $CertPassword" -ForegroundColor Yellow
Write-Host ""
Write-Host "Add this to your terraform.tfvars:" -ForegroundColor Cyan
Write-Host "ssl_certificate_password = `"$CertPassword`"" -ForegroundColor White
Write-Host ""
Write-Host "Or set as environment variable:" -ForegroundColor Cyan
Write-Host "Set-Item -Path env:TF_VAR_ssl_certificate_password -Value '$CertPassword'" -ForegroundColor White

# Clean up - remove from cert store (optional, uncomment if desired)
# Remove-Item "Cert:\CurrentUser\My\$($cert.Thumbprint)"

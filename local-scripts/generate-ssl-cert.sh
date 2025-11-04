#!/bin/bash
# SSL Certificate Generation Script
# Generates self-signed SSL certificates for local and AWS environments

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
LOCAL_DOMAIN="crypto-ai.local"
AWS_DOMAIN="crypto-ai.crypto-vision.com"
CERT_DIR="$PROJECT_ROOT/certs"
LOCAL_CERT_DIR="$CERT_DIR/local"
AWS_CERT_DIR="$CERT_DIR/aws"

# Certificate settings
CERT_DAYS=365
KEY_SIZE=2048
COUNTRY="US"
STATE="State"
CITY="City"
ORGANIZATION="Crypto Market Analysis SaaS"
ORGANIZATIONAL_UNIT="Development"

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

log_info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check if OpenSSL is available
check_openssl() {
    if ! command -v openssl >/dev/null 2>&1; then
        log_error "OpenSSL is not installed or not in PATH"
        log_error "Please install OpenSSL:"
        log_error "  Ubuntu/Debian: sudo apt-get install openssl"
        log_error "  CentOS/RHEL: sudo yum install openssl"
        log_error "  macOS: brew install openssl"
        log_error "  Windows: Install Git Bash or use WSL"
        exit 1
    fi
    
    log "OpenSSL version: $(openssl version)"
}

# Create certificate directories
create_cert_dirs() {
    log "Creating certificate directories..."
    
    mkdir -p "$LOCAL_CERT_DIR"
    mkdir -p "$AWS_CERT_DIR"
    
    # Set proper permissions
    chmod 755 "$CERT_DIR"
    chmod 755 "$LOCAL_CERT_DIR"
    chmod 755 "$AWS_CERT_DIR"
    
    log "Certificate directories created:"
    log "  Local: $LOCAL_CERT_DIR"
    log "  AWS: $AWS_CERT_DIR"
}

# Generate certificate for a domain
generate_certificate() {
    local domain="$1"
    local cert_dir="$2"
    local env_name="$3"
    
    log "Generating SSL certificate for $domain ($env_name environment)..."
    
    local key_file="$cert_dir/key.pem"
    local cert_file="$cert_dir/cert.pem"
    local csr_file="$cert_dir/cert.csr"
    local config_file="$cert_dir/openssl.conf"
    
    # Create OpenSSL configuration file
    cat > "$config_file" << EOF
[req]
default_bits = $KEY_SIZE
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C=$COUNTRY
ST=$STATE
L=$CITY
O=$ORGANIZATION
OU=$ORGANIZATIONAL_UNIT
CN=$domain

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = $domain
DNS.2 = localhost
DNS.3 = 127.0.0.1
IP.1 = 127.0.0.1
EOF

    # Add additional SANs for local environment
    if [[ "$env_name" == "local" ]]; then
        cat >> "$config_file" << EOF
DNS.4 = *.crypto-ai.local
DNS.5 = crypto-ai.localhost
IP.2 = ::1
EOF
    fi
    
    # Generate private key
    log_info "Generating private key..."
    openssl genrsa -out "$key_file" $KEY_SIZE
    
    # Generate certificate signing request
    log_info "Generating certificate signing request..."
    openssl req -new -key "$key_file" -out "$csr_file" -config "$config_file"
    
    # Generate self-signed certificate
    log_info "Generating self-signed certificate..."
    openssl x509 -req -in "$csr_file" -signkey "$key_file" -out "$cert_file" \
        -days $CERT_DAYS -extensions v3_req -extfile "$config_file"
    
    # Set proper permissions
    chmod 600 "$key_file"
    chmod 644 "$cert_file"
    chmod 644 "$csr_file"
    chmod 644 "$config_file"
    
    # Clean up CSR file (optional)
    rm -f "$csr_file"
    
    log "Certificate generated successfully:"
    log "  Private key: $key_file"
    log "  Certificate: $cert_file"
    log "  Valid for: $CERT_DAYS days"
    
    # Display certificate information
    log_info "Certificate details:"
    openssl x509 -in "$cert_file" -text -noout | grep -E "(Subject:|DNS:|IP Address:|Not Before|Not After)"
}

# Verify certificate
verify_certificate() {
    local cert_file="$1"
    local key_file="$2"
    local domain="$3"
    
    log "Verifying certificate for $domain..."
    
    # Check if certificate and key match
    local cert_hash=$(openssl x509 -noout -modulus -in "$cert_file" | openssl md5)
    local key_hash=$(openssl rsa -noout -modulus -in "$key_file" | openssl md5)
    
    if [[ "$cert_hash" == "$key_hash" ]]; then
        log "✓ Certificate and private key match"
    else
        log_error "✗ Certificate and private key do not match"
        return 1
    fi
    
    # Check certificate validity
    if openssl x509 -checkend 86400 -noout -in "$cert_file" >/dev/null; then
        log "✓ Certificate is valid for at least 24 hours"
    else
        log_warn "⚠ Certificate expires within 24 hours"
    fi
    
    # Check if certificate is for the correct domain
    local cert_subject=$(openssl x509 -noout -subject -in "$cert_file" | sed 's/.*CN=\([^,]*\).*/\1/')
    if [[ "$cert_subject" == "$domain" ]]; then
        log "✓ Certificate subject matches domain: $domain"
    else
        log_warn "⚠ Certificate subject ($cert_subject) does not match domain ($domain)"
    fi
}

# Create certificate bundle
create_certificate_bundle() {
    local cert_dir="$1"
    local env_name="$2"
    
    log "Creating certificate bundle for $env_name environment..."
    
    local cert_file="$cert_dir/cert.pem"
    local key_file="$cert_dir/key.pem"
    local bundle_file="$cert_dir/bundle.pem"
    
    # Create bundle (certificate + private key)
    cat "$cert_file" "$key_file" > "$bundle_file"
    chmod 600 "$bundle_file"
    
    log "Certificate bundle created: $bundle_file"
}

# Generate PKCS#12 format (for some applications)
generate_pkcs12() {
    local cert_dir="$1"
    local domain="$2"
    local env_name="$3"
    
    log "Generating PKCS#12 certificate for $domain..."
    
    local cert_file="$cert_dir/cert.pem"
    local key_file="$cert_dir/key.pem"
    local p12_file="$cert_dir/cert.p12"
    
    # Generate PKCS#12 file (no password for development)
    openssl pkcs12 -export -out "$p12_file" -inkey "$key_file" -in "$cert_file" \
        -name "$domain" -passout pass:
    
    chmod 600 "$p12_file"
    
    log "PKCS#12 certificate created: $p12_file"
}

# Create certificate information file
create_cert_info() {
    local cert_dir="$1"
    local domain="$2"
    local env_name="$3"
    
    local cert_file="$cert_dir/cert.pem"
    local info_file="$cert_dir/cert-info.txt"
    
    log "Creating certificate information file..."
    
    cat > "$info_file" << EOF
SSL Certificate Information
===========================

Environment: $env_name
Domain: $domain
Generated: $(date)
Valid for: $CERT_DAYS days

Certificate Details:
$(openssl x509 -in "$cert_file" -text -noout)

Certificate Fingerprints:
SHA256: $(openssl x509 -noout -fingerprint -sha256 -in "$cert_file" | cut -d= -f2)
SHA1:   $(openssl x509 -noout -fingerprint -sha1 -in "$cert_file" | cut -d= -f2)
MD5:    $(openssl x509 -noout -fingerprint -md5 -in "$cert_file" | cut -d= -f2)

Files:
- Certificate: $(basename "$cert_file")
- Private Key: key.pem
- Bundle: bundle.pem
- PKCS#12: cert.p12
- Config: openssl.conf

Usage Instructions:
===================

For Nginx:
ssl_certificate     $cert_file;
ssl_certificate_key $cert_dir/key.pem;

For Apache:
SSLCertificateFile    $cert_file
SSLCertificateKeyFile $cert_dir/key.pem

For Python/Flask:
app.run(ssl_context=('$cert_file', '$cert_dir/key.pem'))

For Node.js:
const options = {
  key: fs.readFileSync('$cert_dir/key.pem'),
  cert: fs.readFileSync('$cert_file')
};

Security Notes:
===============
- These are self-signed certificates for development use only
- Browsers will show security warnings for self-signed certificates
- For production, use certificates from a trusted CA
- Keep private keys secure and never commit them to version control

EOF
    
    log "Certificate information saved: $info_file"
}

# Print usage instructions
print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -l, --local-only     Generate certificate for local environment only"
    echo "  -a, --aws-only       Generate certificate for AWS environment only"
    echo "  -d, --domain DOMAIN  Custom domain name (overrides default)"
    echo "  -t, --days DAYS      Certificate validity in days (default: $CERT_DAYS)"
    echo "  -h, --help           Show this help message"
    echo
    echo "Examples:"
    echo "  $0                   Generate certificates for both environments"
    echo "  $0 --local-only      Generate certificate for local development only"
    echo "  $0 --aws-only        Generate certificate for AWS deployment only"
    echo "  $0 -d example.com    Generate certificate for custom domain"
    echo "  $0 -t 730            Generate certificate valid for 2 years"
}

# Print installation instructions
print_installation_instructions() {
    log_info "Installation Instructions:"
    echo
    echo "Local Development:"
    echo "1. Add the following to your /etc/hosts file (or C:\\Windows\\System32\\drivers\\etc\\hosts on Windows):"
    echo "   127.0.0.1 $LOCAL_DOMAIN"
    echo
    echo "2. Trust the certificate in your browser:"
    echo "   - Chrome: Go to chrome://settings/certificates, import cert.pem"
    echo "   - Firefox: Go to about:preferences#privacy, import cert.pem"
    echo "   - Safari: Double-click cert.pem and add to Keychain"
    echo
    echo "3. Configure your application to use the certificates:"
    echo "   - Certificate: $LOCAL_CERT_DIR/cert.pem"
    echo "   - Private Key: $LOCAL_CERT_DIR/key.pem"
    echo
    echo "AWS Deployment:"
    echo "1. Copy certificates to your EC2 instance:"
    echo "   scp -i your-key.pem $AWS_CERT_DIR/* ec2-user@your-instance:/etc/ssl/"
    echo
    echo "2. Configure Nginx or your web server to use the certificates"
    echo
    echo "3. Update DNS to point $AWS_DOMAIN to your EC2 instance IP"
    echo
    log_warn "Remember: These are self-signed certificates for development use only!"
    log_warn "For production, use certificates from a trusted Certificate Authority."
}

# Main function
main() {
    local generate_local=true
    local generate_aws=true
    local custom_domain=""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -l|--local-only)
                generate_local=true
                generate_aws=false
                shift
                ;;
            -a|--aws-only)
                generate_local=false
                generate_aws=true
                shift
                ;;
            -d|--domain)
                custom_domain="$2"
                shift 2
                ;;
            -t|--days)
                CERT_DAYS="$2"
                shift 2
                ;;
            -h|--help)
                print_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done
    
    log "Starting SSL certificate generation..."
    
    # Check prerequisites
    check_openssl
    
    # Create certificate directories
    create_cert_dirs
    
    # Generate local certificate
    if [[ "$generate_local" == true ]]; then
        local domain="$LOCAL_DOMAIN"
        if [[ -n "$custom_domain" ]]; then
            domain="$custom_domain"
        fi
        
        generate_certificate "$domain" "$LOCAL_CERT_DIR" "local"
        verify_certificate "$LOCAL_CERT_DIR/cert.pem" "$LOCAL_CERT_DIR/key.pem" "$domain"
        create_certificate_bundle "$LOCAL_CERT_DIR" "local"
        generate_pkcs12 "$LOCAL_CERT_DIR" "$domain" "local"
        create_cert_info "$LOCAL_CERT_DIR" "$domain" "local"
    fi
    
    # Generate AWS certificate
    if [[ "$generate_aws" == true ]]; then
        local domain="$AWS_DOMAIN"
        if [[ -n "$custom_domain" ]]; then
            domain="$custom_domain"
        fi
        
        generate_certificate "$domain" "$AWS_CERT_DIR" "aws"
        verify_certificate "$AWS_CERT_DIR/cert.pem" "$AWS_CERT_DIR/key.pem" "$domain"
        create_certificate_bundle "$AWS_CERT_DIR" "aws"
        generate_pkcs12 "$AWS_CERT_DIR" "$domain" "aws"
        create_cert_info "$AWS_CERT_DIR" "$domain" "aws"
    fi
    
    log "SSL certificate generation completed successfully!"
    
    # Print installation instructions
    print_installation_instructions
}

# Run main function with all arguments
main "$@"
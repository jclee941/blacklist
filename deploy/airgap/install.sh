#!/bin/bash
set -euo pipefail

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
log_step() { echo -e "\n${CYAN}===${NC} ${BOLD}$1${NC}\n"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGES_DIR="${SCRIPT_DIR}/images"

install_docker_offline() {
    log_step "Offline Docker Installation"
    
    local prereqs_dir="${SCRIPT_DIR}/prereqs"
    if [ ! -d "$prereqs_dir" ]; then
        log_error "prereqs/ directory not found. Cannot install Docker."
    fi

    log_info "Installing Docker Engine..."
    # Find docker tarball
    local docker_tgz=$(find "${prereqs_dir}" -name "docker-*.tgz" | head -n 1)
    if [ -z "$docker_tgz" ]; then
        log_error "Docker binary tarball not found in prereqs/"
    fi
    
    # Extract to /usr/bin
    if ! tar -xzf "$docker_tgz" -C /usr/bin --strip-components=1; then
        log_error "Failed to extract Docker binaries"
    fi
    
    # Setup service
    if [ -f "${prereqs_dir}/docker.service" ]; then
        cp "${prereqs_dir}/docker.service" /etc/systemd/system/
        systemctl daemon-reload
        systemctl enable --now docker
        sleep 5
    else
        log_error "docker.service not found in prereqs/"
    fi
}

install_docker_compose() {
    log_info "Installing Docker Compose Plugin..."
    local prereqs_dir="${SCRIPT_DIR}/prereqs"
    local compose_bin="${prereqs_dir}/docker-compose-linux-x86_64"
    
    if [ ! -f "$compose_bin" ]; then
        log_error "Docker Compose binary not found in prereqs/"
    fi
    
    mkdir -p /usr/libexec/docker/cli-plugins
    cp "$compose_bin" /usr/libexec/docker/cli-plugins/docker-compose
    chmod +x /usr/libexec/docker/cli-plugins/docker-compose
}

preflight_checks() {
    log_step "Preflight Checks"

    if ! command -v docker &> /dev/null; then
        log_warning "Docker not found. Attempting offline installation..."
        install_docker_offline
    fi
    log_success "Docker $(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"

    if ! docker compose version &> /dev/null; then
         log_warning "Docker Compose not found. Attempting offline installation..."
         install_docker_compose
    fi
    log_success "Docker Compose $(docker compose version --short)"

    if [ ! -d "${IMAGES_DIR}" ]; then
        log_error "images/ directory not found"
    fi

    local required_images=(
        "app.tar.gz"
        "collector.tar.gz"
        "frontend.tar.gz"
        "postgres.tar.gz"
        "redis.tar.gz"
    )

    for img in "${required_images[@]}"; do
        if [ -f "${IMAGES_DIR}/${img}" ]; then
            log_success "${img} ($(du -h "${IMAGES_DIR}/${img}" | cut -f1))"
        elif [ -f "${IMAGES_DIR}/blacklist-${img}" ]; then
            log_success "blacklist-${img} ($(du -h "${IMAGES_DIR}/blacklist-${img}" | cut -f1))"
        else
            log_error "${img} not found"
        fi
    done

    if [ ! -f "${SCRIPT_DIR}/docker-compose.yml" ]; then
        log_error "docker-compose.yml not found"
    fi
    log_success "docker-compose.yml"

    # Support both checksum filenames (legacy: SHA256SUMS, current: checksums.sha256)
    local CHECKSUM_FILE=""
    if [ -f "${IMAGES_DIR}/checksums.sha256" ]; then
        CHECKSUM_FILE="checksums.sha256"
        log_success "checksums.sha256"
    elif [ -f "${IMAGES_DIR}/SHA256SUMS" ]; then
        CHECKSUM_FILE="SHA256SUMS"
        log_success "SHA256SUMS"
    else
        log_warning "Checksum file not found (integrity check will be skipped)"
    fi

    local available_gb=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "${available_gb}" -lt 3 ]; then
        log_warning "Low disk space: ${available_gb}GB (recommend 3GB+)"
    else
        log_success "Disk space: ${available_gb}GB"
    fi

    for port in 443 2542 5432 6379 8545; do
        if ss -tuln 2>/dev/null | grep -q ":${port} "; then
            log_warning "Port ${port} in use"
        fi
    done
}

verify_checksums() {
    log_step "Verify Image Integrity (SHA256)"

    local CHECKSUM_FILE=""
    if [ -f "${IMAGES_DIR}/checksums.sha256" ]; then
        CHECKSUM_FILE="checksums.sha256"
    elif [ -f "${IMAGES_DIR}/SHA256SUMS" ]; then
        CHECKSUM_FILE="SHA256SUMS"
    fi

    if [ -z "$CHECKSUM_FILE" ]; then
        log_warning "Checksum file not found, skipping verification"
        return 0
    fi

    cd "${IMAGES_DIR}"
    if sha256sum -c "$CHECKSUM_FILE" --status 2>/dev/null; then
        log_success "All checksums verified"
    else
        log_info "Verifying individual files..."
        local failed=0
        while IFS='  ' read -r expected_hash filename; do
            if [ -f "$filename" ]; then
                actual_hash=$(sha256sum "$filename" | awk '{print $1}')
                if [ "$expected_hash" = "$actual_hash" ]; then
                    log_success "${filename}: OK"
                else
                    log_error "${filename}: CHECKSUM MISMATCH (corrupted or tampered)"
                    failed=1
                fi
            fi
        done < "$CHECKSUM_FILE"
        if [ "$failed" -eq 1 ]; then
            log_error "Integrity check failed. Re-download the airgap package."
        fi
    fi
    cd "${SCRIPT_DIR}"
}

load_images() {
    log_step "Load Docker Images"

    local images=(
        "app.tar.gz"
        "collector.tar.gz"
        "frontend.tar.gz"
        "postgres.tar.gz"
        "redis.tar.gz"
    )

    for img in "${images[@]}"; do
        local name="${img%.tar.gz}"
        local img_path="${IMAGES_DIR}/${img}"
        # Support both app.tar.gz and blacklist-app.tar.gz naming
        if [ ! -f "${img_path}" ] && [ -f "${IMAGES_DIR}/blacklist-${img}" ]; then
            img_path="${IMAGES_DIR}/blacklist-${img}"
        fi
        log_info "Loading ${name}..."
        if gunzip -c "${img_path}" | docker load > /dev/null 2>&1; then
            log_success "${name}"
        else
            log_error "Failed to load ${name}"
        fi
    done

    log_success "All images loaded"
}

setup_ssl() {
    log_step "Setup SSL Certificates"

    local ssl_dir="${SCRIPT_DIR}/ssl"
    mkdir -p "${ssl_dir}"

    if [ -f "${ssl_dir}/server.crt" ] && [ -f "${ssl_dir}/server.key" ]; then
        log_info "SSL certificates already exist"
        return 0
    fi

    log_info "Generating self-signed certificate..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "${ssl_dir}/server.key" \
        -out "${ssl_dir}/server.crt" \
        -subj "/CN=blacklist/O=Blacklist/C=KR" \
        2>/dev/null

    chmod 644 "${ssl_dir}/server.key" "${ssl_dir}/server.crt"
    log_success "SSL certificates created"
}

setup_secrets() {
    log_step "Setup Environment Secrets"

    local env_file="${SCRIPT_DIR}/.env"
    local need_gen=false

    # Check if .env exists and has required keys
    if [ -f "${env_file}" ]; then
        if grep -q "CREDENTIAL_MASTER_KEY=.\+" "${env_file}" && \
           grep -q "SECRET_KEY=.\+" "${env_file}" && \
           grep -q "CREDENTIAL_ENCRYPTION_KEY=.\+" "${env_file}"; then
            log_info ".env already exists with all required secrets"
            return 0
        else
            log_warning ".env exists but missing required secrets, regenerating..."
            need_gen=true
        fi
    else
        need_gen=true
    fi

    if [ "$need_gen" = true ]; then
        log_info "Generating secrets..."
        
        local fernet_key=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64)
        local secret_key=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n')
        local master_key=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n')
        
        cat > "${env_file}" << EOF
# Blacklist Platform Secrets (auto-generated)
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

CREDENTIAL_MASTER_KEY=${master_key}
SECRET_KEY=${secret_key}
CREDENTIAL_ENCRYPTION_KEY=${fernet_key}
EOF

        chmod 600 "${env_file}"
        log_success "Secrets generated (.env)"
        log_warning "Store .env securely - it contains encryption keys"
    fi
}

deploy_services() {
    log_step "Deploy Services"

    cd "${SCRIPT_DIR}"

    local containers="blacklist-app blacklist-collector blacklist-frontend blacklist-postgres blacklist-redis"
    for c in $containers; do
        if docker ps -aq -f "name=^${c}$" | grep -q .; then
            log_info "Removing existing container: ${c}..."
            docker rm -f "$c" 2>/dev/null || true
        fi
    done

    log_info "Starting services..."
    docker compose up -d 2>&1 | grep -v "^$" || true

    log_info "Waiting for services to initialize (30s)..."
    sleep 30

    log_success "Services started"
}

health_checks() {
    log_step "Health Checks"

    docker compose ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || docker compose ps

    local endpoints=(
        "http://localhost:2542/api/health|API"
        "http://localhost:8545/health|Collector"
    )

    echo ""
    for ep in "${endpoints[@]}"; do
        local url="${ep%|*}"
        local name="${ep#*|}"
        if curl -s "${url}" 2>/dev/null | grep -q "healthy\|status"; then
            log_success "${name}: healthy"
        else
            log_warning "${name}: not responding"
        fi
    done

    if curl -sk "https://localhost:443" > /dev/null 2>&1; then
        log_success "Frontend: accessible"
    else
        log_warning "Frontend: not responding"
    fi
}

post_install() {
    log_step "Installation Complete"

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  Blacklist Platform Deployed Successfully                  ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Access Points:"
    echo "  Frontend:  https://localhost:443"
    echo "  API:       http://localhost:2542/api/health"
    echo "  Collector: http://localhost:8545/health"
    echo ""
    echo "Management:"
    echo "  Status:    docker compose ps"
    echo "  Logs:      docker compose logs -f"
    echo "  Stop:      docker compose down"
    echo "  Restart:   docker compose restart"
    echo ""
}

show_help() {
    echo "Blacklist Airgap Installer"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --skip-load    Skip image loading (images already loaded)"
    echo "  --skip-ssl     Skip SSL certificate generation"
    echo "  --help, -h     Show this help"
    echo ""
}

main() {
    local skip_load=false
    local skip_ssl=false

    for arg in "$@"; do
        case $arg in
            --skip-load) skip_load=true ;;
            --skip-ssl) skip_ssl=true ;;
            --help|-h) show_help; exit 0 ;;
            *) log_warning "Unknown option: $arg" ;;
        esac
    done

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  Blacklist Airgap Installer v1.0                          ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""

    preflight_checks
    verify_checksums

    if [ "$skip_load" = false ]; then
        load_images
    else
        log_info "Skipping image load (--skip-load)"
    fi

    if [ "$skip_ssl" = false ]; then
        setup_ssl
    else
        log_info "Skipping SSL setup (--skip-ssl)"
    fi

    setup_secrets

    deploy_services
    health_checks
    post_install

    log_success "Installation completed!"
}

main "$@"

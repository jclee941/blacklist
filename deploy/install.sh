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
VERSION="$(cat "${SCRIPT_DIR}/VERSION" 2>/dev/null || echo 'unknown')"
readonly REQUIRED_SECRET_KEYS=(
    "CREDENTIAL_MASTER_KEY"
    "SECRET_KEY"
    "CREDENTIAL_ENCRYPTION_KEY"
    "ENCRYPTION_SALT"
    "POSTGRES_PASSWORD"
    "ADMIN_USERNAME"
    "ADMIN_PASSWORD"
)
readonly DEPLOYMENT_VOLUME_NAMES=(
    "blacklist-pgdata"
    "blacklist-redis-data"
    "blacklist-collector-data"
    "blacklist-logs"
    "blacklist-uploads"
    "blacklist-app-data"
    "blacklist_blacklist-pgdata"
    "blacklist_blacklist-redis-data"
    "blacklist_blacklist-collector-data"
    "blacklist_blacklist-logs"
    "blacklist_blacklist-uploads"
    "blacklist_blacklist-app-data"
)
readonly VARIABLE_REFERENCE_PREFIX="\${"

install_docker_offline() {
    log_step "Offline Docker Installation"
    
    local prereqs_dir="${SCRIPT_DIR}/prereqs"
    if [ ! -d "$prereqs_dir" ]; then
        log_error "prereqs/ directory not found. Cannot install Docker."
    fi

    log_info "Installing Docker Engine..."
    # Find docker tarball
    local docker_tgz
    docker_tgz=$(find "${prereqs_dir}" -name "docker-*.tgz" | head -n 1)
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

    local available_gb
    available_gb=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
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
                    echo -e "${RED}[FAIL]${NC} ${filename}: CHECKSUM MISMATCH"
                    failed=1
                fi
            fi
        done < "$CHECKSUM_FILE"
        if [ "$failed" -eq 1 ]; then
            log_error "Integrity check failed. Re-download the release package."
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
        local load_output
        if load_output=$(gunzip -c "${img_path}" | docker load 2>&1); then
            # Extract loaded image name:tag (e.g. "blacklist-app:3.5.41") and tag as :latest
            local loaded_image
            loaded_image=$(echo "$load_output" | grep -oP 'Loaded image: \K.*' | head -1)
            if [ -n "$loaded_image" ]; then
                local repo="${loaded_image%%:*}"
                docker tag "$loaded_image" "${repo}:latest" 2>/dev/null || true
            fi
            log_success "${name}"
        else
            log_error "Failed to load ${name}"
        fi
    done

    log_success "All images loaded"
}

trim_whitespace() {
    local value="$1"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    printf '%s' "${value}"
}

normalize_dotenv_value() {
    local value
    value=$(trim_whitespace "$1")

    case "${value}" in
        \"*)
            if [[ "${value}" =~ ^\"(.*)\"[[:space:]]*(\#.*)?$ ]]; then
                DOTENV_NORMALIZED_VALUE="${BASH_REMATCH[1]}"
            else
                return 1
            fi
            ;;
        \'*)
            if [[ "${value}" =~ ^\'(.*)\'[[:space:]]*(\#.*)?$ ]]; then
                DOTENV_NORMALIZED_VALUE="${BASH_REMATCH[1]}"
            else
                return 1
            fi
            ;;
        *)
            value="${value%%[[:space:]]\#*}"
            DOTENV_NORMALIZED_VALUE=$(trim_whitespace "${value}")
            ;;
    esac

    [ -n "${DOTENV_NORMALIZED_VALUE}" ]
}

read_required_secret_value() {
    local env_file="$1"
    local required_key="$2"
    local line value=""
    local matches=0

    DOTENV_NORMALIZED_VALUE=""
    while IFS= read -r line || [ -n "${line}" ]; do
        line="${line%$'\r'}"
        [[ "${line}" =~ ^[[:space:]]*$ || "${line}" =~ ^[[:space:]]*\# ]] && continue

        if [[ "${line}" =~ ^[[:space:]]*(export[[:space:]]+)?${required_key}[[:space:]]*=(.*)$ ]]; then
            matches=$((matches + 1))
            value="${BASH_REMATCH[2]}"
        fi
    done < "${env_file}"

    [ "${matches}" -eq 1 ] || return 1
    normalize_dotenv_value "${value}"
}

deployment_state_exists() {
    local container_ids volume

    command -v docker > /dev/null 2>&1 || return 1

    if ! container_ids=$(docker ps -aq --filter 'name=^/blacklist-'); then
        log_error "Unable to inspect Docker deployment state; refusing to generate secrets."
    fi
    [ -n "${container_ids}" ] && return 0

    for volume in "${DEPLOYMENT_VOLUME_NAMES[@]}"; do
        if docker volume inspect "${volume}" > /dev/null 2>&1; then
            return 0
        fi
    done

    return 1
}

generate_env_file() {
    local env_file="$1"
    local temp_file
    local fernet_key secret_key master_key encryption_salt pg_password admin_username admin_password

    temp_file=$(mktemp "${env_file}.tmp.XXXXXX") || log_error "Unable to create private environment file."
    chmod 600 "${temp_file}" || log_error "Unable to protect generated environment file."

    fernet_key=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64)
    secret_key=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n')
    master_key=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n')
    encryption_salt=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n')
    pg_password=$(openssl rand -hex 16 2>/dev/null || head -c 16 /dev/urandom | xxd -p | tr -d '\n')
    admin_username="admin-$(openssl rand -hex 8 2>/dev/null || head -c 8 /dev/urandom | xxd -p | tr -d '\n')"
    admin_password=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64)

    if ! cat > "${temp_file}" << EOF
# Blacklist Platform Secrets (auto-generated)
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

COMPOSE_PROJECT_NAME=blacklist
CREDENTIAL_MASTER_KEY=${master_key}
SECRET_KEY=${secret_key}
CREDENTIAL_ENCRYPTION_KEY=${fernet_key}
ENCRYPTION_SALT=${encryption_salt}
POSTGRES_PASSWORD=${pg_password}
ADMIN_USERNAME=${admin_username}
ADMIN_PASSWORD=${admin_password}
EOF
    then
        rm -f "${temp_file}"
        log_error "Unable to write generated environment file."
    fi

    if ! mv "${temp_file}" "${env_file}"; then
        rm -f "${temp_file}"
        log_error "Unable to save generated environment file."
    fi
}

setup_secrets() {
    log_step "Setup Environment Secrets"

    umask 077

    local env_file="${SCRIPT_DIR}/.env"
    if [ -f "${env_file}" ]; then
        chmod 600 "${env_file}" || log_error "Unable to protect existing environment file."
    else
        if deployment_state_exists; then
            log_error "Existing deployment state detected; refusing to generate new secrets. Restore the original .env."
        fi

        log_info "Generating secrets..."
        generate_env_file "${env_file}"
        chmod 600 "${env_file}" || log_error "Unable to protect generated environment file."
        log_success "Secrets generated (.env)"
        log_warning "Administrator credentials were generated; record them securely before deployment."
    fi

    local invalid_keys=()
    local key value
    for key in "${REQUIRED_SECRET_KEYS[@]}"; do
        if ! read_required_secret_value "${env_file}" "${key}"; then
            invalid_keys+=("${key}")
            continue
        fi

        value="${DOTENV_NORMALIZED_VALUE}"
        if [ -z "${value}" ] ||
           [[ "${value}" == op://* ]] ||
           [[ "${value}" == *"${VARIABLE_REFERENCE_PREFIX}"* ]] ||
           [[ "${value}" =~ \$[A-Za-z_][A-Za-z0-9_]* ]] ||
           [[ "${value}" == __SET_* ]] ||
           { [ "${key}" = "POSTGRES_PASSWORD" ] && [ "${value}" = "postgres" ]; }; then
            invalid_keys+=("${key}")
        fi
    done

    if [ "${#invalid_keys[@]}" -gt 0 ]; then
        log_error "Invalid or unresolved secret values: ${invalid_keys[*]}. Restore literal target-local values in .env."
    fi

    log_success ".env secret validation passed"
    log_warning "Back up .env securely; upgrades require the same encryption keys"
}

stop_all_running_containers() {
    log_step "Stop Running Containers"

    local running_ids=()
    local running_output
    if ! running_output=$(docker ps -q); then
        log_error "Failed to list running containers"
    fi
    if [ -n "${running_output}" ]; then
        mapfile -t running_ids <<< "${running_output}"
    fi

    if [ "${#running_ids[@]}" -eq 0 ]; then
        log_info "No running containers found"
        return 0
    fi

    log_info "Stopping ${#running_ids[@]} running container(s)..."
    if ! docker stop "${running_ids[@]}" > /dev/null; then
        log_error "Failed to stop all running containers"
    fi

    local remaining_output
    if ! remaining_output=$(docker ps -q); then
        log_error "Failed to verify stopped containers"
    fi
    if [ -n "${remaining_output}" ]; then
        log_error "Some containers are still running after stop"
    fi
    log_success "All running containers stopped"
}

deploy_services() {
    log_step "Deploy Services"

    cd "${SCRIPT_DIR}"

    # Backup current image tags for rollback
    local backup_file="${SCRIPT_DIR}/.rollback-images"
    if docker images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep -q '^blacklist-'; then
        docker images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep '^blacklist-' | grep -v '<none>' > "${backup_file}" || true
        log_info "Current image tags saved to .rollback-images"
    fi

    local containers="blacklist-app blacklist-collector blacklist-frontend blacklist-postgres blacklist-redis"
    for c in $containers; do
        if docker ps -aq -f "name=^${c}$" | grep -q .; then
            log_info "Removing existing container: ${c}..."
            docker rm -f "$c" 2>/dev/null || true
        fi
    done

    log_info "Starting services..."
    local compose_output
    if ! compose_output=$(docker compose up -d 2>&1); then
        printf '%s\n' "${compose_output}"
        log_error "Failed to start Blacklist services"
    fi
    printf '%s\n' "${compose_output}"

    log_info "Waiting for services to initialize (30s)..."
    sleep 30

    log_success "Services started"
}

validate_compose_config() {
    log_step "Validate Compose Configuration"
    if ! (cd "${SCRIPT_DIR}" && docker compose config --quiet); then
        log_error "Compose configuration validation failed"
    fi
    log_success "Compose configuration"
}

health_checks() {
    log_step "Health Checks"

    if ! docker compose ps --format "table {{.Name}}\t{{.Status}}"; then
        log_error "Failed to read service status"
    fi

    local endpoints=(
        "http://localhost:2542/health|API"
        "http://localhost:8545/health|Collector"
    )

    echo ""
    for ep in "${endpoints[@]}"; do
        local url="${ep%|*}"
        local name="${ep#*|}"
        if curl -s "${url}" 2>/dev/null | grep -q "healthy\|status"; then
            log_success "${name}: healthy"
        else
            log_error "${name}: not responding"
        fi
    done

    if curl -sk "https://localhost:443" > /dev/null 2>&1; then
        log_success "Frontend: accessible"
    else
        log_error "Frontend: not responding"
    fi
}

post_install() {
    log_step "Installation Complete"

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  Blacklist Platform ${VERSION} Deployed Successfully      ║"
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
    echo "Blacklist Offline Installer"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --skip-load    Skip image loading (images already loaded)"
    echo "  --check-secrets Generate or validate .env, then exit"
    echo "  --help, -h     Show this help"
    echo ""
}

main() {
    local skip_load=false
    local check_secrets=false

    for arg in "$@"; do
        case $arg in
            --skip-load) skip_load=true ;;
            --check-secrets) check_secrets=true ;;
            --help|-h) show_help; exit 0 ;;
            *) log_warning "Unknown option: $arg" ;;
        esac
    done

    if [ "$check_secrets" = true ]; then
        setup_secrets
        return 0
    fi

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  Blacklist Offline Installer ${VERSION}                   ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""

    preflight_checks
    verify_checksums

    if [ "$skip_load" = false ]; then
        load_images
    else
        log_info "Skipping image load (--skip-load)"
    fi

    setup_secrets
    validate_compose_config
    stop_all_running_containers

    deploy_services
    health_checks
    post_install

    log_success "Installation completed!"
}

main "$@"

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
ENV_FILE="${BLACKLIST_ENV_FILE:-/etc/blacklist/.env}"
STOP_ALL_CONTAINERS=false
SKIP_POSTURE_CHECK=false
REQUIRE_SIGNATURE=false
ADMIN_CREDENTIALS_GENERATED=false
POSTURE_COMPOSE_FILES=()
readonly PUBLISHED_FRONTEND_PORT=443
readonly HEALTH_WAIT_TIMEOUT_SECONDS=180
readonly HEALTH_POLL_INTERVAL_SECONDS=5
readonly REQUIRED_SECRET_KEYS=(
    "ADMIN_USERNAME"
    "ADMIN_PASSWORD"
    "CREDENTIAL_MASTER_KEY"
    "SECRET_KEY"
    "COLLECTOR_AUTH_TOKEN"
    "CREDENTIAL_ENCRYPTION_KEY"
    "ENCRYPTION_SALT"
    "POSTGRES_PASSWORD"
    "REDIS_PASSWORD"
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
readonly POSTURE_COMPOSE_CANDIDATES=(
    "docker-compose.yml"
    "docker-compose.override.yml"
)
readonly JWT_DEFERRAL_ADR="docs/decisions/0002-collector-authentication-enforcement.md"
readonly POSTURE_CHECK_PY='
import json
import shlex
import sys

ALLOWED_PUBLISHED_PORTS = {"blacklist-frontend": {"443"}}
JWT_ADR_SERVICE = "blacklist-collector"
JWT_DISABLED_VALUES = {"true", "1", "yes"}

adr_decision = sys.argv[1] if len(sys.argv) > 1 else "defer"
services = json.load(sys.stdin).get("services") or {}
findings = []

for name in sorted(services):
    service = services[name] or {}

    if service.get("network_mode") == "host":
        findings.append(name + ": network_mode: host is forbidden; every service must stay on the internal bridge network (C-04)")

    for port in service.get("ports") or []:
        published = str(port.get("published") or "")
        target = str(port.get("target") or "")
        if published not in ALLOWED_PUBLISHED_PORTS.get(name, frozenset()):
            findings.append(name + ": publishes host port " + (published or "ephemeral->" + target) + "; only blacklist-frontend may publish 443 (C-04, ADR-0001)")

    if name == "blacklist-redis":
        command = service.get("command") or []
        if isinstance(command, str):
            command = shlex.split(command)
        command = [str(part) for part in command]
        if "--requirepass" not in command:
            findings.append(name + ": redis command lacks --requirepass; a passwordless Redis is forbidden (C-04)")
        else:
            position = command.index("--requirepass") + 1
            if position >= len(command) or not command[position].strip():
                findings.append(name + ": --requirepass resolved to an empty value; REDIS_PASSWORD is unset or empty in the environment file (C-04)")

    # The collector flag must MATCH ADR-0002 in both directions. Under Decision: defer
    # enforcement does not exist, so claiming it is on is a false security posture;
    # under Decision: enforce the collector really does verify a bearer token, so
    # turning the flag back on silently reopens the control API (C-05).
    if name == JWT_ADR_SERVICE:
        flag = (service.get("environment") or {}).get("DISABLE_JWT_AUTH")
        if flag is not None:
            disabled = str(flag).strip().lower() in JWT_DISABLED_VALUES
            if adr_decision == "defer" and not disabled:
                findings.append(name + ": DISABLE_JWT_AUTH=" + str(flag) + " contradicts ADR-0002 (Decision: defer); collector token enforcement does not exist yet (C-05)")
            elif adr_decision == "enforce" and disabled:
                findings.append(name + ": DISABLE_JWT_AUTH=" + str(flag) + " contradicts ADR-0002 (Decision: enforce); this reopens the collector control API (C-05)")

for finding in findings:
    print(finding)

sys.exit(1 if findings else 0)
'

require_root() {
    [ "$(id -u)" -eq 0 ] || log_error "Root privileges are required to install; re-run as root (current EUID: $(id -u))."
}

normalize_manifest_records() {
    sed -E 's/^([[:xdigit:]]{64})[[:space:]]+(\*)?(\.\/)?/\1  /' "${SCRIPT_DIR}/MANIFEST.sha256"
}

verify_manifest_entry() {
    local relative_path="${1#./}"
    relative_path="${relative_path#\*}"

    local expected_hash=""
    local listed_hash listed_path
    while read -r listed_hash listed_path; do
        if [ "${listed_path}" = "${relative_path}" ]; then
            expected_hash="${listed_hash}"
            break
        fi
    done < <(normalize_manifest_records)

    if ! [[ "${expected_hash}" =~ ^[[:xdigit:]]{64}$ ]]; then
        log_error "Manifest entry missing or malformed: ${relative_path}"
    fi

    local actual_hash
    if ! actual_hash=$(sha256sum "${SCRIPT_DIR}/${relative_path}" 2>/dev/null | awk '{print $1}'); then
        log_error "Manifest-listed file not found: ${relative_path}"
    fi
    if [ "${expected_hash,,}" != "${actual_hash}" ]; then
        log_error "Manifest verification failed for ${relative_path}"
    fi
}

verify_manifest() {
    log_step "Verify Bundle Manifest (SHA256)"

    local manifest_file="${SCRIPT_DIR}/MANIFEST.sha256"
    if [ ! -f "${manifest_file}" ]; then
        log_error "Bundle manifest not found: MANIFEST.sha256"
    fi

    local entry_count
    entry_count=$(awk 'NF { count++ } END { print count + 0 }' "${manifest_file}")
    if [ "${entry_count}" -eq 0 ]; then
        log_error "Bundle manifest contains no verifiable entries: MANIFEST.sha256"
    fi

    if ! (cd "${SCRIPT_DIR}" && normalize_manifest_records | sha256sum -c --strict -); then
        log_error "Bundle manifest verification failed"
    fi

    local docker_tgz=""
    if [ -d "${SCRIPT_DIR}/prereqs" ]; then
        docker_tgz=$(find "${SCRIPT_DIR}/prereqs" -maxdepth 1 -type f -name 'docker-*.tgz' -print -quit)
    fi
    if [ -n "${docker_tgz}" ]; then
        verify_manifest_entry "${docker_tgz#"${SCRIPT_DIR}/"}"
    fi

    local privileged_file
    for privileged_file in prereqs/docker.service prereqs/docker-compose-linux-x86_64; do
        if [ -f "${SCRIPT_DIR}/${privileged_file}" ]; then
            verify_manifest_entry "${privileged_file}"
        fi
    done

    log_success "Bundle manifest verified"
}

verify_manifest_signature() {
    log_step "Verify Bundle Manifest Signature"

    if [ ! -f /etc/blacklist/release-pubkey.gpg ]; then
        if [ "${REQUIRE_SIGNATURE}" = true ]; then
            log_error "Required release keyring not found: /etc/blacklist/release-pubkey.gpg"
        fi
        log_warning "Manifest signature verification skipped: host keyring not found at /etc/blacklist/release-pubkey.gpg"
        return 0
    fi

    if [ ! -f "${SCRIPT_DIR}/MANIFEST.sha256.asc" ]; then
        if [ "${REQUIRE_SIGNATURE}" = true ]; then
            log_error "Required detached signature not found: MANIFEST.sha256.asc"
        fi
        log_warning "Manifest signature verification skipped: MANIFEST.sha256.asc not found"
        return 0
    fi

    if ! (cd "${SCRIPT_DIR}" && gpgv --keyring /etc/blacklist/release-pubkey.gpg MANIFEST.sha256.asc MANIFEST.sha256); then
        log_error "Bundle manifest signature verification failed"
    fi

    log_success "Bundle manifest signature verified"
}

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
    local docker_relative="${docker_tgz#"${SCRIPT_DIR}/"}"
    
    # Extract to /usr/bin
    verify_manifest_entry "${docker_relative}"
    if ! tar -xzf "$docker_tgz" -C /usr/bin --strip-components=1; then
        log_error "Failed to extract Docker binaries"
    fi
    
    # Setup service
    if [ -f "${prereqs_dir}/docker.service" ]; then
        verify_manifest_entry "prereqs/docker.service"
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
    verify_manifest_entry "prereqs/docker-compose-linux-x86_64"
    cp "$compose_bin" /usr/libexec/docker/cli-plugins/docker-compose
    chmod +x /usr/libexec/docker/cli-plugins/docker-compose
}

preflight_verify() {
    log_step "Preflight Checks"

    verify_manifest
    verify_manifest_signature

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

    local image_path
    for img in "${required_images[@]}"; do
        image_path="${IMAGES_DIR}/blacklist-${img}"
        if [ -f "${image_path}" ]; then
            log_success "blacklist-${img} ($(du -h "${image_path}" | cut -f1))"
        else
            log_error "blacklist-${img} not found"
        fi
    done

    if [ ! -f "${SCRIPT_DIR}/docker-compose.yml" ]; then
        log_error "docker-compose.yml not found"
    fi
    log_success "docker-compose.yml"

    if [ ! -f "${IMAGES_DIR}/checksums.sha256" ]; then
        log_error "Checksum file not found: images/checksums.sha256"
    fi
    log_success "checksums.sha256"

    local disk_target="/var/lib"
    local docker_root_dir=""
    if command -v docker > /dev/null 2>&1; then
        if docker_root_dir=$(docker info --format '{{.DockerRootDir}}' 2>/dev/null) && [ -n "${docker_root_dir}" ]; then
            disk_target="${docker_root_dir}"
        fi
    fi

    local available_gb
    if ! available_gb=$(df -BG "${disk_target}" 2>/dev/null | awk 'NR == 2 {sub(/G$/, "", $4); print $4}'); then
        log_error "Unable to determine available disk space on ${disk_target}"
    fi
    if ! [[ "${available_gb}" =~ ^[0-9]+$ ]]; then
        log_error "Unable to parse available disk space on ${disk_target}"
    fi
    if [ "${available_gb}" -lt 3 ]; then
        log_error "Insufficient disk space on ${disk_target}: ${available_gb}GB available (3GB required)"
    else
        log_success "Disk space on ${disk_target}: ${available_gb}GB"
    fi

}

preflight_checks() {
    preflight_verify

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
}

verify_published_port_available() {
    log_step "Verify Published Port Availability"

    local listeners
    if ! listeners=$(ss -H -ltn "sport = :${PUBLISHED_FRONTEND_PORT}" 2>/dev/null); then
        log_error "Unable to inspect published port ${PUBLISHED_FRONTEND_PORT}"
    fi
    if [ -n "${listeners}" ]; then
        log_error "Published frontend port ${PUBLISHED_FRONTEND_PORT} is already in use"
    fi

    log_success "Published frontend port ${PUBLISHED_FRONTEND_PORT} is available"
}

verify_checksums() {
    log_step "Verify Image Integrity (SHA256)"

    local checksum_file="${IMAGES_DIR}/checksums.sha256"
    if [ ! -f "${checksum_file}" ]; then
        log_error "Checksum file not found: images/checksums.sha256"
    fi

    local checked=0
    local failed=0
    local expected_hash filename actual_hash
    while read -r expected_hash filename; do
        if [ -z "${expected_hash}" ] && [ -z "${filename}" ]; then
            continue
        fi

        filename="${filename#./}"
        filename="${filename#\*}"
        if [ ! -f "${IMAGES_DIR}/${filename}" ]; then
            log_error "Checksum-listed image not found: ${filename}"
        fi

        checked=$((checked + 1))
        actual_hash=$(sha256sum "${IMAGES_DIR}/${filename}" | awk '{print $1}')
        if [ "${expected_hash}" = "${actual_hash}" ]; then
            log_success "${filename}: OK"
        else
            echo -e "${RED}[FAIL]${NC} ${filename}: CHECKSUM MISMATCH"
            failed=1
        fi
    done < "${checksum_file}"

    if [ "${checked}" -eq 0 ]; then
        log_error "Checksum file contains no verifiable entries: images/checksums.sha256"
    fi
    if [ "${failed}" -eq 1 ]; then
        log_error "Integrity check failed. Re-download the release package."
    fi
    log_success "All checksums verified"
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
        local img_path="${IMAGES_DIR}/blacklist-${img}"
        log_info "Loading ${name}..."
        local load_output
        if load_output=$(gunzip -c "${img_path}" | docker load 2>&1); then
            local loaded_image
            loaded_image=$(printf '%s\n' "$load_output" | sed -n 's/^Loaded image: //p' | head -n 1)
            if [ -z "${loaded_image}" ]; then
                log_error "Unable to determine the loaded image tag for ${name}"
            fi
            log_success "${name} (${loaded_image})"
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
    local fernet_key secret_key collector_auth_token master_key encryption_salt pg_password redis_password admin_password

    temp_file=$(mktemp "${env_file}.tmp.XXXXXX") || log_error "Unable to create private environment file."
    chmod 600 "${temp_file}" || log_error "Unable to protect generated environment file."

    fernet_key=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64)
    secret_key=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n')
    collector_auth_token=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n')
    master_key=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n')
    encryption_salt=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n')
    pg_password=$(openssl rand -hex 16 2>/dev/null || head -c 16 /dev/urandom | xxd -p | tr -d '\n')
    redis_password=$(openssl rand -hex 16 2>/dev/null || head -c 16 /dev/urandom | xxd -p | tr -d '\n')
    admin_password=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n')

    if ! cat > "${temp_file}" << EOF
# Blacklist Platform Secrets (auto-generated)
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

COMPOSE_PROJECT_NAME=blacklist
BLACKLIST_VERSION=${VERSION}
ADMIN_USERNAME=admin
ADMIN_PASSWORD=${admin_password}
CREDENTIAL_MASTER_KEY=${master_key}
SECRET_KEY=${secret_key}
COLLECTOR_AUTH_TOKEN=${collector_auth_token}
CREDENTIAL_ENCRYPTION_KEY=${fernet_key}
ENCRYPTION_SALT=${encryption_salt}
POSTGRES_PASSWORD=${pg_password}
REDIS_PASSWORD=${redis_password}
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

# BLACKLIST_VERSION selects the image tag every compose file resolves. It is NOT a
# secret, and setup_secrets() deliberately never rewrites an existing environment
# file, so an upgrade would otherwise keep the previous release's tag and silently
# redeploy the old images. Re-sync it on every run instead.
sync_deployment_version() {
    local env_file="$1"
    local temp_file

    temp_file=$(mktemp "${env_file}.tmp.XXXXXX") || log_error "Unable to stage the environment file update."
    chmod 600 "${temp_file}" || log_error "Unable to protect the staged environment file."

    if ! { grep -v '^BLACKLIST_VERSION=' "${env_file}" || true; } > "${temp_file}"; then
        rm -f "${temp_file}"
        log_error "Unable to read the existing environment file: ${env_file}"
    fi

    if ! printf 'BLACKLIST_VERSION=%s\n' "${VERSION}" >> "${temp_file}"; then
        rm -f "${temp_file}"
        log_error "Unable to record the deployment version."
    fi

    if ! mv "${temp_file}" "${env_file}"; then
        rm -f "${temp_file}"
        log_error "Unable to update the environment file: ${env_file}"
    fi

    chmod 600 "${env_file}" || log_error "Unable to protect the updated environment file."
}

setup_secrets() {
    log_step "Setup Environment Secrets"

    umask 077

    install -d -m 700 "$(dirname "${ENV_FILE}")" || log_error "Unable to create the secret directory for ${ENV_FILE}."

    local env_file="${ENV_FILE}"
    if [ -f "${env_file}" ]; then
        chmod 600 "${env_file}" || log_error "Unable to protect existing environment file."
    else
        if deployment_state_exists; then
            log_error "Existing deployment state detected; refusing to generate new secrets. Restore the original ${env_file}."
        fi

        log_info "Generating secrets..."
        generate_env_file "${env_file}"
        chmod 600 "${env_file}" || log_error "Unable to protect generated environment file."
        ADMIN_CREDENTIALS_GENERATED=true
        log_success "Secrets generated (${env_file})"
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
        log_error "Invalid or unresolved secret values: ${invalid_keys[*]}. Restore literal target-local values in ${env_file}."
    fi

    log_success "Secret validation passed (${env_file})"
    sync_deployment_version "${env_file}"
    log_info "Deployment version pinned to ${VERSION}"
    log_warning "Back up ${env_file} securely; upgrades require the same encryption keys"
}

show_initial_admin_password() {
    if [ "${ADMIN_CREDENTIALS_GENERATED}" != true ]; then
        return 0
    fi

    if ! read_required_secret_value "${ENV_FILE}" "ADMIN_PASSWORD"; then
        log_error "Unable to read the generated administrator password from ${ENV_FILE}."
    fi
    local admin_password="${DOTENV_NORMALIZED_VALUE}"

    log_step "First-Run Administrator Credentials"
    log_warning "This administrator password is shown only once."
    log_warning "Store it in your password manager and change it after the first login."
    printf '  Admin username: admin\n'
    printf '  Admin password: %s\n' "${admin_password}"
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

wait_for_health() {
    local containers=("$@")
    local pending=("${containers[@]}")
    local deadline=$((SECONDS + HEALTH_WAIT_TIMEOUT_SECONDS))
    local terminal_failure=false
    local container status
    declare -A last_status=()

    log_info "Waiting up to ${HEALTH_WAIT_TIMEOUT_SECONDS}s for container health..."
    while [ "${#pending[@]}" -gt 0 ] && [ "${SECONDS}" -le "${deadline}" ]; do
        local remaining=()
        terminal_failure=false

        for container in "${pending[@]}"; do
            if ! status=$(docker inspect -f '{{.State.Health.Status}}' "${container}" 2>/dev/null); then
                status="missing"
            elif [ -z "${status}" ]; then
                status="<no value>"
            fi
            last_status["${container}"]="${status}"

            case "${status}" in
                healthy)
                    log_success "${container}: healthy"
                    ;;
                starting)
                    remaining+=("${container}")
                    ;;
                *)
                    terminal_failure=true
                    ;;
            esac
        done

        if [ "${terminal_failure}" = true ]; then
            for container in "${containers[@]}"; do
                log_info "${container}: last status ${last_status["${container}"]:-not checked}"
            done
            log_error "Container health check failed"
        fi

        pending=("${remaining[@]}")
        if [ "${#pending[@]}" -eq 0 ]; then
            return 0
        fi
        sleep "${HEALTH_POLL_INTERVAL_SECONDS}"
    done

    for container in "${containers[@]}"; do
        log_info "${container}: last status ${last_status["${container}"]:-not checked}"
    done
    log_error "Timed out waiting for container health"
}

deploy_services() {
    log_step "Deploy Services"

    cd "${SCRIPT_DIR}"

    local containers=(
        "blacklist-app"
        "blacklist-collector"
        "blacklist-frontend"
        "blacklist-postgres"
        "blacklist-redis"
    )
    local c
    for c in "${containers[@]}"; do
        if docker ps -aq -f "name=^${c}$" | grep -q .; then
            log_info "Removing existing container: ${c}..."
            docker rm -f "$c" 2>/dev/null || true
        fi
    done

    verify_published_port_available

    log_info "Starting services..."
    local compose_output
    if ! compose_output=$(docker compose --env-file "${ENV_FILE}" up -d --pull never 2>&1); then
        printf '%s\n' "${compose_output}"
        log_error "Failed to start Blacklist services"
    fi
    printf '%s\n' "${compose_output}"

    wait_for_health "${containers[@]}"

    log_success "Services started"
}

validate_compose_config() {
    log_step "Validate Compose Configuration"
    if ! (cd "${SCRIPT_DIR}" && docker compose --env-file "${ENV_FILE}" config --quiet); then
        log_error "Compose configuration validation failed"
    fi
    log_success "Compose configuration"
}

collect_posture_compose_files() {
    POSTURE_COMPOSE_FILES=()
    local candidate
    for candidate in "${POSTURE_COMPOSE_CANDIDATES[@]}"; do
        if [ -f "${SCRIPT_DIR}/${candidate}" ]; then
            POSTURE_COMPOSE_FILES+=(-f "${candidate}")
        fi
    done

    [ "${#POSTURE_COMPOSE_FILES[@]}" -gt 0 ]
}

render_effective_config() {
    (cd "${SCRIPT_DIR}" && docker compose --env-file "${ENV_FILE}" "${POSTURE_COMPOSE_FILES[@]}" config "$@")
}

# ADR-0002 governs the collector flag only; its Decision line is the binding baseline.
jwt_adr_decision() {
    local adr_file="${SCRIPT_DIR}/../${JWT_DEFERRAL_ADR}"
    local decision=""

    if [ -f "${adr_file}" ]; then
        decision=$(grep -m1 -E '^Decision:' "${adr_file}" | sed -E 's/^Decision:[[:space:]]*//' | tr -d '[:space:]') || true
    fi

    # The shipped offline bundle does NOT contain docs/decisions/, so this fallback is
    # the value used by every real install. It must track ADR-0002's current decision:
    # enforcement is implemented (collector verifies a bearer token on its control
    # routes), so the baseline is "enforce". Leaving it at "defer" would make the gate
    # reject every production deployment, because base.yml now ships
    # DISABLE_JWT_AUTH="false".
    printf '%s' "${decision:-enforce}"
}

verify_security_posture() {
    log_step "Verify Security Posture"

    if [ "${SKIP_POSTURE_CHECK}" = true ]; then
        log_warning "Security posture check skipped (--skip-posture-check): host networking, published ports, Redis password enforcement, and ADR drift are NOT verified."
        return 0
    fi

    if ! command -v python3 > /dev/null 2>&1; then
        log_error "python3 is required to verify the security posture; install python3 or re-run with --skip-posture-check to accept the risk explicitly."
    fi

    if [ ! -f "${ENV_FILE}" ]; then
        log_error "Environment file ${ENV_FILE} not found; run --check-secrets first so the effective configuration can be rendered."
    fi

    if ! collect_posture_compose_files; then
        log_error "No Compose file found in ${SCRIPT_DIR}; refusing to verify an unrenderable configuration."
    fi

    local rendered
    if ! rendered=$(render_effective_config --format json 2> /dev/null); then
        render_effective_config --quiet || true
        log_error "Unable to render the effective Compose configuration for the security posture check."
    fi

    local findings
    if findings=$(printf '%s' "${rendered}" | python3 -c "${POSTURE_CHECK_PY}" "$(jwt_adr_decision)"); then
        log_success "Security posture verified (internal networking, published ports, Redis password, ADR-0002 flag)"
        return 0
    fi

    local finding
    while IFS= read -r finding; do
        if [ -n "${finding}" ]; then
            echo -e "${RED}[FAIL]${NC} ${finding}"
        fi
    done <<< "${findings}"

    log_error "Security posture check failed; refusing to deploy this configuration."
}

health_checks() {
    log_step "Health Checks"

    if ! docker compose --env-file "${ENV_FILE}" ps --format "table {{.Name}}\t{{.Status}}"; then
        log_error "Failed to read service status"
    fi

    echo ""
    if curl -sk "https://localhost:${PUBLISHED_FRONTEND_PORT}/health" 2>/dev/null |
        grep -Eq '"status"[[:space:]]*:[[:space:]]*"healthy"'; then
        log_success "Frontend: healthy"
    else
        log_error "Frontend: unhealthy or not responding"
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
    echo "  --verify-only  Verify the bundle layout, image checksums, and security posture, then exit (read-only)"
    echo "  --stop-all-containers  Stop every running container on the host before deploying"
    echo "  --skip-posture-check  Deploy even if the security posture check fails (emergency use; logs a warning)"
    echo "  --require-signature  Require MANIFEST.sha256.asc verification with the host release keyring"
    echo "  --help, -h     Show this help"
    echo ""
}

main() {
    local skip_load=false
    local check_secrets=false
    local verify_only=false

    for arg in "$@"; do
        case $arg in
            --skip-load) skip_load=true ;;
            --check-secrets) check_secrets=true ;;
            --verify-only) verify_only=true ;;
            --stop-all-containers) STOP_ALL_CONTAINERS=true ;;
            --skip-posture-check) SKIP_POSTURE_CHECK=true ;;
            --require-signature) REQUIRE_SIGNATURE=true ;;
            --help|-h) show_help; exit 0 ;;
            *) log_warning "Unknown option: $arg" ;;
        esac
    done

    if [ "$check_secrets" = true ]; then
        setup_secrets
        show_initial_admin_password
        return 0
    fi

    if [ "$verify_only" = true ]; then
        preflight_verify
        verify_published_port_available
        verify_checksums
        verify_security_posture
        log_success "Bundle verification completed (no changes were made)"
        return 0
    fi

    require_root

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
    verify_security_posture
    if [ "$STOP_ALL_CONTAINERS" = true ]; then
        stop_all_running_containers
    else
        log_info "Leaving unrelated containers running (use --stop-all-containers to stop every container on this host)"
    fi

    deploy_services
    health_checks
    post_install

    log_success "Installation completed!"
    show_initial_admin_password
}

main "$@"

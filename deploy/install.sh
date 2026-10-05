#!/bin/bash
# noqa: SIZE_OK - Customers run this as one integrity-verified executable; splitting sourced files enlarges the installer attack surface.
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
VERSION_PATH="${SCRIPT_DIR}/VERSION"
if [ ! -f "${VERSION_PATH}" ] && [ -f "${SCRIPT_DIR}/../VERSION" ]; then
    VERSION_PATH="${SCRIPT_DIR}/../VERSION"
fi
VERSION="$(cat "${VERSION_PATH}" 2>/dev/null || echo 'unknown')"
ENV_FILE="${BLACKLIST_ENV_FILE:-/etc/blacklist/.env}"
TLS_DIR="${BLACKLIST_TLS_DIR:-/etc/blacklist/tls}"
FORTIGATE_TRUST_DIR="${FORTIGATE_TRUST_DIR:-/etc/blacklist/fortigate}"
FRONTEND_TLS_DIR="${BLACKLIST_FRONTEND_TLS_DIR:-/etc/blacklist/frontend-tls}"
RELEASE_KEYRING="${BLACKLIST_RELEASE_KEYRING:-/etc/blacklist/release-pubkey.gpg}"
INITIAL_ADMIN_PASSWORD_FILE="${BLACKLIST_INITIAL_ADMIN_PASSWORD_FILE:-${ENV_FILE}.initial-admin-password}"
STOP_ALL_CONTAINERS=false
SKIP_POSTURE_CHECK=false
REQUIRE_SIGNATURE=false
ADMIN_CREDENTIALS_GENERATED=false
RELEASE_KEY_FILE=""
RELEASE_KEY_FINGERPRINT=""
RELEASE_KEY_EXPECTED=""
STAGED_KEYRING_DIR=""
FRONTEND_SERVER_NAME_ARG=""
FRONTEND_TLS_CERT_ARG=""
FRONTEND_TLS_KEY_ARG=""
OPERATOR_PROBLEMS=()
POSTURE_COMPOSE_FILES=()
readonly PUBLISHED_FRONTEND_PORT=443
readonly HEALTH_WAIT_TIMEOUT_SECONDS=180
readonly HEALTH_POLL_INTERVAL_SECONDS=5
readonly TLS_ROOT_UID="${BLACKLIST_TLS_ROOT_UID:-0}"
readonly TLS_ROOT_GID="${BLACKLIST_TLS_ROOT_GID:-0}"
readonly FRONTEND_TLS_UID="${BLACKLIST_FRONTEND_UID:-1001}"
readonly FRONTEND_TLS_GID="${BLACKLIST_FRONTEND_GID:-1001}"
readonly -a TLS_SERVICE_NAMES=("app" "collector" "postgres" "redis")
readonly -a TLS_SERVICE_DNS_NAMES=("blacklist-app" "blacklist-collector" "blacklist-postgres" "blacklist-redis")
readonly -a TLS_SERVICE_UIDS=(
    "${BLACKLIST_APP_UID:-999}"
    "${BLACKLIST_COLLECTOR_UID:-10001}"
    "${BLACKLIST_POSTGRES_UID:-70}"
    "${BLACKLIST_REDIS_UID:-999}"
)
readonly -a TLS_SERVICE_GIDS=(
    "${BLACKLIST_APP_GID:-999}"
    "${BLACKLIST_COLLECTOR_GID:-0}"
    "${BLACKLIST_POSTGRES_GID:-70}"
    "${BLACKLIST_REDIS_GID:-1000}"
)
readonly LEGACY_REQUIRED_SECRET_KEYS=(
    "ADMIN_USERNAME"
    "ADMIN_PASSWORD"
    "CREDENTIAL_MASTER_KEY"
    "SECRET_KEY"
    "FLASK_SECRET_KEY"
    "JWT_SECRET_KEY"
    "COLLECTOR_AUTH_TOKEN"
    "CREDENTIAL_ENCRYPTION_KEY"
    "ENCRYPTION_SALT"
    "SETTINGS_ENCRYPTION_KEY"
    "POSTGRES_PASSWORD"
    "REDIS_PASSWORD"
)
readonly REQUIRED_SECRET_KEYS=(
    "${LEGACY_REQUIRED_SECRET_KEYS[@]}"
    "DB_OWNER_ROLE"
    "APP_DB_USER"
    "APP_DB_PASSWORD"
    "COLLECTOR_DB_USER"
    "COLLECTOR_DB_PASSWORD"
)
readonly DEPLOYMENT_VOLUME_NAMES=(
    "blacklist-pgdata"
    "blacklist-redis-data"
    "blacklist-collector-data"
    "blacklist-collector-logs"
    "blacklist-logs"
    "blacklist-uploads"
    "blacklist-app-data"
    "blacklist_blacklist-pgdata"
    "blacklist_blacklist-redis-data"
    "blacklist_blacklist-collector-data"
    "blacklist_blacklist-collector-logs"
    "blacklist_blacklist-logs"
    "blacklist_blacklist-uploads"
    "blacklist_blacklist-app-data"
)
readonly VARIABLE_REFERENCE_PREFIX="\${"
readonly POSTURE_COMPOSE_CANDIDATES=(
    "docker-compose.yml"
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

    if "no-new-privileges:true" not in (service.get("security_opt") or []):
        findings.append(name + ": security_opt must include no-new-privileges:true")
    if "ALL" not in (service.get("cap_drop") or []):
        findings.append(name + ": cap_drop must include ALL")
    if not service.get("pids_limit"):
        findings.append(name + ": pids_limit is required")
    if not service.get("mem_limit"):
        findings.append(name + ": mem_limit is required")

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

    local bundled_file relative_path
    while IFS= read -r -d '' bundled_file; do
        relative_path="${bundled_file#"${SCRIPT_DIR}/"}"
        case "${relative_path}" in
            MANIFEST.sha256|MANIFEST.sha256.asc) continue ;;
        esac
        if ! normalize_manifest_records | awk -v target="${relative_path}" '$2 == target { found=1 } END { exit(found ? 0 : 1) }'; then
            log_error "Bundle contains an unlisted file: ${relative_path}. Keep release keys, certificates, and other operator files outside the bundle directory."
        fi
    done < <(find "${SCRIPT_DIR}" -type f -print0)

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

    if [ ! -f "${RELEASE_KEYRING}" ]; then
        if [ "${REQUIRE_SIGNATURE}" = true ]; then
            log_error "Required release keyring not found: ${RELEASE_KEYRING}"
        fi
        log_warning "Manifest signature verification skipped: host keyring not found at ${RELEASE_KEYRING}"
        return 0
    fi

    if [ ! -f "${SCRIPT_DIR}/MANIFEST.sha256.asc" ]; then
        log_error "Detached signature not found while trusted keyring exists: MANIFEST.sha256.asc"
    fi

    if ! (cd "${SCRIPT_DIR}" && gpgv --keyring "${RELEASE_KEYRING}" MANIFEST.sha256.asc MANIFEST.sha256); then
        log_error "Bundle manifest signature verification failed"
    fi

    log_success "Bundle manifest signature verified"
}

normalize_fingerprint() {
    local value="${1//[[:space:]]/}"
    value="${value#0[xX]}"
    value="${value^^}"
    [[ "${value}" =~ ^([0-9A-F]{40}|[0-9A-F]{64})$ ]] || return 1
    printf '%s' "${value}"
}

cleanup_staged_keyring() {
    if [ -n "${STAGED_KEYRING_DIR}" ] && [ -d "${STAGED_KEYRING_DIR}" ]; then
        gpgconf --homedir "${STAGED_KEYRING_DIR}" --kill all > /dev/null 2>&1 || true
        rm -rf -- "${STAGED_KEYRING_DIR}"
    fi
}

primary_key_fingerprints() {
    gpg --homedir "${STAGED_KEYRING_DIR}" --batch --with-colons --show-keys "$1" 2>/dev/null |
        awk -F: '$1 == "pub" { primary = 1; next } primary && $1 == "fpr" { print toupper($10); primary = 0 }'
}

stage_release_keyring() {
    local expected fingerprints

    if ! expected=$(normalize_fingerprint "${RELEASE_KEY_FINGERPRINT}"); then
        log_error "--fingerprint must be the 40- or 64-digit hexadecimal release key fingerprint confirmed through an independent channel."
    fi
    if [ ! -f "${RELEASE_KEY_FILE}" ] || [ ! -r "${RELEASE_KEY_FILE}" ]; then
        log_error "Release public key is not a readable file: ${RELEASE_KEY_FILE}"
    fi
    command -v gpg > /dev/null 2>&1 || log_error "gpg is required to register --release-key."

    STAGED_KEYRING_DIR=$(mktemp -d) || log_error "Unable to stage the release keyring."
    trap cleanup_staged_keyring EXIT

    if ! fingerprints=$(primary_key_fingerprints "${RELEASE_KEY_FILE}") || [ -z "${fingerprints}" ]; then
        log_error "No OpenPGP public key could be read from ${RELEASE_KEY_FILE}."
    fi
    if [ "${fingerprints}" != "${expected}" ]; then
        log_error "Release key fingerprint mismatch: ${RELEASE_KEY_FILE} holds ${fingerprints//$'\n'/, }, expected ${expected}. Do not install this package."
    fi
    if ! gpg --homedir "${STAGED_KEYRING_DIR}" --batch --quiet --import "${RELEASE_KEY_FILE}" > /dev/null 2>&1 ||
        ! gpg --homedir "${STAGED_KEYRING_DIR}" --batch --export "${expected}" > "${STAGED_KEYRING_DIR}/release-pubkey.gpg" 2>/dev/null ||
        [ ! -s "${STAGED_KEYRING_DIR}/release-pubkey.gpg" ]; then
        log_error "Unable to stage the release keyring from ${RELEASE_KEY_FILE}."
    fi
    RELEASE_KEY_EXPECTED="${expected}"
    log_success "Release key fingerprint matches ${expected}"
}

keyring_trusts_fingerprint() {
    local fingerprints
    fingerprints=$(primary_key_fingerprints "$1") || return 1
    printf '%s\n' "${fingerprints}" | grep -Fxq "$2"
}

install_release_keyring() {
    local keyring_dir

    [ -n "${RELEASE_KEY_EXPECTED}" ] || return 0
    if [ -f "${RELEASE_KEYRING}" ]; then
        log_info "Host release keyring already trusts ${RELEASE_KEY_EXPECTED}"
        return 0
    fi
    keyring_dir=$(dirname "${RELEASE_KEYRING}")
    if [ ! -d "${keyring_dir}" ]; then
        install -d -m 700 "${keyring_dir}" || log_error "Unable to create ${keyring_dir}."
    fi
    install -m 644 "${STAGED_KEYRING_DIR}/release-pubkey.gpg" "${RELEASE_KEYRING}" ||
        log_error "Unable to register the release keyring at ${RELEASE_KEYRING}."
    log_success "Registered release keyring ${RELEASE_KEYRING} (${RELEASE_KEY_EXPECTED})"
}

install_docker_offline() {
    log_step "Offline Docker Installation"
    
    local prereqs_dir="${SCRIPT_DIR}/prereqs"
    if [ ! -d "$prereqs_dir" ]; then
        log_error "prereqs/ directory not found. Cannot install Docker."
    fi

    log_info "Installing Docker Engine..."
    local docker_tgz
    docker_tgz=$(find "${prereqs_dir}" -name "docker-*.tgz" | head -n 1)
    if [ -z "$docker_tgz" ]; then
        log_error "Docker binary tarball not found in prereqs/"
    fi
    local docker_relative="${docker_tgz#"${SCRIPT_DIR}/"}"
    
    verify_manifest_entry "${docker_relative}"
    if ! tar -xzf "$docker_tgz" -C /usr/bin --strip-components=1; then
        log_error "Failed to extract Docker binaries"
    fi
    
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
            if [ "${loaded_image}" != "blacklist-${name}:${VERSION}" ]; then
                log_error "Loaded image tag mismatch for ${name}: expected blacklist-${name}:${VERSION}, got ${loaded_image}"
            fi
            log_success "${name} (${loaded_image})"
        else
            log_error "Failed to load ${name}"
        fi
    done

    log_success "All images loaded"
}

prepare_collector_volumes() {
    local volume
    local image="blacklist-collector:${VERSION}"
    for volume in blacklist_blacklist-collector-data blacklist_blacklist-collector-logs; do
        if ! docker volume inspect "${volume}" > /dev/null 2>&1; then
            docker volume create --label com.docker.compose.project=blacklist \
                --label "com.docker.compose.volume=${volume#blacklist_}" "${volume}" > /dev/null ||
                log_error "Unable to create collector volume ${volume}."
        fi
        # CAP_FOWNER is required because chmod runs after chown: once /target belongs to
        # 10001, uid 0 is no longer its owner and the kernel rejects chmod without FOWNER.
        # CAP_DAC_READ_SEARCH lets chown -R descend into a volume an earlier run already left
        # as 10001:10001 mode 750; without it every second re-run or upgrade fails with EACCES.
        docker run --rm --user 0:0 --cap-drop ALL --cap-add CHOWN --cap-add FOWNER --cap-add DAC_READ_SEARCH \
            --network none --read-only \
            --security-opt no-new-privileges:true --entrypoint sh -v "${volume}:/target" "${image}" \
            -c 'chown -R 10001:10001 /target && chmod 750 /target' > /dev/null ||
            log_error "Unable to set collector volume ownership for ${volume}."
    done
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
    local fernet_key settings_encryption_key secret_key flask_secret_key jwt_secret_key collector_auth_token master_key encryption_salt pg_password app_db_password collector_db_password redis_password admin_password

    temp_file=$(mktemp "${env_file}.tmp.XXXXXX") || log_error "Unable to create private environment file."
    chmod 600 "${temp_file}" || log_error "Unable to protect generated environment file."

    fernet_key=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64)
    settings_encryption_key=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64)
    secret_key=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n')
    flask_secret_key=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n')
    jwt_secret_key=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n')
    collector_auth_token=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n')
    master_key=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n')
    encryption_salt=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n')
    pg_password=$(openssl rand -hex 16 2>/dev/null || head -c 16 /dev/urandom | xxd -p | tr -d '\n')
    app_db_password=$(openssl rand -hex 16 2>/dev/null || head -c 16 /dev/urandom | xxd -p | tr -d '\n')
    collector_db_password=$(openssl rand -hex 16 2>/dev/null || head -c 16 /dev/urandom | xxd -p | tr -d '\n')
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
FLASK_SECRET_KEY=${flask_secret_key}
JWT_SECRET_KEY=${jwt_secret_key}
COLLECTOR_AUTH_TOKEN=${collector_auth_token}
CREDENTIAL_ENCRYPTION_KEY=${fernet_key}
ENCRYPTION_SALT=${encryption_salt}
SETTINGS_ENCRYPTION_KEY=${settings_encryption_key}
POSTGRES_PASSWORD=${pg_password}
DB_OWNER_ROLE=blacklist_owner
APP_DB_USER=blacklist_app
APP_DB_PASSWORD=${app_db_password}
COLLECTOR_DB_USER=blacklist_collector
COLLECTOR_DB_PASSWORD=${collector_db_password}
REDIS_PASSWORD=${redis_password}
FRONTEND_TLS_MODE=provided
FRONTEND_TLS_SERVER_NAME=
FRONTEND_BIND_ADDRESS=0.0.0.0
WARP_ENABLED=false
WARP_PROXY_URL=
TRUSTED_PROXY_NETWORKS=172.30.0.10/32
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

sync_frontend_tls_settings() {
    local env_file="$1"
    local mode="provided"
    local bind_address
    local temp_file
    local line

    if frontend_tls_inputs_given; then
        mode="provided"
    elif read_required_secret_value "${env_file}" "FRONTEND_TLS_MODE"; then
        mode="${DOTENV_NORMALIZED_VALUE}"
    fi
    case "${mode}" in
        provided)
            bind_address="0.0.0.0"
            if read_required_secret_value "${env_file}" "FRONTEND_BIND_ADDRESS"; then
                bind_address="${DOTENV_NORMALIZED_VALUE}"
            fi
            ;;
        self-signed)
            bind_address="127.0.0.1"
            ;;
        *)
            log_error "FRONTEND_TLS_MODE must be either provided or self-signed."
            ;;
    esac

    temp_file=$(mktemp "${env_file}.tmp.XXXXXX") || log_error "Unable to stage frontend TLS settings."
    chmod 600 "${temp_file}" || log_error "Unable to protect staged frontend TLS settings."
    while IFS= read -r line || [ -n "${line}" ]; do
        case "${line}" in
            FRONTEND_TLS_MODE=*|FRONTEND_BIND_ADDRESS=*)
                ;;
            FRONTEND_TLS_SERVER_NAME=*)
                if [ -z "${FRONTEND_SERVER_NAME_ARG}" ]; then
                    printf '%s\n' "${line}" >> "${temp_file}" || log_error "Unable to stage frontend TLS settings."
                fi
                ;;
            *)
                printf '%s\n' "${line}" >> "${temp_file}" || log_error "Unable to stage frontend TLS settings."
                ;;
        esac
    done < "${env_file}"
    {
        printf 'FRONTEND_TLS_MODE=%s\n' "${mode}"
        printf 'FRONTEND_BIND_ADDRESS=%s\n' "${bind_address}"
        if [ -n "${FRONTEND_SERVER_NAME_ARG}" ]; then
            printf 'FRONTEND_TLS_SERVER_NAME=%s\n' "${FRONTEND_SERVER_NAME_ARG}"
        fi
    } >> "${temp_file}" || log_error "Unable to record frontend TLS settings."
    mv "${temp_file}" "${env_file}" || log_error "Unable to update frontend TLS settings in ${env_file}."
    chmod 600 "${env_file}" || log_error "Unable to protect updated frontend TLS settings."
}

sync_database_role_secrets() {
    local env_file="$1"
    local db_owner="blacklist_owner" app_user="blacklist_app" collector_user="blacklist_collector"
    local app_password collector_password temp_file line

    if read_required_secret_value "${env_file}" "DB_OWNER_ROLE"; then
        db_owner="${DOTENV_NORMALIZED_VALUE}"
    fi
    if read_required_secret_value "${env_file}" "APP_DB_USER"; then
        app_user="${DOTENV_NORMALIZED_VALUE}"
    fi
    if read_required_secret_value "${env_file}" "COLLECTOR_DB_USER"; then
        collector_user="${DOTENV_NORMALIZED_VALUE}"
    fi
    if read_required_secret_value "${env_file}" "APP_DB_PASSWORD"; then
        app_password="${DOTENV_NORMALIZED_VALUE}"
    else
        app_password=$(openssl rand -hex 16 2>/dev/null || head -c 16 /dev/urandom | xxd -p | tr -d '\n')
    fi
    if read_required_secret_value "${env_file}" "COLLECTOR_DB_PASSWORD"; then
        collector_password="${DOTENV_NORMALIZED_VALUE}"
    else
        collector_password=$(openssl rand -hex 16 2>/dev/null || head -c 16 /dev/urandom | xxd -p | tr -d '\n')
    fi

    temp_file=$(mktemp "${env_file}.tmp.XXXXXX") || log_error "Unable to stage database role secrets."
    chmod 600 "${temp_file}" || log_error "Unable to protect database role secrets."
    while IFS= read -r line || [ -n "${line}" ]; do
        case "${line}" in
            DB_OWNER_ROLE=*|APP_DB_USER=*|APP_DB_PASSWORD=*|COLLECTOR_DB_USER=*|COLLECTOR_DB_PASSWORD=*)
                ;;
            *)
                printf '%s\n' "${line}" >> "${temp_file}" || log_error "Unable to stage database role secrets."
                ;;
        esac
    done < "${env_file}"
    {
        printf 'DB_OWNER_ROLE=%s\n' "${db_owner}"
        printf 'APP_DB_USER=%s\n' "${app_user}"
        printf 'APP_DB_PASSWORD=%s\n' "${app_password}"
        printf 'COLLECTOR_DB_USER=%s\n' "${collector_user}"
        printf 'COLLECTOR_DB_PASSWORD=%s\n' "${collector_password}"
    } >> "${temp_file}" || log_error "Unable to record database role secrets."
    mv "${temp_file}" "${env_file}" || log_error "Unable to update database role secrets."
    chmod 600 "${env_file}" || log_error "Unable to protect updated database role secrets."
}

validate_secret_keys() {
    local env_file="$1"
    shift
    local invalid_keys=()
    local key value
    for key in "$@"; do
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
}

validate_database_role_names() {
    local env_file="$1"
    local bootstrap_owner="postgres" db_owner app_user collector_user

    if read_required_secret_value "${env_file}" "POSTGRES_USER"; then
        bootstrap_owner="${DOTENV_NORMALIZED_VALUE}"
    fi
    read_required_secret_value "${env_file}" "DB_OWNER_ROLE" || log_error "DB_OWNER_ROLE is required."
    db_owner="${DOTENV_NORMALIZED_VALUE}"
    read_required_secret_value "${env_file}" "APP_DB_USER" || log_error "APP_DB_USER is required."
    app_user="${DOTENV_NORMALIZED_VALUE}"
    read_required_secret_value "${env_file}" "COLLECTOR_DB_USER" || log_error "COLLECTOR_DB_USER is required."
    collector_user="${DOTENV_NORMALIZED_VALUE}"
    if [ "${bootstrap_owner}" = "${db_owner}" ] ||
       [ "${bootstrap_owner}" = "${app_user}" ] ||
       [ "${bootstrap_owner}" = "${collector_user}" ] ||
       [ "${db_owner}" = "${app_user}" ] ||
       [ "${db_owner}" = "${collector_user}" ] ||
       [ "${app_user}" = "${collector_user}" ]; then
        log_error "POSTGRES_USER, DB_OWNER_ROLE, APP_DB_USER, and COLLECTOR_DB_USER must be unique."
    fi
}

sync_warp_settings() {
    local env_file="$1"
    local temp_file

    temp_file=$(mktemp "${env_file}.tmp.XXXXXX") || log_error "Unable to stage WARP settings."
    chmod 600 "${temp_file}" || log_error "Unable to protect staged WARP settings."

    while IFS= read -r line || [ -n "${line}" ]; do
        case "${line}" in
            WARP_ENABLED=*|WARP_PROXY_URL=*)
                ;;
            *)
                printf '%s\n' "${line}" >> "${temp_file}" || log_error "Unable to stage WARP settings."
                ;;
        esac
    done < "${env_file}"

    {
        printf 'WARP_ENABLED=false\n'
        printf 'WARP_PROXY_URL=\n'
    } >> "${temp_file}" || log_error "Unable to record WARP settings."

    mv "${temp_file}" "${env_file}" || log_error "Unable to update WARP settings in ${env_file}."
    chmod 600 "${env_file}" || log_error "Unable to protect the updated environment file."

    log_info "Production collector proxy disabled"
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
        write_initial_admin_password_file
    fi


    validate_secret_keys "${env_file}" "${LEGACY_REQUIRED_SECRET_KEYS[@]}"
    sync_database_role_secrets "${env_file}"
    validate_database_role_names "${env_file}"
    validate_secret_keys "${env_file}" "${REQUIRED_SECRET_KEYS[@]}"

    log_success "Secret validation passed (${env_file})"
    sync_deployment_version "${env_file}"
    log_info "Deployment version pinned to ${VERSION}"
    sync_frontend_tls_settings "${env_file}"
    sync_warp_settings "${env_file}"
    log_warning "Back up ${env_file} securely; upgrades require the same encryption keys"
}

tls_material_complete() {
    local path
    local required_paths=("ca/ca.crt" "ca/ca.key")
    local service_name
    for service_name in "${TLS_SERVICE_NAMES[@]}"; do
        required_paths+=("${service_name}/tls.crt" "${service_name}/tls.key")
    done

    for path in "${required_paths[@]}"; do
        [ -f "${TLS_DIR}/${path}" ] || return 1
    done
}

protect_tls_material() {
    chown -R "${TLS_ROOT_UID}:${TLS_ROOT_GID}" "${TLS_DIR}" || log_error "Unable to set TLS root ownership."
    chmod 700 "${TLS_DIR}" "${TLS_DIR}/ca" || log_error "Unable to protect TLS directories."
    chmod 600 "${TLS_DIR}/ca/ca.key" || log_error "Unable to protect the local CA private key."
    chmod 644 "${TLS_DIR}/ca/ca.crt" || log_error "Unable to make the local CA certificate readable."

    local index service_dir
    for index in "${!TLS_SERVICE_NAMES[@]}"; do
        service_dir="${TLS_DIR}/${TLS_SERVICE_NAMES[$index]}"
        chown -R "${TLS_SERVICE_UIDS[$index]}:${TLS_SERVICE_GIDS[$index]}" "${service_dir}" ||
            log_error "Unable to set TLS ownership for ${TLS_SERVICE_NAMES[$index]}."
        chmod 700 "${service_dir}" || log_error "Unable to protect ${TLS_SERVICE_NAMES[$index]} TLS directory."
        chmod 600 "${service_dir}/tls.key" || log_error "Unable to protect ${TLS_SERVICE_NAMES[$index]} private key."
        chmod 644 "${service_dir}/tls.crt" || log_error "Unable to make ${TLS_SERVICE_NAMES[$index]} certificate readable."
    done
}

generate_service_certificate() {
    local output_dir="$1"
    local service_name="$2"
    local dns_name="$3"
    local extension_file="${output_dir}/${service_name}/extensions.cnf"
    local request_file="${output_dir}/${service_name}/tls.csr"

    cat > "${extension_file}" << EOF
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:${dns_name}
EOF

    openssl req -new -nodes -newkey rsa:2048 \
        -keyout "${output_dir}/${service_name}/tls.key" \
        -out "${request_file}" \
        -subj "/CN=${dns_name}/O=Blacklist/C=KR" > /dev/null 2>&1 ||
        log_error "Unable to generate the ${service_name} private key."
    openssl x509 -req -sha256 -days 825 \
        -in "${request_file}" \
        -CA "${output_dir}/ca/ca.crt" \
        -CAkey "${output_dir}/ca/ca.key" \
        -CAcreateserial \
        -extfile "${extension_file}" \
        -out "${output_dir}/${service_name}/tls.crt" > /dev/null 2>&1 ||
        log_error "Unable to sign the ${service_name} certificate."
    rm -f "${request_file}" "${extension_file}"
}

setup_internal_tls() {
    log_step "Setup Internal Transport Certificates"
    umask 077

    install -d -m 700 "$(dirname "${TLS_DIR}")" || log_error "Unable to create the TLS parent directory."
    if [ -d "${TLS_DIR}" ]; then
        if tls_material_complete; then
            protect_tls_material
            log_success "Internal TLS material validated (${TLS_DIR})"
            return 0
        fi
        if [ -n "$(find "${TLS_DIR}" -mindepth 1 -print -quit 2>/dev/null)" ]; then
            log_error "Incomplete TLS material found in ${TLS_DIR}; restore the complete target-local PKI backup."
        fi
        rmdir "${TLS_DIR}" || log_error "Unable to replace the empty TLS directory."
    fi

    local staging_dir
    staging_dir=$(mktemp -d "${TLS_DIR}.tmp.XXXXXX") || log_error "Unable to stage internal TLS material."
    install -d -m 700 "${staging_dir}/ca" || log_error "Unable to stage the local CA directory."

    openssl req -x509 -nodes -newkey rsa:4096 -sha256 -days 3650 \
        -keyout "${staging_dir}/ca/ca.key" \
        -out "${staging_dir}/ca/ca.crt" \
        -subj "/CN=Blacklist Internal CA/O=Blacklist/C=KR" > /dev/null 2>&1 ||
        log_error "Unable to generate the local certificate authority."

    local index service_name
    for index in "${!TLS_SERVICE_NAMES[@]}"; do
        service_name="${TLS_SERVICE_NAMES[$index]}"
        install -d -m 700 "${staging_dir}/${service_name}" || log_error "Unable to stage ${service_name} TLS material."
        generate_service_certificate "${staging_dir}" "${service_name}" "${TLS_SERVICE_DNS_NAMES[$index]}"
    done
    rm -f "${staging_dir}/ca/ca.srl"

    mv "${staging_dir}" "${TLS_DIR}" || log_error "Unable to install target-local TLS material."
    protect_tls_material
    log_success "Generated target-local CA and service certificates (${TLS_DIR})"
}

write_initial_admin_password_file() {
    if [ "${ADMIN_CREDENTIALS_GENERATED}" != true ]; then
        return 0
    fi

    if ! read_required_secret_value "${ENV_FILE}" "ADMIN_PASSWORD"; then
        log_error "Unable to read the generated administrator password from ${ENV_FILE}."
    fi
    umask 077
    printf '%s\n' "${DOTENV_NORMALIZED_VALUE}" > "${INITIAL_ADMIN_PASSWORD_FILE}" ||
        log_error "Unable to write initial administrator password file."
    chmod 600 "${INITIAL_ADMIN_PASSWORD_FILE}" || log_error "Unable to protect initial administrator password file."
    log_success "Initial administrator password saved to ${INITIAL_ADMIN_PASSWORD_FILE} (mode 0600)"
}

print_initial_admin_password_notice() {
    if [ ! -f "${INITIAL_ADMIN_PASSWORD_FILE}" ]; then
        return 0
    fi
    log_warning "Initial administrator password is in ${INITIAL_ADMIN_PASSWORD_FILE}; import it into a password manager and delete the file."
    log_warning "The generated ADMIN_PASSWORD only bootstraps the administrator row; it stays readable in ${ENV_FILE} and through 'docker inspect'."
    log_warning "After the first login, rotate the password in the dashboard and overwrite ADMIN_PASSWORD in ${ENV_FILE} with an unused random value."
}

setup_trust_directories() {
    install -d -m 755 "${FORTIGATE_TRUST_DIR}" || log_error "Unable to create FortiGate trust directory."
    install -d -m 700 -o "${FRONTEND_TLS_UID}" -g "${FRONTEND_TLS_GID}" "${FRONTEND_TLS_DIR}" ||
        log_error "Unable to create persistent frontend TLS directory."
}

frontend_certificate_problem() {
    local certificate="$1"
    local private_key="$2"
    local server_name="$3"
    local cert_public_key key_public_key coverage

    if [ ! -r "${certificate}" ] || [ ! -r "${private_key}" ]; then
        printf 'Frontend TLS certificate and private key must be readable: %s, %s' "${certificate}" "${private_key}"
        return 1
    fi
    if ! openssl x509 -in "${certificate}" -noout -checkend 0 > /dev/null 2>&1; then
        printf 'Frontend TLS certificate is invalid or expired: %s' "${certificate}"
        return 1
    fi
    if ! cert_public_key=$(openssl x509 -in "${certificate}" -pubkey -noout 2>/dev/null | openssl pkey -pubin -outform pem 2>/dev/null | sha256sum | cut -d' ' -f1) ||
        ! key_public_key=$(openssl pkey -in "${private_key}" -pubout -outform pem 2>/dev/null | sha256sum | cut -d' ' -f1); then
        printf 'Unable to read the frontend TLS certificate or private key: %s, %s' "${certificate}" "${private_key}"
        return 1
    fi
    if [ "${cert_public_key}" != "${key_public_key}" ]; then
        printf 'Frontend TLS certificate and private key do not match: %s, %s' "${certificate}" "${private_key}"
        return 1
    fi
    if [[ "${server_name}" =~ ^[0-9]+(\.[0-9]+){3}$ || "${server_name}" == *:* ]]; then
        coverage=$(openssl x509 -in "${certificate}" -noout -checkip "${server_name}" 2>/dev/null) || coverage=""
    else
        coverage=$(openssl x509 -in "${certificate}" -noout -checkhost "${server_name}" 2>/dev/null) || coverage=""
    fi
    # openssl exits 0 even when the name does not match, so only its verdict text is authoritative.
    if [[ "${coverage}" != *"does match certificate"* ]]; then
        printf 'Frontend TLS certificate does not cover %s: %s' "${server_name}" "${certificate}"
        return 1
    fi
}

frontend_tls_inputs_given() {
    [ -n "${FRONTEND_SERVER_NAME_ARG}${FRONTEND_TLS_CERT_ARG}${FRONTEND_TLS_KEY_ARG}" ]
}

collect_frontend_tls_problems() {
    local mode="provided"
    local server_name="${FRONTEND_SERVER_NAME_ARG}"
    local certificate="${FRONTEND_TLS_CERT_ARG:-${FRONTEND_TLS_DIR}/server.crt}"
    local private_key="${FRONTEND_TLS_KEY_ARG:-${FRONTEND_TLS_DIR}/server.key}"
    local problem

    if ! frontend_tls_inputs_given && [ -r "${ENV_FILE}" ] &&
        read_required_secret_value "${ENV_FILE}" "FRONTEND_TLS_MODE"; then
        mode="${DOTENV_NORMALIZED_VALUE}"
    fi
    case "${mode}" in
        self-signed)
            return 0
            ;;
        provided)
            ;;
        *)
            OPERATOR_PROBLEMS+=("FRONTEND_TLS_MODE in ${ENV_FILE} must be either provided or self-signed.")
            return 0
            ;;
    esac

    if [ -z "${server_name}" ] && [ -r "${ENV_FILE}" ] &&
        read_required_secret_value "${ENV_FILE}" "FRONTEND_TLS_SERVER_NAME"; then
        server_name="${DOTENV_NORMALIZED_VALUE}"
    fi
    if [ -z "${server_name}" ]; then
        OPERATOR_PROBLEMS+=("Frontend server name is missing: pass --server-name NAME with the FQDN or IP address clients use.")
    elif ! [[ "${server_name}" =~ ^[A-Za-z0-9.:-]{1,253}$ ]]; then
        OPERATOR_PROBLEMS+=("Frontend server name is not a valid host name or IP address: ${server_name}")
        server_name=""
    fi

    if [ ! -e "${certificate}" ] || [ ! -e "${private_key}" ]; then
        OPERATOR_PROBLEMS+=("Frontend TLS certificate is missing: pass --tls-cert FILE --tls-key FILE, or place server.crt and server.key in ${FRONTEND_TLS_DIR}.")
    elif [ -n "${server_name}" ] && ! problem=$(frontend_certificate_problem "${certificate}" "${private_key}" "${server_name}"); then
        OPERATOR_PROBLEMS+=("${problem}")
    fi
}

operator_file_inside_bundle() {
    local path bundle
    path=$(readlink -f -- "$1") || return 1
    bundle=$(readlink -f -- "${SCRIPT_DIR}") || return 1
    [[ "${path}" == "${bundle}"/* ]]
}

preflight_operator_inputs() {
    local purpose="$1"
    local operator_file problem

    log_step "Verify Operator Inputs"
    OPERATOR_PROBLEMS=()

    for operator_file in "${RELEASE_KEY_FILE}" "${FRONTEND_TLS_CERT_ARG}" "${FRONTEND_TLS_KEY_ARG}"; do
        if [ -n "${operator_file}" ] && operator_file_inside_bundle "${operator_file}"; then
            OPERATOR_PROBLEMS+=("Move ${operator_file} outside the bundle directory; MANIFEST.sha256 rejects files it does not list.")
        fi
    done

    if [ -n "${RELEASE_KEY_FILE}" ]; then
        stage_release_keyring
        if [ "${purpose}" = "install" ] && [ -f "${RELEASE_KEYRING}" ] &&
            ! keyring_trusts_fingerprint "${RELEASE_KEYRING}" "${RELEASE_KEY_EXPECTED}"; then
            OPERATOR_PROBLEMS+=("Host keyring ${RELEASE_KEYRING} does not trust ${RELEASE_KEY_EXPECTED}; remove it deliberately before rotating the release key.")
        fi
    elif [ "${purpose}" = "install" ] && [ ! -f "${RELEASE_KEYRING}" ]; then
        OPERATOR_PROBLEMS+=("Release keyring is missing: ${RELEASE_KEYRING}. Pass --release-key FILE --fingerprint FPR, using the fingerprint confirmed through an independent channel.")
    fi

    if [ "${purpose}" = "install" ] || frontend_tls_inputs_given; then
        collect_frontend_tls_problems
    fi

    if [ "${#OPERATOR_PROBLEMS[@]}" -gt 0 ]; then
        for problem in "${OPERATOR_PROBLEMS[@]}"; do
            echo -e "${RED}[FAIL]${NC} ${problem}"
        done
        log_error "Installation inputs are incomplete; nothing was changed. Run 'bash install.sh --help' for the one-command form."
    fi
    log_success "Operator inputs verified"
}

install_frontend_tls_file() {
    local source="$1"
    local destination="$2"
    local mode="$3"

    if [ "$(readlink -f -- "${source}")" = "$(readlink -f -- "${destination}")" ]; then
        return 0
    fi
    install -m "${mode}" -o "${FRONTEND_TLS_UID}" -g "${FRONTEND_TLS_GID}" "${source}" "${destination}" ||
        log_error "Unable to install ${destination}."
}

install_frontend_tls_material() {
    [ -n "${FRONTEND_TLS_CERT_ARG}" ] || return 0
    install_frontend_tls_file "${FRONTEND_TLS_CERT_ARG}" "${FRONTEND_TLS_DIR}/server.crt" 644
    install_frontend_tls_file "${FRONTEND_TLS_KEY_ARG}" "${FRONTEND_TLS_DIR}/server.key" 600
    log_success "Frontend TLS certificate and key installed (${FRONTEND_TLS_DIR})"
}

validate_frontend_tls() {
    local mode server_name problem

    read_required_secret_value "${ENV_FILE}" "FRONTEND_TLS_MODE" || log_error "FRONTEND_TLS_MODE is required."
    mode="${DOTENV_NORMALIZED_VALUE}"
    if [ "${mode}" = "self-signed" ]; then
        return 0
    fi
    [ "${mode}" = "provided" ] || log_error "FRONTEND_TLS_MODE must be either provided or self-signed."
    read_required_secret_value "${ENV_FILE}" "FRONTEND_TLS_SERVER_NAME" ||
        log_error "FRONTEND_TLS_SERVER_NAME is required when FRONTEND_TLS_MODE=provided."
    server_name="${DOTENV_NORMALIZED_VALUE}"
    if ! problem=$(frontend_certificate_problem "${FRONTEND_TLS_DIR}/server.crt" "${FRONTEND_TLS_DIR}/server.key" "${server_name}"); then
        log_error "${problem}"
    fi
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

    log_info "Starting PostgreSQL and configuring runtime roles..."
    local compose_output
    if ! compose_output=$(docker compose --env-file "${ENV_FILE}" -f "${SCRIPT_DIR}/docker-compose.yml" up -d --pull never blacklist-postgres 2>&1); then
        printf '%s\n' "${compose_output}"
        log_error "Failed to start PostgreSQL"
    fi
    printf '%s\n' "${compose_output}"
    wait_for_health "blacklist-postgres"
    local roles_output
    if ! roles_output=$(docker exec blacklist-postgres /usr/local/bin/configure-runtime-roles.sh 2>&1); then
        printf '%s\n' "${roles_output}"
        log_error "Failed to configure PostgreSQL runtime roles"
    fi
    log_success "PostgreSQL runtime roles configured"

    log_info "Starting application services..."
    if ! compose_output=$(docker compose --env-file "${ENV_FILE}" -f "${SCRIPT_DIR}/docker-compose.yml" up -d --pull never 2>&1); then
        printf '%s\n' "${compose_output}"
        log_error "Failed to start Blacklist services"
    fi
    printf '%s\n' "${compose_output}"

    wait_for_health "${containers[@]}"

    log_success "Services started"
}

validate_compose_config() {
    log_step "Validate Compose Configuration"
    if ! docker compose --env-file "${ENV_FILE}" -f "${SCRIPT_DIR}/docker-compose.yml" config --quiet; then
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
    docker compose --env-file "${ENV_FILE}" "${POSTURE_COMPOSE_FILES[@]}" config "$@"
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

    if ! docker compose --env-file "${ENV_FILE}" -f "${SCRIPT_DIR}/docker-compose.yml" ps --format "table {{.Name}}\t{{.Status}}"; then
        log_error "Failed to read service status"
    fi

    local probe_host="localhost"
    if read_required_secret_value "${ENV_FILE}" "FRONTEND_BIND_ADDRESS"; then
        case "${DOTENV_NORMALIZED_VALUE}" in
            0.0.0.0|::) ;;
            *:*) probe_host="[${DOTENV_NORMALIZED_VALUE}]" ;;
            *) probe_host="${DOTENV_NORMALIZED_VALUE}" ;;
        esac
    fi

    echo ""
    if curl -sk "https://${probe_host}:${PUBLISHED_FRONTEND_PORT}/health" 2>/dev/null |
        grep -Eq '"status"[[:space:]]*:[[:space:]]*"healthy"'; then
        log_success "Frontend: healthy"
    else
        log_error "Frontend: unhealthy or not responding"
    fi
}

post_install() {
    log_step "Installation Complete"

    local access_url="https://localhost"
    local compose_command
    if read_required_secret_value "${ENV_FILE}" "FRONTEND_TLS_MODE" && [ "${DOTENV_NORMALIZED_VALUE}" = "provided" ] &&
        read_required_secret_value "${ENV_FILE}" "FRONTEND_TLS_SERVER_NAME"; then
        access_url="https://${DOTENV_NORMALIZED_VALUE}"
        if [[ "${DOTENV_NORMALIZED_VALUE}" == *:* ]]; then
            access_url="https://[${DOTENV_NORMALIZED_VALUE}]"
        fi
    fi
    printf -v compose_command 'docker compose --env-file %q -f %q' "${ENV_FILE}" "${SCRIPT_DIR}/docker-compose.yml"

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  Blacklist Platform ${VERSION} Deployed Successfully      ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Access Points:"
    echo "  Frontend:  ${access_url}"
    echo ""
    echo "Management (as root):"
    echo "  Status:    ${compose_command} ps"
    echo "  Logs:      ${compose_command} logs -f"
    echo "  Stop:      ${compose_command} down"
    echo "  Restart:   ${compose_command} restart"
    echo ""
}

show_help() {
    echo "Blacklist Offline Installer"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "One-command installation (keep keys and certificates outside the bundle directory):"
    echo "  sudo bash $0 --release-key KEY.asc --fingerprint FINGERPRINT \\"
    echo "    --server-name blacklist.example.com --tls-cert server.crt --tls-key server.key"
    echo ""
    echo "Options:"
    echo "  --skip-load    Skip image loading (images already loaded)"
    echo "  --check-secrets Generate or validate .env, then exit"
    echo "  --generate-tls-only  Generate or validate internal TLS material, then exit"
    echo "  --verify-only  Verify the bundle layout, image checksums, and security posture, then exit (read-only)"
    echo "  --stop-all-containers  Stop every running container on the host before deploying"
    echo "  --skip-posture-check  Deploy even if the security posture check fails (emergency use; logs a warning)"
    echo "  --require-signature  Require signature during --verify-only (installation always requires it)"
    echo "  --release-key FILE   Register this release public key in ${RELEASE_KEYRING} (requires --fingerprint)"
    echo "  --fingerprint FPR    Release key fingerprint confirmed through an independent channel"
    echo "  --server-name NAME   FQDN or IP address clients use; the certificate must cover it"
    echo "  --tls-cert FILE      Frontend TLS certificate in PEM (chain allowed); requires --tls-key"
    echo "  --tls-key FILE       Frontend TLS private key in PEM"
    echo "  --help, -h     Show this help"
    echo ""
}

set_operator_input() {
    local option="$1"
    local value="$2"

    if [ -z "${value}" ] || [[ "${value}" == --* ]]; then
        log_error "Option ${option} requires a value."
    fi
    case "${option}" in
        --release-key) RELEASE_KEY_FILE="${value}" ;;
        --fingerprint) RELEASE_KEY_FINGERPRINT="${value}" ;;
        --server-name) FRONTEND_SERVER_NAME_ARG="${value}" ;;
        --tls-cert) FRONTEND_TLS_CERT_ARG="${value}" ;;
        --tls-key) FRONTEND_TLS_KEY_ARG="${value}" ;;
    esac
}

validate_operator_options() {
    local maintenance_only="$1"

    if [ -n "${RELEASE_KEY_FILE}" ] && [ -z "${RELEASE_KEY_FINGERPRINT}" ]; then
        log_error "--release-key requires --fingerprint confirmed through an independent channel."
    fi
    if [ -z "${RELEASE_KEY_FILE}" ] && [ -n "${RELEASE_KEY_FINGERPRINT}" ]; then
        log_error "--fingerprint requires --release-key."
    fi
    if [ -n "${FRONTEND_TLS_CERT_ARG}" ] && [ -z "${FRONTEND_TLS_KEY_ARG}" ]; then
        log_error "--tls-cert requires --tls-key."
    fi
    if [ -z "${FRONTEND_TLS_CERT_ARG}" ] && [ -n "${FRONTEND_TLS_KEY_ARG}" ]; then
        log_error "--tls-key requires --tls-cert."
    fi
    if [ "${maintenance_only}" = true ] && { [ -n "${RELEASE_KEY_FILE}" ] || frontend_tls_inputs_given; }; then
        log_error "--release-key, --fingerprint, --server-name, --tls-cert, and --tls-key apply only to installation and --verify-only."
    fi
}

main() {
    local skip_load=false
    local check_secrets=false
    local generate_tls_only=false
    local verify_only=false
    local maintenance_only=false

    while [ "$#" -gt 0 ]; do
        case "$1" in
            --skip-load) skip_load=true ;;
            --check-secrets) check_secrets=true ;;
            --generate-tls-only) generate_tls_only=true ;;
            --verify-only) verify_only=true ;;
            --stop-all-containers) STOP_ALL_CONTAINERS=true ;;
            --skip-posture-check) SKIP_POSTURE_CHECK=true ;;
            --require-signature) REQUIRE_SIGNATURE=true ;;
            --release-key|--fingerprint|--server-name|--tls-cert|--tls-key)
                set_operator_input "$1" "${2-}"
                shift
                ;;
            --release-key=*|--fingerprint=*|--server-name=*|--tls-cert=*|--tls-key=*)
                set_operator_input "${1%%=*}" "${1#*=}"
                ;;
            --help|-h) show_help; exit 0 ;;
            *) log_error "Unknown option: $1" ;;
        esac
        shift
    done

    if [ "$check_secrets" = true ] || [ "$generate_tls_only" = true ]; then
        maintenance_only=true
    fi
    validate_operator_options "${maintenance_only}"

    if [ "$generate_tls_only" = true ]; then
        setup_internal_tls
        return 0
    fi

    if [ "$check_secrets" = true ]; then
        setup_secrets
        print_initial_admin_password_notice
        return 0
    fi

    if [ "$verify_only" = true ]; then
        if [ -n "${RELEASE_KEY_FILE}" ] || frontend_tls_inputs_given; then
            preflight_operator_inputs verify
        fi
        if [ -n "${RELEASE_KEY_EXPECTED}" ]; then
            RELEASE_KEYRING="${STAGED_KEYRING_DIR}/release-pubkey.gpg"
        fi
        preflight_verify
        verify_checksums
        if [ -f "${ENV_FILE}" ]; then
            verify_security_posture
        else
            log_warning "Target environment is absent; runtime posture verification skipped without modifying the host"
        fi
        log_success "Bundle verification completed (no changes were made)"
        return 0
    fi

    REQUIRE_SIGNATURE=true
    require_root

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  Blacklist Offline Installer ${VERSION}                   ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""

    preflight_operator_inputs install
    install_release_keyring
    preflight_checks
    verify_checksums

    if [ "$skip_load" = false ]; then
        load_images
    else
        log_info "Skipping image load (--skip-load)"
    fi

    setup_secrets
    setup_internal_tls
    setup_trust_directories
    install_frontend_tls_material
    validate_frontend_tls
    prepare_collector_volumes
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
    print_initial_admin_password_notice
}

main "$@"

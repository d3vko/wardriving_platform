#!/usr/bin/env bash
# =============================================================================
# cleanup_ctfd.sh — Limpieza de recursos CTFd del stack Wardrive
#
# Uso:
#   ./cleanup_ctfd.sh [OPCIONES]
#
# Opciones:
#   --runtime docker|podman   Forzar runtime (por defecto: auto-detect)
#   --drop-db                 Eliminar tambien la base de datos 'ctfd' de PostgreSQL
#   --dry-run                 Mostrar que se haria sin ejecutar nada
#   -h, --help                Mostrar esta ayuda
#
# Compatibilidad:
#   - docker + docker compose (plugin v2)
#   - podman + podman-compose
# =============================================================================

set -euo pipefail

# ── Colores ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# ── Helpers ────────────────────────────────────────────────────────────────────
info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
step()    { echo -e "\n${BOLD}── $* ${RESET}"; }

dry_run_prefix() {
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}[DRY-RUN]${RESET} "
    fi
}

run() {
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}[DRY-RUN]${RESET} $*"
    else
        eval "$@"
    fi
}

# ── Defaults ───────────────────────────────────────────────────────────────────
RUNTIME=""
COMPOSE_CMD=""
DROP_DB=false
DRY_RUN=false

# ── Parsear argumentos ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --runtime)
            RUNTIME="${2:-}"
            shift 2
            ;;
        --drop-db)
            DROP_DB=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            sed -n '/^# Uso:/,/^# =====/p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            error "Argumento desconocido: $1"
            exit 1
            ;;
    esac
done

# ── Auto-deteccion de runtime ──────────────────────────────────────────────────
detect_runtime() {
    if [[ -n "$RUNTIME" ]]; then
        if ! command -v "$RUNTIME" &>/dev/null; then
            error "Runtime '$RUNTIME' no encontrado en PATH."
            exit 1
        fi
        CT="$RUNTIME"
    elif command -v podman &>/dev/null; then
        CT="podman"
        info "Runtime auto-detectado: podman"
    elif command -v docker &>/dev/null; then
        CT="docker"
        info "Runtime auto-detectado: docker"
    else
        error "No se encontro docker ni podman en el sistema."
        exit 1
    fi

    # Compose
    if [[ "$CT" == "podman" ]]; then
        if command -v podman-compose &>/dev/null; then
            COMPOSE_CMD="podman-compose"
        else
            warn "podman-compose no encontrado; las operaciones de compose se omitiran."
            COMPOSE_CMD=""
        fi
    else
        # docker compose (plugin v2) o docker-compose (standalone)
        if docker compose version &>/dev/null 2>&1; then
            COMPOSE_CMD="docker compose"
        elif command -v docker-compose &>/dev/null; then
            COMPOSE_CMD="docker-compose"
        else
            warn "docker compose/docker-compose no encontrado."
            COMPOSE_CMD=""
        fi
    fi

    info "Container CLI : ${BOLD}$CT${RESET}"
    [[ -n "$COMPOSE_CMD" ]] && info "Compose CMD   : ${BOLD}$COMPOSE_CMD${RESET}"
}

# ── Verificar que estamos en el directorio correcto ────────────────────────────
check_workdir() {
    if [[ ! -f "docker-compose.yml" ]]; then
        error "No se encontro docker-compose.yml. Ejecuta el script desde la raiz del proyecto."
        exit 1
    fi
}

# ── Nombre del proyecto Compose (prefijo de volumenes) ────────────────────────
compose_project_name() {
    # Docker/Podman compose usa el nombre del directorio como prefijo por defecto
    basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]_-'
}

# ── Paso 1: detener y eliminar contenedor CTFd ────────────────────────────────
stop_ctfd_container() {
    step "Paso 1/4: Detener y eliminar contenedor ctfd_platform"

    local container
    container=$("$CT" ps -aq --filter "name=ctfd_platform" 2>/dev/null || true)

    if [[ -z "$container" ]]; then
        warn "Contenedor ctfd_platform no encontrado (ya eliminado o nunca iniciado)."
        return
    fi

    info "Contenedor encontrado: $container"
    run "$CT stop '$container' 2>/dev/null || true"
    run "$CT rm -f '$container' 2>/dev/null || true"
    success "Contenedor ctfd_platform eliminado."
}

# ── Paso 2: eliminar volumenes CTFd ───────────────────────────────────────────
remove_ctfd_volumes() {
    step "Paso 2/4: Eliminar volumenes de CTFd"

    local project
    project=$(compose_project_name)

    local volumes=("${project}_ctfd_logs" "${project}_ctfd_uploads")

    for vol in "${volumes[@]}"; do
        if "$CT" volume inspect "$vol" &>/dev/null 2>&1; then
            info "Eliminando volumen: $vol"
            run "$CT volume rm '$vol'"
            success "Volumen $vol eliminado."
        else
            warn "Volumen $vol no existe (ya eliminado o nunca creado)."
        fi
    done
}

# ── Paso 3: eliminar imagen CTFd ──────────────────────────────────────────────
remove_ctfd_image() {
    step "Paso 3/4: Eliminar imagen CTFd"

    # Buscar imagenes relacionadas con ctfd
    local images
    images=$("$CT" images --format "{{.Repository}}:{{.Tag}}" 2>/dev/null \
        | grep -i "ctfd" || true)

    if [[ -z "$images" ]]; then
        warn "No se encontraron imagenes de CTFd."
        return
    fi

    while IFS= read -r img; do
        info "Eliminando imagen: $img"
        run "$CT rmi '$img' 2>/dev/null || true"
        success "Imagen $img eliminada."
    done <<< "$images"
}

# ── Paso 4 (opcional): eliminar base de datos CTFd ───────────────────────────
drop_ctfd_database() {
    step "Paso 4/4: Eliminar base de datos 'ctfd' de PostgreSQL"

    # Intentar ejecutar mediante el contenedor wardrive_db
    local db_container
    db_container=$("$CT" ps -q --filter "name=wardrive_db" 2>/dev/null || true)

    if [[ -z "$db_container" ]]; then
        warn "Contenedor wardrive_db no esta corriendo. Levantalo primero con:"
        warn "  ${COMPOSE_CMD:-docker compose} up -d wardrive_db"
        return
    fi

    info "Eliminando base de datos 'ctfd'..."
    run "$CT exec '$db_container' psql -U postgres -c 'DROP DATABASE IF EXISTS ctfd;'"
    success "Base de datos 'ctfd' eliminada."
}

# ── Resumen ────────────────────────────────────────────────────────────────────
print_summary() {
    echo ""
    echo -e "${BOLD}═══════════════════════════════════════════════════${RESET}"
    echo -e "${GREEN}${BOLD}  Limpieza CTFd completada${RESET}"
    echo -e "${BOLD}═══════════════════════════════════════════════════${RESET}"
    echo -e "  Runtime usado  : ${CYAN}$CT${RESET}"
    [[ "$DROP_DB" == "true" ]] && echo -e "  DB ctfd        : ${RED}eliminada${RESET}"
    [[ "$DRY_RUN" == "true" ]]  && echo -e "  Modo           : ${YELLOW}DRY-RUN (sin cambios reales)${RESET}"
    echo ""
    echo -e "  Para levantar el nuevo frontend:"
    echo -e "  ${CYAN}${COMPOSE_CMD:-docker compose} up -d --build wardrive-frontend${RESET}"
    echo ""
}

# ── Main ───────────────────────────────────────────────────────────────────────
main() {
    echo ""
    echo -e "${BOLD}╔═══════════════════════════════════════════════════╗${RESET}"
    echo -e "${BOLD}║        Wardrive — Cleanup CTFd Resources          ║${RESET}"
    echo -e "${BOLD}╚═══════════════════════════════════════════════════╝${RESET}"
    echo ""

    [[ "$DRY_RUN" == "true" ]] && warn "Modo DRY-RUN activo — no se realizaran cambios reales."

    check_workdir
    detect_runtime

    stop_ctfd_container
    remove_ctfd_volumes
    remove_ctfd_image

    if [[ "$DROP_DB" == "true" ]]; then
        drop_ctfd_database
    else
        step "Paso 4/4: Base de datos"
        info "Omitido. Usa --drop-db para eliminar la DB 'ctfd' de PostgreSQL."
    fi

    print_summary
}

main "$@"

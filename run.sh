#!/bin/bash

# BrowserBot Docker-First Launcher
# This script ensures BrowserBot always runs in a secure Docker container

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="browserbot"
CONTAINER_NAME="${PROJECT_NAME}-interactive"
IMAGE_NAME="${PROJECT_NAME}:latest"
VNC_PORT=${VNC_PORT:-5900}
METRICS_PORT=${METRICS_PORT:-8000}
API_PORT=${API_PORT:-8080}

# Print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        print_info "Please install Docker from: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        print_info "Please start Docker and try again"
        exit 1
    fi
}

# Check if Docker Compose is available
check_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        print_error "Docker Compose is not available"
        print_info "Please install Docker Compose or upgrade Docker to include 'docker compose'"
        exit 1
    fi
}

# Create .env file if it doesn't exist
setup_env() {
    if [ ! -f "${SCRIPT_DIR}/.env" ]; then
        print_warning ".env file not found. Creating from template..."
        if [ -f "${SCRIPT_DIR}/.env.example" ]; then
            cp "${SCRIPT_DIR}/.env.example" "${SCRIPT_DIR}/.env"
            print_warning "Please edit .env file and add your API keys before running BrowserBot"
            print_info "Required: OPENROUTER_API_KEY=your-key-here"
            return 1
        else
            print_error ".env.example file not found"
            exit 1
        fi
    fi
    
    # Check if required API key is set
    if ! grep -q "^OPENROUTER_API_KEY=.*[^=]" "${SCRIPT_DIR}/.env"; then
        print_error "OPENROUTER_API_KEY is not set in .env file"
        print_info "Please edit .env file and add: OPENROUTER_API_KEY=your-key-here"
        return 1
    fi
    
    return 0
}

# Build Docker image if needed
build_image() {
    if [ "$1" = "force" ] || ! docker image inspect "${IMAGE_NAME}" &> /dev/null; then
        print_info "Building BrowserBot Docker image..."
        docker build -t "${IMAGE_NAME}" "${SCRIPT_DIR}"
        print_success "Docker image built successfully"
    else
        print_info "Using existing Docker image: ${IMAGE_NAME}"
    fi
}

# Stop and remove existing container
cleanup_container() {
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_info "Stopping and removing existing container..."
        docker stop "${CONTAINER_NAME}" &> /dev/null || true
        docker rm "${CONTAINER_NAME}" &> /dev/null || true
    fi
}

# Check if ports are available
check_ports() {
    local ports=("$VNC_PORT" "$METRICS_PORT" "$API_PORT")
    for port in "${ports[@]}"; do
        if netstat -tuln 2>/dev/null | grep -q ":${port} " || \
           lsof -i ":${port}" &>/dev/null || \
           ss -tuln 2>/dev/null | grep -q ":${port} "; then
            print_warning "Port ${port} is already in use"
            print_info "You can access services on alternative ports or stop the conflicting service"
        fi
    done
}

# Start interactive container
start_interactive() {
    print_info "Starting BrowserBot in interactive mode..."
    
    # Create necessary directories
    mkdir -p "${SCRIPT_DIR}/logs" "${SCRIPT_DIR}/data" "${SCRIPT_DIR}/config"
    
    # Start the container interactively
    docker run -it --rm \
        --name "${CONTAINER_NAME}" \
        --hostname browserbot \
        -p "${VNC_PORT}:5900" \
        -p "${METRICS_PORT}:8000" \
        -p "${API_PORT}:8080" \
        -v "${SCRIPT_DIR}/logs:/home/browserbot/app/logs" \
        -v "${SCRIPT_DIR}/data:/home/browserbot/app/data" \
        -v "${SCRIPT_DIR}/config:/home/browserbot/app/config" \
        -v "${SCRIPT_DIR}/.env:/home/browserbot/app/.env:ro" \
        --env-file "${SCRIPT_DIR}/.env" \
        -e DISPLAY=:99 \
        -e VNC_PORT=5900 \
        --security-opt seccomp=unconfined \
        --shm-size=2g \
        "${IMAGE_NAME}" \
        /usr/local/bin/interactive-entrypoint.sh
}

# Start background services mode
start_services() {
    print_info "Starting BrowserBot services in background..."
    
    cd "${SCRIPT_DIR}"
    
    # Use docker-compose for services mode
    ${COMPOSE_CMD} up -d
    
    print_success "BrowserBot services started successfully!"
    print_info "🖥️  VNC Access: vncviewer localhost:${VNC_PORT} (password: browserbot)"
    print_info "📊 Metrics: http://localhost:${METRICS_PORT}"
    print_info "🔧 API: http://localhost:${API_PORT}"
    print_info ""
    print_info "To stop services: ${COMPOSE_CMD} down"
    print_info "To view logs: ${COMPOSE_CMD} logs -f"
}

# Show help
show_help() {
    cat << EOF
🤖 BrowserBot - AI-Powered Browser Automation

Usage: $0 [command] [options]

Commands:
  interactive, i        Start interactive BrowserBot session (default)
  services, s          Start background services mode
  stop                 Stop all BrowserBot services
  build               Build/rebuild Docker image
  logs                Show service logs
  status              Show system status
  test                Run system tests
  help, -h, --help    Show this help

Options:
  --rebuild           Force rebuild of Docker image
  --vnc-port=PORT     Set VNC port (default: 5900)
  --metrics-port=PORT Set metrics port (default: 8000)
  --api-port=PORT     Set API port (default: 8080)

Examples:
  $0                  # Start interactive mode
  $0 interactive      # Start interactive mode
  $0 services         # Start in background
  $0 --rebuild        # Rebuild and start interactive
  $0 stop             # Stop all services

For more information, visit: https://github.com/yourorg/BrowserBot
EOF
}

# Main script logic
main() {
    local command="interactive"
    local rebuild=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            interactive|i)
                command="interactive"
                shift
                ;;
            services|s)
                command="services"
                shift
                ;;
            stop)
                command="stop"
                shift
                ;;
            build)
                command="build"
                shift
                ;;
            logs)
                command="logs"
                shift
                ;;
            status)
                command="status"
                shift
                ;;
            test)
                command="test"
                shift
                ;;
            help|-h|--help)
                show_help
                exit 0
                ;;
            --rebuild)
                rebuild=true
                shift
                ;;
            --vnc-port=*)
                VNC_PORT="${1#*=}"
                shift
                ;;
            --metrics-port=*)
                METRICS_PORT="${1#*=}"
                shift
                ;;
            --api-port=*)
                API_PORT="${1#*=}"
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Check prerequisites
    check_docker
    
    case $command in
        interactive)
            if ! setup_env; then
                exit 1
            fi
            if [ "$rebuild" = true ]; then
                build_image force
            else
                build_image
            fi
            check_ports
            cleanup_container
            start_interactive
            ;;
        services)
            check_docker_compose
            if ! setup_env; then
                exit 1
            fi
            start_services
            ;;
        stop)
            check_docker_compose
            cd "${SCRIPT_DIR}"
            ${COMPOSE_CMD} down
            cleanup_container
            print_success "All BrowserBot services stopped"
            ;;
        build)
            build_image force
            ;;
        logs)
            check_docker_compose
            cd "${SCRIPT_DIR}"
            ${COMPOSE_CMD} logs -f
            ;;
        status)
            docker ps --filter "name=${PROJECT_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
            ;;
        test)
            if ! setup_env; then
                exit 1
            fi
            build_image
            print_info "Running BrowserBot tests..."
            docker run --rm \
                --env-file "${SCRIPT_DIR}/.env" \
                "${IMAGE_NAME}" \
                python3.11 -m pytest tests/ -v
            ;;
    esac
}

# Run main function
main "$@"
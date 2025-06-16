#!/bin/bash

# BrowserBot Docker-First Launcher with Halo Progress
# This script ensures BrowserBot always runs in a secure Docker container

set -euo pipefail

# Colors for output (only for errors)
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="browserbot"
CONTAINER_NAME="${PROJECT_NAME}-interactive"
IMAGE_NAME="${PROJECT_NAME}:latest"
VNC_PORT=${VNC_PORT:-5900}
METRICS_PORT=${METRICS_PORT:-8000}
API_PORT=${API_PORT:-8080}

# Use halo progress utility
HALO_PROGRESS="${SCRIPT_DIR}/scripts/halo_progress.py"
USE_HALO=true

# Simple print functions for when halo is not available
print_info() {
    echo -e "${BLUE}[INFO]${NC} ${1:-}"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} ${1:-}"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} ${1:-}" >&2
}

print_spinner() {
    echo -e "${YELLOW}[RUNNING]${NC} ${1:-}"
}

# Wrapper functions for halo or fallback printing
halo_or_print() {
    local cmd="$1"
    local message="$2"
    local duration="${3:-}"
    
    if [ "$USE_HALO" = true ] && [ -f "$HALO_PROGRESS" ] && command -v python3 &> /dev/null; then
        if [ -n "$duration" ]; then
            python3 "$HALO_PROGRESS" "$cmd" "$message" "$duration" 2>/dev/null || {
                USE_HALO=false
                case "$cmd" in
                    spinner) print_spinner "$message" ;;
                    success) print_success "$message" ;;
                    error) print_error "$message" ;;
                    info) print_info "$message" ;;
                esac
            }
        else
            python3 "$HALO_PROGRESS" "$cmd" "$message" 2>/dev/null || {
                USE_HALO=false
                case "$cmd" in
                    spinner) print_spinner "$message" ;;
                    success) print_success "$message" ;;
                    error) print_error "$message" ;;
                    info) print_info "$message" ;;
                esac
            }
        fi
    else
        USE_HALO=false
        case "$cmd" in
            spinner) print_spinner "$message" ;;
            success) print_success "$message" ;;
            error) print_error "$message" ;;
            info) print_info "$message" ;;
        esac
    fi
}

# Check and install halo if missing
check_and_install_halo() {
    if [ -f "$HALO_PROGRESS" ] && command -v python3 &> /dev/null; then
        # Check if halo module is available
        if ! python3 -c "import halo" 2>/dev/null; then
            # Try to install halo silently
            if pip3 install --user halo >/dev/null 2>&1 || python3 -m pip install --user halo >/dev/null 2>&1; then
                # Check again if it's available after installation
                if python3 -c "import halo" 2>/dev/null; then
                    USE_HALO=true
                    return
                fi
            fi
            # If we get here, halo isn't available but that's OK
            USE_HALO=false
        else
            # Halo is already installed
            USE_HALO=true
        fi
    else
        USE_HALO=false
    fi
}

# Check if Docker is running
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        print_error "Please install Docker from: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        print_error "Please start Docker and try again"
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
        exit 1
    fi
}

# Create .env file if it doesn't exist
setup_env() {
    if [ ! -f "${SCRIPT_DIR}/.env" ]; then
        if [ -f "${SCRIPT_DIR}/.env.example" ]; then
            cp "${SCRIPT_DIR}/.env.example" "${SCRIPT_DIR}/.env"
            halo_or_print error "Please edit .env file and add your API keys before running BrowserBot"
            return 1
        else
            print_error ".env.example file not found"
            exit 1
        fi
    fi
    
    # Check if required API key is set
    if ! grep -q "^OPENROUTER_API_KEY=.*[^=]" "${SCRIPT_DIR}/.env"; then
        halo_or_print error "OPENROUTER_API_KEY is not set in .env file"
        return 1
    fi
    
    return 0
}

# Build Docker image if needed
build_image() {
    if [ "${1:-}" = "force" ] || ! docker image inspect "${IMAGE_NAME}" &> /dev/null; then
        halo_or_print info "Building BrowserBot Docker image..."
        
        if docker build -t "${IMAGE_NAME}" "${SCRIPT_DIR}"; then
            halo_or_print success "Docker image built successfully!"
        else
            halo_or_print error "Docker build failed"
            return 1
        fi
    else
        halo_or_print info "Using existing Docker image: ${IMAGE_NAME}"
    fi
}

# Stop and remove existing container
cleanup_container() {
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        halo_or_print info "Stopping and removing existing container..."
        docker stop "${CONTAINER_NAME}" &> /dev/null || true
        docker rm "${CONTAINER_NAME}" &> /dev/null || true
    fi
}

# Start Redis container for caching
start_redis() {
    local redis_container="browserbot-redis-standalone"
    
    # Check if Redis is already running
    if docker ps -q -f name="$redis_container" | grep -q .; then
        return 0
    fi
    
    # Remove any stopped Redis container
    docker rm -f "$redis_container" &> /dev/null || true
    
    # Start Redis with progress
    if [ "$USE_HALO" = true ]; then
        halo_or_print spinner "Starting Redis cache" 3 &
        local spinner_pid=$!
    else
        halo_or_print spinner "Starting Redis cache"
    fi
    
    if docker run -d \
        --name "$redis_container" \
        -p 6379:6379 \
        --restart unless-stopped \
        redis:7-alpine \
        redis-server --appendonly yes --requirepass browserbot123 \
        > /dev/null 2>&1; then
        
        # Wait for Redis to be ready
        local retries=10
        while [ $retries -gt 0 ]; do
            if docker exec "$redis_container" redis-cli -a browserbot123 ping &> /dev/null; then
                if [ "$USE_HALO" = true ] && [ -n "${spinner_pid:-}" ]; then
                    kill $spinner_pid 2>/dev/null || true
                    wait $spinner_pid 2>/dev/null || true
                fi
                halo_or_print success "Redis started successfully!"
                return 0
            fi
            sleep 0.5
            ((retries--))
        done
    fi
    
    if [ "$USE_HALO" = true ] && [ -n "${spinner_pid:-}" ]; then
        kill $spinner_pid 2>/dev/null || true
        wait $spinner_pid 2>/dev/null || true
    fi
    halo_or_print error "Failed to start Redis"
    return 1
}

# Validate task input for security
validate_task_input() {
    local task="$1"
    
    # Check if task is empty
    if [ -z "$task" ]; then
        halo_or_print error "Task cannot be empty"
        return 1
    fi
    
    # Check for potentially dangerous patterns
    if echo "$task" | grep -qE '[`$(){};&|<>]'; then
        halo_or_print error "Task contains potentially unsafe characters"
        return 1
    fi
    
    # Check task length (reasonable limit)
    if [ ${#task} -gt 500 ]; then
        halo_or_print error "Task description too long (max 500 characters)"
        return 1
    fi
    
    return 0
}

# Execute a single task
execute_task() {
    local task="$*"
    
    # Validate input
    if ! validate_task_input "$task"; then
        exit 2
    fi
    
    echo -e "\n🤖 BrowserBot Task Execution"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "Task: $task\n"
    
    # Step 1: Initialize environment
    if [ "$USE_HALO" = true ]; then
        halo_or_print spinner "Initializing environment" 2 &
        local spinner_pid=$!
    else
        halo_or_print spinner "Initializing environment"
    fi
    
    if ! setup_env; then
        if [ "$USE_HALO" = true ] && [ -n "${spinner_pid:-}" ]; then
            kill $spinner_pid 2>/dev/null || true
            wait $spinner_pid 2>/dev/null || true
        fi
        exit 1
    fi
    
    if [ "$USE_HALO" = true ] && [ -n "${spinner_pid:-}" ]; then
        kill $spinner_pid 2>/dev/null || true
        wait $spinner_pid 2>/dev/null || true
    fi
    
    # Step 2: Check Docker image
    if ! docker image inspect "${IMAGE_NAME}" &> /dev/null; then
        build_image
    fi
    
    # Step 3: Start Redis
    start_redis
    
    # Step 4: Prepare workspace
    if [ "$USE_HALO" = true ]; then
        halo_or_print spinner "Preparing workspace" 1 &
        spinner_pid=$!
    else
        halo_or_print spinner "Preparing workspace"
    fi
    mkdir -p "${SCRIPT_DIR}/logs" "${SCRIPT_DIR}/data"
    if [ "$USE_HALO" = true ] && [ -n "${spinner_pid:-}" ]; then
        kill $spinner_pid 2>/dev/null || true
        wait $spinner_pid 2>/dev/null || true
    fi
    
    # Step 5: Launch BrowserBot
    halo_or_print info "Launching BrowserBot..."
    echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    # Execute task in container
    docker run -t --rm \
        --name "${PROJECT_NAME}-task-$$" \
        --hostname browserbot \
        -e DISPLAY=:99 \
        -e BROWSER_HEADLESS=true \
        -e REDIS_URL=redis://:browserbot123@host.docker.internal:6379/0 \
        -e LOG_FORMAT=text \
        -e PYTHONUNBUFFERED=1 \
        -e PYTHONIOENCODING=utf-8 \
        -v "${SCRIPT_DIR}/logs:/home/browserbot/app/logs" \
        -v "${SCRIPT_DIR}/data:/home/browserbot/app/data" \
        -v "${SCRIPT_DIR}/.env:/home/browserbot/app/.env:ro" \
        --env-file "${SCRIPT_DIR}/.env" \
        --security-opt seccomp=unconfined \
        --shm-size=2g \
        --add-host=host.docker.internal:host-gateway \
        "${IMAGE_NAME}" \
        python3.11 -u -m browserbot.main --task "$task"
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        halo_or_print success "Task completed successfully"
    else
        halo_or_print error "Task failed with exit code $exit_code"
    fi
    
    return $exit_code
}

# Run tests inside Docker container
run_tests() {
    echo -e "\n🧪 BrowserBot Test Execution"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "Running all tests inside Docker container\n"
    
    # Step 1: Initialize environment
    halo_or_print spinner "Initializing test environment"
    
    if ! setup_env; then
        exit 1
    fi
    
    # Step 2: Check Docker image
    if ! docker image inspect "${IMAGE_NAME}" &> /dev/null; then
        build_image
    fi
    
    # Step 3: Start Redis for tests
    start_redis
    
    # Step 4: Prepare test workspace
    halo_or_print spinner "Preparing test workspace"
    mkdir -p "${SCRIPT_DIR}/logs" "${SCRIPT_DIR}/data" "${SCRIPT_DIR}/test-results"
    
    # Step 5: Run tests in container
    halo_or_print info "Running tests in Docker container..."
    echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    # Execute tests in container
    docker run -t --rm \
        --name "${PROJECT_NAME}-tests-$$" \
        --hostname browserbot-test \
        -e DISPLAY=:99 \
        -e BROWSER_HEADLESS=true \
        -e REDIS_URL=redis://:browserbot123@host.docker.internal:6379/0 \
        -e LOG_FORMAT=text \
        -e PYTHONUNBUFFERED=1 \
        -e PYTHONIOENCODING=utf-8 \
        -e TESTING=true \
        -v "${SCRIPT_DIR}/logs:/home/browserbot/app/logs" \
        -v "${SCRIPT_DIR}/data:/home/browserbot/app/data" \
        -v "${SCRIPT_DIR}/test-results:/home/browserbot/app/test-results" \
        -v "${SCRIPT_DIR}/.env:/home/browserbot/app/.env:ro" \
        --env-file "${SCRIPT_DIR}/.env" \
        --security-opt seccomp=unconfined \
        --shm-size=2g \
        --add-host=host.docker.internal:host-gateway \
        "${IMAGE_NAME}" \
        bash -c "cd /home/browserbot/app && python3.11 -m pytest tests/ -v --tb=short --junit-xml=test-results/junit.xml --html=test-results/report.html --self-contained-html || true"
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        halo_or_print success "All tests passed!"
    else
        halo_or_print error "Some tests failed. Check test-results/report.html for details."
    fi
    
    return $exit_code
}

# Show help
show_help() {
    cat << EOF
🤖 BrowserBot - AI-Powered Browser Automation

Usage: $0 [command] [options]
       $0 task "task description"

Commands:
  task, exec         Execute a single task
  test               Run all tests inside Docker container
  build              Force rebuild Docker image
  help, -h, --help   Show this help

Examples:
  $0 task "go to google.com and search for python"
  $0 task "navigate to amazon and find laptop prices"
  $0 test            # Run all tests
  $0 build           # Force rebuild Docker image

For more information, visit: https://github.com/overtimepog/BrowserBot
EOF
}

# Main script logic
main() {
    # Check and install halo if needed
    check_and_install_halo
    
    # Check prerequisites
    check_docker
    
    # Parse arguments
    case "${1:-}" in
        task|exec)
            shift
            execute_task "$@"
            ;;
        test)
            run_tests
            ;;
        build)
            build_image force
            ;;
        help|-h|--help)
            show_help
            exit 0
            ;;
        *)
            if [ $# -gt 0 ]; then
                # Treat as task
                execute_task "$@"
            else
                show_help
                exit 1
            fi
            ;;
    esac
}

# Run main function
main "$@"
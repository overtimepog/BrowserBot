#!/bin/bash

# BrowserBot Test Runner Script
# This script demonstrates all testing capabilities inside Docker

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Simple print functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} ${1:-}"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} ${1:-}"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} ${1:-}" >&2
}

print_test() {
    echo -e "${YELLOW}[TEST]${NC} ${1:-}"
}

# Show help
show_help() {
    cat << EOF
🧪 BrowserBot Test Runner

This script runs comprehensive tests for BrowserBot inside Docker containers.

Usage: $0 [test-type]

Test Types:
  all           Run all tests (default)
  unit          Run only unit tests
  integration   Run only integration tests
  browser       Run browser automation tests
  quick         Run quick smoke tests
  coverage      Run tests with coverage report

Examples:
  $0              # Run all tests
  $0 unit         # Run only unit tests
  $0 coverage     # Run tests with coverage report

EOF
}

# Run specific test type
run_test_type() {
    local test_type="${1:-all}"
    
    print_test "Running $test_type tests..."
    
    case "$test_type" in
        all)
            ./run.sh test
            ;;
        unit)
            print_info "Running unit tests only..."
            docker run -t --rm \
                --name "browserbot-unit-tests-$$" \
                -e PYTHONPATH=/home/browserbot/app/src \
                -v "${SCRIPT_DIR}/test-results:/home/browserbot/app/test-results" \
                browserbot:latest \
                bash -c "cd /home/browserbot/app && python3.11 -m pytest tests/unit/ -v"
            ;;
        integration)
            print_info "Running integration tests only..."
            docker run -t --rm \
                --name "browserbot-integration-tests-$$" \
                -e DISPLAY=:99 \
                -e PYTHONPATH=/home/browserbot/app/src \
                -v "${SCRIPT_DIR}/test-results:/home/browserbot/app/test-results" \
                --shm-size=2g \
                browserbot:latest \
                bash -c "cd /home/browserbot/app && python3.11 -m pytest tests/integration/ -v"
            ;;
        browser)
            print_info "Running browser automation tests..."
            # Start Redis for browser tests
            docker run -d --name browserbot-redis-test -p 6379:6379 redis:7-alpine > /dev/null 2>&1 || true
            
            docker run -t --rm \
                --name "browserbot-browser-tests-$$" \
                -e DISPLAY=:99 \
                -e BROWSER_HEADLESS=true \
                -e REDIS_URL=redis://host.docker.internal:6379/0 \
                -e PYTHONPATH=/home/browserbot/app/src \
                -v "${SCRIPT_DIR}/test-results:/home/browserbot/app/test-results" \
                --add-host=host.docker.internal:host-gateway \
                --shm-size=2g \
                browserbot:latest \
                bash -c "cd /home/browserbot/app && python3.11 -m pytest tests/integration/test_browser_integration.py -v -s"
            
            # Stop Redis
            docker stop browserbot-redis-test > /dev/null 2>&1 || true
            docker rm browserbot-redis-test > /dev/null 2>&1 || true
            ;;
        quick)
            print_info "Running quick smoke tests..."
            docker run -t --rm \
                --name "browserbot-smoke-tests-$$" \
                -e PYTHONPATH=/home/browserbot/app/src \
                browserbot:latest \
                bash -c "cd /home/browserbot/app && python3.11 -m pytest tests/unit/test_config.py tests/unit/test_errors.py -v"
            ;;
        coverage)
            print_info "Running tests with coverage report..."
            docker run -t --rm \
                --name "browserbot-coverage-tests-$$" \
                -e DISPLAY=:99 \
                -e PYTHONPATH=/home/browserbot/app/src \
                -v "${SCRIPT_DIR}/test-results:/home/browserbot/app/test-results" \
                -v "${SCRIPT_DIR}/htmlcov:/home/browserbot/app/htmlcov" \
                --shm-size=2g \
                browserbot:latest \
                bash -c "cd /home/browserbot/app && python3.11 -m pytest tests/ --cov=src --cov-report=html --cov-report=term -v"
            print_success "Coverage report generated at: htmlcov/index.html"
            ;;
        *)
            print_error "Unknown test type: $test_type"
            show_help
            exit 1
            ;;
    esac
}

# Main execution
main() {
    echo -e "\n🧪 BrowserBot Test Suite"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    # Check if BrowserBot image exists
    if ! docker image inspect browserbot:latest &> /dev/null; then
        print_info "BrowserBot Docker image not found. Building..."
        ./run.sh build
    fi
    
    # Create test directories
    mkdir -p "${SCRIPT_DIR}/test-results" "${SCRIPT_DIR}/htmlcov"
    
    # Run tests based on argument
    if [[ "${1:-}" == "help" ]] || [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
        show_help
        exit 0
    else
        run_test_type "${1:-all}"
    fi
    
    echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_success "Test execution completed!"
    
    # Show test results location
    if [ -f "${SCRIPT_DIR}/test-results/report.html" ]; then
        print_info "View detailed test report: test-results/report.html"
    fi
}

# Run main function
main "$@"
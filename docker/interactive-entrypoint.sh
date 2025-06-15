#!/bin/bash

# Interactive BrowserBot Entry Point
# This script sets up and starts BrowserBot in interactive mode within the container

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

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

print_header() {
    echo -e "${CYAN}$1${NC}"
}

# Start background services
start_services() {
    print_info "Starting background services..."
    
    # Start supervisor for VNC and display services
    sudo /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf > /dev/null 2>&1 &
    
    # Wait for services to start
    sleep 3
    
    # Check if X server is running
    if ! pgrep Xvfb > /dev/null; then
        print_warning "X server not running, starting manually..."
        Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset > /dev/null 2>&1 &
        sleep 2
    fi
    
    # Check if VNC is running
    if ! pgrep x11vnc > /dev/null; then
        print_warning "VNC server not running, starting manually..."
        x11vnc -display :99 -nopw -listen 0.0.0.0 -xkb -ncache 10 -forever -shared -rfbport 5900 -rfbauth /home/browserbot/.vnc/passwd > /dev/null 2>&1 &
        sleep 2
    fi
    
    export DISPLAY=:99
    print_success "Background services started"
}

# Show system status
show_status() {
    print_header "📊 BrowserBot System Status"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Python version
    python_version=$(python3.11 --version 2>/dev/null || echo "Not found")
    echo "🐍 Python: $python_version"
    
    # Display
    echo "🖥️  Display: ${DISPLAY:-Not set}"
    
    # VNC status
    if pgrep x11vnc > /dev/null; then
        echo "🖼️  VNC: Running on port 5900"
    else
        echo "🖼️  VNC: Not running"
    fi
    
    # X server status
    if pgrep Xvfb > /dev/null; then
        echo "🪟 X Server: Running"
    else
        echo "🪟 X Server: Not running"
    fi
    
    # Chrome version
    chrome_version=$(google-chrome --version 2>/dev/null || echo "Not found")
    echo "🌐 Chrome: $chrome_version"
    
    # Environment check
    if [ -f "/home/browserbot/app/.env" ]; then
        if grep -q "^OPENROUTER_API_KEY=.*[^=]" /home/browserbot/app/.env; then
            echo "🔑 API Key: Configured"
        else
            echo "🔑 API Key: Not configured"
        fi
    else
        echo "🔑 API Key: .env file not found"
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Print help
print_help() {
    print_header "🤖 BrowserBot Commands"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  help                     - Show this help message"
    echo "  task: <description>      - Execute a browser automation task"
    echo "  chat <message>           - Chat with the AI agent"
    echo "  screenshot               - Take a screenshot of current page"
    echo "  navigate <url>           - Navigate to a specific URL"
    echo "  status                   - Show system status"
    echo "  test                     - Run basic functionality test"
    echo "  shell                    - Start Python shell with BrowserBot"
    echo "  logs                     - View recent logs"
    echo "  vnc                      - Show VNC connection info"
    echo "  services                 - Restart background services"
    echo "  exit                     - Exit BrowserBot"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Examples:"
    echo "  Go to google.com and search for python automation"
    echo "  task: Navigate to news websites and summarize headlines"
    echo "  chat What can you help me automate?"
    echo "  navigate https://example.com"
}

# Run basic test
run_test() {
    print_info "Running BrowserBot functionality test..."
    
    # Test imports
    python3.11 -c "
import sys
sys.path.insert(0, '/home/browserbot/app/src')

try:
    from browserbot.core.config import settings
    print('✅ Configuration loaded')
    
    from browserbot.browser.browser_manager import BrowserManager
    print('✅ Browser manager imported')
    
    from browserbot.agents.browser_agent import BrowserAgent
    print('✅ Browser agent imported')
    
    print('✅ All components loaded successfully')
    print('🎉 BrowserBot is ready to use!')
except Exception as e:
    print(f'❌ Test failed: {e}')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        print_success "All tests passed!"
    else
        print_error "Tests failed!"
        return 1
    fi
}

# Show VNC info
show_vnc_info() {
    print_header "🖥️ VNC Connection Information"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Host: localhost"
    echo "Port: 5900"
    echo "Password: browserbot"
    echo ""
    echo "Connection examples:"
    echo "  - VNC Viewer: localhost:5900"
    echo "  - macOS: vnc://localhost:5900"
    echo "  - Command line: vncviewer localhost:5900"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# View logs
view_logs() {
    if [ -d "/home/browserbot/app/logs" ]; then
        log_files=$(find /home/browserbot/app/logs -name "*.log" -type f 2>/dev/null || true)
        if [ -n "$log_files" ]; then
            latest_log=$(echo "$log_files" | xargs ls -t | head -n1)
            if [ -f "$latest_log" ]; then
                print_info "Showing last 20 lines from $latest_log:"
                tail -20 "$latest_log"
            else
                print_warning "No log files found"
            fi
        else
            print_warning "No log files found"
        fi
    else
        print_warning "Logs directory not found"
    fi
}

# Execute task
execute_task() {
    local task_description="$1"
    print_info "Executing task: $task_description"
    
    python3.11 -c "
import sys
import asyncio
sys.path.insert(0, '/home/browserbot/app/src')

async def run_task():
    try:
        from browserbot.agents.browser_agent import BrowserAgent
        async with BrowserAgent() as agent:
            result = await agent.execute_task('$task_description')
            if result.get('success'):
                print(f'✅ Task completed: {result.get(\"output\", \"Done\")}')
            else:
                print(f'❌ Task failed: {result.get(\"error\", \"Unknown error\")}')
    except Exception as e:
        print(f'❌ Error: {e}')

asyncio.run(run_task())
"
}

# Chat with agent
chat_with_agent() {
    local message="$1"
    print_info "Chatting with agent: $message"
    
    python3.11 -c "
import sys
import asyncio
sys.path.insert(0, '/home/browserbot/app/src')

async def chat():
    try:
        from browserbot.agents.browser_agent import BrowserAgent
        async with BrowserAgent() as agent:
            result = await agent.chat('$message')
            if result.get('success'):
                print(f'🤖 {result.get(\"response\", \"No response\")}')
            else:
                print(f'❌ Chat failed: {result.get(\"error\", \"Unknown error\")}')
    except Exception as e:
        print(f'❌ Error: {e}')

asyncio.run(chat())
"
}

# Navigate to URL
navigate_to_url() {
    local url="$1"
    execute_task "Navigate to $url"
}

# Take screenshot
take_screenshot() {
    execute_task "Take a screenshot of the current page"
}

# Start Python shell
start_shell() {
    print_info "Starting Python shell with BrowserBot (exit with Ctrl+D)"
    python3.11 -c "
import sys
sys.path.insert(0, '/home/browserbot/app/src')

# Import common modules
try:
    from browserbot.agents.browser_agent import BrowserAgent
    from browserbot.core.config import settings
    print('BrowserBot modules imported. Try: agent = BrowserAgent()')
except Exception as e:
    print(f'Warning: {e}')

import code
code.interact(local=globals())
"
}

# Restart services
restart_services() {
    print_info "Restarting background services..."
    
    # Stop existing services
    sudo pkill -f supervisord || true
    pkill -f x11vnc || true
    pkill -f Xvfb || true
    
    sleep 2
    
    # Start services
    start_services
    print_success "Services restarted"
}

# Main interactive loop
main_loop() {
    print_header "🤖 Welcome to BrowserBot Interactive Mode!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🖥️  VNC Access: Use VNC client to connect to localhost:5900 (password: browserbot)"
    echo "📊 Metrics: http://localhost:8000"
    echo "🔧 API: http://localhost:8080"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Type 'help' for available commands or start with a task like:"
    echo "  Go to google.com and search for python automation"
    echo "  task: Navigate to news websites and summarize headlines"
    echo ""
    
    # Set up Python path
    export PYTHONPATH=/home/browserbot/app/src
    
    while true; do
        echo -n "BrowserBot> "
        read -r user_input
        
        # Trim whitespace
        user_input=$(echo "$user_input" | xargs)
        
        if [ -z "$user_input" ]; then
            continue
        fi
        
        case "$user_input" in
            "exit"|"quit"|"q")
                print_success "Goodbye!"
                break
                ;;
            "help")
                print_help
                ;;
            "status")
                show_status
                ;;
            "test")
                run_test
                ;;
            "logs")
                view_logs
                ;;
            "vnc")
                show_vnc_info
                ;;
            "services")
                restart_services
                ;;
            "shell")
                start_shell
                ;;
            "screenshot")
                take_screenshot
                ;;
            task:*)
                task_desc="${user_input#task:}"
                task_desc=$(echo "$task_desc" | xargs)
                if [ -n "$task_desc" ]; then
                    execute_task "$task_desc"
                else
                    print_error "Please provide a task description"
                fi
                ;;
            chat\ *)
                message="${user_input#chat }"
                if [ -n "$message" ]; then
                    chat_with_agent "$message"
                else
                    print_error "Please provide a message"
                fi
                ;;
            navigate\ *)
                url="${user_input#navigate }"
                if [ -n "$url" ]; then
                    navigate_to_url "$url"
                else
                    print_error "Please provide a URL"
                fi
                ;;
            *)
                # Try to interpret as a task
                execute_task "$user_input"
                ;;
        esac
    done
}

# Entry point
main() {
    # Change to app directory
    cd /home/browserbot/app
    
    # Start background services
    start_services
    
    # Run initial test
    if ! run_test; then
        print_error "Initial test failed. Some features may not work correctly."
    fi
    
    # Set up Python path
    export PYTHONPATH=/home/browserbot/app/src
    
    # Start the Python CLI instead of the bash loop
    print_info "Starting BrowserBot Python CLI..."
    python3.11 -m browserbot.main
}

# Handle signals
trap 'echo ""; print_success "Goodbye!"; exit 0' INT TERM

# Run main function
main "$@"
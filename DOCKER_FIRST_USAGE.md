# BrowserBot Docker-First Usage Guide

BrowserBot is designed with a **Docker-First** approach for maximum security, consistency, and ease of use. You don't need to install Python, dependencies, or manage virtual environments locally - everything runs in a secure, isolated container.

## 🚀 Quick Start

### Prerequisites
- **Docker Desktop** (Windows/macOS) or **Docker Engine** (Linux)
- **8GB+ RAM** recommended
- **2GB+ free disk space**

### One-Command Launch

**Windows:**
```cmd
run.bat
```

**Unix/Linux/macOS:**
```bash
./run.sh
```

That's it! BrowserBot will automatically:
1. Check for Docker installation
2. Create/validate environment configuration
3. Build the Docker image (first run only)
4. Start an interactive session with GUI support

## 🖥️ Access Methods

### Interactive Terminal
Primary interaction through the container terminal:
```
BrowserBot> Go to google.com and search for python automation
BrowserBot> task: Navigate to news websites and summarize headlines
BrowserBot> chat What websites can you help me automate?
```

### VNC Visual Access
Connect with any VNC client to see the browser:
- **Host:** `localhost`
- **Port:** `5900`
- **Password:** `browserbot`

**Connection Examples:**
```bash
# VNC Viewer
vncviewer localhost:5900

# macOS built-in
open vnc://localhost:5900

# Windows: Use any VNC client like RealVNC, TightVNC, etc.
```

### Web Interfaces
- **Metrics Dashboard:** http://localhost:8000
- **API Endpoint:** http://localhost:8080 (if enabled)

## 📋 Available Commands

### Launch Script Commands
```bash
./run.sh [command] [options]

Commands:
  interactive, i        Start interactive session (default)
  services, s          Start background services
  stop                 Stop all services
  build               Force rebuild Docker image
  logs                View container logs
  status              Show running containers
  test                Run system tests
  help                Show help

Options:
  --rebuild           Force image rebuild
  --vnc-port=PORT     Custom VNC port (default: 5900)
  --metrics-port=PORT Custom metrics port (default: 8000)
  --api-port=PORT     Custom API port (default: 8080)
```

### Interactive Session Commands
Once inside BrowserBot:
```
help                     - Show available commands
task: <description>      - Execute automation task
chat <message>           - Chat with AI agent
screenshot               - Take screenshot
navigate <url>           - Go to specific URL
status                   - Show system status
test                     - Run functionality test
shell                    - Python shell access
logs                     - View recent logs
vnc                      - Show VNC connection info
services                 - Restart background services
exit                     - Exit session
```

## 🔧 Configuration

### Environment Setup
On first run, BrowserBot creates `.env` from `.env.example`. Edit it to add your API keys:

```bash
# Required
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key

# Browser settings
BROWSER_HEADLESS=false
VNC_PORT=5900
```

### Custom Ports
If default ports are in use:
```bash
./run.sh --vnc-port=5901 --metrics-port=8001 --api-port=8081
```

## 🌍 Cross-Platform Usage

### Windows
```cmd
# Standard launch
run.bat

# Background services
run.bat services

# Stop everything
run.bat stop
```

### macOS/Linux
```bash
# Standard launch
./run.sh

# Background services
./run.sh services

# Stop everything
./run.sh stop
```

## 📊 Different Operation Modes

### 1. Interactive Mode (Default)
Direct terminal interaction with the AI agent:
```bash
./run.sh interactive
```
- Real-time command execution
- Immediate feedback
- Full access to all features
- VNC visual monitoring

### 2. Background Services Mode
Run as system services:
```bash
./run.sh services
```
- Persistent operation
- Web API access
- Monitoring dashboards
- Suitable for automation servers

### 3. Testing Mode
Validate installation and functionality:
```bash
./run.sh test
```
- Component verification
- Dependency checks
- Basic functionality tests
- Performance benchmarks

## 🔍 Monitoring & Debugging

### Container Logs
```bash
# Real-time logs
./run.sh logs

# Docker compose logs
docker-compose logs -f browserbot
```

### System Status
```bash
# From host
./run.sh status

# From inside container
BrowserBot> status
```

### Health Checks
The container includes built-in health checks:
```bash
docker ps  # Shows health status
```

## 🛠️ Development & Customization

### Custom Browser Settings
Edit `.env` file:
```bash
BROWSER_HEADLESS=false          # Set to true for headless mode
BROWSER_VIEWPORT_WIDTH=1920     # Custom viewport size
BROWSER_VIEWPORT_HEIGHT=1080
BROWSER_TIMEOUT=30000           # Timeout in milliseconds
```

### Adding Custom Tools
Mount additional scripts or tools:
```bash
docker run -it --rm \
  -v ./custom-scripts:/home/browserbot/app/custom \
  browserbot:latest \
  /usr/local/bin/interactive-entrypoint.sh
```

### Performance Tuning
Adjust resource limits in `docker-compose.yml`:
```yaml
services:
  browserbot:
    deploy:
      resources:
        limits:
          memory: 8G      # Increase for heavy workloads
          cpus: '4'       # More CPU cores
```

## 🚨 Troubleshooting

### Common Issues

**Port Already in Use:**
```bash
# Use different ports
./run.sh --vnc-port=5901

# Or stop conflicting services
sudo lsof -i :5900
```

**Docker Not Running:**
```bash
# macOS/Windows: Start Docker Desktop
# Linux: Start Docker daemon
sudo systemctl start docker
```

**Permission Denied:**
```bash
# Make script executable
chmod +x run.sh
```

**API Key Not Set:**
```bash
# Edit .env file
nano .env
# Add: OPENROUTER_API_KEY=your-key-here
```

### Reset Everything
```bash
./run.sh stop
docker system prune -f
./run.sh --rebuild
```

## 🔐 Security Features

### Container Isolation
- Runs as non-root user inside container
- No access to host file system (except mounted volumes)
- Network isolation with controlled port exposure
- Sandboxed browser execution

### Data Persistence
- Logs: `./logs/` (mounted volume)
- Data: `./data/` (mounted volume)  
- Config: `./config/` (mounted volume)
- Environment: `.env` (read-only mount)

### Resource Limits
- Memory: 4GB limit (2GB reserved)
- CPU: 2 cores limit (1 core reserved)
- Disk: Limited to mounted volumes

## 📈 Performance Tips

1. **Allocate Sufficient Memory:** 8GB+ recommended for complex automations
2. **Use SSD Storage:** Faster container startup and operation
3. **Close Unused Applications:** More resources for Docker
4. **Monitor Resource Usage:** Check Docker Desktop resource monitor

## 🤝 Support & Updates

### Getting Help
```bash
./run.sh help              # Script help
BrowserBot> help           # Interactive help
```

### Updates
```bash
git pull                   # Get latest code
./run.sh --rebuild        # Rebuild with updates
```

### Community
- Report issues: GitHub Issues
- Discussions: GitHub Discussions
- Documentation: Project Wiki

---

**Ready to automate? Just run `./run.sh` and start commanding your AI browser agent!** 🤖🌐
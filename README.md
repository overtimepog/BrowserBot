# BrowserBot 🤖

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Type checking: mypy](https://img.shields.io/badge/type%20checking-mypy-blue)](https://mypy.readthedocs.io/)
[![Tests: pytest](https://img.shields.io/badge/tests-pytest-green.svg)](https://pytest.org/)
[![AI Model: DeepSeek-R1](https://img.shields.io/badge/AI-DeepSeek--R1-orange.svg)](https://openrouter.ai/)

A robust, production-ready browser automation agent powered by AI, built with modern Python technologies and best practices.

## ✨ Features

- **🧠 AI-Powered Decision Making**: Integration with DeepSeek-R1 via OpenRouter for intelligent browser automation
- **🕵️ Stealth Browser Automation**: Playwright-based automation with anti-detection capabilities
- **🐳 Docker Containerization**: Full GUI support with VNC access for headed browser operations
- **🛡️ Comprehensive Error Handling**: Circuit breaker patterns, exponential backoff, and intelligent retry mechanisms
- **🧠 Memory Persistence**: Long-term memory capabilities for cross-session learning
- **🏗️ Production-Ready Architecture**: Structured logging, monitoring, and observability
- **🧪 Extensive Testing**: Unit, integration, and end-to-end testing with pytest and Playwright Test
- **🔒 Security First**: Input validation, CSRF protection, and secure secret management
- **📊 Monitoring & Observability**: Prometheus metrics, OpenTelemetry tracing, health checks
- **⚡ High Performance**: Async operations, connection pooling, resource optimization

## Architecture

BrowserBot follows a modular, layered architecture:

```
src/browserbot/
├── core/           # Core functionality (config, logging, errors, retry)
├── browser/        # Browser automation layer (Playwright integration)
├── agents/         # AI agent implementation (LangChain integration)
├── memory/         # Memory and persistence layer
├── utils/          # Utility functions and helpers
└── security/       # Security and authentication components
```

## Requirements

- Python 3.11+
- Docker and Docker Compose
- Redis (for memory persistence)
- VNC viewer (for browser visualization)

## 🚀 Quick Start (Docker-First Approach)

BrowserBot is designed to run in Docker for maximum security and consistency. **No Python installation required!**

### Prerequisites
- Docker Desktop (Windows/macOS) or Docker Engine (Linux)
- 8GB+ RAM recommended

### One-Command Launch

**Windows:**
```cmd
run.bat
```

**Unix/Linux/macOS:**
```bash
./run.sh
```

**That's it!** BrowserBot will automatically:
1. Check Docker installation
2. Create environment configuration  
3. Build the Docker image
4. Start interactive session with GUI support

### First-Time Setup
1. Clone the repository:
```bash
git clone https://github.com/yourusername/BrowserBot.git
cd BrowserBot
```

2. Add your API key to `.env` (created automatically):
```bash
OPENROUTER_API_KEY=your-openrouter-api-key-here
```

3. Launch BrowserBot:
```bash
./run.sh
```

For detailed Docker usage, see [DOCKER_FIRST_USAGE.md](DOCKER_FIRST_USAGE.md)

## 🎬 Demo

![BrowserBot Demo](https://user-images.githubusercontent.com/placeholder/demo.gif)

### Live Example Commands

```bash
# Navigate and extract data
BrowserBot> Go to news.ycombinator.com and summarize the top 5 stories

# E-commerce automation
BrowserBot> Go to Amazon and find the best-rated wireless headphones under $100

# Form automation
BrowserBot> Fill out the contact form at example.com with test data

# Data extraction
BrowserBot> Extract all product prices from this shopping page

# Visual verification
BrowserBot> Take a screenshot and verify the login was successful
```

### Real-World Use Cases

- **🛒 E-commerce Testing**: Automate product searches, cart operations, checkout flows
- **📰 Content Scraping**: Extract news articles, product information, pricing data  
- **🧪 QA Automation**: Automated UI testing, regression testing, user journey validation
- **📊 Data Collection**: Monitor competitor pricing, gather market intelligence
- **🔐 Authentication Testing**: Login flows, multi-factor authentication, session management

## Configuration

BrowserBot uses environment variables for configuration. Key settings include:

- `OPENROUTER_API_KEY`: Your OpenRouter API key for AI model access
- `MODEL_NAME`: AI model to use (default: deepseek/deepseek-r1-0528-qwen3-8b:free)
- `BROWSER_HEADLESS`: Run browser in headless mode (default: false)
- `VNC_PORT`: VNC server port for browser visualization (default: 5900)
- `REDIS_URL`: Redis connection URL for memory persistence
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

See `src/browserbot/core/config.py` for all available configuration options.

## Usage

### Interactive Mode (Recommended)

Launch the interactive terminal:
```bash
./run.sh cli
# or
./run.sh interactive
```

Then use natural language commands:
```
BrowserBot> Go to google.com and search for python automation
BrowserBot> task: Navigate to news websites and summarize headlines  
BrowserBot> chat What can you help me automate?
BrowserBot> screenshot
BrowserBot> help
```

### Available Commands

| Command | Description |
|---------|-------------|
| `./run.sh cli` | Start interactive CLI mode |
| `./run.sh task "description"` | Execute a single task |
| `./run.sh test` | Run all tests |
| `./run.sh build` | Force rebuild Docker image |
| `./run.sh help` | Show help information |

### Visual Browser Access

Connect with VNC to see the browser in action:
- **Host:** localhost:5900
- **Password:** browserbot

```bash
# macOS
open vnc://localhost:5900

# Linux
vncviewer localhost:5900

# Windows: Use any VNC client
```

### Background Services Mode

For persistent operation:
```bash
./run.sh services
```

Access via:
- **VNC:** localhost:5900
- **Metrics:** http://localhost:8000
- **API:** http://localhost:8080

### Programmatic Usage (Advanced)

For custom integrations, you can also use the Python API:
```python
from browserbot import BrowserAgent

# Initialize the agent
agent = BrowserAgent()

# Navigate and interact with a website
result = await agent.execute_task(
    "Go to example.com and find information about their products"
)

print(result)
```

### Running Tests

```bash
./run.sh test           # Run all tests in container
./run.sh build          # Rebuild Docker image
./run.sh logs           # View container logs
./run.sh status         # Show running containers
```

## Development

### Code Quality

The project uses several tools to maintain code quality:

- **Black**: Code formatting
- **Ruff**: Fast Python linter
- **MyPy**: Static type checking
- **Pre-commit**: Git hooks for code quality

Set up pre-commit hooks:
```bash
pre-commit install
```

### Project Structure

- `src/browserbot/`: Main application code
- `tests/`: Test suite
- `docker/`: Docker configuration files
- `config/`: Configuration templates
- `docs/`: Additional documentation
- `logs/`: Application logs (git-ignored)
- `data/`: Persistent data storage (git-ignored)

## Security

BrowserBot implements several security measures:

- Input validation and sanitization
- CSRF protection
- Authentication and authorization
- Secure secret management
- Network isolation in Docker
- Principle of least privilege

## 📊 Monitoring & Performance

### Built-in Monitoring

- **Structured JSON Logging**: Configurable levels with context-aware logging
- **Prometheus Metrics**: `/metrics` endpoint for monitoring integration
- **OpenTelemetry Tracing**: Distributed tracing for performance analysis
- **Health Check Endpoints**: `/health` and `/readiness` for container orchestration
- **Real-time Metrics**: Browser performance, task completion times, error rates

### Key Metrics Tracked

```
browserbot_tasks_total{status="success|failed|timeout"}
browserbot_page_load_duration_seconds
browserbot_ai_response_duration_seconds
browserbot_browser_memory_usage_bytes
browserbot_active_sessions_total
```

### Performance Optimization

- **Connection Pooling**: Reuse browser contexts and connections
- **Resource Management**: Automatic cleanup of browser instances
- **Async Operations**: Non-blocking I/O for better throughput
- **Memory Management**: Configurable limits and garbage collection
- **Caching**: Intelligent caching of AI responses and page data

## 🔧 Troubleshooting

### Common Issues

**Browser Won't Start**
```bash
# Check Docker resources
docker system df
docker system prune  # Free up space if needed

# Verify VNC connection
./run.sh status
```

**Memory Issues**
```bash
# Monitor resource usage
docker stats browserbot
# Increase Docker memory limit in Docker Desktop
```

**VNC Connection Problems**
```bash
# Check VNC server status
docker exec browserbot ps aux | grep vnc
# Test connection
telnet localhost 5900
```

**AI Model Errors**
```bash
# Verify API key
echo $OPENROUTER_API_KEY
# Test API connection
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" https://openrouter.ai/api/v1/models
```

### Debug Mode

Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
./run.sh
```

### Performance Tuning

```bash
# For high-load scenarios
export BROWSER_POOL_SIZE=5
export MAX_CONCURRENT_TASKS=10
export PLAYWRIGHT_BROWSERS_PATH=/tmp/playwright
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Playwright](https://playwright.dev/) for browser automation
- Powered by [LangChain](https://langchain.com/) for AI orchestration
- Uses [DeepSeek-R1](https://openrouter.ai/) for intelligent decision making
- Inspired by production browser automation systems like Suna
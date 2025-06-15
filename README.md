# BrowserBot

A robust, production-ready browser automation agent powered by AI, built with modern Python technologies and best practices.

## Features

- **AI-Powered Decision Making**: Integration with DeepSeek-R1 via OpenRouter for intelligent browser automation
- **Stealth Browser Automation**: Playwright-based automation with anti-detection capabilities
- **Docker Containerization**: Full GUI support with VNC access for headed browser operations
- **Comprehensive Error Handling**: Circuit breaker patterns, exponential backoff, and intelligent retry mechanisms
- **Memory Persistence**: Long-term memory capabilities for cross-session learning
- **Production-Ready Architecture**: Structured logging, monitoring, and observability
- **Extensive Testing**: Unit, integration, and end-to-end testing with pytest and Playwright Test

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
./run.sh
```

Then use natural language commands:
```
BrowserBot> Go to google.com and search for python automation
BrowserBot> task: Navigate to news websites and summarize headlines  
BrowserBot> chat What can you help me automate?
BrowserBot> screenshot
BrowserBot> help
```

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

## Monitoring

The application includes:

- Structured JSON logging with configurable levels
- Prometheus metrics endpoint
- OpenTelemetry tracing support
- Health check endpoints
- Performance monitoring

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
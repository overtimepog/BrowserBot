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

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/BrowserBot.git
cd BrowserBot
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e ".[dev]"
```

4. Install Playwright browsers:
```bash
playwright install chromium
```

5. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

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

### Basic Example

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

### Docker Usage

Build and run with Docker:

```bash
docker-compose up --build
```

Access the browser via VNC:
```bash
vncviewer localhost:5900
# Password: browserbot
```

### Running Tests

Run all tests:
```bash
pytest
```

Run specific test categories:
```bash
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m e2e          # End-to-end tests only
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
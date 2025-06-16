# BrowserBot Project Structure

This document describes the organization and structure of the BrowserBot project.

## Directory Layout

```
BrowserBot/
├── config/                 # Configuration files
├── docker/                 # Docker-specific files
│   ├── interactive-entrypoint.sh
│   └── supervisord.conf
├── docs/                   # Documentation
│   ├── changelogs/        # Version history and changes
│   ├── research/          # Research documents
│   ├── DEPLOYMENT.md
│   ├── ERROR_HANDLING_BEST_PRACTICES.md
│   ├── IMPLEMENTATION_GUIDE.md
│   ├── PERFORMANCE_OPTIMIZATIONS.md
│   └── PROJECT_STRUCTURE.md (this file)
├── examples/              # Example usage scripts
│   ├── advanced_patterns.py
│   ├── basic_automation.py
│   └── error_handling_demo.py
├── scripts/               # Utility scripts
│   ├── debug/            # Debug and development scripts
│   ├── halo_progress.py  # Progress indicator utility
│   ├── start_redis.sh
│   └── test_*.sh         # Test runner scripts
├── src/                   # Source code
│   └── browserbot/       # Main package
│       ├── agents/       # AI agent implementations
│       ├── browser/      # Browser automation layer
│       ├── core/         # Core functionality
│       ├── memory/       # Memory persistence
│       ├── monitoring/   # Metrics and observability
│       ├── security/     # Security components
│       ├── utils/        # Utility functions
│       └── main.py       # Main entry point
├── tests/                 # Test suite
│   ├── e2e/              # End-to-end tests
│   ├── integration/      # Integration tests
│   └── unit/             # Unit tests
├── .gitignore            # Git ignore rules
├── CONTRIBUTING.md       # Contribution guidelines
├── DOCKER_FIRST_USAGE.md # Docker usage guide
├── Dockerfile            # Docker container definition
├── LICENSE               # MIT License
├── README.md             # Project overview
├── RULES.md              # Development rules
├── docker-compose.yml    # Docker Compose configuration
├── pyproject.toml        # Python project configuration
├── requirements-monitoring.txt  # Monitoring dependencies
├── run.bat              # Windows launcher
└── run.sh               # Unix launcher
```

## Key Components

### Source Code (`src/browserbot/`)

- **agents/**: Contains AI agent implementations using LangChain
  - `browser_agent.py`: Main browser automation agent
  - `mistral_tool_executor.py`: Mistral AI integration
  - `tools.py`: Browser automation tools
  - `enhanced_executor.py`: Advanced execution with vision fallback

- **browser/**: Browser automation layer
  - `browser_manager.py`: Manages browser instances
  - `page_controller.py`: High-level page interactions
  - `stealth.py`: Anti-detection techniques
  - `advanced_stealth.py`: 2024 anti-detection methods

- **core/**: Core functionality
  - `config.py`: Configuration management
  - `errors.py`: Custom error definitions
  - `logger.py`: Logging configuration
  - `retry.py`: Retry mechanisms
  - `cache.py`: Caching functionality
  - `feature_flags.py`: Feature flag system

- **monitoring/**: Observability
  - `metrics_server.py`: Prometheus metrics
  - `observability.py`: Tracing and monitoring

### Tests (`tests/`)

Organized by test type:
- **unit/**: Fast, isolated unit tests
- **integration/**: Tests that verify component interactions
- **e2e/**: Full end-to-end tests

### Scripts (`scripts/`)

- Production scripts for running and managing BrowserBot
- **debug/**: Development and debugging scripts

### Documentation (`docs/`)

- Technical documentation and guides
- **changelogs/**: Version history and implementation notes
- **research/**: Research documents and references

## Development Workflow

1. Source code lives in `src/browserbot/`
2. Tests mirror the source structure in `tests/`
3. Documentation in `docs/`
4. Examples demonstrate usage patterns
5. Scripts provide automation and utilities

## Docker-First Design

The project is designed to run primarily in Docker containers:
- `Dockerfile` defines the container
- `docker-compose.yml` orchestrates services
- `run.sh` provides easy Docker execution
- All dependencies are containerized
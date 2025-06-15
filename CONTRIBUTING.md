# Contributing to BrowserBot

Thank you for your interest in contributing to BrowserBot! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Coding Standards](#coding-standards)
- [Documentation](#documentation)

## Code of Conduct

This project adheres to a code of conduct that we expect all contributors to follow. Please be respectful and constructive in all interactions.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/BrowserBot.git
   cd BrowserBot
   ```
3. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git

### Local Development

1. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

3. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run tests to verify setup**:
   ```bash
   pytest tests/unit/
   ```

### Docker Development

```bash
# Build and start development environment
docker-compose -f docker-compose.dev.yml up -d

# Run tests in Docker
docker-compose exec app pytest

# View logs
docker-compose logs -f app
```

## Making Changes

### Branch Naming

Use descriptive branch names with prefixes:
- `feature/` - New features
- `bugfix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test improvements

### Commit Messages

Follow conventional commit format:
```
type(scope): brief description

Longer description if needed

- Bullet points for additional details
- Reference issues: Fixes #123
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting, no code change
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

### Code Changes

1. **Write clear, readable code**
2. **Add type hints** for all functions
3. **Include docstrings** for classes and functions
4. **Handle errors appropriately**
5. **Follow existing patterns** in the codebase

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/           # Unit tests
pytest tests/integration/    # Integration tests
pytest tests/e2e/           # End-to-end tests

# Run with coverage
pytest --cov=src/browserbot --cov-report=html

# Run specific test file
pytest tests/unit/test_browser_agent.py

# Run with debugging
pytest -xvs tests/unit/test_browser_agent.py::test_specific_function
```

### Writing Tests

1. **Write tests for new functionality**
2. **Include both positive and negative test cases**
3. **Use descriptive test names**
4. **Mock external dependencies**
5. **Aim for high test coverage** (>80%)

Example test structure:
```python
import pytest
from unittest.mock import Mock, patch
from browserbot.core.browser_agent import BrowserAgent

class TestBrowserAgent:
    """Test browser agent functionality."""
    
    @pytest.fixture
    def browser_agent(self):
        """Create browser agent for testing."""
        return BrowserAgent()
    
    @pytest.mark.asyncio
    async def test_execute_task_success(self, browser_agent):
        """Test successful task execution."""
        # Arrange
        task = "Navigate to example.com"
        
        # Act
        result = await browser_agent.execute_task(task)
        
        # Assert
        assert result is not None
        assert "success" in result
    
    @pytest.mark.asyncio
    async def test_execute_task_failure(self, browser_agent):
        """Test task execution failure handling."""
        # Test error conditions
        pass
```

### Test Categories

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete user workflows
- **Performance Tests**: Test system performance and scalability

## Submitting Changes

### Before Submitting

1. **Run the full test suite**:
   ```bash
   pytest
   ```

2. **Check code quality**:
   ```bash
   black src/ tests/          # Format code
   ruff check src/ tests/     # Lint code
   mypy src/                  # Type checking
   ```

3. **Update documentation** if needed

4. **Add/update tests** for your changes

### Pull Request Process

1. **Push your changes** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a pull request** on GitHub with:
   - Clear title and description
   - Link to related issues
   - Description of changes made
   - Testing performed

3. **Respond to feedback** from maintainers

4. **Update your PR** as needed

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

## Coding Standards

### Python Style

- Follow **PEP 8** style guide
- Use **Black** for code formatting
- Use **Ruff** for linting
- Use **MyPy** for type checking

### Code Organization

```python
"""Module docstring."""

import standard_library
import third_party_library

from browserbot import local_imports

# Constants
CONSTANT_VALUE = "value"

# Type definitions
TypeAlias = Union[str, int]

class MyClass:
    """Class docstring."""
    
    def __init__(self, param: str) -> None:
        """Initialize instance."""
        self.param = param
    
    async def async_method(self, arg: int) -> Dict[str, Any]:
        """Async method with type hints."""
        return {"result": arg}

def utility_function(param: str) -> bool:
    """Utility function with docstring."""
    return bool(param)
```

### Error Handling

```python
from browserbot.core.errors import BrowserBotError
from browserbot.core.logger import get_logger

logger = get_logger(__name__)

async def risky_operation() -> Dict[str, Any]:
    """Perform operation with proper error handling."""
    try:
        # Operation code
        result = await some_operation()
        return {"success": True, "data": result}
        
    except SpecificError as e:
        logger.error("Specific error occurred", error=str(e))
        raise BrowserBotError(f"Operation failed: {e}") from e
        
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
        raise
```

### Logging

```python
from browserbot.core.logger import get_logger

logger = get_logger(__name__)

# Use structured logging
logger.info("Operation started", operation="example", param=value)
logger.warning("Potential issue detected", issue="timeout", duration=30)
logger.error("Operation failed", error=str(e), context={"param": value})
```

## Documentation

### Code Documentation

- **Docstrings**: All public classes, methods, and functions
- **Type hints**: All function parameters and return values
- **Comments**: Complex logic and business rules

### External Documentation

- **README**: Keep updated with changes
- **API docs**: Update for API changes
- **Examples**: Provide usage examples
- **Deployment**: Update deployment guides

### Documentation Format

```python
async def process_data(
    data: List[Dict[str, Any]], 
    options: Optional[ProcessingOptions] = None
) -> ProcessingResult:
    """
    Process data according to specified options.
    
    Args:
        data: List of data items to process
        options: Processing configuration options
        
    Returns:
        ProcessingResult containing processed data and metadata
        
    Raises:
        ValidationError: When data format is invalid
        ProcessingError: When processing fails
        
    Example:
        >>> data = [{"name": "test", "value": 123}]
        >>> result = await process_data(data)
        >>> print(result.success)
        True
    """
    # Implementation
```

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create release PR
4. Merge to main
5. Create release tag
6. Build and publish Docker image
7. Deploy to production

## Getting Help

- **Issues**: Create GitHub issues for bugs and feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Discord**: Join our Discord server for real-time chat
- **Email**: Contact maintainers directly for security issues

## Recognition

Contributors are recognized in:
- `CONTRIBUTORS.md` file
- Release notes
- GitHub contributors page

Thank you for contributing to BrowserBot! 🎉
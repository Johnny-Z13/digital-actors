# Contributing to Digital Actors

Thank you for your interest in contributing to Digital Actors! This guide will help you get started with development.

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Johnny-Z13/digital-actors.git
cd digital-actors
```

### 2. Install Dependencies

Using `pip`:
```bash
pip install -e ".[dev]"
```

Or using `uv` (recommended):
```bash
uv pip install -e ".[dev]"
```

This installs the package in editable mode with all development dependencies including:
- `ruff` - Linting and formatting
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `pytest-asyncio` - Async test support
- `pre-commit` - Git hook framework

### 3. Set Up Pre-commit Hooks

Pre-commit hooks automatically run code quality checks before each commit to catch issues early.

**Install the hooks:**
```bash
pre-commit install
```

This is a one-time setup. After installation, hooks will run automatically on `git commit`.

## Pre-commit Hooks

### What Hooks Run?

When you commit, the following checks run automatically:

1. **Ruff Format** - Formats Python code for consistency
2. **Ruff Check** - Lints Python code and auto-fixes issues
3. **Trailing Whitespace** - Removes extra spaces at line ends
4. **End-of-File Fixer** - Ensures files end with a newline
5. **YAML Validation** - Checks YAML syntax
6. **Large File Prevention** - Blocks files >500KB from being committed
7. **Merge Conflict Detection** - Catches unresolved merge markers
8. **JSON Validation** - Checks JSON syntax
9. **Python AST Check** - Verifies Python files parse correctly
10. **Debug Statement Detection** - Catches leftover `breakpoint()` calls

### Running Hooks Manually

**Run on all files:**
```bash
pre-commit run --all-files
```

**Run on specific files:**
```bash
pre-commit run --files file1.py file2.py
```

**Run a specific hook:**
```bash
pre-commit run ruff-format --all-files
pre-commit run trailing-whitespace --all-files
```

### Bypassing Hooks (Emergency Use Only)

If you need to commit without running hooks (not recommended):
```bash
git commit --no-verify -m "Emergency commit"
```

**Only use `--no-verify` when:**
- You're committing non-code files that fail incorrectly
- You're making a quick fix in an emergency
- You understand the risks

**Never bypass hooks to commit:**
- Code that doesn't pass linting
- Code with debug statements
- Large binary files

### Updating Hooks

Pre-commit hooks are versioned. To update to the latest versions:

```bash
pre-commit autoupdate
```

This updates the hook versions in `.pre-commit-config.yaml`.

## Code Quality Standards

### Python Style

We use **Ruff** for both linting and formatting:

- **Line length:** 100 characters
- **Quote style:** Double quotes
- **Import order:** Standard library → Third-party → First-party
- **Target Python:** 3.12+

**Manual linting:**
```bash
ruff check .
ruff check --fix .  # Auto-fix issues
```

**Manual formatting:**
```bash
ruff format .
ruff format --check .  # Check without modifying
```

### Ruff Configuration

Configuration is in `pyproject.toml`:
- Selected rules: E, W, F, I, B, C4, UP, SIM, TCH, RUF
- Ignored rules: E501 (line length), B008 (function call in default), SIM108 (ternary)
- Known first-party modules: `llm_prompt_core`, `characters`, `scenes`

## Testing

### Running Tests

**Run all tests:**
```bash
pytest
```

**Run with coverage:**
```bash
pytest --cov=. --cov-report=html --cov-report=term
```

**Run specific test file:**
```bash
pytest tests/test_player_memory.py
```

**Run specific test:**
```bash
pytest tests/test_player_memory.py::TestPlayerMemory::test_init
```

### Writing Tests

- Place tests in `tests/` directory
- Name files `test_*.py`
- Name test functions `test_*`
- Use `pytest-asyncio` for async tests
- Aim for >80% code coverage

**Example test:**
```python
import pytest
from player_memory import PlayerMemory

@pytest.mark.asyncio
async def test_player_memory_init():
    """Test PlayerMemory initialization."""
    memory = PlayerMemory()
    await memory.initialize()
    assert memory.db_path.exists()
```

## Commit Guidelines

### Commit Message Format

```
<type>: <subject>

<body>

Co-Authored-By: Your Name <your.email@example.com>
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `style` - Code style changes (formatting, no logic change)
- `refactor` - Code refactoring
- `test` - Adding or updating tests
- `chore` - Maintenance tasks (dependencies, config)

**Example:**
```
feat: add pre-commit hooks for code quality

- Add .pre-commit-config.yaml with ruff and standard hooks
- Add pre-commit to dev dependencies
- Document setup in CONTRIBUTING.md

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### What to Commit

**Do commit:**
- Source code changes
- Test files
- Documentation updates
- Configuration files

**Don't commit:**
- `.env` files (use `.env.example` instead)
- Large binary files (>500KB)
- Generated files (`__pycache__`, `.coverage`, `htmlcov/`)
- API keys or secrets
- Database files (`data/player_memory.db`)

## Pull Request Process

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Write code following style guidelines
   - Add tests for new functionality
   - Update documentation as needed

3. **Run quality checks:**
   ```bash
   # Run pre-commit hooks
   pre-commit run --all-files

   # Run tests
   pytest --cov=.

   # Check coverage
   open htmlcov/index.html
   ```

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

5. **Push to GitHub:**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create Pull Request:**
   - Go to GitHub repository
   - Click "New Pull Request"
   - Fill in description with:
     - What changed
     - Why it changed
     - How to test it
   - Link related issues

### CI/CD Pipeline

Pull requests automatically trigger:

1. **Code Quality Checks** (`.github/workflows/ci.yml`):
   - Ruff linting
   - Ruff format checking
   - Pytest with coverage
   - Coverage upload to Codecov

2. **Docker Build** (`.github/workflows/docker.yml`):
   - Multi-platform image build
   - Push to GitHub Container Registry

All checks must pass before merging.

## Project Structure

```
digital-actors/
├── characters/          # Character definitions
├── scenes/              # Scene definitions and handlers
├── llm_prompt_core/     # Generic LLM framework
├── web/                 # Frontend (HTML, CSS, JS)
├── tests/               # Test suite
├── docs/                # Documentation
├── config/              # Configuration files
├── data/                # Runtime data (not in git)
├── pyproject.toml       # Python project config
├── .pre-commit-config.yaml  # Pre-commit hooks
└── README.md            # Main documentation
```

## Getting Help

- **Documentation:** See `docs/` directory for system design docs
- **Issues:** Check [GitHub Issues](https://github.com/Johnny-Z13/digital-actors/issues)
- **Discussions:** Start a [GitHub Discussion](https://github.com/Johnny-Z13/digital-actors/discussions)

## Code of Conduct

- Be respectful and professional
- Provide constructive feedback
- Focus on what's best for the project
- Help newcomers get started

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

**Questions?** Open an issue or start a discussion on GitHub!

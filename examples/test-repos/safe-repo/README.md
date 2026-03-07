# pytoolkit

A lightweight Python utility library for common string and file operations.

## Installation

```bash
pip install pytoolkit
```

## Usage

```python
from pytoolkit import greet, read_config

# Simple greeting
print(greet("World"))

# Read a YAML config file
config = read_config("settings.yml")
```

## Features

- String manipulation utilities
- Config file readers (YAML, JSON, TOML)
- Simple logging helpers
- Zero external dependencies for core module

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Lint
ruff check src/
```

## Contributing

1. Fork the repo
2. Create a feature branch
3. Write tests for your changes
4. Submit a PR

## License

MIT License. See [LICENSE](LICENSE) for details.

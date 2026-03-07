# quickhttp

A fast, lightweight HTTP utility library for Python applications.

## Overview

quickhttp simplifies common HTTP operations like making requests, handling retries, and parsing responses. Built for developers who want a thin wrapper around `urllib` without pulling in heavy dependencies.

## Installation

```bash
pip install quickhttp
```

## Quick Start

```python
from quickhttp import get, post

# Simple GET request
response = get("https://api.example.com/users")
print(response.json())

# POST with JSON body
result = post("https://api.example.com/users", json={"name": "Alice"})
```

## Features

- Automatic retry with exponential backoff
- Response caching for GET requests
- Connection pooling
- Timeout handling
- JSON/XML response parsing

## Configuration

Copy `config.example.yml` to `config.yml` and adjust settings as needed.

## License

Apache 2.0

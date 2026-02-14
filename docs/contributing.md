# Contributing

## Development Setup

```bash
git clone git@github.com:lijma/agent-skill-fcontext.git
cd agent-skill-fcontext/fcontext
pip install -e ".[dev]"
```

## Run Tests

```bash
cd fcontext
python -m pytest tests/ -v
```

All 213 tests should pass across 7 test files.

## Project Structure

```
fcontext/
├── fcontext/
│   ├── __init__.py         # Version
│   ├── cli.py              # CLI entry point (argparse)
│   ├── init.py             # Init, enable, instruction templates
│   ├── indexer.py           # Document indexing (markitdown)
│   └── workspace_map.py    # Workspace structure generation
├── tests/
│   ├── test_cli.py
│   ├── test_init.py
│   ├── test_indexer.py
│   └── ...
├── pyproject.toml
└── README.md
```

## Guidelines

- **Python 3.9+** — use `from __future__ import annotations` in all modules
- **Single dependency** — only `markitdown` for document conversion
- **Tests** — add tests for new features, maintain coverage
- **Agent templates** — when adding commands, update instruction templates in `init.py` for all agent types

## Pull Requests

1. Fork the repository
2. Create a feature branch
3. Write tests
4. Ensure all tests pass
5. Submit a PR with a clear description

## License

Apache License 2.0 — see [LICENSE](https://github.com/lijma/agent-skill-fcontext/blob/main/LICENSE) for details.

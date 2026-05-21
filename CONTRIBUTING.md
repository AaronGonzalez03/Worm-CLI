# Contributing to Worm-CLI

Thank you for considering a contribution to Worm-CLI. This document outlines the process for reporting issues, suggesting features, and submitting pull requests.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Report a Bug](#how-to-report-a-bug)
- [How to Suggest a Feature](#how-to-suggest-a-feature)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Commit Message Guidelines](#commit-message-guidelines)

---

## Code of Conduct

By participating in this project you agree to maintain a respectful and constructive environment. This is an educational project — all discussions should remain focused on learning and improvement.

---

## How to Report a Bug

1. Search [existing issues](https://github.com/AaronGonzalez03/Worm-CLI/issues) to avoid duplicates.
2. Open a new issue with the **Bug Report** template and include:
   - Python version (`python3 --version`)
   - Operating system and version
   - Steps to reproduce the problem
   - Expected vs. actual behavior
   - Any relevant terminal output or traceback

---

## How to Suggest a Feature

1. Search [existing issues](https://github.com/AaronGonzalez03/Worm-CLI/issues) for similar suggestions.
2. Open a new issue with the **Feature Request** template.
3. Describe the use case clearly — explain *why* the feature is valuable from an educational perspective.

---

## Development Setup

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/Worm-CLI.git
cd Worm-CLI

# 3. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 4. Install dependencies
pip install prompt_toolkit rich

# 5. Verify everything works
python3 main.py 42
```

---

## Pull Request Process

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes. Keep commits focused and atomic — one logical change per commit.

3. Verify the simulator runs without errors:
   ```bash
   python3 -c "from filesystem import FileSystem; from worm import WormEngine; print('OK')"
   python3 main.py 42
   ```

4. Push your branch and open a Pull Request against `main`.

5. In the PR description:
   - Explain **what** changed and **why**
   - Reference any related issues with `Closes #123`
   - Include a short demo of the new behavior if applicable

6. PRs require at least one approving review before merging.

---

## Coding Standards

- Follow [PEP 8](https://peps.python.org/pep-0008/) for style.
- Use **type hints** for all function signatures (Python 3.10+ union syntax: `X | Y`).
- Keep functions focused — a function should do one thing.
- Avoid comments that describe *what* the code does; use them only when the *why* is non-obvious.
- Do not add error handling for scenarios that cannot happen in normal operation — trust the invariants.

### Module responsibilities (do not mix)

| Module | Owns | Must NOT |
|---|---|---|
| `filesystem.py` | Data model, tree generation, CRUD | Display output, prompt users |
| `worm.py` | Worm state, command logic, narration strings | Import `rich` or `prompt_toolkit` |
| `main.py` | Shell, rendering, REPL | Contain business logic |

---

## Commit Message Guidelines

Use the following prefixes:

| Prefix | When to use |
|---|---|
| `feat:` | New feature or behavior |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `refactor:` | Code change that neither fixes a bug nor adds a feature |
| `style:` | Formatting, whitespace (no logic change) |
| `test:` | Adding or updating tests |
| `chore:` | Maintenance, dependency updates |

Example:
```
feat: add network simulation module with fake TCP handshake
```

---

Thank you for helping make Worm-CLI a better educational resource.

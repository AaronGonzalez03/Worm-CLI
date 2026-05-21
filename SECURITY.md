# Security Policy

## Scope

Worm-CLI is an **educational simulator** that operates entirely on an in-memory fake filesystem. It performs no real I/O, establishes no network connections, and cannot affect any real system, file, or process.

Security reports are still welcomed to ensure the simulator itself does not inadvertently introduce vulnerabilities in the environments where it runs.

---

## Supported Versions

| Version | Supported |
|---|:---:|
| Latest (`main` branch) | Yes |
| Older tags | No — please update to the latest version |

---

## What Qualifies as a Security Issue

Given the nature of this project, the following scenarios are considered valid security reports:

- **Code execution vulnerabilities**: An input sequence that causes arbitrary code execution on the host system (not within the simulated filesystem).
- **Path traversal outside the simulation**: Any command that reads, writes, or deletes files on the real filesystem.
- **Dependency vulnerabilities**: A known CVE in `prompt_toolkit` or `rich` that affects users of this project in a material way.
- **Unintended network activity**: Any behavior that causes the simulator to initiate real network connections.

The following are **out of scope**:

- Behavior that only affects the in-memory fake filesystem (that is the intended functionality).
- Social engineering or misuse of the tool by end users (covered by the [disclaimer](README.md#-disclaimer)).
- Theoretical attacks with no realistic exploitation path.

---

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report security issues by emailing:

**aaronglezcstillo@gmail.com**

Include in your report:

1. A clear description of the vulnerability
2. Steps to reproduce it
3. The potential impact
4. Your suggested fix (optional but appreciated)

You will receive an acknowledgment within **72 hours**. If the issue is confirmed, a patch will be prioritized and released as soon as possible. You will be credited in the release notes unless you prefer to remain anonymous.

---

## Responsible Disclosure

This project follows a coordinated disclosure model. Please allow reasonable time for a fix to be developed and released before making any public disclosure.

---

## Educational Disclaimer

This project is designed for educational purposes only. The author does not endorse or support any malicious use of the concepts demonstrated. See the full disclaimer in [README.md](README.md#-disclaimer).

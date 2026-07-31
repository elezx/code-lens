# Code-Lens — Code Quality Harness for Claude Code

Full sensor layer (Guides + Sensors) for Claude Code: multi-formatter, multi-linter, type checker, bash file detection, safety gates, and test-gating — all via native hooks. Cross-platform single-file Node.js implementation with zero npm dependencies.

## What it does

After every `Write`/`Edit`/`Bash` tool call, Code-Lens automatically runs:

| Sensor | What it checks | Hook |
|--------|---------------|------|
| **format** | Prettier, Biome, Black, Ruff, gofmt, rustfmt, shfmt, sql-formatter | PostToolUse |
| **lint** | ESLint, Biome, Oxlint, Ruff, golangci-lint, Clippy, ShellCheck, markdownlint, yamllint, hadolint, sql-lint | PostToolUse |
| **typecheck** | `tsc --noEmit` for TypeScript files | PostToolUse |
| **bash-detect** | Detects files modified by `sed`, `cat`, `tee`, `mv`, `cp`, `perl`, `awk` | PostToolUse |
| **block-dangerous** | Blocks `rm -rf /`, `DROP TABLE`, force-push main, fork bombs, `.env` edits | PreToolUse |
| **verify-tests** | Prevents agent from stopping while tests are red | Stop |

## Install

```bash
# From local directory
claude plugin install ./code-lens

# Or load for testing
claude --plugin-dir ./code-lens
```

## Architecture

```
code-lens/
├── .claude-plugin/
│   └── plugin.json              # Manifest
├── .github/workflows/
│   └── validate.yml             # CI: manifest + hook validation
├── hooks/
│   ├── hooks.json               # Hook configuration (exec form)
│   └── code-lens.mjs            # Single entry point (782 lines, zero deps)
├── claude-plugin.json           # Marketplace submission manifest
├── code-lens.config.json        # Tool preferences, safety rules, timeouts
├── LICENSE                      # MIT
└── README.md
```

## Configuration

`code-lens.config.json` defines tool preferences with priority order. The first available tool wins:

```json
{
  "formatters": {
    "javascript": ["biome", "prettier"],
    "typescript": ["biome", "prettier"],
    "python": ["ruff", "black"],
    "go": ["gofmt"],
    "rust": ["rustfmt"],
    "shell": ["shfmt"]
  },
  "linters": {
    "javascript": ["oxlint", "biome", "eslint"],
    "typescript": ["oxlint", "biome", "eslint"],
    "python": ["ruff"],
    "go": ["golangci-lint"],
    "rust": ["clippy"],
    "shell": ["shellcheck"]
  }
}
```

Override by creating `code-lens.config.json` in your project root — it merges with defaults.

## SessionStart detection

On every session start, Code-Lens scans your project and reports:

```
code-lens v2.0.0 — sensors active
  ✓ prettier (3.3.0)
  ✓ eslint (9.0.0)
  ✓ tsc (5.5.0)
  ✗ biome — install: npm install --save-dev @biomejs/biome
  ✗ oxlint — install: npm install --save-dev oxlint
  ✗ ruff — install: pip install ruff
  project: my-project · platform: darwin
```

## Requirements

- **Node.js** (already available in Claude Code)
- **jq** is NOT required (unlike the bash version)
- Individual tools (prettier, eslint, etc.) are auto-detected — missing tools are silently skipped

## Cross-platform

Works on **macOS**, **Linux**, and **Windows**. Uses `os.platform()` for platform-specific logic, handles Windows `.cmd`/`.bat` shims, and resolves tools through `node_modules/.bin` (12 levels up) before falling back to `PATH`.

## Inspired by

- [pi-lens](https://github.com/harms-haus/pi-lens) — the original Pi coding agent plugin
- [Harness engineering for coding agent users](https://martinfowler.com/articles/harness-engineering.html) — Birgitta Böckeler, Martin Fowler
- [Maintainability sensors for coding agents](https://martinfowler.com/articles/sensors-for-coding-agents.html) — Birgitta Böckeler

## License

MIT

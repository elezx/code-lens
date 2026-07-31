# Code-Lens — Code Quality Harness for Claude Code

Full sensor layer (Guides + Sensors) for Claude Code: multi-formatter, multi-linter, type checker, bash file detection, safety gates, and test-gating — all via native hooks. Cross-platform single-file Node.js implementation with zero npm dependencies.

## What it does

After every `Write`/`Edit`/`Bash` tool call, Code-Lens automatically runs:

| Sensor | What it checks | Hook |
|--------|---------------|------|
| **format** | Prettier, Biome, Black, Ruff, gofmt, rustfmt, CSharpier, dotnet-format, shfmt, sql-formatter | PostToolUse |
| **lint** | ESLint, Biome, Oxlint, Ruff, golangci-lint, Clippy, dotnet-format, ShellCheck, markdownlint, yamllint, hadolint, sql-lint | PostToolUse |
| **typecheck** | `tsc --noEmit` for TypeScript files | PostToolUse |
| **ast-grep** | 22 structural rules across TS/JS, Python, Go, Rust, C# | PostToolUse |
| **complexity** | Cyclomatic complexity, function length, and parameter count via lizard (27 languages) | PostToolUse |
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
├── ast-grep/
│   ├── sgconfig.yml             # ruleDirs (relative to this file)
│   └── rules/
│       ├── typescript/          # 5 rules (TypeScript + Tsx + JavaScript)
│       ├── python/              # 5 rules
│       ├── go/                  # 3 rules
│       ├── rust/                # 3 rules
│       ├── csharp/              # 3 rules
│       └── shared/              # 3 cross-language rules
├── hooks/
│   ├── hooks.json               # Hook configuration (exec form)
│   ├── code-lens.mjs            # Single entry point, zero deps
│   └── lizard-json.py           # lizard Python API → JSON metrics
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
    "csharp": ["csharpier", "dotnet-format"],
    "shell": ["shfmt"]
  },
  "linters": {
    "javascript": ["oxlint", "biome", "eslint"],
    "typescript": ["oxlint", "biome", "eslint"],
    "python": ["ruff"],
    "go": ["golangci-lint"],
    "rust": ["clippy"],
    "csharp": ["dotnet-format"],
    "shell": ["shellcheck"]
  }
}
```

Override by creating `code-lens.config.json` in your project root — it merges with defaults.

## ast-grep rules

Formatters and linters catch style and type problems. The `ast-grep` sensor catches
*structural* ones — patterns that are syntactically fine but wrong in practice. Every
rule matches against the AST, not text, so comments and string literals do not produce
false hits.

Rules live in `ast-grep/rules/<language>/` and are wired together by `ast-grep/sgconfig.yml`.

| Language | Rule | Severity | What it flags |
|----------|------|----------|---------------|
| TypeScript / JS | `no-console-log` | warning | `console.log(...)` left in source |
| | `no-any-type` | warning | `any` annotations |
| | `prefer-const` | hint | `let` that is never reassigned |
| | `no-await-in-loop` | warning | `await` inside `for`/`while`/`do` (not `for await`) |
| | `no-eval` | error | `eval(...)`, `new Function(...)` |
| Python | `no-bare-except` | error | `except:` with no exception type |
| | `no-mutable-defaults` | error | `def f(x=[])`, `{}`, `set()`, comprehensions |
| | `no-eval-py` | error | `eval(...)`, `exec(...)` |
| | `use-generators` | hint | `sum([...])` and friends — drop the brackets |
| | `no-assert-on-tuple` | error | `assert (x, y)` — always truthy |
| Go | `no-bare-return` | warning | naked `return` in a function with named results |
| | `defer-in-loop` | warning | `defer` inside a `for` |
| | `no-unused-params` | hint | parameter never referenced in the body |
| Rust | `no-unwrap` | warning | `.unwrap()` |
| | `no-expect-message` | warning | `.expect("")` with an empty message |
| | `unsafe-without-block` | error | `unsafe fn` with no `unsafe { }` inside |
| C# | `no-empty-catch` | warning | `catch { }` |
| | `no-throw-exception` | warning | `throw new Exception(...)` |
| | `async-void` | error | `async void` methods |
| Shared | `no-todo-fixme` | hint | `TODO` / `FIXME` / `HACK` / `XXX` comments |
| | `max-function-lines` | warning | functions longer than 50 lines |
| | `max-params` | warning | more than 5 parameters |

Each rule file holds one rule per language it covers, separated by `---`, so the
TypeScript rules also apply to `.tsx` and `.js` and the shared rules apply to all six
languages. Rule ids carry a language suffix (`max-params-go`, `no-todo-fixme-rs`) because
ast-grep requires ids to be unique across the whole project.

Install the binary with:

```bash
npm install -g @ast-grep/cli
```

Run the rule set manually over a whole tree:

```bash
ast-grep scan -c /path/to/code-lens/ast-grep/sgconfig.yml .
```

### Known approximations

Three rules cannot be expressed exactly in ast-grep and deliberately under-report
rather than produce false positives:

- **`prefer-const`** skips any binding that is reassigned anywhere in an enclosing
  scope, including outer scopes, and only matches untyped `let x = ...` declarations.
- **`no-unused-params`** (Go) checks whether the parameter name appears anywhere in
  the body; grouped parameters (`func f(a, b int)`) are only checked on their first name,
  and `_` is exempt.
- **`max-function-lines`** counts newlines with a regex over the node text, and matches
  nested closures on their own — a long function containing a long closure reports twice.

### Adding your own rules

Drop a `.yml` file into any `ast-grep/rules/<language>/` directory, or add a directory
to `ruleDirs` in `sgconfig.yml`. Test it before wiring it in:

```bash
ast-grep scan -r my-rule.yml path/to/fixture.ts --report-style short
```

Disable the sensor entirely with `"analyzers": { "ast-grep": false }`.

## Complexity / SRP analysis

The `complexity` sensor runs [lizard](https://github.com/terryyin/lizard) over the edited
file and reports any function that crosses a threshold:

```
--- complexity: src/checkout.ts ---
  applyDiscounts (L142): cyclomatic 22 > 15
  buildOrder (L61): nloc 84 > 50, params 7 > 5
  A function over these thresholds is usually doing more than one job — split it.
```

Thresholds are configurable:

```json
{
  "analyzers": {
    "ast-grep": true,
    "lizard": true
  },
  "complexity": {
    "cyclomatic": 15,
    "nloc": 50,
    "params": 5
  }
}
```

Install it with:

```bash
pip install lizard
```

lizard covers 27 languages (C/C++, C#, Java, JavaScript, TypeScript, Python, Go, Rust,
Swift, Kotlin, Scala, Ruby, PHP, Zig, …) and ships a Python API. The sensor calls that
API through `hooks/lizard-json.py`, which prints one JSON array of
`{ name, line, cyclomatic, nloc, params }` records — a fixed shape, so no schema guessing
is needed. When lizard is not installed, or its output is not JSON, the sensor stays
silent — like every other sensor, it exits 0 and never blocks the agent.

## SessionStart detection

On every session start, Code-Lens scans your project and reports:

```
code-lens v2.0.0 — sensors active
  ✓ ast-grep (0.42.2)
  ✓ prettier (3.3.0)
  ✓ eslint (9.0.0)
  ✓ tsc (5.5.0)
  ✗ biome — install: npm install --save-dev @biomejs/biome
  ✗ lizard — install: pip install lizard
  ✗ oxlint — install: npm install --save-dev oxlint
  ✗ ruff — install: pip install ruff
  project: my-project · platform: darwin
```

Analyzers are listed when any language they cover is detected in the project.

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

# dev-skill

A [Claude Code skill](https://docs.anthropic.com/en/docs/claude-code/skills) for the full development lifecycle — design, build, assess, and analyze — through coordinated subagents.

## Modes

| Mode | Trigger | What it does |
|------|---------|--------------|
| **Design** | "I have an idea", "architect", "spec" | Clarify intent, research, document |
| **Build** | "build", "add feature", "fix bug" | Test-first subagent builds with verification |
| **Assess** | "assess", "audit", "refactor" | Static analysis, findings ranked by impact/effort |
| **Analyze** | "analyze", "root cause", "why does X fail" | Root cause taxonomy, causal models, experiment design |

## Install

Copy this repo into your Claude Code skills directory:

```
~/.claude/skills/dev/
```

Or add it as a git submodule in your project's `.claude/skills/` folder.

## Structure

```
├── SKILL.md                          # Skill instructions
├── references/
│   ├── design-workflow.md            # Design mode workflow
│   ├── build-directives.md           # Subagent invocation patterns
│   └── assessment-workflow.md        # Assess + Analyze workflows
└── scripts/
    ├── analyze.py                    # Static analysis (--mode summary for context-friendly output)
    ├── run-command.sh                # Universal command wrapper (log to file, JSON summary to stdout)
    └── run-tests.sh                  # Multi-runner test wrapper (pytest/jest/go/cargo)
```

## License

MIT

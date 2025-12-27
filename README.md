# Utility Explorer (ue)

A personal productivity CLI for planning and task management. I originally built this to help keep track of things for my ADHD brain, but it's a general-purpose tool that's highly customizable and extensible. The main difference between this tool and other producitivity tools is it tracks flex blocks that aren't necessarily completed daily to track progress against a weekly goal. This helps keep me from getting distracted by deep focus on one task that interests me at the expense of everything else. 

It aggregates info from Gmail, Google Calendar, and git into a unified dashboard with time-block tracking for recurring activities.

## Demo

[![asciicast](https://asciinema.org/a/hfLqMm2NE0cGyEeyu6yytwMka.svg)](https://asciinema.org/a/hfLqMm2NE0cGyEeyu6yytwMka)

## Features

- **Task management** with natural language due dates
- **Block tracking** for recurring habits/activities with weekly targets
- **Morning/evening routines** (`ue am` / `ue pm`) for structured check-ins
- **Gmail & Calendar sync** to see what needs attention
- **Git commit tracking** across multiple repos
- **AI-powered focus recommendations** (optional, requires Anthropic API key)

## Dependencies

- Python 3.10+
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal formatting
- [Google API Client](https://github.com/googleapis/google-api-python-client) - Gmail/Calendar integration
- [GitHub CLI](https://cli.github.com/) - Git commit tracking (must be authenticated via `gh auth login`)
- [Anthropic](https://docs.anthropic.com/en/docs/client-sdks) - AI focus recommendations (optional)

## Installation

```bash
git clone https://github.com/yourusername/utility-explorer.git
cd utility-explorer
pip install -e .
```

## Setup

Run `ue setup` for detailed instructions on configuring Google API credentials.

**Quick version:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable Gmail API + Google Calendar API
3. Create OAuth credentials (Desktop application)
4. Save the JSON as `~/.utility-explorer/credentials.json`
5. Run `ue sync` to authenticate

**For AI focus recommendations:**
Set `ANTHROPIC_API_KEY` in your environment.

## Quick Start

```bash
ue sync          # Pull data from Gmail, Calendar, git
ue status        # Week-to-date summary
ue am            # Morning standup
ue pm            # Evening review
```

## Commands

### Daily Workflow

| Command | Description |
|---------|-------------|
| `ue am` | Morning standup - overdue tasks, at-risk blocks, today's calendar |
| `ue pm` | Evening review - interactive block check-in, log wins |
| `ue status` | Week-to-date progress on blocks and tasks |
| `ue dashboard` | Main dashboard (alias: `ue d`) |
| `ue focus` | AI recommendation for what to focus on now |

### Quick Actions (Interactive)

```bash
ue did           # Pick a block you just completed
ue done          # Pick a task to mark done
ue task add      # Add a task (interactive prompts)
```

### Task Management

```bash
ue task add "title" -d tomorrow -p high -w ai-research
ue task list              # List pending tasks
ue task done 5            # Mark task #5 complete
ue task cancel 5          # Cancel task #5
```

**Due dates** support natural language:
- `today`, `tomorrow`
- Day names: `monday`, `wed`, `friday`
- Next week: `next monday`, `next wed`
- ISO format: `2025-01-15`

**Priority:** `low`, `normal`, `high`

### Block Tracking

Blocks are recurring activities you want to hit weekly (like workouts) or daily (like dog walks).

```bash
ue block target "Workout" 3        # 3x per week target
ue block target "Dog Walk" 0       # Daily (0 = every day)
ue block done "Workout"            # Mark completed today
ue block skip "Workout" -r "sick"  # Mark skipped with reason
ue block partial "Workout"         # Partially completed
ue block list                      # Show weekly progress
```

### Inbox & Calendar

```bash
ue inbox              # Show email inbox
ue calendar           # Show upcoming events
ue sync               # Refresh data from Gmail/Calendar/git
```

### Activity Logging

```bash
ue log win "Shipped feature X"              # Log accomplishment
ue log application "Company" -r "Engineer"  # Log job application
ue activity                                 # View activity log
```

### Workstream Management

```bash
ue workstream add work -p high       # Add workstream with priority
ue workstream add health -p low      # Priority: high, mid, low
ue workstream list                   # List all workstreams
ue workstream set work -p mid        # Change priority
ue workstream remove old-project     # Remove a workstream
```

### Repository Tracking

```bash
ue add-repo ~/projects/myrepo    # Track git commits from repo
```

## Concepts

**Tasks** - One-off items with optional deadlines and priorities. Good for things like "email back John" or "submit application."

**Blocks** - Recurring activities with weekly targets. The system warns you when blocks are at risk of not being hit. Good for habits like exercise, meditation, or focused work time.

**Workstreams** - User-defined categories to organize tasks and blocks. Create with `ue workstream add`. Each has a priority (high/mid/low) that affects focus recommendations.

## Data Storage

All data lives in `~/.utility-explorer/`:
- `ue.db` - SQLite database
- `credentials.json` - Google OAuth client credentials
- `token.json` - Google OAuth tokens
- `config.json` - User configuration (workstreams, tracked repos)

## Customization

The codebase is designed to be extended. Key directories and files:

```
ue/
├── cli.py              # Main CLI entry point + setup command
├── commands/           # CLI command modules
│   ├── task.py         # Task management (add, list, done, cancel)
│   ├── block.py        # Block tracking (done, skip, partial, target)
│   ├── routines.py     # Daily routines (am, pm, status, focus)
│   ├── sync.py         # Sync + display (sync, dashboard, inbox, calendar)
│   ├── log.py          # Activity logging (log, mark)
│   ├── workstream.py   # Workstream management (add, list, remove, set)
│   └── demo.py         # Demo mode setup/reset
├── utils/              # Shared utilities
│   ├── display.py      # Rich console + logo
│   ├── dates.py        # Date parsing + effective date logic
│   └── analysis.py     # Block risk calculations
├── db.py               # Database schema and queries
├── focus.py            # AI focus logic (swap in your own model)
└── inbox/              # Data ingestion from external sources
```

## Contributing 🤝

Contributions welcome! The codebase is modular:

- **New commands** → `ue/commands/` (see existing modules for patterns)
- **Utility functions** → `ue/utils/` (shared helpers, display, date logic)
- **CLI registration** → Add your command to `ue/cli.py`

Open an issue first for large changes to discuss approach.


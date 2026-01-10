# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Utility Explorer (`ue`) is a personal productivity CLI designed to help with ADHD executive function support. It provides time-block tracking for recurring activities. It can optionally aggregate signals from Gmail, Google Calendar, and git commits - all integrations are optional for privacy-focused users who just want task/block tracking.

## Commands

Install in development mode:
```bash
pip install -e .
```

### Core Commands
```bash
ue --help          # Show all commands
ue setup           # Instructions for Google API and GitHub CLI setup
ue sync            # Sync Gmail, Calendar, and git data
ue status          # Week-to-date summary of blocks and tasks
ue dashboard       # Main dashboard (or ue d)
ue am              # Morning standup - shows overdue tasks, at-risk blocks, calendar, commits
ue pm              # Evening review - interactive block check-in and win logging
ue review          # Alias for pm
ue week            # Weekly review - completion rates, streaks, wins, trends
ue month           # Monthly review - 4-week trends, velocity, patterns
ue catchup         # Log blocks for days you missed
```

### Interactive Quick Actions
```bash
ue did             # Pick a block you just completed (numbered selection)
ue done            # Pick a task to mark done (numbered selection)
ue task add        # Interactive task creation (prompts for name, priority, workstream, due date)
```

### Task Management
```bash
ue task add "title" -d tomorrow -p high -w ai-research  # Add with options
ue task add        # Interactive mode (no args)
ue task list       # List pending tasks
ue task edit 5 -d friday -p high  # Edit task (title, due, priority, workstream, notes)
ue task edit 5 -d none    # Clear due date (use 'none')
ue task done 5     # Mark task #5 complete
ue task cancel 5   # Cancel task #5
```
Due dates support natural language: `today`, `tomorrow`, `tue`, `tues`, `wed`, `thurs`, `friday`, `next monday`, `next tues`, or `YYYY-MM-DD`.

### Block Tracking
```bash
ue block target "Workout" 5        # Set weekly target (5x/week)
ue block target "Dog Walk" 0       # Set as daily (0 = daily)
ue block done "Workout"            # Mark completed today
ue block skip "Workout" -r "sick"  # Mark skipped with reason
ue block partial "Workout"         # Mark partially completed
ue block list                      # Show weekly progress
```

### Activity Logging
```bash
ue log application "Company" -r "Engineer"  # Log job application
ue log win "Shipped feature X"              # Log a win/accomplishment
```

### Inbox Management
```bash
ue inbox              # Show email inbox
ue calendar           # Show upcoming calendar events
ue activity           # Show activity log
ue mark respond 3     # Mark item #3 as needing response
ue mark done 3        # Mark item #3 as responded
ue mark workstream 3 ai-research  # Assign workstream to item
```

### AI Focus (requires ANTHROPIC_API_KEY)
```bash
ue focus              # Get AI recommendation for what to focus on
ue focus --copy       # Print context for manual paste to claude.ai
```

### Workstream Management
```bash
ue workstream list                    # List all workstreams
ue workstream add work -p high        # Add with priority (high, mid, low)
ue workstream add health -p low -c cyan  # Add with priority and color
ue workstream set work -p mid         # Change priority
ue workstream remove old-project      # Remove a workstream
```

### Repository Tracking
```bash
ue add-repo ~/projects/myrepo  # Add git repo for commit tracking
```

### Demo Mode
```bash
UE_DEMO=1 ue demo-setup    # Create demo data in ~/.utility-explorer-demo/
UE_DEMO=1 ue demo-reset    # Wipe demo data
UE_DEMO=1 ue am            # Run any command with demo data
export UE_DEMO=1           # Set for entire shell session
```

## Architecture

### Data Flow
All data lives in `~/.utility-explorer/` (or `~/.utility-explorer-demo/` in demo mode):
- `ue.db` - SQLite database (inbox items, activity log, blocks, tasks)
- `credentials.json` - Google OAuth client credentials
- `token.json` - Google OAuth tokens
- `config.json` - User configuration (workstreams, tracked repos, last_sync timestamp)

### Module Structure

```
ue/
├── cli.py              # Main CLI group + setup command + imports
├── commands/
│   ├── task.py         # task group (add, list, edit, done, cancel) + done standalone
│   ├── block.py        # block group (done, skip, partial, target, list) + did standalone
│   ├── routines.py     # am, pm, status, focus, review
│   ├── review.py       # week, month - weekly/monthly review commands
│   ├── sync.py         # sync, dashboard, d, inbox, calendar, activity, add_repo
│   ├── log.py          # log group (application, win) + mark group (respond, done, workstream)
│   ├── workstream.py   # workstream group (add, list, remove, set)
│   └── demo.py         # demo-setup, demo-reset
└── utils/
    ├── display.py      # console, LOGO, print_logo()
    ├── dates.py        # parse_due_date(), get_effective_date()
    └── analysis.py     # get_at_risk_blocks()
```

**ue/cli.py** - Main Click group with `setup` command. Imports and registers all commands from `commands/` modules.

**ue/utils/display.py** - Rich console instance and logo display.

**ue/utils/dates.py** - Date utilities:
- `get_effective_date()` - Returns "effective" date with 2am day boundary (for night owls)
- `parse_due_date()` - Natural language date parsing including "next monday" etc.

**ue/utils/analysis.py** - Block analysis:
- `get_at_risk_blocks()` - Calculates block status (impossible, at_risk, try_to_do, daily_pending)
- `calculate_block_streak()` - Counts consecutive completion days for a block
- `calculate_completion_rate()` - Calculates percentage of target achieved
- `compare_weeks()` - Returns trend indicator (↑, ↓, →) comparing two values
- `get_week_bounds()` - Gets Monday/Sunday of a week relative to a date
- `get_consecutive_missed_days()` - Finds consecutive days with no block completions before today

**ue/commands/sync.py** - Sync and display commands:
- `run_sync()` - Core sync logic
- `auto_sync_if_stale()` - Auto-syncs if data is older than 1 hour

**ue/commands/routines.py** - Daily routine commands (am, pm, status, focus, review, catchup)

**ue/commands/review.py** - Weekly and monthly review commands:
- `week` - Shows block performance, streaks, task summary, wins, activity breakdown
- `month` - Shows 4-week block trends, task velocity, wins, workstream distribution

**ue/commands/task.py** - Task management commands

**ue/commands/block.py** - Block tracking commands

**ue/commands/log.py** - Manual logging (log, mark groups)

**ue/commands/workstream.py** - Workstream management (add, list, remove, set priority/color)

**ue/commands/demo.py** - Demo mode setup/reset

**ue/db.py** - SQLite database layer. Schema defines 5 tables:
- `inbox_items` - Emails and calendar events needing attention
- `activity_log` - Record of work done (emails sent, commits, wins)
- `block_completions` - Daily/weekly block tracking (completed/skipped/partial)
- `block_targets` - Weekly targets for recurring blocks (0 = daily)
- `tasks` - Time-sensitive tasks with deadlines and priorities

**ue/dashboard.py** - Rich-based dashboard views:
- `show_dashboard()` - Main dashboard with inbox, activity summary
- `show_inbox()` - Tabular inbox view
- `show_activity()` - Activity log view
- `show_calendar()` - Upcoming events view

**ue/focus.py** - AI-powered focus recommendations:
- Uses Anthropic API (claude-3-haiku) for recommendations
- `gather_context()` - Collects tasks, blocks, calendar for AI
- `get_focus()` - Returns single-action recommendation
- Requires `ANTHROPIC_API_KEY` environment variable

**ue/inbox/** - Data ingestion from external sources:
- `gmail.py` - Fetches inbox emails and logs sent emails as activity
- `calendar.py` - Syncs calendar events, `get_upcoming_events()` for today's calendar

**ue/activity/** - Activity logging:
- `git.py` - Fetches commits via GitHub API (requires `gh` CLI authenticated)
- `manual.py` - Manual logging (job applications, wins)

**ue/google_auth.py** - OAuth2 flow for Google APIs (Gmail, Calendar)

**ue/config.py** - Configuration management:
- `DEMO_MODE` - Checks `UE_DEMO` env var to use separate data directory
- `is_google_configured()` - Checks if Google credentials.json exists (for optional Google integration)
- `is_sync_stale()` - Checks if last sync was more than N minutes ago
- `get_last_sync()` / `set_last_sync()` - Track sync timestamps
- Defines paths and default workstreams

### Key Concepts

**Effective Date**: The day "turns over" at 2am, not midnight. Running `ue pm` at 12:41am still counts as the previous day. Controlled by `get_effective_date()`.

**Auto-Sync**: Commands `ue am`, `ue status`, and `ue dashboard` automatically sync if data is older than 1 hour.

**Workstreams**: User-defined categories for organizing tasks and blocks. Created via `ue workstream add`. Each workstream has a priority (high, mid, low) that affects suggested focus ordering. Stored in `config.json`.

**Block Status Tiers**:
- `impossible` - Can't hit weekly target (not enough days left)
- `at_risk` - Only 0-1 days of slack remaining
- `try_to_do` - High/mid priority blocks under halfway, or low priority with ≤2 days slack
- `daily_pending` - Daily block not done today

**Suggested Focus Priority**: Blocks are suggested based on workstream priority (high → mid → low → none), not just order in database.

**Tasks**: Time-sensitive items with:
- Priority: low, normal, high
- Due date: Optional, supports natural language parsing
- Status: pending, done, cancelled

**Inbox vs Activity**: Inbox items are things needing response; activity log tracks completed work.

**Interactive Flows**: Commands like `ue did`, `ue done`, and `ue task add` (without args) use `rich.prompt.Prompt.ask()` for numbered selection menus.

### Patterns

- CLI uses Click with command groups (`task`, `block`, `log`, `mark`)
- Commands organized into modules under `ue/commands/`
- Shared utilities in `ue/utils/` (display, dates, analysis)
- Rich library for tables, panels, colored output
- Lazy imports in CLI commands to keep `ue --help` fast
- SQLite with upsert patterns for idempotent syncing
- Natural language date parsing in `ue/utils/dates.py`
- Environment variable `UE_DEMO=1` for demo mode with separate data directory

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Utility Explorer (`ue`) is a personal productivity CLI designed to help with ADHD executive function support. It aggregates signals from multiple sources (Gmail, Google Calendar, git commits) into a unified dashboard and provides time-block tracking for recurring activities.

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
ue task done 5     # Mark task #5 complete
ue task cancel 5   # Cancel task #5
```
Due dates support natural language: `today`, `tomorrow`, `wed`, `friday`, `next monday`, `next wed`, or `YYYY-MM-DD`.

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

**ue/cli.py** - Click-based CLI with all command definitions. Key functions:
- `get_effective_date()` - Returns "effective" date with 2am day boundary (for night owls)
- `parse_due_date()` - Natural language date parsing including "next monday" etc.
- `get_at_risk_blocks()` - Calculates block status (impossible, at_risk, try_to_do, daily_pending)
- `auto_sync_if_stale()` - Auto-syncs if data is older than 1 hour
- `print_logo()` - Displays the utility-explorer ASCII logo

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
- `is_sync_stale()` - Checks if last sync was more than N minutes ago
- `get_last_sync()` / `set_last_sync()` - Track sync timestamps
- Defines paths and default workstreams

### Key Concepts

**Effective Date**: The day "turns over" at 2am, not midnight. Running `ue pm` at 12:41am still counts as the previous day. Controlled by `get_effective_date()`.

**Auto-Sync**: Commands `ue am`, `ue status`, and `ue dashboard` automatically sync if data is older than 1 hour.

**Workstreams**: Activities can be tagged with workstreams defined in config. Each workstream has a priority (high, mid, low) that affects suggested focus ordering.

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
- Rich library for tables, panels, colored output
- Lazy imports in CLI commands to keep `ue --help` fast
- SQLite with upsert patterns for idempotent syncing
- Natural language date parsing in `parse_due_date()`
- Environment variable `UE_DEMO=1` for demo mode with separate data directory

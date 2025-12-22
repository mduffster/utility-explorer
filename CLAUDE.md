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
ue setup           # Instructions for Google API setup
ue sync            # Sync Gmail, Calendar, and git data
ue dashboard       # Main dashboard (or ue d)
ue am              # Morning standup - shows overdue tasks, at-risk blocks, calendar
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
Due dates support natural language: `today`, `tomorrow`, `wed`, `friday`, or `YYYY-MM-DD`.

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

## Architecture

### Data Flow
All data lives in `~/.utility-explorer/`:
- `ue.db` - SQLite database (inbox items, activity log, blocks, tasks)
- `credentials.json` - Google OAuth client credentials
- `token.json` - Google OAuth tokens
- `config.json` - User configuration (workstreams, tracked repos)

### Module Structure

**ue/cli.py** - Click-based CLI with all command definitions. Commands use lazy imports to keep startup fast. Contains helper functions like `parse_due_date()` and `get_at_risk_blocks()`.

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
- `git.py` - Scans configured repos for commits (uses GitHub API, not local git)
- `manual.py` - Manual logging (job applications, wins)

**ue/google_auth.py** - OAuth2 flow for Google APIs (Gmail, Calendar)

**ue/config.py** - Configuration management, defines paths and default workstreams

### Key Concepts

**Workstreams**: Activities can be tagged with workstreams (ai-research, terrasol, blog, consulting) defined in config. Available via `load_config()["workstreams"]`.

**Block Tracking**: Recurring activities like "Workout" or "Dog Walk" are tracked against weekly targets. The `ue am` command warns about blocks at risk of not being hit. Status can be: completed, skipped, partial.

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

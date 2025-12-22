# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Utility Explorer (`ue`) is a personal productivity CLI designed to help with ADHD executive function support. It aggregates signals from multiple sources (Gmail, Google Calendar, git commits) into a unified dashboard and provides time-block tracking for recurring activities.

## Commands

Install in development mode:
```bash
pip install -e .
```

Run the CLI:
```bash
ue --help          # Show all commands
ue setup           # Instructions for Google API setup
ue sync            # Sync Gmail, Calendar, and git data
ue dashboard       # Main dashboard (or ue d)
ue am              # Morning standup
ue pm              # Evening review
```

## Architecture

### Data Flow
All data lives in `~/.utility-explorer/`:
- `ue.db` - SQLite database (inbox items, activity log, blocks, tasks)
- `credentials.json` - Google OAuth client credentials
- `token.json` - Google OAuth tokens
- `config.json` - User configuration (workstreams, tracked repos)

### Module Structure

**ue/cli.py** - Click-based CLI with all command definitions. Commands use lazy imports to keep startup fast.

**ue/db.py** - SQLite database layer. Schema defines 5 tables:
- `inbox_items` - Emails and calendar events needing attention
- `activity_log` - Record of work done (emails sent, commits, wins)
- `block_completions` - Daily/weekly block tracking (completed/skipped/partial)
- `block_targets` - Weekly targets for recurring blocks (0 = daily)
- `tasks` - Time-sensitive tasks with deadlines

**ue/inbox/** - Data ingestion from external sources:
- `gmail.py` - Fetches inbox emails and logs sent emails as activity
- `calendar.py` - Syncs calendar events

**ue/activity/** - Activity logging:
- `git.py` - Scans configured repos for commits
- `manual.py` - Manual logging (job applications, wins)

**ue/google_auth.py** - OAuth2 flow for Google APIs (Gmail, Calendar)

### Key Concepts

**Workstreams**: Activities can be tagged with workstreams (ai-research, terrasol, blog, consulting) defined in config.

**Block Tracking**: Recurring activities like "Workout" or "Dog Walk" are tracked against weekly targets. The `ue am` command warns about blocks at risk of not being hit.

**Inbox vs Activity**: Inbox items are things needing response; activity log tracks completed work.

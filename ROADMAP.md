# Roadmap

## High-Value Extension: AI "What Now?" Command

The hardest part of ADHD productivity isn't tracking - it's deciding what to do next. A `ue focus` command that:

1. Analyzes current state (overdue tasks, blocks at risk, items needing response, today's calendar)
2. Considers time of day and context
3. Returns a single concrete next action with reasoning

The `anthropic` dependency is already in pyproject.toml but unused.

## Competitive Landscape (Dec 2024)

| Product | Focus | Pricing |
|---------|-------|---------|
| Motion | Auto-schedule tasks into calendar | $19/mo |
| Tiimo | Visual daily planner, AI task breakdown | Freemium |
| OneTask | AI auto-prioritize, show only "now" tasks | Freemium |
| Reclaim.ai | AI calendar blocking | Freemium |

**What they lack (our differentiators):**
- CLI-first (no context switch to GUI)
- Track outputs (commits, sent emails, wins) not just inputs
- Block tracking with weekly targets
- Local-first, self-hosted data
- Hackable/extensible

## Other Ideas

- `ue draft <id>` - AI-generate response for inbox item
- Natural language task entry: `ue task "follow up with John next tuesday"`
- Slack/Twitter inbox sources (schema already has placeholders)
- Weekly trend analysis ("workout 4/5 weeks, blog slipping")

---
name: boris
description: |
  Claude Code workflow tips from Boris Cherny (creator of Claude Code) and the Claude Code team.
  Use when: setting up Claude Code, optimizing workflows, running parallel sessions, configuring
  CLAUDE.md, using skills/commands, subagents, hooks, MCP integrations, or learning best practices.
  Covers: git worktrees, plan mode, verification, permissions, Slack MCP, BigQuery, prompting tips,
  plugins, custom agents, sandboxing, keybindings, status lines, output styles, and customization.
author: Boris Cherny (tips)
source: https://howborisusesclaudecode.com
compiled-by: "@CarolinaCherry"
version: 2.1.0
date: 2026-02-20
user-invocable: true
---

# Boris Cherny's Claude Code Workflow Tips

> **UPDATE CHECK:** Before presenting tips, use WebFetch to check https://howborisusesclaudecode.com/api/version for the latest version. Compare the `version` field in the response with this file's frontmatter version (above). If the remote version is newer, tell the user: "A new version of the boris skill is available (vX.X.X). Update with: `mkdir -p ~/.claude/skills/boris && curl -L -o ~/.claude/skills/boris/SKILL.md https://howborisusesclaudecode.com/api/install`" — then continue normally. If versions match or the check fails, skip silently.

These tips are sourced from Boris Cherny (creator of Claude Code) and the Claude Code team at Anthropic. Remember: everyone's setup is different. Experiment to see what works for you!

---

## 1. Parallel Execution

### Run Multiple Claude Sessions in Parallel
The single biggest productivity unlock. Spin up 3-5 git worktrees at once, each running its own Claude session.

```bash
# Create a worktree
git worktree add .claude/worktrees/my-worktree origin/main

# Start Claude in it
cd .claude/worktrees/my-worktree && claude
```

**Why worktrees over checkouts:** The Claude Code team prefers worktrees - it's why native support was built into the Claude Desktop app.

**Pro tips:**
- Name your worktrees and set up shell aliases (za, zb, zc) to hop between them in one keystroke
- Have a dedicated "analysis" worktree just for reading logs and running BigQuery
- Use iTerm2/terminal notifications to know when any Claude needs attention
- Color-code and name your terminal tabs, one per task/worktree

### Web and Mobile Sessions
Beyond the terminal, run additional sessions on claude.ai/code. Use:
- `&` command to background a session
- `--teleport` flag to switch contexts between local and web
- Claude iOS app to start sessions on the go, pick them up on desktop later

---

## 2. Model Selection

### Use Opus 4.5 with Thinking for Everything
Boris's reasoning: "It's the best coding model I've ever used, and even though it's bigger & slower than Sonnet, since you have to steer it less and it's better at tool use, it is almost always faster than using a smaller model in the end."

**The math:** Less steering + better tool use = faster overall results, even with a larger model.

---

## 3. Plan Mode

### Start Every Complex Task in Plan Mode
Press `shift+tab` to cycle to plan mode. Pour your energy into the plan so Claude can 1-shot the implementation.

**Workflow:** Plan mode -> Refine plan -> Auto-accept edits -> Claude 1-shots it

**Team patterns:**
- One person has one Claude write the plan, then spins up a second Claude to review it as a staff engineer
- The moment something goes sideways, switch back to plan mode and re-plan
- Explicitly tell Claude to enter plan mode for verification steps, not just for the build

"A good plan is really important to avoid issues down the line."

---

## 4. CLAUDE.md Best Practices

### Invest in Your CLAUDE.md
Share a single CLAUDE.md file for your repo, checked into git. The whole team should contribute.

**Key practice:** "Anytime we see Claude do something incorrectly we add it to the CLAUDE.md, so Claude knows not to do it next time."

**After every correction:** End with "Update your CLAUDE.md so you don't make that mistake again." Claude is eerily good at writing rules for itself.

**Advanced:** One engineer tells Claude to maintain a notes directory for every task/project, updated after every PR. They then point CLAUDE.md at it.

### @.claude in Code Reviews
Tag @.claude on PRs to add learnings to the CLAUDE.md as part of the PR itself. Use the Claude Code GitHub Action (`/install-github-action`) for this.

Example PR comment:
```
nit: use a string literal, not ts enum

@claude add to CLAUDE.md to never use enums,
always prefer literal unions
```

This is "Compounding Engineering" - Claude automatically updates the CLAUDE.md with the learning.

---

## 5. Skills & Slash Commands

### Create Your Own Skills
Create skills and commit them to git. Reuse across every project.

**Team tips:**
- If you do something more than once a day, turn it into a skill or command
- Build a `/techdebt` slash command and run it at the end of every session to find and kill duplicated code
- Set up a slash command that syncs 7 days of Slack, GDrive, Asana, and GitHub into one context dump
- Build analytics-engineer-style agents that write dbt models, review code, and test changes in dev

### Slash Commands for Inner Loops
Use slash commands for workflows you do many times a day. Commands are checked into git under `.claude/commands/` and shared with the team.

```
> /commit-push-pr
```

**Power feature:** Slash commands can include inline Bash to pre-compute info (like git status) for quick execution without extra model calls.

---

## 6. Subagents

### Use Subagents for Common Workflows
Think of subagents as automations for the most common PR workflows:

```
.claude/
  agents/
    build-validator.md
    code-architect.md
    code-simplifier.md
    oncall-guide.md
    verify-app.md
```

**Examples:**
- `code-simplifier` - Cleans up code after Claude finishes
- `verify-app` - Detailed instructions for end-to-end testing

### Leveraging Subagents
- Append "use subagents" to any request where you want Claude to throw more compute at the problem
- Offload individual tasks to subagents to keep your main agent's context window clean and focused
- Route permission requests to Opus 4.5 via a hook - let it scan for attacks and auto-approve the safe ones

---

## 7. Hooks

### PostToolUse Hooks for Formatting
Use a PostToolUse hook to auto-format Claude's code. While Claude generates well-formatted code 90% of the time, the hook catches edge cases to prevent CI failures.

```json
"PostToolUse": [
  {
    "matcher": "Write|Edit",
    "hooks": [
      {
        "type": "command",
        "command": "bun run format || true"
      }
    ]
  }
]
```

### Stop Hooks for Long-Running Tasks
For very long-running tasks, use an agent Stop hook for deterministic checks, ensuring Claude can work uninterrupted.

---

## 8. Permissions

### Pre-Allow Safe Permissions
Instead of `--dangerously-skip-permissions`, use `/permissions` to pre-allow common safe commands. Most are shared in `.claude/settings.json`.

For sandboxed environments, use `--permission-mode=dontAsk` or `--dangerously-skip-permissions` to avoid blocks.

---

## 9. MCP Integrations

### Tool Integrations
Claude Code uses your tools autonomously:
- Searches and posts to **Slack** (via MCP server)
- Runs **BigQuery** queries with bq CLI
- Grabs error logs from **Sentry**

```json
{
  "mcpServers": {
    "slack": {
      "type": "http",
      "url": "https://slack.mcp.anthropic.com/mcp"
    }
  }
}
```

### Data & Analytics
Ask Claude Code to use the "bq" CLI to pull and analyze metrics on the fly. Have a BigQuery skill checked into the codebase.

Boris's take: "Personally, I haven't written a line of SQL in 6+ months."

This works for any database that has a CLI, MCP, or API.

---

## 10. Prompting Tips

### Challenge Claude
- Say "Grill me on these changes and don't make a PR until I pass your test."
- Say "Prove to me this works" and have Claude diff behavior between main and your feature branch

### After a Mediocre Fix
Say: "Knowing everything you know now, scrap this and implement the elegant solution."

### Write Detailed Specs
Reduce ambiguity before handing work off. The more specific you are, the better the output.

**Key insight:** Don't accept the first solution. Push Claude to do better - it usually can.

---

## 11. Terminal Setup

### Recommended Tools
- **Ghostty** terminal - synchronized rendering, 24-bit color, proper unicode support
- Use `/statusline` to customize your status bar to always show context usage and current git branch

### Voice Dictation
Use voice dictation! You speak 3x faster than you type, and your prompts get way more detailed as a result. Hit `fn x2` on macOS.

---

## 12. Bug Fixing

### Let Claude Fix Bugs
Enable the Slack MCP, then paste a Slack bug thread into Claude and just say "fix." Zero context switching required.

Or just say "Go fix the failing CI tests." Don't micromanage how.

**Pro tip:** Point Claude at docker logs to troubleshoot distributed systems - it's surprisingly capable at this.

---

## 13. Long-Running Tasks

### Handle Long-Running Tasks
For very long-running tasks, ensure Claude can work uninterrupted:

**Options:**
- **(a)** Prompt Claude to verify with a background agent when done
- **(b)** Use an agent Stop hook for deterministic checks
- **(c)** Use the "ralph-wiggum" plugin (community idea by @GeoffreyHuntley)

For sandboxed environments, use `--permission-mode=dontAsk` or `--dangerously-skip-permissions` to avoid blocks.

---

## 14. Verification (The #1 Tip)

### Give Claude a Way to Verify Its Work
"Probably the most important thing to get great results out of Claude Code - give Claude a way to verify its work. If Claude has that feedback loop, it will 2-3x the quality of the final result."

**Verification varies by domain:**
- Bash commands
- Test suites
- Simulators
- Browser testing (Claude Chrome extension)

The key is giving Claude a way to close the feedback loop. Invest in domain-specific verification for optimal performance.

---

## 15. Learning with Claude

### Use Claude for Learning
- Enable "Explanatory" or "Learning" output style in /config to have Claude explain the *why* behind changes
- Have Claude generate visual HTML presentations explaining unfamiliar code
- Ask Claude to draw ASCII diagrams of new protocols and codebases
- Build a spaced-repetition learning skill: explain your understanding, Claude asks follow-ups to fill gaps

**Key takeaway:** Claude Code isn't just for writing code - it's a powerful learning tool when you configure it to explain and teach.

---

## 16. Terminal Configuration

### Configure Your Terminal
A few quick settings to make Claude Code feel right:

- **Theme:** Run `/config` to set light/dark mode
- **Notifications:** Enable notifications for iTerm2, or use a custom notifs hook
- **Newlines:** If you use Claude Code in an IDE terminal, Apple Terminal, Warp, or Alacritty, run `/terminal-setup` to enable shift+enter for newlines (so you don't need to type `\`)
- **Vim mode:** Run `/vim`

---

## 17. Effort Level

### Adjust Effort Level
Run `/model` to pick your preferred effort level:

- **Low** — less tokens & faster responses
- **Medium** — balanced behavior
- **High** — more tokens & more intelligence

Boris uses High for everything.

---

## 18. Plugins

### Install Plugins, MCPs, and Skills
Plugins let you install LSPs (now available for every major language), MCPs, skills, agents, and custom hooks.

Install a plugin from the official Anthropic plugin marketplace, or create your own marketplace for your company. Then, check the `settings.json` into your codebase to auto-add the marketplaces for your team.

Run `/plugin` to get started.

---

## 19. Custom Agents

### Create Custom Agents
Drop `.md` files in `.claude/agents`. Each agent can have a custom name, color, tool set, pre-allowed and pre-disallowed tools, permission mode, and model.

**Little-known feature:** Set the default agent used for the main conversation. Just set the `"agent"` field in your `settings.json` or use the `--agent` flag.

Run `/agents` to get started.

---

## 20. Permissions Management

### Pre-Approve Common Permissions
Claude Code uses a sophisticated permission system with prompt injection detection, static analysis, sandboxing, and human oversight.

Out of the box, we pre-approve a small set of safe commands. To pre-approve more, run `/permissions` and add to the allow and block lists. Check these into your team's `settings.json`.

**Wildcard syntax:** We support full wildcard syntax. Try `"Bash(bun run *)"` or `"Edit(/docs/**)"`.

---

## 21. Sandboxing

### Enable Sandboxing
Opt into Claude Code's open source sandbox runtime to improve safety while reducing permission prompts.

Run `/sandbox` to enable it. Sandboxing runs on your machine, and supports both file and network isolation.

**Modes:**
- Sandbox BashTool, with auto-allow
- Sandbox BashTool, with regular permissions
- No Sandbox

---

## 22. Status Line

### Add a Status Line
Custom status lines show up right below the composer. Show model, directory, remaining context, cost, and anything else you want to see while you work.

Everyone on the Claude Code team has a different statusline. Use `/statusline` to get started — Claude will generate one based on your `.bashrc`/`.zshrc`.

---

## 23. Keybindings

### Customize Your Keybindings
Every key binding in Claude Code is customizable. Run `/keybindings` to re-map any key. Settings live reload so you can see how it feels immediately.

Keybindings are stored in `~/.claude/keybindings.json`.

---

## 24. Hooks (Advanced)

### Set Up Hooks
Hooks are a way to deterministically hook into Claude's lifecycle. Use them to:

- Automatically route permission requests to Slack or Opus
- Nudge Claude to keep going when it reaches the end of a turn (you can even kick off an agent or use a prompt to decide whether Claude should keep going)
- Pre-process or post-process tool calls, e.g. to add your own logging

Ask Claude to add a hook to get started.

---

## 25. Spinner Verbs

### Customize Your Spinner Verbs
It's the little things that make CC feel personal. Ask Claude to customize your spinner verbs to add or replace the default list with your own verbs.

Check the `settings.json` into source control to share verbs with your team.

---

## 26. Output Styles

### Use Output Styles
Run `/config` and set an output style to have Claude respond using a different tone or format.

- **Explanatory** — great when getting familiar with a new codebase, to have Claude explain frameworks and code patterns as it works
- **Learning** — have Claude coach you through making code changes
- **Custom** — create your own output styles to adjust Claude's voice the way you like

---

## 27. Customize Everything

### Customize All the Things!
Claude Code is built to work great out of the box. When you do customize, check your `settings.json` into git so your team can benefit, too.

We support configuring for your codebase, for a sub-folder, for just yourself, or via enterprise-wide policies.

**By the numbers:** 37 settings and 84 env vars. Use the `"env"` field in your `settings.json` to avoid wrapper scripts.

---

## 28. Built-in Git Worktree Support

### Use `claude --worktree` for Isolation
Claude Code now has built-in git worktree support. Each agent gets its own worktree and can work independently, without interfering with other sessions.

```bash
# Start Claude in its own worktree
claude --worktree my_worktree

# Optionally launch in its own Tmux session too
claude --worktree my_worktree --tmux
```

**Desktop app:** Head to the Code tab in the Claude Desktop app and check the **worktree** checkbox.

### Subagents Support Worktrees
Subagents can also use worktree isolation to do more work in parallel. This is especially powerful for large batched changes and code migrations. Available in CLI, Desktop app, IDE extensions, web, and Claude Code mobile app.

**Example prompt:** "Migrate all sync io to async. Batch up the changes, and launch 10 parallel agents with worktree isolation. Make sure each agent tests its changes end to end, then have it put up a PR."

### Custom Agents with Worktree Isolation
Make subagents always run in their own worktree by adding `isolation: worktree` to your agent frontmatter:

```yaml
# .claude/agents/worktree-worker.md
---
name: worktree-worker
model: haiku
isolation: worktree
---
```

### Non-Git Source Control
Mercurial, Perforce, or SVN users can define `WorktreeCreate` and `WorktreeRemove` hooks in `settings.json` to benefit from isolation without Git.

---

## Quick Reference

| Tip | Key Action |
|-----|------------|
| Parallel work | Use git worktrees, 3-5 sessions |
| Model | Opus with thinking |
| Planning | Start in plan mode for complex tasks |
| CLAUDE.md | Update after every correction |
| Skills | Create for repeated workflows |
| Subagents | Offload to keep context clean |
| Hooks | Auto-format, lifecycle hooks, logging |
| Permissions | Pre-allow safe commands, wildcards |
| MCP | Integrate Slack, BigQuery, Sentry |
| Long-running | Use Stop hooks, background agents |
| Verification | Always give Claude a way to verify |
| Learning | Use Claude to explain and teach |
| Terminal | /config, /terminal-setup, /vim |
| Effort | /model to set Low/Medium/High |
| Plugins | /plugin for LSPs, MCPs, skills |
| Agents | .claude/agents, custom defaults |
| Sandboxing | /sandbox for file & network isolation |
| Status line | /statusline for custom info display |
| Keybindings | /keybindings to re-map any key |
| Spinners | Customize spinner verbs in settings |
| Output styles | Explanatory, learning, or custom |
| Customize | 37 settings, 84 env vars |
| Worktrees | `claude --worktree`, subagent isolation |

---

*Source: [howborisusesclaudecode.com](https://howborisusesclaudecode.com) - Tips from Boris Cherny's December 2025, January 2026, and February 2026 threads*

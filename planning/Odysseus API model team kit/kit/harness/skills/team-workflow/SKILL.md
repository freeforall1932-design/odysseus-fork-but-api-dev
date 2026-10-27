---
name: team-workflow
description: Use at the start of any task in a project that has handoff, worklist, planning-report, decision or improvement-log files, and again when you finish. Tells you where the project's state lives, how to pick the next item, and how to update the files. Also guides the workspace helper when it splits work between other helpers.
---

# Team workflow

Projects keep their memory in markdown files. You do not remember earlier sessions, so these files are how you pick up where the last session stopped. Follow this every time.

## 1. Find the project's state files

Look in the project root and in `docs/` (any depth up to 3 folders). Names vary and capital letters do not matter. Common ones:

- Handoff: `HANDOFF*`, `SESSION_HANDOFF*`, `SESSION*HAND*`, `STATUS*`
- Worklist: `WORKLIST*`, `TODO*`, `BACKLOG*`, `ROADMAP*`
- Planning: `*PLANNING*REPORT*`, `PLAN*`
- Decisions: `DECISIONS*`, `OPEN_DECISIONS*`, `ADR*`
- Log: `IMPROVEMENT*LOG*`, `CHANGELOG*`, `LESSONS*`
- Instructions: `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `README.md`

If none exist, do not invent them. Offer to create them from the files in this skill's `templates/` folder (copy into `docs/`, open a pull request) and wait for a yes.

## 2. Before you start

1. Read the newest handoff completely.
2. Read the top of the worklist: the open items with the highest priority.
3. Read the open decisions and open questions.
4. Read the last 10 entries of the improvement log.
5. If a human message gave you a task, that task comes first. Use the files only for context.
6. In a chat, say in five lines or fewer what you found: the current state, the next item, and anything blocked.

If two files disagree, trust the one with the newest date and tell the human about the conflict. Do not silently pick.

## 3. Choosing work

- Take the highest-priority open item that is not blocked and not waiting for a human decision.
- One worklist item per pull request. Put the item's ID in the pull request title, for example `U-59/P0-7: ...`.
- Items marked human-only (real hardware, releases, tags, legal or licence calls, version numbers) are never yours. Prepare notes or scripts and mark the pull request "needs human run".

## 4. While you work

- Keep a short running note in the pull request description: what you changed, what you ran, what you saw.
- Run the builds and tests you can. Paste the real results. Say plainly what you could not run.
- Never edit a "decisions" or "owner" section to mark something decided. Put the question in the pull request description and add it to the handoff's open questions.

## 5. When you finish

1. Tick the item in the worklist and add the pull request link.
2. Append one entry to the improvement log: date, what changed, what you learned, what you would do differently, link. Append only. Never rewrite history.
3. Update the handoff: current status and next actions, 15 lines at most.
4. Do these file updates inside the same pull request as the work.

## 6. If you are the workspace helper (you can start other helpers)

- Split the worklist into independent items. Start one helper per item with `oat worker create "<task>" --model litellm:<type>`.
- Types: `architect` plans and researches, `implementer` writes code, `reviewer` checks work. For risky items run them in order: architect, then implementer, then reviewer.
- Keep at most 3 helpers running at the same time. The free AI services have small limits.
- When a pull request appears, tell the human in two lines: what it does and what to look at. Never merge anything yourself.

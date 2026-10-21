# test-ai-skills

Agent skills for our UiPath test automation work.

Private repository: the skills cite internal project structure, hostnames and Orchestrator
tenants. Keep it private.

## Skills

| Skill | Area | What it does |
|---|---|---|
| [`web-test-case`](web/web-test-case/SKILL.md) | `web` | Turns a manual web test description (`ATF_RTP_WEB_*.xlsx`) and its test data (`.csv`) into a UiPath test case inside the **web-test-framework** project, using its Object Repository, templates and page-object conventions. |

## Install

```bash
npx skills add ramesh09laksh-boop/test-ai-skills --list          # see what's in here
npx skills add ramesh09laksh-boop/test-ai-skills --skill web-test-case --agent claude-code
```

Skills nested under a top-level area folder (`web/<skill>/SKILL.md`) **are** discovered —
verified with `skills` CLI against this repo; no `--full-depth` needed. They install to
`.claude/skills/<skill>/`, so the folder name must be globally unique across everything you
have installed. Do not use a `uipath-*` prefix: that namespace belongs to UiPath's official
skills, which may be installed alongside these.

Add `-g` to install globally, or `--copy` to copy instead of symlink.

## Repository layout

```
<area>/<skill-name>/
├── SKILL.md            frontmatter (name, trigger-shaped description) + the workflow
├── references/         loaded on demand, one topic per file
├── scripts/            deterministic helpers the agent runs rather than reimplements
└── assets/             templates the agent fills in
```

`SKILL.md` stays short — it is always in context. Anything long, optional or reference-like
belongs in `references/`.

## Adding a skill

1. Create `<area>/<skill-name>/SKILL.md`. Pick a name that will not collide once installed.
2. Write a **trigger-shaped** `description`: when it should fire, and when it should not.
3. Put verifiable facts in `references/`, each one citing the file it came from.
4. Prefer a script over prose for anything deterministic, and ship a test with it.
5. Read [`AGENTS.md`](AGENTS.md) — it applies to anyone, human or agent, editing this repo.
6. Check discovery before you rely on the layout:
   `npx skills add <owner>/test-ai-skills --list`.

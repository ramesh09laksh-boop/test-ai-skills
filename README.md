# test-ai-skills

Agent skills for our UiPath test automation work.

Private repository: the skills cite internal project structure, hostnames and Orchestrator
tenants. Keep it private.

## What's in the repo

| Skill | Area | What it does |
|---|---|---|
| [`web-test-case`](web/web-test-case/SKILL.md) | `web` | Turns manual web test descriptions (`.xlsx`) and their test data (`.csv`) from a spec folder and a data folder into UiPath test cases inside the **web-test-framework** project, using that project's own Object Repository, templates and page-object conventions as they are on the day it runs. |

**Scope.** These skills *author tests inside UiPath Studio projects* — reading a manual spec,
mapping it to the project's page objects and Object Repository, writing the XAML, registering
the test case and running the CLI. They are not about administering Test Manager: test sets,
test data queues, requirements linking and execution reporting in Orchestrator/Test Manager
are covered by UiPath's own `uipath-test` skill, which can be installed alongside these. If a
request is "run and report this test set", that is `uipath-test`; if it is "implement this
manual test case", it is here.

## Prerequisites

- **Node and npx.** Verified on Node `v22.21.1` with npx `11.0.0`. The `skills` CLI is run
  through `npx`, so there is nothing to install globally.
- **Git access to this private repo.** `npx skills add` shells out to `git clone` over HTTPS,
  so you need either a credential helper that can serve github.com
  (`git config --global credential.helper manager` on Windows) or an SSH key plus
  `git config --global url."git@github.com:".insteadOf "https://github.com/"`. Without
  credentials the clone fails with an authentication error, not a "skill not found".
- **The internal NuGet feed**, only needed when you want to `pack` or run
  `web-test-framework` locally. The project depends on the internal `GlobaleWorkflow` package
  (it provides `Swisscom.PHI` / `Get_PHI_Vault`), which is not on nuget.org. Ask the UiPath
  platform team for the feed URL and add it to `%APPDATA%\NuGet\NuGet.Config`; credentials
  for it are not documented here and must not be committed anywhere. Without the feed, pack
  fails with `Cannot create unknown type ... Get_PHI_Vault` — an environment limitation, not
  a project defect. Analyzer and the skill's own parser work without it.

## Install into a project

Run these **from the UiPath project root** (the folder with `project.json`).

Every command below was executed against `skills` CLI **1.7.4**. Where a command people
expect does not exist, that is called out rather than guessed.

**One agent:**

```bash
npx skills add ramesh09laksh-boop/test-ai-skills --agent claude-code
```

**Several agents at once** — one `--agent` flag, agent names space-separated:

```bash
npx skills add ramesh09laksh-boop/test-ai-skills --agent claude-code github-copilot codex
```

**A single skill only** (and the same space-separated form for several skills):

```bash
npx skills add ramesh09laksh-boop/test-ai-skills --skill web-test-case --agent claude-code
```

**List what would be installed, without installing:**

```bash
npx skills add ramesh09laksh-boop/test-ai-skills --list
```

There is no `--dry-run` on `add` in 1.7.4 (`--dry-run` exists only on
`experimental_sync`). `--list` is the way to see the contents first.

Useful extras: `-y` skips the confirmation prompt (non-interactive agents are detected and
get this automatically), `--copy` copies the files instead of linking them, and `--all` is
shorthand for `--skill '*' --agent '*' -y`.

### Project vs global

| | Command | Use it when |
|---|---|---|
| Project | *(default)* `npx skills add … ` | The skill only makes sense inside one repo — which is the case for `web-test-case`, since it targets `web-test-framework`. The install is visible to your team in that repo. |
| Global | add `-g` | You want the skill available in every folder you work in, e.g. you jump between several Studio projects. Nothing lands in the repo, so nobody else gets it. |

Prefer **project** for `web-test-case`.

### Where the files land

Taken from real installs into scratch folders, one per agent, CLI 1.7.4 on Windows:

| Agent | `--agent` value | Project install | Global install (`-g`) |
|---|---|---|---|
| Claude Code | `claude-code` | `.claude/skills/<skill>/` | `~/.claude/skills/<skill>/` |
| GitHub Copilot | `github-copilot` | `.agents/skills/<skill>/` | `~/.agents/skills/<skill>/` |
| Codex | `codex` | `.agents/skills/<skill>/` | `~/.agents/skills/<skill>/` |

Copilot and Codex are *universal* agents: they read the shared `.agents/skills/` location
directly, so installing for both writes one copy. Claude Code has its own directory.

With a **single** agent the files are written straight into that agent's directory. With
**several** agents in one command, the CLI stages the skill in `.agents/skills/<skill>/` and
links the per-agent directories to it — on Windows, `.claude/skills/<skill>` becomes a
symlink/junction. Pass `--copy` if you want a real directory in each location instead.
A `skills-lock.json` is written at the project root either way; commit it so
`npx skills experimental_install` can restore the same versions.

Globally installed skills show the same shape: `~/.agents/skills/<skill>/` with a junction at
`~/.claude/skills/<skill>` for Claude Code. (Observed from the global skills already present
on this machine — a global install was not performed, to avoid disturbing them.)

### Check what is installed

```bash
npx skills list              # project skills
npx skills ls -g             # global skills
npx skills ls -a claude-code # filter by agent
npx skills ls --json         # machine-readable
```

## Update

```bash
npx skills update -y                  # all skills in this scope
npx skills update web-test-case -y    # one skill
npx skills update -g -y               # global skills only
npx skills update -p -y               # project skills only
```

`update` **is** the check: it prints `✓ All project skills are up to date` when there is
nothing to do, so run it to see whether an update is available. There is no separate
`npx skills check` command in `--help`; typing it in 1.7.4 happens to run the update path
anyway, but use `skills update` — that is the documented spelling and the one that will keep
working.

`-y` skips the scope prompt. Without it the CLI asks whether you mean project or global
(non-interactive agents are detected and answered automatically).

**Local edits to an installed skill are overwritten on update.** The installed copy is a
build artefact. Change the skill here in `test-ai-skills`, open a PR, then update.

## Remove

```bash
npx skills remove web-test-case -y    # by name
npx skills remove -y                  # interactive picker when run in a terminal
npx skills rm -g web-test-case -y     # from the global scope
```

`skills-lock.json` and the now-empty agent `skills/` directories are left behind; delete them
by hand if you want the project clean.

## Using the skill

Ask for it in the Studio project root, naming both folders:

> Implement the test cases from `D:\Specs\WebBanking` with data from `D:\Testdaten\WebBanking`.

There is **no default folder name yet** — the skill asks for both folders if you do not name
them, and it never searches the disk for them. If the team agrees on standard locations, add
them here as the default; the arguments still override.

What happens, in order:

1. **Project inspection.** The skill reads the project as it is right now — pages, dispatcher
   cases, Object Repository, stubs, templates, `project.json` — plus two specific checks:
   whether `Config\config.json` exists, and which config path
   `Framework\InitConfig.xaml` actually reads. A mismatch is reported and the fix is
   *proposed*, never applied.
2. **Pairing table.** Every `.xlsx` in the spec folder and every `.csv` in the data folder,
   paired by name. Identical base names pair automatically; a normalised match (case,
   umlauts, separators, `ATF_RTP_WEB_BANKING_`-style prefix) is shown as a **candidate for
   you to confirm**; anything else is listed as unpaired. Lock files (`~$*.xlsx`) and specs
   already present in `Testcases\` are skipped and reported. Nothing is paired on a
   similarity score.
3. **Gap gate** per test case. The placeholders in the spec (`<BETRAG>`, `<STADT>`, …) are
   matched to CSV columns. Only an exact normalised name match is used without asking;
   everything else stops and is put to you as a table. Missing test data is a question, never
   a plausible invention. One blocked test case does not stop the others.
4. **Implementation** of the cleared cases: the Gherkin scenario as the test case annotation,
   the steps mapped onto the existing `Actions\*` dispatchers and `Pages\<Page>\*` element
   workflows, every expected result as an assertion, the test case written to
   `Testcases\<TestCaseName>.xaml` and registered in `project.json`.
5. **Report**, from `web/web-test-case/assets/report-template.md`: the batch table, the data
   mapping, the steps, the files touched, real CLI output, proposed-but-not-applied fixes, and
   open questions.

### The capture list

An agent cannot capture a UI element — selectors come from pointing Studio's recorder at a
live page. So when a test needs an element the Object Repository does not have, the skill does
**not** invent a selector. It writes the Switch case with the activity in place and its target
unbound, marks the test case *not runnable*, and puts the element in a **capture list** in the
report: page, element name, the activity type it will be used with, and how to recognise it on
screen. Someone opens the project in Studio, captures those elements into the existing
`WebApp` app version, and the test becomes runnable. The capture list is the hand-off, not a
defect.

Your inputs are never touched: the skill treats every xlsx and CSV as read-only.

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

Skills nested under a top-level area folder (`web/<skill>/SKILL.md`) **are** discovered — no
`--full-depth` needed. Verified against this repo with `--list` on CLI 1.7.4.

## Contributing

1. **Create `<area>/<skill-name>/SKILL.md`** under a domain folder — `web/` today, more
   later. The folder name is what gets installed.
2. **Naming.** The installed folder name must be **globally unique** across everything a user
   has installed, because all skills land in one flat `skills/` directory per agent. Do not
   use a `uipath-*` prefix: that namespace belongs to UiPath's official skills, which are
   commonly installed alongside these.
3. **Write a trigger-shaped `description`**: when it should fire, and when it should not —
   especially against neighbouring skills it could be confused with.
4. Put verifiable facts in `references/`, each citing the file it came from. Keep *patterns*
   in the references and *inventories* in a dated snapshot file, so a changing target project
   does not silently make the skill wrong.
5. Prefer a script over prose for anything deterministic, and ship a test with it.
6. **Run the parser test before opening a PR:**

   ```bash
   python web/web-test-case/scripts/test_parse_spec.py --samples <dir with the sample xlsx+csv>
   ```

   It covers single-pair and batch mode and must exit 0.
7. Check discovery before you rely on the layout:
   `npx skills add <owner>/test-ai-skills --list`.
8. Read [`AGENTS.md`](AGENTS.md) — it applies to anyone, human or agent, editing this repo.

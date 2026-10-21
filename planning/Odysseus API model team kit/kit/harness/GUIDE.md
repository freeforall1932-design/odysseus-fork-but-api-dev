# AI Team: Setup and Use Guide

A small team of AI helpers that works on your GitHub project. **You stay in charge: nothing is merged unless you press Merge.**

---

## What you will have at the end

- A **dashboard** in your browser. You open it with one double-click.

- In the dashboard you **chat** with a helper, like in any AI chat. It can look through your project, start other helpers, and open **pull requests** (proposed changes) for you.

- You see the project's **files**, what each helper **changed** (with +/- counters), and your **pull requests**. You press **Merge** or **Close**.

- It uses only **free** AI services. A small program called the **model picker** checks every day which free models work best, so you never have to follow the news.

- The helpers read your project's own notes (handoff, worklist, improvement log) before they work, and write them up when they finish.

---

## How the parts fit together

- **Dashboard**: the web page you use. It runs only on your own computer.

- **Agent team (OAT)**: the helpers. They write code and open pull requests.

- **Router (LiteLLM)**: one front door to all the free AI services. If one is busy, it quietly uses another.

- **Model picker**: keeps the router's list of models fresh.

- **GitHub**: where your code lives and where you review changes.

```
You  <->  Dashboard  <->  Agent team (OAT)  ->  Router  ->  Free AI services (NVIDIA, OpenRouter, Google, Mistral)
                                                   ^
                                  Model picker keeps the list fresh
```

One small tool, `harness`, starts, stops and checks all of it. You will use the dashboard most of the time, and `harness` only for the first install.

---

## Words used in this guide

- **Terminal**: a text window where you paste commands and press Enter.

- **Key**: a long secret password that lets a program use an AI service. Never post it.

- **Model**: one specific AI "brain".

- **Pull request**: a proposed change on GitHub that you can read before accepting.

- **Token**: a special GitHub password for programs. Ours only reaches your project.

- **Skill**: a folder with a text file of instructions that the helpers read before they work.

- **Role**: a type of helper. The **architect** plans, the **implementer** writes code, the **reviewer** checks work.

---

## Step 0. Choose where it runs

The helpers run commands on the computer they live on, without asking you each time. So choose the place with care.

### A. Windows, with Ubuntu inside it (recommended)

- Good: it is free, fast, and the dashboard and double-click shortcut work well.

- Careful: it runs on your own PC. By default Ubuntu can see your Windows files, so use the "Keep it separate" steps below.

### B. Mac

- Good: it is simple and the double-click shortcut works.

- Careful: it runs on your own Mac. Use a normal (non-admin) Mac user if you can.

### C. GitHub Codespace (a computer in the cloud, used from your browser)

- Good: nothing is installed on your PC. It is separate from your own files by design, so it is the safest choice.

- Good: you can use it from any computer.

- Careful: it **stops after 30 minutes without activity**, and the helpers stop with it. You start it again whenever you come back.

- Careful: the free allowance is limited. Personal accounts get about **120 core-hours a month** (60 hours on a 2-core machine) and 15 GB of storage. You are not charged unless you raise your spending limit. It is free only for personal accounts, not for organization-owned projects.

- Careful: an unused codespace is deleted after **30 days** by default. Anything inside is lost, including your saved keys.

- Careful: I could not test this route myself. The commands are the same as on Ubuntu (a Codespace runs Ubuntu), but expect to send me an error or two.

### D. Docker (a sealed box on your own PC)

- Good: the strongest isolation on your own PC. Helpers could only touch what you put in the box.

- Careful: it needs Docker installed and more setup. I have not built or tested a Docker version, so this kit does not include one. Everything in the kit would run inside Ubuntu in a box without changes. If you want it, ask me and I will build and test it.

### Which one?

- Want the easiest: **A** (Windows) or **B** (Mac).

- Want the safest, or do not want anything on your PC: **C**.

- Already use Docker and want a sealed box: ask me for **D**.

---

## Step 1. Open a Linux terminal

### A. Windows

1. Click **Start**, type `PowerShell`, right-click it and choose **Run as administrator**.

2. Paste this and press Enter, then restart your computer when it asks:

   ```
   wsl --install -d Ubuntu-24.04
   ```

3. Open **Ubuntu 24.04** from the Start menu. The first time, it asks you to invent a **username** and a **password**.

   About that password:

   - It cannot be empty (I tried: Ubuntu refuses).

   - Short ones like `1234` or `word` are accepted (I tried), but a weak one is risky. The helpers run as this user, and this password is what protects your Ubuntu from them.

   - Nothing shows on screen while you type it. That is normal.

4. This black window is your terminal. Right-click pastes into it.

If it says "virtualization is turned off", switch on "Virtualization" in your computer's BIOS settings. Search for your computer model plus "enable virtualization".

#### Keep it separate (recommended, 2 minutes)

Make a second Ubuntu user just for the helpers. It has no admin rights and cannot see your main user's files.

```
sudo adduser aiteam
```

Choose a password. Press Enter for the other questions. Then switch to that user:

```
sudo -iu aiteam
```

**Do every step below as `aiteam`.** The installer sets up the Windows shortcut for this user.

Extra protection (optional): you can stop Ubuntu from seeing your Windows drives.

```
sudo nano /etc/wsl.conf
```

Add these two lines, save (Ctrl+O, Enter, Ctrl+X), then run `wsl --shutdown` in PowerShell:

```
[automount]
enabled=false
```

Warnings: do this **after** Step 2, because afterwards you cannot copy files from Windows into Ubuntu. It affects the whole Ubuntu, not only `aiteam`. To undo it, change `false` to `true`.

A plain "isolated folder" does not protect you. The helpers run as the user who started them, so they can reach anything that user can reach. A separate user is what really separates them.

### B. Mac

Press Cmd+Space, type `Terminal`, press Enter. Then type `brew --version`. If it says "command not found", go to https://brew.sh and run the one line shown there.

### C. GitHub Codespace

1. Open your project on github.com. Click the green **Code** button, then **Codespaces**, then **Create codespace on main**.

2. Wait for the editor to open in your browser. The terminal is the panel at the bottom.

3. Use this terminal for everything below. It already has `git`, `gh` and Python.

**Is the installation the same as on Ubuntu?** Almost. The differences:

- You do not need Step 2. `unzip` may be missing: run `sudo apt install -y unzip`.

- To get the kit in, drag `ai-team-kit.zip` into the file list on the left, then use the `unzip` line from Step 3 with `~` as the target.

- You are already signed in to GitHub, but only with a short-lived token. Step 7 replaces it with yours. The `harness` command ignores GitHub's temporary one for you.

- There is no double-click shortcut. Run `harness open` in the terminal each time you come back. It prints the dashboard link. You can also open the **Ports** tab, find port 8765 and click the globe.

---

## Step 2. Install the basic tools

**Windows (Ubuntu) and Codespace:**

```
sudo apt update
sudo apt install -y git curl unzip python3 python3-venv gh
```

**Mac:**

```
brew install git gh python
```

`sudo` asks for your Ubuntu password. Nothing shows as you type.

Check:

```
git --version
gh --version
python3 --version
```

**Done when:** all three show a version, and Python says **3.11 or higher** (Ubuntu 24.04 has 3.12). If Python is older, you are not on Ubuntu 24.04: repeat Step 1 with `wsl --install -d Ubuntu-24.04`.

---

## Step 3. Unzip the kit and run the installer

You downloaded **ai-team-kit.zip** from this chat.

**Windows (Ubuntu).** First find your Windows user name:

```
ls /mnt/c/Users
```

Use yours in place of `YOURNAME`:

```
unzip -o /mnt/c/Users/YOURNAME/Downloads/ai-team-kit.zip -d ~
```

If it says the file is not found, Windows may keep your Downloads in OneDrive. Find the file with:

```
find /mnt/c/Users -maxdepth 4 -name ai-team-kit.zip 2>/dev/null
```

**Mac:**

```
unzip -o ~/Downloads/ai-team-kit.zip -d ~
```

**Codespace:** `unzip -o ai-team-kit.zip -d ~`

Now run the installer:

```
bash ~/harness/install.sh
```

It takes 5 to 10 minutes. Lots of text scrolls by. It installs the router and the agent team, puts the `harness` command in place, installs the built-in skills, and (on Windows) puts **Start AI Team** and **Stop AI Team** on your desktop. It never uses `sudo`. If something is missing, it tells you the exact command to run.

When it finishes, open a **new** terminal window (or run `source ~/.bashrc`).

Check everything at any time with:

```
harness doctor
```

It shows `[OK]` or `[FIX]` for every part, with the command that fixes it.

**Done when:** the installer ends with "All installed".

---

## Step 4. Get your free AI keys

Make an account on each service and create a key. **Get at least two.** More services means more backups when one is busy.

- **NVIDIA** (strong models, free for testing): https://build.nvidia.com. Sign in (it may ask you to verify your phone). Open any model page and click **Get API Key**. The key starts with `nvapi-`.

- **OpenRouter** (many free models): https://openrouter.ai, then https://openrouter.ai/keys, then **Create Key**.

- **Google AI Studio** (fast "Flash" models): https://aistudio.google.com, then **Get API key**.

- **Mistral** (free coding model for a limited time): https://console.mistral.ai. Choose the free **Experiment** plan, then **API Keys**, then **Create new key**.

Websites move their buttons sometimes. Look for the words "API key".

### OpenRouter: what the free allowance really is

- Free models (the ones ending in `:free`) allow **20 requests a minute**, and **50 a day** until you have bought at least $10 of credit. After that the daily limit is **1,000**.

- Does depositing $10 really raise it? **Yes, according to OpenRouter's own documentation.** The documentation says the check looks at credits purchased **over all time**. So you keep the 1,000 a day even after you spend the balance down.

- Is it guaranteed? **No.** OpenRouter's terms say it may change features and limits at any time, and may change its terms without notice. The docs also say free capacity comes from other companies and can change. Credits are non-refundable after 24 hours, and OpenRouter reserves the right to expire unused credits 365 days after purchase. The docs do not say what happens to your 1,000 a day if credits expire. I read these through search results, so check https://openrouter.ai/terms before paying.

- Extra accounts or extra keys do **not** raise the limits (the docs say so). So one key per service is right.

- You said you want free only. Depositing is your choice, and it is not needed: the other services cover for OpenRouter.

### Free services can use what you send them

Free endpoints may keep prompts or use them to improve models. Keep private things (passwords, customer data) out of your code and out of your chats.

---

## Step 5. Save your keys, one service at a time

```
harness setup-keys
```

It asks for **one service at a time**: OpenRouter, NVIDIA, Mistral, Google. For each one:

- Paste the key and press Enter. Nothing shows on screen. That is normal.

- Press **Enter on its own** to skip a service you do not have. It stays empty.

- Each key is **tested before it is saved**.

What can happen, and what it means:

- `saved. (key accepted)`: the key works and is saved.

- `That key was refused`: the key is **not saved**, and your **old key is kept**. You can paste another one (3 tries) or press Enter to skip.

- `I could not check the key`: your internet or the service is down. It asks if you want to save it anyway. Say `n` if unsure. Run `harness check` later.

To change one key later, without going through all four:

```
harness set-key nvidia
```

To remove one:

```
harness remove-key nvidia
```

**What happens to the old key when you paste a new one?** It is replaced, and the previous keys file is kept once as `keys.env.bak` in `~/.config/gifscythe-harness/`. If the new key is refused, nothing changes.

**What if a saved key stops working later?** Nothing is deleted behind your back. The service shows as `[refused]` and is **skipped** (never retried again and again) until you replace the key. Then it clears by itself.

See where every key stands:

```
harness keys
```

```
Service      Status      Key        Last result
openrouter   [ok]        sk-...a1b2 12 free models look usable
nvidia       [refused]   nva...9xyz the service answered 401: the key was refused
mistral      [skip]                 MISTRAL_API_KEY is not set
```

The words:

- `[ok]` works.

- `[skip]` no key saved. Nothing wrong.

- `[refused]` the key was rejected. Replace it with `harness set-key NAME`.

- `[offline]` could not reach the service (internet or the service is down). It tries again next time.

- `[limit]` the free allowance is used up for now. It comes back later.

- `[blocked]` an account setting blocks free models. For OpenRouter, open https://openrouter.ai/settings/privacy and allow free models that may log prompts (this is what free models need). Then run `harness check`.

You can also do all of this later in the dashboard (**Connections** tab).

**Done when:** `harness keys` shows `[ok]` for at least one service.

---

## Step 6. Test the model picker

The model picker finds free models that work well today and writes the router's list. Test it in small steps, from safest to most real.

### 6a. Test the script itself (needs no keys, no internet)

```
harness selftest
```

**You should see:** many lines starting with `ok`, and at the end `selftest passed`. If you see `FAIL`, stop and send me the last 20 lines.

### 6b. Test your keys

```
harness check
```

This uses almost none of your free allowance (one tiny request per service).

```
[OK]      nvidia: key accepted; 12 free models look usable (of 140 listed)
[OK]      openrouter: key accepted; 25 free models look usable (of 310 listed)
[skip]    mistral: MISTRAL_API_KEY is not set
```

You need at least one `[OK]`. Anything else is explained under Step 5.

### 6c. First real run

```
harness scout
```

It looks at the free models and **quick-tests** the best ones: a few tiny questions each, to see if they can use tools, read code and follow instructions.

It is **gentle on purpose**:

- It tests **one model at a time on each service**, and **rests 20 seconds** between two models of the same service, so no service sees a burst of requests.

- It tests the **most-used model of the week first** (OpenRouter publishes that), and otherwise the **biggest model** first.

- It tests only a few models per service per run, to protect your free allowance. The list gets better each time it runs.

- It takes **5 to 15 minutes** the first time. You will see lines like `tested nvidia:... tools ok, code 2/2, bugs 1/2`.

Want it even gentler, or faster? Make a settings file (all settings are optional):

```
cat > ~/harness/scout.yaml <<'EOF'
probe:
  pause_between_models: 45   # seconds of rest between models
  models_at_a_time: 1        # 1 or 2 per service
  services_at_a_time: 1      # 1 = one service after another
  test_order: popular_then_big   # or: balanced
EOF
```

**You should see** a report at the end. The three roles each list one to three models. Number 1 is the first choice, 2 and 3 are backups:

```
## architect
1. nvidia:nvidia/nemotron-3-ultra-550b-a55b - score 0.71 (tests 0.8, hints 0.6, newness 0.9, size 0.7)
2. ...
```

Read it any time with `cat ~/harness/scout_report.md`, or in the dashboard (**Models** tab).

Look at the role titles in the report:

- A plain title is normal.

- `(no model of its own right now - using picks from other roles)`: no model passed the tests for that role, so it **borrows** models from the other roles. It still works.

- `(UNAVAILABLE - no working model right now)`: nothing works for any role. This is not about "no tasks to do". It means every service is `[offline]`, `[refused]` or has no usable free model. Run `harness check` to see which, and fix that.

### 6d. See that it remembers

Run `harness scout` again right away. It should finish in seconds and say `No change in the picks.` That means it saved the results and is not wasting your free allowance.

**Done when:** the three roles have models and the second run is quick.

---

## Step 7. Sign in to GitHub

### 7a. Make a token that only reaches your project

1. On github.com click your picture (top right), then **Settings**, then **Developer settings** at the bottom of the left menu.

2. **Personal access tokens**, then **Fine-grained tokens**, then **Generate new token**.

3. Name it `ai-team`. Set **Expiration** to 90 days. Put a reminder in your calendar for day 80.

4. **Repository access**: **Only select repositories**, then pick your project. (If you add more projects later, edit the token and add them.)

5. **Repository permissions**. This is the set I recommend. It is close to the one you use:

   - **Contents**: Read and write (needed: read and change code)

   - **Pull requests**: Read and write (needed: open and read pull requests)

   - **Issues**: Read and write (needed: read and comment on issues)

   - **Commit statuses**: Read and write (optional)

   - **Actions**: Read and write (optional: see build results, rerun builds)

   - **Metadata**: Read-only (added by GitHub automatically)

   - **Administration**, **Code scanning alerts**, **Dependabot alerts**, **Secret scanning alerts**: Read-only (optional: lets helpers audit your project)

   - **Workflows**: Read and write (**only if you want helpers to edit** `.github/workflows`)

   Important: **"Actions" is not the same as "Workflows".** "Actions" is for build runs and logs. Changing the workflow files needs **Workflows**. Your list had Actions but not Workflows, so helpers could read and rerun builds but GitHub would refuse their changes to workflow files.

   The more you allow, the more a mistake can break. A helper that can change workflows can change what runs with your project's secrets. That is why the helpers are told to put workflow changes in a pull request and wait for you (see Step 11).

6. Click **Generate token** and copy it (starts with `github_pat_`). GitHub shows it only once.

### 7b. Give it to the helpers

```
harness github-login
```

Paste the token and press Enter (nothing shows).

**You should see:** `OK: your token can see ...`.

If you see a message about `GITHUB_TOKEN`, run `unset GITHUB_TOKEN` and try again.

**Done when:** you see that `OK` line.

---

## Step 8. Connect the agent team and add your project

Do these three commands in this order:

```
harness connect-oat
harness start
harness add-repo https://github.com/freeforall1932-design/gifscythe
```

- `harness connect-oat` tells the agent team how to reach the router. It also writes a small file the agent team needs to start.

- `harness start` starts the router and the agent team. (If the model list is older than 12 hours, it refreshes it first.)

- `harness add-repo ...` adds your project. The agent team makes its own copy of your code. It also **turns off the auto-merge helper** so nothing merges unless you press Merge, and makes this project the **default** one.

**You should see:** `Done. The project 'gifscythe' is added...`

### Adding more projects later

Use `harness add-repo` with another GitHub address, or **+ Add project** in the dashboard. A design repository, a skills collection, or a project you want helpers to work on all work the same way: they become another project in the dropdown at the top of the dashboard.

**What is `--repo`?** Some `oat` commands need to know which project you mean. You add `--repo NAME` at the **end** of the command, with the **full** name shown by `oat list`, for example:

```
oat worker create "your task" --model litellm:implementer --repo gifscythe
```

`oat list` itself does not need it (it lists all projects). `harness add-repo` already chose a default project, so you rarely need `--repo`. The dashboard always adds it for you.

### If connect-oat refuses

It refuses only when `~/.oat/config.toml` already exists with other settings (it will not overwrite them). Open it and add this block at the end, using your router password from `~/.config/gifscythe-harness/keys.env` (the `LITELLM_MASTER_KEY` line):

```
[models.providers.litellm]
models = ["architect", "implementer", "reviewer"]
class_path = "langchain_openai:ChatOpenAI"

[models.providers.litellm.params]
base_url = "http://127.0.0.1:4000/v1"
api_key = "PASTE_THE_ROUTER_PASSWORD_HERE"
```

Then put these two lines in `~/.oat/.env`:

```
OPENAI_API_KEY=PASTE_THE_ROUTER_PASSWORD_HERE
OPENAI_BASE_URL=http://127.0.0.1:4000/v1
```

(The agent team refuses to start work unless it finds some provider key there. All models still go through the router.)

---

## Step 9. Open the dashboard

```
harness open
```

It starts everything that is not running yet, then opens the dashboard in your browser. On Windows you can also **double-click Start AI Team** on your desktop. On Mac, double-click `Start AI Team.command` in the `mac` folder inside `harness`.

**Leave the black window open while you work.** It keeps Windows from shutting Ubuntu down, which would stop the helpers.

If the browser does not open, copy the address the window prints (it ends with `?t=` and a secret). That secret link is the key to the dashboard: keep it private.

### How to start it again later

- **Windows:** double-click **Start AI Team**. It does everything. If you prefer: open Ubuntu and type `harness open`. From PowerShell: `wsl -e bash -lc "harness open"`. (Plain `harness open` typed into PowerShell does not work: PowerShell does not know it.)

- **Mac:** double-click **Start AI Team**, or type `harness open` in Terminal.

- **Codespace:** open the codespace again, then type `harness open` in its terminal.

It is always safe to start it again. It only starts what is not already running.

**What if my internet is off?** The dashboard still opens. The services show `[offline]`, and the helpers cannot think until it is back. Nothing breaks. When the internet returns, press **Refresh models** or just run `harness start`.

To stop everything: double-click **Stop AI Team**, or run `harness stop`, or press **Stop** in the dashboard (that one keeps the dashboard open).

**Done when:** the dashboard shows green dots for Router, Agent team and GitHub.

---

## Using the dashboard

**Top bar**: the project dropdown, four status dots (Router, Agent team, GitHub, Models), **Start** and **Stop**.

**Left**: your projects, the helpers that are working right now (click one to see its changes), recent work, and quick buttons.

**Middle, three tabs:**

- **Chat**: talk to the **workspace helper**. Type what you want, like in any chat: "fix the save bug", "what is left on the worklist?". It can read your project and start other helpers by itself. The reply area is a live copy of what that helper prints in its terminal, so it looks more like a transcript than polished chat bubbles. It updates every two seconds.

- **Tasks**: hand a task straight to a **new** helper and pick its role (implementer, architect, reviewer). Handy buttons for common tasks are here too.

- **Ask the models**: a plain chat with the free models, like a normal AI chat. They cannot see your project here. It shows which model answered.

**Right, seven tabs:**

- **Files**: browse the project's files. Pick a helper at the top to see **that helper's** own copy.

- **Changes**: what a helper changed, with **+ and − counters** per file. Click a file to see the colored difference.

- **Pull requests**: your open, merged or closed pull requests with counters. **View changes** shows the difference. **Merge** and **Close** ask you to confirm first. Only press Merge after you have read the changes.

- **Models**: the three roles, their models in order, the services' status, and the last report. **Refresh models** is here.

- **Connections**: GitHub sign-in, and your AI keys (paste, test, replace, remove). Also a place for a free **Tavily** key so helpers can search the web. Plug-ins that need MCP are **not** supported by this agent team (see Step 11).

- **Skills**: the skills the helpers have. You can add skills from any GitHub project (see Step 11).

- **Logs**: the router, agent team, dashboard and model report logs.

If something is not set up yet, the middle area shows a **checklist** with a button for each missing part.

---

## Step 10. Your first test

1. In the dashboard open **Tasks**. Pick **implementer** and write: `Add one comment line at the very top of README.md that says: AI team test. Then open a pull request.` Press **Start the task**.

2. Watch the left side: a helper appears. After about 5 to 15 minutes a pull request appears (free services can be slow; that is normal).

3. Open **Pull requests**, read it, then **Close** it. It was only a test.

Nothing after 20 minutes? Press **Doctor** in the left quick buttons, or run `harness status` and `harness logs`.

---

## Step 11. Make the team smarter

### Your handoff, worklist and improvement log

Will the helpers know how to pick up your project's own notes, such as a session handoff, a worklist, an improvement log, or a planning report? **Not by magic.** The helpers are general AI. They only follow your conventions if someone tells them. So the kit gives them two things:

- A **skill called `team-workflow`**, installed for all helpers. It tells them where to look (handoff, worklist, planning, decisions, improvement-log files, in the root or in `docs/`, with any capital letters), what to read first, how to choose the next item, never to decide the things you reserve for yourself, and how to update the files when they finish. The workspace helper also learns how to split work between other helpers. It does **not** invent files: if your project has none, it offers to create them from small templates.

- A small **workflow note for every worker**. OAT reads every file in a folder named `oat-worker-prompt-extensions/` in your project before each worker starts. Ask the workspace helper once: *"Using the team-workflow skill, add the project workflow files to this project and open a pull request."* (The **Tasks** tab has a button for it.) Merge that pull request.

Then check that it works: in **Chat** press **What should we do next?** (in Tasks, "Handy tasks"). It should read your files and answer with the top items and why. If it does not mention your files, tell me what it said.

Be honest about the limit: skills work by the helper noticing that a skill fits. A very small or very confused model can miss it. The worker note is read every time, so it is the safer one. Model choice also matters: the architect and reviewer picks are the strongest.

### Project rules only for this project (optional)

Add a skill that lives **in your project**. Open the project on github.com, **Add file**, **Create new file**, and name it exactly:

```
.agents/skills/gifscythe-guardrails/SKILL.md
```

Paste:

```markdown
---
name: gifscythe-guardrails
description: Project rules for Gifscythe work. Read before starting any task or opening any pull request in this project.
---

# Gifscythe guardrails

- Never decide OD-16 (GPLv2 engine in-process with Ms-PL code), OD-18, the wasm Option A vs B call, or the 1.0.0 version bump. If a task depends on one, stop and put the question in the pull request description.
- Do not create tags or releases. The release re-cut (U-09/P0-4) is done by a human. Prepare notes only.
- W-18 (clean-Windows smoke test) and W-19 (desktop probes) need real Windows hardware. Write the steps or scripts and mark the pull request "needs human run".
- One worklist item per pull request, with its ID (for example U-59/P0-7) in the title. Run the build and tests you can, and paste the results in the pull request.
- Never write keys, tokens or passwords into any file.
```

Commit to the main branch. Helpers pick it up the next time they start a task.

### Helpers that find and add what they are missing

The kit also installs a skill called **`self-extend`**. When a helper cannot finish something because a tool, skill or workflow is missing, the skill tells it to:

1. Say what is missing.

2. Research: its installed skills, your project's docs, then the web. For the web it uses the `web_search` tool if you added a free Tavily key (dashboard, **Connections**), and otherwise `fetch_url`, GitHub search (`gh search`), and the PyPI and npm lists.

3. **Check before trusting**: the licence, whether it is maintained, and every script. It refuses anything that downloads and runs other code, uses `sudo`, reads keys, or sends data to strange places.

4. Add it **the safe way**:

   - Skills a helper writes itself, workflow changes, and new packages all go in a **pull request**. Nothing is pushed straight to your main branch, and helpers never merge.

   - It must **ask you first** before adding a third-party skill, changing `.github/workflows`, changing the project's dependencies, or touching anything outside the project.

   - It must **never** write secrets into files, switch off checks, or decide your reserved decisions.

You asked that they can change things directly, and your GitHub token allows it. The skill is deliberately a little stricter than the token, because a helper that reads the web can be tricked by text on a page into doing something harmful. To loosen it (for example, allow adding skills to your own skills folder without asking), edit `~/.agents/skills/self-extend/SKILL.md`. It is only a text file. `harness install-skills --force` puts the original back.

Do you need to build your own tool for skills? **No.** Skills are built into the agent team. A tool is a small script inside a skill's `scripts` folder, described in its text file. **MCP plug-ins** are the one thing the agent team does not load. You will rarely need them. If you do, ask me: it needs a small patch.

### Adding other repositories: design or skills

- To **work on** a repository (code, design files): **+ Add project**, or `harness add-repo URL`.

- To use a repository as a **source of skills** (a skills collection, a design kit, or skills that came out of Microsoft's SkillOpt): dashboard, **Skills** tab, paste its GitHub address, press **Look inside**. You see every skill in it, whether it has scripts (flagged in yellow), and whether it has a licence file. Tick the ones you want, press **Install selected**. Skills can contain scripts, so only add repositories you trust.

- Microsoft's **SkillOpt** is a separate program that trains and improves skill files. It is not part of this kit, and the helpers do not run it. Its output skill files can be installed with the Skills tab.

---

## Your daily routine

1. Double-click **Start AI Team** (or `harness open`).

2. Chat or give tasks.

3. Review the pull requests. Merge or close.

4. When done, **Stop AI Team**.

Every few days, glance at **Models** to see that the picks are fresh. If a free model disappears or a better new one appears, the model picker handles it the next time it runs (every time you start, if the list is older than 12 hours).

---

## When something goes wrong

Start with `harness doctor`. It lists what is missing and how to fix it. Then look here.

**`command not found` for `harness`, `oat` or `uv`**
Close the terminal and open a new one, or run `source ~/.bashrc`. If it is still missing, run `bash ~/harness/install.sh` again.

**A service shows `[refused]`**
The key was rejected. Run `harness set-key NAME` and paste it again, making sure you copy all of it.

**A service shows `[offline]`**
The service or your internet is down. Wait and run `harness check`. Nothing was lost.

**A service shows `[limit]`**
Its free allowance is used up for now. It comes back. Other services keep working.

**A service shows `[blocked]`**
An account setting blocks free models. For OpenRouter, open https://openrouter.ai/settings/privacy and allow free models that may log prompts. Then `harness check`.

**A role shows `UNAVAILABLE`**
No working model for any role. Run `harness check` and fix the services that are not `[OK]`.

**`harness scout` says it could not reach any AI service**
Check your internet. On Windows try `wsl --shutdown` in PowerShell, then open Ubuntu again.

**The router will not start**
Run `harness logs`. If you changed keys after starting it, run `harness stop` then `harness start`.

**`harness ask` shows an error**
Free services are sometimes busy. Wait a few minutes. Or run `harness scout`.

**The dashboard says it is locked**
Open it with the link from `harness open` (it ends with `?t=` and a secret).

**Chat says the agent team did not take the message**
The team may not be running: press **Start**. Also check that your project is listed in the left column.

**A helper cannot push or open a pull request**
Check the token (Step 7). It needs **Contents** and **Pull requests** set to Read and write, for your project. Make a new one and run `harness github-login`.

**OAT says a model is "not onboarded"**
OAT's model safety check is switched on. Tell me and I will walk you through turning it off.

**`oat init` says no provider key**
Run `harness connect-oat` (it writes the small file OAT needs), then `harness add-repo ...` again.

**Nothing happens after I give a task**
Run `harness status`. If the router or the agent team is not running, press **Start**. Then `harness logs`.

**The installer ends with `tmpdir: unbound variable`**
Ignore it. It is a harmless cleanup message from OAT's own installer. What counts is that `oat version` works.

**My Codespace stopped**
Open it again and run `harness open`.

---

## Quick reference

- `harness open`: start everything and open the dashboard.

- `harness doctor`: check every part, with fixes.

- `harness keys` / `set-key NAME` / `remove-key NAME` / `setup-keys`: your keys.

- `harness check` / `scout` / `selftest`: the model picker.

- `harness start` / `stop` / `status` / `logs`: run and watch.

- `harness github-login`, `connect-oat`, `add-repo URL`, `install-skills`: set-up pieces.

- Settings file for the model picker: `~/harness/scout.yaml`.

- Keys: `~/.config/gifscythe-harness/keys.env` (the previous one is `keys.env.bak`).

- Reports: `~/harness/scout_report.md`.

---

## Notes: what was wrong in the first plan

You do not need this to follow the steps. Keep it for troubleshooting, or ask me about any line.

**Things that would not have worked**

- The OAT install link belonged to a different project. This guide uses the real one from OAT's own page.

- OAT supports Mac and Linux. Its page says Windows is "not tested". That is why Windows goes through Ubuntu (WSL).

- The commands `oat task create`, `oat task status`, `--assign` and `--role` do not exist. The real command is `oat worker create "task" --model ...`.

- The settings `OAT_MODEL_ENDPOINT` and `OAT_MODEL_API_KEY` do not exist. The real way is a block in `~/.oat/config.toml`. On top of that, OAT will not add a project unless it finds some provider key in `~/.oat/.env`. I found this by running it. `harness connect-oat` now writes both.

- The router's "backup" rules were written so only the first counted. They are now separate entries and never loop.

- The key-rotation tool (`llm-keypool`) had a wrong flag and does not support NVIDIA. The router already rotates and rests failing services, so the tool was dropped.

- OAT has a model safety check that turns on after you "onboard" even one model. This guide avoids it by never onboarding.

**Safety problems**

- The router would have listened on every network connection with a guessable password. Now it listens only on your computer and uses a random password.

- OAT starts helpers that run commands without asking. So: a separate user or a cloud box, a token for one project, and your AI keys are kept out of the helpers' environment (I checked this).

- OAT's auto-merge helper merges pull requests by itself unless turned off. `harness add-repo` turns it off.

- The first plan mixed up GitHub token types and typed the token into a command line. `harness github-login` asks for it without showing it.

- The first plan ran an install script straight from the internet. The installer now downloads it, and the version is fixed.

**Facts that were out of date or could not be confirmed**

- OpenRouter's free allowance is about 50 a day (1,000 after buying $10 of credit), not 200. Extra keys do not help.

- Google's free-allowance numbers could not be confirmed. Google shows the real numbers inside AI Studio.

- "Chutes 200 a day" and "FHRouter" could not be confirmed. I found no trace of fhrouter.com. They were left out.

- The "free" status of the three models in the first plan is shaky, which is why the model picker exists.

- Node.js 20 reached end of life in April 2026, and Node is not needed.

**Design changes**

- Four layers became three: OAT, the router, the services.

- `llm-keypool`, OmniRoute and Claw Orchestrator were dropped.

- OAT has no per-role model setting. You choose with `--model` per task, and the dashboard does this for you.

- The first plan did not say where OAT runs. It is a program that must keep running on some computer.

---

## Notes: how the files in the kit were checked

**`model_scout.py`** (the model picker) has 68 built-in checks (`harness selftest`). They cover filtering, ranking, new models appearing, models disappearing, running out of free use, temporary errors, paced testing (never two models at once per service, a rest between models, biggest or most-used first), refused keys, the OpenRouter privacy setting, borrowed roles, key saving and replacing, and the real network code against a fake AI service on your own computer. It also passes on Python 3.10, 3.12 and 3.14, and the code scanners found nothing left to fix.

Problems I found in my own earlier versions and fixed:

- `--dry-run` with `--probe` spent free requests and threw the results away.

- A "maintenance" page from a service marked a good model unusable for a week.

- A "403 forbidden" blocked a model for 7 days (now 1 day).

- Two bug-finding questions had the same answer.

- "Thinking" models could run out of room (the answer limit is higher now) and their thinking text broke the answer checks.

- A missing `~/.litellm` folder crashed it, and a half-written file could be read by the router.

- A run with no internet could save empty results.

- A redirect to another site could have carried your key. It is now refused.

- One odd reply could crash a whole run. Now it is skipped.

- A refused key was tried again on every run.

- The OpenRouter privacy setting would have marked every free model unusable for a week.

- A role with nothing used to be called `EMPTY`. It now borrows from the other roles or says `UNAVAILABLE`.

- Progress lines from two services could be glued together.

**`harness.sh`** was tested for key saving (including a refused key, replace, backup and remove), `start`, `stop`, `status`, `ask`, `doctor`, `open`, `add-repo` (up to the GitHub step), and `connect-oat` (including refusing to overwrite). Found and fixed: `connect-oat` did not satisfy OAT's startup key check, so `oat init` would have failed; `status` said no project was added when one was; the Codespace token and link handling; and an error message that pointed to a guide section that did not exist.

**`harness_ui.py`** (the dashboard) has 84 checks: 63 on its server and 21 that run the real page in a test browser engine against it. They cover the secret link, other website names refused, the protection against other sites making it act, every route, file and symlink escapes, key handling (never sent back to the page), pull requests, skills install, jobs, and chat. Found and fixed: a Stop button that would have stopped the dashboard itself; your chat messages shifting when the helper's output had non-English characters; a refused request leaving data on the connection; links not limited to https.

**What I could not test**

- Your real accounts, and what the real AI services answer.

- The GitHub steps with a real token (`harness github-login`, `oat init`, helpers opening real pull requests, Merge and Close buttons against real GitHub).

- Windows (WSL), Mac and Codespace specifics: the install commands, the double-click files, `wsl.conf`, the forwarded dashboard address.

- What the workspace helper's real output looks like in the Chat tab (I tested with a stand-in).

- Docker (not built).

If any of these misbehave, send me the exact text on screen and I will fix it.

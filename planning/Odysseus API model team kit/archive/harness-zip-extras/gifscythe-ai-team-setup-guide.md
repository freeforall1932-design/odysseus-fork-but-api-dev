# Gifscythe AI Team: Setup Guide

A small team of AI helpers that works on your Gifscythe project while you stay in charge.

---

## What you will have at the end

- You type a task, like "fix the save bug".

- An AI helper works on its own copy of your code.

- It opens a **pull request** on GitHub (a proposed change).

- You read it. If you like it, you press **Merge**. If not, you close it.

- **Nothing is merged unless you press the button.**

All the AI "thinking" happens on free services on the internet, so nothing heavy runs on your computer.

---

## How the parts fit together

1. **Free AI services** (NVIDIA, OpenRouter, Google, Mistral) do the thinking. Each one gives you a free key, which works like a password.

2. **The router** (called LiteLLM) is one front door to all of them. If one service is busy or out of free use, it quietly tries another.

3. **The model picker** (`model_scout.py`) keeps the router's list fresh. Free AI models change every few months, so it checks what is free and good today, tests the best ones, and updates the list. You don't have to follow the news.

4. **The agent team** (called OAT) is the helpers themselves. They write code and open pull requests.

5. **GitHub** is where your code lives and where you review changes.

```
You  -->  Agent team (OAT)  -->  Router (LiteLLM)  -->  Free AI services
                                      ^
                       Model picker keeps the list fresh
```

One small tool called `harness` ties it together. One short command starts, stops, tests and checks everything.

---

## Before you start

- **Time:** about 1 to 1.5 hours the first time. Much of it is waiting for downloads.

- **You need:** your GitHub account (the one that owns the Gifscythe project), an email address for signing up to the free AI services, and a Windows or Mac computer.

- **Two files from this chat**, saved in your computer's Downloads folder: `model_scout.py` and `harness.sh`.

- I tested the scripts and the connections between the parts on my side. I could not test your real accounts or GitHub. If any step shows an error, copy it to me.

**Read this safety note first:**

- The AI helpers can run commands on the computer they live on, without asking you each time. So run them somewhere you don't mind them working, and don't keep private files or other passwords there.

- On Windows, the helpers live in the Ubuntu window, but Ubuntu can see your Windows files. Don't open the helpers in folders that hold private things.

- Only use **free** keys here. Never anything linked to your bank card.

- The GitHub token you will make only works on the Gifscythe project.

- Free AI services may keep what you send them. Keep private information out of your code.

---

## Words used in this guide

- **Terminal:** a text window where you type or paste commands. You press Enter to run them.

- **Key:** a long secret password that lets a program use an AI service. Never share it or post it online.

- **Model:** one specific AI "brain". Different models are good at different things.

- **Pull request:** a proposed code change on GitHub that you can read before accepting it.

- **Token:** a special GitHub password made for programs. Ours only works on one project.

- **Skill:** a folder with a text file of instructions that the helpers read before they work.

---

## The steps at a glance

1. Open a Linux terminal
2. Install the basic tools
3. Put the two helper files in place
4. Get your free AI keys
5. Save your keys
6. Install the router
7. Set up and test the model picker
8. Start the router and test it
9. Install the agent team
10. Sign in to GitHub
11. Connect the agent team to the router
12. Start the team and add your project
13. Run a first test task
14. Teach the helpers your rules (skills)
15. Your daily routine
16. Your Gifscythe worklist

After the steps: **When something goes wrong**, **Reference: the model picker**, and **Notes** at the very bottom.

---

## Step 1. Open a Linux terminal

Everything below is typed into a Linux terminal. Choose ONE way to get one.

### Windows (recommended): Ubuntu inside Windows

1. Click **Start**, type `PowerShell`, right-click it and choose **Run as administrator**.

2. Paste this and press Enter:

   ```
   wsl --install -d Ubuntu
   ```

3. Restart your computer when it asks.

4. Click **Start**, type `Ubuntu` and open it. The first time, it asks you to invent a username and a password. When you type the password, nothing appears on screen. That is normal.

5. This black window is your terminal. Use it for every step below.

Tip: to paste into this window, right-click, or press Ctrl+Shift+V.

If it says "virtualization is turned off", your computer needs "Virtualization" switched on in its BIOS settings. Search for your computer model plus "enable virtualization".

### Mac

1. Press Cmd+Space, type `Terminal`, press Enter.

2. Type `brew --version`. If it says "command not found", go to https://brew.sh and run the one line shown there.

### Browser only (advanced): GitHub Codespace

Possible, but I have not tested it, and it stops when you stop using it. Skip this unless you cannot use Windows or Mac. If you go this way: drag the two files into the file list on the left, and run `harness start` every time you come back.

**Done when:** you have a terminal open with a blinking cursor.

---

## Step 2. Install the basic tools

This installs `git` (a code tool), `gh` (GitHub's helper), `python3`, `curl`, and `uv`.

**Windows (Ubuntu):**

```
sudo apt update
sudo apt install -y git curl python3 python3-venv gh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

`sudo` asks for the password you made in Step 1 (nothing shows as you type).

**Mac:**

```
brew install git gh python uv
```

Now run these three lines. They tell the terminal where to find the programs we install. (On Mac, write `.zshrc` instead of `.bashrc` in both lines.)

```
mkdir -p ~/.local/bin
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Check that everything is there:

```
git --version
gh --version
python3 --version
uv --version
```

**Done when:** each one shows a version number, and `python3` says **3.11 or higher** (3.12 is typical).

If `python3` says 3.10 or lower (an older Ubuntu): in PowerShell run `wsl --install -d Ubuntu-24.04`, open that Ubuntu instead, and repeat Step 2.

---

## Step 3. Put the two helper files in place

You downloaded two files from this chat: `model_scout.py` and `harness.sh`. Copy them into a folder called `harness`.

**Windows (Ubuntu):** first find your Windows user name:

```
ls /mnt/c/Users
```

It shows names like `Public` and your own. Use yours in place of `YOURNAME` below.

```
mkdir -p ~/harness
cp /mnt/c/Users/YOURNAME/Downloads/model_scout.py ~/harness/
cp /mnt/c/Users/YOURNAME/Downloads/harness.sh ~/harness/
```

**Mac:**

```
mkdir -p ~/harness
cp ~/Downloads/model_scout.py ~/Downloads/harness.sh ~/harness/
```

Then, on both:

```
chmod +x ~/harness/harness.sh
ln -sf ~/harness/harness.sh ~/.local/bin/harness
harness help
```

**Done when:** `harness help` shows a list of commands. From now on you can type `harness` plus a command, from any folder.

If your browser renamed the file (for example `harness (1).sh`), fix it with:

```
mv ~/harness/"harness (1).sh" ~/harness/harness.sh
```

---

## Step 4. Get your free AI keys

Make accounts on these free services and create a key on each. **Get at least two.** More services means more backups when one is busy.

**NVIDIA** (strong models, free for testing)

1. Go to https://build.nvidia.com and sign in (it may ask you to verify your phone number).

2. Open any model page and click **Get API Key** (or open your profile menu and choose **API Keys**).

3. Copy the key. It starts with `nvapi-`.

**OpenRouter** (many free models, about 50 uses per day)

1. Go to https://openrouter.ai and sign in.

2. Open https://openrouter.ai/keys and click **Create Key**.

3. Copy the key.

**Google AI Studio** (fast "Flash" models)

1. Go to https://aistudio.google.com and sign in.

2. Click **Get API key**, then **Create API key**.

3. Copy the key.

**Mistral** (a free coding model for a limited time)

1. Go to https://console.mistral.ai and sign up. Choose the free **Experiment** plan.

2. Open **API Keys** and click **Create new key**.

3. Copy the key.

Websites move their buttons around sometimes. Look for the words "API key".

Keep your keys handy for a moment. The next step saves them.

**Done when:** you have at least two keys copied somewhere you can reach.

---

## Step 5. Save your keys

```
harness setup-keys
```

It asks for each key. Paste the key and press Enter. Nothing shows on screen while you paste. That is normal. Press Enter on its own to skip a service you don't have.

**You should see:** "Saved to ... (only you can read it)" and a list showing `saved` for each key you entered.

It also makes a private password for your router. You never need to type that password yourself.

Never paste your keys into a chat, an email, or GitHub.

**Done when:** you see the "Saved" message.

---

## Step 6. Install the router

```
python3 -m venv ~/litellm-env
~/litellm-env/bin/pip install "litellm[proxy]"
```

The first line makes a private folder for the router's programs. The second downloads the router. It takes 3 to 6 minutes and a lot of text scrolls by. That is normal.

Check it worked:

```
~/litellm-env/bin/python -c "import litellm; print('router installed')"
```

**Done when:** it prints `router installed`.

---

## Step 7. Set up and test the model picker

The model picker finds free models that work well today and writes the router's list. We test it in three small steps, from safest to most real.

### 7a. Test the script itself (needs no keys, no internet)

```
harness selftest
```

**You should see:** a list of lines starting with `ok`, and at the very end `selftest passed`.

If you see `FAIL` or an error, stop here and send me the last 20 lines.

### 7b. Test your keys

```
harness check
```

This asks each service for its list of models. It uses almost none of your free allowance.

**You should see** something like this (yours will differ):

```
[OK]   nvidia: key accepted; 12 free models look usable (of 140 listed)
[OK]   openrouter: key accepted; 25 free models look usable (of 310 listed)
[skip] mistral: MISTRAL_API_KEY is not set
```

- `[OK]` means that service is ready.

- `[skip]` means you did not give a key for it. That is fine.

- `[FAIL]` with 401 or 403 means the key was refused. Run `harness setup-keys` and paste that key again.

You need at least one `[OK]` to go on. Two or more is better.

### 7c. First real run

```
harness scout
```

This takes the first look at the free models and **quick-tests** the best ones: a few tiny questions each, to see if they can use tools, read code and follow instructions.

- It takes **5 to 15 minutes** the first time. You will see lines like `tested nvidia:... tools ok, code 2/2, bugs 1/2`.

- It stops to rest if a service says "too many requests". That is fine.

- It tests only a few models per service on each run, to protect your free allowance. So the list gets better when you run it again, or each day when you run `harness start`.

**You should see** at the end a report with three jobs, each with one to three models. Yours will have different names and numbers:

```
## architect
1. nvidia:nvidia/nemotron-3-ultra-550b-a55b - score 0.71 (tests 0.8, hints 0.6, newness 0.9, size 0.7)
2. ...
## implementer
1. ...
## reviewer
1. ...
```

- The **architect** makes plans, the **implementer** writes code, and the **reviewer** checks code.

- The number is the order: 1 is the first choice, 2 and 3 are backups.

Read it any time with:

```
cat ~/harness/scout_report.md
```

**What good looks like:** every job has at least one model, and most jobs have models from two or more services.

### 7d. See that it remembers

Run it again right away:

```
harness scout
```

**You should see:** it finishes in seconds and says `No change in the picks.` That means it saved the test results and does not waste your free allowance.

**Done when:** all three jobs have models, and the second run is quick.

If a job says `EMPTY`, see **When something goes wrong** near the bottom.

---

## Step 8. Start the router and test it

```
harness start
```

**You should see:** `Router is running.` (It may also say the agent team is not installed yet. That is fine for now.)

Now ask a real question through the whole chain:

```
harness ask
harness ask reviewer "What is 2 + 2?"
```

**You should see** lines like:

```
Reply: Hello there, nice to meet you.
Answered by: nvidia:qwen/qwen3-coder-480b-a35b-instruct (first choice)
```

(If it says "backup number 1", the first choice was busy and the router quietly used the next one. That is the router doing its job.)

That means your keys, the model picker and the router all work together.

If you see an error, run `harness logs` and see **When something goes wrong**.

**Done when:** `harness ask` prints a `Reply:`.

---

## Step 9. Install the agent team (OAT)

This downloads the installer, then runs a fixed, tested version of it.

```
cd ~
curl -fsSL https://raw.githubusercontent.com/Root-IO-Labs/open-agent-teams/main/install.sh -o oat-install.sh
OAT_VERSION=v0.1.0 bash oat-install.sh
```

It takes 2 to 4 minutes.

(To read the installer before you run it: `less oat-install.sh`. Press `q` to leave.)

Check:

```
oat version
```

**Done when:** it shows `oat 0.1.0`.

If you see `tmpdir: unbound variable` at the very end, ignore it. It is a harmless cleanup message. What counts is that `oat version` works.

---

## Step 10. Sign in to GitHub

### 10a. Make a token that only works on the Gifscythe project

1. Go to https://github.com and click your profile picture (top right), then **Settings**.

2. In the left menu, scroll to the bottom and click **Developer settings**.

3. Click **Personal access tokens**, then **Fine-grained tokens**, then **Generate new token**.

4. Name it `gifscythe-ai-team`. Set **Expiration** to 90 days.

5. Under **Repository access**, choose **Only select repositories** and pick `gifscythe`. (If the project belongs to an organization, set **Resource owner** to that organization first.)

6. Under **Repository permissions**, set these three to **Read and write**:

   - **Contents**

   - **Pull requests**

   - **Issues**

7. Click **Generate token**. **Copy it now.** GitHub shows it only once. It starts with `github_pat_`.

Put a reminder in your calendar for 80 days from now to make a new one.

### 10b. Give the token to GitHub's helper

```
harness github-login
```

Paste the token and press Enter (nothing shows on screen).

**You should see:** `Logged in to github.com` and `OK: your token can see freeforall1932-design/gifscythe.`

**Done when:** you see that `OK` line.

---

## Step 11. Connect the agent team to the router

```
harness connect-oat
```

**You should see:** `Done. The agent team will now use the router.`

This tells OAT to talk to your router on your own computer, using the router's private password.

---

## Step 12. Start the team and add your project

```
harness start
oat init https://github.com/freeforall1932-design/gifscythe --model=litellm:architect
oat config gifscythe --mq-enabled=false
oat list
```

What each line does:

- `harness start` starts the router and the agent team.

- `oat init ...` adds your project. OAT makes its own copy of your code on this computer. It can take a minute.

- `oat config ... --mq-enabled=false` turns off the **auto-merge helper**, so nothing merges unless you press Merge yourself.

- `oat list` shows the projects OAT knows about. You should see `gifscythe`.

If OAT says it does not know `gifscythe`, run `oat list` to see the exact name it uses. If it says it does not know which project you mean, add `--repo gifscythe` to the end of the command.

**Done when:** `oat list` shows your project.

---

## Step 13. Run a first test task

```
oat worker create "Add one comment line at the very top of README.md that says: AI team test. Then open a pull request." --model litellm:implementer
oat worker list
oat ui
```

- `oat worker create` hands the task to a helper.

- `oat worker list` shows the helpers working.

- `oat ui` opens a live dashboard. Press **Ctrl+C** to leave it.

**You should see:** after about 5 to 15 minutes, a new pull request appears on your project on GitHub (open the **Pull requests** tab). Free services can be slow. That is normal.

Read it. This one was only a test, so **close it without merging**.

If nothing appears after 20 minutes: run `harness status` and `harness logs`, and see **When something goes wrong**.

**Done when:** a test pull request showed up on GitHub.

---

## Step 14. Teach the helpers your rules (skills)

A **skill** is a folder with one text file of instructions. The helpers read it before they work. You do not need to build or patch anything: OAT already knows how to load skills.

Add your first skill using the GitHub website:

1. Open your project on GitHub. Click **Add file**, then **Create new file**.

2. In the name box, type exactly this path (the slashes make the folders):

   ```
   .agents/skills/gifscythe-guardrails/SKILL.md
   ```

3. Paste this text into the big box:

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

4. Click **Commit changes**, then **Commit directly to the main branch**.

Helpers pick the skill up the next time they start a task.

Let a helper write a second skill for you:

```
oat worker create "Using the skill-creator skill, create .agents/skills/gifscythe-build that explains how to configure, build and test this project. Run every command you write down to check that it works. Then open a pull request." --model litellm:implementer
```

Review that pull request like any other and merge it if it looks right.

**Do I need to build my own harness to use skills and tools? No.**

- **Skills:** built in. Put them in `.agents/skills/` in your project.

- **Tools:** helpers can already run commands, read and write files, and fetch web pages. To give them a new ability, put a small script in a skill's `scripts` folder and describe it in the skill's text file.

- **MCP tools** (a plug-in format some AI tools use) are **not** supported by OAT. You will rarely need them. If you do, ask me. It needs a small patch.

**Done when:** the skill file is on your main branch.

---

## Step 15. Your daily routine

Start of a work session:

```
harness start
```

(If the model list is older than 12 hours, it refreshes the list first.)

Give a task:

```
oat worker create "describe the task here" --model litellm:implementer
```

Watch the helpers:

```
oat ui
harness status
```

Review: open your project on GitHub, **Pull requests** tab. Read the changes. Merge or close.

End of the session:

```
harness stop
```

Which `--model` to choose:

- `litellm:architect` for planning and research.

- `litellm:implementer` for writing code.

- `litellm:reviewer` for checking someone else's work.

---

## Step 16. Your Gifscythe worklist

**U-59/P0-7, GUI partial-write safety.** Three tasks, one after another:

```
oat worker create "Write a short plan for item U-59/P0-7 (GUI partial-write safety) as the file docs/plans/U-59-P0-7.md and open a pull request. Plan only, no code changes." --model litellm:architect
```

Merge the plan if it is good. Then:

```
oat worker create "Implement the plan in docs/plans/U-59-P0-7.md and open a pull request." --model litellm:implementer
```

When that pull request exists (replace 12 with its number):

```
oat worker create "Review pull request 12. Look for partial-write failure cases and missing tests. Leave comments only. Do not change any code." --model litellm:reviewer
```

**Wasm Option A vs B.** The helper writes a comparison. You decide:

```
oat worker create "Compare two options for the web version: (A) build gifsicle.wasm ourselves, (B) use the ready-made gifsicle-wasm-browser package. Write a one-page comparison as docs/decisions/wasm-option.md. Do not write code." --model litellm:architect
```

**W-18 and W-19.** These need a real Windows computer, so you run them. A helper can write the steps:

```
oat worker create "Write a step-by-step checklist for the clean-Windows smoke test (item W-18) as docs/tests/W-18.md and open a pull request." --model litellm:implementer
```

**U-09/P0-4, release re-cut.** Do this one yourself. Ask a helper for release notes only.

**OD-16, OD-18, version bump.** These are your decisions. The skill from Step 14 tells the helpers not to decide them.

---

## When something goes wrong

**`command not found` for `harness`, `oat` or `uv`**
Close the terminal and open a new one, or run `source ~/.bashrc`. If it is still missing, repeat the three PATH lines in Step 2.

**`harness check` shows `[FAIL]` with 401 or 403**
That key was refused. Run `harness setup-keys` and paste it again. Make sure you copied all of it.

**`harness check` says the free limit is used up**
Wait a while or try tomorrow. Add keys for more services (Step 4) so you have backups.

**`harness scout` says a job is `EMPTY`**
Run `harness check`. Make sure at least one service shows `[OK]`. Then run `harness scout` again. Each run tests a few more models.

**`harness scout` says it could not reach any AI service**
Check your internet connection and try again. On Windows, try closing Ubuntu, running `wsl --shutdown` in PowerShell, and opening Ubuntu again.

**The router will not start**
Run `harness logs`. If you changed your keys after starting it, run `harness stop` and then `harness start`.

**`harness ask` shows an error from the router**
Free services are sometimes busy. Wait a few minutes and try again. Or run `harness scout` to refresh the list.

**OAT says `not in a tracked repository`**
Do Step 12 (`oat init ...`), or add `--repo gifscythe` to the command.

**A helper cannot push or open a pull request**
Check the token. It needs **Read and write** for **Contents** and **Pull requests**, and it must be set for the `gifscythe` project. Make a new token (Step 10) and run `harness github-login` again.

**OAT says a model is "not onboarded"**
This means OAT's model safety check is switched on. Tell me and I will walk you through turning it off.

**Nothing happens after `oat worker create`**
Run `harness status`. If the router or the agent team is not running, run `harness start`. Then `harness logs`.

**You use a Codespace and it stopped**
Open it again and run `harness start`.

---

## Reference: the model picker

**What it does each time you run it**

1. Asks each AI service which models it offers.

2. Keeps only the free ones that can use tools (the helpers need that). It skips image, voice and "safety filter" models, and anything about to expire.

3. Quick-tests the best-looking new ones with six tiny questions each, and saves the results for 3 days.

4. Scores them for three jobs: **architect** (plans), **implementer** (writes code), **reviewer** (checks code). It likes newer models, spreads the picks over different services, and keeps the reviewer's first choice different from the implementer's.

5. Writes the router's list and a report. A model that disappears or runs out of free use drops out on the next run. A brand-new free model gets tested and can move up.

**Commands** (type `harness` first for the ones that exist there):

- `harness selftest` tests the script itself.

- `harness check` tests your keys and shows what it found.

- `harness scout` does the full run and restarts the router if the list changed.

- `harness status` shows the current picks.

**Where things are**

- `~/harness/scout_report.md` is the latest report.

- `~/harness/scout_state.json` is what it remembers.

- `~/.litellm/config.yaml` is the router's list (written for you).

- `~/harness/scout.yaml` holds your own settings. It is optional and does not exist until you make it.

**Lock in a model you trust** so it is always used for a job:

```
cat > ~/harness/scout.yaml <<'EOF'
pins:
  reviewer:
    - "nvidia:nvidia/nemotron-3-ultra-550b-a55b"
EOF
```

Then run `harness scout`. Use the form `service:model-name`, with the service one of `openrouter`, `nvidia`, `mistral`, `google`. A locked model is used as-is, so it is not quick-tested.

**Protect OpenRouter's small daily allowance** (stop the picker from using it for tests):

```
cat > ~/harness/scout.yaml <<'EOF'
probe:
  budget:
    openrouter: 0
EOF
```

(If you want both settings, put both blocks in one file, one after the other.)

**Run it on a schedule (optional).** `harness start` already refreshes the list when it is older than 12 hours. For a computer that stays on all the time, you can also add this with `crontab -e`:

```
0 6,18 * * * ~/.local/bin/harness scout >> ~/harness/scout.log 2>&1
```

**Good to know**

- The quick test is a smoke test, not a full exam. It catches models that cannot use tools, that have no free allowance, or that are clearly weak. It cannot tell two good models apart perfectly. Lock in the ones you trust.

- Free services change without warning. That is why it runs again and again.

---

## Notes: what was wrong in the first plan

You do not need this to follow the steps. Keep it for troubleshooting, or ask me about any line.

**Things that would not have worked**

- The OAT install link in the first plan belonged to a different project. This guide uses the real one from OAT's own page.

- OAT supports Mac and Linux. Its page says Windows is "not tested". That is why Windows users go through Ubuntu (WSL).

- The commands `oat task create`, `oat task status`, `--assign` and `--role` do not exist (I ran OAT to check). The real command is `oat worker create "task" --model ...`.

- The settings `OAT_MODEL_ENDPOINT` and `OAT_MODEL_API_KEY` do not exist anywhere in OAT. The real way is a short block in `~/.oat/config.toml`, which `harness connect-oat` writes. I tested that OAT's own model loader reaches a router this way.

- The router's "backup" rules were written so that only the first one counted. I tested this with the router's own code. They are now separate entries, and they never loop back on each other.

- The key-rotation tool in the first plan (`llm-keypool`) used a wrong flag name and does not support NVIDIA (I tested both). The router already rotates between services and rests a failing one (I tested that too), so the extra tool was dropped.

- OAT has a model safety check. After you "onboard" even one model, OAT demands that every model be onboarded and pass a score for its job. This guide avoids it by never onboarding.

**Safety problems**

- The router would have listened on every network connection and accepted any password. It now listens only on your own computer and needs its private password.

- OAT starts its helpers so they run commands without asking. So: a disposable place to run them, a token for one project only, and your AI keys are kept out of the helpers' environment (I checked this).

- OAT's auto-merge helper merges pull requests by itself unless turned off. Step 12 turns it off.

- The first plan mixed up GitHub token types: `ghp_` tokens are the old kind, new "fine-grained" ones start with `github_pat_`, and the permission names `repo` and `workflow` belong to the old kind. Typing a token into a command also leaves it in your history. `harness github-login` asks for it without showing it.

- The first plan told you to run an install script straight from the internet. This guide downloads it first, lets you read it, and fixes the version.

**Facts that were out of date or could not be confirmed**

- OpenRouter's free allowance is about 50 uses a day (1,000 a day only after buying at least $10 of credit), not 200. Extra accounts or keys do not raise it, so rotating several OpenRouter keys gains nothing.

- The Google free-allowance numbers in the first plan could not be confirmed. Google now shows the real numbers inside AI Studio.

- "Chutes: 200 calls a day" and "FHRouter" could not be confirmed. I found no trace of fhrouter.com. Don't send your code or keys through an unknown service. Both were left out.

- The "free" status of the three models named in the first plan is shaky. GLM-5.3-Flash exists but its maker's own service is paid, and I could not confirm a free OpenRouter listing. Devstral 2 is free for a limited, undated time. Nemotron 3 Ultra is a trial service. That is exactly why the model picker exists.

- Node.js 20 reached end of life in April 2026, and Node is not needed here.

**Design changes**

- Four layers became three: OAT, then the router, then the services. The model picker sits beside them.

- Three extras were dropped: `llm-keypool`, OmniRoute (both are key and service routers, not needed once LiteLLM is used) and Claw Orchestrator (it runs coding tools that need their own paid accounts, and it overlaps with OAT's dashboard and reviewers).

- OAT has no per-job model setting. You choose the model with `--model` for each task. `oat review` always uses the project's main model.

- OAT is a program that must keep running on some computer. That computer is yours, or a cloud computer you rent or borrow.

- W-18 and W-19 need real Windows hardware, and the release re-cut touches tags and releases, so those stay with you.

- The first plan was inconsistent in places: six services listed, "seven pools" promised, five in the picture, and some wired up while others were not. That is fixed.

---

## Notes: how the two helper files were checked

**`model_scout.py`**

- Run in my test area: `harness selftest` has 34 checks. They cover filtering, ranking, new models appearing, models disappearing, running out of free use, temporary errors, and a real fake AI service on your own computer to exercise the actual network code. The output router list is loaded by the real LiteLLM code, and a real router started from a generated list.

- Also tested on Python 3.10, 3.12 and 3.14, and checked with a code checker that found nothing.

- Problems I found in my own first version and fixed:

  - `--dry-run` with `--probe` would have spent free requests and thrown the results away. Now a dry run spends nothing.

  - A "maintenance" page from a service would have marked a good model unusable for a week. Now it only pauses that service.

  - Some services send tool details in a different shape. That crashed the test. Now handled.

  - A "403 forbidden" blocked a model for 7 days. Now 1 day.

  - Both bug-finding questions had the same answer, so a model that always said "5" passed both. Now different.

  - "Thinking" models could run out of room and look broken. Raised the answer limit.

  - A missing `~/.litellm` folder crashed it, and a half-written file could be read by the router. Now the folder is created and files are written safely.

  - A run with no internet could have saved empty results. Now it stops, says so, and changes nothing.

  - A typo in a locked-in model now gives a clear message. A damaged memory file is ignored safely.

  - It was silent for minutes. Now it prints progress. Added `--check`.

**`harness.sh`**

- I tested `setup-keys` (including pasting with stray spaces or quotes), `connect-oat` (including refusing to overwrite a settings file it did not write), `start`, `stop`, `status`, `ask` (through a real router to a test AI service), and `start` when the model list is old and there is no internet (it carries on with the old list).

**What I could not test**

- Your real accounts, and what the real AI services actually answer.

- The GitHub steps (`harness github-login` with a real token, `oat init`, helpers opening real pull requests).

- The Windows (WSL) and Mac install commands, and OAT inside a Codespace.

If any of these misbehave, send me the exact text on screen and I will fix it.

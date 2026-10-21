# Odysseus API model team kit — portable migration

Prepared 2026-10-18. This is the same live project formerly located under
workbench/projects/ai-team-kit, now renamed for download and migration. It
includes the existing harness source, built-in project-specific agent skills,
audits, worklist and handoff. **Renaming it does not implement the planned
Odysseus room/council, quota-aware provider pool or online Colab integration.**

## Download and copy

Download the repository ZIP and extract this whole folder, or download
**Odysseus API model team kit.zip** from the CI portable-dropins artifact.
Each archive contains a top-level folder of the same name and a SHA-256 file
manifest. Quote this folder name in shell commands because it contains spaces.

Copy the entire folder into your destination repository root. Do not overwrite
an existing directory without reviewing collisions. Record the source Dionysus
commit, destination commit and date in SESSION_HANDOFF.md. The original
workbench path remains a compatibility link in the testing repository only;
the downloadable root folder contains real files and needs no symlink.

Start with README.md, READING_GUIDE.md, SESSION_HANDOFF.md, the code audit and
WORKLIST.md. Historical workbench paths in old reports are provenance, not the
new copy layout. This folder is the team-kit project itself, unlike the two
other projects' support-only drop-ins.

## Dependencies and limits

| Operation | Requirements / limits |
|---|---|
| Read/migrate the project | No credentials, external services or installer needed |
| Syntax-check Python | Python 3.11+ recommended to match the installer requirement |
| Syntax-check shell scripts | Bash; runtime targets Linux/macOS/WSL, not native Windows Bash-less execution |
| Existing installer | git, curl, Python 3.11+, venv/ensurepip, gh; installs uv if missing, LiteLLM proxy and OAT |
| Router | litellm[proxy] in a virtual environment; installer does not pin its version |
| Agent team | OAT installer fetched remotely; default requested OAT version is v0.1.0, not a fully locked supply chain |
| Optional scout YAML config | PyYAML; inspect model_scout.py for optional-import behavior |
| Live provider use | Your own provider accounts/keys, compatible endpoints, current terms and quota/free-tier verification |
| GitHub operations | Authenticated gh on your machine, appropriate permissions and owner review before merge |
| Planned Odysseus/Colab work | Still tracked in the worklist; not dependencies automatically installed by this ZIP |

The companion KoboldCpp notebook remains a separate project under the testing
repository's workbench. It is **not included in this team-kit ZIP** and is not
required for syntax checks or the existing harness source. Consult the current
worklist before relying on its endpoint.

## Safe checks after copying

From the destination repository root, without installing anything or contacting
providers:

```sh
python3 -m compileall -q "Odysseus API model team kit/kit/harness"
bash -n "Odysseus API model team kit/kit/harness/install.sh"
bash -n "Odysseus API model team kit/kit/harness/harness.sh"
```

These checks prove syntax only. The archived scout self-test evidence and its
skipped LiteLLM checks remain historical; do not relabel them as a new live test.

## Installation is a separate, explicit owner decision

Do not run install.sh just to migrate. First read GUIDE.md under kit/harness,
review the audit's fix-before-trust issues and choose a worklist item. The
installer changes shell startup files, creates user directories/symlinks,
installs Python dependencies, downloads remote installers, and installs built-in
skills. It is not a read-only check and its dependencies are not fully locked.
Use a normal dedicated user and review/pin downloaded code before trusting it.

The old launchers assume a harness installation in the home directory; changing
the migration folder's name does not change those runtime paths or the existing
Gifscythe-specific defaults. For a future reviewed install, the source supports
HARNESS_DIR and LITELLM_VENV overrides. In a POSIX shell the location can be set
explicitly, without pretending that relocation itself ran the installer:

```sh
export HARNESS_DIR="$PWD/Odysseus API model team kit/kit/harness"
# Only AFTER review and explicit approval:
# bash "$HARNESS_DIR/install.sh"
```

Keep that environment consistent for subsequent harness commands; inspect the
existing command defaults before configuring a different repository. Do not
blindly use the old double-click launchers for a custom install location.
Never commit keys.env, tokens, provider credentials, runtime logs or scout
state. Keep runtime state outside the migration source, and never package a
used runtime directory as a clean source distribution. The provided dashboard
is loopback-only; do not expose it publicly to make a remote preview work.

## Skills after migration

The nested kit/harness/skills files are project-specific runtime assets; retain
them with the harness, not as competing copies of the root reusable catalog.
Optionally copy the separate skills drop-in to the destination root and append
its INSTALL.md loader to existing agent instructions. Use the universal process
layer; the Qt and Lua workload lanes do not match this Python/Bash kit.

**Not verifiable here:** live installation, provider quotas/keys, router and OAT
compatibility, Odysseus integration, model quality and an actual Colab endpoint.
This migration preserves existing code and evidence; it does not resolve the
known audit findings or authorize model calls, service startup or PR merges.

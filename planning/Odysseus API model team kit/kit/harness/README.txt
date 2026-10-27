AI TEAM KIT
===========
A small team of AI helpers that works on your GitHub project. You review and merge what they do.

What is in this folder
  install.sh        one-time installer (run:  bash ~/harness/install.sh)
  harness.sh        the "harness" command (start, stop, keys, models, doctor, ...)
  model_scout.py    picks the best free AI models every day
  harness_ui.py     the dashboard (opens in your browser, runs only on your computer)
  skills/           built-in skills the helpers read (project workflow, self-extend)
  windows/          double-click Start / Stop files for Windows
  mac/              double-click Start / Stop files for Mac

Quick start (after unzipping into your home folder)
  bash ~/harness/install.sh
  harness setup-keys
  harness github-login
  harness connect-oat
  harness start
  harness add-repo https://github.com/OWNER/NAME
  harness open

Something not working?   harness doctor
Everything is explained step by step in the setup guide.

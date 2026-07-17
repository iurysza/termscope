# Publishing Termscope

Termscope is published as a Herdr plugin from the repo root.

## One-time GitHub repo setup

```bash
gh repo edit iurysza/termscope \
  --description "Open files and links already visible on your terminal screen." \
  --homepage "https://github.com/iurysza/termscope"

gh repo edit iurysza/termscope \
  --add-topic herdr-plugin \
  --add-topic herdr \
  --add-topic television \
  --add-topic tmux \
  --add-topic terminal \
  --add-topic python
```

The `herdr-plugin` topic is what makes the repo eligible for the Herdr plugin
marketplace index.

## Release checklist

1. Update `version` in `herdr-plugin.toml`.
2. Update `CHANGELOG.md`.
3. Run checks:

   ```bash
   python3 -m py_compile termscope termscope_herdr.py
   python3 -m unittest discover -s tests
   herdr plugin link "$PWD"
   herdr plugin action list --plugin termscope
   ```

4. Commit and tag:

   ```bash
   git add .
   git commit -m "chore: prepare Termscope release"
   git tag v0.2.0
   git push origin main --tags
   gh release create v0.2.0 --title "v0.2.0" --notes-file CHANGELOG.md
   ```

## Install smoke test

On a clean machine or temp user profile:

Start with Television absent or older than `0.15`, but with Homebrew available:

```bash
herdr --version  # 0.7.4+
herdr plugin install iurysza/termscope
tv --version     # now 0.15+
herdr plugin action list --plugin termscope
```

Also verify installation aborts before registration when Homebrew is absent.

Then add keybindings from the README and run:

```bash
herdr server reload-config
```

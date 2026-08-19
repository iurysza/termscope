# Publishing Termscope

Termscope is published as a source-only Herdr plugin from the repo root. Releases use [Release Please](https://github.com/googleapis/release-please) to update the version files and changelog, create the Git tag, and publish the GitHub Release.

`version.txt` is the version source of truth. Each release PR keeps `version.txt`, `herdr-plugin.toml`, and `.release-please-manifest.json` aligned.

## One-time GitHub repository setup

Keep the repository metadata and marketplace topics configured:

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

The `herdr-plugin` topic makes the repository eligible for the Herdr plugin marketplace index.

Create a fine-grained personal access token with `contents:write` and `pull-requests:write` access to this repository. Add it to the repository's Actions secrets as `RELEASE_PLEASE_TOKEN`.

Release Please must use this token instead of the default `GITHUB_TOKEN` so its release PRs and tags trigger the repository's normal workflows.

## Cut a release

1. Merge changes to `main` using Conventional Commits:
   - `fix:` selects a patch release.
   - `feat:` selects a minor release.
   - `feat!:` or a `BREAKING CHANGE:` footer selects a major release.
2. Wait for the `Release Please` workflow to open or update its release PR.
3. Review the generated version changes and `CHANGELOG.md`, and confirm CI passes.
4. Merge the release PR.
5. The next `Release Please` workflow run creates the `vX.Y.Z` tag and matching GitHub Release.

Do not create or force-push release tags by hand. Fix release problems on `main` and cut a new patch release.

Termscope ships as source. There are no package artifacts or release assets to build or upload. Herdr checks out the selected Git ref, reads `herdr-plugin.toml`, and runs its install-time build command.

Install a specific release by tag:

```bash
herdr plugin install iurysza/termscope --ref vX.Y.Z
```

## Install smoke test

On a clean machine or temporary user profile, start with Television absent or older than `0.15`, but with Homebrew available:

```bash
herdr --version  # 0.7.4+
herdr plugin install iurysza/termscope --ref vX.Y.Z
tv --version     # now 0.15+
herdr plugin action list --plugin termscope
```

Also verify installation aborts before registration when Homebrew is absent.

Then add the keybindings from the README and run:

```bash
herdr server reload-config
```

// Termscope Links: open the picker in a floating pane over the focused terminal.
// owner: termscope (rendered by scripts/install-herdr-app.sh; removed on --uninstall)
// Opened by a key as a 1x1 headless overlay. Nothing is drawn.

import { View, div } from "gpui-kit";
import { exec, focused, notify, props, closeOverlay } from "herdr";

const TITLE = "Termscope Links";
// `exec` already provides the user environment. Do not pass `env -i`: that
// drops TERMSCOPE_* and the session variables herdr-ui and hc use to find the
// running app. Pin only the tool paths recorded at install.
const COMMAND = ["/usr/bin/env",
  "HC_BIN_PATH=@@HC@@", "HERDR_APP_BIN_PATH=@@HERDR_APP@@", "HERDR_UI_BIN=@@HERDR_UI@@",
  "@@PYTHON@@", "@@LAUNCHER@@", "--open-links"];

async function launch(terminal, cwd) {
  try {
    const args = [...COMMAND.slice(1), "--terminal", terminal];
    if (cwd) args.push("--cwd", cwd);
    const r = await exec(COMMAND[0], args, { cwd: cwd || "@@HOME@@" });
    if (r.code !== 0) {
      const err = (r.stderr || r.stdout).trim().split("\n").filter(Boolean).slice(-2).join(" ");
      notify({ title: TITLE + " failed", body: err || `exit ${r.code}`, level: "error", timeout: 8000 });
    }
  } catch (e) {
    notify({ title: TITLE + " failed", body: String(e?.message ?? e), level: "error", timeout: 8000 });
  }
}

export default class Termscope extends View {
  init(_props, cx) {
    const overlay = props()?.overlay;
    const f = focused();
    const close = () => { if (overlay) closeOverlay(overlay); };
    if (!f?.terminal) {
      notify({ title: TITLE, body: "No focused terminal", level: "warning", timeout: 3000 });
      close();
      return;
    }
    // This task belongs to the overlay. Closing first drops the view and
    // cancels exec before it runs, and the failure notify is lost with it.
    cx.spawn(async () => {
      await launch(f.terminal, f.cwd);
      close();
    });
  }

  render() {
    return div().id("root").size(1);
  }
}

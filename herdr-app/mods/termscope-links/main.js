// Termscope Links: open the picker in a floating pane over the focused terminal.
// owner: termscope (rendered by scripts/install-herdr-app.sh; removed on --uninstall)
// Opened by a key as a 1x1 headless overlay. Nothing is drawn.

import { View, div } from "gpui-kit";
import { exec, focused, notify, props, closeOverlay } from "herdr";

const TITLE = "Termscope Links";
const COMMAND = ["/usr/bin/env", "-i", "HOME=@@HOME@@", "PATH=@@PATH@@",
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
    if (!f?.terminal) notify({ title: TITLE, body: "No focused terminal", level: "warning", timeout: 3000 });
    else cx.spawn(async () => { await launch(f.terminal, f.cwd); });
    if (overlay) closeOverlay(overlay);
  }

  render() {
    return div().id("root").size(1);
  }
}

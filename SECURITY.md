# Security

Termscope reads visible terminal text and local filesystem paths. It does not
send data to a network service.

Things to know:

- It indexes files under the current git root with `fd`.
- It opens selected files with `nvim` or the configured/default opener.
- It opens selected URLs with the configured/default opener.
- `Ctrl-Y` in the file picker sends a `/plannotator-annotate <file>` command to
  the source pane.

If you find a vulnerability, open a private GitHub security advisory or contact
the repository owner directly.

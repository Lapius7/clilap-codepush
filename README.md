<div align="center">

<p align="center">
  <img src="docs/images/banner.png" alt="Codepush CLI" width="100%">
</p>

<p align="center"><b>English</b> | <a href="README.ja.md">日本語</a></p>

<h1 align="center">Codepush CLI</h1>

<h3 align="center">Upload, fetch and manage files from your terminal.</h3>

<p align="center">CLI client for <a href="https://codepush.clilap.org">codepush.clilap.org</a>. Upload, fetch and manage files from an interactive terminal UI.</p>

<p align="center">
  <a href="https://github.com/Lapius7/clilap-codepush/releases"><img alt="Release" src="https://img.shields.io/github/v/release/Lapius7/clilap-codepush?label=release&style=flat-square&color=e8833a&logo=github"></a>
  <a href="https://www.npmjs.com/package/@lapius/clilap-codepush"><img alt="npm" src="https://img.shields.io/npm/v/@lapius/clilap-codepush?style=flat-square&color=cb3837&logo=npm"></a>
  <a href="https://pypi.org/project/clilap-codepush/"><img alt="PyPI" src="https://img.shields.io/pypi/v/clilap-codepush?style=flat-square&color=3776ab&logo=pypi&logoColor=white"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/github/license/Lapius7/clilap-codepush?style=flat-square&color=97ca00"></a>
  <a href="https://github.com/Lapius7/clilap-codepush/stargazers"><img alt="Stars" src="https://img.shields.io/github/stars/Lapius7/clilap-codepush?style=flat-square&color=e3b341&logo=github"></a>
  <a href="https://github.com/Lapius7/clilap-codepush/commits/main"><img alt="Last commit" src="https://img.shields.io/github/last-commit/Lapius7/clilap-codepush?label=last%20commit&style=flat-square&color=2f81f7"></a>
</p>

<p align="center"><a href="#install">Install</a> · <a href="#usage">Usage</a> · <a href="#features">Features</a> · <a href="#managing-your-files">Managing your files</a> · <a href="#environment-variables">Environment variables</a> · <a href="#troubleshooting">Troubleshooting</a></p>

</div>

---

## Install

Use pnpm. Installing with both npm and pnpm registers the same command twice, so use `pnpm add -g` only.

```bash
pnpm add -g @lapius/clilap-codepush
```

This installs the `codepush` command. It needs Node.js 18+ and Python 3.9+. To update, run `pnpm add -g @lapius/clilap-codepush@latest`.

With pip, run:

```bash
pip install clilap-codepush
```

To update, use `--upgrade`. A plain `pip install` does not raise the version of an installed package.

```bash
pip install --upgrade clilap-codepush
```

To keep the global environment clean, use [pipx](https://pipx.pypa.io/): `pipx install clilap-codepush` and `pipx upgrade clilap-codepush`.

## Usage

### Interactive menu (recommended)

```bash
codepush
```

Pick an item with the arrow keys and press Enter. Ctrl+C quits.

### Command line

```bash
codepush upload <file>   # upload a file
codepush get <id>        # print a paste to stdout
codepush myfiles         # manage your uploaded files (alias: my)
codepush delete          # opens the same screen as myfiles
codepush diff            # diff two pastes
codepush health          # check the server
codepush version         # show the version (-v, --version)
codepush help            # show help
```

## Features

| Feature | Description |
| --- | --- |
| Upload | Text, code, zip and more. Expiry is selectable: never, 1 hour, 1 day, 7 days, 30 days or custom. |
| Download | Fetch a file by ID to stdout or to a file. |
| My files | List, inspect, delete, overwrite and check whether each file still exists on the server. |
| Diff | Show the difference between two pastes in color. |
| Health | Check server status, database status and the total file count. |
| Folder upload | Upload a tar.gz or zip and share it as a file tree. |
| Password protection | Set a password on upload and require it on download. |

## Managing your files

`codepush myfiles` (or "My files" in the menu) lists your upload history.

- Opening the list checks in parallel, in the background, whether each file still exists on the server (not deleted, not expired).
- A file missing from the server is shown with its **ID and name in red**, and its detail screen cannot be opened.
- Press `r` to run the check again.
- Press `d` to delete and `u` to overwrite (re-upload).

The list is only what is recorded in the local `keys.json` (see below). The check exists so that files already deleted or expired on the server can be told apart on screen.

## Custom expiry

```
3d12h     # 3 days 12 hours
2h30m     # 2 hours 30 minutes
90m       # 90 minutes
7200s     # 7200 seconds (= 2 hours)
7200      # a bare number is read as seconds
```

## Admin key

The admin key (`delete_key`) issued at upload is saved automatically to `~/.config/clilap-codepush/keys.json`. You can delete or overwrite from the "My files" menu.

Examples with curl are below.

```bash
# overwrite
curl clilap.org/cp/<id> -F file=@new.py -F key=<delete_key>

# delete
curl clilap.org/cp -X DELETE -d key=<delete_key>

# stats
curl clilap.org/cp/stats/<id>
```

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `CODEPUSH_URL` | `https://codepush.clilap.org` | Base URL of the API |

## Requirements

- Python 3.9+
- Windows, macOS and Linux (including WSL)
- Clipboard copy: `xclip`, `xsel` or `wl-copy` (Linux), `pbcopy` (macOS), built in on Windows
- No extra dependencies (standard library only)

> [!NOTE]
> Folder upload and password protection are carried over from the old README. Neither could be confirmed in this client's code, so they are unverified here and may be handled by the server. Commands that talk to the server were not run for this rewrite.

## Troubleshooting

**The version is old after `pip install`.** `pip install` does not check the version of an installed package. Use `pip install --upgrade clilap-codepush`.

**The `codepush` command is not found.** Check that Python's `Scripts` directory (Windows) or `bin` directory (macOS and Linux) is on your PATH.

**pip asks for `--break-system-packages`.** This happens on Debian and Ubuntu when installing into the system Python is restricted. Use `pipx` as above, or add `--break-system-packages`.

## License

MIT ([LICENSE](LICENSE))

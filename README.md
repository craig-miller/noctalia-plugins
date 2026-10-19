# noctalia-plugins

[Noctalia](https://github.com/noctalia-dev/noctalia-shell) plugins by Craig Miller for a Wayland desktop on Apple Silicon running Asahi Linux. Companion system packages are available through [gentoo-overlay](https://github.com/craig-miller/gentoo-overlay).

## Plugins

| Plugin | Purpose | Requires |
| --- | --- | --- |
| `craig-miller/ndi_sender` | Bar tile + control-center shortcut to broadcast the desktop as an NDI source on the LAN | `app-misc/ndi-cast` (gentoo-overlay) |
| `craig-miller/next_event` | Bar widget that shows the next timed event from Noctalia's configured vdir calendars | `app-misc/khal` |

## Install

Add this repo as a Noctalia plugin source:

```
noctalia msg plugins source add noctalia-plugins-release git https://github.com/craig-miller/noctalia-plugins
```

Enable a plugin:

```
noctalia msg plugins enable craig-miller/ndi_sender
noctalia msg plugins enable craig-miller/next_event
```

Then add the widget through `Settings → Bar widgets`, or wire the control-center shortcut through `Settings → Control Center`.

## Compatibility

Tracks `gui-apps/noctalia-shell` in [gentoo-overlay](https://github.com/craig-miller/gentoo-overlay). Minimum supported Noctalia version is declared per-plugin via each plugin's `plugin.toml` `min_noctalia` field. The Noctalia v5 plugin API is upstream-flagged experimental, so a plugin may need a refresh on each Noctalia pin bump.

## License

[MIT](LICENSE).

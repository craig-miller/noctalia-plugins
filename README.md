# zentoo-noctalia-plugins

[Noctalia](https://github.com/noctalia-dev/noctalia-shell) Tier 4 plugins built for the [zentoo](https://github.com/craig-miller/zentoo) Wayland substrate on Apple Silicon Asahi Linux. Each plugin pairs the Noctalia shell with a system-level package shipped from the [zentoo-overlay](https://github.com/craig-miller/zentoo-overlay).

## Plugins

| Plugin | Purpose | Requires |
| --- | --- | --- |
| `zentoo/ndi_sender` | Bar tile + control-center shortcut to broadcast the desktop as an NDI source on the LAN | `app-misc/ndi-cast` (gentoo-overlay) |

## Install

Add this repo as a Noctalia plugin source:

```
noctalia msg plugins source add zentoo git https://github.com/craig-miller/zentoo-noctalia-plugins
```

Enable a plugin:

```
noctalia msg plugins enable zentoo/ndi_sender
```

Then add the widget through `Settings → Bar widgets`, or wire the control-center shortcut through `Settings → Control Center`.

## Compatibility

Tracks `gui-apps/noctalia-shell` in the zentoo overlay. Minimum supported Noctalia version is declared per-plugin via each plugin's `plugin.toml` `min_noctalia` field. The Noctalia v5 plugin API is upstream-flagged experimental, so a plugin may need a refresh on each Noctalia pin bump.

## License

[MIT](LICENSE).

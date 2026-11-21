# Quiet Tizen

A practical, agent-readable guide to making a Samsung Tizen TV quieter and
more useful as an HDMI display.

This project documents work performed on two Samsung Tizen TVs:
- **Samsung UN75U8000FFXZA (2025 75" U8000F)** running Tizen 9.0 (`T-KSU2EFAKUC-0090-1300.9`)
- **Samsung QN75Q90TAFXZA (2020 75" Q90T QLED)** running Tizen 5.5 (`T-NKMAKUC-2743.0`)

It includes **Quiet Home**, a native launcher with a colorful,
English-language interface, Dark/Light Mode theme support, lightweight quick
settings, live sound output device switching, local app cards and a shortcut to
native Bluetooth controller pairing.

![Quiet Home layout illustration](docs/quiet-home-preview.svg)

*Layout illustration with the public text-only app cards. Input labels are configurable.*

It also includes targeted cleanup profiles, source-build tools and rollback
recipes. **It is a working case study with a reusable toolkit, not a universal
installer or a replacement operating system.**

## Give this repository to your coding agent

Clone the repository, open it in Codex, and use:

> Read README.md and AGENTS.md, then inspect the documentation before touching
> my TV. Help me reproduce Quiet Tizen on a TV I own. First identify its exact
> model, firmware and runtime, compare them with the tested profile, and show
> me any compatibility gaps. Keep HDMI, sound, networking, Bluetooth and
> accessibility working. Prefer HDMI and minimize smart features; keep the
> streaming apps I choose. Back up my actual settings and prepare rollback
> before each change. Install and verify Quiet Home before assigning it to
> Home/startup or replacing the slow settings sidebar. Use the measured
> findings and known limitations rather than assuming every package is spyware
> or promising a particular speed improvement.

If your TV differs, begin with an inventory. A matching brand, year, Tizen
version or successful root check is **not** enough to establish launcher or
cleanup compatibility.

## What is here

| Component | What it does |
|---|---|
| [Quiet Home source](launcher/src/Home.cs) | Native .NET/NUI home, HDMI cards, app library and quick settings |
| [App catalog](launcher/assets/apps.json) | Example shortcuts for Netflix, YouTube, Prime Video, HBO Max, Disney+, Hulu, Spotify, Apple TV, Tubi, Luna and Xbox |
| [Artwork tools](docs/06-artwork.md) | Vector/high-resolution artwork sources, optional local downloads and retained image views |
| [Cleanup profile (U8000F)](profiles/un75u8000ffxza-1300.9.json) | Separately selectable advertising, voice, context, smart-extras, sidebar and TV Plus groups for Tizen 9.0 |
| [Cleanup profile (Q90T)](profiles/qn75q90tafxza-2743.0.json) | Separately selectable cleanup groups for `QN75Q90TAFXZA` (`T-NKMAKUC-2743.0`, Tizen 5.5) |
| [Tizen 5.5 TPK builder](tools/build_tizen55_tpk.py) | Standalone Partner-signed TPK builder with Dark Mode, focus highlight rings, Sound Output selector, and `DotnetPolicyChecker` stubs |
| [Cleanup planner](tools/plan_cleanup.py) | Field-specific apply/restore SQL generated from your own fresh snapshot |
| [Access helper](tools/tv.py) | Explicit-target SDB preflight, temporary authenticated root, bounded transfers and session cleanup checks |
| [Recipes](recipes) | Snapshot, stop-marker, launcher, settings-bridge and restoration scripts |
| [Evidence (U8000F)](evidence/observations.json) | Sanitized observations and the limits of what was verified on `UN75U8000FFXZA` |
| [Evidence (Q90T)](evidence/observations-qn75q90tafxza.json) | Sanitized observations and memory measurements on `QN75Q90TAFXZA` (`T-NKMAKUC-2743.0`) |

Quiet Home uses Tizen's existing display, audio, HDMI and application stack.
It can become the default Home/startup experience; Samsung's underlying OS
continues to run. The TV does not need a laptop running after installation.
Root access is reacquired from the computer when maintenance requires it.

## Tested scope and current status

| Item | `UN75U8000FFXZA` (2025 U8000F) | `QN75Q90TAFXZA` (2020 Q90T QLED) |
|---|---|---|
| Firmware | `T-KSU2EFAKUC-0090-1300.9` | `T-NKMAKUC-2743.0` (`B1052220/B60101 , BT - S`) |
| Platform | Tizen 9.0, Linux 5.4.261, ARMv7; .NET 6.0.9 | Tizen 5.5, Linux 4.9.185, ARMv7; .NET Core 3.1.0 |
| Access / DB Modification | Temporary UID/EUID 0 (`CVE-2022-26330`) | `uid=901(sdk)`, `context="System"`, group `1051(system_share)` + `User::Home` transmute staging (`CVE-2022-26330` patched) |
| Launcher Packaging | Replaced `BixbyPromotion.dll` in `com.samsung.tv.bixby-promotion` | Standalone Partner-signed TPK (`org.quiettizen.home`) with managed `DotnetPolicyChecker` P/Invoke whitelist stubs |
| Home & Startup | Verified after full restart | Verified after full restart (`XF86Home`, `XF86Display`, `XF86SysMenu`, `XF86More`, `app_onboot='true'`) |
| Home Button Toggle | Opens Quiet Home | Opens Quiet Tizen when closed; closes back to current HDMI input when already open (`on_selector='~with-package:org.quiettizen.home'`) |
| Inputs & Everyday Controls | HDMI 1–3 (`13..15`), volume, mute, brightness, Game Mode, sleep timer | HDMI 4 PC Monitor (`16`), HDMI 2 Consoles (`14`), HDMI 1 Chromecast (`13`), HDMI 3 eARC Soundbar (`15`), volume, mute, brightness, Game Mode, sleep timer |
| Sound Output Selector | Native settings shortcut | Live selector on Home dock & Quick Settings cycling `HDMI eARC (2)` $\rightarrow$ `TV Speaker (0)` $\rightarrow$ `Optical (1)` |
| Voice Control | Disabled in case study | Retained with live UI toggle tile (`db/si_service/voice_recog_enable` & `db/multi-assistant/prelaunch_mode`) |
| Theme & Focus UI | Light theme (`Free My TV` palette) | Dark Mode default + Light Mode toolbar toggle, `Quiet Tizen` 512×512 icon, and double-stroke vector focus highlight rings (`#38BDF8` + `#FFFFFF`) |
| Cleanup & Memory | 54 app records disabled; `MemAvailable` `~509 MiB` $\rightarrow$ `~921 MiB` | 20 app records disabled across 5 snapshotted phases (`voice` retained); `MemAvailable` `479 MiB` $\rightarrow$ `621 MiB`, `SwapUsed` `854 MiB` $\rightarrow$ `588 MiB` after restart |

## Specific Changes & Adaptations for `QN75Q90TAFXZA` (Tizen 5.5, `T-NKMAKUC-2743.0`)

Full architectural details are documented in [docs/10-qn75q90tafxza-tizen55.md](docs/10-qn75q90tafxza-tizen55.md):

1. **Database Updates Without UID 0 (`system_share` & `User::Home` Transmute)**:
   - On 2026 firmware `T-NKMAKUC-2743.0`, `CVE-2022-26330` is patched. Because `/opt/dbspace` is `0775 root:system_share` (no sticky bit) and the Developer Mode SDB foothold runs in group `1051(system_share)` with SMACK label `System`, `.app-context.db` and `.pkgmgr_parser.db` are staged in `/opt/usr/home/owner/.applications/dbspace` (`access="User::Home" transmute="TRUE"`, `PRAGMA journal_mode = PERSIST;`, `umask 000`) and moved atomically into `/opt/dbspace/` while preserving `.orig` inodes.
2. **Standalone Partner-Signed TPK (`org.quiettizen.home`) & `DotnetPolicyChecker` Stubs**:
   - Built via [tools/build_tizen55_tpk.py](tools/build_tizen55_tpk.py). Bundles five tiny managed stub `.dll` assemblies (`libsource-api.dll`, `libvconf.dll`, `libcapi-media-sound-manager-tv.dll`, `libsettings-api.dll`, `libcapi-appfw-app-control.dll`) in `bin/` and `lib/` so `DotnetPolicyChecker.WhiteListManager.AddAppDllAndSoFilesToWhiteList` registers their strong names while CoreCLR P/Invokes the genuine `/usr/lib/*.so` system libraries (`_` SMACK label).
   - Uses a reflection-free JSON catalog parser (`AppLibrary`) and safe `IntPtr` string marshaling for `libsettings-api.so` (`CSharpGetItemValue`).
3. **UI Features Added**:
   - **Dark Mode UI** by default with a persistent Light/Dark Mode toggle button in the top-right toolbar.
   - **Custom `Quiet Tizen` 512×512 app icon** on the Tizen Apps screen and clean **PC Monitor (`HDMI 4`)** hero card (with `"Ready to work."` removed).
   - **High-Contrast Vector Focus Highlight Rings**: SVG focus overlays (`focus-hero.svg`, `focus-portrait.svg`, `focus-dock.svg`, `focus-tile.svg`, `focus-app.svg`, `focus-toolbar.svg`) with an outer `#38BDF8` glow and inner `#FFFFFF` border around every selectable UI element, plus highlighted card captions and top navigation tab pills.
   - **Sound Output Device Selector on Home Menu & Quick Settings**: Displays and cycles the active audio output directly between **`HDMI eARC` (`2`) $\rightarrow$ `TV Speaker` (`0`) $\rightarrow$ `Optical` (`1`)** using `libcapi-media-sound-manager-tv.so.0` (`sound_manager_get/set_speaker_selection`) and `libsettings-api.so` (`soundoutput`).
   - **Voice Control UI Toggle**: Toggles voice recognition on/off from the Home dock or Quick Settings while keeping voice packages installed.
4. **Remote Key Routing & HDMI Source-Switching Fixes**:
   - **Home Button (`XF86Home`) Open/Close Toggle**: Configured `key_filter` in `/opt/dbspace/.app-context.db` with `on_selector='~with-package:org.quiettizen.home'` so pressing **Home** opens Quiet Tizen when watching HDMI/apps, and closes Quiet Tizen back to the active HDMI input when Quiet Tizen is already in the foreground without `tvctx-manager` immediately re-launching it.
   - **Prevented Samsung Source-Switching Banner (`CSourceSwitchBanner`) Hang on Close**: `org.tizen.tv-viewer` ignores `CSourceSwitchBanner::t_Hide` when unfocused (`"Ignore to hide when video window focus out"`). Added `CloseLauncher()` (and guarded `SelectSource(int source)` against `vconf_get_int("memory/system/source_type", out cur)`) so closing Quiet Tizen or selecting the already-active HDMI card raises `org.tizen.tv-viewer` directly without calling `connect_source`, and actual input changes raise `org.tizen.tv-viewer` before calling `connect_source`.

## Walkthrough

1. [Understand compatibility and inventory the TV](docs/01-inventory.md).
2. [Enable Developer Mode and check temporary access](docs/02-access.md).
3. [Take snapshots and apply selected cleanup](docs/03-cleanup.md).
4. [Build, install and assign Quiet Home](docs/04-launcher.md).
5. [Pair a DualSense using the TV's Bluetooth support](docs/05-controller.md).
6. [Customize apps, fetch artwork and keep it preloaded](docs/06-artwork.md).
7. [Diagnose slow streaming apps without overclaiming](docs/07-performance.md).
8. [Understand privacy findings](docs/08-privacy.md).
9. [Restore the original experience](docs/09-recovery.md).
10. [Reproduction on Samsung QN75Q90TAFXZA (Tizen 5.5, `T-NKMAKUC-2743.0`)](docs/10-qn75q90tafxza-tizen55.md).

Read [AGENTS.md](AGENTS.md) before using the tools. TV commands require a
specific address and a verified firmware declaration. All downloaded
proprietary references, local artwork, snapshots and session records stay
under ignored paths.

## Development

Host tools use Python 3.12+ and the standard library. Raster artwork conversion
optionally uses Pillow. Source builds use the .NET 6 SDK to match the tested
TV; it is an older SDK and should be isolated from unrelated projects.
Install Samsung's SDB separately.

```sh
python3 -m unittest discover -s tests -v
python3 tools/build.py payloads
# After obtaining the four private Tizen reference assemblies:
python3 tools/build.py launcher --framework .local/tv-framework
```

GitHub Actions runs the offline tests and builds the open-source access
payloads and app-catalog tests. The NUI launcher build needs Samsung reference
assemblies and is deliberately not built from redistributed SDK files.

## Credits

The visual design adapts [Free My TV](https://github.com/simbasjungles/free-my-tv);
the temporary archive-launcher access route comes from
[samsung-tv-root](https://github.com/chris-ritsen/samsung-tv-root).
This is a native Tizen port of the visual approach, not an installation of
the Android launcher. See [NOTICE.md](NOTICE.md) and
[provenance](docs/provenance.md) for exact commits, licenses and local changes.

Original project code is MIT-licensed. Third-party fonts, symbols and access
code retain their own licenses. No Samsung firmware, stock app binaries,
private TV backups or publisher app artwork is included.

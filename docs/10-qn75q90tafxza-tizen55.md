# Reproduction on Samsung QN75Q90TAFXZA (Tizen 5.5, Firmware `T-NKMAKUC-2743.0`)

This document records the adaptations, architecture, UI features, and verified findings from reproducing Quiet Tizen on a **2020 75-inch Samsung Q90T QLED (`QN75Q90TAFXZA`)** running firmware **`T-NKMAKUC-2743.0`** (`B1052220/B60101 , BT - S`, internal build `T-NKMAKUC-REL-202607031800`).

---

## 1. Platform Comparison (`UN75U8000FFXZA` vs. `QN75Q90TAFXZA`)

| Property | Original Case Study (`UN75U8000FFXZA`) | This Reproduction (`QN75Q90TAFXZA`) |
|---|---|---|
| Model Year / Series | 2025 75" U8000F Crystal UHD | 2020 75" Q90T QLED |
| Firmware | `T-KSU2EFAKUC-0090-1300.9` | `T-NKMAKUC-2743.0` |
| OS & Kernel | Tizen 9.0, Linux 5.4.261 ARMv7 | Tizen 5.5, Linux 4.9.185 ARMv7 |
| .NET Runtime | .NET 6.0.9 (`/usr/share/dotnet.tizen/netcoreapp`) | .NET Core 3.1.0 (`netcoreapp2.0` TFM) |
| Execution Context | Temporary UID 0 via `CVE-2022-26330` | `uid=901(sdk)`, `context="System"`, group `1051(system_share)` (`CVE-2022-26330` patched) |
| Launcher Packaging | Replaced `BixbyPromotion.dll` inside `com.samsung.tv.bixby-promotion` | Standalone Partner-signed TPK (`org.quiettizen.home`) |
| HDMI Source IDs | HDMI 1 = `13`, HDMI 2 = `14`, HDMI 3 = `15` | HDMI 1 = `13` (Chromecast), HDMI 2 = `14` (Game Consoles), HDMI 3 = `15` (eARC Soundbar), HDMI 4 = `16` (PC Monitor) |
| YouTube App ID | `com.samsung.tv.cobalt-yt` | `9Ur5IzDKqV.TizenYouTube` (with fallback to `com.samsung.tv.cobalt-yt`) |
| Settings Key Rules | `com.samsung.tv.quicklaunch` (`XF86More`), `org.tizen.menu` (`XF86SysMenu`) | `org.tizen.function-osd` (`XF86More`, `~context:tv`), `org.tizen.menu` (`XF86SysMenu`) |

---

## 2. Database Access Without UID 0 (`system_share` & `User::Home` Transmute)

On firmware `T-NKMAKUC-2743.0`, `CVE-2022-26330` (`su`) is patched. However, the Developer Mode SDB command foothold runs as:

```text
uid=901(sdk) gid=901(sdk) groups=29(audio),44(video),201(display),901(sdk),1004(input),1051(system_share),6505(cts),6506(sdbd) context="System"
```

1. **Directory Permissions on `/opt/dbspace`**:
   - `/opt/dbspace` has mode `0775` (`drwxrwxr-x 1 root system_share User::Home`) with **no sticky bit**.
   - Because the SDB session belongs to group `1051(system_share)` and runs under SMACK label `System` (`System User::Home rwxat`), it can rename original database files inside `/opt/dbspace` (preserving `/opt/dbspace/.app-context.db.orig` and `/opt/dbspace/.pkgmgr_parser.db.orig` in place) and atomically `mv` staged databases into `/opt/dbspace`.
2. **SMACK Transmutation via `/opt/usr/home/owner/.applications/dbspace`**:
   - Files created directly by `sdk` (`System`) inherit the `System` SMACK label unless created in a transmuting directory.
   - `/opt/usr/home/owner/.applications/dbspace` resides on the same `/opt` (`/dev/mmcblk0p21`) filesystem and carries `access="User::Home" transmute="TRUE"`.
   - Staging SQLite databases inside `/opt/usr/home/owner/.applications/dbspace/` with `umask 000` and `PRAGMA journal_mode = PERSIST;` produces database and `-journal` files with mode `0666` (`-rw-rw-rw-`) and SMACK label `User::Home` (the exact SMACK label expected by `app_fw`, `owner`, and `System`), which are then moved atomically into `/opt/dbspace/`.

---

## 3. Standalone TPK & `DotnetPolicyChecker` Native Interop on Tizen 5.5

On Tizen 5.5, `/usr/apps/com.samsung.tv.bixby-promotion` does not exist on the writable `/opt` partition. Instead, Quiet Tizen is packaged and installed as a standalone Partner-signed `.NET` TPK (`org.quiettizen.home`) built with [tools/build_tizen55_tpk.py](../tools/build_tizen55_tpk.py).

### Solving `DotnetPolicyChecker` and SMACK `.so` Execution Restrictions
When a Partner-signed `.NET` TPK runs on Tizen 5.5, Samsung's `Dotnet.Launcher.dll` installs an AppDomain assembly/PInvoke policy (`DotnetPolicyChecker`) that blocks P/Invoke calls to non-public native libraries unless their base name is in `WhiteListManager`. At the same time, SMACK blocks `dlopen` (`PROT_EXEC`) on native `.so` binaries placed inside `/opt/usr/apps/org.quiettizen.home/lib/` (`User::Pkg::org.quiettizen.home::RO`).

Inspecting `DotnetPolicyChecker.WhiteListManager.AddAppDllAndSoFilesToWhiteList` revealed that it iterates every file in the package's `bin/` and `lib/` directories:
- If `IsSoFile(file)` is true, it strips `lib` and `.so` and adds the name to the P/Invoke whitelist.
- If `IsSoFile(file)` is false (a managed `.dll`), it reads the managed assembly's `AssemblyName` and adds its strong name to the **same** whitelist!

By compiling five tiny 3 KB managed stub `.dll` assemblies into `bin/` and `lib/`:
- `libsource-api.dll`
- `libvconf.dll`
- `libcapi-media-sound-manager-tv.dll`
- `libsettings-api.dll`
- `libcapi-appfw-app-control.dll`

`WhiteListManager` whitelists all five names as managed assemblies during app startup, while CoreCLR's `[DllImport("libsource-api.so")]` (and `.so.0` counterparts) resolves and loads the genuine system `/usr/lib/*.so` binaries (which carry the `_` floor SMACK label and execute without restriction).

### Additional Tizen 5.5 (.NET Core 3.1 / Dali 1.4) Adaptations
1. **Reflection-Free Catalog Loader**: Replaced `System.Text.Json.JsonSerializer` reflection serialization with a deterministic JSON parser so `DotnetPolicyChecker` never blocks property reflection on `LibraryApp`.
2. **`libsettings-api.so` String Marshaling**: Declared `CSharpGetItemValue(string id, out IntPtr name, out IntPtr value)` with `Marshal.PtrToStringAnsi` without freeing the returned pointers (which point to internal C++ `std::string` buffers owned by `libsettings-api.so`).
3. **Scene Disposal Safety**: Cleared `notice`, `detail`, `clock`, and `toolbarHint` references immediately upon scene teardown in `BuildPage()` so error handlers never write to disposed NUI `TextLabel` handles.

---

## 4. UI Features & Bug Fixes Implemented for `QN75Q90TAFXZA`

### A. Dark Mode Theme (Default) & Light Mode Toggle
- Launches in **Dark Mode** by default (`#0B0E14` / `#111726` radial-glow background `free-background-dark.svg` and dark translucent dock shelf `glass-shelf-dark.svg`).
- Includes a 4th top-right toolbar button (**Light Mode / Dark Mode**) that toggles themes live and persists the choice to `/opt/usr/home/owner/apps_rw/org.quiettizen.home/data/quiet-home-theme.txt`.

### B. Custom `Quiet Tizen` App Icon & Input Layout
- Generates a 512×512 PNG app icon displaying **`QUIET TIZEN`** (`quiet-tizen-icon.png`) for the Tizen Apps shelf.
- Configures the three video inputs on the Home page (`page == 0`):
  - **PC Monitor (`HDMI 4`, source `16`)**: Wide hero card (without the `"Ready to work."` text, showing only `"PC MONITOR"` and `"Switch to HDMI 4"`).
  - **Game Consoles (`HDMI 2`, source `14`)**: First portrait card.
  - **Chromecast (`HDMI 1`, source `13`)**: Second portrait card.

### C. High-Contrast Highlight Frame Around the Selected UI Element
- Because Tizen 5.5 NUI (Dali 1.4) does not render Tizen 6.0+ `View.BorderlineWidth` strokes, each slot (`Feature` hero/portrait cards, `Dock` cards, `SettingsTile` cards, `BuildLibrary` app cards, and `Toolbar` buttons) includes a matching vector SVG `FocusRing` overlay (`focus-hero.svg`, `focus-portrait.svg`, `focus-dock.svg`, `focus-tile.svg`, `focus-app.svg`, `focus-toolbar.svg`) with an outer `#38BDF8` glow stroke and inner `#FFFFFF` rim.
- Focused card captions also highlight in accent blue, and the top navigation bar (`Inputs | Apps | Settings`) highlights the active tab with a solid accent pill when focused.

### D. Sound Output Device Selector on Home Menu & Quick Settings
- Added a **Sound Output** selector card directly in the Home menu's bottom dock (slot 2, beside YouTube) and on Quick Settings (`page == 2`).
- Reads live speaker state from both `sound_manager_get_speaker_selection(out int speaker)` (`libcapi-media-sound-manager-tv.so.0`) and `CSharpGetItemValue("soundoutput", ...)` (`libsettings-api.so`), displaying the active output device on the card (**`HDMI eARC`**, **`TV Speaker`**, or **`Optical`**).
- Pressing **Select** on the **Sound Output** card cycles directly through:
  $$\text{HDMI eARC } (2) \longrightarrow \text{TV Speaker } (0) \longrightarrow \text{Optical } (1) \longrightarrow \text{HDMI eARC } (2)$$
  via `sound_manager_set_speaker_selection` and `CSharpSetItemValue("soundoutput", ...)` without leaving Quiet Tizen.

### E. Voice Control Toggle Tile
- Retains the 16 packages in the `voice` profile group and provides a **Voice Control** tile in the Home dock and Quick Settings that toggles `db/si_service/voice_recog_enable` and `db/multi-assistant/prelaunch_mode` via `libvconf.so.0` (`Voice on` / `Voice off`).

### F. Home Button (`XF86Home`) Open & Close Toggle
- Pressing **Home** (`XF86Home`) while watching HDMI or another app opens Quiet Tizen.
- Pressing **Home** (`XF86Home`) again while Quiet Tizen is already open (> 500 ms) closes Quiet Tizen back to the active HDMI input, matching the **Back** button.
- **Preventing `tvctx-manager` Re-Launch After Close**:
  In `/opt/dbspace/.app-context.db`, the `XF86Home` and `XF86Display` rows in `key_filter` use:
  ```sql
  UPDATE key_filter
  SET on_selector='~with-package:org.quiettizen.home',
      target_selector='package:org.quiettizen.home',
      args='quiet_page:home'
  WHERE appid='com.samsung.tv.csfs' AND key IN ('XF86Home', 'XF86Display');
  ```
  With `on_selector='~with-package:org.quiettizen.home'`, Tizen's global key router (`tvctx-manager`) launches `org.quiettizen.home` only when Quiet Tizen is **not** already the foreground window. When Quiet Tizen **is** in the foreground, `XF86Home` is delivered solely to `QuietHome.OnKey`, which closes Quiet Tizen without `tvctx-manager` immediately re-opening it.

### G. Fix for Samsung Source-Switching Banner (`CSourceSwitchBanner`) Hang on Close
- **Symptom**: Closing Quiet Tizen without changing the current HDMI input could leave Samsung's source-switching spinner (`CSourceSwitchBanner::t_Show` / `SHOW BANNER_FULLBG.`) hung on screen until the user switched to another input and back.
- **Root Cause**: `org.tizen.tv-viewer` logs `"Ignore to hide when video window focus out"` inside `CSourceSwitchBanner::t_Hide`. Previously, pressing **Back** or **Home** called `SelectSource(lastSource)` $\rightarrow$ `connect_source(lastSource)` while Quiet Tizen still had window focus and while the hardware scaler was already on `lastSource`. Because no hardware port change was needed, `source-service` emitted the completion (`t_Hide`) event immediately—before `Launch("org.tizen.tv-viewer")` finished returning window focus to `tv-viewer`—causing `tv-viewer` to ignore `t_Hide` and leave the switching banner up indefinitely.
- **Fix**:
  1. Added `CloseLauncher()` for **Back**, **Exit**, and **Home** close actions: reads `vconf_get_int("memory/system/source_type", out cur)`. When the TV is already on an HDMI input (`13..16`), it skips `connect_source` completely and simply calls `Launch("org.tizen.tv-viewer")`.
  2. Guarded `SelectSource(int source)`: if `cur == source` (selecting the HDMI card for the already-active input), it likewise skips `connect_source` and raises `org.tizen.tv-viewer`. When actually switching to a different input (`cur != source`), it calls `Launch("org.tizen.tv-viewer")` **before** `connect_source(source)` so `tv-viewer` already holds window focus when `t_Hide` arrives.

---

## 5. Applied Cleanup Groups & Measured Post-Restart Results

Using [profiles/qn75q90tafxza-2743.0.json](../profiles/qn75q90tafxza-2743.0.json) and [tools/plan_cleanup.py](../tools/plan_cleanup.py), five cleanup groups were applied in separate snapshotted phases (`advertising-01`, `context-01`, `smart-extras-01`, `light-shell-01`, `tv-plus-01`), disabling 20 app records (`app_disable='true'`, `app_onboot='false'`, `app_autorestart='false'`) while keeping `voice`, `org.tizen.menu`, YouTube (`9Ur5IzDKqV.TizenYouTube`), HDMI, eARC audio, networking, Bluetooth, and accessibility intact:

- **`advertising` (9 apps)**: `com.samsung.tizen.samsung-analytics`, `org.tizen.acr-service-app`, `com.samsung.tv.canalysis-service`, `com.samsung.tv.contents-recognition-dbmgr`, `com.samsung.tv.adagent-service`, `com.samsung.tv.pisa-service`, `org.tizen.pisa-control-service`, `yL49PNFmjW.PromotionApp`, `yL49PNFmjW.service`
- **`context` (3 apps)**: `com.samsung.tv.context-aware-agent`, `com.samsung.tv.vif`, `content-grab-service`
- **`smart-extras` (5 apps)**: `com.samsung.tizen.smartthings-client`, `com.samsung.tv.adplayer`, `com.samsung.tv.ghdaemon`, `com.samsung.tv.ghservice`, `samsunghealth-service-tv`
- **`light-shell` (1 app)**: `org.tizen.browser`
- **`tv-plus` (2 apps + preference)**: `com.samsung.tv.tvplus`, `com.samsung.tv.tvPlusDeeplinker`, and `db/menu/autorun_tv_plus = False`

See [evidence/observations-qn75q90tafxza.json](../evidence/observations-qn75q90tafxza.json) for before/after memory measurements (`MemAvailable` increased from `479 MiB` to `621 MiB`; swap usage decreased from `854 MiB` to `588 MiB` after a full restart) and known limitations.

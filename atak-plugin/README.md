# C2D2 ATAK Plugin

Android plugin for ATAK (Android Team Awareness Kit) that bridges field soldiers to the C2D2 backend.

## Capabilities

| Feature | Description |
|---|---|
| **Device linking** | One-time pairing of ATAK device UID to a soldier record |
| **Position sync** | Auto-pushes GPS every 30 s → `/api/v1/cot/position` |
| **Readiness entry** | Sleep hours + injury status form → `/api/v1/cot/readiness` |
| **Team overlay** | Loads mission team composition and renders markers on ATAK map |

## Prerequisites

### 1. ATAK Plugin Development Kit (PDK)

The ATAK SDK is distributed by the TAK Product Center (US government).

1. Register at **https://tak.gov** (free, requires .mil / .gov / CAC or sponsorship)
2. Download **ATAK Plugin Development Kit** for your ATAK version (4.x)
3. Copy `main.jar` from the PDK into `atak-plugin/libs/main.jar`

### 2. Android Studio

- Android Studio Hedgehog or later
- NDK 21.4.7075529 (`SDK Manager → SDK Tools → NDK`)
- Android SDK 34

## Build

```bash
# From the atak-plugin/ directory
./gradlew assembleDebug
```

The signed APK will be at `app/build/outputs/apk/debug/app-debug.apk`.

## Install on device

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

ATAK will auto-discover the plugin on next launch (or via `Settings → Plugins`).

## First-time setup (in-app)

1. Open the C2D2 panel from the ATAK toolbar (amber icon)
2. **Settings tab** — paste the Bearer token from the web app (`/api/v1/auth/login`)
3. Select your soldier record from the dropdown → tap **Save & Link Device**
4. The device UID is now paired and position sync starts automatically

## Backend configuration

| Env var | Default | Description |
|---|---|---|
| `TAK_SERVER_HOST` | *(empty)* | TAK Server hostname/IP — leave empty to disable subscriber |
| `TAK_SERVER_PORT` | `8087` | TCP port (8087 = plain, 8089 = TLS) |
| `TAK_SERVER_TLS`  | `false` | Enable TLS connection |
| `TAK_SERVER_CERT` | *(empty)* | Path to client cert PEM (TLS only) |

Add these to `backend/.env` when deploying alongside a real TAK Server:

```
TAK_SERVER_HOST=192.168.1.50
TAK_SERVER_PORT=8087
```

The backend subscriber will auto-update `SoldierPosition` records as ATAK devices
broadcast CoT SA messages through the TAK Server — no plugin involvement needed for
passive position tracking.

## Data flow

```
ATAK Device
  ├── GPS (CoT SA)  ──→  TAK Server  ──→  Backend subscriber  ──→  soldier_positions
  ├── Manual entry  ──→  Plugin HTTP ──→  /api/v1/cot/*        ──→  soldier_readiness
  └── Team request  ←──  Plugin HTTP ←──  /api/v1/missions/*/team-options
                                          (overlaid on ATAK map)
```

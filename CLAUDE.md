# pi-frame

Daily photo display using a Waveshare 7.3" E6 Full Color E-Paper (Spectra 6, 6-color, 800×480) in a solid wood frame, powered by a Raspberry Pi Zero 2W running NixOS.

## Repository layout

```
pi/          Pi firmware (NixOS config + Python service)
server/      Backend server (FastAPI)
dev/         Development tooling (Docker Compose, QEMU test, example config)
.github/     CI workflows
flake.nix    Nix flake: Pi SD image, server package, devShell
```

## Hardware

- **Display**: Waveshare RPi Zero PhotoPainter (7.3" E6 / epd7in3e driver)
  - SPI0: CS=GPIO8, DC=GPIO25, RST=GPIO17, BUSY=GPIO24, PWR=GPIO18
- **RTC**: DS3231 at I2C 0x68 (I2C1: SDA=GPIO2, SCL=GPIO3)
- **Battery monitor**: INA219 at I2C 0x40
- **Serial debug**: ttyAMA0 @ 115200 baud (3-pin header on HAT)

## Quick start

### Run tests

```bash
cd server && pip install -e ".[test]" && pytest
cd pi     && pip install -e ".[test]" && pytest
```

### Local dev server

```bash
docker compose -f dev/docker-compose.yml up
# Server at http://localhost:8000
# Upload: curl -F "file=@photo.jpg" -H "X-API-Key: dev-key" http://localhost:8000/api/images
# Daily:  curl http://localhost:8000/api/images/daily
```

### Build SD image (requires aarch64 binfmt on build host)

```bash
# On a NixOS machine with boot.binfmt.emulatedSystems = ["aarch64-linux"]:
nix build .#pi-sd-image
# Flash:
sudo dd if=result/sd-image/pi-frame.img of=/dev/sdX bs=4M conv=fsync status=progress
```

### First boot setup

1. After flashing, mount the SD card's FAT boot partition.
2. Copy your config to the boot partition:
   ```bash
   cp dev/piframe-config.example.json /mnt/boot/piframe-config.json
   # Edit /mnt/boot/piframe-config.json with your values
   ```
3. Insert SD card and power on. The Pi will:
   - Read secrets from the boot partition on first boot
   - Scan for known WiFi networks
   - If none found: display "PiFrame-Setup" SSID + QR code on the e-paper
   - Connect your phone/laptop to PiFrame-Setup and visit http://192.168.4.1
   - After WiFi setup, connect to Tailscale and fetch+display today's image

## Architecture

```
Pi Zero 2W (NixOS)                  NixOS Server
  piframe-wifi.service               piframe-server.service
    scan → try known → AP fallback     FastAPI + SQLite
  tailscale-autoconnect.service        /api/images/daily  ← Pi fetches
  piframe.service (daily @ 08:00)      /api/images        ← upload photos
  piframe-listener.service             /api/push          → Pi push listener
    Flask on Tailscale :8080
```

## API key

The Pi authenticates to the server using `X-API-Key`. The key is set via:
- Server: `PIFRAME_API_KEY` environment variable
- Pi: `/etc/piframe/api-key` file (written on first boot from `piframe-config.json`)

For `GET /api/images/daily` (Pi pull), **no auth required**.

## Secrets

The SD image contains no embedded secrets. Place `piframe-config.json` on the boot partition before first insert:

```json
{
  "server_url": "https://piframe.example.com",
  "api_key": "your-api-key-here",
  "tailscale_authkey": "tskey-auth-..."
}
```

The activation script reads this on first boot and writes individual files to `/etc/piframe/`, then renames the JSON to `piframe-config.done`.

## WiFi provisioning

1. Pi scans for visible APs and checks against `/var/lib/piframe/networks.json`
2. Tries each matching network (strongest signal first), waiting 30s per attempt
3. If none work: enables AP `PiFrame-Setup` (open, no password)
4. E-paper shows SSID and QR code linking to http://192.168.4.1
5. User connects and picks a network via the web form
6. Pi tears down AP and tries the new credential
7. On failure: back to step 3

Credentials persist across reboots in `/var/lib/piframe/networks.json`.

## Tailscale

Both Pi and server must be on the same Tailscale network.
- Pi: authenticates on first boot using `tailscale-authkey` from the config file. Hostname: `pi-frame`.
- Server: set `TAILSCALE_TAILNET` to your tailnet name (e.g., `my-tailnet.ts.net`) to enable push.
- Server can push an immediate update via `POST /api/push` (uses MagicDNS: `http://pi-frame.<tailnet>:8080`).

## RTC / deep sleep

The DS3231 RTC provides timekeeping without internet. After displaying an image, the Pi:
1. Sets a DS3231 wake alarm for the next display time (default 08:00)
2. Suspends to RAM via `rtcwake`

On wake, the DS3231 restores the system clock before NTP syncs.

## Git commit convention

- One-line messages only
- Follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/): `type(scope): description`
- Never include co-author or author attribution lines

## Code style

- Each file does one thing. Split files that mix unrelated concerns.
- Functions abstract away implementation details; callers should not need to know internals.
- Comments explain WHY, never WHAT. If you need a comment to explain what code does, refactor the code to be self-explanatory instead.
- No module-level docstrings — the filename conveys the same information.
- No function docstrings that just restate the function name or describe what the code does.
- Acceptable comments: hardware constraints, non-obvious invariants, workarounds for specific bugs, or tradeoffs that would surprise a reader.
- Frontend: HTML, CSS, and JS must live in separate files. Inline a few lines of one when truly necessary, but not entire stylesheets or scripts.

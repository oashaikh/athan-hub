# Athan Hub TV app (LG webOS)

A small hosted web app that shows a Home Assistant dashboard full screen on an
LG TV, with no browser bar. It targets a 2020 LG TV on webOS 5.x and is
installed through LG's Developer Mode. No root is needed.

The app opens `http://192.168.1.210/home-dashboard/home?kiosk` by default. If
Home Assistant can't be reached, it shows "Can't reach Home Assistant at ...,
retrying" and tries again every 15 seconds.

## What is in this folder

- `app/appinfo.json`: app id `com.athanhub.dashboard`, title "Athan Hub".
- `app/index.html` and `app/app.js`: the launcher. The JavaScript is plain ES5
  because webOS 5 runs an old Chromium (about version 68).
- `app/config.js`: the dashboard URL, display mode and retry interval.
- `app/icon.png` (80x80) and `app/largeIcon.png` (130x130).
- `build.sh`: checks `appinfo.json`, checks the JavaScript parses as ES5, and
  packages the app into `dist/`. The `dist/` folder is not committed.

The app runs at 1280x720 (`resolution` in `appinfo.json`) and the TV scales it
up, so the dashboard looks as big on a 4K TV as on a 720p screen. Set it to
`1920x1080` to fit more on screen at a smaller size.

## Display modes

`navigate` (the default) replaces the launcher page with the dashboard, so the
dashboard is the whole app. This works whatever headers Home Assistant sends.

`iframe` keeps the launcher page and puts the dashboard in a full-screen
frame. Home Assistant sends `X-Frame-Options: SAMEORIGIN` by default, which
gives a blank screen inside a frame. To use this mode you have to set
`use_x_frame_options: false` under `http:` in Home Assistant's
`configuration.yaml`, which also lets any other site frame your Home Assistant.
Stick with `navigate` unless you have a reason to change.

## One-time setup

### 1. Turn on Developer Mode on the TV

1. Create a free LG developer account at
   <https://webostv.developer.lge.com> (sign in, then accept the developer
   terms).
2. On the TV, open the LG Content Store, search for "Developer Mode" and
   install it.
3. Open the Developer Mode app and sign in with the LG developer account.
4. Switch "Dev Mode Status" on. The TV restarts.
5. Open the Developer Mode app again and switch "Key Server" on.
6. Write down the TV's IP address and the passphrase the app shows. The
   passphrase is six characters and changes if you reset Developer Mode.

Give the TV a fixed IP address (a DHCP reservation on the router) so the
setup below keeps working.

### 2. Install the webOS CLI on your computer

You need Node.js. Either install the CLI once:

```sh
npm install -g @webos-tools/cli
```

or put `npx -y -p @webos-tools/cli` in front of each `ares-*` command below.
`build.sh` uses `npx` on its own if `ares-package` is not installed.

### 3. Register the TV

Replace `192.168.1.50` with the TV's IP address:

```sh
ares-setup-device -a lgtv -i "{'username':'prisoner','host':'192.168.1.50','port':'9922'}"
ares-novacom --getkey -d lgtv
```

When `ares-novacom` asks, type the passphrase from the Developer Mode app.
Check the connection with:

```sh
ares-device -i -d lgtv
```

## Build, install and launch

From this folder:

```sh
./build.sh
ares-install -d lgtv dist/com.athanhub.dashboard_1.0.0_all.ipk
ares-launch -d lgtv com.athanhub.dashboard
```

The app then appears in the TV's app list as "Athan Hub" and can be launched
with the remote like any other app.

### Changing the dashboard URL

Pick whichever suits you:

- Edit `app/config.js` and rebuild.
- Set it at build time without touching the tracked file:
  `DASHBOARD_URL='http://192.168.1.210:8123/lovelace/0?kiosk' ./build.sh`.
  `DASHBOARD_MODE=iframe` works the same way.
- Override it for one launch while testing:
  `ares-launch -d lgtv com.athanhub.dashboard -p "{'url':'http://192.168.1.210/other?kiosk'}"`.
- When opening `index.html` in a desktop browser, pass `?url=` with the value
  URL-encoded, for example
  `index.html?url=http%3A%2F%2F192.168.1.210%2Fhome-dashboard%2Fhome%3Fkiosk`.

### Logging in to Home Assistant

The first time the dashboard opens, Home Assistant asks you to log in. Tick
"Keep me logged in" so the TV remembers it. Typing with the remote is slow, so
you may prefer a dedicated Home Assistant user for the TV, or the
`trusted_networks` auth provider limited to the TV's IP address.

### Debugging

```sh
ares-inspect -d lgtv --app com.athanhub.dashboard --open
```

opens Chrome DevTools attached to the app on the TV. To remove the app:

```sh
ares-install -d lgtv --remove com.athanhub.dashboard
```

## Remote control behaviour

The app sets `disableBackHistoryAPI`, so webOS hands the Back key (code 461)
to the page instead of closing the app. On the launcher and the "can't reach"
screen, Back retries straight away. Once the dashboard has loaded in
`navigate` mode, Back does nothing, which keeps you on the dashboard. Use the
Home button to leave the app.

## Keeping the Developer Mode session alive

Developer Mode runs on a timer. When it runs out, the TV removes every app
installed this way, including this one, and you have to reinstall it. The
Developer Mode app shows the time left and has an "Extend" button that resets
it. LG's current guide says the limit is 1000 hours; older reports say 50
hours. Check what your TV shows.

A Home Assistant automation can press "Extend" every night through the core
LG webOS TV (`webostv`) integration: switch the TV to the Developer Mode app
with `media_player.select_source`, then send the remote presses with
`webostv.button` (on the 2022 write-up this was DOWN, DOWN, ENTER). That will
be wired up separately.

## Things to check on the real TV

- The dashboard renders properly on the webOS 5 engine. The Home Assistant
  frontend is built for modern browsers, and LG's forum has a report of Home
  Assistant failing inside a webOS app.
- Whether the screen saver or "Auto Power Off" kicks in while the dashboard is
  showing. There is no public webOS API for a web app to block the screen
  saver, so if it does, change it in the TV's settings (General, then
  Eco/Energy Saving, and the screen saver options).
- How long the Developer Mode timer really is on this firmware.

## Automatic session renewal

The Developer Mode session token lives on the TV at `/var/luna/preferences/devmode_enabled`. Read it once with `ares-novacom --device lgtv --run "cat /var/luna/preferences/devmode_enabled"` and add it to Home Assistant's `secrets.yaml` as:

```yaml
lg_devmode_reset_url: "https://developer.lge.com/secure/ResetDevModeSession.dev?sessionToken=<token>"
```

`deploy/setup-home-assistant.sh` then adds a `rest_command` and an automation that renews the session every night at 03:30, so the app is never removed. If LG refuses the renewal, Home Assistant shows a notification asking you to press Extend in the Developer Mode app. Keep the token out of the repository.

## Signing in on the TV

The remote cannot comfortably type a password, so set `ATHAN_HA_TV_IP` in `/etc/athan-hub/athan-hub.env` to the TV's address and rerun the setup script. Home Assistant then signs that one address in as the owner without a login screen.

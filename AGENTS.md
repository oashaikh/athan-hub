# Athan Hub agent instructions

This repository is the canonical source for Athan Hub. The live `athan.local`
device is a deployment target, not a development workspace. Never edit
`/opt/athan-hub` directly.

## Workflow

- Work from the Plane integration branch, `dev`.
- Keep `main` releasable; promotion from `dev` to `main` remains a deliberate
  human action.
- The live server polls the public GitHub `dev` branch and deploys a commit only
  after it has been merged and pushed.
- Do not commit credentials, Wi-Fi passwords, dashboard PINs, Bluetooth device
  addresses, user uploads, databases, audio files, or runtime configuration.
- Persistent state belongs under `/var/lib/athan-hub`; configuration belongs
  under `/etc/athan-hub`. Installer and updater changes must preserve both.

## Required checks

Run these before considering a change complete:

```sh
python3 -m pytest backend/tests
npm --prefix frontend ci
npm --prefix frontend test
npm --prefix frontend run build
bash -n install.sh deploy/*.sh
```

The committed `frontend/dist` output must match the frontend source because the
headless installer deliberately does not require Node.js on the target device.
For deployment changes, preserve rollback behavior and test shell syntax.

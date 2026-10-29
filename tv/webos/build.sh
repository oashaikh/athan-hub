#!/usr/bin/env bash
# Validate the webOS app and package it as dist/<id>_<version>_all.ipk.
# Optional build-time overrides: DASHBOARD_URL, DASHBOARD_MODE (navigate|iframe).
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
app="$here/app"
dist="$here/dist"
stage="$dist/stage"

# Use a global install if present, otherwise fetch the official CLI with npx.
if command -v ares-package >/dev/null 2>&1; then
  ares_package=(ares-package)
else
  ares_package=(npx -y -p @webos-tools/cli ares-package)
fi

node - "$app" <<'EOF'
const fs = require("fs"), path = require("path");
const dir = process.argv[2];
const info = JSON.parse(fs.readFileSync(path.join(dir, "appinfo.json"), "utf8"));
const fail = (msg) => { console.error("appinfo.json: " + msg); process.exit(1); };
for (const k of ["id", "version", "vendor", "type", "main", "title", "icon", "largeIcon"]) {
  if (!info[k]) fail("missing " + k);
}
if (!/^[a-z0-9.\-]+$/.test(info.id)) fail("id must be lowercase letters, digits, dots or hyphens");
if (!/^\d+\.\d+\.\d+$/.test(info.version)) fail("version must be x.y.z");
if (info.type !== "web") fail("type must be web");
for (const k of ["main", "icon", "largeIcon"]) {
  if (!fs.existsSync(path.join(dir, info[k]))) fail(k + " file not found: " + info[k]);
}
console.log("appinfo.json OK: " + info.id + " " + info.version);
EOF

rm -rf "$stage"
mkdir -p "$stage"
cp -R "$app"/. "$stage"/

if [[ -n "${DASHBOARD_URL:-}" || -n "${DASHBOARD_MODE:-}" ]]; then
  node - "$stage/config.js" <<'EOF'
const fs = require("fs");
const file = process.argv[2];
const src = fs.readFileSync(file, "utf8");
const cfg = JSON.parse(JSON.stringify(eval("(function(window){" + src + ";return window.ATHAN_TV_CONFIG;})({})")));
if (process.env.DASHBOARD_URL) cfg.url = process.env.DASHBOARD_URL;
if (process.env.DASHBOARD_MODE) cfg.mode = process.env.DASHBOARD_MODE;
fs.writeFileSync(file, "window.ATHAN_TV_CONFIG = " + JSON.stringify(cfg, null, 2) + ";\n");
console.log("config: " + cfg.mode + " " + cfg.url);
EOF
fi

# The TV's engine is old: refuse anything that is not plain ES5.
npx -y acorn --ecma5 --silent "$stage/app.js" "$stage/config.js"

"${ares_package[@]}" -o "$dist" "$stage"
rm -rf "$stage"
ls -l "$dist"/*.ipk

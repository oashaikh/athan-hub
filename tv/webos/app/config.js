// Defaults for the TV app. build.sh rewrites this file in the staged copy when
// DASHBOARD_URL or DASHBOARD_MODE is set, so the tracked file stays as it is.
window.ATHAN_TV_CONFIG = {
  url: "http://192.168.1.210/home-dashboard/home?kiosk",
  mode: "navigate",
  retrySeconds: 15
};

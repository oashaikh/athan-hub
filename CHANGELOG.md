# Changelog

## 2.0.0

- Fixed locally bundled Material Icons rendering as clipped ligature text across the dashboard and navigation.
- Added a child-safe Quran memorisation workspace with 114 surahs, 6,236 ayahs, translation, transliteration, and 139 pinned QUL recitations.
- Added admin-created child profiles with independent preferences, progress, sessions, rewards, streaks, badges, and three themes.
- Added safe on-demand Quran audio caching with host validation, atomic writes, cache limits, and LRU eviction.
- Added measured Athan playback state so scheduled Athan stops Quran audio and locks child interaction for the recording duration.
- Reworked public and admin authorization so prayer and Quran child experiences remain public while system/profile administration requires the PIN.
- Refined stars into meaningful milestones: daily practice, completed surahs, and 10/50/100-ayah memorisation achievements; individual ayahs and repetitions no longer award stars. A completed surah awards one star per ayah.
- Added an accessible fullscreen control to the public header, including an exit state and graceful browser support detection.
- Made earned surah stars reversible: changing a completed surah's ayah away from Memorised removes one star, and restoring it restores the star.

## 1.0.0

- Added a hardware-neutral, one-shot Ubuntu/Debian installer.
- Added persistent headless audio services and web-based Bluetooth discovery/pairing.
- Added offline fonts and icons with a committed production frontend build.
- Added generated PIN protection, unique signing secrets, upload limits, file validation, and service hardening.
- Added idempotent upgrades, diagnostics, backups, and uninstall tooling.
- Added automated backend, frontend, installer, dependency, and secret checks.
- Removed recovered device identifiers, personal audio, historical data, and network credentials from the release tree.

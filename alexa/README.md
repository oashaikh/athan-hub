# Athan Hub Alexa skill

A private Alexa skill that streams the full-length athan with Alexa's AudioPlayer. The SSML `<audio>` clip that Home Assistant normally uses is capped at 240 seconds by Amazon, and the skill has no such limit. It stays in the development stage, so only Echo devices on your own Amazon account can use it, and it is never published.

## How it fits together

- `api/alexa.js` is the skill's endpoint. `athan-audio-sync` deploys it to the same Vercel project as the athan audio, together with a generated `api/_manifest.js` listing the full-length recordings from Home Assistant's `athan/general` and `athan/fajr` media folders.
- The endpoint only answers requests carrying your skill's ID (`ATHAN_ALEXA_SKILL_ID`).
- With `ATHAN_HA_PLAYBACK=skill`, Athan Hub asks the Echo, through Home Assistant, to "ask call to prayer to play the athan" (or "the morning prayer" for Fajr), and the skill streams a randomly chosen recording.
- You can also say it yourself: "Alexa, open call to prayer".

## One-time setup

1. Sign in at developer.amazon.com with the same Amazon account as the Echo.
2. On a computer with Node.js, authorise the Alexa Skills Kit CLI: `npx ask-cli@2 configure` and approve the browser prompt. Skip the AWS step.
3. Create the skill from this folder. Its invocation name is "call to prayer": Alexa's speech recognition does not pick up "athan hub", it heard "further author".

```sh
cd alexa
npx ask-cli@2 smapi create-skill-for-vendor --manifest "file:skill-package/skill.json"
# note the skillId it prints, then:
npx ask-cli@2 smapi set-interaction-model -s <skillId> -g development -l en-GB --interaction-model "file:skill-package/interactionModels/custom/en-GB.json"
npx ask-cli@2 smapi set-skill-enablement -s <skillId> -g development
```

4. On the Athan Hub machine, add to `/etc/athan-hub/athan-hub.env` and publish:

```text
ATHAN_ALEXA_SKILL_ID=<skillId>
ATHAN_HA_PLAYBACK=skill
```

```sh
sudo athan-audio-sync
sudo systemctl restart athan-hub-scheduler
```

Check it with "Alexa, open call to prayer". To go back to the 240-second clips, remove `ATHAN_HA_PLAYBACK`.

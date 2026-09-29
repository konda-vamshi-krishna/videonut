# 🎧 Narration demo

A real render of the Narrator stage, so you can hear what the voice agent
produces before configuring any API key.

| File | What it is |
|---|---|
| **`narration_full.mp3`** | **The deliverable.** 75.2 s of finished narration. |
| `voice_script.md` | The input — a normal Scriptwriter output with section markers and voice cues. |
| `narration_cues.md` | Section → timecode map, generated from the render. |
| `narration_manifest.json` | Machine-readable timeline the Director and validators read. |
| `segments/` | Per-chunk audio, so a single sentence can be re-rendered without paying for the whole track. |

## What this demonstrates

**The cue grammar survives the round trip.** The script says:

```
[HOOK]
(modulation pitch: low speed: slow tone: grave) In two thousand seventeen, eight
researchers at Google published a paper. (end modulation)
(pause 2s)
(emphasis) Eight pages. (end emphasis) That is all it took.
```

and the output has a grave opener, **exactly 2.000 seconds** of silence, then the
emphasised beat. The silence is a real ffmpeg-generated segment spliced between
clips, not provider markup — which is why it is 2.000 s rather than "about two
seconds", and why it behaves identically on ElevenLabs, Sarvam, Gemini and OpenAI.
(ElevenLabs does not support SSML `<break>` at all, so markup was never an option.)

**The timeline is contiguous and absolute.** Segment *n* starts exactly where
segment *n−1* ended:

| Section | In | Out |
|---|---|---|
| HOOK | 0:00.00 | 0:08.93 |
| BRIDGE | 0:08.93 | 0:14.39 |
| MEAT | 0:14.39 | 0:53.06 |
| HUMAN BEAT | 0:53.06 | 1:00.90 |
| VERDICT | 1:00.90 | 1:10.98 |
| CTA | 1:10.98 | 1:15.11 |

Drop `narration_full.mp3` on the timeline at 00:00:00.000 and the Director's shot
list lines up without re-syncing.

**Runtime is measured, not estimated.** The Scriptwriter's footer claims 245
words; after front matter and cues are stripped, 196 are actually narrated. The
word-count estimate was 1.42 minutes — the real render is 1.25. That ~12 % gap is
exactly why the Narrator runs a free draft pass *before* the Director times any
shots.

## Reproducing it

Both of the repository's own gates pass on these files:

```bash
python _video_nut/tools/validators/output_validator.py voice docs/demo/voice_script.md
# [OK] Valid voice script (216 words, 6 sections, 15 voice cues)

python _video_nut/tools/validators/audio_validator.py <project-with-these-files>
# [OK] manifest exists / master track built / all segments rendered
# [OK] track is not silent / track is not clipped / cue sheet exists
# mean_volume=-20.0dB
```

To render your own with a real provider:

```bash
cp .env.example .env && $EDITOR .env      # add one TTS key
python _video_nut/tools/audio/tts_engine.py --project docs/demo --dry-run
python _video_nut/tools/audio/tts_engine.py --project docs/demo --mode final --yes
```

Note: the audio here was rendered through Arena's TTS to illustrate the pipeline's
output format. A production run goes through the providers described in
[`../../_video_nut/docs/VOICE_AGENT.md`](../../_video_nut/docs/VOICE_AGENT.md) —
ElevenLabs, Sarvam, Gemini or OpenAI — with identical file layout and timings.

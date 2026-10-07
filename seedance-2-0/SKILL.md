---
name: seedance-2-0
description: Plan and validate Seedance 2.0 text-to-video, first-frame, first/last-frame, and reference-asset jobs; use when a user asks for a Seedance 2.0 prompt, shot list, continuity workflow, or API generation.
---

# Seedance 2.0

Use this skill when the task is to turn a creative brief into a small,
reviewable Seedance 2.0 job. Keep the prompt and the API request separate:
first identify the subject, action, camera, timing, audio, and reference roles;
then validate the JSON and run the request.

## Prompt structure

1. State the shot's subject, location, action, camera movement, and visual tone.
2. Name references by upload order: `@Image 1`, `@Video 1`, and `@Audio 1`.
3. For a sequence, use `Shot 1`, `Shot 2`, and explicit continuity notes. Seedance
   2.0 does not use timestamp syntax as a reliable shot controller.
4. Put speech, music, and subtitle constraints in positive, testable language.
5. End with output constraints: duration, ratio, resolution, and whether audio is
   generated. Do not request a 2.5-only edit mode on the 2.0 route.

## Reference roles and limits

| Mode | Allowed input | Limits |
|---|---|---|
| Text | prompt | 4–15 seconds; fixed ratios |
| First frame | `start_image` | one image; adaptive or fixed ratio |
| First + last frame | `start_image`, `end_image` | two images; adaptive or fixed ratio |
| Multimodal reference | `reference_images`, `reference_videos`, `reference_audios` | 9 images, 3 videos, 3 audio clips, 15 assets total |

Audio references may be used without adding a visual reference when the selected model page accepts them. The
2.0 model family supports 480p, 720p, 1080p and 4K; Fast and Mini expose only
the tiers listed in the README. Never send an unsupported resolution merely to
match a different Seedance page.

## Execution contract

Use `scripts/seedance_job.py` for the submit → poll → download lifecycle. The
script checks the model, duration, ratio and assets before a request is
submitted. It uses `https://argolink.io/v1` by default, but
the environment can point to another compatible gateway. Every request has an
explicit User-Agent. A successful job is downloaded only after status `done`.

```bash
python3 scripts/seedance_job.py check templates/first-last-frame.json
python3 scripts/seedance_job.py submit templates/first_last.json
python3 scripts/seedance_job.py wait REQUEST_ID
python3 scripts/seedance_job.py download REQUEST_ID result.mp4
```

Keep the `request_id` when polling stops. `pending` means the server still owns
the job; `failed` and `expired` mean it is terminal. Failed jobs are not billed,
but a new POST should only be sent after reviewing the error.

The client uses `POST /v1/videos/generations`, `GET /v1/videos/{request_id}`,
and `GET /v1/videos/{request_id}/content`. Local assets must first be uploaded
through the provider's upload-ticket endpoint; the templates intentionally use
placeholder HTTPS URLs and never contain a secret. A timeout while observing a
POST is not proof that no job exists, so the script never retries a submission
automatically.

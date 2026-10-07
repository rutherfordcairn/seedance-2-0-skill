# Seedance 2.0 Claude Code skill

An installable Claude Code skill for planning Seedance 2.0 shots, selecting the
right 2.0 tier, validating reference roles, and running the real asynchronous
video lifecycle. It is a skill, not a provider SDK: the backend is configured
through `SEEDANCE_BASE_URL` and `SEEDANCE_API_KEY`, with the default endpoint
available on [ArgoLink](https://argolink.io/gh-seedance-2-0-skill).

Last checked: 2026-10-07.

## Install

Copy the skill directory into a personal or project skill location:

```bash
mkdir -p ~/.claude/skills/seedance-2-0
cp seedance-2-0/SKILL.md ~/.claude/skills/seedance-2-0/
cp -R seedance-2-0/scripts ~/.claude/skills/seedance-2-0/
cp -R seedance-2-0/templates seedance-2-0/references ~/.claude/skills/seedance-2-0/
```

Claude Code loads `SKILL.md` when a request asks for Seedance 2.0 prompting,
reference inputs, or a generation workflow. Keep the API key outside the
repository:

```bash
export SEEDANCE_API_KEY='your-key'
export SEEDANCE_BASE_URL='https://argolink.io/v1'
```

The frontmatter description is the trigger boundary: the skill is useful for a
Seedance 2.0 shot, continuity plan, reference-role question, or API generation
request. It does not claim to be a Claude Code plugin, a hosted service, or a
video editor. Install it at either the user location above or a project-local
`.claude/skills/seedance-2-0/` directory. Reload skills after copying files,
then ask for a 2.0 shot and confirm that the skill is selected before sending a
paid request.

## Repository map

| Path | Use |
|---|---|
| `seedance-2-0/SKILL.md` | Trigger description, prompt structure, reference roles, limits, and execution checklist. |
| `seedance-2-0/scripts/seedance_job.py` | Standard-library checker and submit/status/wait/download/upload CLI. |
| `seedance-2-0/templates/` | Text, first-frame, first/last-frame, and multimodal JSON starting points. |

## Tier choice

| Model ID | Resolution | Duration | ArgoLink price snapshot |
|---|---|---|---:|
| `seedance-2.0-mini` | 480p/720p | 4–15 s | $0.026/$0.057 per s |
| `seedance-2.0-fast` | 480p/720p | 4–15 s | $0.042/$0.091 per s |
| `seedance-2.0` | 480p/720p/1080p/4K | 4–15 s | $0.053/$0.11/$0.28/$0.58 per s |

Prices are from the model catalog on 2026-10-07. Start a storyboard with
Mini, use Fast when turnaround matters, and use 2.0 for final resolution. A
reference video adds its seconds to the billed seconds; unsuccessful jobs are
not billed.

## First run

```bash
python3 seedance-2-0/scripts/seedance_job.py check seedance-2-0/templates/text.json
python3 seedance-2-0/scripts/seedance_job.py submit seedance-2-0/templates/text.json
python3 seedance-2-0/scripts/seedance_job.py wait REQUEST_ID
python3 seedance-2-0/scripts/seedance_job.py download REQUEST_ID output.mp4
```

The CLI submits to `POST /v1/videos/generations`, polls
`GET /v1/videos/{request_id}` while `pending`, and downloads
`GET /v1/videos/{request_id}/content` after `done`. `failed` and `expired` are
terminal. `check` performs all local validation without a network call.

The request JSON is intentionally explicit. The validator accepts only the
three current catalog IDs, their documented duration and resolution
combinations, six fixed aspect ratios, HTTPS media URLs, and the
9-image/3-video/3-audio/15-total reference limits. First/last-frame inputs are kept separate from multimodal references. The checked 2.0 contract has no edit mode; an edit field is rejected instead of being silently sent to a model that may ignore it.
This prevents a copied Seedance 2.5 request from being sent to a 2.0 endpoint
with a silently ignored field. The `references/` notes explain the roles and
the templates show text, frame, and multimodal shapes with deliberately fake
URLs that must be replaced with uploaded media.

## Safety and reproducibility

The skill never invents a model ID, ratio, or output size. It asks for missing
references instead of silently dropping them, keeps the request ID in the
conversation, and does not retry a POST after an observation timeout. Do not
put a key in a template or commit generated media. The script adds a User-Agent
to every JSON request and upload PUT so it works through the public edge.

## Cost and failure handling

The dated ArgoLink output-second snapshot is $0.026/$0.057 for Mini,
$0.042/$0.091 for Fast, and $0.053/$0.11/$0.28/$0.58 for regular 2.0 from
480p through 4K. A reference video adds its duration to billed seconds. A
`pending` job remains owned by the service while polling stops; resume with the
same request ID. `failed` and `expired` are terminal and are not charged. A
429 or 503 should be retried at the status boundary according to the server's
retry hint, never by issuing a second POST blindly.

## Example review sequence

1. Copy `templates/text.json` and replace its prompt, model, duration and
   resolution with values checked on the current model page.
2. Run `check` and fix every problem before setting a key.
3. If references are needed, upload them through the ticket endpoint and replace
   the placeholder URLs; describe their roles as `@Image 1` and so on.
4. Run `submit` once and save the printed request ID in your shot notes.
5. Run `wait` until a terminal state, then use `download` only for `done`.

The command never stores a bearer token in a template, and the upload helper
sets a User-Agent on its presigned PUT as well as on API requests. If a request
times out after submission, keep the ID and query status later. If no ID was
observed, inspect the provider's job list before trying again; this repository
cannot prove that an unknown network outcome was not billed.

## Troubleshooting

An error from `check` is local and safe to fix. A 401 means the environment key
is missing or invalid; a 429 means the account is rate limited; and a 503 means
capacity is temporarily unavailable. Keep the same request ID for status calls
and honor a returned `Retry-After` value. A content request before completion
returns a not-ready response, while a failed job returns a terminal error. The
skill intentionally does not make a second submission to recover from any of
these conditions. For a new creative take, copy the JSON, change the prompt or
an explicit local take note, and submit it as a deliberate new job.

# Security policy

## Reporting a vulnerability

If you find a security issue in this project — credentials in logs,
arbitrary code execution via a crafted source URL, dependency CVE that
affects users, anything in that space — **please do not open a public
issue**.

Email instead: **web@conversaoextrema.com.br**

Include:

- A short description of the issue
- A reproduction (commands, input file, or steps)
- The version / commit you saw it on
- Optional: a proposed fix

I'll acknowledge within a few days, agree on a disclosure timeline with
you, and credit you in the changelog when the fix ships (unless you
prefer to stay anonymous).

## Out of scope

- Issues in the upstream tools this skill calls (ffmpeg, yt-dlp, Groq
  Whisper, MediaPipe, silero-vad). Report those to their respective
  projects.
- "I committed my own API key" — that's on you, but I'm happy to help
  you rotate and rewrite history if you ping me.

## What I commit to

- I will not knowingly ship code that exfiltrates user data, network
  beacons, or anything that contacts a server I control without explicit
  config.
- Every release runs through `gitleaks` and a compile-check workflow
  before merge (see [`.github/workflows/ci.yml`](.github/workflows/ci.yml)).
- The skill is MIT-licensed and the source is the source — what you read
  is what runs.

---

By [@onetogregorio](https://github.com/onetogregorio) · [netogregorio.com](https://netogregorio.com) · [@onetogregorio](https://instagram.com/onetogregorio)

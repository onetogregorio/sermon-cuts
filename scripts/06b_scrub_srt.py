#!/usr/bin/env python3
"""Lint a brand SRT for likely YouTube-auto-caption errors before burn-in.

Catches the failure modes we see most often when transcribing sermons
through YouTube auto-captions (PT-BR, ~10 cuts/week dogfooding):

  1. **dropped_word_boundary** — a function word (em/que/de/etc.) sits
     directly before a capitalized non-proper-noun. YouTube ate a word
     at a sentence boundary.
       "do que Mas não"   →  was actually  "do que nós. Mas não"
       "uma Então, aqui"  →  was actually  "uma relação. Então, aqui"

  2. **immediate_repetition** — hesitation duplicated by the transcriber.
     Only flags short / function-word repetitions ("um um", "que que",
     "a a") so stylistic emphasis like "cansa, cansa" survives.

  3. **forbidden_ending** — a cue ends on a word from
     ``cut_validation.forbid_endings`` (porque, mas, que, para, …).
     ``05_validate_cut.py`` already checks this at cut-level; here
     we check it per-cue.

  4. **dictionary** — ``memory/messages/<slug>/corrections.txt`` with
     ``wrong=right`` lines applies automatically. Always on. Useful
     for recurring theological / proper-name fixes ("Quisto=Cristo").

Three review paths beyond the rules:

  • **--agent-review** (default in non-TTY when there are suspects).
    Emits a structured JSON with prev/next cue context, word-level
    transcript snippet around each suspect, and a path to
    ``prompts/scrub_srt.md`` so whichever AI coding agent is
    orchestrating the run (Claude Code, Cursor, Codex, Cline, Aider,
    Continue, Windsurf, …) can read the report, edit the SRT via the
    file-edit tool its runtime exposes, and resume the pipeline with
    ``--skip-scrub``.

  • **--use-llm** — calls Anthropic Claude (preferred via
    ANTHROPIC_API_KEY) or Groq Llama (fallback via GROQ_API_KEY)
    with ``prompts/scrub_srt.md`` as the system prompt and the
    suspect list as the user message. Applies the LLM's returned
    fixes. For unattended runs (cron, nightly) where no agent is
    orchestrating.

  • **--auto-apply** — rule-only, applies confidence ≥ 0.85 silently
    (effectively just the immediate_repetition pattern). Cheapest mode.

Usage:
    06b_scrub_srt.py <slug> <cut_index> [--agent-review]
                                       [--use-llm]
                                       [--auto-apply]
                                       [--dry-run]
                                       [--corrections FILE]

Mode resolution when no flag is passed:
    TTY + stdin attached       → interactive y/n/edit/skip
    non-TTY, suspects > 0      → --agent-review (default)
    non-TTY, suspects == 0     → no-op

Output: a stable JSON document on stdout. In --agent-review mode the
schema is documented in ``prompts/scrub_srt.md``. Otherwise:
    {
      "ok": true,
      "srt": "...path...",
      "suspects": [...],
      "applied_count": <int>,
      "dry_run": <bool>
    }

Reads:
    memory/messages/<slug>/cuts_proposed.json
    memory/messages/<slug>/srts/NN-slug.srt
    memory/messages/<slug>/transcript.json   (for word-level context)
    memory/messages/<slug>/corrections.txt   (optional dictionary)
Writes:
    memory/messages/<slug>/srts/NN-slug.srt   (in-place when applying)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from _common import _BOLD, _DIM, _RST, _TTY, _YEL, fail, warn

SKILL_ROOT = Path.home() / ".claude/skills/sermon-cuts"
MESSAGES = SKILL_ROOT / "memory/messages"
CFG = yaml.safe_load((SKILL_ROOT / "config/render_defaults.yaml").read_text())
FORBID_ENDINGS = set(CFG.get("cut_validation", {}).get("forbid_endings", []))

# ─── pattern data ─────────────────────────────────────────────────────────

# Proper nouns commonly seen in sermons — they're legitimately capitalized
# after a function word (e.g. "de Deus", "em Cristo") so we whitelist them
# to avoid drowning the user in false positives. Case-sensitive on purpose.
PROPER_NOUNS = {
    # Bible & deity
    "Deus",
    "Jesus",
    "Cristo",
    "Senhor",
    "Pai",
    "Espírito",
    "Santo",
    "Filho",
    "Salvador",
    "Messias",
    "Cordeiro",
    "Verbo",
    # Bible characters & places
    "Mateus",
    "Marcos",
    "Lucas",
    "João",
    "Paulo",
    "Pedro",
    "Tiago",
    "Judas",
    "André",
    "Filipe",
    "Tomé",
    "Bartolomeu",
    "Simão",
    "Davi",
    "Salomão",
    "Moisés",
    "Abraão",
    "Isaque",
    "Jacó",
    "Israel",
    "Maria",
    "José",
    "Ana",
    "Ester",
    "Rute",
    "Marta",
    "Lázaro",
    "Sara",
    "Rebeca",
    "Raquel",
    "Lia",
    "Débora",
    "Eva",
    "Saulo",
    "Estêvão",
    "Lídia",
    "Priscila",
    "Áquila",
    "Timóteo",
    "Tito",
    "Barnabé",
    "Zaqueu",
    "Lúcifer",
    "Satanás",
    "Jerusalém",
    "Belém",
    "Nazaré",
    "Galileia",
    "Judeia",
    "Cafarnaum",
    "Egito",
    "Roma",
    "Babilônia",
    "Sinai",
    # Concepts / institutions
    "Bíblia",
    "Evangelho",
    "Igreja",
    "Reino",
    "Aliança",
    "Lei",
    "Páscoa",
    "Cristão",
    "Cristãos",
    "Cristã",
    # Brazilian / Portuguese-language common
    "São",
    "Santa",
    "Brasil",
    "Portugal",
    "São Paulo",
    "Rio",
    # Sentence-starter pronouns that often follow a function word legitimately
    # ("para Ele", "com Ela", "em Mim")
    "Ele",
    "Ela",
    "Eles",
    "Elas",
    "Mim",
    "Nós",
}

# Function words that we expect to be followed by a noun phrase. When the
# next token starts with a capital that isn't a proper noun, the transcriber
# probably ate a sentence boundary.
FUNCTION_WORDS = (
    r"a|o|os|as|um|uma|uns|umas|"
    r"para|pra|com|de|do|da|dos|das|"
    r"em|no|na|nos|nas|que|por|"
    r"pelo|pela|pelos|pelas|"
    r"ao|à|aos|às"
)
FUNCTION_WORDS_PATTERN = re.compile(rf"\b({FUNCTION_WORDS})\s+([A-ZÀ-Ú][a-záéíóúâêôãõçñ]+)\b")

# Words we accept as "real hesitations" — only these get flagged when
# duplicated. Avoids flagging stylistic repetition like "cansa, cansa".
HESITATION_TOKENS = {
    "a",
    "o",
    "e",
    "é",
    "um",
    "uma",
    "que",
    "eu",
    "ele",
    "ela",
    "de",
    "do",
    "da",
    "the",
    "uh",
    "ah",
    "hum",
}

# ASS-override prefix like {\fs22\b1} that we add in 06_build_srt for hook
# boost. Strip it before pattern matching so we don't trip on the braces.
ASS_OVERRIDE = re.compile(r"\{\\[^}]+\}")

# ─── SRT parsing / serialization ──────────────────────────────────────────


def parse_srt(text: str) -> list[dict]:
    """Parse SRT text into a list of cue dicts.

    Output shape: ``[{n, tc_start, tc_end, text, override_prefix}]``.
    ``override_prefix`` captures any leading ASS override block (e.g.
    ``{\\fs22\\b1}`` on the first cue) so we can re-attach it on write
    without including it in the pattern matching.
    """
    cues: list[dict] = []
    blocks = re.split(r"\n\n+", text.strip())
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        try:
            n = int(lines[0])
        except ValueError:
            continue
        m = re.match(
            r"(\d{2}:\d{2}:\d{2},\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2},\d{3})",
            lines[1],
        )
        if not m:
            continue
        raw = "\n".join(lines[2:])
        prefix_match = ASS_OVERRIDE.match(raw)
        if prefix_match:
            override_prefix = prefix_match.group(0)
            text_body = raw[prefix_match.end() :]
        else:
            override_prefix = ""
            text_body = raw
        cues.append(
            {
                "n": n,
                "tc_start": m.group(1),
                "tc_end": m.group(2),
                "text": text_body,
                "override_prefix": override_prefix,
            }
        )
    return cues


def serialize_srt(cues: list[dict]) -> str:
    """Render a parsed cue list back to SRT text."""
    out: list[str] = []
    for cue in cues:
        out.append(str(cue["n"]))
        out.append(f"{cue['tc_start']} --> {cue['tc_end']}")
        out.append(f"{cue.get('override_prefix', '')}{cue['text']}")
        out.append("")
    return "\n".join(out) + "\n"


# ─── heuristics ───────────────────────────────────────────────────────────


def detect_dropped_word_boundary(cues: list[dict]) -> list[dict]:
    """Find "<function-word> <CapitalizedNonProperNoun>" patterns.

    Skips:
      • when the cap word is in PROPER_NOUNS (legit "em Cristo")
      • when the match is preceded by sentence-ending punctuation
        (legit "para ela. Ele disse")
      • when the function word is the very first token of the cue
        (cue boundary already handles the break)
    """
    suspects: list[dict] = []
    for cue in cues:
        text = cue["text"]
        for m in FUNCTION_WORDS_PATTERN.finditer(text):
            func, capword = m.group(1), m.group(2)
            if capword in PROPER_NOUNS:
                continue
            # Skip if the function word is the cue's first token — joining
            # the previous cue's content can't be done from inside this cue.
            prefix = text[: m.start()].strip()
            if not prefix:
                continue
            # Legit sentence break already in place?
            if prefix.endswith((".", "!", "?")):
                continue
            # Suggest inserting a period before the capitalized word.
            # Without the original audio we can't recover the dropped word,
            # so the safest fix is to mark the sentence break — the user
            # can refine in --auto-apply review.
            fix = _insert_period_before_word(text, m)
            suspects.append(
                {
                    "cue": cue["n"],
                    "tc": cue["tc_start"],
                    "text": text,
                    "pattern": "dropped_word_boundary",
                    "matched": f"{func} {capword}",
                    "suggestion": fix,
                    "confidence": 0.75,
                    "applied": False,
                }
            )
    return suspects


def _insert_period_before_word(text: str, match: re.Match) -> str:
    """Build the suggestion: insert ". " between the function word and the
    capitalized word that follows it.
        "do que Mas não"  →  "do que. Mas não"
    Preserves whitespace structure as much as possible.
    """
    # match.group(1) is the function word; the cap word starts after the
    # whitespace inside the match. Recover the cap word's start by walking
    # the match text.
    func_end_in_text = match.start() + len(match.group(1))
    head = text[:func_end_in_text].rstrip()
    tail = text[func_end_in_text:].lstrip()
    return f"{head}. {tail}"


def detect_immediate_repetition(cues: list[dict]) -> list[dict]:
    """Find "<word> <word>" repetitions where the word is a known hesitation."""
    suspects: list[dict] = []
    # Strict pattern: a word, whitespace, the same word — case-insensitive.
    pattern = re.compile(r"\b(\w+)(\s+)\1\b", flags=re.IGNORECASE)
    for cue in cues:
        text = cue["text"]
        for m in pattern.finditer(text):
            word = m.group(1).lower()
            # Only flag known short hesitations to avoid stylistic false
            # positives like "cansa, cansa" or "lá, lá".
            if word not in HESITATION_TOKENS and len(word) > 3:
                continue
            # If the writer put a comma between the two repetitions, it's
            # almost certainly stylistic emphasis — leave it alone.
            sep = m.group(2)
            if "," in text[m.start() : m.end()]:
                continue
            if not sep.isspace():
                continue
            fix = text[: m.start()] + m.group(1) + text[m.end() :]
            suspects.append(
                {
                    "cue": cue["n"],
                    "tc": cue["tc_start"],
                    "text": text,
                    "pattern": "immediate_repetition",
                    "matched": m.group(0),
                    "suggestion": fix,
                    "confidence": 0.85,
                    "applied": False,
                }
            )
    return suspects


def detect_forbidden_ending(cues: list[dict]) -> list[dict]:
    """Flag cues that end on a forbidden function word.

    ``05_validate_cut.py`` already checks this at the CUT level (last word
    of the whole segment). Here we re-apply per-CUE so the SRT itself
    doesn't read as a hanging thought. We don't auto-fix — the right move
    is to shift the trailing word into the next cue, which mutates two
    cues at once and is better left to interactive review.
    """
    suspects: list[dict] = []
    for i, cue in enumerate(cues):
        if i == len(cues) - 1:
            # Last cue; no next cue to shift into.
            continue
        clean = cue["text"].strip().rstrip(".,!?;:").strip()
        if not clean:
            continue
        last_word = clean.split()[-1].lower()
        if last_word in FORBID_ENDINGS:
            suspects.append(
                {
                    "cue": cue["n"],
                    "tc": cue["tc_start"],
                    "text": cue["text"],
                    "pattern": "forbidden_ending",
                    "matched": last_word,
                    "suggestion": (
                        f'(considere mover "{last_word}" pro início da cue {cue["n"] + 1})'
                    ),
                    "confidence": 0.60,
                    "applied": False,
                }
            )
    return suspects


def apply_corrections_dict(cues: list[dict], dict_path: Path) -> list[dict]:
    """Read ``wrong=right`` pairs and apply them in place, recording each
    application as an already-``applied: true`` suspect for the report."""
    if not dict_path.exists():
        return []
    corrections: dict[str, str] = {}
    for line in dict_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        wrong, right = line.split("=", 1)
        corrections[wrong.strip()] = right.strip()
    if not corrections:
        return []
    applied: list[dict] = []
    for cue in cues:
        original = cue["text"]
        new_text = original
        for wrong, right in corrections.items():
            if wrong in new_text:
                new_text = new_text.replace(wrong, right)
        if new_text != original:
            cue["text"] = new_text
            applied.append(
                {
                    "cue": cue["n"],
                    "tc": cue["tc_start"],
                    "text": original,
                    "pattern": "dictionary",
                    "matched": "(see corrections.txt)",
                    "suggestion": new_text,
                    "confidence": 1.0,
                    "applied": True,
                }
            )
    return applied


# ─── interactive review ───────────────────────────────────────────────────


def interactive_prompt(suspect: dict) -> str:
    """Render a suspect and read y/n/edit/skip from stdin. Returns the
    raw answer (lower-cased, stripped)."""
    print(file=sys.stderr)
    print(
        f"{_BOLD}Cue #{suspect['cue']}{_RST} "
        f"{_DIM}@ {suspect['tc']} · {suspect['pattern']} "
        f"(conf {suspect['confidence']:.2f}){_RST}",
        file=sys.stderr,
    )
    print(f"  {_DIM}current   :{_RST} {suspect['text']}", file=sys.stderr)
    print(f"  {_YEL}suggestion:{_RST} {suspect['suggestion']}", file=sys.stderr)
    try:
        ans = input("  apply? [y/n/edit/skip] ").strip().lower()
    except EOFError:
        ans = "skip"
    return ans


def apply_to_cue(cues: list[dict], cue_n: int, new_text: str) -> None:
    """Mutate the cue whose ``n == cue_n`` to ``new_text``."""
    for cue in cues:
        if cue["n"] == cue_n:
            cue["text"] = new_text
            return


# ─── context extraction (for --agent-review and --use-llm) ────────────────


def _srt_tc_to_seconds(tc: str) -> float:
    """SRT timestamp "HH:MM:SS,mmm" → seconds (float). Pipeline always
    writes SRT in UTF-8 with comma as the decimal separator."""
    h, m, rest = tc.split(":", 2)
    s, ms = rest.split(",", 1)
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def transcript_snippet_around(
    transcript_words: list[dict], cue_tc: str, cut_start_s: float, window_s: float = 4.0
) -> str:
    """Return a short transcript snippet around ``cue_tc`` (which is
    measured from the cut start, not the source start).

    Useful for the agent / LLM: the cue's own text is often misleading
    (that's why it's a suspect) and the raw word-level transcript
    contains the word(s) the transcriber dropped.
    """
    if not transcript_words:
        return ""
    cue_abs_s = cut_start_s + _srt_tc_to_seconds(cue_tc)
    lo, hi = cue_abs_s - window_s, cue_abs_s + window_s
    tokens: list[str] = []
    for w in transcript_words:
        if w.get("type") != "word":
            continue
        start = w.get("start")
        if start is None or start < lo or start > hi:
            continue
        text = (w.get("text") or "").strip()
        if text:
            tokens.append(text)
    return " ".join(tokens).strip()


def attach_agent_context(
    suspects: list[dict],
    cues: list[dict],
    transcript_words: list[dict],
    cut_start_s: float,
) -> None:
    """Mutate each suspect dict to add a ``context`` block with the
    surrounding cues' text + the raw word-level transcript around the
    cue's timestamp. Skips suspects that are already applied."""
    cues_by_n = {c["n"]: c for c in cues}
    for s in suspects:
        if s.get("applied"):
            continue
        n = s["cue"]
        prev = cues_by_n.get(n - 1)
        nxt = cues_by_n.get(n + 1)
        snippet = transcript_snippet_around(transcript_words, s["tc"], cut_start_s)
        s["context"] = {
            "prev_cue_text": (prev["text"].strip() if prev else None),
            "next_cue_text": (nxt["text"].strip() if nxt else None),
            "transcript_around_tc": snippet,
        }
        # Rename rule output key for consistency with the prompt schema.
        if "suggestion" in s and "rule_suggestion" not in s:
            s["rule_suggestion"] = s["suggestion"]


# ─── --use-llm: call Anthropic API (or Groq fallback) ─────────────────────


def _build_llm_prompt(srt_text: str, suspects: list[dict]) -> tuple[str, str]:
    """Return (system_prompt, user_message) for the LLM call. The system
    prompt is loaded from ``prompts/scrub_srt.md`` so the SDK-less path
    here stays in sync with the agent-review prompt."""
    system_path = SKILL_ROOT / "prompts" / "scrub_srt.md"
    system = (
        system_path.read_text()
        if system_path.exists()
        else "You are a Portuguese-language SRT proofreader."
    )
    actionable = [s for s in suspects if not s.get("applied")]
    user = (
        "Here is the full SRT file content:\n\n"
        f"```srt\n{srt_text}\n```\n\n"
        "Suspect cues to review (JSON):\n\n"
        f"```json\n{json.dumps(actionable, indent=2, ensure_ascii=False)}\n```\n\n"
        "Return a JSON object of the form:\n"
        '  {"fixes": [{"cue": <int>, "new_text": <str>, "reason": <str>}, ...]}\n\n'
        "Include only cues you're confident about. Omit ones to skip. "
        "Don't wrap the JSON in markdown — return raw JSON only."
    )
    return system, user


def _parse_llm_fixes(raw: str) -> list[dict]:
    """The LLM should return a single JSON object with a `fixes` array.
    Strip optional ```json fences and parse defensively."""
    txt = raw.strip()
    # Tolerate fenced output even though we asked for raw.
    if txt.startswith("```"):
        # Drop first and last fence lines.
        lines = txt.splitlines()
        txt = "\n".join(line for line in lines if not line.startswith("```"))
    try:
        data = json.loads(txt)
    except json.JSONDecodeError as e:
        warn(f"LLM resposta não é JSON válido: {e}")
        return []
    fixes = data.get("fixes") if isinstance(data, dict) else None
    return fixes if isinstance(fixes, list) else []


def llm_review(srt_text: str, suspects: list[dict]) -> list[dict]:
    """Call Anthropic Claude (preferred) or Groq (fallback) to review
    rule-based suspects. Returns a list of ``{cue, new_text, reason}``
    fixes the LLM is confident about. Returns ``[]`` on any failure
    (missing key, network error, malformed JSON) — caller falls back
    gracefully to rule-based handling."""
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_groq = bool(os.environ.get("GROQ_API_KEY"))
    if not (has_anthropic or has_groq):
        warn(
            "--use-llm pedido mas nenhuma API key encontrada",
            hint="defina ANTHROPIC_API_KEY ou GROQ_API_KEY no env",
        )
        return []
    system, user = _build_llm_prompt(srt_text, suspects)

    if has_anthropic:
        try:
            import anthropic
        except ImportError:
            warn(
                "pacote `anthropic` não instalado",
                hint="pip install anthropic, ou exporte só GROQ_API_KEY pra usar Groq",
            )
            return []
        try:
            client = anthropic.Anthropic()
            resp = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=2048,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            # Anthropic returns a list of content blocks; concat their text.
            raw = "".join(getattr(b, "text", "") for b in resp.content)
        except Exception as e:
            warn(f"chamada Anthropic falhou: {e}")
            return []
        return _parse_llm_fixes(raw)

    # Groq fallback — uses an OpenAI-compatible chat completions endpoint.
    try:
        from groq import Groq
    except ImportError:
        warn("pacote `groq` não instalado (e ANTHROPIC_API_KEY ausente)")
        return []
    try:
        client = Groq()
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=2048,
            temperature=0.2,
        )
        raw = resp.choices[0].message.content or ""
    except Exception as e:
        warn(f"chamada Groq falhou: {e}")
        return []
    return _parse_llm_fixes(raw)


# ─── main ─────────────────────────────────────────────────────────────────


def main() -> None:
    ap = argparse.ArgumentParser(description="Lint a brand SRT for transcription errors.")
    ap.add_argument("slug")
    ap.add_argument("cut_index", type=int)
    ap.add_argument(
        "--auto-apply",
        action="store_true",
        help="apply rule-based fixes with confidence ≥ 0.85 without asking",
    )
    ap.add_argument(
        "--use-llm",
        action="store_true",
        help=(
            "run an LLM-assisted review pass (prefers ANTHROPIC_API_KEY, "
            "falls back to GROQ_API_KEY). Applies fixes the LLM returns."
        ),
    )
    ap.add_argument(
        "--agent-review",
        action="store_true",
        help=(
            "emit a structured JSON document with context (prev/next cue, "
            "word-level transcript snippet) for an orchestrating agent to "
            "read and apply fixes via its editor. Doesn't modify the SRT."
        ),
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="only report suspects, don't modify the SRT",
    )
    ap.add_argument(
        "--corrections",
        default=None,
        help="path to a custom dictionary file (defaults to memory/messages/<slug>/corrections.txt)",
    )
    args = ap.parse_args()

    msg_dir = MESSAGES / args.slug
    cuts_file = msg_dir / "cuts_proposed.json"
    if not cuts_file.exists():
        fail(
            f"cuts_proposed.json não encontrado em {msg_dir}",
            hint="rode a Fase A (pipeline.sh <source>) primeiro",
        )
    cuts = json.loads(cuts_file.read_text())
    if args.cut_index < 1 or args.cut_index > len(cuts):
        fail(
            f"cut_index {args.cut_index} fora do range",
            hint=f"esse slug tem {len(cuts)} cortes propostos (1..{len(cuts)})",
        )
    cut = cuts[args.cut_index - 1]
    n = cut.get("n", args.cut_index)
    slug = cut["slug"]
    srt_path = msg_dir / "srts" / f"{n:02d}-{slug}.srt"
    if not srt_path.exists():
        fail(
            f"SRT não encontrado: {srt_path}",
            hint=f"rode primeiro: ./scripts/06_build_srt.py {args.slug} {args.cut_index}",
        )

    cues = parse_srt(srt_path.read_text())
    all_suspects: list[dict] = []
    applied_count = 0

    # Pass 1: dictionary corrections — always auto-apply, no prompts.
    dict_path = Path(args.corrections) if args.corrections else (msg_dir / "corrections.txt")
    dict_applied = apply_corrections_dict(cues, dict_path)
    all_suspects.extend(dict_applied)
    applied_count += len(dict_applied)

    # Pass 2: rule-based heuristics — collect, then prompt / auto-apply /
    # forward to LLM / forward to agent, depending on mode.
    rule_suspects: list[dict] = []
    rule_suspects.extend(detect_dropped_word_boundary(cues))
    rule_suspects.extend(detect_immediate_repetition(cues))
    rule_suspects.extend(detect_forbidden_ending(cues))

    # Decide the operational mode. Order of preference:
    #   1. explicit flag (--agent-review, --use-llm, --auto-apply, --dry-run)
    #   2. TTY + stdin attached → interactive
    #   3. non-TTY with rule_suspects → default to --agent-review so the
    #      orchestrating AI agent (whichever — Claude Code, Cursor, Codex,
    #      Cline, …) gets to revise instead of silently auto-applying.
    #      Lets pipeline.sh route review through the agent loop without
    #      changing its caller.
    #   4. non-TTY with no suspects → behave like --dry-run (no-op).
    explicit = args.agent_review or args.use_llm or args.auto_apply or args.dry_run
    interactive = _TTY and sys.stdin.isatty() and not explicit
    agent_mode = args.agent_review or (not explicit and not interactive and bool(rule_suspects))

    if args.dry_run or agent_mode:
        # Don't mutate; collect and emit.
        all_suspects.extend(rule_suspects)
    elif args.use_llm:
        # First collect everything for the report, then call the LLM and
        # apply its fixes on top of the rule list.
        all_suspects.extend(rule_suspects)
        srt_text_for_llm = srt_path.read_text()
        llm_fixes = llm_review(srt_text_for_llm, rule_suspects)
        for fx in llm_fixes:
            try:
                target_n = int(fx.get("cue"))
                new_text = str(fx.get("new_text", "")).strip()
            except (TypeError, ValueError):
                continue
            if not new_text:
                continue
            apply_to_cue(cues, target_n, new_text)
            applied_count += 1
            # Tag the matching suspect (if any) as applied so the report
            # reflects what changed.
            for s in all_suspects:
                if s.get("cue") == target_n and not s.get("applied"):
                    s["applied"] = True
                    s["llm_suggestion"] = new_text
                    s["llm_reason"] = fx.get("reason", "")
                    break
    elif args.auto_apply:
        for s in rule_suspects:
            if s["confidence"] >= 0.85 and s["pattern"] != "forbidden_ending":
                apply_to_cue(cues, s["cue"], s["suggestion"])
                s["applied"] = True
                applied_count += 1
            all_suspects.append(s)
    elif interactive:
        print(
            f"{_BOLD}06b_scrub_srt{_RST}  {_DIM}— {len(rule_suspects)} suspeitos em "
            f"{srt_path.name}{_RST}",
            file=sys.stderr,
        )
        for s in rule_suspects:
            ans = interactive_prompt(s)
            if ans in ("y", "yes", "s", "sim"):
                if s["pattern"] == "forbidden_ending":
                    print(
                        f"  {_YEL}!{_RST} forbidden_ending precisa de edit manual "
                        f"(não tem auto-fix aqui)",
                        file=sys.stderr,
                    )
                else:
                    apply_to_cue(cues, s["cue"], s["suggestion"])
                    s["applied"] = True
                    applied_count += 1
            elif ans in ("e", "edit"):
                try:
                    new = input("  novo texto: ").rstrip("\n")
                except EOFError:
                    new = ""
                if new:
                    apply_to_cue(cues, s["cue"], new)
                    s["applied"] = True
                    applied_count += 1
            all_suspects.append(s)
    else:
        # Should be unreachable given the agent_mode default, but kept as
        # a defensive fallback: no rule suspects + non-TTY + no flags → no-op.
        all_suspects.extend(rule_suspects)

    if not args.dry_run and not agent_mode and applied_count > 0:
        srt_path.write_text(serialize_srt(cues), encoding="utf-8")
        print(
            f"{_BOLD}wrote{_RST} {srt_path} ({_YEL}{applied_count}{_RST} fix(es) applied)",
            file=sys.stderr,
        )

    # Build the JSON output. agent_mode adds extra context fields and a
    # next_action hint so the agent reading stdout has everything it needs
    # without re-reading config files.
    if agent_mode:
        transcript_path = msg_dir / "transcript.json"
        transcript_words: list[dict] = []
        if transcript_path.exists():
            try:
                transcript_words = json.loads(transcript_path.read_text()).get("words", [])
            except json.JSONDecodeError:
                transcript_words = []
        attach_agent_context(all_suspects, cues, transcript_words, float(cut.get("start", 0)))
        output: dict = {
            "ok": True,
            "mode": "agent_review",
            "srt_path": str(srt_path),
            "transcript_path": str(transcript_path),
            "prompt_path": str(SKILL_ROOT / "prompts" / "scrub_srt.md"),
            "cut_index": args.cut_index,
            "cut": {
                "n": n,
                "slug": slug,
                "start": cut.get("start"),
                "end": cut.get("end"),
                "theme": cut.get("theme"),
                "hook": cut.get("hook"),
            },
            "suspects": all_suspects,
            "applied_count": applied_count,
            "next_action": (
                "agent should read prompt_path (system message), then for each "
                "suspect with applied=false apply a file-edit to srt_path using "
                "whichever edit tool the runtime exposes (Edit / edit_file / "
                "apply_patch / write_to_file / etc.). Run pipeline.sh "
                "--render-cut N --slug <slug> --skip-scrub when done."
            ),
        }
    else:
        output = {
            "ok": True,
            "srt": str(srt_path),
            "suspects": all_suspects,
            "applied_count": applied_count,
            "dry_run": args.dry_run,
        }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

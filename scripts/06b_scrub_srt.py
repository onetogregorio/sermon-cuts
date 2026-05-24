#!/usr/bin/env python3
"""Lint a brand SRT for likely YouTube-auto-caption errors before burn-in.

Catches the three failure modes we see most often when transcribing
sermons through YouTube auto-captions (PT-BR, ~10 cuts/week dogfooding):

  1. **dropped_word_boundary** — a function word (em/que/de/etc.) sits
     directly before a capitalized non-proper-noun. YouTube ate a word
     at a sentence boundary.
       "do que Mas não"   →  was actually  "do que nós. Mas não"
       "uma Então, aqui"  →  was actually  "uma relação. Então, aqui"

  2. **immediate_repetition** — hesitation duplicated by the transcriber.
       "um um", "que que", "a a"
     We only flag short-and-functional repetitions (≤3 chars or in a
     small allow-list) so we don't false-positive on stylistic
     repetitions like "cansa, cansa" or "lá, lá".

  3. **forbidden_ending** — a cue ends on a word from
     ``cut_validation.forbid_endings`` (porque, mas, que, para, …).
     ``05_validate_cut.py`` already checks this at cut-level; here we
     check it per-cue so the SRT itself reads well.

Plus a hands-off dictionary pass:

  4. **dictionary** — ``memory/messages/<slug>/corrections.txt`` with
     ``wrong=right`` lines applies automatically. Useful for recurring
     theological / proper-name fixes ("Quisto=Cristo").

And an opt-in LLM pass (--use-llm) when GROQ_API_KEY or
ANTHROPIC_API_KEY is in env. Currently emits a warning and skips
the LLM call — wiring the call is left for a follow-up commit so this
step can ship without an API surface change.

Usage:
    06b_scrub_srt.py <slug> <cut_index> [--auto-apply]
                                       [--use-llm]
                                       [--dry-run]
                                       [--corrections FILE]

Modes:
    interactive  (default, TTY)  prompts y/n/edit/skip per suspect
    --auto-apply                 applies confidence ≥ 0.8 silently
    --dry-run                    reports without modifying the SRT

Output: a stable JSON document on stdout shaped like
    {
      "ok": true,
      "srt": "...path...",
      "suspects": [
        {"cue": 27, "tc": "00:00:36,080",
         "text": "do que Mas não",
         "pattern": "dropped_word_boundary",
         "matched": "que Mas",
         "suggestion": "do que. Mas não",
         "confidence": 0.75, "applied": false}
      ],
      "applied_count": 0,
      "dry_run": false
    }

Reads:
    memory/messages/<slug>/cuts_proposed.json
    memory/messages/<slug>/srts/NN-slug.srt
    memory/messages/<slug>/corrections.txt   (optional)
Writes:
    memory/messages/<slug>/srts/NN-slug.srt   (in-place, unless --dry-run)
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


# ─── main ─────────────────────────────────────────────────────────────────


def main() -> None:
    ap = argparse.ArgumentParser(description="Lint a brand SRT for transcription errors.")
    ap.add_argument("slug")
    ap.add_argument("cut_index", type=int)
    ap.add_argument(
        "--auto-apply",
        action="store_true",
        help="apply rule-based fixes with confidence ≥ 0.8 without asking",
    )
    ap.add_argument(
        "--use-llm",
        action="store_true",
        help="run an LLM-assisted review pass (requires GROQ_API_KEY or ANTHROPIC_API_KEY)",
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

    # Pass 1: dictionary corrections — auto-apply, no prompts.
    dict_path = Path(args.corrections) if args.corrections else (msg_dir / "corrections.txt")
    dict_applied = apply_corrections_dict(cues, dict_path)
    all_suspects.extend(dict_applied)
    applied_count += len(dict_applied)

    # Pass 2: rule-based heuristics — collect, then prompt or auto-apply.
    rule_suspects: list[dict] = []
    rule_suspects.extend(detect_dropped_word_boundary(cues))
    rule_suspects.extend(detect_immediate_repetition(cues))
    rule_suspects.extend(detect_forbidden_ending(cues))

    if args.use_llm:
        has_groq = bool(os.environ.get("GROQ_API_KEY"))
        has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
        if not (has_groq or has_anthropic):
            warn(
                "--use-llm pedido mas nenhuma API key encontrada",
                hint="defina GROQ_API_KEY ou ANTHROPIC_API_KEY no env",
            )
        else:
            warn("--use-llm: pass LLM ainda não conectado nesta versão; rodando só rule-based")

    # Decide how to handle the rule-based suspects.
    if args.dry_run:
        all_suspects.extend(rule_suspects)
    elif args.auto_apply:
        # Threshold raised to 0.85: in practice this means only
        # immediate_repetition (conf 0.85) auto-applies silently.
        # dropped_word_boundary (0.75) and forbidden_ending (0.60) still
        # show up in the report but require manual review — they have
        # more ambiguous fixes (insert period vs. recover dropped word,
        # move cue text vs. accept short cue, etc.).
        for s in rule_suspects:
            if s["confidence"] >= 0.85 and s["pattern"] != "forbidden_ending":
                apply_to_cue(cues, s["cue"], s["suggestion"])
                s["applied"] = True
                applied_count += 1
            all_suspects.append(s)
    elif _TTY and sys.stdin.isatty():
        # Interactive review.
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
            # 'n', 'skip', empty, or anything else → leave as-is.
            all_suspects.append(s)
    else:
        # Non-interactive, non-TTY, no flags → behave like --dry-run so we
        # never modify an SRT silently in scripted environments.
        all_suspects.extend(rule_suspects)

    if not args.dry_run and applied_count > 0:
        srt_path.write_text(serialize_srt(cues), encoding="utf-8")
        print(
            f"{_BOLD}wrote{_RST} {srt_path} ({_YEL}{applied_count}{_RST} fix(es) applied)",
            file=sys.stderr,
        )

    print(
        json.dumps(
            {
                "ok": True,
                "srt": str(srt_path),
                "suspects": all_suspects,
                "applied_count": applied_count,
                "dry_run": args.dry_run,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Przelicza statystyki EuroJackpot z eurojackpot.csv i podmienia dane
na wszystkich 10 stronach (PL/EN/DE/FR/IT x statystyki/wyniki),
pomiedzy znacznikami <!--EJ:...--> ... <!--/EJ:...--> oraz w
<span id="ej-total">/<span id="ej-lastdate">.

Uruchamiane automatycznie przez .github/workflows/aktualizacja.yml
po kazdej aktualizacji eurojackpot.csv.
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).parent
CSV_PATH = ROOT / "eurojackpot.csv"

with open(CSV_PATH, encoding="utf-8") as f:
    draws = []
    for row in csv.reader(f):
        if not row or len(row) < 9:
            continue
        draws.append({
            "date": row[1],
            "main": [int(x) for x in row[2:7]],
            "euro": [int(x) for x in row[7:9]],
        })

total = len(draws)
last_date = draws[-1]["date"]


def freq_and_last(nums_range, key):
    freq = {n: 0 for n in nums_range}
    last_seen = {n: -1 for n in nums_range}
    for i, d in enumerate(draws):
        for n in d[key]:
            freq[n] += 1
            last_seen[n] = i
    return freq, last_seen


main_freq, main_last = freq_and_last(range(1, 51), "main")
euro_freq, euro_last = freq_and_last(range(1, 13), "euro")


def top_hot(freq, n):
    return [k for k, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:n]]


def top_cold(freq, n):
    return [k for k, _ in sorted(freq.items(), key=lambda kv: (kv[1], kv[0]))[:n]]


def top_overdue(last_seen, n):
    gaps = {k: total - 1 - v for k, v in last_seen.items()}
    return sorted(gaps.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


hot_main = top_hot(main_freq, 10)
cold_main = top_cold(main_freq, 10)
overdue_main = top_overdue(main_last, 10)

hot_euro = top_hot(euro_freq, 6)
cold_euro = top_cold(euro_freq, 6)
overdue_euro = top_overdue(euro_last, 6)


def kulki_html(numbers, euro=False):
    cls = "kulka euro" if euro else "kulka"
    spans = "".join(f'<span class="{cls}">{n}</span>' for n in numbers)
    return f"\n      {spans}\n    "


OVERDUE_NOTE_TEMPLATES = {
    "pl": "Najdłużej zalegają: {n1} ({c1} losowań), {n2} ({c2} losowań), {n3} ({c3} losowań).",
    "en": "Longest overdue: {n1} ({c1} draws), {n2} ({c2} draws), {n3} ({c3} draws).",
    "de": "Am längsten überfällig: {n1} ({c1} Ziehungen), {n2} ({c2} Ziehungen), {n3} ({c3} Ziehungen).",
    "fr": "Les plus en retard : {n1} ({c1} tirages), {n2} ({c2} tirages), {n3} ({c3} tirages).",
    "it": "I più ritardatari: {n1} ({c1} estrazioni), {n2} ({c2} estrazioni), {n3} ({c3} estrazioni).",
}


def overdue_note(lang):
    (n1, c1), (n2, c2), (n3, c3) = overdue_main[:3]
    return OVERDUE_NOTE_TEMPLATES[lang].format(n1=n1, c1=c1, n2=n2, c2=c2, n3=n3, c3=c3)


STATS_FILES = {
    "pl": "eurojackpot-statystyki.html",
    "en": "en/eurojackpot-statistics.html",
    "de": "de/eurojackpot-statistiken.html",
    "fr": "fr/eurojackpot-statistiques.html",
    "it": "it/statistiche-eurojackpot.html",
}
RESULTS_FILES = {
    "pl": "eurojackpot-wyniki.html",
    "en": "en/eurojackpot-results.html",
    "de": "de/eurojackpot-ergebnisse.html",
    "fr": "fr/eurojackpot-resultats.html",
    "it": "it/risultati-eurojackpot.html",
}


def replace_between(content, start_marker, end_marker, new_inner):
    pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.DOTALL)
    replacement = start_marker + new_inner + end_marker
    new_content, count = pattern.subn(lambda m: replacement, content, count=1)
    if count == 0:
        raise RuntimeError(f"Nie znaleziono znacznika {start_marker} ... {end_marker}")
    return new_content


def replace_span(content, span_id, new_text):
    pattern = re.compile(r'(<span id="' + re.escape(span_id) + r'">).*?(</span>)')
    new_content, count = pattern.subn(lambda m: m.group(1) + new_text + m.group(2), content, count=1)
    if count == 0:
        raise RuntimeError(f"Nie znaleziono span#{span_id}")
    return new_content


for lang, relpath in STATS_FILES.items():
    path = ROOT / relpath
    content = path.read_text(encoding="utf-8")
    content = replace_span(content, "ej-total", str(total))
    content = replace_span(content, "ej-lastdate", last_date)
    content = replace_between(content, "<!--EJ:HOT_MAIN-->", "<!--/EJ:HOT_MAIN-->", kulki_html(hot_main))
    content = replace_between(content, "<!--EJ:HOT_EURO-->", "<!--/EJ:HOT_EURO-->", kulki_html(hot_euro, euro=True))
    content = replace_between(content, "<!--EJ:COLD_MAIN-->", "<!--/EJ:COLD_MAIN-->", kulki_html(cold_main))
    content = replace_between(content, "<!--EJ:COLD_EURO-->", "<!--/EJ:COLD_EURO-->", kulki_html(cold_euro, euro=True))
    content = replace_between(
        content, "<!--EJ:OVERDUE_MAIN-->", "<!--/EJ:OVERDUE_MAIN-->",
        kulki_html([n for n, _ in overdue_main]),
    )
    content = replace_between(
        content, "<!--EJ:OVERDUE_NOTE-->", "<!--/EJ:OVERDUE_NOTE-->",
        f"\n      {overdue_note(lang)}\n    ",
    )
    path.write_text(content, encoding="utf-8")


def results_rows_html():
    rows = []
    for d in reversed(draws[-15:]):
        main_spans = "".join(f'<span class="mini-kulka">{n}</span>' for n in d["main"])
        euro_spans = "".join(f'<span class="mini-kulka euro">{n}</span>' for n in d["euro"])
        rows.append(
            f'        <tr><td class="data">{d["date"]}</td><td>\n'
            f'          {main_spans}\n'
            f'          {euro_spans}\n'
            f'        </td></tr>'
        )
    return "\n" + "\n".join(rows) + "\n      "


for lang, relpath in RESULTS_FILES.items():
    path = ROOT / relpath
    content = path.read_text(encoding="utf-8")
    content = replace_span(content, "ej-total", str(total))
    content = replace_span(content, "ej-lastdate", last_date)
    content = replace_between(content, "<!--EJ:RESULTS_ROWS-->", "<!--/EJ:RESULTS_ROWS-->", results_rows_html())
    path.write_text(content, encoding="utf-8")

print(f"Zaktualizowano statystyki EuroJackpot: {total} losowan, ostatnia data {last_date}")

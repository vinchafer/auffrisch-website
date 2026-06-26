#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_pricing.py - Preis-Injektor fuer die Auffrisch-Landingpage.

Single Source of Truth: pricing.json. Dieses Skript liest die Betraege dort und
schreibt sie statisch in alle HTML-Dateien (DE/EN/FR/IT): Karten, Dropdown,
SEO-Fliesstext, FAQ, JSON-LD (Offer/AggregateOffer/priceRange) sowie
Meta/OG/Twitter-Descriptions.

Warum statisch injizieren statt Laufzeit-JS: priceRange/lowPrice/highPrice und die
Meta-/OG-Felder sind SEO-relevant und muessen im ausgelieferten HTML stehen -
Crawler lesen kein nachtraeglich per JS gesetztes JSON-LD zuverlaessig.

Die Injektion ist ANKER-basiert und idempotent: jeder Preis wird ueber stabilen
umgebenden Kontext (Feldname, Tier-Label, Praeposition, value=, Kartenreihenfolge)
gefunden - nicht ueber seinen alten Zahlenwert. Mehrfaches Ausfuehren erzeugt
denselben Output (leerer git-diff = Beweis).

Aufruf:  python build_pricing.py          (schreibt)
         python build_pricing.py --check  (nur pruefen, exit 1 bei Abweichung)

Karten/Fliesstext-Format: CHF mit Hochkomma (1'500). JSON-LD: rohe Zahl (1500).
Jahrespflege (990) und Domain/Hosting (100) werden bewusst NICHT angefasst.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

FILES = [
    "index.html",
    "en/index.html",
    "fr/index.html",
    "it/index.html",
    "professionelle-website-kmu.html",
    "technologie.html",
    "webauftritt-fixpreis.html",
    "webdesign-kmu-schweiz.html",
    "website-erneuern-schweiz.html",
    "website-kmu-zuerich.html",
]

# Lokalisierte Tier-Labels (Matching-Anker fuer Fliesstext). Reihenfolge der
# Karten-/Dropdown-/Listen-Tiers ist immer: starter, komplett, online_praesenz.
TIER_LABELS = {
    "starter":         ["Starter"],
    "komplett":        ["Komplett", "Complet", "Completo", "Complete"],
    "online_praesenz": ["Online Präsenz", "Présence en ligne",
                         "Presenza online", "Online Presence"],
}

# Zeichenklasse fuer einen Preis-Token in sichtbarem Text:
#   Ziffern, gerades '/krummes Hochkomma, Komma, Punkt, NBSP, &nbsp;-Entity-Reste
AMT = r"\d(?:[\d'’,\.]*\d)?"
# Whitespace inkl. NBSP/&nbsp; zwischen "CHF" und Zahl
WS = r"(?:&nbsp;| |\s)*"


def ap(amount: int) -> str:
    """1500 -> 1'500 (Schweizer Hochkomma-Tausender)."""
    return format(amount, ",").replace(",", "'")


def build_context(cfg: dict) -> dict:
    t = cfg["tiers"]
    starter = t["starter"]["amount"]
    komplett = t["komplett"]["amount"]
    praesenz = t["online_praesenz"]["amount"]
    mains = [starter, komplett, praesenz]
    return {
        "starter": starter,
        "komplett": komplett,
        "praesenz": praesenz,
        "low": min(mains),
        "high": max(mains),
        # Kartenreihenfolge
        "card_order": [starter, komplett, praesenz],
    }


def inject(text: str, c: dict) -> str:
    low, high = c["low"], c["high"]

    # --- R1: JSON-LD priceRange  "CHF <low>-<high>" -> roh, en-dash ---
    text = re.sub(
        r'("priceRange"\s*:\s*"CHF\s*)\d+(\s*[–-]\s*)\d+(")',
        rf'\g<1>{low}–{high}\g<3>',
        text,
    )

    # --- R2: AggregateOffer lowPrice / highPrice (roh) ---
    text = re.sub(r'("lowPrice"\s*:\s*")\d+(")',  rf'\g<1>{low}\g<2>',  text)
    text = re.sub(r'("highPrice"\s*:\s*")\d+(")', rf'\g<1>{high}\g<2>', text)

    # --- R3: JSON-LD Offer "price" je Tier, ueber "name" angekert (roh) ---
    for key, amount in (("starter", c["starter"]),
                        ("komplett", c["komplett"]),
                        ("online_praesenz", c["praesenz"])):
        for label in TIER_LABELS[key]:
            text = re.sub(
                r'("name"\s*:\s*"' + re.escape(label) +
                r'[^"]*"(?:(?!"price").)*?"price"\s*:\s*")\d+',
                rf'\g<1>{amount}',
                text,
                flags=re.S,
            )

    # --- R5: Bereichsangabe "CHF <low> bis CHF <high>" ---
    text = re.sub(
        r'(CHF' + WS + r')' + AMT + r'(' + WS + r'bis' + WS + r'CHF' + WS + r')' + AMT,
        rf'\g<1>{ap(low)}\g<2>{ap(high)}',
        text,
    )

    # --- R6b: "CHF <x> (Komplett" / "CHF <x> (Online Praesenz"  (Preis vor Name) ---
    for amount, label in ((c["komplett"], "Komplett"),
                          (c["praesenz"], "Online Präsenz")):
        text = re.sub(
            r'(CHF' + WS + r')' + AMT + r'(' + WS + r'\(' + re.escape(label) + r')',
            rf'\g<1>{ap(amount)}\g<2>',
            text,
        )

    # --- R6a: "<Label> CHF <x>"  (Name direkt vor Preis, Listen/SEO-Text) ---
    for key, amount in (("starter", c["starter"]),
                        ("komplett", c["komplett"]),
                        ("online_praesenz", c["praesenz"])):
        for label in TIER_LABELS[key]:
            text = re.sub(
                r'(' + re.escape(label) + r'\s+CHF' + WS + r')' + AMT,
                rf'\g<1>{ap(amount)}',
                text,
            )

    # --- R4: Praeposition + CHF + Preis  -> immer der niedrigste (Start-)Preis ---
    #   "ab CHF", "from CHF", "des CHF" (dès), "da CHF" (it). Deckt Meta/OG/Twitter/
    #   JSON-LD-description/Hero/card-num ab. Vereinheitlicht EN-Komma -> Hochkomma.
    text = re.sub(
        r'(\b(?:ab|from|dès|da)\s+CHF' + WS + r')' + AMT,
        rf'\g<1>{ap(low)}',
        text,
        flags=re.IGNORECASE,
    )

    # --- R7: Dropdown-Optionen, ueber value= angekert ---
    for value, amount in (("starter", c["starter"]),
                          ("komplett", c["komplett"]),
                          ("praesenz", c["praesenz"])):
        text = re.sub(
            r'(value="' + value + r'">[^<]*?CHF' + WS + r')' + AMT,
            rf'\g<1>{ap(amount)}',
            text,
        )

    # --- R8: Preis-Karten, positionell (n-te paket-price/-preis = n-ter Tier) ---
    order = c["card_order"]
    counter = {"i": 0}

    def card_repl(m):
        amount = order[counter["i"] % len(order)]
        counter["i"] += 1
        return m.group(1) + "CHF " + ap(amount)

    text = re.sub(
        r'(<div class="paket-pr(?:ice|eis)">)(?:ab\s+)?CHF' + WS + AMT,
        card_repl,
        text,
    )

    return text


def main():
    check = "--check" in sys.argv
    cfg = json.loads((ROOT / "pricing.json").read_text(encoding="utf-8"))
    c = build_context(cfg)

    changed = []
    for rel in FILES:
        path = ROOT / rel
        original = path.read_text(encoding="utf-8")
        updated = inject(original, c)
        if updated != original:
            changed.append(rel)
            if not check:
                path.write_text(updated, encoding="utf-8")

    if check:
        if changed:
            print("ABWEICHUNG - HTML nicht synchron mit pricing.json:")
            for r in changed:
                print("  ", r)
            sys.exit(1)
        print("OK - alle HTML synchron mit pricing.json.")
    else:
        if changed:
            print("Aktualisiert:")
            for r in changed:
                print("  ", r)
        else:
            print("Keine Aenderung - bereits synchron.")


if __name__ == "__main__":
    main()

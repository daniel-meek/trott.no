#!/usr/bin/env python3

"""Generer const-blokker til index.html fra dag.csv og unnskyldninger.txt.

Kjor: python oppdater_dag_og_unnskyldninger.py
Filene leses fra samme mappe som skriptet. index.html endres ikke.
"""

import csv
import io
import json
import sys
from pathlib import Path

DAGER = {"mandag": 1, "tirsdag": 2, "onsdag": 3, "torsdag": 4, "fredag": 5, "lørdag": 6, "søndag": 0}

def les_utf8(path):
    tekst = path.read_text(encoding="utf-8-sig")
    if "\ufffd" in tekst:
        raise ValueError(f"{path.name}: inneholder ødelagte tegn (�). Lagre originalen som UTF-8.")
    return tekst


def js(verdi):
    return (json.dumps(verdi, ensure_ascii=False)
            .replace("<", "\\u003c")
            .replace("\u2028", "\\u2028")
            .replace("\u2029", "\\u2029"))


def generer(mappe):
    tabell = {nummer: [] for nummer in DAGER.values()}
    sett = set()
    reader = csv.DictReader(io.StringIO(les_utf8(mappe / "dag.csv")), delimiter=";")
    if reader.fieldnames != ["dag", "tid", "kommentar"]:
        raise ValueError("dag.csv må ha overskriften dag;tid;kommentar.")
    for rad in reader:
        linje = reader.line_num
        if None in rad or any(v is None for v in rad.values()):
            raise ValueError(f"dag.csv, linje {linje}: forventet tre kolonner.")
        dag = rad["dag"].strip().lower()
        if dag not in DAGER:
            raise ValueError(f"dag.csv, linje {linje}: ukjent dag {dag!r}.")
        tid = rad["tid"].strip().replace(":", "")
        if not tid.isascii() or not tid.isdigit() or len(tid) > 4:
            raise ValueError(f"dag.csv, linje {linje}: ugyldig tid {tid!r}.")
        tid = int(tid)
        if tid // 100 > 23 or tid % 100 > 59:
            raise ValueError(f"dag.csv, linje {linje}: ugyldig klokkeslett.")
        tekst = rad["kommentar"].strip()
        if not tekst:
            raise ValueError(f"dag.csv, linje {linje}: mangler kommentar.")
        nummer = DAGER[dag]
        if (nummer, tid) in sett:
            raise ValueError(f"dag.csv, linje {linje}: duplikat for {dag} kl. {tid:04d}.")
        sett.add((nummer, tid))
        tabell[nummer].append({"tid": tid, "tekst": tekst})
    for dag, nummer in DAGER.items():
        tabell[nummer].sort(key=lambda rad: rad["tid"])
        if not tabell[nummer] or tabell[nummer][0]["tid"] != 0:
            raise ValueError(f"dag.csv: {dag} må ha en oppføring ved 0000.")

    unnskyldninger = [linje.strip() for linje in
                     les_utf8(mappe / "unnskyldninger.txt").splitlines() if linje.strip()]
    if not unnskyldninger:
        raise ValueError("unnskyldninger.txt er tom.")

    linjer = ["const tidstabell = {"]
    for dag, nummer in DAGER.items():
        linjer.append(f"    {nummer}: [ // {dag.capitalize()}")
        for rad in tabell[nummer]:
            linjer.append("        { tid: " + str(rad["tid"]) +
                          ", tekst: " + js(rad["tekst"]) + " },")
        linjer.append("    ],")
    linjer.extend(["};", "", "const unnskyldninger = ["])
    linjer.extend("    " + js(tekst) + "," for tekst in unnskyldninger)
    linjer.extend(["];", ""])
    output = mappe / "oppdatert_tekst.js"
    output.write_text("\n".join(linjer), encoding="utf-8")
    return output, sum(map(len, tabell.values())), len(unnskyldninger)


def main():
    try:
        output, antall_dager, antall_unnskyldninger = generer(Path(__file__).resolve().parent)
    except (OSError, UnicodeError, ValueError) as feil:
        print(f"Feil: {feil}", file=sys.stderr)
        return 1
    print(f"Laget {output.name}: {antall_dager} tidsoppføringer og "
          f"{antall_unnskyldninger} unnskyldninger.")
    print("Erstatt de eksisterende const-blokkene i index.html med innholdet.")
    print("index.html og kildefilene er ikke endret.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

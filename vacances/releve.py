"""Lecture du relevé de paye (PDF) pour contre-vérifier les heures et les dates d'une période.

Les relevés n'ont pas tous la même présentation : la lecture repère les lignes qui parlent
d'heures (« Heures travaillées », « Salaire régulier », « Temps supplémentaire »…) et prend le
premier nombre qui suit, en ignorant les montants en $, les taux et les cumuls annuels.
"""

import datetime as dt
import io
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from . import calcul

MOIS = {
    "janvier": 1, "janv": 1, "février": 2, "fevrier": 2, "févr": 2, "fevr": 2, "mars": 3, "avril": 4, "avr": 4,
    "mai": 5, "juin": 6, "juillet": 7, "juil": 7, "août": 8, "aout": 8, "septembre": 9, "sept": 9,
    "octobre": 10, "oct": 10, "novembre": 11, "nov": 11, "décembre": 12, "decembre": 12, "déc": 12, "dec": 12,
}

MOTS_HEURES = re.compile(r"heure|\bhres?\b|\bhrs?\b|r[ée]guli[eè]r|normal|travaill|temps\s+suppl|suppl[ée]mentaire",
                         re.IGNORECASE)
# Lignes à ignorer : cumuls, taux, banques d'heures, vacances déjà payées…
MOTS_EXCLUS = re.compile(r"cumul|annuel|à ce jour|a ce jour|\bytd\b|banque|solde|taux|vacances|cong[ée]|maladie",
                         re.IGNORECASE)
MOT_TOTAL = re.compile(r"total", re.IGNORECASE)
NOMBRE = re.compile(r"(?<![\d.,/-])(\d{1,3}(?:[  ]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)(?![\d/-])"
                    r"(\s*[$%])?")

DATE_ISO = re.compile(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b")
DATE_JMA = re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b")
DATE_TEXTE = re.compile(r"\b(\d{1,2})(?:er)?\s+([a-zéû]+)\.?\s+(\d{4})\b", re.IGNORECASE)


@dataclass
class Analyse:
    lisible: bool
    heures: list = field(default_factory=list)  # [(libellé, Decimal, est_total)]
    dates: set = field(default_factory=set)

    @property
    def suggestion(self):
        """Le nombre d'heures le plus probable : la ligne « total » s'il y en a une, sinon la somme."""
        totaux = [h for _, h, total in self.heures if total]
        if totaux:
            return totaux[0]
        if self.heures:
            return sum(h for _, h, _ in self.heures)
        return None


@dataclass
class Verification:
    statut: str  # "ok", "attention" ou "inconnu"
    message: str
    suggestion: Decimal | None = None


def extraire_texte(contenu):
    from pypdf import PdfReader  # importé ici : le démarrage reste rapide
    lecteur = PdfReader(io.BytesIO(contenu))
    return "\n".join((page.extract_text() or "") for page in lecteur.pages)


def analyser(contenu):
    try:
        texte = extraire_texte(contenu)
    except Exception:  # PDF protégé ou abîmé
        return Analyse(lisible=False)
    return analyser_texte(texte)


def analyser_texte(texte):
    analyse = Analyse(lisible=bool(texte.strip()))
    for ligne in texte.splitlines():
        analyse.dates.update(_dates(ligne))
        mot = MOTS_HEURES.search(ligne)
        if not mot or MOTS_EXCLUS.search(ligne):
            continue
        for m in NOMBRE.finditer(ligne, mot.end()):
            if m.group(2):  # montant en $ ou pourcentage
                continue
            try:
                valeur = Decimal(m.group(1).replace(" ", "").replace(" ", "").replace(",", "."))
            except InvalidOperation:
                continue
            if Decimal("0.25") <= valeur <= 300:
                libelle = ligne[:mot.start()].strip() + " " + mot.group(0)
                analyse.heures.append((libelle.strip(), valeur, bool(MOT_TOTAL.search(ligne))))
            break  # le premier nombre de la ligne est celui des heures
    return analyse


def _dates(ligne):
    trouvees = set()
    for a, m, j in DATE_ISO.findall(ligne):
        trouvees.add(_date(int(a), int(m), int(j)))
    for j, m, a in DATE_JMA.findall(ligne):
        trouvees.add(_date(int(a), int(m), int(j)))
    for j, mois, a in DATE_TEXTE.findall(ligne):
        if mois.lower() in MOIS:
            trouvees.add(_date(int(a), MOIS[mois.lower()], int(j)))
    trouvees.discard(None)
    return trouvees


def _date(a, m, j):
    try:
        return dt.date(a, m, j)
    except ValueError:
        return None


def verifier(analyse, heures, debut=None, fin=None):
    if not analyse.lisible:
        return Verification("inconnu", "Ce relevé ne contient pas de texte lisible (PDF numérisé) : "
                                       "vérification impossible.")
    suggestion = analyse.suggestion
    if suggestion is None:
        return Verification("inconnu", "Aucun nombre d'heures reconnu dans ce relevé.")
    trouve = calcul.formater_nombre(suggestion)
    dates_absentes = [d for d in (debut, fin) if d and analyse.dates and d not in analyse.dates]
    note_dates = ""
    if dates_absentes:
        note_dates = f" Attention : la date {dates_absentes[0].isoformat()} n'apparaît pas dans le relevé."
    if heures is None:
        return Verification("attention", f"Le relevé indique {trouve} h.{note_dates}", suggestion)
    valeurs = {h for _, h, _ in analyse.heures} | {suggestion}
    if Decimal(heures) in valeurs:
        statut = "attention" if dates_absentes else "ok"
        return Verification(statut, f"Le relevé confirme {calcul.formater_nombre(heures)} h.{note_dates}")
    return Verification("attention", f"Le relevé indique {trouve} h, tu as entré "
                                     f"{calcul.formater_nombre(heures)} h.{note_dates}", suggestion)

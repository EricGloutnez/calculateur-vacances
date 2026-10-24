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

MOTS_HEURES = re.compile(r"heure|(?<![a-zà-ÿ])hres?\b|(?<![a-zà-ÿ])hrs?\b|r[ée]guli[eè]r|normal|travaill|temps\s+suppl|suppl[ée]mentaire",
                         re.IGNORECASE)
# Lignes à ignorer : cumuls, taux, banques d'heures, vacances déjà payées…
MOTS_EXCLUS = re.compile(r"cumul|annuel|à ce jour|a ce jour|\bytd\b|banque|solde|taux|vacances|cong[ée]|maladie",
                         re.IGNORECASE)
MOT_TOTAL = re.compile(r"total", re.IGNORECASE)
MOTS_GAINS = re.compile(r"^\s*(?:total\s+des\s+gains|gains\s+bruts?|salaire\s+brut|brut|gains)\b", re.IGNORECASE)
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
    gains: Decimal | None = None  # salaire brut de la période

    @property
    def periode(self):
        """(début, fin) : les deux premières dates du relevé, si elles forment une période de paye."""
        dates = sorted(self.dates)
        if len(dates) >= 2 and 6 <= (dates[1] - dates[0]).days <= 31:
            return dates[0], dates[1]
        return None

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
    suggestion: Decimal | None = None  # heures du relevé, si elles diffèrent
    periode: tuple | None = None  # dates du relevé, si elles diffèrent


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
        if analyse.gains is None and MOTS_GAINS.search(ligne):
            analyse.gains = _premier_montant(ligne)
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


def _premier_montant(ligne):
    for m in NOMBRE.finditer(ligne):
        try:
            return Decimal(m.group(1).replace("\u00a0", "").replace(" ", "").replace(",", "."))
        except InvalidOperation:
            return None
    return None


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


def verifier(analyse, heures, debut=None, fin=None, taux=None):
    if not analyse.lisible:
        return Verification("inconnu", "Ce relevé ne contient pas de texte lisible (PDF numérisé) : "
                                       "vérification impossible.")
    suggestion = analyse.suggestion
    if suggestion is None:
        return Verification("inconnu", "Aucun nombre d'heures reconnu dans ce relevé.")
    trouve = calcul.formater_nombre(suggestion)
    notes = []
    periode = analyse.periode
    if periode and (debut, fin) != periode:
        notes.append(f"Le relevé couvre du {periode[0].isoformat()} au {periode[1].isoformat()}.")
    else:
        periode = None
        absentes = [d for d in (debut, fin) if d and analyse.dates and d not in analyse.dates]
        if absentes:
            notes.append(f"La date {absentes[0].isoformat()} n'apparaît pas dans le relevé.")
    if heures is not None and analyse.gains and taux and Decimal(heures) > 0:
        taux_releve = calcul.arrondir(analyse.gains / Decimal(heures))
        if abs(taux_releve - Decimal(taux)) > Decimal("0.01"):
            notes.append(f"Brut du relevé : {calcul.formater_argent(analyse.gains)} ÷ "
                         f"{calcul.formater_nombre(heures)} h = {calcul.formater_argent(taux_releve)}/h, "
                         f"ton taux est {calcul.formater_argent(taux)}/h.")
    if heures is None:
        message, ok, suggere = f"Le relevé indique {trouve} h.", False, suggestion
    elif Decimal(heures) in ({h for _, h, _ in analyse.heures} | {suggestion}):
        message, ok, suggere = f"Heures confirmées par le relevé : {calcul.formater_nombre(heures)} h.", True, None
    else:
        message, ok, suggere = (f"Le relevé indique {trouve} h, tu as entré {calcul.formater_nombre(heures)} h.",
                                False, suggestion)
    statut = "ok" if ok and not notes else "attention"
    return Verification(statut, " ".join([message, *notes]), suggere, periode)

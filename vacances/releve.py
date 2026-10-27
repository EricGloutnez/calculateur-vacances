"""Lecture du relevé de paye (PDF) pour contre-vérifier les heures et les dates d'une période.

Les relevés n'ont pas tous la même présentation : la lecture repère les lignes qui parlent
d'heures (« Heures travaillées », « Salaire régulier », « Temps supplémentaire »…) et prend le
premier nombre qui suit, en ignorant les montants en $, les taux et les cumuls annuels.
"""

import datetime as dt
import io
import re
from collections import namedtuple
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
MOTS_GAINS = re.compile(r"(?:total\s+des\s+gains|gains\s+bruts?|salaire\s+brut|\bbrut|gains)\b", re.IGNORECASE)
MOT_FERIE = re.compile(r"f[ée]ri[ée]", re.IGNORECASE)
MOT_VACANCES_VERSEES = re.compile(r"vacances\s+vers[ée]es?|paie\s+de\s+vacances|indemnit[ée]\s+de\s+vacances",
                                  re.IGNORECASE)

# Une ligne d'heures du relevé : heures et montant gagné pour ces heures (si on le trouve).
LigneHeures = namedtuple("LigneHeures", "libelle heures total montant")
NOMBRE = re.compile(r"(?<![\d.,/-])(\d{1,3}(?:[  ]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)(?![\d/-])"
                    r"(\s*[$%])?")

DATE_ISO = re.compile(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b")
DATE_JMA = re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b")
DATE_TEXTE = re.compile(r"\b(\d{1,2})(?:er)?\s+([a-zéû]+)\.?\s+(\d{4})\b", re.IGNORECASE)


@dataclass
class Analyse:
    lisible: bool
    heures: list = field(default_factory=list)  # [LigneHeures]
    dates: set = field(default_factory=set)
    gains: Decimal | None = None  # salaire brut total de la période
    ferie: Decimal = Decimal(0)  # paie de jour(s) férié(s) de la période
    vacances_versees: Decimal = Decimal(0)  # vacances payées sur cette paye ($)
    vacances_heures: Decimal | None = None  # heures de vacances payées, si le relevé les indique

    def taux(self, heures=None):
        """Taux horaire calculé : montant brut des heures ÷ nombre d'heures (férié exclu)."""
        lignes = [l for l in self.heures if not l.total and l.montant is not None]
        nb = sum((l.heures for l in lignes), Decimal(0))
        if nb > 0:
            return (sum(l.montant for l in lignes) / nb).quantize(Decimal("0.0001"))
        heures = heures if heures is not None else self.suggestion
        if self.gains and heures and Decimal(heures) > 0:  # relevé sans montant par ligne : brut total
            return ((self.gains - self.ferie) / Decimal(heures)).quantize(Decimal("0.0001"))
        return None

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
        totaux = [l.heures for l in self.heures if l.total]
        if totaux:
            return totaux[0]
        if self.heures:
            return sum(l.heures for l in self.heures)
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
        gains = MOTS_GAINS.search(ligne)
        if analyse.gains is None and gains:
            # Le montant courant suit le mot (« Gains 4 712.50 ») ; un nombre placé avant est le cumul.
            analyse.gains = (_nombres(ligne, gains.end()) or [None])[0]
        mot_vacances = MOT_VACANCES_VERSEES.search(ligne)
        if mot_vacances:
            # Même disposition que les autres gains : montants de la période (puis cumul) avant le
            # libellé, quantité après (« 1 000.00 1 000.00Vacances versées 16.00 »).
            avant = _nombres(ligne[:mot_vacances.start()])
            apres = _nombres(ligne, mot_vacances.end(), sans_unite=True)
            if avant:
                analyse.vacances_versees += avant[0]
                if apres and apres[0] > 0:
                    analyse.vacances_heures = (analyse.vacances_heures or Decimal(0)) + apres[0]
            elif apres:  # « Vacances versées 0.00 » : un seul nombre, le montant
                analyse.vacances_versees += apres[0]
            continue
        if MOT_FERIE.search(ligne):
            # « 212.50 212.50Congé Férié » : le premier nombre est le montant de la période.
            analyse.ferie += (_nombres(ligne) or [Decimal(0)])[0]
            continue
        mot = MOTS_HEURES.search(ligne)
        if not mot or MOTS_EXCLUS.search(ligne):
            continue
        apres = _nombres(ligne, mot.end(), sans_unite=True)
        if not apres:
            continue
        valeur = apres[0]  # le premier nombre après le libellé est celui des heures
        if Decimal("0.25") <= valeur <= 300:
            avant = _nombres(ligne[:mot.start()])
            if avant:  # « 4 500.00 8 750.00 140.00Hres régulières 72.00 » : montant de la période en tête
                montant = avant[0]
            elif len(apres) >= 3:  # « Salaire régulier 80,00 25,00 2 000,00 » : heures, taux, montant
                montant = apres[2]
            else:
                montant = None
            analyse.heures.append(LigneHeures(mot.group(0), valeur, bool(MOT_TOTAL.search(ligne)), montant))
    return analyse


def _nombres(ligne, debut=0, sans_unite=False):
    """Les nombres de la ligne à partir de `debut` ; `sans_unite` écarte ceux suivis de $ ou %."""
    valeurs = []
    for m in NOMBRE.finditer(ligne, debut):
        if sans_unite and m.group(2):
            continue
        try:
            valeurs.append(Decimal(m.group(1).replace("\u00a0", "").replace(" ", "").replace(",", ".")))
        except InvalidOperation:
            pass
    return valeurs


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
    elif Decimal(heures) in ({l.heures for l in analyse.heures} | {suggestion}):
        message, ok, suggere = f"Heures confirmées par le relevé : {calcul.formater_nombre(heures)} h.", True, None
    else:
        message, ok, suggere = (f"Le relevé indique {trouve} h, tu as entré {calcul.formater_nombre(heures)} h.",
                                False, suggestion)
    statut = "ok" if ok and not notes else "attention"
    return Verification(statut, " ".join([message, *notes]), suggere, periode)

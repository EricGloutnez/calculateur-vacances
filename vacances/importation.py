"""Ajout de périodes à partir de relevés de paye : un relevé dans le formulaire, ou plusieurs d'un coup."""

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from . import calcul, releve
from .db import Base


@dataclass
class Resultat:
    ajoutees: list = field(default_factory=list)  # [(début, fin)]
    deja_la: list = field(default_factory=list)  # [nom du fichier]
    illisibles: list = field(default_factory=list)  # [nom du fichier]
    vacances: int = 0  # entrées « vacances prises » créées


def vacances_deja_inscrites(base, debut, fin):
    """Montant des vacances prises inscrites entre deux dates (incluses)."""
    return sum((-e.montant for e in base.entrees() if e.type == "vacances" and debut <= e.debut <= fin),
               Decimal(0))


def inscrire_vacances_versees(base, analyse, debut, fin):
    """Les vacances payées sur ce relevé deviennent une entrée « vacances prises », une seule fois.

    Retourne True si une entrée a été créée.
    """
    a_inscrire = analyse.vacances_versees - vacances_deja_inscrites(base, debut, fin)
    if a_inscrire <= 0:
        return False
    note = "Vacances versées (relevé)"
    if analyse.vacances_heures:
        note += f", {calcul.formater_nombre(analyse.vacances_heures)} h"
    base.ajouter_vacances(fin, montant=a_inscrire, note=note)
    return True


def ajouter_releves(base, chemins):
    """Crée une période par relevé (dates, heures, taux, férié, vacances versées) et y joint le PDF."""
    resultat = Resultat()
    lus = []
    for chemin in chemins:
        nom = Path(chemin).name
        try:
            _nom, contenu = Base.lire_pdf(chemin)
        except ValueError:
            resultat.illisibles.append(nom)
            continue
        analyse = releve.analyser(contenu)
        if not analyse.lisible or analyse.periode is None or analyse.suggestion is None:
            resultat.illisibles.append(nom)
            continue
        lus.append((analyse.periode, nom, contenu, analyse))
    for (debut, fin), nom, contenu, analyse in sorted(lus, key=lambda x: x[0]):
        if base.periode_existe(debut):
            resultat.deja_la.append(nom)
            continue
        taux = analyse.taux()
        if taux is None and base.taux <= 0:
            resultat.illisibles.append(nom)
            continue
        id_ = base.ajouter_periode(debut, fin, analyse.suggestion, taux=taux, ferie=analyse.ferie or None)
        base.joindre_releve(id_, nom, contenu)
        if taux is not None:
            base.taux = taux  # le relevé le plus récent donne le taux courant
        resultat.ajoutees.append((debut, fin))
        if inscrire_vacances_versees(base, analyse, debut, fin):
            resultat.vacances += 1
    return resultat

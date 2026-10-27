"""Relecture des relevés de paye déjà enregistrés, pour revalider les périodes."""

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from . import importation, releve

TOLERANCE_TAUX = Decimal("0.005")


@dataclass
class Ecart:
    entree: object  # db.Entree
    element: str  # "Début", "Fin", "Heures", "Taux", "Férié" ou "Vacances versées"
    enregistre: object
    selon_releve: object
    analyse: object = None  # le relevé lu (pour inscrire les vacances versées)


@dataclass
class Rapport:
    verifies: int = 0
    illisibles: list = field(default_factory=list)  # [db.Entree]
    ecarts: list = field(default_factory=list)  # [Ecart]


def revalider(base):
    """Relit le relevé de chaque période et liste ce qui ne concorde pas avec ce qui est enregistré."""
    rapport = Rapport()
    for e in base.entrees():
        if e.type != "periode" or not e.releve:
            continue
        _nom, contenu = base.lire_releve(e.id)
        analyse = releve.analyser(contenu)
        heures = analyse.suggestion
        if not analyse.lisible or heures is None:
            rapport.illisibles.append(e)
            continue
        rapport.verifies += 1
        comparaisons = []
        if analyse.periode:
            comparaisons += [("Début", e.debut, analyse.periode[0]), ("Fin", e.fin, analyse.periode[1])]
        comparaisons.append(("Heures", e.heures, heures))
        taux = analyse.taux(heures)
        if taux is not None and (e.taux is None or abs(Decimal(e.taux) - taux) > TOLERANCE_TAUX):
            rapport.ecarts.append(Ecart(e, "Taux", e.taux, taux))
        comparaisons.append(("Férié", e.ferie or Decimal(0), analyse.ferie))
        for element, enregistre, selon_releve in comparaisons:
            if enregistre != selon_releve:
                rapport.ecarts.append(Ecart(e, element, enregistre, selon_releve))
        if analyse.vacances_versees > 0:
            debut, fin = analyse.periode or (e.debut, e.fin)
            inscrites = importation.vacances_deja_inscrites(base, debut, fin)
            if inscrites < analyse.vacances_versees:
                rapport.ecarts.append(Ecart(e, "Vacances versées", inscrites, analyse.vacances_versees, analyse))
    return rapport


def appliquer(base, ecarts):
    """Corrige les périodes selon leur relevé ; retourne le nombre de périodes modifiées."""
    par_periode = defaultdict(dict)
    vacances = []
    for ecart in ecarts:
        if ecart.element == "Vacances versées":
            vacances.append(ecart)
        else:
            par_periode[ecart.entree.id][ecart.element] = ecart.selon_releve
    for id_, valeurs in par_periode.items():
        e = base.entree(id_)
        base.modifier_periode(
            id_,
            valeurs.get("Début", e.debut),
            valeurs.get("Fin", e.fin),
            valeurs.get("Heures", e.heures),
            ferie=valeurs.get("Férié", e.ferie),
            taux=valeurs.get("Taux"),
        )
    for ecart in vacances:  # vacances payées sur le relevé mais pas encore inscrites
        e = base.entree(ecart.entree.id)
        importation.inscrire_vacances_versees(base, ecart.analyse, e.debut, e.fin)
    return len(set(par_periode) | {ecart.entree.id for ecart in vacances})

"""Regroupement par année de référence et rapport à présenter à la paie (CSV pour Excel)."""

import csv
from dataclasses import dataclass, field
from decimal import Decimal

from . import calcul

TYPES = {"depart": "Solde de départ", "periode": "Période de paye", "vacances": "Vacances prises"}


def date_de_rattachement(e):
    """Une période compte dans l'année où elle se termine ; le reste, à sa date."""
    return e.fin if e.type == "periode" and e.fin else e.debut


@dataclass
class Annee:
    debut: object
    fin: object
    entrees: list = field(default_factory=list)
    gagne: Decimal = Decimal(0)
    pris: Decimal = Decimal(0)
    solde_fin: Decimal = Decimal(0)

    @property
    def libelle(self):
        return calcul.libelle_annee(self.debut)


def par_annee(entrees):
    """Entrées (ordre chronologique, avec solde cumulé) regroupées par année de référence."""
    annees = {}
    for e in entrees:
        debut, fin = calcul.annee_reference(date_de_rattachement(e))
        a = annees.setdefault(debut, Annee(debut, fin))
        a.entrees.append(e)
        if e.type == "vacances":
            a.pris += -e.montant
        else:
            a.gagne += e.montant
        a.solde_fin = e.solde
    return [annees[d] for d in sorted(annees)]


def _n(valeur):
    """Nombre au format Excel français (virgule décimale, sans séparateur de milliers)."""
    return "" if valeur is None else format(Decimal(valeur).quantize(Decimal("0.01")), "f").replace(".", ",")


def exporter_csv(base, chemin, annee=None):
    """Rapport détaillé + sommaire par année de référence, lisible dans Excel ; `annee` : début d'une seule année."""
    annees = [a for a in par_annee(base.entrees()) if annee is None or a.debut == annee]
    with open(chemin, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Calculateur de vacances — rapport"])
        w.writerow([])
        w.writerow(["Année de référence", "Début", "Fin", "Type", "Heures", "Taux horaire", "Férié",
                    "% vacances", "Montant", "Solde cumulé", "Note", "Relevé joint"])
        for a in annees:
            for e in a.entrees:
                w.writerow([a.libelle, e.debut.isoformat(), e.fin.isoformat() if e.fin else "", TYPES[e.type],
                            _n(e.heures), _n(e.taux) if e.type == "periode" else "", _n(e.ferie),
                            _n(e.pct), _n(e.montant), _n(e.solde), e.note, "oui" if e.releve else ""])
        w.writerow([])
        w.writerow(["Sommaire par année de référence (1er mai au 30 avril)"])
        w.writerow(["Année de référence", "Du", "Au", "Vacances gagnées", "Vacances prises", "Solde à la fin"])
        for a in annees:
            w.writerow([a.libelle, a.debut.isoformat(), a.fin.isoformat(), _n(a.gagne), _n(a.pris),
                        _n(a.solde_fin)])
    return annees

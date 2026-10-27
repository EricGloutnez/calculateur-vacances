import csv
import datetime as dt
from decimal import Decimal

from vacances import calcul, rapport
from vacances.db import Base

D = dt.date


def test_annee_reference():
    assert calcul.annee_reference(D(2026, 10, 21)) == (D(2026, 5, 1), D(2027, 4, 30))
    assert calcul.annee_reference(D(2027, 4, 30)) == (D(2026, 5, 1), D(2027, 4, 30))
    assert calcul.annee_reference(D(2027, 5, 1)) == (D(2027, 5, 1), D(2028, 4, 30))
    assert calcul.libelle_annee(D(2026, 5, 1)) == "2026-2027"


def test_pourcentage_selon_service():
    embauche = D(2024, 3, 15)
    assert calcul.annees_service(embauche, D(2027, 3, 14)) == 2
    assert calcul.annees_service(embauche, D(2027, 3, 15)) == 3
    assert calcul.pourcentage_selon_service(embauche, D(2025, 6, 1)) == Decimal(4)  # 30 avril 2026 : 2 ans
    assert calcul.pourcentage_selon_service(embauche, D(2026, 6, 1)) == Decimal(6)  # 30 avril 2027 : 3 ans


def test_par_annee_et_csv(tmp_path):
    b = Base(tmp_path / "v.db")
    b.pct = Decimal(4)
    b.definir_solde_depart(Decimal(100), D(2026, 1, 1))
    b.ajouter_periode(D(2026, 4, 22), D(2026, 5, 5), Decimal(70), taux=Decimal(60))  # se termine en mai
    b.ajouter_periode(D(2026, 10, 8), D(2026, 10, 21), Decimal(72), taux=Decimal("62.5"), ferie=Decimal("212.50"))
    b.ajouter_vacances(D(2026, 12, 24), montant=Decimal(50), note="Noël")
    annees = rapport.par_annee(b.entrees())
    assert [(a.libelle, a.gagne, a.pris, a.solde_fin) for a in annees] == [
        ("2025-2026", Decimal(100), Decimal(0), Decimal(100)),
        ("2026-2027", Decimal("356.50"), Decimal("50.00"), Decimal("406.50")),
    ]
    chemin = tmp_path / "rapport.csv"
    rapport.exporter_csv(b, chemin)
    lignes = list(csv.reader(open(chemin, encoding="utf-8-sig"), delimiter=";"))
    detail = [l for l in lignes if l and l[0] == "2026-2027" and len(l) > 6]
    assert detail[1][3:10] == ["Période de paye", "72,00", "62,50", "212,50", "4,00", "188,50", "456,50"]
    assert ["2026-2027", "2026-05-01", "2027-04-30", "356,50", "50,00", "406,50"] in lignes
    b.fermer()


def test_embauche_et_rappels(tmp_path):
    b = Base(tmp_path / "v.db")
    assert b.embauche is None
    b.embauche = None
    assert b.embauche == ""
    b.embauche = D(2024, 3, 15)
    assert b.embauche == D(2024, 3, 15)
    assert not b.rappel_fait("6pct_2026")
    b.marquer_rappel("6pct_2026")
    assert b.rappel_fait("6pct_2026")
    b.fermer()


def test_changer_pct_de_l_annee(tmp_path):
    b = Base(tmp_path / "v.db")
    b.pct = Decimal(4)
    b.ajouter_periode(D(2026, 4, 8), D(2026, 4, 21), Decimal(72), taux=Decimal("62.5"))  # année précédente
    b.ajouter_periode(D(2026, 10, 8), D(2026, 10, 21), Decimal(72), taux=Decimal("62.5"), ferie=Decimal("212.50"))
    assert b.changer_pct_periodes(D(2026, 5, 1), D(2027, 4, 30), Decimal(6)) == 1
    avant, apres = b.entrees()
    assert (avant.pct, avant.montant) == (Decimal(4), Decimal("180.00"))
    assert (apres.pct, apres.montant) == (Decimal(6), Decimal("282.75"))  # 4 712,50 × 6 %
    b.fermer()

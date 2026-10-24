import datetime as dt
from decimal import Decimal

import pytest

from vacances.db import Base

D = dt.date


@pytest.fixture
def base(tmp_path):
    b = Base(tmp_path / "vacances.db")
    b.taux = Decimal(25)
    b.pct = Decimal(4)
    yield b
    b.fermer()


def test_scenario_maquette(base):
    base.definir_solde_depart(Decimal(520), D(2026, 1, 1))
    base.ajouter_periode(D(2026, 9, 7), D(2026, 9, 20), Decimal(80))
    base.ajouter_periode(D(2026, 9, 21), D(2026, 10, 4), Decimal("75.5"))
    base.ajouter_vacances(D(2026, 10, 6), heures=Decimal(16), note="Action de grâce")
    base.ajouter_periode(D(2026, 10, 5), D(2026, 10, 18), Decimal(80))

    soldes = [(e.type, e.solde) for e in base.entrees()]
    assert soldes == [
        ("depart", Decimal("520")),
        ("periode", Decimal("600")),
        ("periode", Decimal("675.5")),
        ("periode", Decimal("755.5")),
        ("vacances", Decimal("355.5")),
    ]
    t = base.totaux()
    assert t.accumule == Decimal("755.50")
    assert t.pris == Decimal("400.00")
    assert t.heures_prises == Decimal(16)
    assert t.solde == Decimal("355.50")
    assert t.solde_heures == Decimal("14.22")


def test_changement_de_taux_garde_historique(base):
    base.ajouter_periode(D(2026, 1, 1), D(2026, 1, 14), Decimal(80))
    base.taux = Decimal(30)
    base.ajouter_periode(D(2026, 1, 15), D(2026, 1, 28), Decimal(80))
    montants = [e.montant for e in base.entrees()]
    assert montants == [Decimal("80.00"), Decimal("96.00")]


def test_modifier_periode_recalcule_avec_taux_d_origine(base):
    id_ = base.ajouter_periode(D(2026, 1, 1), D(2026, 1, 14), Decimal(80))
    base.taux = Decimal(50)
    base.modifier_periode(id_, D(2026, 1, 1), D(2026, 1, 14), Decimal(40))
    assert base.entree(id_).montant == Decimal("40.00")


def test_vacances_en_montant(base):
    base.ajouter_periode(D(2026, 1, 1), D(2026, 1, 14), Decimal(80))
    id_ = base.ajouter_vacances(D(2026, 2, 1), montant=Decimal("30"))
    e = base.entree(id_)
    assert e.montant == Decimal("-30.00")
    assert e.heures is None
    assert base.totaux().heures_prises == Decimal("1.2")
    base.modifier_vacances(id_, D(2026, 2, 1), heures=Decimal(2))
    assert base.entree(id_).montant == Decimal("-50.00")


def test_solde_depart_unique_et_retrait(base):
    base.definir_solde_depart(Decimal(100), D(2026, 1, 1))
    base.definir_solde_depart(Decimal(200), D(2026, 1, 1))
    assert [e.montant for e in base.entrees()] == [Decimal(200)]
    base.definir_solde_depart(Decimal(0), D(2026, 1, 1))
    assert base.entrees() == []


def test_validations(base):
    with pytest.raises(ValueError):
        base.ajouter_periode(D(2026, 1, 14), D(2026, 1, 1), Decimal(80))
    with pytest.raises(ValueError):
        base.ajouter_periode(D(2026, 1, 1), D(2026, 1, 14), Decimal(0))
    with pytest.raises(ValueError):
        base.ajouter_vacances(D(2026, 1, 1))
    with pytest.raises(ValueError):
        base.pct = Decimal(150)


def test_derniere_periode_et_doublon(base):
    assert base.derniere_periode() is None
    base.ajouter_periode(D(2026, 10, 7), D(2026, 10, 21), Decimal(80))
    base.ajouter_periode(D(2026, 9, 23), D(2026, 10, 7), Decimal(80))
    assert base.derniere_periode().debut == D(2026, 10, 7)
    assert base.periode_existe(D(2026, 10, 7))
    assert not base.periode_existe(D(2026, 10, 21))


def test_persistance_et_parametres(tmp_path):
    chemin = tmp_path / "v.db"
    b = Base(chemin)
    assert not b.est_configure
    b.taux = Decimal("27.35")
    b.maj_auto = False
    b.ajouter_periode(D(2026, 1, 1), D(2026, 1, 14), Decimal(80))
    b.fermer()
    b = Base(chemin)
    assert b.est_configure and b.taux == Decimal("27.35") and not b.maj_auto
    assert len(b.entrees()) == 1
    b.fermer()


def test_export_import(base, tmp_path):
    base.ajouter_periode(D(2026, 1, 1), D(2026, 1, 14), Decimal(80))
    sauvegarde = tmp_path / "sauvegarde.db"
    base.exporter(sauvegarde)
    base.ajouter_periode(D(2026, 1, 15), D(2026, 1, 28), Decimal(80))
    base.importer(sauvegarde)
    assert len(base.entrees()) == 1


def test_import_refuse_mauvais_fichier(base, tmp_path):
    autre = tmp_path / "autre.db"
    import sqlite3
    sqlite3.connect(autre).execute("CREATE TABLE x (y)").connection.close()
    base.ajouter_periode(D(2026, 1, 1), D(2026, 1, 14), Decimal(80))
    with pytest.raises(ValueError):
        base.importer(autre)
    assert len(base.entrees()) == 1

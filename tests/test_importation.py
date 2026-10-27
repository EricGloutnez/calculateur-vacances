import datetime as dt
from decimal import Decimal

import pytest

from vacances import importation, revalidation, sauvegarde
from vacances.db import Base
from test_releve import RAPPORT_DE_PAYE, RAPPORT_FERIE
from test_revalidation import _pdf

D = dt.date
AVEC_VACANCES = RAPPORT_FERIE.replace(" 0.00Vacances versées 0.00", " 1 000.00 1 000.00Vacances versées 16.00")


@pytest.fixture
def base(tmp_path):
    b = Base(tmp_path / "v.db")
    b.pct = Decimal(4)
    yield b
    b.fermer()


def _fichiers(tmp_path, **textes):
    chemins = []
    for nom, texte in textes.items():
        chemin = tmp_path / f"{nom}.pdf"
        chemin.write_bytes(_pdf(texte))
        chemins.append(chemin)
    return chemins


def test_ajout_de_plusieurs_releves(base, tmp_path):
    # Dans le désordre, avec un fichier qui n'est pas un relevé
    pas_un_pdf = tmp_path / "notes.pdf"
    pas_un_pdf.write_text("bonjour")
    chemins = _fichiers(tmp_path, octobre=RAPPORT_FERIE, septembre=RAPPORT_DE_PAYE) + [pas_un_pdf]
    r = importation.ajouter_releves(base, chemins)
    assert r.ajoutees == [(D(2026, 9, 24), D(2026, 10, 7)), (D(2026, 10, 8), D(2026, 10, 21))]
    assert r.illisibles == ["notes.pdf"] and r.deja_la == [] and r.vacances == 0
    montants = [(e.debut, e.montant, e.releve is not None) for e in base.entrees()]
    assert montants == [(D(2026, 9, 24), Decimal("170.00"), True), (D(2026, 10, 8), Decimal("188.50"), True)]
    assert base.taux == Decimal("62.5")
    # Les relevés déjà là ne sont pas ajoutés deux fois
    r = importation.ajouter_releves(base, chemins[:2])
    assert r.ajoutees == [] and sorted(r.deja_la) == ["octobre.pdf", "septembre.pdf"]


def test_vacances_versees_inscrites_une_seule_fois(base, tmp_path):
    r = importation.ajouter_releves(base, _fichiers(tmp_path, octobre=AVEC_VACANCES))
    assert r.vacances == 1
    vac = [e for e in base.entrees() if e.type == "vacances"]
    assert [(v.debut, v.montant) for v in vac] == [(D(2026, 10, 21), Decimal("-1000.00"))]
    assert "16,00 h" in vac[0].note
    assert revalidation.revalider(base).ecarts == []


def test_revalidation_ajoute_les_vacances_versees(base, tmp_path):
    id_ = base.ajouter_periode(D(2026, 10, 8), D(2026, 10, 21), Decimal(72), taux=Decimal("62.5"),
                               ferie=Decimal("212.50"))
    base.joindre_releve(id_, "r.pdf", _pdf(AVEC_VACANCES))
    rapport = revalidation.revalider(base)
    assert [(e.element, e.selon_releve) for e in rapport.ecarts] == [("Vacances versées", Decimal("1000.00"))]
    assert revalidation.appliquer(base, rapport.ecarts) == 1
    assert revalidation.revalider(base).ecarts == []
    assert base.totaux().pris == Decimal("1000.00")


def test_sauvegardes_toutes_gardees(base, tmp_path):
    dossier = tmp_path / "OneDrive" / "Sauvegardes"
    for i in range(12):
        sauvegarde.sauvegarder(base, dossier, dt.datetime(2026, 10, 27, 12, 0, i))
    assert len(list(dossier.iterdir())) == 12
    copie = Base(sorted(dossier.iterdir())[-1])
    assert copie.pct == Decimal(4)
    copie.fermer()


def test_archive_de_l_annee(base, tmp_path):
    import zipfile
    dossier = tmp_path / "Sauvegardes"
    importation.ajouter_releves(base, _fichiers(tmp_path, septembre=RAPPORT_DE_PAYE, octobre=RAPPORT_FERIE))
    base.ajouter_periode(D(2027, 5, 5), D(2027, 5, 18), Decimal(72), taux=Decimal("62.5"))  # année suivante
    for jour in (D(2026, 9, 30), D(2027, 4, 30), D(2027, 5, 2)):
        sauvegarde.sauvegarder(base, dossier, dt.datetime.combine(jour, dt.time(17)))
    assert sauvegarde.derniere_annee_terminee(base, D(2027, 4, 30)) is None
    assert sauvegarde.derniere_annee_terminee(base, D(2027, 5, 3)) == D(2026, 5, 1)
    archive = sauvegarde.archiver_annee(base, dossier, D(2026, 5, 1), dt.datetime(2027, 5, 3, 9))
    assert archive.name == "Sauvegarde-annee-2026-2027.zip"
    noms = sorted(zipfile.ZipFile(archive).namelist())
    assert noms == ["rapport-2026-2027.csv",
                    "releves/Releve_2026-09-24_au_2026-10-07.pdf", "releves/Releve_2026-10-08_au_2026-10-21.pdf",
                    "sauvegardes/vacances-sauvegarde-2026-09-30_170000.db",
                    "sauvegardes/vacances-sauvegarde-2027-04-30_170000.db",
                    "vacances-complete-2027-05-03.db"]
    # Les copies de l'année sont dans le zip ; celle de l'année suivante reste dans le dossier
    assert sorted(p.name for p in dossier.glob("*.db")) == ["vacances-sauvegarde-2027-05-02_170000.db"]
    # Refaire l'archive ne perd pas les copies déjà rangées dedans
    sauvegarde.archiver_annee(base, dossier, D(2026, 5, 1), dt.datetime(2027, 5, 4, 9))
    noms = zipfile.ZipFile(archive).namelist()
    assert "sauvegardes/vacances-sauvegarde-2026-09-30_170000.db" in noms and "vacances-complete-2027-05-04.db" in noms


def test_archive_base_chiffree_sans_fichier_en_clair(base, tmp_path):
    import zipfile
    importation.ajouter_releves(base, _fichiers(tmp_path, octobre=RAPPORT_FERIE))
    base.definir_mot_de_passe("secret123")
    archive = sauvegarde.archiver_annee(base, tmp_path / "S", D(2026, 5, 1), dt.datetime(2027, 5, 3))
    assert zipfile.ZipFile(archive).namelist() == ["vacances-complete-2027-05-03.db"]


def test_dossier_sauvegarde(base):
    assert base.dossier_sauvegarde is None  # jamais demandé
    base.dossier_sauvegarde = None
    assert base.dossier_sauvegarde == ""  # refusé : on ne redemande pas
    base.dossier_sauvegarde = "C:/Users/x/OneDrive"
    assert base.dossier_sauvegarde == "C:/Users/x/OneDrive"

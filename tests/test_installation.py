from pathlib import Path

import pytest

from vacances import installation, updater


@pytest.fixture
def faux_windows(tmp_path, monkeypatch):
    telecharge = tmp_path / "Downloads" / "CalculateurVacances.exe"
    telecharge.parent.mkdir()
    telecharge.write_bytes(b"nouveau")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))
    monkeypatch.setattr(updater, "chemin_exe", lambda: telecharge)
    raccourcis = []
    monkeypatch.setattr(installation, "creer_raccourcis", raccourcis.append)
    return telecharge, raccourcis


def test_chemin_installe(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert installation.chemin_installe() == tmp_path / "Programs" / "CalculateurVacances" / "CalculateurVacances.exe"
    assert installation.est_installe_ici(installation.chemin_installe())
    assert not installation.est_installe_ici(tmp_path / "Downloads" / "CalculateurVacances.exe")


def test_installer_copie_et_cree_raccourcis(faux_windows):
    _, raccourcis = faux_windows
    cible = installation.installer("1.1.3")
    assert cible.read_bytes() == b"nouveau"
    assert raccourcis == [cible]


def test_installer_met_a_jour_une_vieille_copie(faux_windows):
    cible = installation.chemin_installe()
    cible.parent.mkdir(parents=True)
    cible.write_bytes(b"ancien")
    installation.installer("1.1.3", version_installee="1.1.2")
    assert cible.read_bytes() == b"nouveau"


def test_installer_n_ecrase_pas_une_version_plus_recente(faux_windows):
    cible = installation.chemin_installe()
    cible.parent.mkdir(parents=True)
    cible.write_bytes(b"plus recent")
    installation.installer("1.1.3", version_installee="1.2.0")
    assert cible.read_bytes() == b"plus recent"


def test_doit_installer_hors_exe():
    assert not installation.doit_installer()  # en développement : pas un .exe Windows


def test_script_raccourcis_echappe_les_apostrophes():
    script = installation.script_raccourcis(Path("C:/Users/d'Arcy/AppData/Local/Programs/CV/CalculateurVacances.exe"))
    assert "'C:/Users/d''Arcy/AppData/Local/Programs/CV/CalculateurVacances.exe'" in script.replace("\\", "/")
    assert "GetFolderPath('Desktop')" in script
    assert "'Calculateur de vacances.lnk'" in script

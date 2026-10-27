import datetime as dt
from decimal import Decimal

import pytest

from vacances import chiffrement, sauvegarde
from vacances.db import Base, MotDePasseIncorrect

D = dt.date
PDF = b"%PDF-1.4\nGLOUTNEZ ERIC 507-9805 BOUL. LEDUC\n%%EOF"


def _base_remplie(chemin):
    b = Base(chemin)
    b.pct = Decimal(4)
    id_ = b.ajouter_periode(D(2026, 10, 8), D(2026, 10, 21), Decimal(72), taux=Decimal("62.5"),
                            ferie=Decimal("212.50"))
    b.joindre_releve(id_, "r.pdf", PDF)
    return b


def test_fichier_illisible_sans_mot_de_passe(tmp_path):
    chemin = tmp_path / "vacances.db"
    b = _base_remplie(chemin)
    assert b"GLOUTNEZ" in chemin.read_bytes()  # en clair avant le mot de passe
    b.definir_mot_de_passe("secret123")
    contenu = chemin.read_bytes()
    assert contenu.startswith(chiffrement.ENTETE)
    assert b"GLOUTNEZ" not in contenu and b"SQLite format" not in contenu
    # Modifications après le chiffrement : toujours écrites chiffrées
    b.ajouter_vacances(D(2026, 12, 24), montant=Decimal(50), note="Noël")
    b.fermer()
    assert b"No\xc3\xabl" not in chemin.read_bytes()
    assert not list(tmp_path.glob("*.ecriture"))

    with pytest.raises(MotDePasseIncorrect):
        Base(chemin)
    with pytest.raises(MotDePasseIncorrect):
        Base(chemin, mot_de_passe="mauvais")
    b = Base(chemin, mot_de_passe="secret123")
    assert b.chiffree and b.lire_releve(b.entrees()[0].id)[1] == PDF
    assert b.totaux().solde == Decimal("138.50")
    b.fermer()


def test_changer_puis_retirer_le_mot_de_passe(tmp_path):
    chemin = tmp_path / "vacances.db"
    b = _base_remplie(chemin)
    b.definir_mot_de_passe("premier")
    b.definir_mot_de_passe("deuxieme")
    b.fermer()
    with pytest.raises(MotDePasseIncorrect):
        Base(chemin, mot_de_passe="premier")
    b = Base(chemin, mot_de_passe="deuxieme")
    b.definir_mot_de_passe(None)
    assert not b.chiffree
    b.ajouter_vacances(D(2026, 12, 24), montant=Decimal(10))
    b.fermer()
    assert not chiffrement.est_chiffre(chemin)
    b = Base(chemin)
    assert len(b.entrees()) == 2 and not b.a_mot_de_passe
    b.fermer()


def test_sauvegardes_chiffrees_et_restauration(tmp_path):
    b = _base_remplie(tmp_path / "vacances.db")
    b.definir_mot_de_passe("secret123")
    copie = sauvegarde.sauvegarder(b, tmp_path / "OneDrive")
    assert chiffrement.est_chiffre(copie) and b"GLOUTNEZ" not in copie.read_bytes()
    b.supprimer(b.entrees()[0].id)
    b.importer(copie)
    assert len(b.entrees()) == 1
    b.fermer()
    # Une autre base avec un autre mot de passe ne peut pas la restaurer
    autre = Base(tmp_path / "autre.db")
    autre.definir_mot_de_passe("autre-mdp")
    with pytest.raises(ValueError, match="autre mot de passe"):
        autre.importer(copie)
    autre.fermer()
    sans = Base(tmp_path / "sans.db")
    with pytest.raises(ValueError, match="protégée"):
        sans.importer(copie)
    sans.fermer()

import datetime as dt
import unicodedata
from decimal import Decimal

import pytest

from vacances import revalidation
from vacances.db import Base
from test_releve import RAPPORT_DE_PAYE, RAPPORT_FERIE, _pdf_texte

D = dt.date


def _pdf(texte):
    # Le petit générateur de PDF de test ne gère ni les accents ni les parenthèses.
    texte = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return _pdf_texte([l.replace("(", "").replace(")", "") for l in texte.splitlines()])


@pytest.fixture
def base(tmp_path):
    b = Base(tmp_path / "v.db")
    b.taux = Decimal("62.5")
    b.pct = Decimal(4)
    yield b
    b.fermer()


def test_tout_concorde(base):
    id_ = base.ajouter_periode(D(2026, 9, 24), D(2026, 10, 7), Decimal(68), taux=Decimal("62.5"))
    base.joindre_releve(id_, "r.pdf", _pdf(RAPPORT_DE_PAYE))
    rapport = revalidation.revalider(base)
    assert rapport.verifies == 1 and rapport.ecarts == [] and rapport.illisibles == []


def test_ferie_oublie_puis_corrige(base):
    # Période ajoutée avant la 2.1 : mauvaises dates, sans le férié.
    id_ = base.ajouter_periode(D(2026, 10, 7), D(2026, 10, 21), Decimal(72), taux=Decimal("62.5"))
    base.joindre_releve(id_, "r.pdf", _pdf(RAPPORT_FERIE))
    rapport = revalidation.revalider(base)
    assert {(e.element, e.selon_releve) for e in rapport.ecarts} == {
        ("Début", D(2026, 10, 8)), ("Férié", Decimal("212.50"))}
    assert revalidation.appliquer(base, rapport.ecarts) == 1
    e = base.entree(id_)
    assert (e.debut, e.ferie, e.montant) == (D(2026, 10, 8), Decimal("212.50"), Decimal("188.50"))
    assert revalidation.revalider(base).ecarts == []


def test_heures_et_taux_corriges(base):
    id_ = base.ajouter_periode(D(2026, 9, 24), D(2026, 10, 7), Decimal(70), taux=Decimal(25))
    base.joindre_releve(id_, "r.pdf", _pdf(RAPPORT_DE_PAYE))
    rapport = revalidation.revalider(base)
    assert {e.element for e in rapport.ecarts} == {"Heures", "Taux"}
    revalidation.appliquer(base, rapport.ecarts)
    e = base.entree(id_)
    assert (e.heures, e.taux, e.montant) == (Decimal("68.00"), Decimal("62.5000"), Decimal("170.00"))


def test_releve_illisible(base):
    id_ = base.ajouter_periode(D(2026, 9, 24), D(2026, 10, 7), Decimal(68))
    base.joindre_releve(id_, "r.pdf", b"%PDF-1.4 abime")
    rapport = revalidation.revalider(base)
    assert rapport.verifies == 0 and [e.id for e in rapport.illisibles] == [id_]

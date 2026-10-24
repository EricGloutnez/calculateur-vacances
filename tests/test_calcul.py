import datetime as dt
from decimal import Decimal

import pytest

from vacances import calcul


@pytest.mark.parametrize("texte, attendu", [
    ("25", "25"), ("25,50", "25.50"), ("25.5", "25.5"), (" 1 234,56 $ ", "1234.56"), ("4 %", "4"),
])
def test_parse_nombre(texte, attendu):
    assert calcul.parse_nombre(texte) == Decimal(attendu)


@pytest.mark.parametrize("texte", ["", "abc", "1,2,3", "nan", "inf"])
def test_parse_nombre_invalide(texte):
    with pytest.raises(ValueError):
        calcul.parse_nombre(texte)


def test_parse_date():
    assert calcul.parse_date("2026-10-07") == dt.date(2026, 10, 7)
    assert calcul.parse_date("2026/10/07") == dt.date(2026, 10, 7)
    with pytest.raises(ValueError):
        calcul.parse_date("07-10-2026")


def test_vacances_periode():
    assert calcul.vacances_periode(Decimal(80), Decimal("25.00"), Decimal(4)) == Decimal("80.00")
    assert calcul.vacances_periode(Decimal("75.5"), Decimal(25), Decimal(4)) == Decimal("75.50")
    # arrondi au cent, moitié vers le haut : 37.5 × 23.13 × 6 % = 52.0425
    assert calcul.vacances_periode(Decimal("37.5"), Decimal("23.13"), Decimal(6)) == Decimal("52.04")
    assert calcul.vacances_periode(Decimal("1"), Decimal("0.125"), Decimal(100)) == Decimal("0.13")


def test_montant_heures():
    assert calcul.montant_heures(Decimal(16), Decimal(25)) == Decimal("400.00")


def test_cents_aller_retour():
    assert calcul.en_cents(Decimal("355.50")) == 35550
    assert calcul.de_cents(35550) == Decimal("355.50")


def test_formatage():
    assert calcul.formater_argent(Decimal("1234.5")) == "1 234,50 $"
    assert calcul.formater_argent(Decimal("-400")) == "− 400,00 $"
    assert calcul.formater_signe(Decimal("80")) == "+ 80,00 $"
    assert calcul.formater_simple(Decimal("4.50")) == "4,5"
    assert calcul.formater_simple(Decimal("80")) == "80"
    assert calcul.formater_simple(Decimal("100")) == "100"


def test_prochaine_periode():
    debut, fin = calcul.prochaine_periode(dt.date(2026, 10, 7), dt.date(2026, 10, 21))
    assert (debut, fin) == (dt.date(2026, 10, 21), dt.date(2026, 11, 4))


def test_masquer_mode_confidentiel():
    masquer = calcul.masquer
    assert masquer("1 234,50 $", True) == "••• $"
    assert masquer("68 h × 62,50 $ × 4 %", True) == "••• h × ••• $ × ••• %"
    assert masquer("68 h", False) == "68 h"

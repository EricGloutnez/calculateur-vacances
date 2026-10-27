"""Calculs et formatage (montants en Decimal, arrondis au cent)."""

import datetime as dt
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal("0.01")
DUREE_PERIODE_JOURS = 14


def parse_nombre(texte):
    """Accepte « 25,50 », « 25.50 », « 1 234,5 $ », « 4 % »."""
    t = str(texte).strip()
    for c in (" ", " ", " ", "$", "%"):
        t = t.replace(c, "")
    t = t.replace(",", ".")
    if not t:
        raise ValueError("Valeur manquante.")
    try:
        d = Decimal(t)
    except InvalidOperation:
        raise ValueError(f"Nombre invalide : « {texte} ».") from None
    if not d.is_finite():
        raise ValueError(f"Nombre invalide : « {texte} ».")
    return d


def parse_date(texte):
    t = str(texte).strip().replace("/", "-")
    try:
        return dt.date.fromisoformat(t)
    except ValueError:
        raise ValueError(f"Date invalide : « {texte} » (format AAAA-MM-JJ).") from None


def arrondir(d):
    return Decimal(d).quantize(CENT, ROUND_HALF_UP)


def vacances_periode(heures, taux, pct, ferie=0):
    """Vacances gagnées : (heures × taux + paie de férié) × pct / 100."""
    return arrondir((Decimal(heures) * Decimal(taux) + Decimal(ferie or 0)) * Decimal(pct) / 100)


def montant_heures(heures, taux):
    """Valeur en $ d'un nombre d'heures de vacances."""
    return arrondir(Decimal(heures) * Decimal(taux))


def en_cents(d):
    return int(arrondir(d) * 100)


def de_cents(c):
    return Decimal(c) / 100


def formater_nombre(d, decimales=2):
    q = Decimal(d).quantize(Decimal(1).scaleb(-decimales), ROUND_HALF_UP)
    signe = "− " if q < 0 else ""
    entier, _, frac = f"{abs(q):,.{decimales}f}".partition(".")
    entier = entier.replace(",", " ")
    return f"{signe}{entier},{frac}" if frac else f"{signe}{entier}"


def formater_argent(d):
    return f"{formater_nombre(d)} $"


def formater_signe(d):
    """« + 80,00 $ » ou « − 400,00 $ »."""
    d = Decimal(d)
    return ("+ " if d >= 0 else "") + formater_argent(d)


def formater_simple(d):
    """4 → « 4 », 4.50 → « 4,5 »."""
    d = Decimal(d).normalize()
    texte = format(d, "f")
    if "." in texte:
        texte = texte.rstrip("0").rstrip(".")
    return texte.replace(".", ",")


def prochaine_periode(debut, fin, jours=DUREE_PERIODE_JOURS):
    delta = dt.timedelta(days=jours)
    return debut + delta, fin + delta


CHIFFRES = re.compile(r"\d(?:[\d\u00a0 ,.]*\d)?")


def masquer(texte, actif):
    """Mode confidentiel : chaque nombre devient « ••• » (pour une démonstration)."""
    return CHIFFRES.sub("•••", texte) if actif else texte

import datetime as dt
from decimal import Decimal

from vacances import releve

D = dt.date

TALON = """
Employeur inc.                          Relevé de paye
Période du 2026-10-07 au 2026-10-21     Date de paie : 2026-10-24
Description          Heures   Taux     Montant    Cumul annuel
Salaire régulier     75,50    25,00    1 887,50   40 000,00
Temps supplémentaire 4,50     37,50    168,75
Total des heures     80,00
Vacances payées      0,00
Banque d'heures      12,00
Taux horaire         25,00 $
"""


def test_lit_les_heures_et_les_dates():
    a = releve.analyser_texte(TALON)
    assert a.lisible
    assert [(h, total) for _, h, total in a.heures] == [
        (Decimal("75.50"), False), (Decimal("4.50"), False), (Decimal("80.00"), True)]
    assert a.suggestion == Decimal("80.00")
    assert {D(2026, 10, 7), D(2026, 10, 21), D(2026, 10, 24)} <= a.dates


def test_verifier_ok_et_ecart():
    a = releve.analyser_texte(TALON)
    v = releve.verifier(a, Decimal(80), D(2026, 10, 7), D(2026, 10, 21))
    assert v.statut == "ok" and "confirme 80,00 h" in v.message
    v = releve.verifier(a, Decimal("75.5"), D(2026, 10, 7), D(2026, 10, 21))
    assert v.statut == "ok"  # les heures régulières seules sont aussi reconnues
    v = releve.verifier(a, Decimal(70), D(2026, 10, 7), D(2026, 10, 21))
    assert v.statut == "attention" and v.suggestion == Decimal(80)
    v = releve.verifier(a, Decimal(80), D(2026, 10, 21), D(2026, 11, 4))
    assert v.statut == "attention" and "2026-11-04" in v.message


def test_sans_total_on_additionne():
    a = releve.analyser_texte("Heures normales 70,00 24,00\nHeures supplémentaires 5,5 36,00\n")
    assert a.suggestion == Decimal("75.5")


def test_formats_de_date():
    a = releve.analyser_texte("Du 7 octobre 2026 au 21/10/2026, payé le 1er nov. 2026")
    assert {D(2026, 10, 7), D(2026, 10, 21), D(2026, 11, 1)} <= a.dates


def test_releve_illisible():
    v = releve.verifier(releve.analyser(b"%PDF-1.4 pas vraiment un pdf"), Decimal(80))
    assert v.statut == "inconnu"
    v = releve.verifier(releve.analyser_texte("Bonjour"), Decimal(80))
    assert v.statut == "inconnu"


def _pdf_texte(lignes):
    """Petit PDF valide contenant du texte (pour tester la vraie lecture)."""
    flux = "BT /F1 11 Tf 14 TL 50 780 Td " + " ".join(f"({l}) '" for l in lignes) + " ET"
    objets = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(flux)} >>\nstream\n{flux}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf, positions = "%PDF-1.4\n", []
    for i, o in enumerate(objets, 1):
        positions.append(len(pdf))
        pdf += f"{i} 0 obj\n{o}\nendobj\n"
    xref = len(pdf)
    pdf += f"xref\n0 {len(objets) + 1}\n0000000000 65535 f \n"
    pdf += "".join(f"{p:010d} 00000 n \n" for p in positions)
    pdf += f"trailer\n<< /Size {len(objets) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return pdf.encode("latin-1")


def test_lecture_d_un_vrai_pdf():
    pdf = _pdf_texte(["Periode du 2026-10-07 au 2026-10-21", "Salaire regulier 80,00 25,00 2 000,00"])
    a = releve.analyser(pdf)
    assert a.lisible and a.suggestion == Decimal("80.00")
    assert releve.verifier(a, Decimal(80), D(2026, 10, 7), D(2026, 10, 21)).statut == "ok"

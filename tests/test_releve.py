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
    assert v.statut == "ok" and "confirmées par le relevé : 80,00 h" in v.message
    v = releve.verifier(a, Decimal("75.5"), D(2026, 10, 7), D(2026, 10, 21))
    assert v.statut == "ok"  # les heures régulières seules sont aussi reconnues
    v = releve.verifier(a, Decimal(70), D(2026, 10, 7), D(2026, 10, 21))
    assert v.statut == "attention" and v.suggestion == Decimal(80)
    v = releve.verifier(a, Decimal(80), D(2026, 10, 21), D(2026, 11, 4))
    assert v.statut == "attention" and v.periode == (D(2026, 10, 7), D(2026, 10, 21))


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


# Texte extrait d'un vrai relevé (format « Rapport de paye »), données personnelles remplacées.
RAPPORT_DE_PAYE = """RAPPORT DE PAYEEMPLOYEUR EXEMPLE INC.       0I 
Période duX000 24 septembre 2026
NOM PRENOM                           07 octobre 2026  Au
Payable le123 RUE EXEMPLE                         15 octobre 2026  
VILLE  QC  A1A 1A1                  Taux hor./Période 4 250.00
Qtés Cour. Montant Cour. Qtés acc. Montant acc.Gains
  
 4 250.00Hres régulières 68.00
Hres majorées 0.00 0.00
Vacances versées 0.00
Congé Férié Versé 0.00
Déductions
 259.27RRQ
Assurance-emploi 55.25
Sommaire Montant Couru.Montant Acc.
Gains 4 250.00
 1 409.94Déductions
Paie Net 2 840.06"""


def test_rapport_de_paye():
    a = releve.analyser_texte(RAPPORT_DE_PAYE)
    assert [h for _, h, _ in a.heures] == [Decimal("68.00")]
    assert a.periode == (D(2026, 9, 24), D(2026, 10, 7))
    assert a.gains == Decimal("4250.00")
    v = releve.verifier(a, Decimal(68), D(2026, 9, 24), D(2026, 10, 7), taux=Decimal("62.50"))
    assert v.statut == "ok", v.message
    v = releve.verifier(a, Decimal(68), D(2026, 10, 8), D(2026, 10, 21), taux=Decimal("62.50"))
    assert v.statut == "attention" and v.periode == (D(2026, 9, 24), D(2026, 10, 7))
    v = releve.verifier(a, Decimal(68), D(2026, 9, 24), D(2026, 10, 7), taux=Decimal(25))
    assert v.statut == "attention" and "62,50" in v.message

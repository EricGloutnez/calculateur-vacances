"""Sauvegardes : une copie de la base à chaque fermeture (toutes gardées), et une archive zip par année
de référence quand celle-ci se termine (30 avril)."""

import datetime as dt
import os
import tempfile
import zipfile
from pathlib import Path

from . import calcul, rapport

PREFIXE = "vacances-sauvegarde-"


def dossiers_suggeres():
    """Dossiers synchronisés présents sur cet ordinateur (OneDrive, iCloud Drive), puis Documents."""
    candidats = [os.environ.get(v) for v in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial")]
    candidats += [str(Path.home() / "iCloudDrive"), str(Path.home() / "Documents")]
    vus, resultat = set(), []
    for c in candidats:
        if c and Path(c).is_dir() and c not in vus:
            vus.add(c)
            resultat.append(Path(c))
    return resultat


NOM_DOSSIER = "Sauvegardes Calculateur de vacances"


def dossier_par_defaut():
    """Dossier utilisé si aucun n'est choisi : dans OneDrive / iCloud Drive / Documents, sinon à côté des données."""
    from .db import dossier_donnees
    suggeres = dossiers_suggeres()
    return (suggeres[0] if suggeres else dossier_donnees()) / NOM_DOSSIER


def sauvegarder(base, dossier, maintenant=None):
    """Copie la base dans `dossier` ; toutes les copies sont gardées (regroupées ensuite par année)."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    maintenant = maintenant or dt.datetime.now()
    chemin = dossier / f"{PREFIXE}{maintenant:%Y-%m-%d_%H%M%S}.db"
    base.exporter(chemin)
    return chemin


def _date_copie(chemin):
    try:
        return dt.date.fromisoformat(chemin.name[len(PREFIXE):len(PREFIXE) + 10])
    except ValueError:
        return None


def copies_de_l_annee(dossier, annee_debut):
    """Copies automatiques faites pendant l'année de référence qui commence à `annee_debut`."""
    debut, fin = calcul.annee_reference(annee_debut)
    return sorted(c for c in Path(dossier).glob(f"{PREFIXE}*.db") if (d := _date_copie(c)) and debut <= d <= fin)


def chemin_archive(dossier, annee_debut):
    return Path(dossier) / f"Sauvegarde-annee-{calcul.libelle_annee(annee_debut)}.zip"


def derniere_annee_terminee(base, aujourdhui=None):
    """Début de la plus récente année de référence terminée qui contient des données, sinon None."""
    aujourdhui = aujourdhui or dt.date.today()
    debut_courante, _fin = calcul.annee_reference(aujourdhui)
    terminees = [a.debut for a in rapport.par_annee(base.entrees()) if a.debut < debut_courante]
    return max(terminees) if terminees else None


def archiver_annee(base, dossier, annee_debut, maintenant=None):
    """Zip de l'année : la base complète, les copies automatiques de l'année (retirées du dossier une
    fois dans le zip), le rapport de l'année et ses relevés PDF.

    Avec une base chiffrée, seuls les fichiers chiffrés vont dans le zip (un zip n'est pas chiffré).
    """
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    maintenant = maintenant or dt.datetime.now()
    libelle = calcul.libelle_annee(annee_debut)
    copies = copies_de_l_annee(dossier, annee_debut)
    archive = chemin_archive(dossier, annee_debut)
    temporaire = archive.with_name(archive.name + ".ecriture")
    with tempfile.TemporaryDirectory() as travail:
        travail = Path(travail)
        complete = travail / f"vacances-complete-{maintenant:%Y-%m-%d}.db"
        base.exporter(complete)
        with zipfile.ZipFile(temporaire, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(complete, complete.name)
            for copie in copies:
                z.write(copie, f"sauvegardes/{copie.name}")
            if archive.exists():  # archive refaite : on garde les copies déjà rangées dans l'ancienne
                deja = {f"sauvegardes/{c.name}" for c in copies}
                with zipfile.ZipFile(archive) as ancienne:
                    for nom in ancienne.namelist():
                        if nom.startswith("sauvegardes/") and nom not in deja:
                            z.writestr(nom, ancienne.read(nom))
            if not base.chiffree:
                fichier_rapport = travail / f"rapport-{libelle}.csv"
                rapport.exporter_csv(base, fichier_rapport, annee=annee_debut)
                z.write(fichier_rapport, fichier_rapport.name)
                debut, fin = calcul.annee_reference(annee_debut)
                for e in base.entrees():
                    if e.releve and debut <= rapport.date_de_rattachement(e) <= fin:
                        nom, contenu = base.lire_releve(e.id)
                        z.writestr(f"releves/{nom}", contenu)
        with zipfile.ZipFile(temporaire) as z:
            if z.testzip() is not None:
                raise OSError("L'archive créée est endommagée.")
    os.replace(temporaire, archive)
    for copie in copies:  # elles sont maintenant dans le zip
        try:
            copie.unlink()
        except OSError:
            pass
    return archive

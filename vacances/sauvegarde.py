"""Sauvegarde automatique : une copie de la base à chaque fermeture, dans le dossier choisi."""

import datetime as dt
import os
from pathlib import Path

NB_A_GARDER = 10
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


def sauvegarder(base, dossier, maintenant=None):
    """Copie la base dans `dossier` et ne garde que les NB_A_GARDER copies les plus récentes."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    maintenant = maintenant or dt.datetime.now()
    chemin = dossier / f"{PREFIXE}{maintenant:%Y-%m-%d_%H%M%S}.db"
    base.exporter(chemin)
    for vieux in sorted(dossier.glob(f"{PREFIXE}*.db"))[:-NB_A_GARDER]:
        try:
            vieux.unlink()
        except OSError:
            pass
    return chemin

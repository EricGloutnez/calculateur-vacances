"""Installation sur l'ordinateur : copie du .exe et raccourcis Bureau / menu Démarrer.

Aucun droit d'administrateur : l'application va dans %LOCALAPPDATA%\\Programs, comme la
plupart des applications installées « pour moi seulement ».
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import updater

NOM_APP = "Calculateur de vacances"


def dossier_installation():
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "Programs" / "CalculateurVacances"


def chemin_installe():
    return dossier_installation() / updater.NOM_EXE


def est_exe_windows():
    return getattr(sys, "frozen", False) and sys.platform == "win32"


def _meme_fichier(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def est_installe_ici(exe=None):
    return _meme_fichier(exe or updater.chemin_exe(), chemin_installe())


def doit_installer():
    """Vrai quand on lance le .exe téléchargé (ailleurs que dans le dossier d'installation)."""
    return est_exe_windows() and not est_installe_ici()


def _fichier_version():
    from .db import dossier_donnees
    return dossier_donnees() / "version_installee.txt"


def lire_version_installee():
    """Version de la copie installée (fichier à part : lisible même quand la base est chiffrée)."""
    try:
        return _fichier_version().read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def noter_version_installee(version):
    try:
        _fichier_version().parent.mkdir(parents=True, exist_ok=True)
        _fichier_version().write_text(version, encoding="utf-8")
    except OSError:
        pass


def installer(version_actuelle, version_installee=None):
    """Copie ce .exe dans le dossier d'installation et crée les raccourcis ; retourne le chemin installé.

    Une version installée plus récente n'est pas écrasée par un vieux téléchargement.
    """
    cible = chemin_installe()
    cible.parent.mkdir(parents=True, exist_ok=True)
    plus_recente = (
        cible.exists()
        and version_installee is not None
        and updater.parse_version(version_installee) > updater.parse_version(version_actuelle)
    )
    if not plus_recente:
        try:
            shutil.copy2(updater.chemin_exe(), cible)
        except OSError:
            if not cible.exists():  # sinon : la copie installée est ouverte, on la garde
                raise
    creer_raccourcis(cible)
    return cible


def _ps(texte):
    return "'" + str(texte).replace("'", "''") + "'"


def script_raccourcis(cible):
    cible = Path(cible)
    return f"""
$shell = New-Object -ComObject WScript.Shell
foreach ($dossier in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {{
    $lien = $shell.CreateShortcut((Join-Path $dossier {_ps(NOM_APP + '.lnk')}))
    $lien.TargetPath = {_ps(cible)}
    $lien.WorkingDirectory = {_ps(cible.parent)}
    $lien.IconLocation = {_ps(str(cible) + ',0')}
    $lien.Description = 'Calcul des vacances accumulées'
    $lien.Save()
}}
"""


def creer_raccourcis(cible):
    # PowerShell trouve le vrai Bureau, même redirigé vers OneDrive.
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-Command", script_raccourcis(cible)],
        check=True, timeout=60, env=updater.environnement_propre(),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def lancer(cible, *args):
    subprocess.Popen([str(cible), *args], env=updater.environnement_propre(), close_fds=True)

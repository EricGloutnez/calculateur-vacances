"""Mise à jour automatique à partir des « Releases » GitHub."""

import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DEPOT = "EricGloutnez/calculateur-vacances"
URL_API = f"https://api.github.com/repos/{DEPOT}/releases/latest"
URL_PAGE = f"https://github.com/{DEPOT}/releases/latest"
NOM_EXE = "CalculateurVacances.exe"


@dataclass
class Release:
    version: str
    url_exe: str | None
    url_page: str
    notes: str


def parse_version(texte):
    texte = texte.strip().lstrip("vV")
    parties = []
    for p in texte.split("."):
        chiffres = "".join(c for c in p if c.isdigit())
        parties.append(int(chiffres or 0))
    while len(parties) < 3:
        parties.append(0)
    return tuple(parties)


def analyser_release(donnees):
    url_exe = None
    for asset in donnees.get("assets", []):
        if asset.get("name", "").lower() == NOM_EXE.lower():
            url_exe = asset.get("browser_download_url")
    return Release(
        version=donnees.get("tag_name", "").lstrip("vV"),
        url_exe=url_exe,
        url_page=donnees.get("html_url") or URL_PAGE,
        notes=donnees.get("body") or "",
    )


def verifier(version_actuelle, timeout=8):
    """Retourne la Release si elle est plus récente que la version actuelle, sinon None."""
    req = urllib.request.Request(
        URL_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "CalculateurVacances"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as rep:
        donnees = json.load(rep)
    release = analyser_release(donnees)
    if parse_version(release.version) > parse_version(version_actuelle):
        return release
    return None


def chemin_exe():
    return Path(sys.executable).resolve()


def peut_installer(release):
    """Remplacement automatique seulement pour le .exe, dans un dossier où on peut écrire."""
    return (
        release.url_exe is not None
        and getattr(sys, "frozen", False)
        and sys.platform == "win32"
        and os.access(chemin_exe().parent, os.W_OK)
    )


def telecharger(release):
    exe = chemin_exe()
    nouveau = exe.with_name(exe.stem + ".nouveau.exe")
    req = urllib.request.Request(release.url_exe, headers={"User-Agent": "CalculateurVacances"})
    with urllib.request.urlopen(req, timeout=60) as rep, open(nouveau, "wb") as f:
        while bloc := rep.read(1 << 16):
            f.write(bloc)
    if nouveau.stat().st_size < 1_000_000:
        nouveau.unlink(missing_ok=True)
        raise RuntimeError("Le fichier téléchargé est incomplet.")
    return nouveau


def environnement_propre(env=None):
    """Environnement sans les variables internes de PyInstaller.

    Sinon le nouveau .exe, relancé depuis l'ancien, croit être son processus enfant et cherche
    python3XX.dll dans le dossier temporaire _MEI… de l'ancien, déjà effacé.
    """
    env = dict(os.environ if env is None else env)
    for cle in list(env):
        if cle.upper().startswith(("_PYI_", "_MEIPASS")):
            del env[cle]
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def lancer_remplacement(nouveau):
    """Un petit script attend la fermeture de l'appli, remplace le .exe et le relance."""
    exe = chemin_exe()
    script = f"""@echo off
set /a essais=0
:attente
ping -n 2 127.0.0.1 >nul
move /y "{nouveau}" "{exe}" >nul 2>&1
if not errorlevel 1 goto relance
set /a essais+=1
if %essais% lss 30 goto attente
:relance
start "" "{exe}"
del "%~f0"
"""
    fd, chemin = tempfile.mkstemp(suffix=".bat", prefix="maj_vacances_")
    with os.fdopen(fd, "w", encoding="mbcs" if sys.platform == "win32" else "utf-8") as f:
        f.write(script)
    # Console cachée (pas DETACHED_PROCESS : sans console, l'attente du script échoue).
    drapeaux = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(["cmd", "/c", chemin], creationflags=drapeaux, close_fds=True, env=environnement_propre())

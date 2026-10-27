"""Chiffrement de la base quand un mot de passe est défini (AES-256-GCM, clé tirée du mot de passe).

Format du fichier : ENTETE | sel (16 octets) | nonce (12 octets) | données chiffrées + étiquette.
Sans le bon mot de passe, le fichier est illisible ; il n'y a aucune récupération possible.
"""

import hashlib
import os
from pathlib import Path

ENTETE = b"CALCVAC-CHIFFRE-1\n"
TAILLE_SEL = 16
TAILLE_NONCE = 12


class MotDePasseIncorrect(ValueError):
    pass


def deriver_cle(mot_de_passe, sel):
    # scrypt : lent exprès, pour freiner les essais de mots de passe.
    return hashlib.scrypt(mot_de_passe.encode("utf-8"), salt=sel, n=2 ** 15, r=8, p=1, maxmem=64 * 1024 * 1024,
                          dklen=32)


def nouveau_sel():
    return os.urandom(TAILLE_SEL)


def est_chiffre(chemin):
    try:
        with open(chemin, "rb") as f:
            return f.read(len(ENTETE)) == ENTETE
    except OSError:
        return False


def chiffrer(donnees, cle, sel):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = os.urandom(TAILLE_NONCE)
    return ENTETE + sel + nonce + AESGCM(cle).encrypt(nonce, donnees, ENTETE)


def dechiffrer(blob, mot_de_passe):
    """Retourne (données, clé, sel) ; MotDePasseIncorrect si le mot de passe ne convient pas."""
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if not blob.startswith(ENTETE):
        raise ValueError("Ce fichier n'est pas une base chiffrée.")
    debut = len(ENTETE)
    sel = blob[debut:debut + TAILLE_SEL]
    nonce = blob[debut + TAILLE_SEL:debut + TAILLE_SEL + TAILLE_NONCE]
    cle = deriver_cle(mot_de_passe, sel)
    try:
        donnees = AESGCM(cle).decrypt(nonce, blob[debut + TAILLE_SEL + TAILLE_NONCE:], ENTETE)
    except InvalidTag:
        raise MotDePasseIncorrect("Mot de passe incorrect.") from None
    return donnees, cle, sel


def ecrire_atomique(chemin, octets):
    """Écrit d'abord à côté puis remplace : une panne ne laisse jamais un fichier à moitié écrit."""
    chemin = Path(chemin)
    temporaire = chemin.with_name(chemin.name + ".ecriture")
    with open(temporaire, "wb") as f:
        f.write(octets)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporaire, chemin)

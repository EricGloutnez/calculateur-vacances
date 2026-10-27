"""Base de données SQLite intégrée (un seul fichier, vacances.db)."""

import datetime as dt
import hashlib
import hmac
import os
import sqlite3
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from . import calcul

VERSION_SCHEMA = 3
TAILLE_MAX_RELEVE = 25 * 1024 * 1024  # 25 Mo
LONGUEUR_MIN_MOT_DE_PASSE = 4
ITERATIONS_MOT_DE_PASSE = 300_000

SCHEMA = """
CREATE TABLE IF NOT EXISTS parametres (
    cle    TEXT PRIMARY KEY,
    valeur TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS entrees (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    type          TEXT NOT NULL CHECK (type IN ('depart', 'periode', 'vacances')),
    date_debut    TEXT NOT NULL,
    date_fin      TEXT,
    heures        TEXT,
    taux          TEXT,
    pct           TEXT,
    montant_cents INTEGER NOT NULL,
    note          TEXT NOT NULL DEFAULT '',
    ferie         TEXT,
    cree_le       TEXT NOT NULL DEFAULT (datetime('now'))
);
-- Relevé de paye (PDF) joint à une entrée, conservé dans la base même.
CREATE TABLE IF NOT EXISTS releves (
    entree_id INTEGER PRIMARY KEY,
    nom       TEXT NOT NULL,
    contenu   BLOB NOT NULL,
    ajoute_le TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

ORDRE_TYPE = {"depart": 0, "periode": 1, "vacances": 2}


def dossier_donnees():
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "CalculateurVacances"


def chemin_par_defaut():
    return dossier_donnees() / "vacances.db"


@dataclass
class Entree:
    id: int
    type: str
    debut: dt.date
    fin: dt.date | None
    heures: Decimal | None
    taux: Decimal | None
    pct: Decimal | None
    montant: Decimal  # positif = gagné, négatif = vacances prises
    note: str
    solde: Decimal = Decimal(0)
    releve: str | None = None  # nom du PDF joint
    ferie: Decimal | None = None  # paie de jour férié comptée dans la période


@dataclass
class Totaux:
    accumule: Decimal
    accumule_heures: Decimal | None
    pris: Decimal
    heures_prises: Decimal
    solde: Decimal
    solde_heures: Decimal | None


def _dec(v):
    return Decimal(v) if v not in (None, "") else None


class Base:
    def __init__(self, chemin=None):
        self.chemin = Path(chemin) if chemin else chemin_par_defaut()
        if str(self.chemin) != ":memory:":
            self.chemin.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.chemin))
        self.conn.row_factory = sqlite3.Row
        self._migrer()

    def _migrer(self):
        self.conn.executescript(SCHEMA)
        colonnes = {r[1] for r in self.conn.execute("PRAGMA table_info(entrees)")}
        if "ferie" not in colonnes:  # bases créées avant la 2.1 : paie de férié par période
            self.conn.execute("ALTER TABLE entrees ADD COLUMN ferie TEXT")
        self.conn.execute(f"PRAGMA user_version = {VERSION_SCHEMA}")
        self.conn.commit()

    def fermer(self):
        self.conn.close()

    # --- Paramètres -------------------------------------------------------

    def _param(self, cle, defaut=None):
        row = self.conn.execute("SELECT valeur FROM parametres WHERE cle = ?", (cle,)).fetchone()
        return row["valeur"] if row else defaut

    def _set_param(self, cle, valeur):
        self.conn.execute(
            "INSERT INTO parametres (cle, valeur) VALUES (?, ?) "
            "ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
            (cle, str(valeur)),
        )
        self.conn.commit()

    @property
    def taux(self):
        return Decimal(self._param("taux", "0"))

    @taux.setter
    def taux(self, valeur):
        if Decimal(valeur) < 0:
            raise ValueError("Le taux horaire ne peut pas être négatif.")
        self._set_param("taux", Decimal(valeur))

    @property
    def pct(self):
        return Decimal(self._param("pct", "4"))

    @pct.setter
    def pct(self, valeur):
        if not 0 <= Decimal(valeur) <= 100:
            raise ValueError("Le pourcentage doit être entre 0 et 100.")
        self._set_param("pct", Decimal(valeur))

    @property
    def maj_auto(self):
        return self._param("maj_auto", "1") == "1"

    @maj_auto.setter
    def maj_auto(self, valeur):
        self._set_param("maj_auto", "1" if valeur else "0")

    @property
    def version_installee(self):
        """Version de la copie installée (inscrite par celle-ci à chaque démarrage)."""
        return self._param("version_installee")

    @version_installee.setter
    def version_installee(self, valeur):
        self._set_param("version_installee", valeur)

    @property
    def dossier_sauvegarde(self):
        """None : jamais demandé ; "" : pas de sauvegarde automatique ; sinon le dossier choisi."""
        return self._param("dossier_sauvegarde")

    @dossier_sauvegarde.setter
    def dossier_sauvegarde(self, valeur):
        self._set_param("dossier_sauvegarde", valeur or "")

    def preference(self, cle, defaut=True):
        """Préférence d'affichage oui/non (ex. afficher l'historique)."""
        return self._param(f"pref_{cle}", "1" if defaut else "0") == "1"

    def definir_preference(self, cle, valeur):
        self._set_param(f"pref_{cle}", "1" if valeur else "0")

    @property
    def premier_lancement_fait(self):
        return self._param("premier_lancement_fait") == "1"

    def marquer_premier_lancement(self):
        self._set_param("premier_lancement_fait", "1")

    # --- Mot de passe (verrou d'ouverture ; les données ne sont pas chiffrées) ----

    @property
    def a_mot_de_passe(self):
        return self._param("mot_de_passe") is not None

    def definir_mot_de_passe(self, mot_de_passe):
        """Définit le mot de passe ; None le retire."""
        if mot_de_passe is None:
            self.conn.execute("DELETE FROM parametres WHERE cle = 'mot_de_passe'")
            self.conn.commit()
            return
        if len(mot_de_passe) < LONGUEUR_MIN_MOT_DE_PASSE:
            raise ValueError(f"Le mot de passe doit avoir au moins {LONGUEUR_MIN_MOT_DE_PASSE} caractères.")
        sel = os.urandom(16)
        empreinte = _empreinte(mot_de_passe, sel, ITERATIONS_MOT_DE_PASSE)
        self._set_param("mot_de_passe", f"pbkdf2_sha256${ITERATIONS_MOT_DE_PASSE}${sel.hex()}${empreinte.hex()}")

    def verifier_mot_de_passe(self, mot_de_passe):
        stocke = self._param("mot_de_passe")
        if stocke is None:
            return True
        _algo, iterations, sel, empreinte = stocke.split("$")
        essai = _empreinte(mot_de_passe, bytes.fromhex(sel), int(iterations))
        return hmac.compare_digest(essai, bytes.fromhex(empreinte))

    @property
    def est_configure(self):
        return self._param("taux") is not None

    # --- Entrées ----------------------------------------------------------

    def ajouter_periode(self, debut, fin, heures, taux=None, ferie=None):
        """Ajoute une période ; `taux` : celui lu dans le relevé de paye, sinon celui des paramètres ;
        `ferie` : paie de jour férié de la période, comptée dans le calcul des vacances."""
        heures = Decimal(heures)
        ferie = self._valider_ferie(ferie)
        self._valider_periode(debut, fin, heures)
        taux, pct = (Decimal(taux) if taux is not None else self.taux), self.pct
        montant = calcul.vacances_periode(heures, taux, pct, ferie)
        cur = self.conn.execute(
            "INSERT INTO entrees (type, date_debut, date_fin, heures, taux, pct, montant_cents, ferie) "
            "VALUES ('periode', ?, ?, ?, ?, ?, ?, ?)",
            (debut.isoformat(), fin.isoformat(), str(heures), str(taux), str(pct), calcul.en_cents(montant),
             _str_ou_none(ferie)),
        )
        self.conn.commit()
        return cur.lastrowid

    def modifier_periode(self, id_, debut, fin, heures, ferie=None, taux=None):
        """Modifie une période ; `taux` None garde le taux de la période."""
        heures = Decimal(heures)
        ferie = self._valider_ferie(ferie)
        self._valider_periode(debut, fin, heures)
        e = self.entree(id_)
        taux = Decimal(taux) if taux is not None else e.taux
        montant = calcul.vacances_periode(heures, taux, e.pct, ferie)
        self.conn.execute(
            "UPDATE entrees SET date_debut = ?, date_fin = ?, heures = ?, taux = ?, montant_cents = ?, ferie = ? "
            "WHERE id = ?",
            (debut.isoformat(), fin.isoformat(), str(heures), str(taux), calcul.en_cents(montant),
             _str_ou_none(ferie), id_),
        )
        self.conn.commit()

    def ajouter_vacances(self, date, heures=None, montant=None, note=""):
        heures, montant = self._valeur_vacances(heures, montant)
        cur = self.conn.execute(
            "INSERT INTO entrees (type, date_debut, heures, taux, montant_cents, note) "
            "VALUES ('vacances', ?, ?, ?, ?, ?)",
            (date.isoformat(), _str_ou_none(heures), str(self.taux), calcul.en_cents(montant), note.strip()),
        )
        self.conn.commit()
        return cur.lastrowid

    def modifier_vacances(self, id_, date, heures=None, montant=None, note=""):
        heures, montant = self._valeur_vacances(heures, montant)
        self.conn.execute(
            "UPDATE entrees SET date_debut = ?, heures = ?, montant_cents = ?, note = ? WHERE id = ?",
            (date.isoformat(), _str_ou_none(heures), calcul.en_cents(montant), note.strip(), id_),
        )
        self.conn.commit()

    def definir_solde_depart(self, montant, date):
        """Un seul solde de départ ; 0 le retire."""
        montant = calcul.arrondir(montant)
        self.conn.execute("DELETE FROM entrees WHERE type = 'depart'")
        if montant != 0:
            self.conn.execute(
                "INSERT INTO entrees (type, date_debut, montant_cents) VALUES ('depart', ?, ?)",
                (date.isoformat(), calcul.en_cents(montant)),
            )
        self.conn.commit()

    def solde_depart(self):
        for e in self.entrees():
            if e.type == "depart":
                return e
        return None

    def supprimer(self, id_):
        self.conn.execute("DELETE FROM releves WHERE entree_id = ?", (id_,))
        self.conn.execute("DELETE FROM entrees WHERE id = ?", (id_,))
        self.conn.commit()

    # --- Relevés de paye (PDF) ------------------------------------------------

    @staticmethod
    def lire_pdf(chemin):
        """Lit et valide un PDF ; retourne (nom, contenu)."""
        chemin = Path(chemin)
        try:
            contenu = chemin.read_bytes()
        except OSError as err:
            raise ValueError(f"Impossible de lire « {chemin.name} » : {err.strerror or err}") from None
        if b"%PDF-" not in contenu[:1024]:
            raise ValueError(f"« {chemin.name} » n'est pas un fichier PDF.")
        if len(contenu) > TAILLE_MAX_RELEVE:
            raise ValueError(f"« {chemin.name} » est trop volumineux (maximum 25 Mo).")
        return chemin.name, contenu

    def joindre_releve(self, id_, nom, contenu):
        self.conn.execute(
            "INSERT INTO releves (entree_id, nom, contenu) VALUES (?, ?, ?) "
            "ON CONFLICT(entree_id) DO UPDATE SET nom = excluded.nom, contenu = excluded.contenu, "
            "ajoute_le = datetime('now')",
            (id_, nom, sqlite3.Binary(contenu)),
        )
        self.conn.commit()

    def lire_releve(self, id_):
        row = self.conn.execute("SELECT nom, contenu FROM releves WHERE entree_id = ?", (id_,)).fetchone()
        return (self.entree(id_).releve, bytes(row["contenu"])) if row else None

    def retirer_releve(self, id_):
        self.conn.execute("DELETE FROM releves WHERE entree_id = ?", (id_,))
        self.conn.commit()

    def entree(self, id_):
        for e in self.entrees():
            if e.id == id_:
                return e
        raise KeyError(id_)

    def entrees(self):
        """Toutes les entrées en ordre chronologique, avec le solde cumulé."""
        rows = self.conn.execute(
            "SELECT e.*, r.nom AS releve_nom FROM entrees e LEFT JOIN releves r ON r.entree_id = e.id"
        ).fetchall()
        rows = sorted(rows, key=lambda r: (r["date_debut"], ORDRE_TYPE[r["type"]], r["id"]))
        resultat, solde = [], Decimal(0)
        for r in rows:
            montant = calcul.de_cents(r["montant_cents"])
            if r["type"] == "vacances":
                montant = -montant
            solde += montant
            resultat.append(Entree(
                id=r["id"],
                type=r["type"],
                debut=dt.date.fromisoformat(r["date_debut"]),
                fin=dt.date.fromisoformat(r["date_fin"]) if r["date_fin"] else None,
                heures=_dec(r["heures"]),
                taux=_dec(r["taux"]),
                pct=_dec(r["pct"]),
                ferie=_dec(r["ferie"]),
                montant=montant,
                note=r["note"],
                solde=solde,
                releve=_nom_releve(r) if r["releve_nom"] else None,
            ))
        return resultat

    def totaux(self):
        accumule = pris = heures_prises = Decimal(0)
        for e in self.entrees():
            if e.type == "vacances":
                pris += -e.montant
                if e.heures is not None:
                    heures_prises += e.heures
                elif e.taux:
                    heures_prises += -e.montant / e.taux
            else:
                accumule += e.montant
        solde = accumule - pris
        taux = self.taux
        return Totaux(
            accumule=accumule,
            accumule_heures=(accumule / taux) if taux > 0 else None,
            pris=pris,
            heures_prises=heures_prises,
            solde=solde,
            solde_heures=(solde / taux) if taux > 0 else None,
        )

    def derniere_periode(self):
        periodes = [e for e in self.entrees() if e.type == "periode"]
        return max(periodes, key=lambda e: (e.debut, e.id)) if periodes else None

    def periode_existe(self, debut, sauf_id=None):
        row = self.conn.execute(
            "SELECT id FROM entrees WHERE type = 'periode' AND date_debut = ? AND id IS NOT ?",
            (debut.isoformat(), sauf_id),
        ).fetchone()
        return row is not None

    # --- Sauvegarde -------------------------------------------------------

    def exporter(self, destination):
        dest = sqlite3.connect(str(destination))
        try:
            self.conn.backup(dest)
        finally:
            dest.close()

    def importer(self, source):
        src = sqlite3.connect(f"file:{Path(source).as_posix()}?mode=ro", uri=True)
        try:
            tables = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            if not {"parametres", "entrees"} <= tables:
                raise ValueError("Ce fichier n'est pas une sauvegarde du calculateur de vacances.")
            src.backup(self.conn)
        finally:
            src.close()
        self._migrer()

    # --- Validation --------------------------------------------------------

    @staticmethod
    def _valider_periode(debut, fin, heures):
        if fin < debut:
            raise ValueError("La date de fin est avant la date de début.")
        if heures <= 0:
            raise ValueError("Le nombre d'heures doit être plus grand que 0.")

    @staticmethod
    def _valider_ferie(ferie):
        if ferie in (None, ""):
            return None
        ferie = Decimal(ferie)
        if ferie < 0:
            raise ValueError("La paie de férié ne peut pas être négative.")
        return ferie if ferie > 0 else None

    def _valeur_vacances(self, heures, montant):
        if heures is not None:
            heures = Decimal(heures)
            if heures <= 0:
                raise ValueError("Le nombre d'heures doit être plus grand que 0.")
            if self.taux <= 0:
                raise ValueError("Le taux horaire n'est pas encore connu : ajoute d'abord une période avec son "
                                 "relevé de paye, ou entre les vacances prises en $.")
            return heures, calcul.montant_heures(heures, self.taux)
        if montant is None or Decimal(montant) <= 0:
            raise ValueError("Le montant doit être plus grand que 0.")
        return None, calcul.arrondir(montant)


def _nom_releve(r):
    """Nom neutre du relevé, tiré des dates (le nom d'origine contient souvent le nom de l'employé)."""
    if r["date_fin"]:
        return f"Releve_{r['date_debut']}_au_{r['date_fin']}.pdf"
    return f"Releve_{r['date_debut']}.pdf"


def _empreinte(mot_de_passe, sel, iterations):
    return hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode("utf-8"), sel, iterations)


def _str_ou_none(v):
    return None if v is None else str(v)

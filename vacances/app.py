"""Interface (Tkinter) du calculateur de vacances."""

import calendar
import datetime as dt
import os
import queue
import re
import sys
import tempfile
import threading
import tkinter as tk
import webbrowser
from decimal import Decimal
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__, calcul, importation, installation, rapport, releve, revalidation, sauvegarde, updater
from .db import Base, MotDePasseIncorrect

VERT = "#1F6F5C"
VERT_FONCE = "#14503F"
VERT_PALE = "#E4F1EC"
VERT_TEXTE_PALE = "#D6EDE5"
ROUGE = "#A3420F"
FOND = "#F5F6F4"
BLANC = "#FFFFFF"
TEXTE = "#1C1F1E"
GRIS = "#4A524E"
BORD = "#E1E4E2"

POLICE = "Segoe UI"

# Petites icônes PNG (16-18 px) intégrées au code.
CALENDRIER = (
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAACR0lEQVR4nJ2SP2tUQRTFz5mZ93b37eaP9mIpiAEFU8awFgE1JkSMjYUgKhgQtLBRcEEQrPwCfoTFFIuIlQQLIRYiCIqV30CQ7J+3szNzLLKbBJPKAwdmbvG7514usCtOvLy8XCytLx1vtVoGANGCObK+a5gxQBOHjA9crP38vb2dARCfMx1VH3uXsnhrsTrlpxq2b4O3seVs9tAFnPDe94qicP1+P6QKn+3Va75nuzZ0Op0dBwD1PzMPXDV/MrQ+UKzHGBWob6hYdWNJVKwoVWOMitRXF6omOL8F4JrD7iAFDWchRZBGUiI5u78eAKQkJQDHaGgAzgCAG+8gSpJ1zhoSACwOiwCspMlvdBBglMQU41YatxynMJP3GGBIBpHzSsoPAlwIAe82O80jOh/SpWtXPwOoHwRYSb3La6sbtaJ6vRwMPv+ylWcnY9nO83xqWMa7YDrXaNQ3et3uR4oeRLZ/BwIleSDN1eq1poCLAOCsWynqRVPkjCFOFfV6E8AFEAEHD0lQJDlNZq+G3d55It783m6PUsDZwaA8P+3cj5Hsa++H84bpjqBivJe9EQigBMNCpFsR7JfT6+svFcvHSrZRlsNHxnEuhnAbMJ8oekFuLwHBKqBRijqT5/kqgAvf220v8EaeZ6sjaw2hk1mWr0paABEI1vYBxHvnslka3h8MBpC0cHnt6hdrTea9B5neknza7/UAcCmv5ItJ6c0kugGQrqytrNOaeynGJCADUADYISlBDQgBwMBamyGlD283Oy/+vbL/0l+kDBt2ia+H8AAAAABJRU5ErkJggg=="
)
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
        "novembre", "décembre"]
TROMBONE = (
    "iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAYAAABWzo5XAAACeUlEQVR4nI2Uz2sTQRTHv29msknaiArSf0APNhZBawVP8dDSJG3STWUrQsFDQQS9CPWc5qo9KkWPUi/dCqEmGEHPeigUPQRBD15aBA8epDHZnZ3nIT9I7Kb4ve2b4TPft2++A4QolUqp/6n1i4bUeNqZPmkhfo0CIdDSH6rV6q/uWhhI9H8Ui0UBgNMLuZWoGd2PR0fexEZiVcTUQcbO3wXAnT3DHTmOI13XNVk7l48nRsrNZusLa/PSwLBU6lY8HrvQaBzenJq4vF2v18l13aAf1Os7mUwyAIagR17LPwh8fV9a6qmEsHTLv9MU9BwsHpdKpa2OgYE2u44kgCBj5+aVFXnt+35ZSXGOiM4w0DCGPTbmq1JqRutg9erFSxtra2tMRD2QAIBUKkUAQEQrgdZNEO/G4vEJ3+jbFbd8Vkl5HgStA/1eCHpSqVRkB0IDoK6Y+RAAgdEwxjC1ncIYw2TQAADD5ncikTgyucEJEImOM4HBq0HcWQNIhgwNoaMMkQYQHLdhCIgYgCbR/pmWZSkCTrVhHAocABHAzMwAq4hlKQ44BgAtz1sn4AUYpwWJE2GggfwwoKSUMgjMD6/lbTFjHwBVt8sPAdDcDXvWGPN9bGwsNCY9Z+nC/FR+aZEz9vxmt55Op6MAkLFzm/mlxZ8zy8ujQC9O/d20VSwWRalUMulC7qNlRa54Wk/VXu3sAUDWtseVJfa0r7+ZP95krVbz8E94e9R6vU4ASCn5gEBSkdjNFPLPsoXchlD4TEJEDZt7tVqt5TjOkSENPCNdV7MLc9eVkutSRSYJgK/1p8DXq293qu+YmfqjcZx6p2Vtezzt5JPDDu7XX0akABzlZsjhAAAAAElFTkSuQmCC"
)

LIBELLES_TYPE = {"depart": "Solde de départ", "periode": "Période de paye", "vacances": "Vacances prises"}


def _date_courte(e):
    if e.type == "periode" and e.fin:
        if e.fin.year == e.debut.year:
            return f"{e.debut.isoformat()} → {e.fin.strftime('%m-%d')}"
        return f"{e.debut.isoformat()} → {e.fin.isoformat()}"
    return e.debut.isoformat()


def _abreger(nom, longueur=28):
    return nom if len(nom) <= longueur else nom[:longueur - 1] + "…"


def arrondir_coins(fenetre):
    """Coins arrondis et ombre (Windows 11) pour une fenêtre sans bordure ; sans effet ailleurs."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        fenetre.update_idletasks()
        hwnd = int(fenetre.wm_frame(), 16)
        preference = ctypes.c_int(2)  # DWMWCP_ROUND
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(preference), ctypes.sizeof(preference))
    except Exception:  # Windows 10 : coins carrés
        pass


class MenuContextuel(tk.Toplevel):
    """Menu du clic droit aux coins arrondis.

    `elements` : liste de (libellé, commande) ou (libellé, commande, "danger") ; None = séparateur.
    """

    def __init__(self, parent, elements, x, y):
        super().__init__(parent)
        self.parent = parent
        self.overrideredirect(True)
        self.configure(bg=BLANC if sys.platform == "win32" else BORD)
        cadre = tk.Frame(self, bg=BLANC, padx=5, pady=5)
        cadre.pack(padx=0 if sys.platform == "win32" else 1, pady=0 if sys.platform == "win32" else 1)
        for element in elements:
            if element is None:
                tk.Frame(cadre, bg=BORD, height=1).pack(fill="x", padx=8, pady=4)
                continue
            libelle, commande, *option = element
            couleur = ROUGE if option and option[0] == "danger" else TEXTE
            ligne = tk.Label(cadre, text=libelle, bg=BLANC, fg=couleur, anchor="w", padx=14, pady=6,
                             font=(POLICE, 10), cursor="hand2")
            ligne.pack(fill="x")
            ligne.bind("<Enter>", lambda _e, l=ligne: l.configure(bg=VERT_PALE))
            ligne.bind("<Leave>", lambda _e, l=ligne: l.configure(bg=BLANC))
            ligne.bind("<ButtonRelease-1>", lambda _e, c=commande: self._choisir(c))
        self.update_idletasks()
        largeur, hauteur = self.winfo_reqwidth(), self.winfo_reqheight()
        x = min(x, self.winfo_screenwidth() - largeur - 4)
        y = min(y, self.winfo_screenheight() - hauteur - 40)
        self.geometry(f"+{x}+{y}")
        arrondir_coins(self)
        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<FocusOut>", lambda _e: self.destroy())
        self.focus_force()

    def _choisir(self, commande):
        self.destroy()
        self.parent.after_idle(commande)


class ChoixReleve(ttk.Frame):
    """Choix d'un relevé de paye (PDF) : joindre, remplacer ou retirer."""

    def __init__(self, parent, nom_existant=None, on_change=None):
        super().__init__(parent, style="Carte.TFrame")
        self.on_change = on_change
        self.nom_existant = nom_existant
        self.chemin = None
        self.retirer = False
        self.btn = ttk.Button(self, command=self._choisir)
        self.btn.pack(side="left")
        self.lbl = ttk.Label(self, text="", style="Aide.TLabel")
        self.lbl.pack(side="left", padx=(8, 0))
        self.btn_x = ttk.Button(self, text="✕", width=3, command=self._effacer)
        self._maj()

    def _choisir(self):
        chemin = filedialog.askopenfilename(parent=self.winfo_toplevel(), title="Choisir le relevé de paye",
                                            filetypes=[("Relevé PDF", "*.pdf"), ("Tous les fichiers", "*.*")])
        if chemin:
            self.chemin = chemin
            self.retirer = False
            self._maj()

    def _effacer(self):
        if self.chemin:
            self.chemin = None
        else:
            self.retirer = True
        self._maj()

    def _maj(self):
        nom = Path(self.chemin).name if self.chemin else (None if self.retirer else self.nom_existant)
        self.lbl.configure(text="relevé joint" if nom else "aucun relevé")
        self.btn.configure(text="Remplacer…" if nom else "Joindre le relevé PDF…")
        if nom:
            self.btn_x.pack(side="left", padx=(6, 0))
        else:
            self.btn_x.pack_forget()
        if self.on_change:
            self.on_change()

    def reinitialiser(self):
        self.nom_existant = None
        self.chemin = None
        self.retirer = False
        self._maj()

    def lire(self):
        """Valide le PDF choisi avant tout enregistrement ; None si aucun."""
        return Base.lire_pdf(self.chemin) if self.chemin else None

    def appliquer(self, base, id_, pdf):
        if pdf:
            base.joindre_releve(id_, *pdf)
        elif self.retirer:
            base.retirer_releve(id_)


class ChampDate(ttk.Frame):
    """Champ de date : on tape AAAA-MM-JJ, ou on clique pour choisir dans un calendrier."""

    def __init__(self, parent, variable, largeur=12, police=(POLICE, 11), on_change=None):
        super().__init__(parent, style="Carte.TFrame")
        self.var = variable
        self.on_change = on_change
        self.popup = None
        self._liaisons = []
        self.entree = ttk.Entry(self, textvariable=variable, width=largeur, font=police)
        self.entree.pack(side="left", fill="both", expand=True)
        self.img = tk.PhotoImage(data=CALENDRIER)
        self.btn = ttk.Button(self, image=self.img, style="Icone.TButton", takefocus=False, command=self.basculer)
        self.btn.pack(side="left", fill="y", padx=(4, 0))
        self.entree.bind("<Button-1>", lambda _e: self.after(1, self.ouvrir), add="+")
        self.entree.bind("<Escape>", self._echap, add="+")
        self.entree.bind("<Tab>", lambda _e: self.fermer(), add="+")
        self.bind("<Destroy>", lambda _e: self.fermer(), add="+")

    def basculer(self):
        if self.popup:
            self.fermer()
        else:
            self.entree.focus_set()
            self.ouvrir()

    def ouvrir(self):
        if self.popup:
            return
        try:
            choisie = calcul.parse_date(self.var.get())
        except ValueError:
            choisie = dt.date.today()
        self.mois = choisie.replace(day=1)
        self.popup = tk.Toplevel(self)
        self.popup.overrideredirect(True)
        self.popup.configure(bg=BORD)
        self.cadre = tk.Frame(self.popup, bg=BLANC, padx=8, pady=8)
        self.cadre.pack(padx=1, pady=1)
        self._dessiner()
        self.popup.geometry(f"+{self.winfo_rootx()}+{self.winfo_rooty() + self.winfo_height() + 2}")
        arrondir_coins(self.popup)
        self.popup.lift()
        fenetre = self.winfo_toplevel()
        self._liaisons = [(fenetre, "<Button-1>", fenetre.bind("<Button-1>", self._clic_ailleurs, add="+")),
                          (fenetre, "<Configure>", fenetre.bind("<Configure>", self._deplacement, add="+"))]

    def fermer(self):
        for widget, sequence, ident in self._liaisons:
            try:
                widget.unbind(sequence, ident)
            except tk.TclError:
                pass
        self._liaisons = []
        if self.popup:
            self.popup.destroy()
            self.popup = None

    def _echap(self, _e):
        if self.popup:
            self.fermer()
            return "break"  # ne ferme pas la fenêtre de dialogue
        return None

    def _clic_ailleurs(self, ev):
        if str(ev.widget).startswith(str(self)):
            return
        self.fermer()

    def _deplacement(self, ev):
        if ev.widget is self.winfo_toplevel():
            self.fermer()

    def _changer_mois(self, delta):
        mois = self.mois.month - 1 + delta
        self.mois = dt.date(self.mois.year + mois // 12, mois % 12 + 1, 1)
        self._dessiner()

    def _dessiner(self):
        for w in self.cadre.winfo_children():
            w.destroy()
        try:
            choisie = calcul.parse_date(self.var.get())
        except ValueError:
            choisie = None
        aujourdhui = dt.date.today()
        bouton = dict(relief="flat", bd=0, cursor="hand2", takefocus=0, font=(POLICE, 10))
        tk.Button(self.cadre, text="‹", bg=BLANC, activebackground=VERT_PALE, width=3,
                  command=lambda: self._changer_mois(-1), **bouton).grid(row=0, column=0)
        tk.Label(self.cadre, text=f"{MOIS[self.mois.month - 1]} {self.mois.year}", bg=BLANC, fg=TEXTE,
                 font=(POLICE, 10, "bold")).grid(row=0, column=1, columnspan=5)
        tk.Button(self.cadre, text="›", bg=BLANC, activebackground=VERT_PALE, width=3,
                  command=lambda: self._changer_mois(1), **bouton).grid(row=0, column=6)
        for col, jour in enumerate(("L", "M", "M", "J", "V", "S", "D")):
            tk.Label(self.cadre, text=jour, bg=BLANC, fg=GRIS, font=(POLICE, 9)).grid(row=1, column=col, pady=(4, 2))
        semaines = calendar.Calendar(firstweekday=0).monthdatescalendar(self.mois.year, self.mois.month)
        for ligne, semaine in enumerate(semaines, 2):
            for col, jour in enumerate(semaine):
                if jour == choisie:
                    fond, texte = VERT, BLANC
                elif jour == aujourdhui:
                    fond, texte = VERT_PALE, VERT_FONCE
                else:
                    fond, texte = BLANC, TEXTE if jour.month == self.mois.month else "#9AA19D"
                tk.Button(self.cadre, text=str(jour.day), bg=fond, fg=texte, activebackground=VERT_PALE, width=3,
                          command=lambda j=jour: self.choisir(j), **bouton).grid(row=ligne, column=col, padx=1, pady=1)
        tk.Button(self.cadre, text="Aujourd'hui", bg=BLANC, fg=VERT, activebackground=VERT_PALE,
                  command=lambda: self.choisir(aujourdhui), **bouton).grid(row=9, column=0, columnspan=7, pady=(6, 0))

    def choisir(self, jour):
        self.var.set(jour.isoformat())
        self.fermer()
        self.entree.focus_set()
        if self.on_change:
            self.on_change(jour)


class Dialogue(tk.Toplevel):
    """Fenêtre modale de base avec boutons Annuler / OK."""

    titre = ""
    libelle_ok = "Enregistrer"
    style_ok = "Primaire.TButton"

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.resultat = None
        self.title(self.titre)
        self.configure(bg=BLANC)
        self.resizable(False, False)
        self.transient(parent)

        self.corps = ttk.Frame(self, style="Carte.TFrame", padding=20)
        self.corps.pack(fill="both", expand=True)
        self.construire(self.corps)

        pied = ttk.Frame(self, style="Pied.TFrame", padding=(20, 12))
        pied.pack(fill="x")
        ttk.Button(pied, text=self.libelle_ok, style=self.style_ok, command=self._ok).pack(side="right")
        ttk.Button(pied, text="Annuler", command=self.destroy).pack(side="right", padx=(0, 8))

        self.bind("<Return>", lambda _e: self._ok())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.grab_set()
        self.focus_set()

    def construire(self, cadre):
        raise NotImplementedError

    def valider(self):
        """Retourne True si l'enregistrement a réussi."""
        raise NotImplementedError

    def _ok(self):
        try:
            if self.valider():
                self.destroy()
        except ValueError as err:
            messagebox.showerror("Valeur invalide", str(err), parent=self)

    def champ(self, cadre, ligne, libelle, valeur="", largeur=14, aide=None, masque=False, date=False):
        ttk.Label(cadre, text=libelle, style="Champ.TLabel").grid(row=ligne, column=0, sticky="w", pady=(0, 4))
        var = tk.StringVar(value=valeur)
        if date:
            widget = ChampDate(cadre, var, largeur=largeur)
            entree = widget.entree
        else:
            widget = entree = ttk.Entry(cadre, textvariable=var, width=largeur, font=(POLICE, 11),
                                        show="•" if masque else "")
        widget.grid(row=ligne + 1, column=0, sticky="w", pady=(0, 2 if aide else 14))
        if aide:
            ttk.Label(cadre, text=aide, style="Aide.TLabel").grid(row=ligne + 2, column=0, sticky="w", pady=(0, 14))
        return var, entree


class DialogueSoldeDepart(Dialogue):
    """Solde de vacances déjà inscrit sur le talon de paye au moment de commencer le suivi."""

    titre = "Solde de départ"

    def construire(self, c):
        base = self.parent.base
        depart = base.solde_depart()
        ttk.Label(c, text="Solde de départ ($)", style="Champ.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 4))
        ligne = ttk.Frame(c, style="Carte.TFrame")
        ligne.grid(row=1, column=0, sticky="w")
        self.var_depart = tk.StringVar(value=calcul.formater_nombre(depart.montant) if depart else "0,00")
        self.var_date = tk.StringVar(
            value=(depart.debut if depart else dt.date(dt.date.today().year, 1, 1)).isoformat())
        entree = ttk.Entry(ligne, textvariable=self.var_depart, width=12, font=(POLICE, 11),
                           show="•" if self.parent.confidentiel else "")
        entree.pack(side="left")
        ttk.Label(ligne, text=" $  au ", style="Carte.TLabel").pack(side="left")
        ChampDate(ligne, self.var_date).pack(side="left")
        ttk.Label(c, text="Pour reprendre un solde déjà inscrit sur ton talon de paye (0 = aucun).",
                  style="Aide.TLabel").grid(row=2, column=0, sticky="w", pady=(4, 0))
        entree.focus_set()
        entree.select_range(0, "end")

    def valider(self):
        montant = calcul.parse_nombre(self.var_depart.get() or "0")
        if montant < 0:
            raise ValueError("Le solde de départ ne peut pas être négatif.")
        self.parent.base.definir_solde_depart(montant, calcul.parse_date(self.var_date.get()))
        self.parent.rafraichir()
        return True


class DialogueEmbauche(Dialogue):
    titre = "Date d'embauche"

    def construire(self, c):
        embauche = self.parent.base.embauche
        self.var_date = tk.StringVar(value=embauche.isoformat() if embauche else "")
        ttk.Label(c, text="Date d'embauche", style="Champ.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 4))
        champ = ChampDate(c, self.var_date)
        champ.grid(row=1, column=0, sticky="w")
        ttk.Label(c, text="Sert au rappel du passage à 6 % (3 ans de service continu au 30 avril).",
                  style="Aide.TLabel").grid(row=2, column=0, sticky="w", pady=(6, 0))
        champ.entree.focus_set()

    def valider(self):
        texte = self.var_date.get().strip()
        self.parent.base.embauche = calcul.parse_date(texte) if texte else None
        return True


class DialogueRevalidation(tk.Toplevel):
    """Résultat de la relecture des relevés enregistrés, avec correction en un clic."""

    def __init__(self, parent, rapport):
        super().__init__(parent)
        self.parent = parent
        self.rapport = rapport
        self.title("Revalider les relevés")
        self.configure(bg=BLANC)
        self.transient(parent)
        c = ttk.Frame(self, style="Carte.TFrame", padding=20)
        c.pack(fill="both", expand=True)
        n, ecarts = rapport.verifies, rapport.ecarts
        resume = f"{n} relevé{'s' if n > 1 else ''} relu{'s' if n > 1 else ''}"
        if ecarts:
            periodes = len({e.entree.id for e in ecarts})
            resume += f" · {periodes} période{'s' if periodes > 1 else ''} à corriger"
        else:
            resume += " · tout concorde avec ce qui est enregistré"
        if rapport.illisibles:
            resume += f" · {len(rapport.illisibles)} illisible{'s' if len(rapport.illisibles) > 1 else ''}"
        ttk.Label(c, text=resume, style="SousTitre.TLabel").pack(anchor="w", pady=(0, 12))

        if ecarts:
            cadre = ttk.Frame(c, style="Carte.TFrame")
            cadre.pack(fill="both", expand=True)
            arbre = ttk.Treeview(cadre, columns=("periode", "element", "avant", "apres"), show="headings",
                                 height=min(12, len(ecarts)))
            for col, txt, larg in (("periode", "Période", 190), ("element", "Élément", 90),
                                   ("avant", "Enregistré", 130), ("apres", "Selon le relevé", 130)):
                arbre.heading(col, text=txt, anchor="w")
                arbre.column(col, width=larg, anchor="w")
            cache = parent.confidentiel
            for e in ecarts:
                arbre.insert("", "end", values=(_date_courte(e.entree), e.element,
                                                calcul.masquer(self._texte(e.element, e.enregistre), cache),
                                                calcul.masquer(self._texte(e.element, e.selon_releve), cache)))
            arbre.pack(fill="both", expand=True)
        for e in rapport.illisibles:
            ttk.Label(c, text=f"Relevé illisible (PDF numérisé ?) : {_date_courte(e)}", style="Aide.TLabel").pack(
                anchor="w", pady=(6, 0))

        pied = ttk.Frame(self, style="Pied.TFrame", padding=(20, 12))
        pied.pack(fill="x")
        if ecarts:
            ttk.Button(pied, text="Corriger selon les relevés", style="Primaire.TButton",
                       command=self._corriger).pack(side="right")
        ttk.Button(pied, text="Fermer", command=self.destroy).pack(side="right", padx=(0, 8))
        self.bind("<Escape>", lambda _e: self.destroy())
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.grab_set()

    @staticmethod
    def _texte(element, valeur):
        if valeur is None:
            return "—"
        if element in ("Début", "Fin"):
            return valeur.isoformat()
        if element == "Heures":
            return f"{calcul.formater_nombre(valeur)} h"
        if element == "Taux":
            return f"{calcul.formater_argent(valeur)}/h"
        return calcul.formater_argent(valeur)

    def _corriger(self):
        nombre = revalidation.appliquer(self.parent.base, self.rapport.ecarts)
        self.parent.rafraichir()
        self.destroy()
        messagebox.showinfo("Revalider les relevés",
                            f"{nombre} période{'s' if nombre > 1 else ''} corrigée{'s' if nombre > 1 else ''} "
                            "selon les relevés.", parent=self.parent)


class DialoguePourcentage(Dialogue):
    titre = "Pourcentage de vacances"

    def construire(self, c):
        ttk.Label(c, text="Pourcentage de vacances (%)", style="Champ.TLabel").grid(row=0, column=0, sticky="w",
                                                                                    pady=(0, 4))
        ligne = ttk.Frame(c, style="Carte.TFrame")
        ligne.grid(row=1, column=0, sticky="w", pady=(0, 8))
        self.var_pct = tk.StringVar(value=calcul.formater_simple(self.parent.base.pct))
        entree = ttk.Entry(ligne, textvariable=self.var_pct, width=8, font=(POLICE, 11))
        entree.pack(side="left")
        for p in ("4", "6", "8"):
            ttk.Button(ligne, text=f"{p} %", width=5, command=lambda p=p: self.var_pct.set(p)).pack(side="left",
                                                                                                padx=(8, 0))
        ttk.Label(c, text="S'applique aux nouvelles périodes ajoutées.", style="Aide.TLabel").grid(
            row=2, column=0, sticky="w")
        entree.focus_set()
        entree.select_range(0, "end")

    def valider(self):
        self.parent.base.pct = calcul.parse_nombre(self.var_pct.get())
        self.parent.rafraichir()
        return True


class DialogueMotDePasse(Dialogue):
    def __init__(self, parent, base, retirer=False):
        self.base = base
        self.retirer = retirer
        self.existe = base.a_mot_de_passe
        if retirer:
            self.titre, self.libelle_ok, self.style_ok = "Retirer le mot de passe", "Retirer", "Danger.TButton"
        else:
            self.titre = "Changer le mot de passe" if self.existe else "Définir un mot de passe"
        super().__init__(parent)

    def construire(self, c):
        ligne, premier = 0, None
        if self.existe:
            self.var_actuel, premier = self.champ(c, 0, "Mot de passe actuel", largeur=28, masque=True)
            ligne = 2
        if not self.retirer:
            self.var_nouveau, entree = self.champ(c, ligne, "Nouveau mot de passe", largeur=28, masque=True)
            self.var_confirmation, _ = self.champ(c, ligne + 2, "Confirmer le mot de passe", largeur=28, masque=True)
            ttk.Label(c, text="Il sera demandé à chaque ouverture, et tes données (relevés compris)\n"
                              "seront chiffrées avec lui : sans ce mot de passe, elles sont illisibles.\n"
                              "Aucune récupération possible : note-le en lieu sûr.",
                      style="Aide.TLabel").grid(row=ligne + 4, column=0, sticky="w")
            premier = premier or entree
        premier.focus_set()

    def valider(self):
        if self.existe and not self.base.verifier_mot_de_passe(self.var_actuel.get()):
            raise ValueError("Le mot de passe actuel est incorrect.")
        if self.retirer:
            self.base.definir_mot_de_passe(None)
            return True
        if self.var_nouveau.get() != self.var_confirmation.get():
            raise ValueError("Les deux mots de passe ne sont pas identiques.")
        self.base.definir_mot_de_passe(self.var_nouveau.get())
        return True


class DialogueVacances(Dialogue):
    titre = "Déduire des vacances prises"
    libelle_ok = "Déduire"
    style_ok = "Danger.TButton"

    def __init__(self, parent, entree=None):
        self.entree = entree
        if entree:
            self.titre = "Modifier des vacances prises"
            self.libelle_ok = "Enregistrer"
        super().__init__(parent)

    def construire(self, c):
        base = self.parent.base
        e = self.entree
        self.taux = (e.taux if e and e.taux else None) or base.taux
        self.var_date, _ = self.champ(c, 0, "Date (ou première journée)",
                                      (e.debut if e else dt.date.today()).isoformat(), date=True)

        ttk.Label(c, text="Saisir en", style="Champ.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 4))
        self.var_mode = tk.StringVar(value="montant" if e and e.heures is None else "heures")
        modes = ttk.Frame(c, style="Carte.TFrame")
        modes.grid(row=3, column=0, sticky="w", pady=(0, 14))
        ttk.Radiobutton(modes, text="Heures", value="heures", variable=self.var_mode, style="Carte.TRadiobutton",
                        command=self._apercu).pack(side="left")
        ttk.Radiobutton(modes, text="Montant $", value="montant", variable=self.var_mode, style="Carte.TRadiobutton",
                        command=self._apercu).pack(side="left", padx=(16, 0))

        if e:
            valeur = calcul.formater_simple(e.heures) if e.heures is not None else calcul.formater_nombre(-e.montant)
        else:
            valeur = ""
        self.lbl_valeur = ttk.Label(c, text="", style="Champ.TLabel")
        self.lbl_valeur.grid(row=4, column=0, sticky="w", pady=(0, 4))
        ligne = ttk.Frame(c, style="Carte.TFrame")
        ligne.grid(row=5, column=0, sticky="w", pady=(0, 14))
        self.var_valeur = tk.StringVar(value=valeur)
        entree = ttk.Entry(ligne, textvariable=self.var_valeur, width=10, font=(POLICE, 11, "bold"))
        entree.pack(side="left")
        self.lbl_calc = ttk.Label(ligne, text="", style="Carte.TLabel")
        self.lbl_calc.pack(side="left", padx=(10, 0))

        self.var_note, _ = self.champ(c, 6, "Note (optionnel)", e.note if e else "", largeur=40)

        ttk.Label(c, text="Relevé de paye (optionnel)", style="Champ.TLabel").grid(row=8, column=0, sticky="w",
                                                                                   pady=(0, 4))
        self.releve = ChoixReleve(c, e.releve if e else None)
        self.releve.grid(row=9, column=0, sticky="w", pady=(0, 14))

        self.recap = ttk.Frame(c, style="Recap.TFrame", padding=(14, 10))
        self.recap.grid(row=10, column=0, sticky="we")
        self.recap.columnconfigure(1, weight=1)
        self.lbl_recap = []
        for i, txt in enumerate(("Solde actuel", "Vacances prises", "Nouveau solde")):
            ttk.Label(self.recap, text=txt, style="Recap.TLabel").grid(row=i, column=0, sticky="w", pady=2)
            lbl = ttk.Label(self.recap, text="", style="Recap.TLabel")
            lbl.grid(row=i, column=1, sticky="e", pady=2, padx=(40, 0))
            self.lbl_recap.append(lbl)
        self.lbl_alerte = ttk.Label(c, text="", style="Alerte.TLabel")
        self.lbl_alerte.grid(row=11, column=0, sticky="w", pady=(8, 0))

        self.var_valeur.trace_add("write", lambda *_: self._apercu())
        self._apercu()
        entree.focus_set()

    def _montant(self):
        valeur = calcul.parse_nombre(self.var_valeur.get())
        if self.var_mode.get() == "heures":
            return valeur, calcul.montant_heures(valeur, self.taux)
        return None, calcul.arrondir(valeur)

    def _apercu(self):
        heures_mode = self.var_mode.get() == "heures"
        self.lbl_valeur.configure(text="Nombre d'heures prises" if heures_mode else "Montant pris ($)")
        solde = self.parent.base.totaux().solde
        if self.entree:
            solde -= self.entree.montant  # on retire l'ancienne valeur pour l'aperçu
        try:
            heures, montant = self._montant()
        except ValueError:
            heures, montant = None, None
        if montant is None:
            self.lbl_calc.configure(text=calcul.masquer(f"h  ×  {calcul.formater_argent(self.taux)}", self.parent.confidentiel)
                                    if heures_mode else "$")
            nouveau = None
        else:
            if heures_mode:
                self.lbl_calc.configure(text=calcul.masquer(f"h  ×  {calcul.formater_argent(self.taux)}  =  "
                                                     f"{calcul.formater_argent(montant)}", self.parent.confidentiel))
            else:
                self.lbl_calc.configure(text="$")
            nouveau = solde - montant
        c = self.parent.confidentiel
        self.lbl_recap[0].configure(text=calcul.masquer(calcul.formater_argent(solde), c))
        self.lbl_recap[1].configure(text=calcul.masquer(calcul.formater_argent(-montant), c) if montant is not None else "—")
        if nouveau is None:
            self.lbl_recap[2].configure(text="—")
            self.lbl_alerte.configure(text="")
        else:
            txt = calcul.formater_argent(nouveau)
            if self.parent.base.taux > 0:
                txt += f"  (≈ {calcul.formater_nombre(nouveau / self.parent.base.taux)} h)"
            self.lbl_recap[2].configure(text=calcul.masquer(txt, c))
            self.lbl_alerte.configure(text="Attention : le solde deviendra négatif." if nouveau < 0 else "")

    def valider(self):
        date = calcul.parse_date(self.var_date.get())
        heures, montant = self._montant()
        pdf = self.releve.lire()
        base = self.parent.base
        if self.entree:
            id_ = self.entree.id
            base.modifier_vacances(id_, date, heures=heures, montant=None if heures else montant,
                                   note=self.var_note.get())
        else:
            id_ = base.ajouter_vacances(date, heures=heures, montant=None if heures else montant,
                                        note=self.var_note.get())
        self.releve.appliquer(base, id_, pdf)
        self.parent.rafraichir()
        return True


class DialoguePeriode(Dialogue):
    titre = "Modifier une période de paye"

    def __init__(self, parent, entree):
        self.entree = entree
        super().__init__(parent)

    def construire(self, c):
        e = self.entree
        self.var_debut, _ = self.champ(c, 0, "Début", e.debut.isoformat(), date=True)
        self.var_fin, _ = self.champ(c, 2, "Fin", e.fin.isoformat(), date=True)
        self.var_heures, entree = self.champ(c, 4, "Heures travaillées", calcul.formater_simple(e.heures),
                                             aide=f"Taux de cette période : {calcul.formater_argent(e.taux)} · "
                                                  f"{calcul.formater_simple(e.pct)} %")
        self.var_ferie, _ = self.champ(c, 7, "Paie de férié ($)",
                                       calcul.formater_nombre(e.ferie) if e.ferie else "")
        ttk.Label(c, text="Relevé de paye (PDF)", style="Champ.TLabel").grid(row=9, column=0, sticky="w", pady=(0, 4))
        self.releve = ChoixReleve(c, e.releve)
        self.releve.grid(row=10, column=0, sticky="w")
        entree.focus_set()
        entree.select_range(0, "end")

    def valider(self):
        debut = calcul.parse_date(self.var_debut.get())
        fin = calcul.parse_date(self.var_fin.get())
        heures = calcul.parse_nombre(self.var_heures.get())
        pdf = self.releve.lire()
        ferie = calcul.parse_nombre(self.var_ferie.get()) if self.var_ferie.get().strip() else None
        self.parent.base.modifier_periode(self.entree.id, debut, fin, heures, ferie=ferie)
        self.releve.appliquer(self.parent.base, self.entree.id, pdf)
        self.parent.rafraichir()
        return True


class Application(tk.Tk):
    def __init__(self, base, vient_d_installer=False):
        super().__init__()
        self.base = base
        self.release = None
        self._file_maj = queue.Queue()
        self.title("Calculateur de vacances")
        self.geometry(f"1060x{min(820, self.winfo_screenheight() - 80)}")
        self.minsize(900, 640)
        self.configure(bg=FOND)
        icone = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "icone.ico"
        if sys.platform == "win32" and icone.exists():
            self.iconbitmap(default=str(icone))
        self._styles()
        if base is None or base.a_mot_de_passe:  # base chiffrée : elle s'ouvre avec le mot de passe
            self._ecran_connexion(vient_d_installer)
        else:
            self._demarrer(vient_d_installer)

    def _demarrer(self, vient_d_installer=False):
        self._construire()
        self._appliquer_affichage(demarrage=True)
        self._titre()
        self.entree_heures.configure(show="•" if self.confidentiel else "")
        self.entree_ferie.configure(show="•" if self.confidentiel else "")
        self.rafraichir()
        self._preremplir_periode()
        self.after(150, self._sonder_maj)
        self.verifier_maj()
        self.protocol("WM_DELETE_WINDOW", self.quitter)
        if self.base.premier_lancement_fait:
            self.after(600, self._questions_demarrage)
        if vient_d_installer:
            self.after(300, self._bienvenue_installation)
        elif not self.base.premier_lancement_fait:
            self.after(300, self._premier_lancement)

    def _premier_lancement(self):
        """Au tout premier lancement : choisir le % de vacances (le taux, lui, vient du relevé)."""
        self.base.marquer_premier_lancement()
        self.ouvrir_pourcentage()

    def _ecran_connexion(self, vient_d_installer):
        ecran = ttk.Frame(self)
        ecran.pack(fill="both", expand=True)
        carte = tk.Frame(ecran, bg=BLANC, highlightbackground=BORD, highlightcolor=BORD, highlightthickness=1,
                         padx=36, pady=30)
        carte.place(relx=0.5, rely=0.42, anchor="center")
        tk.Label(carte, text="Mes vacances", bg=BLANC, fg=TEXTE, font=(POLICE, 18, "bold")).pack(anchor="w")
        ttk.Label(carte, text="Entre ton mot de passe pour ouvrir l'application.", style="Aide.TLabel").pack(
            anchor="w", pady=(4, 16))
        ttk.Label(carte, text="Mot de passe", style="Champ.TLabel").pack(anchor="w", pady=(0, 4))
        var = tk.StringVar()
        entree = ttk.Entry(carte, textvariable=var, show="•", width=30, font=(POLICE, 12))
        entree.pack(anchor="w")
        erreur = ttk.Label(carte, text="", style="Alerte.TLabel")
        erreur.pack(anchor="w", pady=(6, 10))

        def valider(_e=None):
            if bouton.instate(["disabled"]):
                return
            mot_de_passe = var.get()
            ok = True
            if self.base is None:
                try:
                    self.base = Base(mot_de_passe=mot_de_passe)
                except MotDePasseIncorrect:
                    ok = False
            elif not self.base.verifier_mot_de_passe(mot_de_passe):
                ok = False
            elif not self.base.chiffree:
                self.base.definir_mot_de_passe(mot_de_passe)  # protégée avant la 2.5 : chiffrée maintenant
            if ok:
                ecran.destroy()
                self._demarrer(vient_d_installer)
                return
            var.set("")
            erreur.configure(text="Mot de passe incorrect.")
            bouton.state(["disabled"])  # petite pause entre deux essais
            self.after(1000, lambda: bouton.state(["!disabled"]) if bouton.winfo_exists() else None)

        bouton = ttk.Button(carte, text="Ouvrir", style="Primaire.TButton", command=valider)
        bouton.pack(anchor="e")
        entree.bind("<Return>", valider)
        entree.focus_set()

    # --- Construction -------------------------------------------------------

    def _styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", font=(POLICE, 10), foreground=TEXTE, background=FOND)
        s.configure("TFrame", background=FOND)
        s.configure("Carte.TFrame", background=BLANC)
        s.configure("Pied.TFrame", background="#FAFBFA")
        s.configure("Recap.TFrame", background=FOND)
        s.configure("TLabel", background=FOND)
        s.configure("Carte.TLabel", background=BLANC)
        s.configure("Titre.TLabel", font=(POLICE, 18, "bold"))
        s.configure("SousTitre.TLabel", background=BLANC, font=(POLICE, 11, "bold"))
        s.configure("Info.TLabel", foreground=GRIS)
        s.configure("Champ.TLabel", background=BLANC, font=(POLICE, 10, "bold"))
        s.configure("Aide.TLabel", background=BLANC, foreground=GRIS, font=(POLICE, 9))
        s.configure("Note.TLabel", background=FOND, foreground="#3A423E", font=(POLICE, 9))
        s.configure("Recap.TLabel", background=FOND)
        s.configure("Alerte.TLabel", background=BLANC, foreground=ROUGE, font=(POLICE, 9, "bold"))
        s.configure("Calcul.TLabel", background=BLANC, foreground=GRIS)
        s.configure("Icone.TButton", padding=(6, 2), background=BLANC)
        for st in ("Carte.TCheckbutton", "Carte.TRadiobutton"):
            s.configure(st, background=BLANC)
            s.map(st, background=[("active", BLANC)])
        s.configure("TButton", padding=(12, 6), background=BLANC, bordercolor="#C8CDCA")
        s.map("TButton", background=[("active", "#EEF1EF")])
        s.configure("Primaire.TButton", background=VERT, foreground=BLANC, bordercolor=VERT,
                    font=(POLICE, 10, "bold"))
        s.map("Primaire.TButton", background=[("active", VERT_FONCE)])
        s.configure("Danger.TButton", background=BLANC, foreground=ROUGE, bordercolor=ROUGE,
                    font=(POLICE, 10, "bold"))
        s.map("Danger.TButton", background=[("active", "#FBEDE6")])
        s.configure("Danger.TButton", focuscolor=ROUGE)
        s.configure("Treeview", rowheight=28, background=BLANC, fieldbackground=BLANC, bordercolor=BORD)
        s.configure("Treeview.Heading", font=(POLICE, 10, "bold"), background="#F0F2F0", foreground="#3A423E",
                    relief="flat")
        s.map("Treeview", background=[("selected", VERT_PALE)], foreground=[("selected", TEXTE)])

    def _construire(self):
        self._menus()
        # Numéro de version en bas à gauche
        tk.Label(self, text=f"Version : {__version__}", bg=FOND, fg=GRIS, font=(POLICE, 9), anchor="w",
                 padx=24, pady=6).pack(side="bottom", fill="x")
        self.contenu = ttk.Frame(self, padding=(24, 18, 24, 4))
        self.contenu.pack(fill="both", expand=True)
        c = self.contenu

        self.img_trombone = tk.PhotoImage(data=TROMBONE)

        # Tuiles de totaux
        tuiles = self.cadre_soldes = ttk.Frame(c)
        tuiles.pack(fill="x", pady=(0, 14))
        for i in range(3):
            tuiles.columnconfigure(i, weight=1, uniform="tuile")
        self.t_accumule = self._tuile(tuiles, 0, "TOTAL ACCUMULÉ", BLANC, TEXTE, GRIS)
        self.t_pris = self._tuile(tuiles, 1, "VACANCES PRISES", BLANC, ROUGE, GRIS)
        self.t_solde = self._tuile(tuiles, 2, "SOLDE DISPONIBLE", VERT, BLANC, VERT_TEXTE_PALE)

        # Formulaire : nouvelle période (champs à gauche, résultat en évidence à droite)
        carte = self.carte_form = tk.Frame(c, bg=BLANC, highlightbackground=BORD, highlightcolor=BORD,
                                           highlightthickness=1)
        carte.pack(fill="x", pady=(0, 14))
        droite = tk.Frame(carte, bg=VERT_PALE, padx=22, pady=16)
        droite.pack(side="right", fill="y")
        tk.Frame(droite, bg=VERT_PALE, width=250, height=0).pack()
        tk.Label(droite, text="VACANCES GAGNÉES", bg=VERT_PALE, fg=VERT_FONCE, font=(POLICE, 9, "bold")).pack(
            anchor="w")
        self.lbl_resultat = tk.Label(droite, text="", bg=VERT_PALE, fg=VERT, font=(POLICE, 24, "bold"))
        self.lbl_resultat.pack(anchor="w")
        self.lbl_formule = tk.Label(droite, text="", bg=VERT_PALE, fg="#2E3632", font=(POLICE, 10))
        self.lbl_formule.pack(anchor="w")
        self.lbl_nouveau_solde = tk.Label(droite, text="", bg=VERT_PALE, fg="#2E3632", font=(POLICE, 10),
                                          justify="left")
        self.lbl_nouveau_solde.pack(anchor="w", pady=(2, 12))
        ttk.Button(droite, text="Ajouter la période", style="Primaire.TButton", command=self.ajouter_periode).pack(
            side="bottom", fill="x", ipady=4)

        gauche = tk.Frame(carte, bg=BLANC, padx=22, pady=16)
        gauche.pack(side="left", fill="both", expand=True)
        titre = ttk.Frame(gauche, style="Carte.TFrame")
        titre.pack(fill="x", pady=(0, 12))
        ttk.Label(titre, text="Nouvelle période de paye", style="SousTitre.TLabel").pack(side="left")

        champs = ttk.Frame(gauche, style="Carte.TFrame")
        champs.pack(fill="x")
        self.var_debut = tk.StringVar()
        self.var_fin = tk.StringVar()
        self.var_heures = tk.StringVar()
        self.var_ferie = tk.StringVar()
        for col, (txt, var) in enumerate((("Début", self.var_debut), ("Fin", self.var_fin),
                                          ("Heures travaillées", self.var_heures), ("Férié ($)", self.var_ferie))):
            champs.columnconfigure(col, weight=3 if col < 2 else 2)
            ttk.Label(champs, text=txt, style="Champ.TLabel").grid(row=0, column=col, sticky="w", padx=(0, 14),
                                                                   pady=(0, 4))
            if col < 2:
                champ = ChampDate(champs, var, largeur=10, police=(POLICE, 12),
                                  on_change=self._debut_choisi if col == 0 else lambda _j: self._verifier_releve())
                champ.grid(row=1, column=col, sticky="we", padx=(0, 14))
                e = champ.entree
            else:
                e = ttk.Entry(champs, textvariable=var, width=8, font=(POLICE, 12, "bold" if col == 2 else "normal"))
                e.grid(row=1, column=col, sticky="we", ipady=3, padx=(0, 14 if col == 2 else 0))
            e.bind("<Return>", lambda _e: self.ajouter_periode())
            if col == 2:
                self.entree_heures = e
            elif col == 3:
                self.entree_ferie = e

        zone = tk.Frame(gauche, bg=BLANC, highlightbackground="#C8CDCA", highlightcolor="#C8CDCA",
                        highlightthickness=1, padx=12, pady=8)
        zone.pack(fill="x", pady=(0, 16), before=champs)
        tk.Label(zone, image=self.img_trombone, bg=BLANC).pack(side="left")
        ttk.Label(zone, text="Relevé de paye", style="Aide.TLabel").pack(side="left", padx=(8, 0))
        self.releve_periode = ChoixReleve(zone, on_change=self._releve_choisi)
        self.releve_periode.pack(side="right")
        self.cadre_verif = ttk.Frame(gauche, style="Carte.TFrame")
        self.cadre_verif.pack(fill="x")
        self.lbl_verif = tk.Label(self.cadre_verif, text="", bg=BLANC, fg=GRIS, font=(POLICE, 10), anchor="w",
                                  justify="left", wraplength=430)
        self.btn_suggestion = ttk.Button(self.cadre_verif, command=self._utiliser_suggestion)

        self._analyse = None
        self._suggestion = None

        self.var_heures.trace_add("write", lambda *_: (self._apercu_periode(), self._verifier_releve()))
        self.var_ferie.trace_add("write", lambda *_: self._apercu_periode())
        self.var_debut.trace_add("write", lambda *_: self._verifier_releve())
        self.var_fin.trace_add("write", lambda *_: self._verifier_releve())

        # Historique
        hist = self.cadre_hist = tk.Frame(c, bg=BLANC, highlightbackground=BORD, highlightcolor=BORD,
                                          highlightthickness=1)
        hist.pack(fill="both", expand=True)
        tete = ttk.Frame(hist, style="Carte.TFrame", padding=(18, 10))
        tete.pack(fill="x")
        ttk.Label(tete, text="Historique", style="SousTitre.TLabel").pack(side="left")

        colonnes = ("date", "type", "heures", "montant", "solde", "releve")
        cadre_arbre = ttk.Frame(hist, style="Carte.TFrame")
        cadre_arbre.pack(fill="both", expand=True)
        self.arbre = ttk.Treeview(cadre_arbre, columns=colonnes, show="headings", selectmode="browse")
        for col, txt, larg, ancre in (("date", "Période / date", 200, "w"), ("type", "Type", 220, "w"),
                                      ("heures", "Heures", 90, "e"), ("montant", "Montant", 130, "e"),
                                      ("solde", "Solde cumulé", 140, "e"), ("releve", "Relevé", 80, "center")):
            self.arbre.heading(col, text=txt, anchor=ancre)
            self.arbre.column(col, width=larg, anchor=ancre, stretch=col in ("date", "type"))
        self.arbre.tag_configure("vacances", foreground=ROUGE)
        self.arbre.tag_configure("depart", foreground=GRIS)
        self.arbre.tag_configure("annee", background="#EEF1EF", font=(POLICE, 10, "bold"))
        defil = ttk.Scrollbar(cadre_arbre, orient="vertical", command=self.arbre.yview)
        self.arbre.configure(yscrollcommand=defil.set)
        self.arbre.pack(side="left", fill="both", expand=True)
        defil.pack(side="right", fill="y")
        self.arbre.bind("<Double-1>", self._double_clic)
        self.arbre.bind("<Return>", lambda _e: self.modifier_selection())
        self.arbre.bind("<Delete>", lambda _e: self.supprimer_selection())

        def menu_contextuel(ev):
            ligne = self.arbre.identify_row(ev.y)
            if not ligne:
                return
            self.arbre.selection_set(ligne)
            e = self._entree_selectionnee()
            if e is None:  # ligne d'année de référence
                return
            elements = [("Modifier…", self.modifier_selection)]
            if e and e.type != "depart":
                elements.append(None)
                if e.releve:
                    elements += [("Ouvrir le relevé", self.ouvrir_releve),
                                 ("Enregistrer le relevé sous…", self.enregistrer_releve),
                                 ("Remplacer le relevé…", self.joindre_releve),
                                 ("Retirer le relevé", self.retirer_releve)]
                else:
                    elements.append(("Joindre un relevé PDF…", self.joindre_releve))
            elements += [None, ("Supprimer", self.supprimer_selection, "danger")]
            MenuContextuel(self, elements, ev.x_root, ev.y_root)
        self.arbre.bind("<Button-3>", menu_contextuel)

    def _menus(self):
        """Barre maison : Fichier et Mise à jour à gauche, Confidentiel complètement à droite."""
        barre = tk.Frame(self, bg=BLANC)
        barre.pack(side="top", fill="x")
        tk.Frame(self, bg=BORD, height=1).pack(side="top", fill="x")
        style = dict(bg=BLANC, fg=TEXTE, activebackground=VERT_PALE, activeforeground=TEXTE, relief="flat", bd=0,
                     font=(POLICE, 10), padx=12, pady=5, cursor="hand2")

        bouton_fichier = tk.Menubutton(barre, text="Fichier", **style)
        bouton_fichier.pack(side="left")
        fichier = tk.Menu(bouton_fichier, tearoff=False)
        bouton_fichier.configure(menu=fichier)
        outils = tk.Menu(fichier, tearoff=False)
        affichage = tk.Menu(outils, tearoff=False)

        # Fichier ▸ Outils ▸ Affichage
        self.var_voir_soldes = tk.BooleanVar(value=self.base.preference("soldes"))
        self.var_voir_hist = tk.BooleanVar(value=self.base.preference("historique"))
        affichage.add_checkbutton(label="Soldes (total, vacances prises, solde)", variable=self.var_voir_soldes,
                                  command=self._appliquer_affichage)
        affichage.add_checkbutton(label="Historique", variable=self.var_voir_hist, command=self._appliquer_affichage)

        def remplir_outils():
            outils.delete(0, "end")
            outils.add_command(label=calcul.masquer(f"Pourcentage de vacances ({calcul.formater_simple(self.base.pct)} %)…",
                                                    self.confidentiel),
                               command=self.ouvrir_pourcentage)
            outils.add_command(label="Solde de départ…", command=self.ouvrir_solde_depart)
            outils.add_command(label="Revalider les relevés enregistrés…", command=self.revalider_releves)
            outils.add_command(label="Dossier de sauvegarde…", command=self.choisir_dossier_sauvegarde)
            outils.add_command(label="Sauvegarde complète de l'année (zip)…", command=self.archiver_annee)
            outils.add_command(label="Date d'embauche…", command=self.ouvrir_embauche)
            outils.add_cascade(label="Affichage", menu=affichage)
            outils.add_separator()
            if self.base.a_mot_de_passe:
                outils.add_command(label="Changer le mot de passe…", command=lambda: self.mot_de_passe(False))
                outils.add_command(label="Retirer le mot de passe…", command=lambda: self.mot_de_passe(True))
            else:
                outils.add_command(label="Définir un mot de passe…", command=lambda: self.mot_de_passe(False))
            outils.add_separator()
            outils.add_command(label="À propos", command=lambda: messagebox.showinfo(
                "À propos", f"Calculateur de vacances\nVersion {__version__}\n\nDonnées : {self.base.chemin}",
                parent=self))
        outils.configure(postcommand=remplir_outils)
        remplir_outils()

        fichier.add_command(label="Ajouter des relevés de paye…", command=self.ajouter_releves)
        fichier.add_command(label="J'ai pris des vacances…", accelerator="Ctrl+D", command=self.deduire_vacances)
        fichier.add_separator()
        fichier.add_cascade(label="Outils", menu=outils)
        fichier.add_separator()
        fichier.add_command(label="Exporter un rapport (Excel)…", command=self.exporter_rapport)
        fichier.add_separator()
        fichier.add_command(label="Exporter une sauvegarde…", command=self.exporter_sauvegarde)
        fichier.add_command(label="Restaurer une sauvegarde…", command=self._importer_depuis_menu)
        fichier.add_separator()
        fichier.add_command(label="Quitter", command=self.quitter)

        self.var_confidentiel = tk.BooleanVar(value=self.confidentiel)
        tk.Checkbutton(barre, text="Confidentiel", variable=self.var_confidentiel, command=self._appliquer_confidentiel,
                       bg=BLANC, fg=TEXTE, activebackground=VERT_PALE, selectcolor=BLANC, bd=0,
                       highlightthickness=0, font=(POLICE, 10), padx=12, pady=5, cursor="hand2").pack(side="right")
        self.bind_all("<Control-d>", lambda _e: self.deduire_vacances())
        self.bind_all("<Control-D>", lambda _e: self.deduire_vacances())

    @property
    def confidentiel(self):
        return self.base.preference("confidentiel", False)

    def _appliquer_confidentiel(self):
        self.base.definir_preference("confidentiel", self.var_confidentiel.get())
        self._titre()
        self.entree_heures.configure(show="•" if self.confidentiel else "")
        self.entree_ferie.configure(show="•" if self.confidentiel else "")
        self.rafraichir()
        self._verifier_releve()

    def _titre(self):
        self.title("Calculateur de vacances" + ("  —  Confidentiel" if self.confidentiel else ""))

    def _appliquer_affichage(self, demarrage=False):
        soldes, hist = self.var_voir_soldes.get(), self.var_voir_hist.get()
        self.base.definir_preference("soldes", soldes)
        self.base.definir_preference("historique", hist)
        self.cadre_soldes.pack_forget()
        self.cadre_hist.pack_forget()
        if soldes:
            self.cadre_soldes.pack(fill="x", pady=(0, 14), before=self.carte_form)
        if hist:
            self.cadre_hist.pack(fill="both", expand=True)
            self.minsize(900, 640)
            if not demarrage and self.winfo_height() < 640:
                self.geometry(f"{self.winfo_width()}x{min(820, self.winfo_screenheight() - 80)}")
        else:
            # Sans l'historique, la fenêtre se réduit à son contenu.
            self.minsize(900, 1)
            self.update_idletasks()
            largeur = 1060 if demarrage else self.winfo_width()
            self.geometry(f"{largeur}x{self.winfo_reqheight()}")

    def _tuile(self, parent, col, titre, fond, couleur_valeur, couleur_info):
        cadre = tk.Frame(parent, bg=fond, padx=18, pady=14,
                         highlightbackground=BORD if fond == BLANC else fond,
                         highlightcolor=BORD if fond == BLANC else fond, highlightthickness=1)
        cadre.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 0))
        tk.Label(cadre, text=titre, bg=fond, fg=couleur_info, font=(POLICE, 9)).pack(anchor="w")
        valeur = tk.Label(cadre, text="", bg=fond, fg=couleur_valeur, font=(POLICE, 20, "bold"))
        valeur.pack(anchor="w")
        info = tk.Label(cadre, text="", bg=fond, fg=couleur_info, font=(POLICE, 9), justify="left")
        info.pack(anchor="w")
        return valeur, info

    # --- Affichage ----------------------------------------------------------

    def rafraichir(self):
        base = self.base
        t = base.totaux()
        entrees = base.entrees()
        depart = next((e for e in entrees if e.type == "depart"), None)
        premiere = entrees[0].debut if entrees else None

        c = self.confidentiel
        self.t_accumule[0].configure(text=calcul.masquer(calcul.formater_argent(t.accumule), c))
        if premiere:
            info = f"depuis le {premiere.isoformat()}" + (" (incl. solde de départ)" if depart else "")
        else:
            info = "aucune période inscrite"
        info = f"{calcul.masquer(self._heures(t.accumule_heures), c)}\n{info}"
        self.t_accumule[1].configure(text=info)
        self.t_pris[0].configure(text=calcul.masquer(calcul.formater_argent(-t.pris) if t.pris else calcul.formater_argent(0), c))
        self.t_pris[1].configure(text=calcul.masquer(f"{calcul.formater_nombre(t.heures_prises)} h", c))
        self.t_solde[0].configure(text=calcul.masquer(calcul.formater_argent(t.solde), c))
        self.t_solde[1].configure(text=calcul.masquer(self._heures(t.solde_heures), c))

        self.arbre.delete(*self.arbre.get_children())
        for annee in reversed(rapport.par_annee(entrees)):
            parent = self.arbre.insert(
                "", "end", iid=f"annee-{annee.debut.year}", open=True, tags=("annee",),
                values=(f"Année {annee.libelle}",
                        calcul.masquer(f"Gagné {calcul.formater_argent(annee.gagne)}  ·  "
                                       f"Pris {calcul.formater_argent(annee.pris)}", c),
                        "", "", calcul.masquer(calcul.formater_argent(annee.solde_fin), c), ""))
            self._lignes_annee(parent, annee.entrees, c)
        self._apercu_periode()

    def _lignes_annee(self, parent, entrees, c):
        for e in reversed(entrees):
            heures = calcul.formater_nombre(e.heures) if e.heures is not None else "—"
            libelle = LIBELLES_TYPE[e.type] + (f" — {e.note}" if e.note else "")
            if e.ferie:
                libelle += calcul.masquer(f" + férié {calcul.formater_argent(e.ferie)}", c)
            montant = calcul.formater_argent(e.montant) if e.type == "depart" else calcul.formater_signe(e.montant)
            self.arbre.insert(parent, "end", iid=str(e.id), tags=(e.type,),
                              values=(_date_courte(e), libelle, calcul.masquer(heures, c), calcul.masquer(montant, c),
                                      calcul.masquer(calcul.formater_argent(e.solde), c), "PDF" if e.releve else ""))

    @staticmethod
    def _heures(valeur):
        """Équivalent en heures (montant ÷ taux horaire actuel)."""
        return f"{calcul.formater_nombre(valeur)} h" if valeur is not None else "— h (taux lu au premier relevé)"

    def _preremplir_periode(self):
        derniere = self.base.derniere_periode()
        if derniere:
            debut, fin = calcul.prochaine_periode(derniere.debut, derniere.fin)
        else:
            debut = dt.date.today()
            fin = debut + dt.timedelta(days=calcul.DUREE_PERIODE_JOURS - 1)
        self.var_debut.set(debut.isoformat())
        self.var_fin.set(fin.isoformat())
        self.var_heures.set("")
        self.var_ferie.set("")
        self.releve_periode.reinitialiser()
        self.releve_periode.btn.focus_set()

    def _ferie(self):
        """Paie de férié entrée (vide ou invalide = 0)."""
        try:
            return calcul.parse_nombre(self.var_ferie.get()) if self.var_ferie.get().strip() else Decimal(0)
        except ValueError:
            return Decimal(0)

    def _taux_releve(self, heures):
        analyse = getattr(self, "_analyse", None)
        return analyse.taux(heures) if analyse and heures is not None else None

    def _apercu_periode(self):
        try:
            heures = calcul.parse_nombre(self.var_heures.get())
        except ValueError:
            heures = None
        taux, pct = self._taux_releve(heures) or self.base.taux, self.base.pct
        ferie = self._ferie()
        c = self.confidentiel
        h = calcul.formater_simple(heures) if heures is not None else "…"
        formule = f"{h} h × {calcul.formater_argent(taux)}"
        if ferie:
            formule = f"({formule} + {calcul.formater_argent(ferie)} férié)"
        self.lbl_formule.configure(text=calcul.masquer(f"{formule} × {calcul.formater_simple(pct)} %", c))
        if heures is None:
            self.lbl_resultat.configure(text="—")
            self.lbl_nouveau_solde.configure(text="Entre les heures de la période")
            return
        montant = calcul.vacances_periode(heures, taux, pct, ferie)
        self.lbl_resultat.configure(text=calcul.masquer(calcul.formater_signe(montant), c))
        solde = self.base.totaux().solde + montant
        txt = f"Nouveau solde : {calcul.formater_argent(solde)}"
        if taux > 0:
            txt += f"\n≈ {calcul.formater_nombre(solde / taux)} h"
        self.lbl_nouveau_solde.configure(text=calcul.masquer(txt, c))

    # --- Actions ------------------------------------------------------------

    def _debut_choisi(self, jour):
        """Choisir le début au calendrier remplit la fin (même durée de période)."""
        self.var_fin.set((jour + dt.timedelta(days=calcul.DUREE_PERIODE_JOURS)).isoformat())
        self._verifier_releve()

    def _releve_choisi(self):
        if not hasattr(self, "lbl_verif"):
            return
        self._analyse = None
        if self.releve_periode.chemin:
            try:
                _nom, contenu = Base.lire_pdf(self.releve_periode.chemin)
                self._analyse = releve.analyser(contenu)
            except ValueError:
                self._analyse = releve.Analyse(lisible=False)
            # Les dates et les heures de la période viennent du relevé.
            if self._analyse.periode:
                debut, fin = self._analyse.periode
                self.var_debut.set(debut.isoformat())
                self.var_fin.set(fin.isoformat())
            if self._analyse.suggestion is not None:
                self.var_heures.set(calcul.formater_simple(self._analyse.suggestion))
            self.var_ferie.set(calcul.formater_nombre(self._analyse.ferie) if self._analyse.ferie else "")
            # Étape 2 : corriger les heures au besoin.
            self.entree_heures.focus_set()
            self.entree_heures.select_range(0, "end")
        self._verifier_releve()

    def _verifier_releve(self):
        if not hasattr(self, "lbl_verif"):
            return
        self.btn_suggestion.pack_forget()
        self._suggestion = None
        if self._analyse is None:
            self.lbl_verif.pack_forget()
            return
        try:
            heures = calcul.parse_nombre(self.var_heures.get())
        except ValueError:
            heures = None
        dates = []
        for var in (self.var_debut, self.var_fin):
            try:
                dates.append(calcul.parse_date(var.get()))
            except ValueError:
                dates.append(None)
        v = releve.verifier(self._analyse, heures, *dates)
        couleurs = {"ok": (VERT, "✓  "), "attention": (ROUGE, "⚠  "), "inconnu": (GRIS, "")}
        couleur, prefixe = couleurs[v.statut]
        # Tout concorde : rien à afficher ; seuls les écarts et les problèmes de lecture sont signalés.
        if v.statut == "ok":
            self.lbl_verif.pack_forget()
        else:
            self.lbl_verif.configure(text=prefixe + calcul.masquer(v.message, self.confidentiel), fg=couleur)
            self.lbl_verif.pack(side="left", fill="x", expand=True, pady=(8, 0))
        if v.suggestion is not None and v.suggestion != heures:
            self._suggestion = v.suggestion
            self.btn_suggestion.configure(
                text=calcul.masquer(f"Utiliser {calcul.formater_nombre(v.suggestion)} h", self.confidentiel))
            self.btn_suggestion.pack(side="right", pady=(8, 0), padx=(8, 0))


    def _utiliser_suggestion(self):
        if self._suggestion is not None:
            self.var_heures.set(calcul.formater_simple(self._suggestion))

    def ajouter_periode(self):
        try:
            debut = calcul.parse_date(self.var_debut.get())
            fin = calcul.parse_date(self.var_fin.get())
            heures = calcul.parse_nombre(self.var_heures.get())
            pdf = self.releve_periode.lire()
            taux = self._taux_releve(heures) if pdf else None
            if taux is None and self.base.taux <= 0:
                raise ValueError("Joins le relevé de paye : le taux horaire y est calculé.")
            if pdf and self._analyse is not None:
                v = releve.verifier(self._analyse, heures, debut, fin)
                if v.statut == "attention" and not messagebox.askyesno(
                        "Relevé de paye", f"{v.message}\n\nAjouter la période quand même ?", icon="warning",
                        parent=self):
                    return
            if self.base.periode_existe(debut) and not messagebox.askyesno(
                    "Période existante", f"Une période commençant le {debut.isoformat()} existe déjà.\n"
                                         "L'ajouter quand même ?", parent=self):
                return
            ferie = calcul.parse_nombre(self.var_ferie.get()) if self.var_ferie.get().strip() else None
            id_ = self.base.ajouter_periode(debut, fin, heures, taux=taux, ferie=ferie)
            self.releve_periode.appliquer(self.base, id_, pdf)
            if pdf and self._analyse is not None:
                importation.inscrire_vacances_versees(self.base, self._analyse, debut, fin)
            if taux:
                self.base.taux = taux  # le dernier relevé donne le taux courant
        except ValueError as err:
            messagebox.showerror("Valeur invalide", str(err), parent=self)
            return
        self.rafraichir()
        self._preremplir_periode()

    def mot_de_passe(self, retirer):
        DialogueMotDePasse(self, self.base, retirer)

    def exporter_sauvegarde(self, parent=None):
        parent = parent or self
        nom = f"vacances-sauvegarde-{dt.date.today().isoformat()}.db"
        chemin = filedialog.asksaveasfilename(parent=parent, title="Exporter une sauvegarde", initialfile=nom,
                                              defaultextension=".db", filetypes=[("Sauvegarde", "*.db")])
        if chemin:
            self.base.exporter(chemin)
            messagebox.showinfo("Sauvegarde", "Sauvegarde exportée.", parent=parent)

    def importer_sauvegarde(self, parent=None):
        """Remplace les données par une sauvegarde ; True si l'import a eu lieu."""
        parent = parent or self
        chemin = filedialog.askopenfilename(parent=parent, title="Restaurer une sauvegarde",
                                            initialdir=self.base.dossier_sauvegarde or None,
                                            filetypes=[("Sauvegarde", "*.db"), ("Tous les fichiers", "*.*")])
        if not chemin:
            return False
        if not messagebox.askyesno("Restaurer", "Remplacer toutes les données actuelles par cette sauvegarde ?",
                                   icon="warning", parent=parent):
            return False
        try:
            self.base.importer(chemin)
        except Exception as err:  # fichier corrompu, mauvais format…
            messagebox.showerror("Restaurer", f"Restauration impossible : {err}", parent=parent)
            return False
        self.rafraichir()
        self._preremplir_periode()
        return True

    def _importer_depuis_menu(self):
        if self.importer_sauvegarde():
            messagebox.showinfo("Restaurer", "Sauvegarde restaurée.", parent=self)

    def _questions_demarrage(self):
        """Questions posées une seule fois, puis rappel du 6 % quand il s'applique."""
        if not self.base.dossier_sauvegarde:  # jamais choisi, ou refusé avant la 2.7 : sauvegarde obligatoire
            self._demander_dossier_sauvegarde()
        if self.base.embauche is None:
            if messagebox.askyesno(
                    "Date d'embauche",
                    "Veux-tu entrer ta date d'embauche ?\n\nAu Québec, après 3 ans de service continu, "
                    "les vacances passent de 4 % à 6 % ; l'application pourra te le rappeler.", parent=self):
                self.wait_window(DialogueEmbauche(self))
            if self.base.embauche is None:
                self.base.embauche = None  # « plus tard » : ne plus demander
        self._rappel_6_pct()
        self._proposer_archive_annuelle()

    def _proposer_archive_annuelle(self):
        """Après le 30 avril : sauvegarde complète de l'année terminée, faite d'office, puis un avis."""
        dossier = self.base.dossier_sauvegarde
        annee = sauvegarde.derniere_annee_terminee(self.base)
        if not dossier or annee is None or self.base.rappel_fait(f"archive_{annee.year}"):
            return
        if self.archiver_annee(annee):
            self.base.marquer_rappel(f"archive_{annee.year}")  # en cas d'échec, on réessaie à la prochaine ouverture

    def archiver_annee(self, annee=None):
        dossier = self.base.dossier_sauvegarde
        if not dossier:
            messagebox.showinfo("Sauvegarde de l'année", "Choisis d'abord un dossier de sauvegarde "
                                                       "(Fichier ▸ Outils ▸ Dossier de sauvegarde).", parent=self)
            return False
        annee = annee or sauvegarde.derniere_annee_terminee(self.base) or calcul.annee_reference(dt.date.today())[0]
        self.configure(cursor="watch")
        self.update_idletasks()
        try:
            archive = sauvegarde.archiver_annee(self.base, dossier, annee)
        except OSError as err:
            messagebox.showerror("Sauvegarde de l'année", f"Sauvegarde impossible :\n{err}", parent=self)
            return False
        finally:
            self.configure(cursor="")
        messagebox.showinfo("Sauvegarde de l'année", f"La sauvegarde complète de l'année de référence "
                                                    f"{calcul.libelle_annee(annee)} a été faite :\n{archive}",
                            parent=self)
        return True

    def _rappel_6_pct(self):
        embauche = self.base.embauche
        if not embauche or self.base.pct != 4:  # un autre % a été choisi : on ne demande rien
            return
        debut, fin = calcul.annee_reference(dt.date.today())
        cle = f"6pct_{debut.year}"
        if calcul.pourcentage_selon_service(embauche, debut) < 6 or self.base.rappel_fait(cle):
            return
        self.base.marquer_rappel(cle)
        ans = calcul.annees_service(embauche, fin)
        if messagebox.askyesno(
                "Vacances à 6 %",
                f"Au {fin.day} avril {fin.year}, tu auras {ans} ans de service continu : pour l'année de "
                f"référence {calcul.libelle_annee(debut)} (1er mai {debut.year} au 30 avril {fin.year}), "
                "l'indemnité de vacances est de 6 % (3 semaines).\n\n"
                "Passer à 6 % maintenant, y compris pour les périodes déjà inscrites de cette année ?",
                parent=self):
            self.base.pct = Decimal(6)
            n = self.base.changer_pct_periodes(debut, fin, Decimal(6))
            self.rafraichir()
            messagebox.showinfo("Vacances à 6 %", f"Pourcentage réglé à 6 % ; {n} période{'s' if n > 1 else ''} "
                                                 "de l'année recalculée" + ("s." if n > 1 else "."), parent=self)

    def ouvrir_embauche(self):
        d = DialogueEmbauche(self)
        self.wait_window(d)
        self._rappel_6_pct()

    def exporter_rapport(self):
        nom = f"rapport-vacances-{dt.date.today().isoformat()}.csv"
        chemin = filedialog.asksaveasfilename(parent=self, title="Exporter un rapport", initialfile=nom,
                                              defaultextension=".csv", filetypes=[("Excel (CSV)", "*.csv")])
        if not chemin:
            return
        try:
            annees = rapport.exporter_csv(self.base, chemin)
        except OSError as err:
            messagebox.showerror("Rapport", f"Impossible d'écrire le rapport :\n{err}", parent=self)
            return
        messagebox.showinfo("Rapport", f"Rapport exporté ({len(annees)} année{'s' if len(annees) > 1 else ''} "
                                       f"de référence).\nIl s'ouvre dans Excel.", parent=self)

    # --- Sauvegarde automatique ---------------------------------------------------

    def _demander_dossier_sauvegarde(self):
        """Demandé une seule fois : où copier la base (la sauvegarde, elle, est obligatoire)."""
        messagebox.showinfo(
            "Sauvegarde automatique",
            "À chaque fermeture, l'application fait une copie de tes données (toutes gardées, puis "
            "regroupées dans un zip à la fin de chaque année de référence, le 30 avril).\n\n"
            "Choisis le dossier de sauvegarde : un dossier OneDrive ou iCloud Drive la met aussi à l'abri "
            "si l'ordinateur brise. Sans choix, un dossier par défaut est utilisé.",
            parent=self)
        self.choisir_dossier_sauvegarde(premiere_fois=True)

    def choisir_dossier_sauvegarde(self, premiere_fois=False):
        suggeres = sauvegarde.dossiers_suggeres()
        actuel = self.base.dossier_sauvegarde
        depart = actuel or (str(suggeres[0]) if suggeres else None)
        dossier = filedialog.askdirectory(parent=self, title="Dossier de sauvegarde", initialdir=depart,
                                          mustexist=False)
        if dossier:
            dossier = str(Path(dossier) / "Sauvegardes Calculateur de vacances") if premiere_fois else dossier
            self.base.dossier_sauvegarde = dossier
            try:
                sauvegarde.sauvegarder(self.base, dossier)
            except OSError as err:
                messagebox.showerror("Sauvegarde", f"Impossible d'écrire dans ce dossier :\n{err}", parent=self)
                return
            messagebox.showinfo("Sauvegarde", f"Sauvegardes automatiques dans :\n{dossier}", parent=self)
        elif premiere_fois:
            # Aucun choix : la sauvegarde se fait quand même, dans le dossier par défaut.
            dossier = str(sauvegarde.dossier_par_defaut())
            self.base.dossier_sauvegarde = dossier
            try:
                sauvegarde.sauvegarder(self.base, dossier)
            except OSError:
                pass
            messagebox.showinfo("Sauvegarde", f"Sauvegardes automatiques dans :\n{dossier}\n\n"
                                              "Tu peux changer de dossier dans Fichier ▸ Outils ▸ Dossier de "
                                              "sauvegarde.", parent=self)

    def _sauvegarde_auto(self):
        dossier = self.base.dossier_sauvegarde if hasattr(self, "arbre") else None
        if dossier:
            try:
                sauvegarde.sauvegarder(self.base, dossier)
            except Exception:  # dossier débranché, disque plein… : la fermeture n'est pas bloquée
                pass

    def quitter(self):
        self._sauvegarde_auto()
        self.destroy()

    # --- Ajout de plusieurs relevés ------------------------------------------------

    def ajouter_releves(self):
        chemins = filedialog.askopenfilenames(parent=self, title="Ajouter des relevés de paye",
                                              filetypes=[("Relevés PDF", "*.pdf"), ("Tous les fichiers", "*.*")])
        if not chemins:
            return
        self.configure(cursor="watch")
        self.update_idletasks()
        try:
            r = importation.ajouter_releves(self.base, chemins)
        finally:
            self.configure(cursor="")
        self.rafraichir()
        self._preremplir_periode()
        lignes = [f"{len(r.ajoutees)} période{'s' if len(r.ajoutees) > 1 else ''} ajoutée"
                  f"{'s' if len(r.ajoutees) > 1 else ''}"]
        if r.ajoutees:
            lignes[0] += f" (du {r.ajoutees[0][0].isoformat()} au {r.ajoutees[-1][1].isoformat()})"
        if r.vacances:
            lignes.append(f"{r.vacances} entrée{'s' if r.vacances > 1 else ''} de vacances versées")
        if r.deja_la:
            lignes.append(f"{len(r.deja_la)} déjà présente{'s' if len(r.deja_la) > 1 else ''} (non ajoutée"
                          f"{'s' if len(r.deja_la) > 1 else ''})")
        if r.illisibles:
            lignes.append("Illisible(s) : " + ", ".join(r.illisibles))
        messagebox.showinfo("Ajouter des relevés de paye", "\n".join(lignes), parent=self)

    def deduire_vacances(self):
        DialogueVacances(self)

    def _bienvenue_installation(self):
        messagebox.showinfo(
            "Installation terminée",
            "Le Calculateur de vacances est installé sur cet ordinateur.\n\n"
            "Un raccourci a été créé sur le Bureau et dans le menu Démarrer.\n"
            "Tu peux supprimer le fichier que tu as téléchargé.",
            parent=self)
        if not self.base.premier_lancement_fait:
            self._premier_lancement()

    def ouvrir_pourcentage(self):
        DialoguePourcentage(self)

    def ouvrir_solde_depart(self):
        DialogueSoldeDepart(self)

    def revalider_releves(self):
        self.configure(cursor="watch")
        self.update_idletasks()
        try:
            rapport = revalidation.revalider(self.base)
        finally:
            self.configure(cursor="")
        if not rapport.verifies and not rapport.illisibles:
            messagebox.showinfo("Revalider les relevés", "Aucun relevé de paye n'est joint aux périodes.",
                                parent=self)
            return
        DialogueRevalidation(self, rapport)

    def _entree_selectionnee(self):
        sel = self.arbre.selection()
        if not sel:
            return None
        try:
            return self.base.entree(int(sel[0]))
        except (KeyError, ValueError):  # ligne d'année de référence
            return None

    def modifier_selection(self):
        e = self._entree_selectionnee()
        if e is None:
            return
        if e.type == "periode":
            DialoguePeriode(self, e)
        elif e.type == "vacances":
            DialogueVacances(self, e)
        else:
            self.ouvrir_solde_depart()

    def _double_clic(self, ev):
        e = self._entree_selectionnee()
        if e and e.releve and self.arbre.identify_column(ev.x) == "#6":
            self.ouvrir_releve()
        else:
            self.modifier_selection()

    def ouvrir_releve(self):
        e = self._entree_selectionnee()
        releve = self.base.lire_releve(e.id) if e else None
        if not releve:
            return
        nom, contenu = releve
        dossier = Path(tempfile.gettempdir()) / "CalculateurVacances"
        dossier.mkdir(exist_ok=True)
        nom_sur = re.sub(r'[<>:"/\\|?*]', "_", nom)
        chemin = dossier / f"{e.id}-{nom_sur}"
        try:
            chemin.write_bytes(contenu)
            if sys.platform == "win32":
                os.startfile(chemin)
            else:
                webbrowser.open(chemin.as_uri())
        except OSError as err:
            messagebox.showerror("Relevé", f"Impossible d'ouvrir le relevé : {err}", parent=self)

    def enregistrer_releve(self):
        e = self._entree_selectionnee()
        releve = self.base.lire_releve(e.id) if e else None
        if not releve:
            return
        chemin = filedialog.asksaveasfilename(parent=self, title="Enregistrer le relevé", initialfile=releve[0],
                                              defaultextension=".pdf", filetypes=[("Relevé PDF", "*.pdf")])
        if chemin:
            Path(chemin).write_bytes(releve[1])

    def joindre_releve(self):
        e = self._entree_selectionnee()
        if e is None:
            return
        chemin = filedialog.askopenfilename(parent=self, title="Choisir le relevé de paye",
                                            filetypes=[("Relevé PDF", "*.pdf"), ("Tous les fichiers", "*.*")])
        if not chemin:
            return
        try:
            self.base.joindre_releve(e.id, *Base.lire_pdf(chemin))
        except ValueError as err:
            messagebox.showerror("Relevé", str(err), parent=self)
            return
        self.rafraichir()
        self.arbre.selection_set(str(e.id))

    def retirer_releve(self):
        e = self._entree_selectionnee()
        if e and messagebox.askyesno("Relevé", f"Retirer le relevé « {e.releve} » ?", parent=self):
            self.base.retirer_releve(e.id)
            self.rafraichir()

    def supprimer_selection(self):
        e = self._entree_selectionnee()
        if e is None:
            return
        desc = f"{LIBELLES_TYPE[e.type].lower()} du {_date_courte(e)} ({calcul.formater_signe(e.montant)})"
        if messagebox.askyesno("Supprimer", f"Supprimer {desc} ?", icon="warning", parent=self):
            self.base.supprimer(e.id)
            self.rafraichir()
            self._preremplir_periode()

    # --- Mises à jour (entièrement automatiques) --------------------------------

    def verifier_maj(self):
        """Au démarrage : s'il existe une version plus récente, elle s'installe d'elle-même, sans question."""
        def travail():
            try:
                release = updater.verifier(__version__)
                if release and updater.peut_installer(release):
                    self._file_maj.put(("trouvee", release))
                    self._file_maj.put(("telecharge", updater.telecharger(release)))
            except Exception:  # hors ligne, GitHub indisponible… : on réessaiera au prochain démarrage
                pass
        threading.Thread(target=travail, daemon=True).start()

    def _sonder_maj(self):
        try:
            while True:
                genre, valeur = self._file_maj.get_nowait()
                if genre == "trouvee":
                    self.title(f"Calculateur de vacances  —  installation de la version "
                               f"{valeur.version}…")
                elif genre == "telecharge":
                    self._sauvegarde_auto()
                    updater.lancer_remplacement(valeur)
                    self.destroy()
                    return
        except queue.Empty:
            pass
        self.after(150, self._sonder_maj)

def _installer():
    """Installe le .exe téléchargé et lance la copie installée ; False si l'installation échoue."""
    try:
        cible = installation.installer(__version__, installation.lire_version_installee())
    except Exception as err:  # pas de PowerShell, disque plein, antivirus…
        racine = tk.Tk()
        racine.withdraw()
        messagebox.showwarning(
            "Installation", f"Installation impossible :\n{err}\n\n"
                            "L'application va s'ouvrir quand même, sans raccourci.", parent=racine)
        racine.destroy()
        return False
    installation.lancer(cible, "--installe")
    return True


def main():
    # Une base chiffrée ne s'ouvre qu'avec le mot de passe, demandé par l'application.
    base = None if Base.est_chiffree_sur_disque() else Base()
    application = None
    try:
        if installation.doit_installer():
            if _installer():
                return
        elif installation.est_exe_windows():
            installation.noter_version_installee(__version__)
        application = Application(base, vient_d_installer="--installe" in sys.argv)
        application.mainloop()
    finally:
        base = application.base if application else base
        if base:
            base.fermer()

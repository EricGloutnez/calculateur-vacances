"""Interface (Tkinter) du calculateur de vacances."""

import datetime as dt
import queue
import threading
import tkinter as tk
import webbrowser
from decimal import Decimal
from tkinter import filedialog, messagebox, ttk

from . import __version__, calcul, updater
from .db import Base

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

LIBELLES_TYPE = {"depart": "Solde de départ", "periode": "Période de paye", "vacances": "Vacances prises"}


def _date_courte(e):
    if e.type == "periode" and e.fin:
        if e.fin.year == e.debut.year:
            return f"{e.debut.isoformat()} → {e.fin.strftime('%m-%d')}"
        return f"{e.debut.isoformat()} → {e.fin.isoformat()}"
    return e.debut.isoformat()


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

    def champ(self, cadre, ligne, libelle, valeur="", largeur=14, aide=None):
        ttk.Label(cadre, text=libelle, style="Champ.TLabel").grid(row=ligne, column=0, sticky="w", pady=(0, 4))
        var = tk.StringVar(value=valeur)
        entree = ttk.Entry(cadre, textvariable=var, width=largeur, font=(POLICE, 11))
        entree.grid(row=ligne + 1, column=0, sticky="w", pady=(0, 2 if aide else 14))
        if aide:
            ttk.Label(cadre, text=aide, style="Aide.TLabel").grid(row=ligne + 2, column=0, sticky="w", pady=(0, 14))
        return var, entree


class DialogueParametres(Dialogue):
    titre = "Paramètres"

    def construire(self, c):
        base = self.parent.base
        self.var_taux, e_taux = self.champ(c, 0, "Taux horaire ($ / heure)", calcul.formater_nombre(base.taux))

        ttk.Label(c, text="Pourcentage de vacances (%)", style="Champ.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 4))
        ligne_pct = ttk.Frame(c, style="Carte.TFrame")
        ligne_pct.grid(row=3, column=0, sticky="w", pady=(0, 14))
        self.var_pct = tk.StringVar(value=calcul.formater_simple(base.pct))
        ttk.Entry(ligne_pct, textvariable=self.var_pct, width=8, font=(POLICE, 11)).pack(side="left")
        for p in ("4", "6", "8"):
            ttk.Button(ligne_pct, text=f"{p} %", width=5, command=lambda p=p: self.var_pct.set(p)).pack(side="left", padx=(8, 0))

        depart = base.solde_depart()
        ttk.Label(c, text="Solde de départ (optionnel)", style="Champ.TLabel").grid(row=4, column=0, sticky="w", pady=(0, 4))
        ligne_dep = ttk.Frame(c, style="Carte.TFrame")
        ligne_dep.grid(row=5, column=0, sticky="w")
        self.var_depart = tk.StringVar(value=calcul.formater_nombre(depart.montant) if depart else "0,00")
        self.var_date_depart = tk.StringVar(value=(depart.debut if depart else dt.date(dt.date.today().year, 1, 1)).isoformat())
        ttk.Entry(ligne_dep, textvariable=self.var_depart, width=12, font=(POLICE, 11)).pack(side="left")
        ttk.Label(ligne_dep, text=" $  au ", style="Carte.TLabel").pack(side="left")
        ttk.Entry(ligne_dep, textvariable=self.var_date_depart, width=12, font=(POLICE, 11)).pack(side="left")
        ttk.Label(c, text="Pour reprendre un solde déjà inscrit sur ton talon de paye.", style="Aide.TLabel").grid(
            row=6, column=0, sticky="w", pady=(2, 10))

        ttk.Label(
            c,
            text="Un changement de taux s'applique aux nouvelles entrées seulement :\n"
                 "l'historique garde le taux en vigueur à ce moment-là.",
            style="Note.TLabel", padding=10,
        ).grid(row=7, column=0, sticky="we", pady=(0, 16))

        ttk.Separator(c).grid(row=8, column=0, sticky="we", pady=(0, 12))
        ttk.Label(c, text="Mises à jour", style="Champ.TLabel").grid(row=9, column=0, sticky="w", pady=(0, 6))
        self.var_maj = tk.BooleanVar(value=base.maj_auto)
        ttk.Checkbutton(c, text="Vérifier automatiquement au démarrage (GitHub)", variable=self.var_maj,
                        style="Carte.TCheckbutton").grid(row=10, column=0, sticky="w")
        ligne_v = ttk.Frame(c, style="Carte.TFrame")
        ligne_v.grid(row=11, column=0, sticky="we", pady=(8, 12))
        ttk.Label(ligne_v, text=f"Version installée : {__version__}", style="Aide.TLabel").pack(side="left")
        ttk.Button(ligne_v, text="Vérifier maintenant",
                   command=lambda: self.parent.verifier_maj(silencieux=False, parent=self)).pack(side="right")

        ttk.Label(c, text="Sauvegarde", style="Champ.TLabel").grid(row=12, column=0, sticky="w", pady=(0, 6))
        ligne_s = ttk.Frame(c, style="Carte.TFrame")
        ligne_s.grid(row=13, column=0, sticky="w")
        ttk.Button(ligne_s, text="Exporter…", command=self._exporter).pack(side="left")
        ttk.Button(ligne_s, text="Importer…", command=self._importer).pack(side="left", padx=(8, 0))
        ttk.Label(c, text=f"Données : {base.chemin}", style="Aide.TLabel", wraplength=440).grid(
            row=14, column=0, sticky="w", pady=(8, 0))
        e_taux.focus_set()
        e_taux.select_range(0, "end")

    def valider(self):
        base = self.parent.base
        taux = calcul.parse_nombre(self.var_taux.get())
        pct = calcul.parse_nombre(self.var_pct.get())
        depart = calcul.parse_nombre(self.var_depart.get() or "0")
        date_depart = calcul.parse_date(self.var_date_depart.get())
        if taux <= 0:
            raise ValueError("Le taux horaire doit être plus grand que 0.")
        if depart < 0:
            raise ValueError("Le solde de départ ne peut pas être négatif.")
        base.taux = taux
        base.pct = pct
        base.maj_auto = self.var_maj.get()
        base.definir_solde_depart(depart, date_depart)
        self.parent.rafraichir()
        return True

    def _exporter(self):
        nom = f"vacances-sauvegarde-{dt.date.today().isoformat()}.db"
        chemin = filedialog.asksaveasfilename(parent=self, title="Exporter une sauvegarde", initialfile=nom,
                                              defaultextension=".db", filetypes=[("Sauvegarde", "*.db")])
        if chemin:
            self.parent.base.exporter(chemin)
            messagebox.showinfo("Sauvegarde", "Sauvegarde exportée.", parent=self)

    def _importer(self):
        chemin = filedialog.askopenfilename(parent=self, title="Importer une sauvegarde",
                                            filetypes=[("Sauvegarde", "*.db"), ("Tous les fichiers", "*.*")])
        if not chemin:
            return
        if not messagebox.askyesno("Importer", "Remplacer toutes les données actuelles par cette sauvegarde ?",
                                   icon="warning", parent=self):
            return
        try:
            self.parent.base.importer(chemin)
        except Exception as err:  # fichier corrompu, mauvais format…
            messagebox.showerror("Importer", f"Import impossible : {err}", parent=self)
            return
        self.parent.rafraichir()
        self.destroy()
        messagebox.showinfo("Importer", "Sauvegarde importée.", parent=self.parent)


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
                                      (e.debut if e else dt.date.today()).isoformat())

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

        self.recap = ttk.Frame(c, style="Recap.TFrame", padding=(14, 10))
        self.recap.grid(row=8, column=0, sticky="we")
        self.recap.columnconfigure(1, weight=1)
        self.lbl_recap = []
        for i, txt in enumerate(("Solde actuel", "Vacances prises", "Nouveau solde")):
            ttk.Label(self.recap, text=txt, style="Recap.TLabel").grid(row=i, column=0, sticky="w", pady=2)
            lbl = ttk.Label(self.recap, text="", style="Recap.TLabel")
            lbl.grid(row=i, column=1, sticky="e", pady=2, padx=(40, 0))
            self.lbl_recap.append(lbl)
        self.lbl_alerte = ttk.Label(c, text="", style="Alerte.TLabel")
        self.lbl_alerte.grid(row=9, column=0, sticky="w", pady=(8, 0))

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
            self.lbl_calc.configure(text=f"h  ×  {calcul.formater_argent(self.taux)}" if heures_mode else "$")
            nouveau = None
        else:
            if heures_mode:
                self.lbl_calc.configure(text=f"h  ×  {calcul.formater_argent(self.taux)}  =  "
                                             f"{calcul.formater_argent(montant)}")
            else:
                self.lbl_calc.configure(text="$")
            nouveau = solde - montant
        self.lbl_recap[0].configure(text=calcul.formater_argent(solde))
        self.lbl_recap[1].configure(text=calcul.formater_argent(-montant) if montant is not None else "—")
        if nouveau is None:
            self.lbl_recap[2].configure(text="—")
            self.lbl_alerte.configure(text="")
        else:
            txt = calcul.formater_argent(nouveau)
            if self.parent.base.taux > 0:
                txt += f"  (≈ {calcul.formater_nombre(nouveau / self.parent.base.taux)} h)"
            self.lbl_recap[2].configure(text=txt)
            self.lbl_alerte.configure(text="Attention : le solde deviendra négatif." if nouveau < 0 else "")

    def valider(self):
        date = calcul.parse_date(self.var_date.get())
        heures, montant = self._montant()
        base = self.parent.base
        if self.entree:
            base.modifier_vacances(self.entree.id, date, heures=heures, montant=None if heures else montant,
                                   note=self.var_note.get())
        else:
            base.ajouter_vacances(date, heures=heures, montant=None if heures else montant, note=self.var_note.get())
        self.parent.rafraichir()
        return True


class DialoguePeriode(Dialogue):
    titre = "Modifier une période de paye"

    def __init__(self, parent, entree):
        self.entree = entree
        super().__init__(parent)

    def construire(self, c):
        e = self.entree
        self.var_debut, _ = self.champ(c, 0, "Début", e.debut.isoformat())
        self.var_fin, _ = self.champ(c, 2, "Fin", e.fin.isoformat())
        self.var_heures, entree = self.champ(c, 4, "Heures travaillées", calcul.formater_simple(e.heures),
                                             aide=f"Taux de cette période : {calcul.formater_argent(e.taux)} · "
                                                  f"{calcul.formater_simple(e.pct)} %")
        entree.focus_set()
        entree.select_range(0, "end")

    def valider(self):
        debut = calcul.parse_date(self.var_debut.get())
        fin = calcul.parse_date(self.var_fin.get())
        heures = calcul.parse_nombre(self.var_heures.get())
        self.parent.base.modifier_periode(self.entree.id, debut, fin, heures)
        self.parent.rafraichir()
        return True


class Application(tk.Tk):
    def __init__(self, base):
        super().__init__()
        self.base = base
        self.release = None
        self._file_maj = queue.Queue()
        self.title(f"Calculateur de vacances v{__version__}")
        self.geometry("1040x740")
        self.minsize(900, 620)
        self.configure(bg=FOND)
        self._styles()
        self._construire()
        self.rafraichir()
        self._preremplir_periode()
        self.after(150, self._sonder_maj)
        if not base.est_configure:
            self.after(300, self.ouvrir_parametres)
        elif base.maj_auto:
            self.verifier_maj(silencieux=True)

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
        s.configure("CalculMontant.TLabel", background=BLANC, foreground=VERT, font=(POLICE, 14, "bold"))
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
        # Bannière de mise à jour (affichée seulement si une version plus récente existe)
        self.banniere = tk.Frame(self, bg=VERT_PALE, padx=24, pady=8)
        self.lbl_banniere = tk.Label(self.banniere, bg=VERT_PALE, fg=TEXTE, font=(POLICE, 10), anchor="w")
        self.lbl_banniere.pack(side="left", fill="x", expand=True)
        self.btn_plus_tard = ttk.Button(self.banniere, text="Plus tard", command=self.banniere.pack_forget)
        self.btn_plus_tard.pack(side="right", padx=(8, 0))
        self.btn_maj = ttk.Button(self.banniere, text="Mettre à jour", style="Primaire.TButton",
                                  command=self.installer_maj)
        self.btn_maj.pack(side="right")

        self.contenu = ttk.Frame(self, padding=24)
        self.contenu.pack(fill="both", expand=True)
        c = self.contenu

        entete = ttk.Frame(c)
        entete.pack(fill="x", pady=(0, 16))
        ttk.Label(entete, text="Mes vacances", style="Titre.TLabel").pack(side="left")
        ttk.Button(entete, text="⚙  Paramètres", command=self.ouvrir_parametres).pack(side="right")
        self.lbl_params = ttk.Label(entete, text="", style="Info.TLabel")
        self.lbl_params.pack(side="right", padx=16)

        # Tuiles de totaux
        tuiles = ttk.Frame(c)
        tuiles.pack(fill="x", pady=(0, 16))
        for i in range(3):
            tuiles.columnconfigure(i, weight=1, uniform="tuile")
        self.t_accumule = self._tuile(tuiles, 0, "TOTAL ACCUMULÉ", BLANC, TEXTE, GRIS)
        self.t_pris = self._tuile(tuiles, 1, "VACANCES PRISES", BLANC, ROUGE, GRIS)
        self.t_solde = self._tuile(tuiles, 2, "SOLDE DISPONIBLE", VERT, BLANC, VERT_TEXTE_PALE)

        # Formulaire : nouvelle période
        carte = tk.Frame(c, bg=BLANC, highlightbackground=BORD, highlightcolor=BORD, highlightthickness=1, padx=18, pady=14)
        carte.pack(fill="x", pady=(0, 16))
        ttk.Label(carte, text="Ajouter une période de paye", style="SousTitre.TLabel").grid(
            row=0, column=0, columnspan=7, sticky="w", pady=(0, 10))
        self.var_debut = tk.StringVar()
        self.var_fin = tk.StringVar()
        self.var_heures = tk.StringVar()
        for col, (txt, var, larg) in enumerate((("Début", self.var_debut, 12), ("Fin", self.var_fin, 12),
                                                 ("Heures travaillées", self.var_heures, 10))):
            ttk.Label(carte, text=txt, style="Aide.TLabel").grid(row=1, column=col, sticky="w", padx=(0, 14))
            e = ttk.Entry(carte, textvariable=var, width=larg, font=(POLICE, 11, "bold" if col == 2 else "normal"))
            e.grid(row=2, column=col, sticky="w", padx=(0, 14))
            e.bind("<Return>", lambda _e: self.ajouter_periode())
            if col == 2:
                self.entree_heures = e
        apercu = ttk.Frame(carte, style="Carte.TFrame")
        apercu.grid(row=3, column=0, columnspan=6, sticky="w", pady=(12, 0))
        ttk.Label(apercu, text="Vacances pour la période :", style="Calcul.TLabel").pack(side="left", padx=(0, 8))
        self.lbl_formule = ttk.Label(apercu, text="", style="Calcul.TLabel")
        self.lbl_formule.pack(side="left")
        self.lbl_resultat = ttk.Label(apercu, text="", style="CalculMontant.TLabel")
        self.lbl_resultat.pack(side="left", padx=(6, 0))
        carte.columnconfigure(3, weight=1)
        ttk.Button(carte, text="+  Ajouter", style="Primaire.TButton", command=self.ajouter_periode).grid(
            row=2, column=4, padx=(14, 8))
        ttk.Button(carte, text="−  Déduire des vacances", style="Danger.TButton",
                   command=self.deduire_vacances).grid(row=2, column=5)
        self.var_heures.trace_add("write", lambda *_: self._apercu_periode())

        # Historique
        hist = tk.Frame(c, bg=BLANC, highlightbackground=BORD, highlightcolor=BORD, highlightthickness=1)
        hist.pack(fill="both", expand=True)
        tete = ttk.Frame(hist, style="Carte.TFrame", padding=(18, 10))
        tete.pack(fill="x")
        ttk.Label(tete, text="Historique", style="SousTitre.TLabel").pack(side="left")
        ttk.Label(tete, text="Double-clic pour modifier · Suppr pour effacer", style="Aide.TLabel").pack(side="right")

        colonnes = ("date", "type", "heures", "montant", "solde")
        cadre_arbre = ttk.Frame(hist, style="Carte.TFrame")
        cadre_arbre.pack(fill="both", expand=True)
        self.arbre = ttk.Treeview(cadre_arbre, columns=colonnes, show="headings", selectmode="browse")
        for col, txt, larg, ancre in (("date", "Période / date", 200, "w"), ("type", "Type", 220, "w"),
                                      ("heures", "Heures", 90, "e"), ("montant", "Montant", 130, "e"),
                                      ("solde", "Solde cumulé", 140, "e")):
            self.arbre.heading(col, text=txt, anchor=ancre)
            self.arbre.column(col, width=larg, anchor=ancre, stretch=col in ("date", "type"))
        self.arbre.tag_configure("vacances", foreground=ROUGE)
        self.arbre.tag_configure("depart", foreground=GRIS)
        defil = ttk.Scrollbar(cadre_arbre, orient="vertical", command=self.arbre.yview)
        self.arbre.configure(yscrollcommand=defil.set)
        self.arbre.pack(side="left", fill="both", expand=True)
        defil.pack(side="right", fill="y")
        self.arbre.bind("<Double-1>", lambda _e: self.modifier_selection())
        self.arbre.bind("<Return>", lambda _e: self.modifier_selection())
        self.arbre.bind("<Delete>", lambda _e: self.supprimer_selection())

        menu = tk.Menu(self, tearoff=False)
        menu.add_command(label="Modifier…", command=self.modifier_selection)
        menu.add_command(label="Supprimer", command=self.supprimer_selection)

        def menu_contextuel(ev):
            ligne = self.arbre.identify_row(ev.y)
            if ligne:
                self.arbre.selection_set(ligne)
                menu.tk_popup(ev.x_root, ev.y_root)
        self.arbre.bind("<Button-3>", menu_contextuel)

    def _tuile(self, parent, col, titre, fond, couleur_valeur, couleur_info):
        cadre = tk.Frame(parent, bg=fond, padx=18, pady=14,
                         highlightbackground=BORD if fond == BLANC else fond,
                         highlightcolor=BORD if fond == BLANC else fond, highlightthickness=1)
        cadre.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 0))
        tk.Label(cadre, text=titre, bg=fond, fg=couleur_info, font=(POLICE, 9)).pack(anchor="w")
        valeur = tk.Label(cadre, text="", bg=fond, fg=couleur_valeur, font=(POLICE, 20, "bold"))
        valeur.pack(anchor="w")
        info = tk.Label(cadre, text="", bg=fond, fg=couleur_info, font=(POLICE, 9))
        info.pack(anchor="w")
        return valeur, info

    # --- Affichage ----------------------------------------------------------

    def rafraichir(self):
        base = self.base
        self.lbl_params.configure(
            text=f"Taux : {calcul.formater_argent(base.taux)}/h  ·  Vacances : {calcul.formater_simple(base.pct)} %")
        t = base.totaux()
        entrees = base.entrees()
        depart = next((e for e in entrees if e.type == "depart"), None)
        premiere = entrees[0].debut if entrees else None

        self.t_accumule[0].configure(text=calcul.formater_argent(t.accumule))
        if premiere:
            info = f"depuis le {premiere.isoformat()}" + (" (incl. solde de départ)" if depart else "")
        else:
            info = "aucune période inscrite"
        self.t_accumule[1].configure(text=info)
        self.t_pris[0].configure(text=calcul.formater_argent(-t.pris) if t.pris else calcul.formater_argent(0))
        self.t_pris[1].configure(text=f"{calcul.formater_nombre(t.heures_prises)} h")
        self.t_solde[0].configure(text=calcul.formater_argent(t.solde))
        self.t_solde[1].configure(
            text=f"≈ {calcul.formater_nombre(t.solde_heures)} h de vacances" if t.solde_heures is not None else "")

        self.arbre.delete(*self.arbre.get_children())
        for e in reversed(entrees):
            heures = calcul.formater_nombre(e.heures) if e.heures is not None else "—"
            libelle = LIBELLES_TYPE[e.type] + (f" — {e.note}" if e.note else "")
            montant = calcul.formater_argent(e.montant) if e.type == "depart" else calcul.formater_signe(e.montant)
            self.arbre.insert("", "end", iid=str(e.id), tags=(e.type,),
                              values=(_date_courte(e), libelle, heures, montant, calcul.formater_argent(e.solde)))
        self._apercu_periode()

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
        self.entree_heures.focus_set()

    def _apercu_periode(self):
        taux, pct = self.base.taux, self.base.pct
        try:
            heures = calcul.parse_nombre(self.var_heures.get())
        except ValueError:
            heures = None
        h = calcul.formater_simple(heures) if heures is not None else "…"
        self.lbl_formule.configure(text=f"{h} h × {calcul.formater_argent(taux)} × {calcul.formater_simple(pct)} % =")
        self.lbl_resultat.configure(
            text=calcul.formater_argent(calcul.vacances_periode(heures, taux, pct)) if heures is not None else "—")

    # --- Actions ------------------------------------------------------------

    def ajouter_periode(self):
        try:
            if self.base.taux <= 0:
                raise ValueError("Entre d'abord ton taux horaire dans les paramètres.")
            debut = calcul.parse_date(self.var_debut.get())
            fin = calcul.parse_date(self.var_fin.get())
            heures = calcul.parse_nombre(self.var_heures.get())
            if self.base.periode_existe(debut) and not messagebox.askyesno(
                    "Période existante", f"Une période commençant le {debut.isoformat()} existe déjà.\n"
                                         "L'ajouter quand même ?", parent=self):
                return
            self.base.ajouter_periode(debut, fin, heures)
        except ValueError as err:
            messagebox.showerror("Valeur invalide", str(err), parent=self)
            return
        self.rafraichir()
        self._preremplir_periode()

    def deduire_vacances(self):
        DialogueVacances(self)

    def ouvrir_parametres(self):
        DialogueParametres(self)

    def _entree_selectionnee(self):
        sel = self.arbre.selection()
        if not sel:
            return None
        try:
            return self.base.entree(int(sel[0]))
        except KeyError:
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
            self.ouvrir_parametres()

    def supprimer_selection(self):
        e = self._entree_selectionnee()
        if e is None:
            return
        desc = f"{LIBELLES_TYPE[e.type].lower()} du {_date_courte(e)} ({calcul.formater_signe(e.montant)})"
        if messagebox.askyesno("Supprimer", f"Supprimer {desc} ?", icon="warning", parent=self):
            self.base.supprimer(e.id)
            self.rafraichir()
            self._preremplir_periode()

    # --- Mises à jour -------------------------------------------------------

    def verifier_maj(self, silencieux=True, parent=None):
        def travail():
            try:
                self._file_maj.put(("verif", silencieux, parent, updater.verifier(__version__)))
            except Exception as err:
                self._file_maj.put(("erreur", silencieux, parent, err))
        threading.Thread(target=travail, daemon=True).start()

    def _sonder_maj(self):
        try:
            while True:
                genre, silencieux, parent, valeur = self._file_maj.get_nowait()
                parent = parent if parent is not None and parent.winfo_exists() else self
                if genre == "verif":
                    if valeur:
                        self.release = valeur
                        self._afficher_banniere()
                        if not silencieux:
                            messagebox.showinfo("Mise à jour", f"La version {valeur.version} est disponible.",
                                                parent=parent)
                    elif not silencieux:
                        messagebox.showinfo("Mise à jour", "Tu as déjà la dernière version.", parent=parent)
                elif genre == "erreur" and not silencieux:
                    messagebox.showerror("Mise à jour", f"Impossible de vérifier les mises à jour :\n{valeur}",
                                         parent=parent)
                elif genre == "telecharge":
                    updater.lancer_remplacement(valeur)
                    self.destroy()
                    return
                elif genre == "echec":
                    messagebox.showerror("Mise à jour", f"Le téléchargement a échoué :\n{valeur}\n\n"
                                                        "La page de téléchargement va s'ouvrir.", parent=self)
                    webbrowser.open(self.release.url_page)
                    self._afficher_banniere()
        except queue.Empty:
            pass
        self.after(150, self._sonder_maj)

    def _afficher_banniere(self):
        self.lbl_banniere.configure(text=f"Une nouvelle version (v{self.release.version}) est disponible sur GitHub.")
        self.btn_maj.state(["!disabled"])
        self.banniere.pack(fill="x", before=self.contenu)

    def installer_maj(self):
        release = self.release
        if release is None:
            return
        if not updater.peut_installer(release):
            webbrowser.open(release.url_page)
            return
        self.lbl_banniere.configure(text=f"Téléchargement de la version {release.version}…")
        self.btn_maj.state(["disabled"])

        def travail():
            try:
                self._file_maj.put(("telecharge", True, None, updater.telecharger(release)))
            except Exception as err:
                self._file_maj.put(("echec", True, None, err))
        threading.Thread(target=travail, daemon=True).start()


def main():
    base = Base()
    try:
        Application(base).mainloop()
    finally:
        base.fermer()

# Calculateur de vacances

Petite application Windows pour contre-vérifier ses vacances accumulées.

- Le **% de vacances** se règle dans **Fichier → Outils → Pourcentage de vacances**. Le **taux horaire** n'est
  jamais entré à la main : il est calculé à partir de chaque relevé de paye (montant brut des heures ÷ heures).
- La **paie de férié** du relevé (« Congé Férié ») est lue et comptée dans le calcul :
  vacances = (heures × taux + férié) × %.
- À chaque paye, entre le **nombre d'heures** de la période : l'application affiche
  les vacances gagnées pour la période (`(heures × taux + férié) × %`) et le **total cumulé**.
- Quand tu prends des vacances : **Fichier → J'ai pris des vacances** (Ctrl+D), en heures ou en $.
  Les **vacances versées** indiquées sur un relevé sont inscrites automatiquement.
- **Fichier → Ajouter des relevés de paye** : choisis plusieurs PDF d'un coup, une période est créée par
  relevé (dates, heures, taux, férié, vacances versées) ; les relevés déjà présents sont ignorés.
- L'historique montre le solde cumulé ligne par ligne. Double-clic pour modifier, Suppr pour effacer.
- Optionnel : un **mot de passe** demandé à l'ouverture (Fichier → Outils → Définir un mot de passe).
  Avec un mot de passe, le fichier de données et ses sauvegardes sont **chiffrés** (AES-256-GCM, clé tirée
  du mot de passe par scrypt) : sans le mot de passe, ils sont illisibles — aucune récupération possible.
- **Confidentiel** (à droite de la barre de menus) cache tous les chiffres, pour une démonstration.
- **Fichier → Outils → Affichage** permet de masquer ou d'afficher les soldes et l'historique.
- Les dates se tapent (AAAA-MM-JJ) ou se choisissent dans un **calendrier**.
- Le relevé PDF joint est **lu pour contre-vérifier les heures** (et les dates) de la période ;
  les dates, les heures et le taux de la période sont repris du relevé.
- Tu peux **joindre le relevé de paye (PDF)** à une période ou à des vacances prises.
  Il est conservé dans la base de l'application sous un nom neutre (`Releve_<début>_au_<fin>.pdf`) ;
  clic droit sur la ligne pour l'ouvrir ou l'enregistrer.
- **Fichier → Outils → Revalider les relevés enregistrés** relit tous les relevés joints et liste ce qui
  ne concorde pas (dates, heures, taux, férié), avec correction en un clic.
- **Fichier → Outils → Solde de départ** reprend un solde déjà inscrit sur ton talon de paye.
- L'historique est regroupé par **année de référence** (1er mai au 30 avril) avec le gagné, le pris et le solde.
- **Fichier → Exporter un rapport (Excel)** : détail et sommaire par année de référence, à présenter à la paie.
- **Fichier → Outils → Date d'embauche** : l'application rappelle le passage de 4 % à **6 %** quand tu atteins
  3 ans de service continu au 30 avril (seulement si le % est à 4 %), et peut recalculer les périodes de l'année.

## Télécharger

Va dans [Releases](https://github.com/EricGloutnez/calculateur-vacances/releases/latest)
et télécharge **`CalculateurVacances.exe`**, puis double-clique dessus.

Au premier lancement, l'application **s'installe d'elle-même** (sans droits d'administrateur)
dans `%LOCALAPPDATA%\Programs\CalculateurVacances` et crée un raccourci
**« Calculateur de vacances »** sur le Bureau et dans le menu Démarrer.
Le fichier téléchargé peut ensuite être supprimé.

Pour désinstaller : supprime le dossier `%LOCALAPPDATA%\Programs\CalculateurVacances`
et les deux raccourcis (tes données restent dans `%APPDATA%\CalculateurVacances`).

> Au premier lancement, Windows SmartScreen peut afficher « Windows a protégé votre ordinateur »
> (l'exécutable n'est pas signé). Clique sur **Informations complémentaires → Exécuter quand même**.

## Tes données

La base de données (SQLite) est intégrée à l'application et enregistrée dans
`%APPDATA%\CalculateurVacances\vacances.db`. Elle contient aussi les relevés PDF joints et est conservée lors des mises à jour.
**Sauvegarde automatique** : au premier démarrage, l'application demande (une seule fois) le dossier de
sauvegarde — idéalement OneDrive ou iCloud Drive — puis y copie la base à chaque fermeture (toutes les
copies sont gardées). Après le 30 avril, elle propose la **sauvegarde complète de l'année** : un zip
`Sauvegarde-annee-AAAA-AAAA.zip` avec la base complète, les copies de l'année, le rapport et les relevés
(avec un mot de passe, seuls les fichiers chiffrés y vont). Aussi dans **Fichier → Outils → Sauvegarde
complète de l'année**. Le dossier se change dans **Fichier → Outils → Dossier de sauvegarde**, et
**Fichier → Restaurer une sauvegarde** remet une copie en place. **Fichier → Exporter une sauvegarde**
fait une copie manuelle, par exemple pour passer à un autre ordinateur.

## Mises à jour automatiques

L'application gère elle-même sa version : à chaque ouverture, elle vérifie la dernière Release
sur GitHub et, s'il y en a une plus récente, la télécharge et l'installe d'elle-même
(elle se ferme puis se rouvre). L'utilisateur n'a aucune action à faire.

## Publier une nouvelle version (développeur)

Dans l'onglet **Actions → Release → Run workflow**, entre le numéro (ex. `1.1.0`).
Ou en ligne de commande :

```powershell
gh workflow run release.yml -R EricGloutnez/calculateur-vacances -f version=1.1.0
```

GitHub Actions lance les tests, fabrique `CalculateurVacances.exe` avec PyInstaller
et publie la Release. Toutes les copies installées la proposeront au prochain démarrage.

## Développement

```powershell
python -m pip install -r requirements-dev.txt   # inclut pypdf (lecture des relevés)
python main.py          # lancer l'application
python -m pytest        # tests
```

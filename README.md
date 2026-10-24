# Calculateur de vacances

Petite application Windows pour contre-vérifier ses vacances accumulées.

- Entre ton **taux horaire** et ton **% de vacances** une seule fois (Paramètres).
- À chaque paye, entre le **nombre d'heures** de la période : l'application affiche
  les vacances gagnées pour la période (`heures × taux × %`) et le **total cumulé**.
- Quand tu prends des vacances, clique sur **Déduire des vacances** (en heures ou en $).
- L'historique montre le solde cumulé ligne par ligne. Double-clic pour modifier, Suppr pour effacer.
- Optionnel : un **mot de passe** demandé à l'ouverture (Paramètres → Mot de passe à l'ouverture).
  C'est un verrou d'accès : le fichier de données lui-même n'est pas chiffré.
- Les dates se tapent (AAAA-MM-JJ) ou se choisissent dans un **calendrier**.
- Le relevé PDF joint est **lu pour contre-vérifier les heures** (et les dates) de la période ;
  si les heures sont vides, elles sont remplies à partir du relevé.
- Tu peux **joindre le relevé de paye (PDF)** à une période ou à des vacances prises.
  Il est conservé dans la base de l'application ; clic droit sur la ligne pour l'ouvrir ou l'enregistrer.

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
Dans Paramètres, **Exporter / Importer** permet de faire une sauvegarde ou de passer
à un autre ordinateur.

## Mises à jour automatiques

Au démarrage, l'application vérifie la dernière Release sur GitHub. Si une version
plus récente existe, une bannière s'affiche : **Mettre à jour** télécharge le nouveau
`.exe`, remplace l'ancien et relance l'application.

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

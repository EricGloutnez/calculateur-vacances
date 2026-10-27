# Calculateur de vacances

Petite application Windows pour contre-vérifier ses vacances accumulées.

- Le **% de vacances** se règle dans **Fichier → Outils → Pourcentage de vacances**. Le **taux horaire** est
  calculé à partir du relevé de paye (montant brut des heures ÷ nombre d'heures) ; sans relevé, celui de
  Outils → Paramètres est utilisé.
- La **paie de férié** du relevé (« Congé Férié ») est lue et comptée dans le calcul :
  vacances = (heures × taux + férié) × %.
- À chaque paye, entre le **nombre d'heures** de la période : l'application affiche
  les vacances gagnées pour la période (`(heures × taux + férié) × %`) et le **total cumulé**.
- Quand tu prends des vacances : **Fichier → J'ai pris des vacances** (Ctrl+D), en heures ou en $.
- L'historique montre le solde cumulé ligne par ligne. Double-clic pour modifier, Suppr pour effacer.
- Optionnel : un **mot de passe** demandé à l'ouverture (Paramètres → Mot de passe à l'ouverture).
  C'est un verrou d'accès : le fichier de données lui-même n'est pas chiffré.
- **Confidentiel** (à droite de la barre de menus) cache tous les chiffres, pour une démonstration.
- **Fichier → Outils → Affichage** permet de masquer ou d'afficher les soldes et l'historique.
- Les dates se tapent (AAAA-MM-JJ) ou se choisissent dans un **calendrier**.
- Le relevé PDF joint est **lu pour contre-vérifier les heures** (et les dates) de la période ;
  les dates, les heures et le taux de la période sont repris du relevé.
- Tu peux **joindre le relevé de paye (PDF)** à une période ou à des vacances prises.
  Il est conservé dans la base de l'application sous un nom neutre (`Releve_<début>_au_<fin>.pdf`) ;
  clic droit sur la ligne pour l'ouvrir ou l'enregistrer.

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

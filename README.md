# Calculateur de vacances

Petite application Windows pour contre-vérifier ses vacances accumulées.

- Entre ton **taux horaire** et ton **% de vacances** une seule fois (Paramètres).
- À chaque paye, entre le **nombre d'heures** de la période : l'application affiche
  les vacances gagnées pour la période (`heures × taux × %`) et le **total cumulé**.
- Quand tu prends des vacances, clique sur **Déduire des vacances** (en heures ou en $).
- L'historique montre le solde cumulé ligne par ligne. Double-clic pour modifier, Suppr pour effacer.

## Télécharger

Va dans [Releases](https://github.com/EricGloutnez/calculateur-vacances/releases/latest)
et télécharge **`CalculateurVacances.exe`**. Aucune installation : double-clique pour l'ouvrir.

> Au premier lancement, Windows SmartScreen peut afficher « Windows a protégé votre ordinateur »
> (l'exécutable n'est pas signé). Clique sur **Informations complémentaires → Exécuter quand même**.

## Tes données

La base de données (SQLite) est intégrée à l'application et enregistrée dans
`%APPDATA%\CalculateurVacances\vacances.db`. Elle est conservée lors des mises à jour.
Dans Paramètres, **Exporter / Importer** permet de faire une sauvegarde ou de passer
à un autre ordinateur.

## Mises à jour automatiques

Au démarrage, l'application vérifie la dernière Release sur GitHub. Si une version
plus récente existe, une bannière s'affiche : **Mettre à jour** télécharge le nouveau
`.exe`, remplace l'ancien et relance l'application.

## Publier une nouvelle version (développeur)

```powershell
git tag v1.1.0
git push origin v1.1.0
```

GitHub Actions lance les tests, fabrique `CalculateurVacances.exe` avec PyInstaller
et publie la Release. Toutes les copies installées la proposeront au prochain démarrage.

## Développement

```powershell
python -m pip install -r requirements-dev.txt
python main.py          # lancer l'application
python -m pytest        # tests
```

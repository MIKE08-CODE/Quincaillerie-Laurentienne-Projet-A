# desktop — Application de bureau

Application Windows du personnel de Quincaillerie Laurentienne. Au L1, elle se connecte à l'API et
affiche la liste des produits (pagination, recherche FR/EN), avec des messages clairs quand l'API est
inaccessible (A.8.3).

**Stack :** C# .NET 8, WPF, patron MVVM (CommunityToolkit.Mvvm 8.4) ; tests xUnit.

## Fonctionnalités L1

| Élément | Détail |
|---|---|
| Liste des produits | `GET /products` (25 par page, tri par nom), boutons Précédent / Suivant |
| Recherche | `GET /search?q=` quand le champ de recherche n'est pas vide |
| Chargement | Appels HTTP **asynchrones** (aucune interface figée), indicateur « Chargement… » |
| Erreurs | Bandeau d'erreur (API injoignable, délai dépassé, limite de requêtes, erreur serveur) ; « Actualiser » reste possible |
| Configuration | URL de l'API dans `appsettings.json`, à côté de l'exécutable |

La connexion du personnel avec MFA et les écrans de préparation, de cueillette et de stocks arrivent
aux jalons suivants.

## Configuration de l'URL de l'API

`appsettings.json` (copié à côté de l'exécutable) :

```json
{ "Api": { "BaseUrl": "http://localhost:8000/api/v1", "TimeoutSeconds": 10 } }
```

La variable d'environnement `QL_API_BASE_URL` a priorité sur le fichier, par exemple pour viser l'API
déployée (`https://<hôte-de-l-api>/api/v1`, **à compléter après le déploiement**). L'URL doit être
absolue (`http` ou `https`) ; une URL invalide arrête l'application avec un message explicite. Aucun
secret n'est stocké dans ce fichier.

## Lancer

Prérequis : Windows, SDK .NET 8, et l'API lancée (voir `api/README.md`).

```powershell
cd desktop
dotnet run --project src/QuincaillerieLaurentienne.Desktop
# ou, vers une autre API :
$env:QL_API_BASE_URL = "https://<hôte-de-l-api>/api/v1"; dotnet run --project src/QuincaillerieLaurentienne.Desktop
```

## Contrôles

```powershell
dotnet build -c Release                                   # avertissements traités comme des erreurs
dotnet test -c Release --filter "Category!=Integration"   # tests unitaires (HTTP simulé)
$env:QL_API_INTEGRATION_URL = "http://localhost:8000/api/v1"
dotnet test -c Release --filter Category=Integration      # contre une API réelle
dotnet list package --vulnerable --include-transitive     # audit NuGet
```

Le workflow `desktop-ci` (runner Windows) exécute la restauration, le build, les tests hors
intégration et l'audit NuGet.

| Dossier | Rôle |
|---|---|
| `src/QuincaillerieLaurentienne.Desktop/Models/` | Modèles de données (produit, page, paramètres) |
| `src/QuincaillerieLaurentienne.Desktop/ViewModels/` | `ProductListViewModel` (logique de présentation) |
| `src/QuincaillerieLaurentienne.Desktop/Views/` | `MainWindow` (XAML) |
| `src/QuincaillerieLaurentienne.Desktop/Services/` | Client HTTP de l'API, lecture de la configuration |
| `src/QuincaillerieLaurentienne.Desktop/Resources/` | Styles et dictionnaires (à venir) |
| `tests/QuincaillerieLaurentienne.Desktop.Tests/` | Tests xUnit |

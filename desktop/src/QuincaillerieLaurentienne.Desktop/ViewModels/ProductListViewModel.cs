using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using QuincaillerieLaurentienne.Desktop.Models;
using QuincaillerieLaurentienne.Desktop.Services;

namespace QuincaillerieLaurentienne.Desktop.ViewModels;

/// <summary>
/// Liste des produits de l'API en ligne (L1) : chargement asynchrone, pagination, recherche et messages
/// d'erreur clairs quand l'API est inaccessible (A.8.3).
/// </summary>
public sealed partial class ProductListViewModel(ICatalogApiClient api, string apiBaseUrl) : ObservableObject
{
    public const int PageSize = 25;

    public ObservableCollection<ProductSummary> Products { get; } = [];

    /// <summary>Adresse de l'API visée, affichée dans la barre d'état.</summary>
    public string ApiBaseUrl { get; } = apiBaseUrl;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(IsNotLoading))]
    [NotifyCanExecuteChangedFor(nameof(LoadCommand), nameof(NextPageCommand), nameof(PreviousPageCommand))]
    private bool isLoading;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(HasError))]
    private string? errorMessage;

    [ObservableProperty]
    private string statusText = "Prêt.";

    [ObservableProperty]
    private string searchText = string.Empty;

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(NextPageCommand), nameof(PreviousPageCommand))]
    [NotifyPropertyChangedFor(nameof(PageText))]
    private int currentPage = 1;

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(NextPageCommand))]
    [NotifyPropertyChangedFor(nameof(PageText))]
    private int total;

    public bool IsNotLoading => !IsLoading;

    public bool HasError => !string.IsNullOrEmpty(ErrorMessage);

    public int PageCount => Math.Max(1, (int)Math.Ceiling(Total / (double)PageSize));

    public string PageText => $"Page {CurrentPage} sur {PageCount}";

    /// <summary>Recherche active (texte non vide) : sinon, liste complète triée par nom.</summary>
    private string ActiveQuery => SearchText.Trim();

    [RelayCommand(CanExecute = nameof(CanLoad))]
    private Task LoadAsync() => LoadPageAsync(1);

    [RelayCommand(CanExecute = nameof(CanGoNext))]
    private Task NextPageAsync() => LoadPageAsync(CurrentPage + 1);

    [RelayCommand(CanExecute = nameof(CanGoPrevious))]
    private Task PreviousPageAsync() => LoadPageAsync(CurrentPage - 1);

    private bool CanLoad() => !IsLoading;

    private bool CanGoNext() => !IsLoading && CurrentPage < PageCount;

    private bool CanGoPrevious() => !IsLoading && CurrentPage > 1;

    public async Task LoadPageAsync(int page)
    {
        IsLoading = true;
        ErrorMessage = null;
        StatusText = "Chargement des produits…";
        try
        {
            var query = ActiveQuery;
            var result = query.Length > 0
                ? await api.SearchAsync(query, page, PageSize)
                : await api.GetProductsAsync(page, PageSize);
            Products.Clear();
            foreach (var product in result.Items)
            {
                Products.Add(product);
            }

            Total = result.Total;
            CurrentPage = page;
            StatusText = result.Total == 0
                ? (query.Length > 0 ? $"Aucun produit ne correspond à « {query} »." : "Aucun produit.")
                : $"{result.Total} produit(s).";
        }
        catch (ApiException ex)
        {
            ErrorMessage = Describe(ex);
            StatusText = "Échec du chargement.";
        }
        finally
        {
            IsLoading = false;
        }
    }

    /// <summary>Message compréhensible pour le personnel, sans détail technique sensible.</summary>
    public string Describe(ApiException ex) => ex.Code switch
    {
        "network_error" => $"Impossible de joindre l'API ({ApiBaseUrl}). Vérifiez la connexion réseau ou l'adresse dans appsettings.json.",
        "timeout" => "L'API n'a pas répondu à temps. Réessayez dans un instant.",
        "rate_limited" => "Trop de requêtes. Réessayez dans un moment.",
        _ => $"L'API a renvoyé une erreur ({ex.Status} — {ex.Code}). Réessayez plus tard.",
    };
}

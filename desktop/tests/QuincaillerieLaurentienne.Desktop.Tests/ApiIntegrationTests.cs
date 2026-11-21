using QuincaillerieLaurentienne.Desktop.Models;
using QuincaillerieLaurentienne.Desktop.Services;
using QuincaillerieLaurentienne.Desktop.ViewModels;

namespace QuincaillerieLaurentienne.Desktop.Tests;

/// <summary>
/// Tests contre une API RÉELLE (locale ou déployée), exclus de la CI :
/// <c>QL_API_INTEGRATION_URL=http://localhost:8000/api/v1 dotnet test --filter Category=Integration</c>
/// </summary>
[Trait("Category", "Integration")]
public class ApiIntegrationTests
{
    private static string BaseUrl =>
        Environment.GetEnvironmentVariable("QL_API_INTEGRATION_URL")
        ?? throw new InvalidOperationException("Définir QL_API_INTEGRATION_URL pour ce test d'intégration.");

    [Fact]
    public async Task The_view_model_lists_the_products_of_the_real_api()
    {
        var settings = new ApiSettings { BaseUrl = SettingsLoader.Validate(BaseUrl), TimeoutSeconds = 10 };
        using var http = CatalogApiClient.CreateHttpClient(settings);
        var vm = new ProductListViewModel(new CatalogApiClient(http), settings.BaseUrl);

        await vm.LoadCommand.ExecuteAsync(null);

        Assert.False(vm.HasError, vm.ErrorMessage);
        Assert.True(vm.Total >= 150);
        Assert.Equal(ProductListViewModel.PageSize, vm.Products.Count);
        Assert.All(vm.Products, p => Assert.False(string.IsNullOrWhiteSpace(p.NameFr)));

        vm.SearchText = "equerre";
        await vm.LoadCommand.ExecuteAsync(null);
        Assert.Contains(vm.Products, p => p.Sku.StartsWith("EQUE-", StringComparison.Ordinal));
    }
}

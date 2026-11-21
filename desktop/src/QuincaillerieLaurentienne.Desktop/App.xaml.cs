using System.Net.Http;
using System.Windows;
using QuincaillerieLaurentienne.Desktop.Services;
using QuincaillerieLaurentienne.Desktop.ViewModels;
using QuincaillerieLaurentienne.Desktop.Views;

namespace QuincaillerieLaurentienne.Desktop;

/// <summary>Point d'entrée : lit la configuration, crée le client de l'API et ouvre la fenêtre.</summary>
public partial class App : Application
{
    private HttpClient? http;

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        try
        {
            var settings = SettingsLoader.Load();
            http = CatalogApiClient.CreateHttpClient(settings);
            var viewModel = new ProductListViewModel(new CatalogApiClient(http), settings.BaseUrl);
            new MainWindow(viewModel).Show();
        }
        catch (Exception ex) when (ex is InvalidOperationException or System.Text.Json.JsonException)
        {
            MessageBox.Show(
                $"Configuration invalide : {ex.Message}",
                "Quincaillerie Laurentienne",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
            Shutdown(1);
        }
    }

    protected override void OnExit(ExitEventArgs e)
    {
        http?.Dispose();
        base.OnExit(e);
    }
}

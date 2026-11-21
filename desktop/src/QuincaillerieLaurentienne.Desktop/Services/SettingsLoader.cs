using System.IO;
using System.Text.Json;
using QuincaillerieLaurentienne.Desktop.Models;

namespace QuincaillerieLaurentienne.Desktop.Services;

/// <summary>
/// Lit l'URL de l'API dans appsettings.json (à côté de l'exécutable, A.8.3). La variable d'environnement
/// <c>QL_API_BASE_URL</c>, si elle existe, a priorité : utile pour viser l'API déployée sans modifier
/// le fichier. Aucun secret n'est lu ici.
/// </summary>
public static class SettingsLoader
{
    public const string EnvironmentVariable = "QL_API_BASE_URL";

    public static ApiSettings Load(string? path = null, string? environmentOverride = null)
    {
        path ??= Path.Combine(AppContext.BaseDirectory, "appsettings.json");
        var settings = new ApiSettings();
        if (File.Exists(path))
        {
            using var document = JsonDocument.Parse(File.ReadAllText(path));
            if (document.RootElement.TryGetProperty("Api", out var api))
            {
                settings = api.Deserialize<ApiSettings>() ?? settings;
            }
        }

        var overrideUrl = environmentOverride ?? Environment.GetEnvironmentVariable(EnvironmentVariable);
        if (!string.IsNullOrWhiteSpace(overrideUrl))
        {
            settings.BaseUrl = overrideUrl.Trim();
        }

        settings.BaseUrl = Validate(settings.BaseUrl);
        settings.TimeoutSeconds = Math.Clamp(settings.TimeoutSeconds, 1, 120);
        return settings;
    }

    /// <summary>URL absolue http(s) obligatoire; la barre oblique finale est retirée.</summary>
    public static string Validate(string url)
    {
        var valid = Uri.TryCreate(url.Trim(), UriKind.Absolute, out var uri)
            && (uri.Scheme == Uri.UriSchemeHttp || uri.Scheme == Uri.UriSchemeHttps);
        if (!valid || uri is null)
        {
            throw new InvalidOperationException($"URL de l'API invalide dans la configuration : « {url} ».");
        }

        return uri.ToString().TrimEnd('/');
    }
}

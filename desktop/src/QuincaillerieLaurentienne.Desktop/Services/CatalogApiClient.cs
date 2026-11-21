using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using QuincaillerieLaurentienne.Desktop.Models;

namespace QuincaillerieLaurentienne.Desktop.Services;

/// <summary>Erreur de l'API, avec le code stable renvoyé par le serveur (p. ex. « rate_limited »).</summary>
public sealed class ApiException(int status, string code, string message) : Exception(message)
{
    public int Status { get; } = status;

    public string Code { get; } = code;
}

public interface ICatalogApiClient
{
    Task<Page<ProductSummary>> GetProductsAsync(int page, int size, CancellationToken cancellationToken = default);

    Task<Page<ProductSummary>> SearchAsync(string query, int page, int size, CancellationToken cancellationToken = default);
}

/// <summary>Client HTTP asynchrone (A.8.3 : aucune interface figée) vers le catalogue public.</summary>
public sealed class CatalogApiClient(HttpClient http) : ICatalogApiClient
{
    public Task<Page<ProductSummary>> GetProductsAsync(int page, int size, CancellationToken cancellationToken = default) =>
        GetAsync<Page<ProductSummary>>($"products?page={page}&size={size}&sort=name_asc", cancellationToken);

    public Task<Page<ProductSummary>> SearchAsync(string query, int page, int size, CancellationToken cancellationToken = default) =>
        GetAsync<Page<ProductSummary>>($"search?q={Uri.EscapeDataString(query)}&page={page}&size={size}", cancellationToken);

    /// <summary>HttpClient vers l'API configurée (barre oblique finale ajoutée pour les chemins relatifs).</summary>
    public static HttpClient CreateHttpClient(ApiSettings settings, HttpMessageHandler? handler = null)
    {
        var client = handler is null ? new HttpClient() : new HttpClient(handler);
        client.BaseAddress = new Uri(settings.BaseUrl.TrimEnd('/') + "/");
        client.Timeout = TimeSpan.FromSeconds(settings.TimeoutSeconds);
        client.DefaultRequestHeaders.Accept.ParseAdd("application/json");
        return client;
    }

    private async Task<T> GetAsync<T>(string relativeUrl, CancellationToken cancellationToken)
    {
        HttpResponseMessage response;
        try
        {
            response = await http.GetAsync(relativeUrl, cancellationToken).ConfigureAwait(false);
        }
        catch (HttpRequestException)
        {
            throw new ApiException(0, "network_error", "API injoignable.");
        }
        catch (TaskCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            throw new ApiException(0, "timeout", "L'API n'a pas répondu à temps.");
        }

        using (response)
        {
            var status = (int)response.StatusCode;
            if (!response.IsSuccessStatusCode)
            {
                var code = await ReadErrorCodeAsync(response, cancellationToken).ConfigureAwait(false);
                throw new ApiException(status, code, $"Erreur HTTP {status}.");
            }

            var body = await response.Content.ReadFromJsonAsync<T>(cancellationToken).ConfigureAwait(false);
            return body ?? throw new ApiException(status, "empty_response", "Réponse vide de l'API.");
        }
    }

    private static async Task<string> ReadErrorCodeAsync(HttpResponseMessage response, CancellationToken cancellationToken)
    {
        try
        {
            var text = await response.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false);
            using var document = JsonDocument.Parse(text);
            if (document.RootElement.TryGetProperty("detail", out var detail)
                && detail.ValueKind == JsonValueKind.Object
                && detail.TryGetProperty("code", out var code))
            {
                return code.GetString() ?? "unknown_error";
            }
        }
        catch (JsonException)
        {
            // corps non JSON : code générique ci-dessous
        }

        return $"http_{(int)response.StatusCode}";
    }
}

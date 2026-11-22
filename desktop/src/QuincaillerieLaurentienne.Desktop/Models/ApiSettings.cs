namespace QuincaillerieLaurentienne.Desktop.Models;

/// <summary>Section « Api » de appsettings.json.</summary>
public sealed class ApiSettings
{
    public string BaseUrl { get; set; } = "http://localhost:8000/api/v1";

    // 60 s : le réveil de l'API sur l'offre gratuite de Render prend jusqu'à une minute environ.
    public int TimeoutSeconds { get; set; } = 60;
}

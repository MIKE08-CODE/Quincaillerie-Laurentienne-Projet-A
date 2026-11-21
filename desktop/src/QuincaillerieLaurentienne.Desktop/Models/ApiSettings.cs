namespace QuincaillerieLaurentienne.Desktop.Models;

/// <summary>Section « Api » de appsettings.json.</summary>
public sealed class ApiSettings
{
    public string BaseUrl { get; set; } = "http://localhost:8000/api/v1";

    public int TimeoutSeconds { get; set; } = 10;
}

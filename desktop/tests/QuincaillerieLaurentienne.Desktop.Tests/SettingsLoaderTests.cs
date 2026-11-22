using System.IO;
using QuincaillerieLaurentienne.Desktop.Services;

namespace QuincaillerieLaurentienne.Desktop.Tests;

public sealed class SettingsLoaderTests : IDisposable
{
    private readonly string file = Path.Combine(Path.GetTempPath(), $"ql-settings-{Guid.NewGuid():N}.json");

    public void Dispose()
    {
        if (File.Exists(file))
        {
            File.Delete(file); // fichier temporaire créé par ce test uniquement
        }
    }

    [Fact]
    public void Default_timeout_covers_the_render_cold_start()
    {
        // L'API gratuite de Render se réveille en une minute environ : 10 s faisait échouer le premier appel.
        Assert.Equal(60, new QuincaillerieLaurentienne.Desktop.Models.ApiSettings().TimeoutSeconds);
        var shipped = Path.Combine(AppContext.BaseDirectory, "appsettings.json");
        if (File.Exists(shipped))
        {
            Assert.Equal(60, SettingsLoader.Load(shipped, environmentOverride: "").TimeoutSeconds);
        }
    }

    [Fact]
    public void Reads_the_api_url_from_the_configuration_file()
    {
        File.WriteAllText(file, """{"Api":{"BaseUrl":"https://api.example.com/api/v1/","TimeoutSeconds":7}}""");
        var settings = SettingsLoader.Load(file, environmentOverride: "");
        Assert.Equal("https://api.example.com/api/v1", settings.BaseUrl);
        Assert.Equal(7, settings.TimeoutSeconds);
    }

    [Fact]
    public void Environment_variable_overrides_the_file()
    {
        File.WriteAllText(file, """{"Api":{"BaseUrl":"http://localhost:8000/api/v1"}}""");
        var settings = SettingsLoader.Load(file, environmentOverride: "https://deployed.example.com/api/v1");
        Assert.Equal("https://deployed.example.com/api/v1", settings.BaseUrl);
    }

    [Fact]
    public void Missing_file_uses_the_local_default()
    {
        var settings = SettingsLoader.Load(file, environmentOverride: "");
        Assert.Equal("http://localhost:8000/api/v1", settings.BaseUrl);
    }

    [Theory]
    [InlineData("ftp://api.example.com")]
    [InlineData("pas-une-url")]
    [InlineData("/api/v1")]
    public void Invalid_url_is_rejected(string url)
    {
        Assert.Throws<InvalidOperationException>(() => SettingsLoader.Validate(url));
    }

    [Fact]
    public void Timeout_is_kept_within_bounds()
    {
        File.WriteAllText(file, """{"Api":{"BaseUrl":"http://localhost:8000/api/v1","TimeoutSeconds":0}}""");
        Assert.Equal(1, SettingsLoader.Load(file, environmentOverride: "").TimeoutSeconds);
    }
}

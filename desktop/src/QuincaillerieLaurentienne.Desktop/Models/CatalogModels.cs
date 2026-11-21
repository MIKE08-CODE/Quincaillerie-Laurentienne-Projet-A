using System.Globalization;
using System.Text.Json.Serialization;

namespace QuincaillerieLaurentienne.Desktop.Models;

/// <summary>Produit tel que renvoyé par <c>GET /api/v1/products</c> (contrat d'API §8.3).</summary>
public sealed record ProductSummary(
    [property: JsonPropertyName("id")] Guid Id,
    [property: JsonPropertyName("sku")] string Sku,
    [property: JsonPropertyName("name_fr")] string NameFr,
    [property: JsonPropertyName("name_en")] string NameEn,
    [property: JsonPropertyName("brand")] string? Brand,
    [property: JsonPropertyName("price_cents")] long PriceCents,
    [property: JsonPropertyName("main_image_url")] string? MainImageUrl,
    [property: JsonPropertyName("category_id")] Guid? CategoryId)
{
    private static readonly CultureInfo FrenchCanada = CultureInfo.GetCultureInfo("fr-CA");

    /// <summary>Prix affiché en dollars canadiens (les montants de l'API sont des cents entiers).</summary>
    public string PriceDisplay => (PriceCents / 100m).ToString("C", FrenchCanada);
}

/// <summary>Page d'une collection (contrat d'API §4.2).</summary>
public sealed record Page<T>(
    [property: JsonPropertyName("items")] IReadOnlyList<T> Items,
    [property: JsonPropertyName("page")] int Number,
    [property: JsonPropertyName("size")] int Size,
    [property: JsonPropertyName("total")] int Total);

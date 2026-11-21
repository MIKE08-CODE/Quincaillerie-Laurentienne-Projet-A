using System.Net;
using System.Net.Http;
using System.Text;
using QuincaillerieLaurentienne.Desktop.Models;
using QuincaillerieLaurentienne.Desktop.Services;

namespace QuincaillerieLaurentienne.Desktop.Tests;

/// <summary>Faux gestionnaire HTTP : enregistre les requêtes et renvoie une réponse préparée.</summary>
internal sealed class StubHandler(Func<HttpRequestMessage, HttpResponseMessage> respond) : HttpMessageHandler
{
    public List<Uri> Requests { get; } = [];

    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        Requests.Add(request.RequestUri!);
        return Task.FromResult(respond(request));
    }

    public static HttpResponseMessage Json(string body, HttpStatusCode status = HttpStatusCode.OK) =>
        new(status) { Content = new StringContent(body, Encoding.UTF8, "application/json") };
}

internal static class Samples
{
    public const string OnePage = """
        {"items":[{"id":"11111111-1111-4111-8111-111111111111","sku":"PERC-18V","name_fr":"Perceuse sans fil 18 V",
        "name_en":"Cordless drill 18 V","brand":"Laurentide Pro","price_cents":12999,"main_image_url":null,
        "category_id":null}],"page":1,"size":25,"total":1}
        """;

    public static CatalogApiClient Client(StubHandler handler, string baseUrl = "http://api.test/api/v1") =>
        new(CatalogApiClient.CreateHttpClient(new ApiSettings { BaseUrl = baseUrl, TimeoutSeconds = 5 }, handler));
}

public class ApiClientTests
{
    [Fact]
    public async Task GetProducts_calls_the_paginated_route_and_maps_snake_case_fields()
    {
        var handler = new StubHandler(_ => StubHandler.Json(Samples.OnePage));
        var page = await Samples.Client(handler).GetProductsAsync(2, 25);

        Assert.Equal("http://api.test/api/v1/products?page=2&size=25&sort=name_asc", handler.Requests.Single().ToString());
        var product = Assert.Single(page.Items);
        Assert.Equal("PERC-18V", product.Sku);
        Assert.Equal("Perceuse sans fil 18 V", product.NameFr);
        Assert.Equal(12999, product.PriceCents);
        Assert.Equal(1, page.Total);
    }

    [Fact]
    public async Task Search_encodes_the_query()
    {
        var handler = new StubHandler(_ => StubHandler.Json(Samples.OnePage));
        await Samples.Client(handler).SearchAsync("équerre & co", 1, 25);
        Assert.Equal("/api/v1/search?q=%C3%A9querre%20%26%20co&page=1&size=25", handler.Requests.Single().PathAndQuery);
    }

    [Fact]
    public async Task Api_error_keeps_the_stable_code()
    {
        var handler = new StubHandler(_ =>
            StubHandler.Json("""{"detail":{"code":"rate_limited","message":"x"}}""", HttpStatusCode.TooManyRequests));
        var error = await Assert.ThrowsAsync<ApiException>(() => Samples.Client(handler).GetProductsAsync(1, 25));
        Assert.Equal(429, error.Status);
        Assert.Equal("rate_limited", error.Code);
    }

    [Fact]
    public async Task Non_json_error_gets_a_generic_code()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.BadGateway) { Content = new StringContent("oups") });
        var error = await Assert.ThrowsAsync<ApiException>(() => Samples.Client(handler).GetProductsAsync(1, 25));
        Assert.Equal("http_502", error.Code);
    }

    [Fact]
    public async Task Unreachable_api_is_reported_as_network_error()
    {
        var handler = new StubHandler(_ => throw new HttpRequestException("refused"));
        var error = await Assert.ThrowsAsync<ApiException>(() => Samples.Client(handler).GetProductsAsync(1, 25));
        Assert.Equal("network_error", error.Code);
    }

    [Fact]
    public void Price_is_displayed_in_canadian_dollars()
    {
        var product = new ProductSummary(Guid.NewGuid(), "X", "x", "x", null, 12999, null, null);
        Assert.Equal("129,99 $", product.PriceDisplay.Replace(' ', ' ').Replace(' ', ' '));
    }
}

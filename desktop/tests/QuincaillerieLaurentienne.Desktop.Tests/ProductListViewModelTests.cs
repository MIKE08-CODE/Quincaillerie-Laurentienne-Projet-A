using System.Net;
using System.Net.Http;
using QuincaillerieLaurentienne.Desktop.Services;
using QuincaillerieLaurentienne.Desktop.ViewModels;

namespace QuincaillerieLaurentienne.Desktop.Tests;

public class ProductListViewModelTests
{
    private static ProductListViewModel ViewModel(StubHandler handler) => new(Samples.Client(handler), "http://api.test/api/v1");

    private static string Page(int page, int total, string sku = "PERC-18V") => $$"""
        {"items":[{"id":"{{Guid.NewGuid()}}","sku":"{{sku}}","name_fr":"Produit {{sku}}","name_en":"Product {{sku}}",
        "brand":null,"price_cents":1999,"main_image_url":null,"category_id":null}],"page":{{page}},"size":25,"total":{{total}}}
        """;

    [Fact]
    public async Task Load_fills_the_list_and_the_status()
    {
        var vm = ViewModel(new StubHandler(_ => StubHandler.Json(Page(1, 157))));
        await vm.LoadCommand.ExecuteAsync(null);

        Assert.Single(vm.Products);
        Assert.Equal(157, vm.Total);
        Assert.Equal(7, vm.PageCount);
        Assert.Equal("Page 1 sur 7", vm.PageText);
        Assert.Equal("157 produit(s).", vm.StatusText);
        Assert.False(vm.IsLoading);
        Assert.False(vm.HasError);
        Assert.True(vm.NextPageCommand.CanExecute(null));
        Assert.False(vm.PreviousPageCommand.CanExecute(null));
    }

    [Fact]
    public async Task Next_and_previous_pages_request_the_right_page()
    {
        var handler = new StubHandler(r => StubHandler.Json(Page(r.RequestUri!.Query.Contains("page=2") ? 2 : 1, 60)));
        var vm = ViewModel(handler);
        await vm.LoadCommand.ExecuteAsync(null);
        await vm.NextPageCommand.ExecuteAsync(null);
        Assert.Equal(2, vm.CurrentPage);
        Assert.Contains(handler.Requests, u => u.Query.Contains("page=2"));
        await vm.PreviousPageCommand.ExecuteAsync(null);
        Assert.Equal(1, vm.CurrentPage);
    }

    [Fact]
    public async Task Search_text_uses_the_search_route()
    {
        var handler = new StubHandler(_ => StubHandler.Json(Page(1, 0)));
        var vm = ViewModel(handler);
        vm.SearchText = "  equerre ";
        await vm.LoadCommand.ExecuteAsync(null);
        Assert.StartsWith("/api/v1/search?q=equerre", handler.Requests.Single().PathAndQuery);
        Assert.Equal("Aucun produit ne correspond à « equerre ».", vm.StatusText);
    }

    [Fact]
    public async Task Unreachable_api_shows_a_clear_message_and_keeps_the_app_usable()
    {
        var vm = ViewModel(new StubHandler(_ => throw new HttpRequestException("refused")));
        await vm.LoadCommand.ExecuteAsync(null);

        Assert.True(vm.HasError);
        Assert.Contains("Impossible de joindre l'API (http://api.test/api/v1)", vm.ErrorMessage);
        Assert.Equal("Échec du chargement.", vm.StatusText);
        Assert.False(vm.IsLoading);
        Assert.True(vm.LoadCommand.CanExecute(null)); // « Actualiser » reste possible
    }

    [Fact]
    public async Task Api_error_is_described_without_technical_details()
    {
        var vm = ViewModel(new StubHandler(_ =>
            StubHandler.Json("""{"detail":{"code":"internal_error","message":"trace"}}""", HttpStatusCode.InternalServerError)));
        await vm.LoadCommand.ExecuteAsync(null);
        Assert.Equal("L'API a renvoyé une erreur (500 — internal_error). Réessayez plus tard.", vm.ErrorMessage);
        Assert.DoesNotContain("trace", vm.ErrorMessage);
    }

    [Fact]
    public async Task A_new_load_clears_the_previous_error()
    {
        var fail = true;
        var vm = ViewModel(new StubHandler(_ => fail ? throw new HttpRequestException("x") : StubHandler.Json(Page(1, 1))));
        await vm.LoadCommand.ExecuteAsync(null);
        Assert.True(vm.HasError);
        fail = false;
        await vm.LoadCommand.ExecuteAsync(null);
        Assert.False(vm.HasError);
        Assert.Single(vm.Products);
    }
}

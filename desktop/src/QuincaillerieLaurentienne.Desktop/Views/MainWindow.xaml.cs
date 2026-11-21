using System.Windows;
using QuincaillerieLaurentienne.Desktop.ViewModels;

namespace QuincaillerieLaurentienne.Desktop.Views;

/// <summary>Fenêtre principale : aucune logique ici (MVVM), tout passe par le ViewModel.</summary>
public partial class MainWindow : Window
{
    public MainWindow(ProductListViewModel viewModel)
    {
        InitializeComponent();
        DataContext = viewModel;
        Loaded += async (_, _) => await viewModel.LoadPageAsync(1);
    }
}

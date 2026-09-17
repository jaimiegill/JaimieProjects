using COTWTrackerLedgerC_Edition.Config;
using Microsoft.Data.Sqlite;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace COTWTrackerLedgerC_Edition
{
    public class SpeciesDetail
    {
        public int MaxLevel { get; set; }
        public double DiamondMin { get; set; }
        public List<string> RareFurs { get; set; } = new();
        public bool GreatOne { get; set; }
    }

    public class ReserveBound
    {
        [JsonPropertyName("X_MIN")]
        public double XMin { get; set; }

        [JsonPropertyName("X_MAX")]
        public double XMax { get; set; }

        [JsonPropertyName("Z_MIN")]
        public double ZMin { get; set; }

        [JsonPropertyName("Z_MAX")]
        public double ZMax { get; set; }
    }

    public partial class MainWindow : Window
    {
        private const string path = AppConfig.RESERVE_NAMES_PATH;
        private const int ReserveID = 0;
        private const string ReserveName = "Hirschfelden Hunting Reserve";
        private Reserve reserve = new Reserve(ReserveName, ReserveID);

        // Active reserve coordinate bounds tracked at class level
        private double _currentXMin;
        private double _currentXMax;
        private double _currentYMin;
        private double _currentYMax;
        private bool _isRenderHandlerAttached = false;

        public MainWindow()
        {
            SQLitePCL.Batteries_V2.Init();
            InitializeComponent();

            LoadReserves(ReserveID);
        }

        private void LoadReserves(int defaultReserveID)
        {
            if (!File.Exists(path))
            {
                MessageBox.Show("Reserve file not found.");
                return;
            }

            string jsonString = File.ReadAllText(path);
            var reserves = JsonSerializer.Deserialize<Dictionary<string, string>>(jsonString);

            if (reserves != null)
            {
                ReserveComboBox.Items.Clear();
                foreach (var item in reserves)
                {
                    ReserveComboBox.Items.Add(new ComboBoxItem
                    {
                        Content = item.Value, // Reserve Name
                        Tag = item.Key        // Reserve ID
                    });
                }
            }

            ReserveComboBox.SelectedIndex = defaultReserveID;
            SetSpeciesListButtons(reserve);
            LoadReserveBackgroundPNG();
        }

        private void LoadReserveBackgroundPNG()
        {
            if (Directory.Exists(AppConfig.RESERVE_BACKGROUND_PNG_PATH) && File.Exists(AppConfig.RESERVE_BOUNDS_PATH))
            {
                int reserveID = reserve.GetReserveID();

                var reserveBounds = JsonSerializer.Deserialize<Dictionary<string, ReserveBound>>(File.ReadAllText(AppConfig.RESERVE_BOUNDS_PATH));

                if (reserveBounds != null && reserveBounds.TryGetValue(reserveID.ToString(), out var bounds))
                {
                    AnimalPlot.Height = 800;
                    AnimalPlot.Width = 800;

                    // Update active bounds for the newly selected reserve
                    _currentXMin = Math.Min(bounds.XMin, bounds.XMax);
                    _currentXMax = Math.Max(bounds.XMin, bounds.XMax);
                    _currentYMin = Math.Min(bounds.ZMin, bounds.ZMax);
                    _currentYMax = Math.Max(bounds.ZMin, bounds.ZMax);

                    // 1. Clear previous plot elements and rules
                    AnimalPlot.Plot.Clear();
                    AnimalPlot.Plot.Axes.Rules.Clear();

                    // 2. Set minimum zoom span
                    double minZoomSpanX = 2000;
                    double minZoomSpanY = 2000;

                    AnimalPlot.Plot.Axes.Rules.Add(new ScottPlot.AxisRules.MinimumSpan(
                        AnimalPlot.Plot.Axes.Bottom,
                        AnimalPlot.Plot.Axes.Left,
                        minZoomSpanX,
                        minZoomSpanY
                    ));

                    // 3. Load background map image
                    string pngPath = Path.Combine(AppConfig.RESERVE_BACKGROUND_PNG_PATH, $"reserve_{reserveID}_full.png");
                    if (File.Exists(pngPath))
                    {
                        byte[] imageBytes = File.ReadAllBytes(pngPath);
                        var mapBitmap = new ScottPlot.Image(imageBytes);

                        var imageBounds = new ScottPlot.CoordinateRect(_currentXMin, _currentXMax, _currentYMin, _currentYMax);
                        var imagePlottable = new ScottPlot.Plottables.ImageRect()
                        {
                            Image = mapBitmap,
                            Rect = imageBounds
                        };

                        AnimalPlot.Plot.Add.Plottable(imagePlottable);
                    }

                    // 4. Set initial view limits
                    AnimalPlot.Plot.Axes.SetLimits(_currentXMin, _currentXMax, _currentYMin, _currentYMax);

                    // 5. Hide grid lines and empty axis tick generators to avoid shifting frame artifacts
                    AnimalPlot.Plot.HideGrid();
                    AnimalPlot.Plot.Axes.Bottom.TickGenerator = new ScottPlot.TickGenerators.EmptyTickGenerator();
                    AnimalPlot.Plot.Axes.Left.TickGenerator = new ScottPlot.TickGenerators.EmptyTickGenerator();

                    // 6. Ensure the render boundary clamp handler is attached exactly once
                    if (!_isRenderHandlerAttached)
                    {
                        AnimalPlot.Plot.RenderManager.RenderStarting += OnRenderStarting;
                        _isRenderHandlerAttached = true;
                    }

                    AnimalPlot.Refresh();
                }
            }
        }

        // Class-level handler that dynamically clamps view limits to the current reserve
        private void OnRenderStarting(object? sender, ScottPlot.RenderPack e)
        {
            var limits = AnimalPlot.Plot.Axes.GetLimits();

            double currentWidth = limits.Rect.Width;
            double currentHeight = limits.Rect.Height;

            double maxAllowedWidth = _currentXMax - _currentXMin;
            double maxAllowedHeight = _currentYMax - _currentYMin;

            // Clamp zooming out past full map dimensions
            if (currentWidth > maxAllowedWidth || currentHeight > maxAllowedHeight)
            {
                AnimalPlot.Plot.Axes.SetLimits(_currentXMin, _currentXMax, _currentYMin, _currentYMax);
                return;
            }

            double newXMin = limits.Left;
            double newXMax = limits.Right;
            double newYMin = limits.Bottom;
            double newYMax = limits.Top;

            bool clamped = false;

            // Clamp X position while preserving exact width span
            if (newXMin < _currentXMin)
            {
                newXMin = _currentXMin;
                newXMax = _currentXMin + currentWidth;
                clamped = true;
            }
            else if (newXMax > _currentXMax)
            {
                newXMax = _currentXMax;
                newXMin = _currentXMax - currentWidth;
                clamped = true;
            }

            // Clamp Y position while preserving exact height span
            if (newYMin < _currentYMin)
            {
                newYMin = _currentYMin;
                newYMax = _currentYMin + currentHeight;
                clamped = true;
            }
            else if (newYMax > _currentYMax)
            {
                newYMax = _currentYMax;
                newYMin = _currentYMax - currentHeight;
                clamped = true;
            }

            // Apply updated limits if any edge was breached
            if (clamped)
            {
                AnimalPlot.Plot.Axes.SetLimits(newXMin, newXMax, newYMin, newYMax);
            }
        }

        private void SetSpeciesListButtons(Reserve reserve)
        {
            int reserveID = reserve.GetReserveID();

            if (File.Exists(AppConfig.SPECIES_METADATA_PATH))
            {
                string jsonString = File.ReadAllText(AppConfig.SPECIES_METADATA_PATH);

                var speciesDict = JsonSerializer.Deserialize<Dictionary<string, Dictionary<string, SpeciesDetail>>>(jsonString);

                if (speciesDict != null && speciesDict.TryGetValue(reserveID.ToString(), out var species))
                {
                    SpeciesListBox.ItemsSource = species.Keys.ToList();
                }
                else
                {
                    SpeciesListBox.ItemsSource = null;
                }
            }
            else
            {
                SpeciesListBox.ItemsSource = null;
            }
        }

        private void ReserveComboBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (ReserveComboBox.SelectedItem is ComboBoxItem selectedItem)
            {
                string reserveName = selectedItem.Content.ToString() ?? string.Empty;
                if (int.TryParse(selectedItem.Tag?.ToString(), out int reserveId))
                {
                    reserve.SetReserveName(reserveName);
                    reserve.SetReserveID(reserveId);
                    SetSpeciesListButtons(reserve);

                    LoadReserveBackgroundPNG();
                }
            }
        }
    }
}
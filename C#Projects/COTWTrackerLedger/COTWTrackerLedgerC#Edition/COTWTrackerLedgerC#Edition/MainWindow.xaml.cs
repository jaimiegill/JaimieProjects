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
using COTWTrackerLedgerC_Edition.SpeciesMetaData;
using COTWTrackerLedgerC_Edition.ReserveBounds;
using COTWTrackerLedgerC_Edition.ReserveData;
using CsvHelper;
using CsvHelper.Configuration;
using System.Globalization;
using OpenTK.Graphics.ES20;
using ScottPlot;
using SkiaSharp;
using Svg.Skia;
using Microsoft.Win32;
using ShimSkiaSharp.Editing;


namespace COTWTrackerLedgerC_Edition
{


    public partial class MainWindow : Window
    {
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
            InitializeComponent();

            LoadReserves(ReserveID);
        }

        private void LoadReserves(int defaultReserveID)
        {
            if (!File.Exists(AppConfig.RESERVE_NAMES_PATH))
            {
                MessageBox.Show("Reserve file not found.");
                return;
            }

            string jsonString = File.ReadAllText(AppConfig.RESERVE_NAMES_PATH);
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

                    double left = bounds.XMin;
                    double right = bounds.XMax;
                    double bottom = bounds.ZMin;
                    double top = bounds.ZMax;


                    // Update active bounds for the newly selected reserve
                    _currentXMin = Math.Min(left, right);
                    _currentXMax = Math.Max(left, right);
                    _currentYMin = Math.Min(bottom, top);
                    _currentYMax = Math.Max(bottom, top);

                    // 1. Clear previous plot elements and rules
                    AnimalPlot.Plot.Clear();
                    AnimalPlot.Plot.Axes.Rules.Clear();

                    // 2. Lock 1:1 aspect ratio to avoid image stretching when panning/zooming
                    AnimalPlot.Plot.Axes.Rules.Add(new ScottPlot.AxisRules.SquareZoomOut(
                    AnimalPlot.Plot.Axes.Bottom,
                    AnimalPlot.Plot.Axes.Left
                    ));

                    // 3. Set minimum zoom span
                    double minZoomSpanX = (reserveID == 18) ? 500 : 2000;
                    double minZoomSpanY = (reserveID == 18) ? 500 : 2000;

                    AnimalPlot.Plot.Axes.Rules.Add(new ScottPlot.AxisRules.MinimumSpan(
                        AnimalPlot.Plot.Axes.Bottom,
                        AnimalPlot.Plot.Axes.Left,
                        minZoomSpanX,
                        minZoomSpanY
                    ));

                    // 4. Load background map image
                    string pngPath = Path.Combine(AppConfig.RESERVE_BACKGROUND_PNG_PATH, $"reserve_{reserveID}_full.png");
                    if (File.Exists(pngPath))
                    {
                    byte[] imageBytes = File.ReadAllBytes(pngPath);
                        // 2. Map ImageRect with precise Left, Right, Bottom, Top bounds
                        var mapBitmap = new ScottPlot.Image(imageBytes);

                        // ScottPlot CoordinateRect constructor: (double left, double right, double bottom, double top)
                        var imageBounds = new ScottPlot.CoordinateRect(left, right, bottom, top);

                        var imagePlottable = new ScottPlot.Plottables.ImageRect()
                        {
                            Image = mapBitmap,
                            Rect = imageBounds
                        };

                        AnimalPlot.Plot.Add.Plottable(imagePlottable);
                    }

                    // 5. Set initial view limits
                    AnimalPlot.Plot.Axes.SetLimits(_currentXMin, _currentXMax, _currentYMin, _currentYMax);

                    // 6. Hide grid lines and empty axis tick generators
                    AnimalPlot.Plot.HideGrid();
                    AnimalPlot.Plot.Axes.Bottom.TickGenerator = new ScottPlot.TickGenerators.EmptyTickGenerator();
                    AnimalPlot.Plot.Axes.Left.TickGenerator = new ScottPlot.TickGenerators.EmptyTickGenerator();

                    // 7. Ensure render boundary clamp handler is attached exactly once
                    if (!_isRenderHandlerAttached)
                    {
                        AnimalPlot.Plot.RenderManager.RenderStarting += OnRenderStarting;
                        _isRenderHandlerAttached = true;
                    }

                    AnimalPlot.Refresh();

                    PlotNeedZoneCoordinates();

                }
            }
       }

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

                var speciesDict = JsonSerializer.Deserialize<Dictionary<string, Dictionary<string, SpeciesMetaData.SpeciesMetaData>>>(jsonString);

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
        private ScottPlot.Image RenderSvgToScottPlotImage(string svgPath, int width = 32, int height = 32)
        {
            var svg = new Svg.Skia.SKSvg();
            svg.Load(svgPath);


            SKBitmap skBitmap = new SKBitmap(width, height);

            using (var canvas = new SKCanvas(skBitmap)) 
            {
                canvas.Clear(SKColors.Transparent);
                canvas.DrawPicture(svg.Picture);
            }

            return new ScottPlot.Image(skBitmap.Encode(SKEncodedImageFormat.Png, 100).ToArray());

        }
        private void PlotNeedZoneCoordinates()
        {
            ScottPlot.Image? drinkIcon = null;
            ScottPlot.Image? feedIcon = null;
            ScottPlot.Image? restIcon = null;

            if (File.Exists(AppConfig.DRINK_ZONE_SVG_PATH) && File.Exists(AppConfig.FEED_ZONE_SVG_PATH) && File.Exists(AppConfig.REST_ZONE_SVG_PATH))
            {
                drinkIcon = RenderSvgToScottPlotImage(AppConfig.DRINK_ZONE_SVG_PATH, 24, 24);
                feedIcon = RenderSvgToScottPlotImage(AppConfig.FEED_ZONE_SVG_PATH, 24, 24);
                restIcon = RenderSvgToScottPlotImage(AppConfig.REST_ZONE_SVG_PATH, 24, 24);
            }
            else
            {
                MessageBox.Show("One or more Need Zone SVG files are missing.");
                return;
            }

            NeedZoneRecord[] needZones = NeedZoneRecord.LoadNeedZoneData(reserve.GetReserveID()).ToArray();
            double yCenterBound = _currentYMin + _currentYMax;

            var feedX = new List<double>(); var feedY = new List<double>();
            var drinkX = new List<double>(); var drinkY = new List<double>();
            var restX = new List<double>(); var restY = new List<double>();

            foreach (var zone in needZones)
            {
                double x = zone.PositionX;
                double y = yCenterBound - zone.PositionZ;

                switch (zone.NeedType)
                {
                    case 1: feedX.Add(x); feedY.Add(y); break;
                    case 2: drinkX.Add(x); drinkY.Add(y); break;
                    case 3: restX.Add(x); restY.Add(y); break;
                }
            }

            AddIconMarkerGroup(feedX, feedY, feedIcon);
            AddIconMarkerGroup(drinkX, drinkY, drinkIcon);
            AddIconMarkerGroup(restX, restY, restIcon);

            AnimalPlot.Refresh();
        }

        private void AddIconMarkerGroup(List<double> xs, List<double> ys, ScottPlot.Image? icon)
        {
            if (xs.Count == 0 || icon == null)
                return;

            for (int i = 0; i < xs.Count; i++)
            {
                AnimalPlot.Plot.Add.ImageMarker(new ScottPlot.Coordinates(xs[i], ys[i]), icon);
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
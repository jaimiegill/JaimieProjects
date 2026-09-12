using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Navigation;
using System.Windows.Shapes;
using System;
using System.IO;
using System.Collections.Generic;
using System.Text.Json;

namespace COTWTrackerLedgerC_Edition
{
    /// <summary>
    /// Interaction logic for MainWindow.xaml
    /// </summary>
    public partial class MainWindow : Window
    {
        private const String path = @"C:\Users\gills\JaimieProjects\C#Projects\COTWTrackerLedger\COTWTrackerLedgerC#Edition\COTWTrackerLedgerC#Edition\ReserveData\ReserveNames.db";
        private const int ReserveID = 0; // Initialize ReserveID to 0
        private const String ReserveName = "Hirschfelden Hunting Reserve"; // Initialize ReserveName to "Hirschfelden Hunting Reserve"
        private Reserve reserve = new Reserve(ReserveName, ReserveID); // Create a Reserve object with the initial values

        public MainWindow()
        {

            InitializeComponent();
            LoadReserves(ReserveID);
        }

        private void LoadReserves(int ReserveID)
        {
            

            if (File.Exists(path))
            {
                string jsonString = File.ReadAllText(path);
                var reserves = JsonSerializer.Deserialize<Dictionary<string, string>>(jsonString);

                if (reserves != null)
                {
                    foreach (var reserve in reserves)
                    {
                        // Key is the ID (e.g., "0"), Value is the name (e.g., "Hirschfelden Hunting Reserve")[cite: 1]
                        ReserveComboBox.Items.Add(new ComboBoxItem
                        {
                            Content = reserve.Value,
                            Tag = reserve.Key
                        });
                    }
                }
                ReserveComboBox.SetValue(ComboBox.SelectedIndexProperty, ReserveID); // Set the selected index to ReserveID
            }
            else
            {
                MessageBox.Show("Database file not found.");
            }
        }
        private int ChangeReserveID(string reserveName)
        {
            if (File.Exists(path))
            {
                string jsonString = File.ReadAllText(path);
                var reserves = JsonSerializer.Deserialize<Dictionary<string, string>>(jsonString);
                if (reserves != null)
                {
                    foreach (var reserve in reserves)
                    {
                        if (reserve.Value == reserveName)
                        {
                            return int.Parse(reserve.Key); // Return the ReserveID corresponding to the ReserveName
                        }
                    }
                }
            }
            else
            {
                MessageBox.Show("Database file not found.");
            }
            return -1; // Return -1 if the reserve name is not found
        }

        private void ReserveComboBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            reserve.SetReserveName(((ComboBoxItem)ReserveComboBox.SelectedItem).Content.ToString());
            reserve.SetReserveID(ChangeReserveID(reserve.GetReserveName()));


        }
    }
}
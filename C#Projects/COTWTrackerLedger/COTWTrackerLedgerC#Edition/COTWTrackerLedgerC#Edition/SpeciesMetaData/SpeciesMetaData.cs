using System;
using System.Collections.Generic;
using System.Text;

namespace COTWTrackerLedgerC_Edition.SpeciesMetaData
{
    public class SpeciesMetaData
    {
        public int MaxLevel { get; set; }
        public double DiamondMin { get; set; }
        public List<string> RareFurs { get; set; } = new();
        public bool GreatOne { get; set; }
    }
}

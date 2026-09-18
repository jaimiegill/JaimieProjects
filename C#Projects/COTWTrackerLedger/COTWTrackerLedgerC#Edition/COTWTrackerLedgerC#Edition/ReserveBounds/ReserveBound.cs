using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Json.Serialization;

namespace COTWTrackerLedgerC_Edition.ReserveBounds
{
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
}

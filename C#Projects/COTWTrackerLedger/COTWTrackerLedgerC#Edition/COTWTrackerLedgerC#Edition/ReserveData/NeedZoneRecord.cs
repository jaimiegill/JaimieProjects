using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using CsvHelper.Configuration.Attributes;
using COTWTrackerLedgerC_Edition.Config;
using CsvHelper.Configuration;
using System.Globalization;
using CsvHelper;

namespace COTWTrackerLedgerC_Edition.ReserveData
{
    public class NeedZoneRecord
    {
        [Name("ReserveId")]
        public int ReserveId { get; set; }

        [Name("Position_X")]
        public double PositionX { get; set; }

        [Name("Position_Y")]
        public double PositionY { get; set; }

        [Name("Position_Z")]
        public double PositionZ { get; set; }

        [Name("NeedZoneId")]
        public long NeedZoneId { get; set; }

        [Name("NeedType")]
        public int NeedType { get; set; }

        [Name("MapIconId")]
        public ulong MapIconId { get; set; }

        [Name("NeedZoneStartTimeHours")]
        public double StartTimeHours { get; set; }

        [Name("NeedZoneEndTimeHours")]
        public double EndTimeHours { get; set; }

        [Name("AnimalTypeLocalizationName")]
        public ulong AnimalTypeLocalizationName { get; set; }

        [Name("NeedZoneScheduleIndex")]
        public int ScheduleIndex { get; set; }

        public static List<NeedZoneRecord> LoadNeedZoneData(int reserveID)
        {
            if (!File.Exists(AppConfig.NEED_ZONE_DATA_PATH))
            {
                Console.WriteLine("Need zone data file not found.");
                return new List<NeedZoneRecord>();
            }
            var config = new CsvConfiguration(CultureInfo.InvariantCulture)
            {
                HasHeaderRecord = true,
                Delimiter = ","
            };
            using (var reader = new StreamReader(AppConfig.NEED_ZONE_DATA_PATH))
            using (var csv = new CsvReader(reader, config))
            {
                var records = csv.GetRecords<NeedZoneRecord>().Where(r => r.ReserveId == reserveID).ToList();
                return records;
            }
        }
    }
}

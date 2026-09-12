using System;
using System.Collections.Generic;
using System.Text;

namespace COTWTrackerLedgerC_Edition
{
    internal class Reserve
    {
        String ReserveName;
        int ReserveID;

        public Reserve(String ReserveName, int ReserveID)
        {
            this.ReserveName = ReserveName;
            this.ReserveID = ReserveID;
        }

        public String GetReserveName()
        {
            return ReserveName;
        }

        public int GetReserveID()
        {
            return ReserveID;
        }
        public void SetReserveName(String ReserveName)
        {
            this.ReserveName = ReserveName;
        }
        public void SetReserveID(int ReserveID)
        {
            this.ReserveID = ReserveID;
        }
    }
}

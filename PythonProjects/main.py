from openbb import obb
import matplotlib.pyplot as plt
import pandas as pd
import os
import smtplib
from email.message import EmailMessage

def main():
    # 1. Setup Credentials
    obb.user.credentials.fmp_api_key = "GMIVJpdUOpXcYerIvTNzMUhvrFjieoOe"
    
    # 2. Dictionary Structure for your companies
    # You can easily add or remove companies here
    companies = {
        "AAPL": "Apple Inc.",
        "NVDA": "NVIDIA Corporation",
        "MSFT": "Microsoft",
        "GOOGL": "Alphabet (Google)"
    }
    
    # 3. Create a figure with multiple subplots

    # nrows=len(companies) creates one row for each company
    fig, axes = plt.subplots(nrows=len(companies), ncols=1, figsize=(10, 4 * len(companies)))
    
    # If only one company is provided, axes won't be a list, so we force it to be one
    if len(companies) == 1:
        axes = [axes]

    # 4. Loop through the dictionary items
    for i, (ticker, name) in enumerate(companies.items()):
        try:
            print(f"\n--- Checking {ticker} ---")
            res = obb.equity.price.historical(ticker, provider="fmp")
            df = res.to_df()
            
            print(f"1. Data fetched. Columns found: {df.columns.tolist()}")
            
            # FORCE column names to lowercase just in case
            df.columns = [x.lower() for x in df.columns]
            
            if 'close' not in df.columns:
                print(f"❌ ERROR: 'close' column missing for {ticker}!")
                continue # Skip to next ticker

            # 2. Try the calculation separately
            print("2. Calculating SMA...")
            sma_20 = df['close'].rolling(window=20, min_periods=1).mean()
            sma_100 = df['close'].rolling(window=100, min_periods=1).mean()
            
            # 3. Try the plot
            print("3. Attempting to plot...")
            axes[i].set_title(f"{name} ({ticker}) - Historical Performance", fontsize=12, fontweight='bold')
            axes[i].plot(df.index, df['close'], color='tab:blue', label='Price')
            axes[i].plot(df.index, sma_20, color='tab:red', linewidth=2, label='20d SMA', zorder=5)
            axes[i].plot(df.index, sma_100, color='tab:green', linewidth=2, label='20d SMA', zorder=5)
            
            axes[i].legend()
            print("4. Plot successful!")

        except Exception as e:
            print(f"💥 CRASHED at {ticker}. Error: {e}")

    # 5. Final Layout Adjustments
    plt.tight_layout()

    # Save and Show
    plt.savefig("individual_company_reports.png")
    print("✅ Success! View your charts in 'individual_company_reports.png'")
    #plt.show()
    plt.savefig("stock_report.png")



def send_stock_report(recipient_arr):
    # 1. Setup Sender Details
    receiver_email = "jaimiesgill@gmail.com"
    app_password = "vyid wfjh iycl fzel"  # NOT your regular password!
    
    # 2. Create the Email object
    msg = EmailMessage()
    msg['Subject'] = 'Daily Stock Market Report'
    msg['From'] = "StockScrpt@gmail.com"
    msg['To'] = ", ".join(recipient_arr)
    msg.set_content("Attached are the latest stock performance graphs with 20-day Moving Averages.")

    # 3. Read and Attach the image
    with open('stock_report.png', 'rb') as f:
        file_data = f.read()
        msg.add_attachment(file_data, maintype='image', subtype='png', filename='stock_report.png')

    # 4. Connect to Gmail and Send
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(receiver_email, app_password)
            smtp.send_message(msg)
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

# Call the function after your main loop
# send_stock_report("friend@example.com")

if __name__ == "__main__":
    main()
    recipient_arr = ["jaimiesgill@gmail.com", "gillsuki@gmail.com"]
    send_stock_report(recipient_arr)
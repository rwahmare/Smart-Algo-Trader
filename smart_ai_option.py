import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import warnings
import os
from dotenv import load_dotenv

warnings.filterwarnings('ignore')

# ==========================================
# 🛑 .env फाईलमधून सिक्रेट टेलिग्राम डिटेल्स घेणे
# ==========================================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram_message(message):
    try:
        if BOT_TOKEN and CHAT_ID:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
            requests.get(url)
        else:
            print("⚠️ Telegram ID सापडले नाहीत! कृपया .env फाईल बरोबर बनवली आहे का ते तपासा.")
    except Exception as e:
        print("Telegram मेसेज पाठवण्यात अडचण:", e)

# ==========================================
# 1. इंडेक्सची यादी (Nifty, BankNifty, Sensex, Midcap)
# ==========================================
indices = {
    "^NSEI": "NIFTY 50",
    "^NSEBANK": "BANK NIFTY",
    "^BSESN": "SENSEX",
    "^CRSMID": "NIFTY MIDCAP 100"
}

print("🚀 Options Scanner + Telegram Bot चालू झाला आहे!")
print("सर्व ४ इंडेक्स स्कॅन होत आहेत, कृपया ५-१० सेकंद थांबा...\n")

trade_signals = []

# ==========================================
# 2. इंडेक्स स्कॅन करणे (5 मिनिटांचा चार्ट)
# ==========================================
for ticker, name in indices.items():
    try:
        df = yf.download(ticker, period="5d", interval="5m", progress=False)
        if df.empty: continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # इंडिकेटर्स
        df.ta.ema(length=50, append=True)
        df.ta.supertrend(length=14, multiplier=2.0, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.adx(length=14, append=True)
        df['Res_Level'] = df['High'].rolling(window=10).max().shift(1)
        df['Sup_Level'] = df['Low'].rolling(window=10).min().shift(1)
        df.dropna(inplace=True)
        if df.empty: continue

        # अटी (Conditions)
        adx_thresh = 20
        isSideways = df['ADX_14'] < adx_thresh
        
        # CE आणि PE Logic
        emaBull = df['Close'] > df['EMA_50']
        rsiBullish = df['RSI_14'] > 50
        stBull = df['SUPERTd_14_2.0'] == 1
        stChangeToBull = (df['SUPERTd_14_2.0'] == 1) & (df['SUPERTd_14_2.0'].shift(1) == -1)
        bullBreakout = (df['Close'] > df['Res_Level']) & (df['Close'].shift(1) <= df['Res_Level'].shift(1))

        emaBear = df['Close'] < df['EMA_50']
        rsiBearish = df['RSI_14'] < 50
        stBear = df['SUPERTd_14_2.0'] == -1
        stChangeToBear = (df['SUPERTd_14_2.0'] == -1) & (df['SUPERTd_14_2.0'].shift(1) == 1)
        bearBreakout = (df['Close'] < df['Sup_Level']) & (df['Close'].shift(1) >= df['Sup_Level'].shift(1))

        df['BUY_CE'] = stBull & emaBull & rsiBullish & (~isSideways) & (stChangeToBull | bullBreakout)
        df['BUY_PE'] = stBear & emaBear & rsiBearish & (~isSideways) & (stChangeToBear | bearBreakout)

        # शेवटची ५ मिनिटांची कॅन्डल तपासणे
        last_candle = df.iloc[-1]
        last_time = df.index[-1].strftime('%H:%M')
        current_price = last_candle['Close']

        if last_candle['BUY_CE']:
            msg = f"🟢 BUY CALL (CE) Alert!\n\nइंडेक्स: {name}\nप्राईस: ₹{current_price:.2f}\nवेळ: {last_time}\n\n(Smart AI Scanner 🤖)"
            trade_signals.append(msg)
            print(f"🔥 CALL Signal Found: {name}")
            send_telegram_message(msg)  # टेलिग्रामला मेसेज जाईल
            
        elif last_candle['BUY_PE']:
            msg = f"🔴 BUY PUT (PE) Alert!\n\nइंडेक्स: {name}\nप्राईस: ₹{current_price:.2f}\nवेळ: {last_time}\n\n(Smart AI Scanner 🤖)"
            trade_signals.append(msg)
            print(f"🔥 PUT Signal Found: {name}")
            send_telegram_message(msg)  # टेलिग्रामला मेसेज जाईल
            
    except Exception as e:
        pass

# ==========================================
# 3. फायनल रिझल्ट (Output)
# ==========================================
print("\n=========================================================================")
print("🎯 5-Min Options Trading Signals:")
print("=========================================================================")

if len(trade_signals) == 0:
    print("सध्या Nifty, BankNifty, Sensex आणि Midcap मध्ये कोणताही मजबूत CE किंवा PE सिग्नल नाही.")
    print("मार्केट साईडवेज असू शकते, कृपया पुढील 5 मिनिटांच्या कॅन्डलची वाट बघा.")
else:
    for signal in trade_signals:
        print(signal)
    print("\n✅ सर्व सिग्नल्स तुमच्या टेलिग्रामवर यशस्वीरीत्या पाठवले आहेत!")
print("=========================================================================")
import requests
import pandas as pd
import ta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from transformers import pipeline

TOKEN = "7520322508:AAHFx4G7S25rcL0uiWtP2SKvPOL1S3jAUi0"

# جلب بيانات العملة من CoinGecko (7 أيام)
def fetch_market_data(symbol: str):
    url = f"https://api.coingecko.com/api/v3/coins/{symbol}/market_chart?vs_currency=usd&days=7"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    prices = pd.DataFrame(r.json()["prices"], columns=["time", "price"])
    prices["time"] = pd.to_datetime(prices["time"], unit="ms")
    prices.set_index("time", inplace=True)
    return prices

# تحليل فني
def analyze_tech(data: pd.DataFrame):
    df = data.copy()
    df["rsi"] = ta.momentum.RSIIndicator(df["price"], window=14).rsi()
    df["macd"] = ta.trend.MACD(df["price"]).macd_diff()
    latest = df.iloc[-1]
    return latest["price"], latest["rsi"], latest["macd"]

# توقع ذكي باستخدام نموذج GPT محلي
generator = pipeline("text-generation", model="tiiuae/falcon-7b-instruct", device=-1)

def ai_prediction(symbol: str, price: float, rsi: float, macd: float):
    prompt = (
        f"عملة {symbol.upper()}, السعر الحالي ${price:.2f}, RSI={rsi:.1f}, MACD={macd:.2f}. "
        f"توقع حركة السعر خلال ٢٤ ساعة القادمة مع تفسير منطقي."
    )
    result = generator(prompt, max_length=100, do_sample=True, temperature=0.7)
    return result[0]["generated_text"]

# دالة الرد على /تحليل
async def handle_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("📌 الرجاء كتابة اسم العملة بعد الأمر. مثال:\n/تحليل bitcoin")
        return
    symbol = context.args[0].lower()
    data = fetch_market_data(symbol)
    if data is None:
        await update.message.reply_text(f"❌ تعذر جلب بيانات '{symbol}'. تأكد من الاسم.")
        return
    price, rsi, macd = analyze_tech(data)
    ai_resp = ai_prediction(symbol, price, rsi, macd)
    msg = (
        f"💰 سعر {symbol.upper()} الحالي: ${price:.2f}\n"
        f"📉 RSI={rsi:.1f}, MACD diff={macd:.2f}\n\n"
        f"{ai_resp}"
    )
    await update.message.reply_text(msg)

# إعداد البوت وتشغيله
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("تحليل", handle_analysis))

import asyncio

if __name__ == "__main__":
    asyncio.run(app.run_polling())

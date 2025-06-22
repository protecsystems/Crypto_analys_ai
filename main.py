import requests
import pandas as pd
import ta
import openai
import os
import asyncio

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# مفاتيح من البيئة
TOKEN = os.environ.get("TOKEN")
openai.api_key = os.environ.get("OPENAI_API_KEY")

app = ApplicationBuilder().token(TOKEN).build()

# 1. جلب البيانات من CoinGecko
def fetch_market_data(symbol: str):
    url = f"https://api.coingecko.com/api/v3/coins/{symbol}/market_chart?vs_currency=usd&days=7"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    prices = pd.DataFrame(r.json()["prices"], columns=["time", "price"])
    prices["time"] = pd.to_datetime(prices["time"], unit="ms")
    prices.set_index("time", inplace=True)
    return prices

# 2. تحليل RSI و MACD
def analyze_tech(data: pd.DataFrame):
    df = data.copy()
    df["rsi"] = ta.momentum.RSIIndicator(df["price"], window=14).rsi()
    df["macd"] = ta.trend.MACD(df["price"]).macd_diff()
    latest = df.iloc[-1]
    return latest["price"], latest["rsi"], latest["macd"]

# 3. توقع الذكاء الاصطناعي
def generate_ai_prediction(symbol: str, price: float, rsi: float, macd: float):
    prompt = (
        f"تحليل عملة {symbol.upper()}:\n"
        f"السعر الحالي: {price:.2f} USD\n"
        f"RSI: {rsi:.1f}, MACD diff: {macd:.2f}\n"
        "بناءً على هذه البيانات، ما هو توقعك لحركة السعر خلال 24 ساعة القادمة؟"
    )
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "أنت محلل مالي خبير في سوق العملات الرقمية."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# 4. أمر /analyze
async def handle_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("📌 الرجاء كتابة اسم العملة بعد الأمر. مثال:\n/analyze bitcoin")
        return
    symbol = context.args[0].lower()
    data = fetch_market_data(symbol)
    if data is None:
        await update.message.reply_text(f"❌ تعذر جلب بيانات '{symbol}'. تأكد من الاسم.")
        return
    price, rsi, macd = analyze_tech(data)
    analysis_text = (
        f"💰 السعر الحالي: ${price:.2f}\n"
        f"📉 RSI: {rsi:.1f}\n"
        f"📊 MACD diff: {macd:.2f}\n\n"
        f"🤖 الذكاء الاصطناعي يتوقع:\n"
    )
    try:
        prediction = generate_ai_prediction(symbol, price, rsi, macd)
    except Exception as e:
        prediction = "❌ حدث خطأ أثناء الاتصال بخدمة الذكاء الاصطناعي."
    await update.message.reply_text(analysis_text + prediction)

# 5. إضافة الأمر
app.add_handler(CommandHandler("analyze", handle_analysis))

# 6. تشغيل البوت
if __name__ == "__main__":
    asyncio.run(app.run_polling())

# ✈️ Havo KT Quiz Bot

## 📋 Loyiha tarkibi
```
quiz_bot/
├── bot.py            ← Asosiy bot kodi
├── questions.json    ← 200 ta savol va javoblar
├── requirements.txt  ← Kerakli kutubxonalar
└── README.md         ← Shu fayl
```

---

## 🚀 O'rnatish va ishga tushurish

### 1-qadam: Python tekshirish
```bash
python --version   # Python 3.9+ bo'lishi kerak
```

### 2-qadam: Kutubxona o'rnatish
```bash
pip install -r requirements.txt
```

### 3-qadam: Bot token olish
1. Telegramda **@BotFather** ga boring
2. `/newbot` yozing
3. Bot nomi bering (masalan: `HAVO KT Quiz`)
4. Username bering (masalan: `havokt_quiz_bot`)
5. Token oling: `7123456789:AAHxxxx...`

### 4-qadam: Tokenni qo'shish
`bot.py` faylini oching, 10-qatorni o'zgartiring:
```python
BOT_TOKEN = "BU_YERGA_BOT_TOKENINGIZNI_YOZING"
# ↓ O'zgartiring:
BOT_TOKEN = "7123456789:AAHxxxxxxxxxxxx"
```

### 5-qadam: Botni ishga tushurish
```bash
cd quiz_bot
python bot.py
```

---

## 🎮 Bot ishlash tartibi

```
Foydalanuvchi /start bosadi
        ↓
10 ta bo'lim tugmalari chiqadi
(1-20, 21-40, 41-60 ... 181-200)
        ↓
Foydalanuvchi bo'lim tanlaydi
        ↓
20 ta savol random aralashtiriladi
        ↓
Har savol: 3 ta variant (A, B, C)
+ savol darajasi ko'rsatiladi (1🟢 2🟡 3🔴)
        ↓
To'g'ri javob → ball qo'shiladi
        ↓
Oxirida: to'liq statistika + baho
```

---

## 📊 Ball tizimi
| Daraja | Emoji | Ball |
|--------|-------|------|
| Oson   | 🟢    | 1 ball |
| O'rta  | 🟡    | 2 ball |
| Qiyin  | 🔴    | 3 ball |

**Maksimal ball:** 20 ta savoldagi barcha balllar yig'indisi

---

## 🌐 Server (Render.com) da joylashtirish

1. GitHub da yangi repo yarating
2. Bu 3 faylni yukang (bot.py, questions.json, requirements.txt)
3. render.com ga kiring → New → Web Service
4. GitHub reponi ulang
5. **Start command:** `python bot.py`
6. Environment variable qo'shing: `BOT_TOKEN = sizning_tokeningiz`
7. Deploy qiling!

---

## ⚠️ Muhim eslatmalar
- Bot ishlashi uchun internet kerak
- Render.com free tier da bot 15 daqiqa faoliyatsiz bo'lsa uxlab qoladi
- Uzluksiz ishlashi uchun VPS yoki Railway.app tavsiya etiladi

"""
✈️ Havo Kuchlar Tayyorlash — Quiz Bot
Muallif: refactored version
Tavsif: Professional, xavfsiz, ko'p foydalanuvchili Telegram quiz bot
"""

import os
import json
import random
import logging
import asyncio
import warnings
from telegram.warnings import PTBUserWarning
warnings.filterwarnings("ignore", category=PTBUserWarning)
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    PollAnswerHandler,
    PollHandler,
    MessageHandler,
    filters,
)

# ===================== LOGGING =====================
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ===================== SOZLAMALAR =====================
load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8952375153:AAG7ticCoVrQ4uZ2B_tHUPK_l41zCT3XREs")
if not BOT_TOKEN:
    raise EnvironmentError(
        "❌ BOT_TOKEN topilmadi! .env faylida BOT_TOKEN=... ni to'ldiring."
    )

QUESTIONS_PER_BLOCK = 20
TOTAL_BLOCKS = 10
POLL_OPEN_SECONDS = 40
MAX_SKIPPED_STREAK = 3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUESTIONS_PATH = os.path.join(BASE_DIR, "questions.json")

# ===================== SAVOLLARNI YUKLASH =====================
try:
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        ALL_QUESTIONS: list[dict] = json.load(f)
    logger.info(f"✅ {len(ALL_QUESTIONS)} ta savol yuklandi.")
except FileNotFoundError:
    raise FileNotFoundError(f"❌ questions.json topilmadi: {QUESTIONS_PATH}")
except json.JSONDecodeError as e:
    raise ValueError(f"❌ questions.json noto'g'ri format: {e}")

# 10 ta blok hosil qilish
BLOCKS: dict[int, list[dict]] = {
    i + 1: ALL_QUESTIONS[i * QUESTIONS_PER_BLOCK: (i + 1) * QUESTIONS_PER_BLOCK]
    for i in range(TOTAL_BLOCKS)
}

# ===================== HOLATLAR =====================
SELECTING_BLOCK = 1
IN_QUIZ = 2

# ===================== FOYDALANUVCHI HOLATI =====================
@dataclass
class QuizState:
    """Har bir foydalanuvchi uchun test holati"""
    questions: list[dict] = field(default_factory=list)
    current: int = 0
    score: int = 0
    correct: int = 0
    wrong: int = 0
    block: int = 1
    skipped_streak: int = 0
    answered_current: bool = False
    current_poll_id: Optional[str] = None
    correct_index: int = 0
    current_ball: int = 1
    ball_stats: dict = field(default_factory=lambda: {
        1: {"correct": 0, "wrong": 0},
        2: {"correct": 0, "wrong": 0},
        3: {"correct": 0, "wrong": 0},
    })

    @property
    def max_ball(self) -> int:
        return sum(q.get("ball", 1) for q in self.questions)

    @property
    def answered_count(self) -> int:
        return self.correct + self.wrong

    @property
    def percent(self) -> float:
        return (self.score / self.max_ball * 100) if self.max_ball > 0 else 0.0


def get_quiz_state(context: ContextTypes.DEFAULT_TYPE) -> Optional[QuizState]:
    return context.user_data.get("quiz_state")


def set_quiz_state(context: ContextTypes.DEFAULT_TYPE, state: QuizState):
    context.user_data["quiz_state"] = state


def clear_quiz_state(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("quiz_state", None)


# ===================== KLAVIATURALAR =====================
def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["🚀 Start Test", "🛑 Testni yakunlash"],
            ["🏠 Bosh sahifa", "ℹ️ Test haqida"],
        ],
        resize_keyboard=True,
    )


def block_keyboard() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for i in range(1, TOTAL_BLOCKS + 1):
        start = (i - 1) * QUESTIONS_PER_BLOCK + 1
        end = i * QUESTIONS_PER_BLOCK
        btn = InlineKeyboardButton(f"📚 {start}–{end}", callback_data=f"block_{i}")
        row.append(btn)
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


# ===================== YORDAMCHI FUNKSIYALAR =====================
def ball_emoji(ball: int) -> str:
    return {1: "🟢", 2: "🟡", 3: "🔴"}.get(ball, "⚪")


def grade_result(percent: float) -> tuple[str, str]:
    if percent >= 90:
        return "🏆 A'lo!", "🥇"
    elif percent >= 75:
        return "👍 Yaxshi!", "🥈"
    elif percent >= 60:
        return "📚 Qoniqarli", "🥉"
    else:
        return "📖 Ko'proq o'qing", "📝"


def truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


def generate_variants(
    correct_answer: str, question_text: str
) -> tuple[list[str], int]:
    """To'g'ri javobga 2 ta noto'g'ri variant qo'shish"""
    other_answers = [
        q["javob"]
        for q in ALL_QUESTIONS
        if q["javob"] != correct_answer and q["savol"] != question_text
    ]
    wrong = random.sample(other_answers, 2) if len(other_answers) >= 2 else [
        "Noto'g'ri variant A",
        "Noto'g'ri variant B",
    ]
    variants = [correct_answer] + wrong
    random.shuffle(variants)
    return variants, variants.index(correct_answer)


# ===================== XABAR YUBORISH YORDAMCHISI =====================
async def send_text(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    text: str,
    reply_markup=None,
    parse_mode: str = "Markdown",
):
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.error(f"send_text xatolik (chat_id={chat_id}): {e}")


# ===================== KOMANDALAR =====================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot boshlanishi"""
    clear_quiz_state(context)
    user = update.effective_user
    text = (
        f"✈️ *Salom, {user.first_name}!*\n\n"
        f"🎓 *Havo Kuchlar Tayyorlash Quiz Bot*\n\n"
        f"📦 Jami *200 ta savol*, *10 ta bo'lim* — har biri 20 tadan.\n"
        f"👇 Testni boshlash uchun *🚀 Start Test* tugmasini bosing."
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_keyboard())
    return SELECTING_BLOCK


async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test haqida ma'lumot"""
    text = (
        "ℹ️ *Test haqida:*\n\n"
        "📊 *Savol darajalari:*\n"
        "🟢 1 ball — Oson\n"
        "🟡 2 ball — O'rta\n"
        "🔴 3 ball — Qiyin\n\n"
        f"⏱ Har bir savolga *{POLL_OPEN_SECONDS} soniya* beriladi.\n"
        f"⚠️ Ketma-ket *{MAX_SKIPPED_STREAK} marta* javob berilmasa — test yakunlanadi.\n\n"
        f"📦 Jami: *{len(ALL_QUESTIONS)} ta savol*, *{TOTAL_BLOCKS} ta bo'lim*."
    )
    target = update.callback_query.message if update.callback_query else update.message
    await target.reply_text(text, parse_mode="Markdown")


async def cmd_stop_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi testni to'xtatadi"""
    state = get_quiz_state(context)
    if state and state.current > 0:
        await update.message.reply_text("🛑 Test yakunlanmoqda...")
        await show_result(context, update.effective_chat.id, state)
    else:
        await update.message.reply_text(
            "❌ Faol test mavjud emas.", reply_markup=main_keyboard()
        )
    clear_quiz_state(context)
    return SELECTING_BLOCK


async def cmd_select_block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Blok tanlash menyusini chiqarish"""
    clear_quiz_state(context)
    text = "📚 *Qaysi bo'limni tanlaysiz?*"
    target = update.callback_query.message if update.callback_query else update.message
    await target.reply_text(text, parse_mode="Markdown", reply_markup=block_keyboard())
    return SELECTING_BLOCK


# ===================== BLOK TANLASH =====================
async def on_block_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    block_num = int(query.data.split("_")[1])
    questions = random.sample(BLOCKS[block_num], len(BLOCKS[block_num]))  # aralashtir

    state = QuizState(
        questions=questions,
        block=block_num,
    )
    set_quiz_state(context, state)

    start_idx = (block_num - 1) * QUESTIONS_PER_BLOCK + 1
    end_idx = block_num * QUESTIONS_PER_BLOCK

    text = (
        f"✅ *{start_idx}–{end_idx} bo'limi tanlandi!*\n\n"
        f"📝 *{QUESTIONS_PER_BLOCK} ta savol* random tartibda beriladi.\n"
        f"⏱ Har bir savol uchun *{POLL_OPEN_SECONDS} soniya*.\n\n"
        f"Boshladik! 🚀"
    )
    await query.edit_message_text(text, parse_mode="Markdown")
    await asyncio.sleep(1)
    await send_next_question(context, query.message.chat_id)
    return IN_QUIZ


# ===================== SAVOL YUBORISH =====================
async def send_next_question(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    state = get_quiz_state(context)
    if not state:
        return

    # 3 ta ketma-ket skip → test yakunlash
    if state.skipped_streak >= MAX_SKIPPED_STREAK:
        await send_text(
            context,
            chat_id,
            f"⚠️ *Ketma-ket {MAX_SKIPPED_STREAK} ta savolga javob bermaganligi sababli test yakunlandi!*",
        )
        await show_result(context, chat_id, state)
        clear_quiz_state(context)
        return

    # Barcha savollar tugadi
    if state.current >= len(state.questions):
        await show_result(context, chat_id, state)
        clear_quiz_state(context)
        return

    q = state.questions[state.current]
    variants, correct_index = generate_variants(q["javob"], q["savol"])

    # Holatni yangilash
    state.correct_index = correct_index
    state.current_ball = q.get("ball", 1)
    state.answered_current = False

    # Poll matni
    b_emoji = ball_emoji(state.current_ball)
    poll_question = truncate(
        f"Savol {state.current + 1}/{len(state.questions)} | {b_emoji} {state.current_ball} ball\n\n{q['savol']}",
        300,
    )
    options = [truncate(str(v), 100) for v in variants]

    try:
        poll_msg = await context.bot.send_poll(
            chat_id=chat_id,
            question=poll_question,
            options=options,
            type="quiz",
            correct_option_id=correct_index,
            is_anonymous=False,
            open_period=POLL_OPEN_SECONDS,
        )
        state.current_poll_id = poll_msg.poll.id

        # bot_data ga faqat kerakli ma'lumot saqlanadi
        context.bot_data[poll_msg.poll.id] = {
            "chat_id": chat_id,
            "user_id": update_effective_user_id(context),
        }
        logger.info(
            f"Poll yuborildi: savol {state.current + 1}, chat_id={chat_id}"
        )
    except Exception as e:
        logger.error(f"Poll yuborishda xatolik: {e}")


def update_effective_user_id(context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    """user_data ga tegishli user_id ni topish"""
    return context.user_data.get("_user_id")


# ===================== POLL JAVOB HANDLER =====================
async def on_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi javob berganda"""
    poll_answer = update.poll_answer
    state = get_quiz_state(context)

    # Tegishli poll emasmi?
    if not state or poll_answer.poll_id != state.current_poll_id:
        return

    if state.answered_current:
        return  # Takror javob — e'tiborsiz

    state.answered_current = True
    state.skipped_streak = 0

    selected = poll_answer.option_ids[0]
    ball = state.current_ball

    if selected == state.correct_index:
        state.score += ball
        state.correct += 1
        state.ball_stats[ball]["correct"] += 1
    else:
        state.wrong += 1
        state.ball_stats[ball]["wrong"] += 1

    state.current += 1

    # Keyingi savolga o'tish
    await asyncio.sleep(1.5)
    await send_next_question(context, poll_answer.user.id)


# ===================== POLL YOPILISH HANDLER (TAYMER) =====================
async def on_poll_closed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Poll taymer tugaganda"""
    poll = update.poll
    if not poll.is_closed or poll.id not in context.bot_data:
        return

    saved = context.bot_data.pop(poll.id)
    chat_id: int = saved["chat_id"]

    # Foydalanuvchi context ni topish (global user_data kerak bo'ladi)
    # PollHandler da user_data mavjud bo'lmaydi — shu sababli chat_id orqali ishlaymiz
    # user_data ni ConversationHandler boshqaradi, shuning uchun quyida dispatcher orqali olamiz
    user_data = context.application.user_data

    # chat_id == user_id bo'lgani uchun (private chat)
    u_data = user_data.get(chat_id, {})
    state: Optional[QuizState] = u_data.get("quiz_state")

    if not state or state.answered_current:
        return  # Foydalanuvchi javob bergan, skip shart emas

    state.skipped_streak += 1
    state.wrong += 1
    state.current += 1

    streak = state.skipped_streak
    await send_text(
        context,
        chat_id,
        f"⏱ *Vaqt tugadi!* Javob berilmadi. ⚠️ Ketma-ket: *{streak}/{MAX_SKIPPED_STREAK}*",
    )

    await asyncio.sleep(1)
    await send_next_question(context, chat_id)


# ===================== NATIJA =====================
async def show_result(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    state: QuizState,
):
    block = state.block
    start_idx = (block - 1) * QUESTIONS_PER_BLOCK + 1
    end_idx = block * QUESTIONS_PER_BLOCK
    baho, baho_emoji_str = grade_result(state.percent)

    # Darajalar statistikasi
    stats_lines = []
    for lvl in [1, 2, 3]:
        bs = state.ball_stats[lvl]
        total = bs["correct"] + bs["wrong"]
        if total > 0:
            stats_lines.append(
                f"{ball_emoji(lvl)} {lvl} balllik: ✅ {bs['correct']} / ❌ {bs['wrong']} ({total} ta)"
            )
    stats_text = "\n".join(stats_lines) if stats_lines else "—"

    text = (
        f"🏁 *NATIJA — {start_idx}–{end_idx} bo'limi*\n"
        f"{'═' * 30}\n\n"
        f"{baho_emoji_str} *{baho}*\n\n"
        f"✅ To'g'ri: *{state.correct}*\n"
        f"❌ Noto'g'ri: *{state.wrong}*\n"
        f"📊 Jami javob: *{state.answered_count}/{len(state.questions)}*\n"
        f"🏆 Ball: *{state.score}/{state.max_ball}*\n"
        f"📈 Foiz: *{state.percent:.1f}%*\n\n"
        f"📋 *Darajalar bo'yicha:*\n"
        f"{stats_text}\n\n"
        f"{'─' * 30}\n"
        f"Yana boshlash uchun *🚀 Start Test* ni bosing."
    )

    await send_text(context, chat_id, text, reply_markup=main_keyboard())


# ===================== USER_ID SAQLASH =====================
async def save_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Har bir xabarda user_id ni user_data ga yozib qo'yamiz"""
    if update.effective_user:
        context.user_data["_user_id"] = update.effective_user.id


# ===================== MAIN =====================
def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )
    logger.info("✈️ Bot ishga tushdi!")

    # Har bir updateda user_id saqlansin
    app.add_handler(MessageHandler(filters.ALL, save_user_id), group=-1)

    # ConversationHandler
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start),
            MessageHandler(filters.Regex("^🚀 Start Test$"), cmd_select_block),
            MessageHandler(filters.Regex("^🏠 Bosh sahifa$"), cmd_start),
            MessageHandler(filters.Regex("^ℹ️ Test haqida$"), cmd_about),
        ],
        states={
            SELECTING_BLOCK: [
                CallbackQueryHandler(on_block_selected, pattern=r"^block_\d+$"),
                MessageHandler(filters.Regex("^🚀 Start Test$"), cmd_select_block),
                MessageHandler(filters.Regex("^🏠 Bosh sahifa$"), cmd_start),
                MessageHandler(filters.Regex("^ℹ️ Test haqida$"), cmd_about),
            ],
            IN_QUIZ: [
                MessageHandler(filters.Regex("^🛑 Testni yakunlash$"), cmd_stop_test),
                MessageHandler(filters.Regex("^🚀 Start Test$"), cmd_select_block),
                MessageHandler(filters.Regex("^🏠 Bosh sahifa$"), cmd_start),
                MessageHandler(filters.Regex("^ℹ️ Test haqida$"), cmd_about),
            ],
        },
        fallbacks=[
            CommandHandler("start", cmd_start),
            MessageHandler(filters.Regex("^🏠 Bosh sahifa$"), cmd_start),
        ],
        per_user=True,
        per_chat=True,
        per_message=False,
        allow_reentry=True,
        conversation_timeout=600,  # 10 daqiqa faolsizlik → holatni tozalash
    )

    app.add_handler(conv)
    app.add_handler(PollAnswerHandler(on_poll_answer))
    app.add_handler(PollHandler(on_poll_closed))

    logger.info("✈️ Quiz Bot polling boshlandi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
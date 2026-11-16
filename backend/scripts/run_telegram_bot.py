"""FitAI Telegram Bot (Long Polling).

Cho phép người dùng:
- Liên kết tài khoản FitAI bằng mã (`/link <MÃ>`) hoặc email+mật khẩu (`/link <email> <mật khẩu>`).
- Chụp/gửi ảnh món ăn để Gemini Vision nhận diện, tra calo/macro từ PostgreSQL và bấm nút lưu thẳng vào nhật ký.
- Nhắn tin tự nhiên để hỏi đáp hoặc yêu cầu Agent tự ghi bữa ăn / cân nặng (`FitnessAdvisorAgent`).
- Xem tổng kết dinh dưỡng hôm nay (`/today`).

Chạy từ thư mục `backend`:
    .venv\\Scripts\\python.exe -m scripts.run_telegram_bot
"""
from __future__ import annotations

import logging
import secrets
import sys
from pathlib import Path

from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Đảm bảo `backend/` nằm trong sys.path khi chạy trực tiếp
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.config import settings  # noqa: E402
from core.database import AsyncSessionLocal  # noqa: E402
from core.security import verify_password  # noqa: E402
from models.meal_log import MealType  # noqa: E402
from models.profile import UserProfile  # noqa: E402
from models.user import User  # noqa: E402
from services import meals as meal_service  # noqa: E402
from services.agent_actions import log_body_metric_for_user, log_meal_for_user, log_workout_for_user  # noqa: E402
from services.ai_agents.fitness_advisor import (  # noqa: E402
    AgentToolContext,
    ChatAgentException,
    fitness_agent,
)
from services.foods.lookup import search_foods  # noqa: E402
from services.intent_classifier import try_fast_route  # noqa: E402
from services.meal_vision import VisionMealResult, analyze_meal_photo  # noqa: E402
from services.progress import progress_summary_for_agent  # noqa: E402
from services.training.progress import training_summary_for_agent  # noqa: E402
from services.training.recommend import recommendation_for_user  # noqa: E402

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("fitai.telegram")

MEAL_TYPE_LABELS = {
    MealType.SANG: "Bữa sáng",
    MealType.TRUA: "Bữa trưa",
    MealType.TOI: "Bữa tối",
    MealType.PHU: "Bữa phụ",
}


async def _get_linked_user(chat_id: int) -> User | None:
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
        return res.scalar_one_or_none()


def _format_vision_reply(result: VisionMealResult) -> str:
    if not result.items:
        note = result.notes or "Không nhận diện được món ăn nào trong ảnh."
        return f"🤔 {note}"

    meal_label = MEAL_TYPE_LABELS.get(result.meal_type, result.meal_type.value)
    lines = [f"🍽️ **Nhận diện bữa ăn ({meal_label})**\n"]
    for item in result.items:
        if item.matched:
            kcal = f"{item.energy_kcal:g}" if item.energy_kcal is not None else "?"
            p = f"{item.protein_g:g}" if item.protein_g is not None else "?"
            f = f"{item.fat_g:g}" if item.fat_g is not None else "?"
            c = f"{item.carb_g:g}" if item.carb_g is not None else "?"
            lines.append(
                f"• **{item.food_name_vi}** (~{item.grams:g} g)\n"
                f"  ↳ {kcal} kcal | P: {p}g | F: {f}g | C: {c}g"
            )
            if item.note:
                lines.append(f"  _({item.note})_")
        else:
            lines.append(f"• {item.display_name} (~{item.grams:g} g) — ⚠️ Chưa có trong từ điển DB")

    if result.matched_items:
        lines.append(
            f"\n📊 **Tổng tạm tính:** {result.total_kcal:g} kcal | "
            f"P: {result.total_protein_g:g}g | F: {result.total_fat_g:g}g | C: {result.total_carb_g:g}g"
        )
    if result.notes:
        lines.append(f"\n💡 _{result.notes}_")
    if result.disclaimer:
        lines.append(f"\n⚠️ {result.disclaimer}")
    return "\n".join(lines)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message:
        return
    user = await _get_linked_user(update.effective_chat.id)
    if user:
        name = user.full_name or user.email
        await update.message.reply_text(
            f"Xin chào {name}! Tài khoản FitAI của bạn đã được liên kết.\n\n"
            "📸 Gửi **ảnh bữa ăn** để mình ước lượng calo & lưu nhật ký.\n"
            "💬 Nhắn **tự nhiên** (vd: 'ghi 150g ức gà bữa trưa', 'chạy bộ 30 phút mức vừa', 'hôm nay mình nặng 68kg', 'hôm nay ăn bao nhiêu calo rồi?').\n"
            "📊 Gõ /today để xem nhanh tổng kết hôm nay."
        )
    else:
        await update.message.reply_text(
            "Chào mừng bạn đến với **FitAI Bot**! 🏋️‍♂️🥗\n\n"
            "Để bắt đầu, hãy liên kết tài khoản FitAI của bạn bằng một trong hai cách:\n"
            "1️⃣ `/link <MÃ_LIÊN_KẾT>` (lấy mã từ web FitAI)\n"
            "2️⃣ `/link <email> <mật_khẩu>`"
        )


async def cmd_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message:
        return
    args = context.args or []
    chat_id = update.effective_chat.id

    async with AsyncSessionLocal() as db:
        user: User | None = None
        if len(args) == 1:
            code = args[0].strip().upper()
            res = await db.execute(select(User).where(User.telegram_link_code == code))
            user = res.scalar_one_or_none()
            if user is None:
                await update.message.reply_text("❌ Mã liên kết không hợp lệ hoặc đã hết hạn.")
                return
        elif len(args) >= 2:
            email = args[0].strip().lower()
            password = " ".join(args[1:])
            res = await db.execute(select(User).where(User.email == email))
            candidate = res.scalar_one_or_none()
            if candidate is None or not verify_password(password, candidate.hashed_password):
                await update.message.reply_text("❌ Sai email hoặc mật khẩu FitAI.")
                return
            user = candidate
            try:
                await update.message.delete()
            except Exception:
                pass
        else:
            await update.message.reply_text("Cách dùng: `/link <MÃ>` hoặc `/link <email> <mật_khẩu>`")
            return

        # Gỡ liên kết chat_id cũ nếu từng gắn với tài khoản khác
        old_res = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
        for old_user in old_res.scalars():
            if old_user.id != user.id:
                old_user.telegram_chat_id = None

        user.telegram_chat_id = chat_id
        user.telegram_link_code = None
        await db.commit()
        name = user.full_name or user.email
        await update.message.reply_text(
            f"✅ Đã liên kết thành công với tài khoản **{name}**!\n"
            "Giờ bạn có thể gửi ảnh món ăn hoặc nhắn tin trực tiếp với FitAI."
        )


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message:
        return
    user = await _get_linked_user(update.effective_chat.id)
    if not user:
        await update.message.reply_text("⚠️ Bạn chưa liên kết tài khoản. Hãy dùng `/link <email> <mật_khẩu>` hoặc `/link <MÃ>`.")
        return

    async with AsyncSessionLocal() as db:
        summary = await meal_service.daily_summary(db, user.id, meal_service.today_vn())

    totals = summary.get("totals") or {}
    targets = summary.get("targets") or {}
    kcal = totals.get("energy_kcal")
    target_kcal = targets.get("energy_kcal")
    p = totals.get("protein_g")
    f = totals.get("fat_g")
    c = totals.get("carb_g")

    kcal_str = f"{kcal:g}" if kcal is not None else "0"
    target_str = f" / {target_kcal:g}" if target_kcal is not None else ""
    await update.message.reply_text(
        f"📅 **Tổng kết hôm nay ({summary.get('date')})**\n"
        f"🔥 Calo: **{kcal_str}{target_str} kcal**\n"
        f"🥩 Protein: {p if p is not None else 0:g}g | "
        f"🥑 Fat: {f if f is not None else 0:g}g | "
        f"🍚 Carb: {c if c is not None else 0:g}g\n"
        f"📝 Số món đã ghi: {summary.get('entries_count', 0)}"
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message or not update.message.photo:
        return
    user = await _get_linked_user(update.effective_chat.id)
    if not user:
        await update.message.reply_text("⚠️ Bạn chưa liên kết tài khoản FitAI. Hãy dùng `/link <email> <mật_khẩu>` hoặc `/link <MÃ>`.")
        return

    wait_msg = await update.message.reply_text("🔍 Đang phân tích ảnh món ăn và đối chiếu bảng dinh dưỡng...")
    try:
        largest_photo = update.message.photo[-1]
        tg_file = await largest_photo.get_file()
        image_bytes = bytes(await tg_file.download_as_bytearray())

        async with AsyncSessionLocal() as db:
            result = await analyze_meal_photo(
                db=db,
                image_bytes=image_bytes,
                mime_type="image/jpeg",
                caption=update.message.caption,
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Photo analysis error: %s", exc)
        await wait_msg.edit_text("❌ Xin lỗi, mình chưa phân tích được ảnh này. Bạn thử gửi ảnh rõ hơn nhé!")
        return

    reply_text = _format_vision_reply(result)
    if not result.matched_items:
        await wait_msg.edit_text(reply_text)
        return

    pending_id = secrets.token_hex(4)
    pending_map = context.user_data.setdefault("pending_meals", {})
    pending_map[pending_id] = {
        "user_id": str(user.id),
        "meal_type": result.meal_type.value,
        "items": [
            {
                "food_id": item.food_id,
                "food_name_vi": item.food_name_vi,
                "grams": item.grams,
                "energy_kcal": item.energy_kcal,
            }
            for item in result.matched_items
        ],
    }
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Lưu vào nhật ký", callback_data=f"save_meal:{pending_id}"),
                InlineKeyboardButton("❌ Huỷ", callback_data=f"cancel_meal:{pending_id}"),
            ]
        ]
    )
    await wait_msg.edit_text(reply_text, reply_markup=keyboard)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    action, _, pending_id = query.data.partition(":")
    pending_map: dict = context.user_data.get("pending_meals") or {}
    payload = pending_map.pop(pending_id, None)

    if action == "cancel_meal":
        await query.edit_message_text("❌ Đã huỷ ghi bữa ăn này.")
        return

    if action != "save_meal" or not payload:
        await query.edit_message_text("⚠️ Phiên xác nhận này đã hết hạn hoặc đã được xử lý.")
        return

    user = await _get_linked_user(query.message.chat_id) if query.message else None
    if not user or str(user.id) != payload["user_id"]:
        await query.edit_message_text("⚠️ Không xác thực được tài khoản để lưu.")
        return

    saved_names: list[str] = []
    total_kcal = 0.0
    async with AsyncSessionLocal() as db:
        meal_type = MealType(payload["meal_type"])
        for item in payload["items"]:
            entry = await meal_service.create_meal(
                db=db,
                user_id=user.id,
                food_id=int(item["food_id"]),
                grams=float(item["grams"]),
                meal_type=meal_type,
            )
            saved_names.append(f"{item['food_name_vi']} ({item['grams']:g}g)")
            total_kcal += entry.energy_kcal or 0.0
        await db.commit()

    await query.edit_message_text(
        f"✅ Đã lưu **{', '.join(saved_names)}** ({total_kcal:g} kcal) vào nhật ký hôm nay!"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message or not update.message.text:
        return
    user = await _get_linked_user(update.effective_chat.id)
    if not user:
        await update.message.reply_text(
            "⚠️ Bạn chưa liên kết tài khoản FitAI.\n"
            "Hãy dùng `/link <MÃ>` hoặc `/link <email> <mật_khẩu>` trước nhé!"
        )
        return

    text = update.message.text.strip()
    history: list[dict[str, str]] = context.user_data.setdefault("history", [])

    async with AsyncSessionLocal() as db:
        fast_result = await try_fast_route(db, text)
        if fast_result is not None:
            reply, _sources = fast_result
        else:
            res = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
            profile = res.scalar_one_or_none()
            profile_data = None
            if profile is not None:
                profile_data = {
                    "age": profile.age,
                    "gender": profile.gender,
                    "height_cm": profile.height_cm,
                    "weight_kg": profile.weight_kg,
                    "activity_level": profile.activity_level,
                    "fitness_goal": profile.fitness_goal,
                    "dietary_restrictions": profile.dietary_restrictions,
                }

            async def _load_profile():
                r = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
                return r.scalar_one_or_none()

            tool_context = AgentToolContext(
                load_profile=_load_profile,
                lookup_food=lambda q: search_foods(db, q),
                load_daily_summary=lambda day: meal_service.daily_summary(db, user.id, day),
                load_progress_summary=lambda days: progress_summary_for_agent(db, user.id, days),
                load_recommendation=lambda exp: recommendation_for_user(db, user.id, exp),
                load_training_summary=lambda: training_summary_for_agent(db, user.id),
                log_meal=lambda q, g, mt: log_meal_for_user(db, user.id, q, g, mt),
                log_body_metric=lambda w, waist: log_body_metric_for_user(db, user.id, w, waist),
                log_workout=lambda act, mins, inten, cat, notes: log_workout_for_user(
                    db, user.id, act, mins, inten, cat, notes
                ),
            )
            try:
                reply = await fitness_agent.chat(
                    history=history[-10:],
                    user_message=text,
                    profile_data=profile_data,
                    tool_context=tool_context,
                )
            except ChatAgentException as exc:
                await update.message.reply_text(f"⚠️ {exc.message}")
                return

    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": reply})
    if len(history) > 20:
        del history[:-20]

    await update.message.reply_text(reply[:4000])


def main() -> None:
    token = (settings.TELEGRAM_BOT_TOKEN or "").strip()
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN trống — bỏ qua khởi chạy Telegram Bot.")
        return

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("link", cmd_link))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("FitAI Telegram Bot đang chạy (long polling)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()


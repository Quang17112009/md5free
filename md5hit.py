import hashlib
import json
import os
import joblib
from telegram.ext import ( # Corrected: 'from' before 'telegram.ext'
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from typing import Dict, Tuple

class MD5CharacterAnalyzer:
    def __init__(self): # Corrected: '__init__' instead of 'init'
        self.weights = {
            '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
            'a': 10, 'b': 11, 'c': 12, 'd': 13, 'e': 14, 'f': 15
        }

    def analyze_md5(self, md5: str) -> Tuple[str, float, Dict]:
        md5 = md5.lower()
        if len(md5) != 32 or not all(c in self.weights for c in md5):
            raise ValueError("Mã MD5 không hợp lệ.")

        w1 = sum(self.weights[c] for c in md5[:16])
        w2 = sum(self.weights[c] for c in md5[16:])
        w3 = sum(self.weights[c] for c in md5[::2])
        w4 = sum(self.weights[c] for c in md5[1::2])

        combined = (w1 * 0.4 + w2 * 0.4 + (w3 - w4) * 0.2)
        result = "Tài" if int(combined) % 36 >= 18 else "Xỉu"
        confidence = round(abs(((combined % 36) - 18) / 18 * 100), 2)

        analysis = {
            "even_digits": sum(1 for c in md5 if c in "02468ace"),
            "odd_digits": sum(1 for c in md5 if c in "13579bdf"),
            "alpha_count": sum(1 for c in md5 if c in "abcdef"),
            "num_count": sum(1 for c in md5 if c in "0123456789"),
            "entropy": round(len(set(md5)) / 16, 2)
        }

        return result, confidence, analysis

class TelegramBot:
    def __init__(self, token: str, admin_id: int): # Corrected: '__init__' instead of 'init'
        self.app = Application.builder().token(token).build()
        self.admin_id = admin_id
        self.analyzer = MD5CharacterAnalyzer()
        self.users: Dict[int, dict] = {}
        self.data_file = "md5hit.json"
        self.load_user_data()

    def load_user_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    # Ensure all user IDs are integers when loading
                    self.users = {int(k): v for k, v in data.items()}
            except (json.JSONDecodeError, OSError) as e: # Added error handling
                print(f"Error loading user data: {e}")
                self.users = {}
        else:
            self.users = {}

    def save_user_data(self):
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.users, f, indent=2)
        except OSError as e: # Added error handling
            print(f"Error saving user data: {e}")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        # Use full_name if available, otherwise username, otherwise first_name
        username = update.effective_user.full_name or update.effective_user.username or update.effective_user.first_name

        if user_id not in self.users:
            self.users[user_id] = {"balance": 10, "history": [], "first_start": True}
            welcome_msg = (
                f"✨ Chào {username}\n"
                "🤖 Tool hỗ trợ game hit.club\n"
                "➡️ Gửi mã MD5 để bắt đầu dự đoán\n"
                "🔹 Lệnh Sử Dụng\n"
                ">> /info - Xem Hồ Sơ\n"
                ">> /history - Lịch Sử\n"
                "🔹 Lệnh Admin\n"
                ">> /addxu <id> <xu> - Cộng Xu\n"
                ">> /unxu <id> <xu> - Trừ Xu\n"
                ">> /thongke - Xem Thống Kê User\n"
                "**🎉 Bạn nhận được 10 xu khi tham gia lần đầu!**"
            )
        else:
            welcome_msg = (
                f"✨ Chào {username}\n"
                "🤖 Tool hỗ trợ game hit.club\n"
                "➡️ Gửi mã MD5 để bắt đầu dự đoán\n"
                "🔹 Lệnh Sử Dụng\n"
                ">> /info - Xem Hồ Sơ\n"
                ">> /history - Lịch Sử\n"
                "🔹 Lệnh Admin\n"
                ">> /addxu <id> <xu> - Cộng Xu\n"
                ">> /unxu <id> <xu> - Trừ Xu\n"
                ">> /thongke - Xem Thống Kê User"
            )
            # Ensure first_start is explicitly set to False if user already exists
            self.users[user_id]["first_start"] = False

        self.save_user_data()
        await update.message.reply_text(welcome_msg, parse_mode="Markdown")

    async def info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        username = update.effective_user.full_name or update.effective_user.username or update.effective_user.first_name
        user_data = self.users.get(user_id, {"balance": 0, "history": [], "first_start": False}) # Default if user not found

        info_msg = (
            f"👤 Tên: {username}\n"
            f"🆔 ID: {user_id}\n"
            f"💰 Xu: {user_data['balance']}"
        )
        await update.message.reply_text(info_msg, parse_mode="Markdown")

    async def history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = self.users.get(user_id, {"balance": 0, "history": [], "first_start": False})

        if not user_data["history"]:
            await update.message.reply_text("📜 Lịch sử trống.", parse_mode="Markdown")
            return

        history_msg = "📜 Lịch Sử Dự Đoán\n\n"
        # Display only a few recent entries to avoid very long messages
        for md5, result in user_data["history"][-10:]: # Show last 10 entries
            history_msg += f"Mã MD5: `{md5}` - Dự Đoán: {result}\n" # Added backticks for MD5
        history_msg += "\n*Chỉ hiển thị 10 mục gần nhất." # Indicate truncation

        await update.message.reply_text(history_msg, parse_mode="Markdown")

    async def add_xu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("🚫 Chỉ admin mới có thể sử dụng lệnh này!", parse_mode="Markdown")
            return
        try:
            args = context.args
            if len(args) != 2:
                raise ValueError("Vui lòng nhập đúng định dạng: `/addxu <id> <xu>`") # Added backticks
            target_id, amount = int(args[0]), int(args[1])
            if amount <= 0:
                raise ValueError("Số xu phải lớn hơn 0")

            if target_id not in self.users:
                self.users[target_id] = {"balance": 0, "history": [], "first_start": False}

            self.users[target_id]["balance"] += amount
            self.save_user_data()
            await update.message.reply_text(
                f"✅ **Đã cộng {amount} xu cho ID {target_id}. Số dư mới: {self.users[target_id]['balance']}**",
                parse_mode="Markdown")
            # Added check for send_message to ensure target_id exists in chat
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"💸 **Bạn vừa được admin cộng {amount} xu. Số dư hiện tại: {self.users[target_id]['balance']}**",
                    parse_mode="Markdown")
            except Exception as e:
                print(f"Could not send message to user {target_id}: {e}")
                await update.message.reply_text(f"⚠️ Không thể gửi thông báo tới người dùng ID {target_id}.", parse_mode="Markdown")
        except ValueError as e:
            await update.message.reply_text(f"❌ Lỗi: {e}", parse_mode="Markdown")
        except IndexError: # Catch if args are missing
            await update.message.reply_text("❌ Lỗi: Vui lòng nhập đúng định dạng: `/addxu <id> <xu>`", parse_mode="Markdown")

    async def un_xu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("🚫 Chỉ admin mới có thể sử dụng lệnh này!", parse_mode="Markdown")
            return
        try:
            args = context.args
            if len(args) != 2:
                raise ValueError("Vui lòng nhập đúng định dạng: `/unxu <id> <xu>`") # Added backticks
            target_id, amount = int(args[0]), int(args[1])
            if amount <= 0:
                raise ValueError("Số xu phải lớn hơn 0")
            if target_id not in self.users:
                await update.message.reply_text(f"❌ Người dùng với ID {target_id} không tồn tại.", parse_mode="Markdown")
                return
            if self.users[target_id]["balance"] < amount:
                await update.message.reply_text(
                    f"❌ Số dư của ID {target_id} không đủ ({self.users[target_id]['balance']} xu).",
                    parse_mode="Markdown")
                return
            self.users[target_id]["balance"] -= amount
            self.save_user_data()
            await update.message.reply_text(
                f"✅ Đã trừ {amount} xu từ ID {target_id}. Số dư mới: {self.users[target_id]['balance']}",
                parse_mode="Markdown")
            # Added check for send_message to ensure target_id exists in chat
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"💸 Bạn vừa bị admin trừ {amount} xu. Số dư hiện tại: {self.users[target_id]['balance']}",
                    parse_mode="Markdown")
            except Exception as e:
                print(f"Could not send message to user {target_id}: {e}")
                await update.message.reply_text(f"⚠️ Không thể gửi thông báo tới người dùng ID {target_id}.", parse_mode="Markdown")
        except ValueError as e:
            await update.message.reply_text(f"❌ Lỗi: {e}", parse_mode="Markdown")
        except IndexError: # Catch if args are missing
            await update.message.reply_text("❌ Lỗi: Vui lòng nhập đúng định dạng: `/unxu <id> <xu>`", parse_mode="Markdown")

    async def thongke(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("🚫 Chỉ admin mới có thể sử dụng lệnh này!", parse_mode="Markdown")
            return
        if not self.users:
            await update.message.reply_text("📊 Không có dữ liệu người dùng.", parse_mode="Markdown")
            return
        stats_msg = "📊 Thống Kê Người Dùng\n\nTên - ID - Xu\n"
        for idx, (user_id, data) in enumerate(self.users.items(), 1):
            try:
                chat = await context.bot.get_chat(user_id)
                # Use full_name if available, otherwise username, otherwise first_name
                username = chat.full_name or chat.username or chat.first_name
            except Exception as e: # Catch exceptions if get_chat fails (e.g., user blocked bot)
                username = f"[Unknown User {user_id}]" # Indicate unknown user
                print(f"Could not get chat info for user {user_id}: {e}")
            stats_msg += f"{idx}. {username} - {user_id} - {data['balance']}\n"
        await update.message.reply_text(stats_msg, parse_mode="Markdown")

    async def handle_md5(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        # Ensure user exists in self.users before proceeding
        if user_id not in self.users:
            self.users[user_id] = {"balance": 0, "history": [], "first_start": False}
            self.save_user_data() # Save new user data immediately

        if self.users[user_id]["balance"] < 1:
            await update.message.reply_text("❌ Bạn không đủ xu để dự đoán (cần 1 xu/lần).", parse_mode="Markdown")
            return
        md5_input = update.message.text.strip()
        try:
            result, confidence, analysis = self.analyzer.analyze_md5(md5_input)
            self.users[user_id]["balance"] -= 1
            # Limit history to prevent it from growing indefinitely
            if len(self.users[user_id]["history"]) >= 50: # Example: keep last 50 entries
                self.users[user_id]["history"].pop(0) # Remove oldest entry
            self.users[user_id]["history"].append((md5_input, result))
            self.save_user_data()
            response = (
                "📊 KẾT QUẢ PHÂN TÍCH 📊\n\n"
                f"🔢 Mã MD5: `{md5_input}`\n"
                f"🎯 *Dự đoán*: {result} ({confidence}%)\n\n"
                f"🔍 *Phân Tích*:\n"
                f"▫️ Chữ số chẵn: {analysis['even_digits']}, lẻ: {analysis['odd_digits']}\n"
                f"▫️ Ký tự chữ (a-f): {analysis['alpha_count']}, số (0-9): {analysis['num_count']}\n"
                f"▫️ Mức phân tán (entropy): {analysis['entropy']}\n\n"
                f"💰 Xu còn lại: {self.users[user_id]['balance']}"
            )
            await update.message.reply_text(response, parse_mode="Markdown")
        except ValueError as e:
            await update.message.reply_text(f"❌ Lỗi: {e}", parse_mode="Markdown")

    def run(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("info", self.info))
        self.app.add_handler(CommandHandler("history", self.history))
        self.app.add_handler(CommandHandler("addxu", self.add_xu))
        self.app.add_handler(CommandHandler("unxu", self.un_xu))
        self.app.add_handler(CommandHandler("thongke", self.thongke))
        # MessageHandler should come after CommandHandlers to ensure commands are handled first
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_md5))
        self.app.run_polling()

if __name__ == "__main__": # Corrected: '__main__' instead of 'name == "main"'
    # You should securely manage your bot token and admin ID.
    # Avoid hardcoding sensitive information directly in your code for production.
    # Consider using environment variables.
    # Example: TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    # ADMIN_ID = int(os.getenv("TELEGRAM_ADMIN_ID"))
    bot = TelegramBot(token="7749105278:AAF4q2n-WTZEsMFBXEvrhuYFSMVjkoeXMSg", admin_id=6915752059)
    bot.run()

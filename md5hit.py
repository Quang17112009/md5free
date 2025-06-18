import hashlib
import json
import os
import joblib # Không thấy joblib được sử dụng trong mã này, có thể xóa nếu không dùng đến
from telegram import Update # <<< ĐÃ THAY ĐỔI: Import Update trực tiếp từ telegram
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    # Update, # Đã xóa khỏi đây vì đã import ở trên
)
from typing import Dict, Tuple

class MD5CharacterAnalyzer:
    def __init__(self):
        self.weights = {
            '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
            'a': 10, 'b': 11, 'c': 12, 'd': 13, 'e': 14, 'f': 15
        }

    def analyze_md5(self, md5: str) -> Tuple[str, float, Dict]:
        md5 = md5.lower()
        if len(md5) != 32 or not all(c in self.weights for c in md5):
            raise ValueError("Mã MD5 không hợp lệ. Vui lòng nhập mã MD5 gồm 32 ký tự.")

        w1 = sum(self.weights[c] for c in md5[:16])
        w2 = sum(self.weights[c] for c in md5[16:])
        w3 = sum(self.weights[c] for c in md5[::2])
        w4 = sum(self.weights[c] for c in md5[1::2])

        # Công thức tính toán này dựa trên logic bạn cung cấp
        combined = (w1 * 0.4 + w2 * 0.4 + (w3 - w4) * 0.2)
        result = "Tài" if int(combined) % 36 >= 18 else "Xỉu"
        
        # Tính toán độ tin cậy
        # Giá trị càng xa 18 (hoặc 54, 90...) thì độ tin cậy càng cao
        # abs(((combined % 36) - 18) / 18) sẽ cho ra giá trị từ 0 đến 1.
        # 0 khi combined % 36 = 18 (giữa khoảng)
        # 1 khi combined % 36 = 0 hoặc 35 (hai đầu khoảng)
        confidence = round(abs(((combined % 36) - 18) / 18 * 100), 2)


        analysis = {
            "even_digits": sum(1 for c in md5 if c in "02468ace"),
            "odd_digits": sum(1 for c in md5 if c in "13579bdf"),
            "alpha_count": sum(1 for c in md5 if c in "abcdef"),
            "num_count": sum(1 for c in md5 if c in "0123456789"),
            "entropy": round(len(set(md5)) / 16, 2) # Mức độ đa dạng của các ký tự trong chuỗi
        }

        return result, confidence, analysis

class TelegramBot:
    def __init__(self, token: str, admin_id: int):
        self.app = Application.builder().token(token).build()
        self.admin_id = admin_id
        self.analyzer = MD5CharacterAnalyzer()
        self.users: Dict[int, dict] = {}
        self.data_file = "md5hit.json" # Tên file để lưu dữ liệu người dùng
        self.load_user_data()

    def load_user_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    # Đảm bảo tất cả các khóa ID người dùng là số nguyên khi tải từ JSON
                    self.users = {int(k): v for k, v in data.items()}
            except (json.JSONDecodeError, OSError) as e:
                print(f"Lỗi khi tải dữ liệu người dùng: {e}")
                self.users = {} # Khởi tạo rỗng nếu có lỗi khi đọc file
        else:
            self.users = {} # Khởi tạo rỗng nếu file không tồn tại

    def save_user_data(self):
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.users, f, indent=2) # indent=2 để file JSON dễ đọc hơn
        except OSError as e:
            print(f"Lỗi khi lưu dữ liệu người dùng: {e}")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        # Sử dụng full_name, username hoặc first_name theo thứ tự ưu tiên
        username = update.effective_user.full_name or update.effective_user.username or update.effective_user.first_name

        if user_id not in self.users:
            self.users[user_id] = {"balance": 10, "history": [], "first_start": True}
            welcome_msg = (
                f"✨ Chào {username}\n"
                "🤖 Tool Md5 Free by @heheviptool\n"
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
            # Nếu người dùng đã tồn tại, kiểm tra xem đây có phải lần đầu sau khi khởi động bot không
            # và đặt lại first_start = False để không cấp xu lần nữa.
            if self.users[user_id].get("first_start", False): # Nếu có key và giá trị là True
                 self.users[user_id]["first_start"] = False # Đặt lại về False
            
            welcome_msg = (
                f"✨ Chào {username}\n"
                "🤖 Tool Md5 Free by @heheviptool\n"
                "➡️ Gửi mã MD5 để bắt đầu dự đoán\n"
                "🔹 Lệnh Sử Dụng\n"
                ">> /info - Xem Hồ Sơ\n"
                ">> /history - Lịch Sử\n"
                "🔹 Lệnh Admin\n"
                ">> /addxu <id> <xu> - Cộng Xu\n"
                ">> /unxu <id> <xu> - Trừ Xu\n"
                ">> /thongke - Xem Thống Kê User"
            )
            

        self.save_user_data() # Lưu lại dữ liệu người dùng sau khi cập nhật
        await update.message.reply_text(welcome_msg, parse_mode="Markdown")

    async def info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        username = update.effective_user.full_name or update.effective_user.username or update.effective_user.first_name
        # Sử dụng .get() để tránh lỗi nếu user_id chưa có trong self.users
        user_data = self.users.get(user_id, {"balance": 0, "history": [], "first_start": False})

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
        # Chỉ hiển thị 10 mục gần nhất
        for md5, result in user_data["history"][-10:]:
            history_msg += f"Mã MD5: `{md5}` - Dự Đoán: {result}\n"
        history_msg += "\n*Chỉ hiển thị 10 mục gần nhất."

        await update.message.reply_text(history_msg, parse_mode="Markdown")

    async def add_xu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("🚫 Chỉ admin mới có thể sử dụng lệnh này!", parse_mode="Markdown")
            return
        try:
            args = context.args
            if len(args) != 2:
                raise ValueError("Vui lòng nhập đúng định dạng: `/addxu <id> <xu>`")
            target_id, amount = int(args[0]), int(args[1])
            if amount <= 0:
                raise ValueError("Số xu phải lớn hơn 0")

            if target_id not in self.users:
                # Nếu người dùng chưa tồn tại, khởi tạo dữ liệu cho họ
                self.users[target_id] = {"balance": 0, "history": [], "first_start": False}

            self.users[target_id]["balance"] += amount
            self.save_user_data() # Lưu lại dữ liệu sau khi thay đổi
            await update.message.reply_text(
                f"✅ **Đã cộng {amount} xu cho ID {target_id}. Số dư mới: {self.users[target_id]['balance']}**",
                parse_mode="Markdown")
            try:
                # Gửi thông báo trực tiếp đến người dùng bị ảnh hưởng
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"💸 **Bạn vừa được admin cộng {amount} xu. Số dư hiện tại: {self.users[target_id]['balance']}**",
                    parse_mode="Markdown")
            except Exception as e:
                print(f"Không thể gửi thông báo tới người dùng {target_id}: {e}")
                await update.message.reply_text(f"⚠️ Không thể gửi thông báo tới người dùng ID {target_id} (có thể họ chưa bắt đầu bot hoặc đã chặn bot).", parse_mode="Markdown")
        except ValueError as e:
            await update.message.reply_text(f"❌ Lỗi: {e}", parse_mode="Markdown")
        except IndexError: # Bắt lỗi khi không đủ đối số
            await update.message.reply_text("❌ Lỗi: Vui lòng nhập đúng định dạng: `/addxu <id> <xu>`", parse_mode="Markdown")

    async def un_xu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("🚫 Chỉ admin mới có thể sử dụng lệnh này!", parse_mode="Markdown")
            return
        try:
            args = context.args
            if len(args) != 2:
                raise ValueError("Vui lòng nhập đúng định dạng: `/unxu <id> <xu>`")
            target_id, amount = int(args[0]), int(args[1])
            if amount <= 0:
                raise ValueError("Số xu phải lớn hơn 0")
            if target_id not in self.users:
                await update.message.reply_text(f"❌ Người dùng với ID {target_id} không tồn tại trong dữ liệu.", parse_mode="Markdown")
                return
            if self.users[target_id]["balance"] < amount:
                await update.message.reply_text(
                    f"❌ Số dư của ID {target_id} không đủ ({self.users[target_id]['balance']} xu).",
                    parse_mode="Markdown")
                return
            self.users[target_id]["balance"] -= amount
            self.save_user_data() # Lưu lại dữ liệu sau khi thay đổi
            await update.message.reply_text(
                f"✅ Đã trừ {amount} xu từ ID {target_id}. Số dư mới: {self.users[target_id]['balance']}",
                parse_mode="Markdown")
            try:
                # Gửi thông báo trực tiếp đến người dùng bị ảnh hưởng
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"💸 Bạn vừa bị admin trừ {amount} xu. Số dư hiện tại: {self.users[target_id]['balance']}",
                    parse_mode="Markdown")
            except Exception as e:
                print(f"Không thể gửi thông báo tới người dùng {target_id}: {e}")
                await update.message.reply_text(f"⚠️ Không thể gửi thông báo tới người dùng ID {target_id} (có thể họ chưa bắt đầu bot hoặc đã chặn bot).", parse_mode="Markdown")
        except ValueError as e:
            await update.message.reply_text(f"❌ Lỗi: {e}", parse_mode="Markdown")
        except IndexError: # Bắt lỗi khi không đủ đối số
            await update.message.reply_text("❌ Lỗi: Vui lòng nhập đúng định dạng: `/unxu <id> <xu>`", parse_mode="Markdown")

    async def thongke(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("🚫 Chỉ admin mới có thể sử dụng lệnh này!", parse_mode="Markdown")
            return
        if not self.users:
            await update.message.reply_text("📊 Không có dữ liệu người dùng nào được lưu.", parse_mode="Markdown")
            return
            
        stats_msg = "📊 Thống Kê Người Dùng\n\n"
        # Sắp xếp người dùng theo số dư giảm dần
        sorted_users = sorted(self.users.items(), key=lambda item: item[1].get('balance', 0), reverse=True)

        for idx, (user_id, data) in enumerate(sorted_users, 1):
            username = f"Người dùng ID: {user_id}" # Mặc định nếu không lấy được tên
            try:
                # Cố gắng lấy thông tin chat để có tên người dùng thực tế
                chat = await context.bot.get_chat(user_id)
                username = chat.full_name or chat.username or chat.first_name
            except Exception as e:
                print(f"Không thể lấy thông tin chat cho người dùng {user_id}: {e}")
                # Nếu không lấy được, vẫn dùng ID để xác định
            stats_msg += f"{idx}. {username} (ID: {user_id}) - Xu: {data['balance']}\n"
            
            # Giới hạn độ dài tin nhắn để tránh lỗi Telegram API (max 4096 ký tự)
            if len(stats_msg) > 3500 and idx < len(sorted_users): # Nếu tin nhắn quá dài và vẫn còn user
                stats_msg += "\n*...và nhiều người dùng khác. Vui lòng kiểm tra file dữ liệu để xem đầy đủ."
                break # Dừng thêm vào tin nhắn

        await update.message.reply_text(stats_msg, parse_mode="Markdown")

    async def handle_md5(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # Đảm bảo người dùng có dữ liệu trước khi xử lý
        if user_id not in self.users:
            # Nếu người dùng chưa bắt đầu bot hoặc dữ liệu bị mất, khởi tạo họ với 0 xu
            self.users[user_id] = {"balance": 0, "history": [], "first_start": False}
            self.save_user_data()
            await update.message.reply_text("Chào mừng bạn! Vui lòng sử dụng lệnh /start để nhận xu miễn phí và bắt đầu.", parse_mode="Markdown")
            return

        # Kiểm tra số xu trước khi phân tích
        if self.users[user_id]["balance"] < 1:
            await update.message.reply_text("❌ Bạn không đủ xu để dự đoán (cần 1 xu/lần). Vui lòng liên hệ admin để nạp thêm hoặc chờ nhận xu miễn phí.", parse_mode="Markdown")
            return
            
        md5_input = update.message.text.strip()
        try:
            result, confidence, analysis = self.analyzer.analyze_md5(md5_input)
            
            # Trừ xu sau khi phân tích thành công
            self.users[user_id]["balance"] -= 1
            
            # Giới hạn lịch sử để tránh file quá lớn và tải/lưu chậm
            if len(self.users[user_id]["history"]) >= 50: # Giữ 50 mục gần nhất
                self.users[user_id]["history"].pop(0) # Xóa mục cũ nhất (FIFO)
            self.users[user_id]["history"].append((md5_input, result))
            
            self.save_user_data() # Lưu lại dữ liệu sau khi trừ xu và thêm lịch sử

            response = (
                "🎰 KẾT QUẢ PHÂN TÍCH 🎰\n\n"
                f"🔢 Mã MD5: `{md5_input}`\n"
                f"🎯 *Dự đoán*: **{result}** ({confidence}%)\n\n" # In đậm kết quả
                f"🔍 *Phân Tích*:\n"
                f"▫️ Chữ số chẵn: {analysis['even_digits']}, lẻ: {analysis['odd_digits']}\n"
                f"▫️ Ký tự chữ (a-f): {analysis['alpha_count']}, số (0-9): {analysis['num_count']}\n"
                f"▫️ Mức phân tán (entropy): {analysis['entropy']}\n\n"
                f"💰 Xu còn lại: {self.users[user_id]['balance']}"
            )
            await update.message.reply_text(response, parse_mode="Markdown")
        except ValueError as e:
            await update.message.reply_text(f"❌ Lỗi: {e}", parse_mode="Markdown")
        except Exception as e: # Bắt các lỗi không mong muốn khác
            print(f"Lỗi không xác định khi xử lý MD5 cho user {user_id}: {e}")
            await update.message.reply_text(f"Đã xảy ra lỗi không mong muốn khi xử lý mã MD5 của bạn. Vui lòng thử lại sau.", parse_mode="Markdown")


    def run(self):
        # Thêm các handlers cho các lệnh
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("info", self.info))
        self.app.add_handler(CommandHandler("history", self.history))
        self.app.add_handler(CommandHandler("addxu", self.add_xu))
        self.app.add_handler(CommandHandler("unxu", self.un_xu))
        self.app.add_handler(CommandHandler("thongke", self.thongke))
        
        # MessageHandler phải được thêm SAU CommandHandlers để các lệnh được ưu tiên
        # filters.TEXT & ~filters.COMMAND nghĩa là chỉ xử lý tin nhắn văn bản KHÔNG phải là lệnh
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_md5))
        
        print("Bot đang chạy...")
        self.app.run_polling() # Bắt đầu polling để nhận tin nhắn

if __name__ == "__main__":
    # >>> QUAN TRỌNG: Thay thế TOKEN và ADMIN_ID của bạn vào đây <<<
    # Tốt nhất là lấy từ biến môi trường để đảm bảo an toàn và dễ quản lý
    # Ví dụ: TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    # ADMIN_ID = int(os.getenv("TELEGRAM_ADMIN_ID"))

    # Đặt TOKEN và ADMIN_ID của bot của bạn vào đây
    # Ví dụ:
    # BOT_TOKEN = "YOUR_BOT_TOKEN_HERE" 
    # YOUR_ADMIN_ID = 123456789 # Thay bằng ID Telegram của bạn
    
    # Do bạn đã cung cấp token và admin_id trong ảnh, tôi sẽ dùng chúng:
    BOT_TOKEN = "7749105278:AAF4q2n-WTZEsMFBXEvrhuYFSMVjkoeXMSg"
    ADMIN_ID = 6915752059 

    bot = TelegramBot(token=BOT_TOKEN, admin_id=ADMIN_ID)
    bot.run()

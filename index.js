const express = require("express");
const TelegramBot = require("node-telegram-bot-api");
const crypto = require("crypto");

const app = express();

// ===== CONFIG =====
const BOT_TOKEN = "8751204704:AAHVLFWRt1hQvz3HxnwDNt7IRhA4eZYEfjg"
const DOMAIN = "https://librariannudebot-production.up.railway.app" // ví dụ: https://abc.up.railway.app
const PORT = process.env.PORT || 3000;

if (!BOT_TOKEN || !DOMAIN) {
  console.error("Thiếu BOT_TOKEN hoặc DOMAIN");
  process.exit(1);
}

// ===== BOT (WEBHOOK) =====
const bot = new TelegramBot(BOT_TOKEN);
const WEBHOOK_PATH = `/bot${BOT_TOKEN}`;

bot.setWebHook(`${DOMAIN}${WEBHOOK_PATH}`);

app.use(express.json());
app.post(WEBHOOK_PATH, (req, res) => {
  bot.processUpdate(req.body);
  res.sendStatus(200);
});

// ===== DB tạm =====
const users = {};
const tasks = {};

// ===== HELPER =====
function createToken(userId) {
  return crypto
    .createHash("sha256")
    .update(userId + Date.now() + Math.random())
    .digest("hex");
}

// ===== BOT HANDLER =====
bot.on("message", (msg) => {
  const id = msg.from.id;
  const text = msg.text;

  if (!users[id]) users[id] = { points: 0 };

  // ===== /start =====
  if (text === "/start") {
    return bot.sendMessage(
      id,
      `Điểm: ${users[id].points}\nGõ /task để nhận nhiệm vụ`
    );
  }

  // ===== /task =====
  if (text === "/task") {
    const token = createToken(id);

    tasks[token] = {
      user_id: id,
      status: "created",
      created_at: Date.now()
    };

    const link = `${DOMAIN}/go?token=${token}`;

    return bot.sendMessage(
      id,
      `Nhiệm vụ:\n${link}\n\nSau khi xong sẽ quay lại bot`
    );
  }

  // ===== deep link nhận thưởng =====
  if (text && text.startsWith("/start ")) {
    const token = text.split(" ")[1];
    const task = tasks[token];

    if (!task) return bot.sendMessage(id, "Token sai");

    if (task.user_id !== id)
      return bot.sendMessage(id, "Không phải nhiệm vụ của bạn");

    if (task.status !== "verified")
      return bot.sendMessage(id, "Bạn chưa hoàn thành nhiệm vụ");

    if (task.status === "claimed")
      return bot.sendMessage(id, "Đã nhận rồi");

    users[id].points += 10;
    task.status = "claimed";

    return bot.sendMessage(
      id,
      `+10 điểm\nTổng: ${users[id].points}`
    );
  }
});

// ===== SERVER =====

// bước 1: click link
app.get("/go", (req, res) => {
  const { token } = req.query;
  const task = tasks[token];

  if (!task) return res.send("Invalid token");

  task.status = "clicked";

  // ⚠️ đổi link nhiệm vụ ở đây
  res.redirect("https://oklink.cfd/G89W5K");
});

// bước 2: hoàn thành (bạn phải redirect về đây)
app.get("/complete", (req, res) => {
  const { token } = req.query;
  const task = tasks[token];

  if (!task) return res.send("Invalid");

  const time = Date.now() - task.created_at;

  if (time < 10000) {
    return res.send("Quá nhanh (nghi gian lận)");
  }

  task.status = "verified";

  res.redirect(`https://t.me/YOUR_BOT_USERNAME?start=${token}`);
});

app.get("/", (req, res) => {
  res.send("Bot is running");
});

app.listen(PORT, () => {
  console.log("Server running on port", PORT);
});

"""Telegram gateway untuk autokeren.

Fitur:
- Satu chat Telegram = satu session autokeren
- Typing animation saat agent berpikir
- Approval tool via inline button
- Pesan panjang dipecah jadi beberapa bubble jika perlu
"""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update  # type: ignore[import]
from telegram.constants import ChatAction  # type: ignore[import]
from telegram.ext import (  # type: ignore[import]
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from autokeren.agent import Agent
from autokeren.cli import build_registry
from autokeren.config import load_config
from autokeren.memory import MemoryManager


class TelegramSession:
    """Wrapper sesi autokeren untuk satu chat Telegram."""

    def __init__(self, chat_id: int, agent: Agent):
        self.chat_id = chat_id
        self.agent = agent
        self.pending_approval: dict[str, Any] | None = None
        self._approval_event: asyncio.Event | None = None
        self._send_approval_request: Any = None

    def is_allowed(self, username: str | None, allowed: list[str]) -> bool:
        if not allowed:
            return True
        if username and username.lower() in {u.lower() for u in allowed}:
            return True
        return False


class TelegramGateway:
    """Gateway Telegram yang pakai python-telegram-bot v20+."""

    def __init__(
        self,
        token: str,
        project_root: str,
        config_path: str | None = None,
        allowed_usernames: list[str] | None = None,
    ):
        self.token = token
        self.project_root = project_root
        self.config_path = config_path
        self.allowed_usernames = allowed_usernames or []
        self.sessions: dict[int, TelegramSession] = {}
        self._lock = asyncio.Lock()

    async def _get_or_create_session(self, chat_id: int) -> TelegramSession:
        async with self._lock:
            if chat_id not in self.sessions:
                cfg = load_config(Path(self.config_path) if self.config_path else None)
                memory = MemoryManager(self.project_root)
                reg = build_registry(cfg, Path(self.project_root), memory)
                agent = Agent(cfg, reg, self.project_root, memory=memory)
                session = TelegramSession(chat_id, agent)
                session._approval_event = asyncio.Event()
                self._bind_permission_callback(session)
                self.sessions[chat_id] = session
            return self.sessions[chat_id]

    def _bind_permission_callback(self, session: TelegramSession) -> None:
        """Pasang callback approval ke Telegram inline keyboard."""

        async def _ask_permission(name: str, desc: str, args: dict[str, Any]) -> bool:
            if session._approval_event is None:
                return True
            req_id = str(uuid.uuid4())[:8]
            session.pending_approval = {
                "req_id": req_id,
                "tool_name": name,
                "description": desc,
                "args": args,
                "approved": False,
            }
            session._approval_event.clear()

            if hasattr(session, "_send_approval_request") and session._send_approval_request:
                await session._send_approval_request(name, desc, req_id)

            try:
                await asyncio.wait_for(session._approval_event.wait(), timeout=300.0)
            except asyncio.TimeoutError:
                return False
            return bool(session.pending_approval.get("approved", False))

        session.agent.permission_callback = _ask_permission  # type: ignore[assignment]

    def start(self) -> None:
        application = Application.builder().token(self.token).build()
        application.add_handler(CommandHandler("start", self._cmd_start))
        application.add_handler(CommandHandler("reset", self._cmd_reset))
        application.add_handler(CommandHandler("sessions", self._cmd_sessions))
        application.add_handler(CallbackQueryHandler(self._handle_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
        print("Telegram gateway berjalan. Tekan Ctrl+C untuk berhenti.")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat:
            return
        chat_id = update.effective_chat.id
        await context.bot.send_message(
            chat_id=chat_id,
            text="Halo! Saya autokeren via Telegram. Ketik apa saja untuk mulai.",
        )

    async def _cmd_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat:
            return
        chat_id = update.effective_chat.id
        session = await self._get_or_create_session(chat_id)
        session.agent.reset()
        await context.bot.send_message(chat_id=chat_id, text="Sesi direset.")

    async def _cmd_sessions(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat:
            return
        chat_id = update.effective_chat.id
        session = await self._get_or_create_session(chat_id)
        sessions = session.agent.sessions.list()
        if not sessions:
            await context.bot.send_message(chat_id=chat_id, text="Belum ada session tersimpan.")
            return
        lines = ["Saved sessions:"]
        for s in sessions[:10]:
            lines.append(f"  {s['id']} — {s['name']}")
        await context.bot.send_message(chat_id=chat_id, text="\n".join(lines))

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat or not update.message or not update.message.text:
            return
        chat_id = update.effective_chat.id
        username = update.effective_user.username if update.effective_user else None
        text = update.message.text

        session = await self._get_or_create_session(chat_id)
        allowed = session.is_allowed(username, self.allowed_usernames)
        if not allowed:
            await context.bot.send_message(chat_id=chat_id, text="Akses ditolak.")
            return

        session._send_approval_request = lambda name, desc, req_id: self._send_approval(
            context, chat_id, name, desc, req_id
        )

        stop_typing = asyncio.Event()

        async def typing_loop() -> None:
            while not stop_typing.is_set():
                try:
                    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                except Exception:
                    pass
                try:
                    await asyncio.wait_for(stop_typing.wait(), timeout=4.0)
                except asyncio.TimeoutError:
                    continue

        typing_task = asyncio.create_task(typing_loop())

        response_text = ""
        try:
            chunks: list[str] = []
            session.agent.on_chunk = chunks.append
            resp = await asyncio.get_event_loop().run_in_executor(None, session.agent.run, text)
            response_text = resp.content or ""
            if not response_text and chunks:
                response_text = "".join(chunks)
        finally:
            stop_typing.set()
            session.agent.on_chunk = None
            await typing_task

        await self._send_long_message(context, chat_id, response_text)

    async def _send_approval(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: int,
        tool_name: str,
        description: str,
        req_id: str,
    ) -> None:
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Izinkan", callback_data=f"approve:{req_id}"),
                    InlineKeyboardButton("❌ Tolak", callback_data=f"deny:{req_id}"),
                ]
            ]
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Tool '{tool_name}' meminta izin:\n{description}",
            reply_markup=keyboard,
        )

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query or not update.effective_chat:
            return
        await query.answer()
        data = query.data or ""
        chat_id = update.effective_chat.id
        session = await self._get_or_create_session(chat_id)

        pending = session.pending_approval
        if pending is None:
            return

        if data.startswith("approve:"):
            req_id = data.split(":", 1)[1]
            if pending.get("req_id") == req_id:
                pending["approved"] = True
                if session._approval_event:
                    session._approval_event.set()
                await query.edit_message_text(text=f"✅ Disetujui: {pending['tool_name']}")
        elif data.startswith("deny:"):
            req_id = data.split(":", 1)[1]
            if pending.get("req_id") == req_id:
                pending["approved"] = False
                if session._approval_event:
                    session._approval_event.set()
                await query.edit_message_text(text=f"❌ Ditolak: {pending['tool_name']}")

    async def _send_long_message(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str) -> None:
        """Kirim pesan panjang dengan split jika melebihi limit Telegram."""
        if not text:
            return
        for i in range(0, len(text), 4000):
            chunk = text[i : i + 4000]
            await context.bot.send_message(chat_id=chat_id, text=chunk)


def run_telegram_gateway(
    token: str,
    project_root: str,
    config_path: str | None = None,
    allowed_usernames: list[str] | None = None,
) -> None:
    gateway = TelegramGateway(token, project_root, config_path, allowed_usernames)
    gateway.start()
# ak:ecfb59effeb2a6b0

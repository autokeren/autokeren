"""TUI (Text User Interface) untuk autokeren berbasis Textual dengan dukungan Multi-Bahasa."""
from __future__ import annotations

import threading
import queue
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll, Container
from textual.widgets import Static, Input, OptionList
from textual.screen import ModalScreen
from textual.binding import Binding
from textual.events import Resize
from rich.markdown import Markdown
from rich.text import Text

from autokeren.agent import Agent
from autokeren.config import Config
from autokeren.models.base import ModelResponse
from autokeren.ui import _format_tool_call, _summarize_tool_result

# ------------------------------------------------------------------ #
# Sistem Multi-Bahasa (i18n)
# ------------------------------------------------------------------ #

LANGUAGES = {
    "id": "Bahasa Indonesia",
    "en": "English",
    "zh": "中文 (Chinese)",
    "ja": "日本語 (Japanese)",
    "de": "Deutsch (German)",
    "ar": "العربية (Arabic)",
    "es": "Español (Spanish)",
    "pt": "Português (Portuguese)",
}

TRANSLATIONS = {
    "en": {
        "user_label": "you",
        "interrupted_msg": "🛑 AI execution cancelled by user.",
        "ctrlc_desc": "Cancel/Stop active AI process",
        "welcome_sub": "Type your question below, or press [bold]F1[/bold] for command help.",
        "status_title": "STATUS",
        "model": "Model",
        "auth": "Auth",
        "tokens": "Tokens",
        "remaining_tokens": "Rem. Tok",
        "neurons": "Neurons",
        "active": "Active",
        "session": "Session",
        "temp": "Temp",
        "maxtok": "MaxTok",
        "pmode": "P.Mode",
        "mcalls": "M.Calls",
        "click_change_model": "Click here to change model",
        "click_change_lang": "Click here to change language",
        "lang": "Lang",
        "allowed_all": "All tools are allowed for this session.",
        "denied_tool": "Tool denied by user.",
        "allowed_tool": "Tool [bold cyan]{name}[/bold cyan] allowed.",
        "model_changed": "⚡ Active AI model changed to: [bold cyan]{name}[/bold cyan]",
        "denied_tool_msg": "Tool [bold red]{name}[/bold red] denied.",
        "approved_plan": "Plan approved.",
        "rejected_plan": "Plan rejected.",
        "reset_success": "Session and tool permissions successfully reset.",
        "compacting": "Compacting conversation context...",
        "compact_success": "Compacted context successfully.",
        "compact_fail": "Compact failed: {error}",
        "save_success": "Session '{name}' saved. ID: {sid}",
        "save_fail": "Save failed: {error}",
        "resume_fail": "Resume failed: {error}",
        "no_sessions": "No saved sessions found.",
        "sessions_title": "SAVED SESSIONS:",
        "unknown_cmd": "Unknown command: {cmd}",
        "mikir": "thinking",
        "help_title": "KEY BINDINGS & SLASH COMMANDS HELP",
        "shortcuts": "Shortcuts:",
        "slash_commands_label": "Slash Commands:",
        "f1_desc": "This help menu",
        "f2_desc": "Display & change active AI model",
        "f3_desc": "Reset conversation session",
        "f4_desc": "Copy last AI response to clipboard",
        "f5_desc": "Compact context window history",
        "f6_desc": "Change active UI language",
        "ctrlq_desc": "Exit autokeren cleanly",
        "updown_desc": "Navigate input history (previous/next)",
        "export_success": "Chat exported to: [bold cyan]{path}[/bold cyan]",
        "export_empty": "No messages to export.",
        "last_copied": "✓ Last response successfully copied to clipboard.",
        "copy_fail": "Failed to copy to clipboard: {error}",
        "no_last_msg": "No assistant response to copy.",
        "confirm_title": "TOOL EXECUTION PERMISSION",
        "confirm_sub": "⚡ Run [bold cyan]{label}[/bold cyan]? — {desc}",
        "opt_allow_once": "✓ Allow Once",
        "opt_allow_all": "⚡ Allow All Tools in This Session",
        "opt_deny": "✗ Deny Execution",
        "approve_title": "APPROVE WORK PLAN?",
        "opt_approve": "✓ Approve Plan",
        "opt_reject": "✗ Reject Plan",
        "model_title": "SELECT AI MODEL",
        "lang_title": "SELECT LANGUAGE",
        "thinking_placeholder": "Thinking...",
        "input_placeholder": "✍️ Type a message here...",
        "pypi_update": "⚡ A new version of autokeren is available: [bold cyan]v{version}[/bold cyan]. Run [bold green]pipx upgrade autokeren[/bold green] to update.",
    },
    "id": {
        "user_label": "kamu",
        "interrupted_msg": "🛑 Eksekusi AI dibatalkan oleh pengguna.",
        "ctrlc_desc": "Batalkan/Stop proses AI aktif",
        "welcome_sub": "Ketik pertanyaan kamu di bawah, atau tekan [bold]F1[/bold] untuk bantuan perintah.",
        "status_title": "STATUS",
        "model": "Model",
        "auth": "Auth",
        "tokens": "Tokens",
        "remaining_tokens": "Sisa Tok",
        "neurons": "Neurons",
        "active": "Active",
        "session": "Session",
        "temp": "Temp",
        "maxtok": "MaxTok",
        "pmode": "P.Mode",
        "mcalls": "M.Calls",
        "click_change_model": "Klik di sini untuk ganti model",
        "click_change_lang": "Klik di sini untuk ganti bahasa",
        "lang": "Lang",
        "allowed_all": "Semua tool diizinkan untuk sesi ini.",
        "denied_tool": "Tool ditolak oleh user.",
        "allowed_tool": "Tool [bold cyan]{name}[/bold cyan] diizinkan.",
        "model_changed": "⚡ Model AI aktif diganti ke: [bold cyan]{name}[/bold cyan]",
        "denied_tool_msg": "Tool [bold red]{name}[/bold red] ditolak.",
        "approved_plan": "Rencana kerja disetujui.",
        "rejected_plan": "Rencana kerja ditolak.",
        "reset_success": "Sesi dan izin tool berhasil direset.",
        "compacting": "Meringkas context percakapan...",
        "compact_success": "Context berhasil diringkas.",
        "compact_fail": "Compact gagal: {error}",
        "save_success": "Sesi '{name}' disimpan. ID: {sid}",
        "save_fail": "Save gagal: {error}",
        "resume_fail": "Resume gagal: {error}",
        "no_sessions": "Belum ada sesi yang disimpan.",
        "sessions_title": "SESI YANG DISIMPAN:",
        "unknown_cmd": "Perintah tidak dikenal: {cmd}",
        "mikir": "mikir",
        "help_title": "BANTUAN KEY BINDING & SLASH COMMANDS",
        "shortcuts": "Tombol Pintas:",
        "slash_commands_label": "Perintah Slash:",
        "f1_desc": "Bantuan ini",
        "f2_desc": "Tampilkan & Ganti Model aktif",
        "f3_desc": "Reset Sesi percakapan",
        "f4_desc": "Salin respon terakhir AI ke clipboard",
        "f5_desc": "Compact Context (ringkas percakapan lama)",
        "f6_desc": "Ganti bahasa antarmuka UI",
        "ctrlq_desc": "Keluar dari autokeren dengan aman",
        "updown_desc": "Navigasi history input (sebelumnya/selanjutnya)",
        "export_success": "Chat diekspor ke: [bold cyan]{path}[/bold cyan]",
        "export_empty": "Tidak ada pesan untuk diekspor.",
        "last_copied": "✓ Respon terakhir berhasil disalin ke clipboard.",
        "copy_fail": "Gagal menyalin ke clipboard: {error}",
        "no_last_msg": "Belum ada respon assistant untuk disalin.",
        "confirm_title": "IZIN EKSEKUSI TOOL",
        "confirm_sub": "⚡ Panggil [bold cyan]{label}[/bold cyan]? — {desc}",
        "opt_allow_once": "✓ Izinkan Sekali",
        "opt_allow_all": "⚡ Izinkan Semua Tool Sesi Ini",
        "opt_deny": "✗ Tolak Eksekusi",
        "approve_title": "SETUJUI RENCANA KERJA?",
        "opt_approve": "✓ Setujui Rencana",
        "opt_reject": "✗ Tolak Rencana",
        "model_title": "PILIH MODEL AI",
        "lang_title": "PILIH BAHASA / SELECT LANGUAGE",
        "thinking_placeholder": "Sedang berpikir...",
        "input_placeholder": "✍️ Ketik pesan di sini...",
        "pypi_update": "⚡ Versi baru autokeren tersedia: [bold cyan]v{version}[/bold cyan]. Jalankan [bold green]pipx upgrade autokeren[/bold green] untuk memperbarui.",
    },
    "zh": {
        "user_label": "你",
        "interrupted_msg": "🛑 用户已取消 AI 执行。",
        "ctrlc_desc": "取消/停止当前 AI 进程",
        "welcome_sub": "在下方输入您的问题，或按 [bold]F1[/bold] 获取命令帮助。",
        "status_title": "状态",
        "model": "模型",
        "auth": "认证",
        "tokens": "Token数",
        "remaining_tokens": "剩余Token",
        "neurons": "配额 (Neurons)",
        "active": "当前目录",
        "session": "会话消息",
        "temp": "温度 (Temp)",
        "maxtok": "最大Token",
        "pmode": "计划模式",
        "mcalls": "工具调用",
        "click_change_model": "点击此处更改模型",
        "click_change_lang": "点击此处更改语言",
        "lang": "语言",
        "allowed_all": "此会话允许所有工具调用。",
        "denied_tool": "用户拒绝了工具执行。",
        "allowed_tool": "工具 [bold cyan]{name}[/bold cyan] 已允许执行。",
        "model_changed": "⚡ 活跃 AI 模型已切换为: [bold cyan]{name}[/bold cyan]",
        "denied_tool_msg": "工具 [bold red]{name}[/bold red] 已被拒绝。",
        "approved_plan": "工作计划已批准。",
        "rejected_plan": "工作计划已拒绝。",
        "reset_success": "会话和工具授权已重置。",
        "compacting": "正在压缩对话上下文...",
        "compact_success": "成功压缩上下文。",
        "compact_fail": "压缩失败: {error}",
        "save_success": "会话 '{name}' 已保存。ID: {sid}",
        "save_fail": "保存失败: {error}",
        "resume_fail": "恢复失败: {error}",
        "no_sessions": "未发现已保存的会话。",
        "sessions_title": "已保存的会话:",
        "unknown_cmd": "未知命令: {cmd}",
        "mikir": "思考中",
        "help_title": "按键绑定与斜杠命令帮助",
        "shortcuts": "快捷键:",
        "slash_commands_label": "斜杠命令:",
        "f1_desc": "显示此帮助菜单",
        "f2_desc": "显示并更改当前 AI 模型",
        "f3_desc": "重置当前对话会话",
        "f4_desc": "将 AI 的最后一条回复复制到剪贴板",
        "f5_desc": "压缩上下文窗口历史记录",
        "f6_desc": "更改当前界面语言",
        "ctrlq_desc": "退出 autokeren",
        "updown_desc": "导航输入历史记录（上/下）",
        "export_success": "聊天记录已导出到: [bold cyan]{path}[/bold cyan]",
        "export_empty": "没有可导出的消息。",
        "last_copied": "✓ 最后的回复已成功复制到剪贴板。",
        "copy_fail": "复制到剪贴板失败: {error}",
        "no_last_msg": "没有可复制的回复。",
        "confirm_title": "工具执行权限请求",
        "confirm_sub": "⚡ 是否执行 [bold cyan]{label}[/bold cyan]? — {desc}",
        "opt_allow_once": "✓ 允许一次",
        "opt_allow_all": "⚡ 在此会话中允许所有工具",
        "opt_deny": "✗ 拒绝执行",
        "approve_title": "批准工作计划？",
        "opt_approve": "✓ 批准计划",
        "opt_reject": "✗ 拒绝计划",
        "model_title": "选择 AI 模型",
        "lang_title": "选择界面语言",
        "thinking_placeholder": "思考中...",
        "input_placeholder": "✍️ 在此处输入消息...",
    },
    "ja": {
        "user_label": "あなた",
        "interrupted_msg": "🛑 ユーザーによって AI 実行がキャンセルされました。",
        "ctrlc_desc": "アクティブな AI プロセスをキャンセル/停止",
        "welcome_sub": "質問を以下に入力するか、[bold]F1[/bold] キーでコマンドのヘルプを表示します。",
        "status_title": "ステータス",
        "model": "モデル",
        "auth": "認証",
        "tokens": "トークン",
        "remaining_tokens": "残トークン",
        "neurons": "ニューロン",
        "active": "アクティブ",
        "session": "セッション",
        "temp": "温度",
        "maxtok": "最大トークン",
        "pmode": "計画モード",
        "mcalls": "呼出数",
        "click_change_model": "ここをクリックしてモデルを変更",
        "click_change_lang": "ここをクリックして言語を変更",
        "lang": "言語",
        "allowed_all": "このセッションですべてのツール実行が許可されました。",
        "denied_tool": "ツール実行がユーザーに拒否されました。",
        "allowed_tool": "ツール [bold cyan]{name}[/bold cyan] が許可されました。",
        "model_changed": "⚡ アクティブな AI モデルが変更されました: [bold cyan]{name}[/bold cyan]",
        "denied_tool_msg": "ツール [bold red]{name}[/bold red] が拒否されました。",
        "approved_plan": "計画が承認されました。",
        "rejected_plan": "計画が却下されました。",
        "reset_success": "セッションとツール実行の権限がリセットされました。",
        "compacting": "コンテキストを圧縮中...",
        "compact_success": "コンテキストの圧縮に成功しました。",
        "compact_fail": "圧縮失敗: {error}",
        "save_success": "セッション '{name}' が保存されました。ID: {sid}",
        "save_fail": "保存失敗: {error}",
        "resume_fail": "復元失敗: {error}",
        "no_sessions": "保存されたセッションが見つかりません。",
        "sessions_title": "保存されたセッション:",
        "unknown_cmd": "不明なコマンド: {cmd}",
        "mikir": "考え中",
        "help_title": "キーバインディングとスラッシュコマンドのヘルプ",
        "shortcuts": "ショートカットキー:",
        "slash_commands_label": "スラッシュコマンド:",
        "f1_desc": "このヘルプを表示",
        "f2_desc": "AI モデル의 표시と変更",
        "f3_desc": "会話セッションのリセット",
        "f4_desc": "最後の AI の応答をクリップボードにコピー",
        "f5_desc": "コンテキスト履歴を圧縮",
        "f6_desc": "UI 表示言語の変更",
        "ctrlq_desc": "アプリケーションを安全に終了",
        "updown_desc": "入力履歴をナビゲートする（前/次）",
        "export_success": "チャットをエクスポートしました: [bold cyan]{path}[/bold cyan]",
        "export_empty": "エクスポートするメッセージがありません。",
        "last_copied": "✓ 最後の応答がクリップボードにコピーされました。",
        "copy_fail": "コピー失敗: {error}",
        "no_last_msg": "コピーする応答がありません。",
        "confirm_title": "ツールの実行許可確認",
        "confirm_sub": "⚡ [bold cyan]{label}[/bold cyan] を実行しますか？ — {desc}",
        "opt_allow_once": "✓ 1回許可",
        "opt_allow_all": "⚡ このセッションですべて許可",
        "opt_deny": "✗ 実行を拒否",
        "approve_title": "作業計画を承認しますか？",
        "opt_approve": "✓ 計画を承認",
        "opt_reject": "✗ 計画を却下",
        "model_title": "AI モデルの選択",
        "lang_title": "言語を選択してください",
        "thinking_placeholder": "考え中...",
        "input_placeholder": "✍️ メッセージを入力...",
    },
    "de": {
        "user_label": "du",
        "interrupted_msg": "🛑 AI-Ausführung vom Benutzer abgebrochen.",
        "ctrlc_desc": "Aktiven AI-Prozess abbrechen/stoppen",
        "welcome_sub": "Geben Sie Ihre Frage unten ein oder drücken Sie [bold]F1[/bold] für Befehlshilfe.",
        "status_title": "STATUS",
        "model": "Modell",
        "auth": "Auth",
        "tokens": "Tokens",
        "remaining_tokens": "Verbl. Tok.",
        "neurons": "Neurons",
        "active": "Aktiv",
        "session": "Sitzung",
        "temp": "Temp",
        "maxtok": "MaxTok",
        "pmode": "P.Modus",
        "mcalls": "M.Aufrufe",
        "click_change_model": "Klicken Sie hier, um das Modell zu ändern",
        "click_change_lang": "Klicken Sie hier, um die Sprache zu ändern",
        "lang": "Sprache",
        "allowed_all": "Alle Werkzeuge sind für diese Sitzung zugelassen.",
        "denied_tool": "Werkzeugausführung vom Benutzer abgelehnt.",
        "allowed_tool": "Werkzeug [bold cyan]{name}[/bold cyan] zugelassen.",
        "model_changed": "⚡ Aktives KI-Modell geändert zu: [bold cyan]{name}[/bold cyan]",
        "denied_tool_msg": "Werkzeug [bold red]{name}[/bold red] abgelehnt.",
        "approved_plan": "Arbeitsplan genehmigt.",
        "rejected_plan": "Arbeitsplan abgelehnt.",
        "reset_success": "Sitzung und Werkzeugberechtigungen erfolgreich zurückgesetzt.",
        "compacting": "Kontext wird komprimiert...",
        "compact_success": "Kontext erfolgreich komprimiert.",
        "compact_fail": "Komprimierung fehlgeschlagen: {error}",
        "save_success": "Sitzung '{name}' gespeichert. ID: {sid}",
        "save_fail": "Speichern fehlgeschlagen: {error}",
        "resume_fail": "Wiederherstellung fehlgeschlagen: {error}",
        "no_sessions": "Keine gespeicherten Sitzungen gefunden.",
        "sessions_title": "GESPEICHERTE SITZUNGEN:",
        "unknown_cmd": "Unbekannter Befehl: {cmd}",
        "mikir": "nachdenken",
        "help_title": "TASTENBELEGUNG & SLASH-BEFEHLE HILFE",
        "shortcuts": "Tastaturkürzel:",
        "slash_commands_label": "Slash-Befehle:",
        "f1_desc": "Dieses Hilfemenü",
        "f2_desc": "Aktives AI-Modell anzeigen & ändern",
        "f3_desc": "Konversationssitzung zurücksetzen",
        "f4_desc": "Letzte AI-Antwort in die Zwischenablage kopieren",
        "f5_desc": "Kontexthistorie komprimieren",
        "f6_desc": "Aktive UI-Sprache ändern",
        "ctrlq_desc": "autokeren sauber beenden",
        "updown_desc": "Eingabeverlauf navigieren (vorher/nächste)",
        "export_success": "Chat exportiert nach: [bold cyan]{path}[/bold cyan]",
        "export_empty": "Keine Nachrichten zum Exportieren.",
        "last_copied": "✓ Letzte Antwort erfolgreich in die Zwischenablage kopiert.",
        "copy_fail": "Kopieren fehlgeschlagen: {error}",
        "no_last_msg": "Keine Antwort zum Kopieren vorhanden.",
        "confirm_title": "WERKZEUGAUSFÜHRUNGSRECHTE",
        "confirm_sub": "⚡ [bold cyan]{label}[/bold cyan] ausführen? — {desc}",
        "opt_allow_once": "✓ Einmalig zulassen",
        "opt_allow_all": "⚡ Alle Werkzeuge in dieser Sitzung zulassen",
        "opt_deny": "✗ Ausführung ablehnen",
        "approve_title": "ARBEITSPLAN GENEHMIGEN?",
        "opt_approve": "✓ Plan genehmigen",
        "opt_reject": "✗ Plan ablehnen",
        "model_title": "AI-MODELL AUSWÄHLEN",
        "lang_title": "SPRACHE AUSWÄHLEN",
        "thinking_placeholder": "Nachdenken...",
        "input_placeholder": "✍️ Nachricht hier eingeben...",
    },
    "ar": {
        "user_label": "أنت",
        "interrupted_msg": "🛑 تم إلغاء تشغيل الذكاء الاصطناعي بواسطة المستخدم.",
        "ctrlc_desc": "إلغاء/إيقاف عملية الذكاء الاصطناعي النشطة",
        "welcome_sub": "اكتب سؤالك أدناه، أو اضغط على [bold]F1[/bold] للحصول على مساعدة بشأن الأوامر.",
        "status_title": "الحالة",
        "model": "النموذج",
        "auth": "المصادقة",
        "tokens": "الرموز",
        "remaining_tokens": "المتبقي",
        "neurons": "الحصص",
        "active": "النشط",
        "session": "الجلسة",
        "temp": "الحرارة",
        "maxtok": "أقصى رموز",
        "pmode": "وضع الخطة",
        "mcalls": "الاتصالات",
        "click_change_model": "انقر هنا لتغيير النموذج",
        "click_change_lang": "انقر هنا لتغيير اللغة",
        "lang": "اللغة",
        "allowed_all": "تم السماح بجميع الأدوات لهذه الجلسة.",
        "denied_tool": "رفض المستخدم تشغيل الأداة.",
        "allowed_tool": "تم السماح بالأداة [bold cyan]{name}[/bold cyan].",
        "model_changed": "⚡ تم تغيير نموذج الذكاء الاصطناعي النشط إلى: [bold cyan]{name}[/bold cyan]",
        "denied_tool_msg": "تم رفض الأداة [bold red]{name}[/bold red].",
        "approved_plan": "تمت الموافقة على خطة العمل.",
        "rejected_plan": "تم رفض خطة العمل.",
        "reset_success": "تم إعادة تعيين الجلسة وأذونات الأدوات بنجاح.",
        "compacting": "جاري ضغط سياق المحادثة...",
        "compact_success": "تم ضغط السياق بنجاح.",
        "compact_fail": "فشل الضغط: {error}",
        "save_success": "تم حفظ الجلسة '{name}'. المعرف: {sid}",
        "save_fail": "فشل الحفظ: {error}",
        "resume_fail": "فشلت الاستعادة: {error}",
        "no_sessions": "لم يتم العثور على جلسات محفوظة.",
        "sessions_title": "الجلسات المحفوظة:",
        "unknown_cmd": "أمر غير معروف: {cmd}",
        "mikir": "جاري التفكير",
        "help_title": "مساعدة أزرار الاختصار وأوامر سلاش",
        "shortcuts": "الاختصارات:",
        "slash_commands_label": "أوامر سلاش:",
        "f1_desc": "قائمة المساعدة هذه",
        "f2_desc": "عرض وتغيير نموذج الذكاء الاصطناعي النشط",
        "f3_desc": "إعادة تعيين جلسة المحادثة",
        "f4_desc": "نسخ آخر رد للذكاء الاصطناعي إلى الحافظة",
        "f5_desc": "ضغط تاريخ السياق للمحادثة",
        "f6_desc": "تغيير لغة واجهة المستخدم",
        "ctrlq_desc": "الخروج الآمن من التطبيق",
        "updown_desc": "تصفح سجل الإدخال (السابق/التالي)",
        "export_success": "تم تصدير المحادثة إلى: [bold cyan]{path}[/bold cyan]",
        "export_empty": "لا توجد رسائل للتصدير.",
        "last_copied": "✓ تم نسخ آخر رد بنجاح إلى الحافظة.",
        "copy_fail": "فشل النسخ إلى الحافظة: {error}",
        "no_last_msg": "لا يوجد رد للنسخ.",
        "confirm_title": "إذن تشغيل الأداة",
        "confirm_sub": "⚡ هل تريد تشغيل [bold cyan]{label}[/bold cyan]؟ — {desc}",
        "opt_allow_once": "✓ السماح مرة واحدة",
        "opt_allow_all": "⚡ السماح بجميع الأدوات في هذه الجلسة",
        "opt_deny": "✗ رفض التشغيل",
        "approve_title": "الموافقة على خطة العمل؟",
        "opt_approve": "✓ الموافقة على الخطة",
        "opt_reject": "✗ رفض الخطة",
        "model_title": "اختر نموذج الذكاء الاصطناعي",
        "lang_title": "اختر اللغة / SELECT LANGUAGE",
        "thinking_placeholder": "جاري التفكير...",
        "input_placeholder": "✍️ اكتب رسالتك هنا...",
    },
    "es": {
        "user_label": "tú",
        "interrupted_msg": "🛑 Ejecución de IA cancelada por el usuario.",
        "ctrlc_desc": "Cancelar/Detener proceso de IA activo",
        "welcome_sub": "Escriba su pregunta a continuación o presione [bold]F1[/bold] para obtener ayuda sobre comandos.",
        "status_title": "ESTADO",
        "model": "Modelo",
        "auth": "Autenticación",
        "tokens": "Tokens",
        "remaining_tokens": "Tok. Rest.",
        "neurons": "Neurons",
        "active": "Activo",
        "session": "Sesión",
        "temp": "Temp",
        "maxtok": "MaxTok",
        "pmode": "Modo Plan",
        "mcalls": "Llamadas M.",
        "click_change_model": "Haga clic aquí para cambiar el modelo",
        "click_change_lang": "Haga clic aquí para cambiar el idioma",
        "lang": "Idioma",
        "allowed_all": "Todas las herramientas están permitidas para esta sesión.",
        "denied_tool": "Ejecución de herramienta rechazada por el usuario.",
        "allowed_tool": "Herramienta [bold cyan]{name}[/bold cyan] permitida.",
        "model_changed": "⚡ Modelo de IA activo cambiado a: [bold cyan]{name}[/bold cyan]",
        "denied_tool_msg": "Herramienta [bold red]{name}[/bold red] rechazada.",
        "approved_plan": "Plan de trabajo aprobado.",
        "rejected_plan": "Plan de trabajo rechazado.",
        "reset_success": "Sesión y permisos de herramientas restablecidos con éxito.",
        "compacting": "Compactando el contexto de la conversación...",
        "compact_success": "Contexto compactado con éxito.",
        "compact_fail": "Error de compactación: {error}",
        "save_success": "Sesión '{name}' guardada. ID: {sid}",
        "save_fail": "Error al guardar: {error}",
        "resume_fail": "Error al reanudar: {error}",
        "no_sessions": "No se encontraron sesiones guardadas.",
        "sessions_title": "SESIONES GUARDADAS:",
        "unknown_cmd": "Comando desconocido: {cmd}",
        "mikir": "pensando",
        "help_title": "AYUDA DE ATAJOS DE TECLADO Y COMANDOS DE BARRA",
        "shortcuts": "Atajos de teclado:",
        "slash_commands_label": "Comandos de barra:",
        "f1_desc": "Este menú de ayuda",
        "f2_desc": "Mostrar y cambiar el modelo de IA activo",
        "f3_desc": "Restablecer la sesión de conversación",
        "f4_desc": "Copiar la última respuesta de IA al portapapeles",
        "f5_desc": "Compactar el historial de contexto",
        "f6_desc": "Cambiar el idioma de la interfaz de usuario",
        "ctrlq_desc": "Salir de la aplicación de forma limpia",
        "updown_desc": "Navegar historial de entrada (anterior/siguiente)",
        "export_success": "Chat exportado a: [bold cyan]{path}[/bold cyan]",
        "export_empty": "No hay mensajes para exportar.",
        "last_copied": "✓ Última respuesta copiada al portapapeles con éxito.",
        "copy_fail": "Error al copiar al portapapeles: {error}",
        "no_last_msg": "No hay respuesta para copiar.",
        "confirm_title": "PERMISO DE EJECUCIÓN DE HERRAMIENTA",
        "confirm_sub": "⚡ ¿Ejecutar [bold cyan]{label}[/bold cyan]? — {desc}",
        "opt_allow_once": "✓ Permitir una vez",
        "opt_allow_all": "⚡ Permitir todas las herramientas en esta sesión",
        "opt_deny": "✗ Denegar ejecución",
        "approve_title": "¿APROBAR EL PLAN DE TRABAJO?",
        "opt_approve": "✓ Aprobar plan",
        "opt_reject": "✗ Rechazar plan",
        "model_title": "SELECCIONAR MODELO DE IA",
        "lang_title": "SELECCIONAR IDIOMA",
        "thinking_placeholder": "Pensando...",
        "input_placeholder": "✍️ Escriba un mensaje aquí...",
    },
    "pt": {
        "user_label": "você",
        "interrupted_msg": "🛑 Execução de IA cancelada pelo usuário.",
        "ctrlc_desc": "Cancelar/Parar processo de IA ativo",
        "welcome_sub": "Digite sua pergunta abaixo ou pressione [bold]F1[/bold] para obter ajuda sobre comandos.",
        "status_title": "STATUS",
        "model": "Modelo",
        "auth": "Autenticação",
        "tokens": "Tokens",
        "remaining_tokens": "Tok. Rest.",
        "neurons": "Neurons",
        "active": "Ativo",
        "session": "Sessão",
        "temp": "Temp",
        "maxtok": "MaxTok",
        "pmode": "Modo Plano",
        "mcalls": "Chamadas M.",
        "click_change_model": "Clique aqui para alterar o modelo",
        "click_change_lang": "Clique aqui para alterar o idioma",
        "lang": "Idioma",
        "allowed_all": "Todas as ferramentas são permitidas nesta sessão.",
        "denied_tool": "Execução de ferramenta rejeitada pelo usuário.",
        "allowed_tool": "Ferramenta [bold cyan]{name}[/bold cyan] permitida.",
        "model_changed": "⚡ Modelo de IA ativo alterado para: [bold cyan]{name}[/bold cyan]",
        "denied_tool_msg": "Ferramenta [bold red]{name}[/bold red] rejeitada.",
        "approved_plan": "Plano de trabalho aprovado.",
        "rejected_plan": "Plano de trabalho rejeitado.",
        "reset_success": "Sessão e permissões de ferramentas redefinidas com sucesso.",
        "compacting": "Compactando o contexto da conversa...",
        "compact_success": "Contexto compactado com sucesso.",
        "compact_fail": "Falha na compactação: {error}",
        "save_success": "Sessão '{name}' salva. ID: {sid}",
        "save_fail": "Falha ao salvar: {error}",
        "resume_fail": "Falha ao retomar: {error}",
        "no_sessions": "Nenhuma sessão salva encontrada.",
        "sessions_title": "SESSÕES SALVAS:",
        "unknown_cmd": "Comando desconhecido: {cmd}",
        "mikir": "pensando",
        "help_title": "AJUDA DE ATALHOS DE TECLADO E COMANDOS DE BARRA",
        "shortcuts": "Atalhos de teclado:",
        "slash_commands_label": "Comandos de barra:",
        "f1_desc": "Este menu de ajuda",
        "f2_desc": "Exibir e alterar o modelo de IA ativo",
        "f3_desc": "Redefinir a sessão de conversa",
        "f4_desc": "Copiar a última resposta de IA para a área de transferência",
        "f5_desc": "Compactar o histórico do contexto",
        "f6_desc": "Alterar o idioma da interface do usuário",
        "ctrlq_desc": "Sair do aplicativo de forma limpa",
        "updown_desc": "Navegar histórico de entrada (anterior/próximo)",
        "export_success": "Chat exportado para: [bold cyan]{path}[/bold cyan]",
        "export_empty": "Não há mensagens para exportar.",
        "last_copied": "✓ Última resposta copiada para a área de transferência com sucesso.",
        "copy_fail": "Falha ao copiar para a área de transferência: {error}",
        "no_last_msg": "Nenhuma resposta para copiar.",
        "confirm_title": "PERMISSÃO DE EXECUÇÃO DE FERRAMENTA",
        "confirm_sub": "⚡ Executar [bold cyan]{label}[/bold cyan]? — {desc}",
        "opt_allow_once": "✓ Permitir uma vez",
        "opt_allow_all": "⚡ Permitir todas as ferramentas nesta sessão",
        "opt_deny": "✗ Recusar execução",
        "approve_title": "APROVAR PLANO DE TRABALHO?",
        "opt_approve": "✓ Aprovar plano",
        "opt_reject": "✗ Rejeitar plano",
        "model_title": "SELECIONAR MODELO DE IA",
        "lang_title": "SELECIONAR IDIOMA",
        "thinking_placeholder": "Pensando...",
        "input_placeholder": "✍️ Digite uma mensagem aqui...",
    }
}


class ThinkingWidget(Static):
    """Widget untuk menampilkan animasi 'mikir...'."""

    @property
    def tui(self) -> AutokerenTUI:
        return self.app  # type: ignore

    def on_mount(self) -> None:
        self.frame = 0
        mikir_text = self.tui.t("mikir")
        self.frames = [
            f"🤔 [dim]{mikir_text} .  [/dim]",
            f"🤔 [dim]{mikir_text} .. [/dim]",
            f"🤔 [dim]{mikir_text} ...[/dim]",
            f"🤔 [dim]{mikir_text}  ..[/dim]",
            f"🤔 [dim]{mikir_text}   .[/dim]",
        ]
        self.update(Text.from_markup(self.frames[0]))
        self.timer = self.set_interval(0.3, self.next_frame)

    def next_frame(self) -> None:
        self.frame = (self.frame + 1) % len(self.frames)
        self.update(Text.from_markup(self.frames[self.frame]))


class ModelSelectScreen(ModalScreen[str]):
    """Screen Modal untuk memilih model AI secara interaktif."""

    def __init__(self, models: list[dict[str, Any]], current_model: str) -> None:
        super().__init__()
        self.models = models
        self.current_model = current_model

    @property
    def tui(self) -> AutokerenTUI:
        return self.app  # type: ignore

    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"[bold green]{self.tui.t('model_title')}[/bold green]", id="modal-title"),
            OptionList(id="model-list"),
            id="modal-dialog",
        )

    def on_mount(self) -> None:
        option_list = self.query_one("#model-list", OptionList)
        for m in self.models:
            label = m.get("name", m["id"])
            if m["id"] == self.current_model:
                label = f"✨ [green]{label} ({self.tui.t('active')})[/green]"
            option_list.add_option(label)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        chosen_id = self.models[event.option_index]["id"]
        self.dismiss(chosen_id)

    def on_key(self, event: Any) -> None:
        if event.key == "escape":
            self.dismiss(None)


class LanguageSelectScreen(ModalScreen[str]):
    """Screen Modal untuk memilih bahasa UI secara interaktif."""

    def __init__(self, current_lang: str) -> None:
        super().__init__()
        self.current_lang = current_lang

    @property
    def tui(self) -> AutokerenTUI:
        return self.app  # type: ignore

    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"[bold green]{self.tui.t('lang_title')}[/bold green]", id="modal-title"),
            OptionList(id="lang-list"),
            id="modal-dialog",
        )

    def on_mount(self) -> None:
        option_list = self.query_one("#lang-list", OptionList)
        self.lang_codes = list(LANGUAGES.keys())
        for code in self.lang_codes:
            label = f"{LANGUAGES[code]} ({code})"
            if code == self.current_lang:
                label = f"✨ [green]{label} ({self.tui.t('active')})[/green]"
            option_list.add_option(label)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        chosen_code = self.lang_codes[event.option_index]
        self.dismiss(chosen_code)

    def on_key(self, event: Any) -> None:
        if event.key == "escape":
            self.dismiss(None)


class MCPManageScreen(ModalScreen[str]):
    """Screen Modal untuk mengelola MCP servers: lihat status, list tools, tambah server baru."""

    CSS = """
    #mcp-add-form {
        display: none;
        height: auto;
        margin-top: 1;
    }
    #mcp-add-form.visible {
        display: block;
    }
    #mcp-name-input, #mcp-cmd-input {
        width: 100%;
        margin-bottom: 1;
    }
    """

    def __init__(self, mcp_clients: list[Any]) -> None:
        super().__init__()
        self._clients = mcp_clients
        self._show_add_form = False
        self._selected_index: int = -1

    @property
    def tui(self) -> AutokerenTUI:
        return self.app  # type: ignore

    def compose(self) -> ComposeResult:
        items = self._build_options()
        yield Container(
            Static("[bold green]⚡ MCP Server Manager[/bold green]", id="modal-title"),
            Static("[dim]Pilih server untuk lihat tools · [bold]A[/bold] = Tambah · [bold]ESC[/bold] = Tutup[/dim]", id="modal-desc"),
            OptionList(*items, id="mcp-list"),
            Container(
                Static("[bold yellow]+ Tambah MCP Server[/bold yellow]"),
                Static("[dim]Nama server:[/dim]"),
                Input(placeholder="misal: filesystem", id="mcp-name-input"),
                Static("[dim]Command (pisah spasi, contoh: npx -y @modelcontextprotocol/server-filesystem /tmp):[/dim]"),
                Input(placeholder="npx -y @modelcontextprotocol/server-filesystem", id="mcp-cmd-input"),
                Static("[dim]Tekan Enter setelah mengisi command untuk menyimpan · ESC untuk batal[/dim]"),
                id="mcp-add-form",
            ),
            id="modal-dialog",
        )

    def _build_options(self) -> list[str]:
        if not self._clients:
            return [
                "[dim]Tidak ada MCP server aktif[/dim]",
                "[dim]──────────────────────────[/dim]",
                "[bold cyan]+ Tambah server baru (tekan A)[/bold cyan]",
            ]
        items = []
        for client in self._clients:
            status = "🟢" if client.is_alive() else "🔴"
            tc = len(client.tools()) if client.is_alive() else 0
            items.append(f"{status} [bold]{client.name}[/bold]  ({tc} tools) — klik untuk lihat tools")
        items.append("[dim]──────────────────────────[/dim]")
        items.append("[bold cyan]+ Tambah server baru (tekan A)[/bold cyan]")
        return items

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        idx = event.option_index
        if idx < len(self._clients):
            # Tampilkan tool list server yang dipilih
            client = self._clients[idx]
            try:
                tools = client.tools()
                tool_names = "\n".join(f"  • {t['name']}: {t.get('description', '')[:60]}" for t in tools)
                self.tui.append_chat_message(
                    "system",
                    f"[bold green]🔧 Tools di server '[bold]{client.name}[/bold]':[/bold green]\n{tool_names or '(tidak ada tools)'}"
                )
            except Exception as exc:
                self.tui.append_chat_message("system", f"[red]Gagal baca tools: {exc}[/red]")
            self.dismiss("ok")
        else:
            # Klik "Tambah server baru"
            self._toggle_add_form()

    def _toggle_add_form(self) -> None:
        form = self.query_one("#mcp-add-form")
        self._show_add_form = not self._show_add_form
        if self._show_add_form:
            form.add_class("visible")
            self.query_one("#mcp-name-input", Input).focus()
        else:
            form.remove_class("visible")
            self.query_one("#mcp-list", OptionList).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "mcp-name-input":
            # Pindah fokus ke field command
            self.query_one("#mcp-cmd-input", Input).focus()
        elif event.input.id == "mcp-cmd-input":
            self._save_new_server()

    def _save_new_server(self) -> None:
        name = self.query_one("#mcp-name-input", Input).value.strip()
        cmd_raw = self.query_one("#mcp-cmd-input", Input).value.strip()
        if not name or not cmd_raw:
            return
        command = cmd_raw.split()
        try:
            from autokeren.config import save_config
            from autokeren.config import MCPServerConfig
            # Tambah ke config
            new_srv = MCPServerConfig(name=name, command=command)
            self.tui.cfg.mcp_servers.append(new_srv)
            save_config(self.tui.cfg)
            self.tui.append_chat_message(
                "system",
                f"[green]✓ Server '[bold]{name}[/bold]' ditambahkan ke config.yaml.[/green]\n"
                f"  Restart autokeren untuk mengaktifkannya.",
            )
        except Exception as exc:
            self.tui.append_chat_message("system", f"[red]Gagal simpan: {exc}[/red]")
        self.dismiss("saved")

    def on_key(self, event: Any) -> None:
        if event.key == "escape":
            if self._show_add_form:
                self._toggle_add_form()
                event.stop()
            else:
                self.dismiss(None)
        elif event.key == "a" and not self._show_add_form:
            self._toggle_add_form()
            event.stop()


class PermissionSelectScreen(ModalScreen[str]):
    """Screen Modal untuk meminta izin eksekusi tool."""

    def __init__(self, tool_call_label: str, description: str) -> None:
        super().__init__()
        self.tool_call_label = tool_call_label
        self.description = description

    @property
    def tui(self) -> AutokerenTUI:
        return self.app  # type: ignore

    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"[bold yellow]{self.tui.t('confirm_title')}[/bold yellow]", id="modal-title"),
            Static(f"[bold]{self.tool_call_label}[/bold]\n[dim]{self.description}[/dim]", id="modal-desc"),
            OptionList(
                self.tui.t("opt_allow_once"),
                self.tui.t("opt_allow_all"),
                self.tui.t("opt_deny"),
                id="perm-list"
            ),
            id="modal-dialog-perm",
        )

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        choices = ["y", "a", "n"]
        self.dismiss(choices[event.option_index])

    def on_key(self, event: Any) -> None:
        if event.key == "escape":
            self.dismiss("n")


class ApprovalSelectScreen(ModalScreen[bool]):
    """Screen Modal untuk menyetujui rencana kerja."""

    @property
    def tui(self) -> AutokerenTUI:
        return self.app  # type: ignore

    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"[bold yellow]{self.tui.t('approve_title')}[/bold yellow]", id="modal-title"),
            OptionList(
                self.tui.t("opt_approve"),
                self.tui.t("opt_reject"),
                id="approve-list"
            ),
            id="modal-dialog-approve",
        )

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        choices = [True, False]
        self.dismiss(choices[event.option_index])

    def on_key(self, event: Any) -> None:
        if event.key == "escape":
            self.dismiss(False)


class StatusWidget(Static):
    """Widget untuk menampilkan informasi status di panel kiri."""

    def __init__(self, agent: Agent, cfg: Config) -> None:
        super().__init__()
        self.agent = agent
        self.cfg = cfg

    @property
    def tui(self) -> AutokerenTUI:
        return self.app  # type: ignore

    def on_mount(self) -> None:
        self.update_status()

    def update_status(self) -> None:
        info = self.agent.status_bar_info()
        ctx = self.agent.context_info()

        model = info.get("model", "?")
        cwd = info.get("cwd", "?")
        neurons_remaining = info.get("neurons_remaining")
        neurons_quota = info.get("neurons_quota")

        if neurons_remaining is not None and neurons_quota:
            neurons_str = f"{neurons_quota - neurons_remaining:,}/{neurons_quota:,}"
        else:
            neurons_str = "-"

        sisa_tokens = ctx["window"] - ctx["tokens"] if ctx["window"] > 0 else 0
        lang_label = LANGUAGES.get(self.tui.active_language, self.tui.active_language)

        res = f"""[bold yellow]{self.tui.t('status_title')}[/bold yellow]

[bold]{self.tui.t('model')}[/bold]   : {model}
[bold]{self.tui.t('auth')}[/bold]    : {self.cfg.auth.mode}
[bold]{self.tui.t('tokens')}[/bold]  : {ctx['tokens']:,} ({ctx['pct']:.1f}%)
[bold]{self.tui.t('remaining_tokens')}[/bold]: {sisa_tokens:,}
[bold]{self.tui.t('neurons')}[/bold] : {neurons_str}

[bold]{self.tui.t('active')}[/bold]  : {cwd}
[bold]{self.tui.t('session')}[/bold] : {self.agent.context.summary().get('messages', 0)} msg
[bold]{self.tui.t('lang')}[/bold]    : {lang_label}

[bold]{self.tui.t('temp')}[/bold]    : {self.cfg.cloudflare.temperature}
[bold]{self.tui.t('maxtok')}[/bold]  : {self.cfg.cloudflare.max_tokens}

[bold]{self.tui.t('pmode')}[/bold]  : {self.cfg.autokeren.plan_mode}
[bold]{self.tui.t('mcalls')}[/bold] : {self.agent._tool_call_count}/{self.cfg.autokeren.max_tool_calls or 'unlimited'}

[dim]{self.tui.t('click_change_model')}[/dim]"""
        try:
            self.update(Text.from_markup(res))
        except Exception:
            self.update(res)

    async def on_click(self) -> None:
        # Klik pada panel status memicu aksi pemilihan model
        await self.tui.action_model()


class MessageWidget(Static):
    """Widget untuk menampilkan pesan user/assistant/system."""

    def __init__(self, role: str, content: str = "") -> None:
        super().__init__()
        self.role = role
        self.msg_content = content

    @property
    def tui(self) -> AutokerenTUI:
        return self.app  # type: ignore

    def on_mount(self) -> None:
        self.update_content(self.msg_content)

    def update_content(self, new_content: str) -> None:
        self.msg_content = new_content
        if self.role == "user":
            tx = Text()
            label = self.tui.t("user_label")
            tx.append(f"{label}: ", style="bold blue")
            tx.append(self.msg_content)
            self.update(tx)
        elif self.role == "system":
            try:
                self.update(Text.from_markup(self.msg_content))
            except Exception:
                self.update(self.msg_content)
        else:
            self.update(Markdown(self.msg_content or "..."))



class ToolWidget(Static):
    """Widget untuk menampilkan jalannya tool secara inline."""

    def __init__(self, name: str, arguments: dict) -> None:
        super().__init__()
        self.tool_name: str = name
        self.arguments = arguments
        self.status = "running"
        self.result_summary = ""
        self.output_lines: list[str] = []
        self.output_payload: Any = None

    def update_status(self, status: str, summary: str = "", payload: Any = None) -> None:
        self.status = status
        self.result_summary = summary
        self.output_payload = payload
        self.refresh()

    def append_line(self, line: str) -> None:
        self.output_lines.append(line)
        self.refresh()

    def render(self) -> Text:
        res = Text()
        label = _format_tool_call(self.tool_name, self.arguments)
        
        if self.status == "running":
            res.append("  ⏺ ", style="bold cyan")
            res.append(label)
        elif self.status == "success":
            res.append("  ✓ ", style="green")
            res.append(self.result_summary, style="dim")
        else:
            res.append("  ✗ ", style="red")
            res.append(self.result_summary, style="red")
            
        if self.output_lines:
            for line in self.output_lines:
                res.append("\n")
                res.append("  │ ", style="dim")
                res.append(line)

        # Render code snippet diff jika tool patch_file sukses
        if self.status == "success" and self.tool_name == "patch_file" and isinstance(self.output_payload, dict):
            out = self.output_payload
            start_line = out.get("start_line", 1)
            before = out.get("context_before", [])
            after = out.get("context_after", [])
            old = out.get("old_string", "")
            new = out.get("new_string", "")

            # Render baris-baris sebelum
            line_num = start_line - len(before)
            for line in before:
                res.append("\n")
                res.append("  │ ", style="dim")
                res.append(f" {line_num:4} │  {line}")
                line_num += 1

            # Render baris-baris yang dihapus (old)
            for line in old.splitlines():
                res.append("\n")
                res.append("  │ ", style="dim")
                res.append(f" {line_num:4} │- {line}", style="red")
                line_num += 1

            # Render baris-baris yang ditambahkan (new)
            for line in new.splitlines():
                res.append("\n")
                res.append("  │ ", style="dim")
                res.append(f" {' ':4} │+ {line}", style="green")

            # Render baris-baris sesudah
            for line in after:
                res.append("\n")
                res.append("  │ ", style="dim")
                res.append(f" {line_num:4} │  {line}")
                line_num += 1

        # Render preview jika tool write_file sukses
        elif self.status == "success" and self.tool_name == "write_file" and isinstance(self.output_payload, dict):
            out = self.output_payload
            content = out.get("content", "")
            if content:
                lines = content.splitlines()
                max_preview = 20
                shown_lines = lines[:max_preview]
                for i, line in enumerate(shown_lines, 1):
                    res.append("\n")
                    res.append("  │ ", style="dim")
                    res.append(f" {i:4} │+ {line}", style="green")
                if len(lines) > max_preview:
                    remaining = len(lines) - max_preview
                    res.append("\n")
                    res.append("  │ ", style="dim")
                    res.append(f" {' ':4} │  ... (terpotong {remaining} baris lagi)", style="dim")

        return res


class ChatArea(Container):
    """Container khusus untuk area chat yang mendeteksi perubahan ukuran untuk autoscroll."""
    def on_resize(self, event: Resize) -> None:
        if hasattr(self.app, "scroll_chat_to_end"):
            self.app.scroll_chat_to_end()


class AutokerenTUI(App):
    """Aplikasi Full TUI untuk autokeren bergaya Antigravity."""

    CSS = """
    Screen {
        layout: vertical;
        background: $background;
    }
    Horizontal {
        height: 100%;
        width: 100%;
    }
    #status-pane {
        width: 32;
        height: 100%;
        border: round #555555;
        padding: 1 1;
    }
    #right-layout {
        width: 1fr;
        height: 100%;
        layout: vertical;
    }
    #chat-pane {
        height: 1fr;
        width: 100%;
        border: round #555555;
        padding: 0 1;
    }
    #chat-area {
        height: auto;
        padding-bottom: 2;
    }
    #input-pane {
        height: 3;
        width: 100%;
        border: round #555555;
        margin: 0;
    }
    MessageWidget {
        height: auto;
        margin: 1 0;
    }
    ToolWidget {
        height: auto;
        margin: 0;
    }
    ThinkingWidget {
        height: auto;
        margin: 1 0;
    }
    ModelSelectScreen, LanguageSelectScreen, MCPManageScreen, PermissionSelectScreen, ApprovalSelectScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.6);
    }
    #modal-dialog {
        width: 50;
        height: auto;
        border: double #555555;
        background: $panel;
        padding: 1 2;
    }
    #modal-dialog-perm {
        width: 55;
        height: auto;
        border: double #555555;
        background: $panel;
        padding: 1 2;
    }
    #modal-dialog-approve {
        width: 40;
        height: auto;
        border: double #555555;
        background: $panel;
        padding: 1 2;
    }
    #modal-desc {
        margin-bottom: 1;
        height: auto;
    }
    #modal-title {
        text-align: center;
        margin-bottom: 1;
    }
    #model-list {
        height: 6;
    }
    #lang-list {
        height: 8;
    }
    #perm-list {
        height: 5;
    }
    #approve-list {
        height: 3;
    }
    """


    BINDINGS = [
        Binding("f1", "help", "Help"),
        Binding("f2", "model", "Ganti Model"),
        Binding("f3", "reset", "Reset Sesi"),
        Binding("f4", "copy_last", "Salin Respon"),
        Binding("f5", "compact", "Compact Context"),
        Binding("f6", "lang", "Bahasa / Lang"),
        Binding("ctrl+c", "cancel", "Batal / Stop"),
        Binding("ctrl+q", "quit", "Keluar"),
    ]

    def __init__(self, agent: Agent, cfg: Config) -> None:
        super().__init__()
        self.agent = agent
        self.cfg = cfg
        self.input_mode = "chat"
        self.allow_all = False
        self.allowed_tools: set[str] = set()

        # Inisialisasi bahasa aktif (pilihan config atau deteksi sistem)
        self.active_language = self.cfg.autokeren.language
        if not self.active_language:
            self.active_language = self.detect_system_language()

        # Shared thread-safe structures
        self.permission_queue: queue.Queue[tuple[bool, bool]] = queue.Queue()
        self.approval_queue: queue.Queue[bool] = queue.Queue()

        # Current active widgets
        self.thinking_widget: ThinkingWidget | None = None
        self.current_assistant_widget: MessageWidget | None = None
        self.current_tool_widget: ToolWidget | None = None

        # Input history untuk navigasi ↑↓
        self.input_history: list[str] = []
        self.history_idx: int = -1
        self._history_draft: str = ""  # simpan draft saat navigasi history
        self._agent_running: bool = False  # guard: prevent double submit (Windows fix)

        # Multi-agent project manager
        from autokeren.multiagent import ProjectManager
        self.project_manager: ProjectManager = ProjectManager()

    def t(self, key: str, **kwargs: Any) -> str:
        """Menerjemahkan key string berdasarkan bahasa aktif saat ini."""
        translated = TRANSLATIONS.get(self.active_language, {}).get(key, TRANSLATIONS["en"].get(key, key))
        if kwargs:
            return translated.format(**kwargs)
        return translated

    def detect_system_language(self) -> str:
        """Mendeteksi bahasa sistem terminal secara otomatis."""
        import os
        import locale
        
        # 1. Cek variabel lingkungan LANG
        lang_env = os.environ.get("LANG", "").lower()
        for code in LANGUAGES:
            if code in lang_env:
                return code
                
        # 2. Cek default locale OS
        try:
            sys_loc, _ = locale.getdefaultlocale()
            if sys_loc:
                sys_loc = sys_loc.lower()
                for code in LANGUAGES:
                    if code in sys_loc:
                        return code
        except Exception:
            pass
            
        return "en"

    def compose(self) -> ComposeResult:
        from textual.suggester import SuggestFromList
        commands = [
            "/help", "/reset", "/compact", "/permissions", "/memory",
            "/model", "/lang", "/export", "/mcp", "/save", "/resume", "/sessions", "/q", "/quit",
            "/project", "/tdd",
        ]
        suggester = SuggestFromList(commands, case_sensitive=False)
        yield Horizontal(
            Container(StatusWidget(self.agent, self.cfg), id="status-pane"),
            Container(
                VerticalScroll(ChatArea(id="chat-area"), id="chat-pane"),
                Input(id="input-pane", placeholder=self.t("input_placeholder"), suggester=suggester),
                id="right-layout"
            )
        )

    def on_key(self, event: object) -> None:
        """Handle navigasi history input dengan tombol Up/Down."""
        from textual.events import Key
        if not isinstance(event, Key):
            return
        try:
            input_pane = self.query_one("#input-pane", Input)
        except Exception:
            return
        if input_pane.disabled:
            return
        if event.key == "up":
            if not self.input_history:
                return
            if self.history_idx == -1:
                self._history_draft = input_pane.value
            next_idx = min(self.history_idx + 1, len(self.input_history) - 1)
            if next_idx != self.history_idx:
                self.history_idx = next_idx
                input_pane.value = self.input_history[-(self.history_idx + 1)]
                input_pane.cursor_position = len(input_pane.value)
            event.prevent_default()
        elif event.key == "down":
            if self.history_idx == -1:
                return
            self.history_idx -= 1
            if self.history_idx == -1:
                input_pane.value = self._history_draft
            else:
                input_pane.value = self.input_history[-(self.history_idx + 1)]
            input_pane.cursor_position = len(input_pane.value)
            event.prevent_default()

    def on_mount(self) -> None:
        # Bind Agent callbacks ke TUI
        self.agent.on_model_start = self.on_model_start
        self.agent.on_model_end = self.on_model_end
        self.agent.on_tool_start = self.on_tool_start
        self.agent.on_tool_end = self.on_tool_end
        self.agent.on_tool_output = self.on_tool_output
        self.agent.on_chunk = self.on_chunk
        self.agent.permission_callback = self.confirm_permission

        # Tampilkan welcome banner
        import pyfiglet
        from autokeren import __version__
        from rich.markup import escape

        full_art = pyfiglet.figlet_format("AUTOKEREN", font="slant").rstrip("\n").split("\n")
        mid = len(full_art) // 2
        colored_lines = []
        for i, line in enumerate(full_art):
            line_esc = escape(line)
            if i < mid:
                colored_lines.append(f"[bold red]{line_esc}[/bold red]")
            else:
                extra = f"  [bold yellow]v{__version__}[/bold yellow]" if i == mid else ""
                colored_lines.append(f"[bold white]{line_esc}[/bold white]{extra}")
        
        welcome = (
            "\n".join(colored_lines) + "\n\n"
            + self.t("welcome_sub")
        )
        self.append_chat_message("system", welcome)
        self.update_status()

        # Jalankan pengecekan update di background worker asinkron
        self.run_worker(self.check_for_updates())
        self._focus_input()

    async def check_for_updates(self) -> None:
        """Pengecekan versi terbaru dari PyPI secara asinkron di latar belakang."""
        import httpx
        from autokeren import __version__
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://pypi.org/pypi/autokeren/json", timeout=2.0)
                if resp.status_code == 200:
                    latest_ver = resp.json()["info"]["version"]
                    if latest_ver != __version__:
                        self.append_chat_message(
                            "system",
                            self.t("pypi_update", version=latest_ver)
                        )
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Agent Thread-safe Callbacks
    # ------------------------------------------------------------------ #

    def on_model_start(self) -> None:
        def _start():
            self.thinking_widget = ThinkingWidget()
            self.query_one("#chat-area").mount(self.thinking_widget)
            self.scroll_chat_to_end()
        self.call_from_thread(_start)

    def on_chunk(self, text: str) -> None:
        def _chunk():
            # Hapus animasi mikir jika ada sebelum memount widget streaming text
            if self.thinking_widget:
                self.thinking_widget.remove()
                self.thinking_widget = None
                self.current_assistant_widget = MessageWidget("assistant", "")
                self.query_one("#chat-area").mount(self.current_assistant_widget)

            if self.current_assistant_widget:
                self.current_assistant_widget.update_content(self.current_assistant_widget.msg_content + text)
                self.scroll_chat_to_end()
        self.call_from_thread(_chunk)

    def on_model_end(self, resp: ModelResponse) -> None:
        def _end():
            if self.thinking_widget:
                self.thinking_widget.remove()
                self.thinking_widget = None
            self.current_assistant_widget = None
            self.update_status()
        self.call_from_thread(_end)

    def on_tool_start(self, name: str, arguments: dict) -> None:
        def _tool():
            self.current_tool_widget = ToolWidget(name, arguments)
            self.query_one("#chat-area").mount(self.current_tool_widget)
            self.scroll_chat_to_end()
        self.call_from_thread(_tool)

    def on_tool_output(self, name: str, line: str) -> None:
        def _output():
            if self.current_tool_widget:
                self.current_tool_widget.append_line(line)
                self.scroll_chat_to_end()
        self.call_from_thread(_output)

    def on_tool_end(self, name: str, result: Any) -> None:
        def _end():
            if self.current_tool_widget:
                ok = result.ok if hasattr(result, "ok") else True
                output = result.output if hasattr(result, "output") else result
                error = result.error if hasattr(result, "error") else None
                status = "success" if ok else "error"
                summary = _summarize_tool_result(name, output) if ok else (error or "gagal")
                self.current_tool_widget.update_status(status, summary, output)
                self.current_tool_widget = None
                self.scroll_chat_to_end()
                self.update_status()
        self.call_from_thread(_end)

    def confirm_permission(self, tool_name: str, description: str, arguments: dict) -> bool:
        if self.allow_all:
            return True
        if tool_name in self.allowed_tools:
            return True

        # Kita harus prompt user di thread utama TUI. Block thread agent saat ini.
        evt = threading.Event()
        result = [False]

        def _prompt():
            from rich.markup import escape
            label = _format_tool_call(tool_name, arguments)
            label_esc = escape(label)
            desc_esc = escape(description)
            self.append_chat_message("system", self.t("confirm_sub", label=label_esc, desc=desc_esc))

            def on_perm_result(choice: str | None) -> None:
                from rich.markup import escape
                allowed = False
                name_esc = escape(tool_name)
                if choice == "y":
                    allowed = True
                    self.allowed_tools.add(tool_name)
                    self.append_chat_message("system", self.t("allowed_tool", name=name_esc))
                elif choice == "a":
                    allowed = True
                    self.allow_all = True
                    self.append_chat_message("system", self.t("allowed_all"))
                else:
                    self.append_chat_message("system", self.t("denied_tool_msg", name=name_esc))

                result[0] = allowed
                evt.set()

            self.push_screen(PermissionSelectScreen(label, description), on_perm_result)

        self.call_from_thread(_prompt)
        evt.wait()
        return result[0]

    # ------------------------------------------------------------------ #
    # Helper & UI Actions
    # ------------------------------------------------------------------ #

    def append_chat_message(self, role: str, content: str) -> None:
        widget = MessageWidget(role, content)
        self.query_one("#chat-area").mount(widget)
        self.scroll_chat_to_end()

    def scroll_chat_to_end(self) -> None:
        chat_pane = self.query_one("#chat-pane", VerticalScroll)
        def _scroll() -> None:
            chat_pane.scroll_to(y=chat_pane.max_scroll_y, animate=False)
        self.call_after_refresh(_scroll)


    def _focus_input(self) -> None:
        """Kembalikan fokus kursor ke input box."""
        try:
            self.query_one("#input-pane", Input).focus()
        except Exception:
            pass

    def update_status(self) -> None:
        self.query_one("#status-pane StatusWidget", StatusWidget).update_status()

    # ------------------------------------------------------------------ #
    # Input Submission Handler
    # ------------------------------------------------------------------ #

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        val = event.value.strip()
        if not val:
            return
        if self._agent_running:
            return

        input_pane = self.query_one("#input-pane", Input)
        input_pane.value = ""
        self._agent_running = True

        if val.startswith("/"):
            await self.handle_slash_command(val)
            self._focus_input()
            return

        self.append_chat_message("user", val)
        # Simpan ke history input (hindari duplikat berturutan)
        if not self.input_history or self.input_history[-1] != val:
            self.input_history.append(val)
        self.history_idx = -1
        self._history_draft = ""
        input_pane.disabled = True
        input_pane.placeholder = self.t("thinking_placeholder")
        
        # Jalankan agent loop di background worker thread
        self.run_worker(self._run_agent_flow(val), thread=True)

    async def _run_agent_flow(self, user_input: str) -> None:
        try:
            # Panggil Agent loop
            self.agent.run(user_input)

            # Jika Plan Mode aktif dan rencana belum disetujui
            while self.cfg.autokeren.plan_mode and not self.agent.plan_approved:
                approved = await self.prompt_plan_approval()
                if approved:
                    self.agent.approve_plan()
                    self.agent.run("")
                else:
                    self.agent.context.add_user("User menolak rencana. Tanya apa yang perlu diubah.")
                    self.agent.run("")

        except Exception as e:
            self.append_chat_message("system", self.t("unknown_cmd", cmd=str(e)))
        finally:
            def _reset_input():
                self._agent_running = False
                input_pane = self.query_one("#input-pane", Input)
                input_pane.disabled = False
                input_pane.placeholder = self.t("input_placeholder")
                input_pane.focus()
                self.update_status()
            self.call_from_thread(_reset_input)

    async def prompt_plan_approval(self) -> bool:
        evt = threading.Event()
        result = [False]

        def _prompt():
            def on_approve_result(approved: bool | None) -> None:
                res = approved if approved is not None else False
                if res:
                    self.append_chat_message("system", self.t("approved_plan"))
                else:
                    self.append_chat_message("system", self.t("rejected_plan"))
                result[0] = res
                evt.set()

            self.push_screen(ApprovalSelectScreen(), on_approve_result)

        self.call_from_thread(_prompt)
        evt.wait()
        return result[0]

    # ------------------------------------------------------------------ #
    # Key Bindings & Slash Commands
    # ------------------------------------------------------------------ #

    async def action_help(self) -> None:
        help_text = (
            f"[bold yellow]{self.t('help_title')}[/bold yellow]\n\n"
            f"{self.t('shortcuts')}\n"
            f"  - [bold]F1[/bold]   : {self.t('f1_desc')}\n"
            f"  - [bold]F2[/bold]   : {self.t('f2_desc')}\n"
            f"  - [bold]F3[/bold]   : {self.t('f3_desc')}\n"
            f"  - [bold]F4[/bold]   : {self.t('f4_desc')}\n"
            f"  - [bold]F5[/bold]   : {self.t('f5_desc')}\n"
            f"  - [bold]F6[/bold]   : {self.t('f6_desc')}\n"
            f"  - [bold]↑/↓[/bold]  : {self.t('updown_desc')}\n"
            f"  - [bold]Ctrl+C[/bold]: {self.t('ctrlc_desc')}\n"
            f"  - [bold]Ctrl+Q[/bold]: {self.t('ctrlq_desc')}\n\n"
            f"{self.t('slash_commands_label')}\n"
            "  - [bold]/model <name>[/bold]  : Switch model\n"
            "  - [bold]/lang <code2>[/bold]  : Switch TUI language\n"
            "  - [bold]/export [file][/bold]  : Export chat to Markdown file\n"
            "  - [bold]/compact[/bold]       : Compact context history\n"
            "  - [bold]/reset[/bold]         : Reset conversation session\n"
            "  - [bold]/permissions[/bold]   : Check allowed tools\n"
            "  - [bold]/memory[/bold]        : Display project memory\n"
            "  - [bold]/sessions[/bold]      : List saved sessions\n"
            "  - [bold]/save <name>[/bold]    : Save current session\n"
            "  - [bold]/resume <id>[/bold]    : Resume saved session\n"
            "  - [bold]/project <sub>[/bold]  : Multi-agent project management\n"
            "  - [bold]/q[/bold]              : Quit autokeren"
        )
        self.append_chat_message("system", help_text)

    async def action_model(self) -> None:
        from autokeren.models.cloudflare import fetch_available_models
        all_models = fetch_available_models(self.cfg)
        current_model = self.agent.router.current_model_id()

        def on_select(chosen_id: str | None) -> None:
            if chosen_id:
                from autokeren.models.cloudflare import resolve_model_id
                resolved = resolve_model_id(chosen_id, self.agent.router.models[0].auth_mode)
                if self.agent.router.switch_model(resolved):
                    self.append_chat_message("system", self.t("model_changed", name=chosen_id))
                    self.update_status()
                else:
                    self.append_chat_message("system", f"[red]Model '{chosen_id}' not found.[/red]")
            self._focus_input()

        self.push_screen(ModelSelectScreen(all_models, current_model), on_select)

    async def action_lang(self) -> None:
        """Picu modal pemilihan bahasa."""
        def on_select(chosen_code: str | None) -> None:
            if chosen_code:
                self.active_language = chosen_code
                self.cfg.autokeren.language = chosen_code
                from autokeren.config import save_config
                try:
                    save_config(self.cfg)
                except Exception:
                    pass
                self.append_chat_message("system", f"Language changed to: [bold]{LANGUAGES[chosen_code]}[/bold]")
                
                # Update placeholder input
                self.query_one("#input-pane", Input).placeholder = self.t("input_placeholder")
                self.update_status()
            self._focus_input()

        self.push_screen(LanguageSelectScreen(self.active_language), on_select)

    async def action_cancel(self) -> None:
        """Menghentikan proses AI yang sedang berjalan."""
        self.agent.interrupted = True
        self._agent_running = False
        self.append_chat_message("system", self.t("interrupted_msg"))
        try:
            input_pane = self.query_one("#input-pane", Input)
            input_pane.disabled = False
            input_pane.placeholder = self.t("input_placeholder")
            input_pane.focus()
        except Exception:
            pass
        self.update_status()

    async def action_reset(self) -> None:
        self.agent.reset()
        self.allow_all = False
        self.allowed_tools.clear()
        
        # Hapus widget chat
        chat_area = self.query_one("#chat-area")
        for child in list(chat_area.children):
            child.remove()
            
        self.append_chat_message("system", self.t("reset_success"))
        self.update_status()

    async def action_copy_last(self) -> None:
        last_assistant_msg = None
        for msg in reversed(self.agent.context.messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                last_assistant_msg = msg["content"]
                break
        
        if last_assistant_msg:
            try:
                self.copy_to_clipboard(last_assistant_msg)
                self.append_chat_message("system", self.t("last_copied"))
            except Exception as e:
                self.append_chat_message("system", self.t("copy_fail", error=str(e)))
        else:
            self.append_chat_message("system", self.t("no_last_msg"))

    async def action_compact(self) -> None:
        self.append_chat_message("system", self.t("compacting"))
        try:
            msg = self.agent.compact()
            self.append_chat_message("system", f"[green]{msg}[/green]")
            self.update_status()
        except Exception as e:
            self.append_chat_message("system", self.t("compact_fail", error=str(e)))

    async def handle_slash_command(self, cmd_line: str) -> None:
        parts = cmd_line.split(" ", 1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("/q", "/quit"):
            self.exit()
        elif cmd == "/help":
            await self.action_help()
        elif cmd == "/reset":
            await self.action_reset()
        elif cmd == "/compact":
            await self.action_compact()
        elif cmd == "/permissions":
            if self.allow_all:
                self.append_chat_message("system", self.t("allowed_all"))
            elif self.allowed_tools:
                self.append_chat_message("system", f"Tools: {', '.join(sorted(self.allowed_tools))}")
            else:
                self.append_chat_message("system", "No permissions granted yet.")
        elif cmd == "/memory":
            mem = self.agent.memory.load()
            if mem:
                self.append_chat_message("system", f"[bold magenta]MEMORY:[/bold magenta]\n{mem}")
            else:
                self.append_chat_message("system", "Memory is empty.")
        elif cmd == "/model":
            if not arg:
                await self.action_model()
            else:
                from autokeren.models.cloudflare import resolve_model_id
                resolved = resolve_model_id(arg, self.agent.router.models[0].auth_mode)
                if self.agent.router.switch_model(resolved):
                    self.append_chat_message("system", self.t("allowed_tool", name=arg))
                    self.update_status()
                else:
                    self.append_chat_message("system", f"[red]Model '{arg}' not found.[/red]")
        elif cmd == "/lang":
            if not arg:
                await self.action_lang()
            else:
                code = arg.lower()
                if code in LANGUAGES:
                    self.active_language = code
                    self.cfg.autokeren.language = code
                    from autokeren.config import save_config
                    try:
                        save_config(self.cfg)
                    except Exception:
                        pass
                    self.append_chat_message("system", f"Language changed to: [bold]{LANGUAGES[code]}[/bold]")
                    
                    # Update placeholder input
                    self.query_one("#input-pane", Input).placeholder = self.t("input_placeholder")
                    self.update_status()
                else:
                    self.append_chat_message("system", f"[red]Language code '{arg}' not supported. Available: {', '.join(LANGUAGES.keys())}[/red]")
        elif cmd == "/mcp":
            from autokeren.cli import _mcp_clients
            await self.push_screen(MCPManageScreen(_mcp_clients))
        elif cmd == "/save":
            name = arg or f"session-{len(self.agent.sessions.list()) + 1}"
            try:
                sid = self.agent.save_session(name)
                self.append_chat_message("system", self.t("save_success", name=name, sid=sid))
            except Exception as e:
                self.append_chat_message("system", self.t("save_fail", error=str(e)))
        elif cmd == "/resume":
            if not arg:
                self.append_chat_message("system", "Use: [bold]/resume <name|id>[/bold]")
            else:
                try:
                    msg = self.agent.resume_session(arg)
                    self.append_chat_message("system", f"[green]{msg}[/green]")
                    self.rebuild_chat_history()
                    self.update_status()
                except Exception as e:
                    self.append_chat_message("system", self.t("resume_fail", error=str(e)))
        elif cmd == "/sessions":
            sessions = self.agent.sessions.list()
            if not sessions:
                self.append_chat_message("system", self.t("no_sessions"))
            else:
                lines = [f"[bold yellow]{self.t('sessions_title')}[/bold yellow]"]
                for s in sessions:
                    lines.append(f"  - [cyan]{s['id']}[/cyan] [bold]{s['name']}[/bold] ({s['messages']} msg)")
                self.append_chat_message("system", "\n".join(lines))
        elif cmd == "/export":
            msgs = [m for m in self.agent.context.messages if m.get("role") in ("user", "assistant")]
            if not msgs:
                self.append_chat_message("system", self.t("export_empty"))
            else:
                import datetime
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                fname = arg.strip() if arg.strip() else f"autokeren_export_{ts}.md"
                if not fname.endswith(".md"):
                    fname += ".md"
                out_path = Path(self.agent.project_root) / fname
                lines_md: list[str] = [f"# autokeren Chat Export\n\n*Exported: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n---\n"]
                for m in msgs:
                    role_label = "**User**" if m["role"] == "user" else "**Assistant**"
                    content = m.get("content") or ""
                    if isinstance(content, list):
                        content = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
                    lines_md.append(f"### {role_label}\n\n{content}\n\n---\n")
                try:
                    out_path.write_text("\n".join(lines_md), encoding="utf-8")
                    self.append_chat_message("system", self.t("export_success", path=str(out_path)))
                except Exception as exc:
                    self.append_chat_message("system", f"[red]Export gagal: {exc}[/red]")
        elif cmd == "/project":
            await self._handle_project_cmd(arg)
        elif cmd == "/tdd":
            if not arg or "|" not in arg:
                self.append_chat_message(
                    "system",
                    "[red]Gunakan: /tdd <nama_file> | <deskripsi_fitur>[/red]\n"
                    "Contoh: [bold]/tdd kalkulator | buat fungsi hitung_pajak yang menghitung pajak 10%[/bold]"
                )
            else:
                target_name, task_desc = arg.split("|", 1)
                self.run_worker(self._run_tdd_workflow(target_name.strip(), task_desc.strip()))
        else:
            self.append_chat_message("system", self.t("unknown_cmd", cmd=cmd))

    async def _handle_project_cmd(self, arg: str) -> None:
        """Handler untuk semua sub-command /project."""
        from autokeren.multiagent import WorkerStatus
        parts = arg.strip().split(maxsplit=1)
        sub = parts[0].lower() if parts else ""
        rest = parts[1] if len(parts) > 1 else ""

        pm = self.project_manager

        # /project new <nama>
        if sub == "new":
            if not rest:
                self.append_chat_message("system", "[red]Gunakan: /project new <nama_project>[/red]")
                return
            try:
                project = pm.new_project(rest.strip())
                self.append_chat_message(
                    "system",
                    f"[green]✓ Project '[bold]{project.name}[/bold]' dibuat.[/green] "
                    f"Tambah agent dengan [bold]/project add <nama> <task>[/bold]",
                )
            except ValueError as exc:
                self.append_chat_message("system", f"[red]{exc}[/red]")

        # /project add <nama_agent> <task>
        elif sub == "add":
            project = pm.get_active()  # type: ignore[assignment]
            if not project:
                self.append_chat_message("system", "[red]Belum ada project aktif. Buat dulu dengan /project new <nama>[/red]")
                return
            assert project is not None
            add_parts = rest.split(maxsplit=1)
            if len(add_parts) < 2:
                self.append_chat_message("system", "[red]Gunakan: /project add <nama_agent> <task deskripsi>[/red]")
                return
            worker_name, task = add_parts[0], add_parts[1]
            try:
                project.add_worker(worker_name, task)
                self.append_chat_message(
                    "system",
                    f"[cyan]⏳ Agent '[bold]{worker_name}[/bold]' ditambahkan ke project '[bold]{project.name}[/bold]'.[/cyan]\n"
                    f"   Task: {task[:80]}{'...' if len(task) > 80 else ''}",
                )
            except ValueError as exc:
                self.append_chat_message("system", f"[red]{exc}[/red]")

        # /project run
        elif sub == "run":
            project = pm.get_active()  # type: ignore[assignment]
            if not project:
                self.append_chat_message("system", "[red]Belum ada project aktif.[/red]")
                return
            assert project is not None
            if not project.workers:
                self.append_chat_message("system", "[red]Project belum memiliki worker. Gunakan /project add terlebih dahulu.[/red]")
                return
            pending = [w for w in project.workers if w.status == WorkerStatus.PENDING]
            if not pending:
                self.append_chat_message("system", "[yellow]Semua worker sudah berjalan atau selesai.[/yellow]")
                return

            self.append_chat_message(
                "system",
                f"[bold green]🚀 Menjalankan {len(pending)} agent secara paralel...[/bold green]",
            )

            def _agent_factory(worker_name: str):
                from autokeren.cli import build_registry
                from autokeren.agent import Agent
                from pathlib import Path as _Path
                worker_memory = self.agent.memory
                worker_reg = build_registry(self.cfg, _Path(self.agent.project_root), worker_memory)
                child_agent = Agent(self.cfg, worker_reg, self.agent.project_root, memory=worker_memory)
                return child_agent

            def _on_done(worker) -> None:
                icon = worker.status_icon()
                elapsed = f"{worker.elapsed():.1f}s"
                if worker.status == WorkerStatus.DONE:
                    msg = f"{icon} Agent '[bold]{worker.name}[/bold]' selesai dalam {elapsed}."
                else:
                    msg = f"{icon} Agent '[bold]{worker.name}[/bold]' error ({elapsed}): {worker.error[:80]}"
                self.call_from_thread(self.append_chat_message, "system", msg)

            self.run_worker(
                lambda: pm.run_project(project, _agent_factory, _on_done),
                thread=True,
            )

        # /project status
        elif sub == "status":
            project = pm.get_active()  # type: ignore[assignment]
            if not project:
                self.append_chat_message("system", "[red]Belum ada project aktif.[/red]")
                return
            assert project is not None
            lines = [f"[bold yellow]📊 Project: {project.name}[/bold yellow]  {project.summary()}"]
            for w in project.workers:
                elapsed = f"{w.elapsed():.1f}s" if w.started_at else "-"
                lines.append(
                    f"  {w.status_icon()} [bold]{w.name}[/bold]  [{w.status.value}]  {elapsed}"
                    f"\n     Task: {w.task[:60]}{'...' if len(w.task) > 60 else ''}"
                )
            self.append_chat_message("system", "\n".join(lines))

        # /project switch <nama>
        elif sub == "switch":
            if not rest:
                self.append_chat_message("system", "[red]Gunakan: /project switch <nama_project>[/red]")
                return
            try:
                project = pm.switch(rest.strip())
                self.append_chat_message("system", f"[green]✓ Aktif ke project '[bold]{project.name}[/bold]'.[/green]")
            except ValueError as exc:
                self.append_chat_message("system", f"[red]{exc}[/red]")

        # /project list
        elif sub == "list":
            if not pm.projects:
                self.append_chat_message("system", "[dim]Belum ada project. Buat dengan /project new <nama>[/dim]")
                return
            lines = ["[bold yellow]📁 Semua Project:[/bold yellow]"]
            for name, proj in pm.projects.items():
                active_marker = " [green]← aktif[/green]" if name == pm.active_project else ""
                lines.append(f"  • [bold]{name}[/bold]{active_marker}  {proj.summary()}")
            self.append_chat_message("system", "\n".join(lines))

        # /project output <nama_agent>
        elif sub == "output":
            project = pm.get_active()  # type: ignore[assignment]
            if not project:
                self.append_chat_message("system", "[red]Belum ada project aktif.[/red]")
                return
            assert project is not None
            worker = project.get_worker(rest.strip())
            if not worker:
                self.append_chat_message("system", f"[red]Agent '{rest.strip()}' tidak ditemukan.[/red]")
                return
            output = worker.output or worker.error or "(belum ada output)"
            self.append_chat_message("system", f"[bold]Output agent '{worker.name}':[/bold]\n{output}")

        else:
            self.append_chat_message(
                "system",
                "[bold yellow]📁 /project — Multi-Agent Mode[/bold yellow]\n\n"
                "  [bold]/project new <nama>[/bold]           — Buat project baru\n"
                "  [bold]/project add <agent> <task>[/bold]   — Tambah agent ke project aktif\n"
                "  [bold]/project run[/bold]                  — Jalankan semua agent paralel\n"
                "  [bold]/project status[/bold]               — Lihat status semua agent\n"
                "  [bold]/project output <agent>[/bold]       — Lihat output agent tertentu\n"
                "  [bold]/project list[/bold]                 — Lihat semua project\n"
                "  [bold]/project switch <nama>[/bold]        — Ganti project aktif\n",
            )

    def rebuild_chat_history(self) -> None:
        chat_area = self.query_one("#chat-area")
        for child in list(chat_area.children):
            child.remove()

        # Re-add pesan dari history (skip system prompt index 0)
        for msg in self.agent.context.messages[1:]:
            role = msg.get("role")
            content = msg.get("content")
            if role in ("user", "assistant") and content:
                self.query_one("#chat-area").mount(MessageWidget(role, content))
        self.scroll_chat_to_end()

    async def _run_tdd_workflow(self, target_name: str, task_desc: str) -> None:
        from autokeren.multiagent.tdd import TDDEngine

        # Disable input field selama proses TDD berjalan
        def _disable():
            input_pane = self.query_one("#input-pane", Input)
            input_pane.disabled = True
            input_pane.placeholder = "🔴 TDD loop sedang berjalan..."
        _disable()

        def _log(msg: str):
            # Kirim output log TDD ke TUI chat window secara live
            def _append():
                self.append_chat_message("system", msg)
            import threading
            if self._thread_id == threading.get_ident():
                _append()
            else:
                self.call_from_thread(_append)

        try:
            engine = TDDEngine(self.agent, str(self.agent.project_root), _log)
            # Jalankan alur TDD secara sinkron di background thread
            import anyio
            success = await anyio.to_thread.run_sync(engine.execute_tdd_flow, task_desc, target_name)
            if success:
                _log("[bold green]✓ TDD Workflow sukses diselesaikan![/bold green]")
            else:
                _log("[bold red]✗ TDD Workflow gagal diselesaikan.[/bold red]")
        except Exception as exc:
            _log(f"[bold red]⚠ Error TDD: {exc}[/bold red]")
        finally:
            # Aktifkan kembali input field
            def _enable():
                input_pane = self.query_one("#input-pane", Input)
                input_pane.disabled = False
                input_pane.placeholder = self.t("input_placeholder")
                input_pane.focus()
            _enable()


def run_tui(agent: Agent, cfg: Config) -> None:
    """Fungsi runner untuk meluncurkan TUI."""
    app = AutokerenTUI(agent, cfg)
    try:
        app.run()
    except KeyboardInterrupt:
        pass

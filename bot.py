import logging
import html
import asyncio
from telegram import Update, ChatMember, ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ApplicationBuilder, ContextTypes, CommandHandler, ChatMemberHandler, CallbackQueryHandler
from config import load_config
from utils import restricted, owner_only, is_arbitrator, is_owner
from database import (
    add_arbitrator_db, remove_arbitrator_db, get_all_arbitrators_db,
    create_motion_db, get_active_motions_db, get_motion_db, close_motion_db,
    record_vote_db, get_motion_votes_db, set_setting_db, get_setting_db,
    init_db
)
from monitor import start_monitor

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

config = load_config()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 歡迎使用仲裁委員會機器人。\n\n"
        "此機器人僅供授權人員使用。"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "<b>可用指令：</b>\n\n"
        "<b>仲裁員指令：</b>\n"
        "/motion [標題] | [內容] - 建立新動議\n"
        "/list_motions - 列出進行中的動議\n"
        "/close_motion [ID] - 關閉動議\n"
        "/list_arbitrators - 列出授權仲裁員\n"
        "/set_threshold [活躍人數] [門檻] - 設定絕對多數門檻\n\n"
        "<b>管理員指令：</b>\n"
        "/add_arbitrator [ID] - 新增仲裁員\n"
        "/remove_arbitrator [ID] - 移除仲裁員"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

@owner_only
async def add_arbitrator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("用法：/add_arbitrator <用戶ID>")
        return
    
    try:
        user_id = int(context.args[0])
        if add_arbitrator_db(user_id):
            await update.message.reply_text(f"✅ 用戶 {user_id} 已新增至仲裁員名單。")
        else:
            await update.message.reply_text(f"⚠️ 用戶 {user_id} 已經是仲裁員了。")
    except ValueError:
        await update.message.reply_text("❌ 無效的用戶ID。請輸入數字。")

@owner_only
async def remove_arbitrator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("用法：/remove_arbitrator <用戶ID>")
        return
    
    try:
        user_id = int(context.args[0])
        if remove_arbitrator_db(user_id):
            await update.message.reply_text(f"✅ 用戶 {user_id} 已從仲裁員名單移除。")
        else:
            await update.message.reply_text(f"⚠️ 用戶 {user_id} 不是仲裁員。")
    except ValueError:
        await update.message.reply_text("❌ 無效的用戶ID。請輸入數字。")

@restricted
async def list_arbitrators(update: Update, context: ContextTypes.DEFAULT_TYPE):
    arbitrators = get_all_arbitrators_db()
    if not arbitrators:
        await update.message.reply_text("找不到仲裁員。")
        return
    
    msg = "<b>授權仲裁員：</b>\n"
    for uid in arbitrators:
        msg += f"- <code>{uid}</code>\n"
    
    await update.message.reply_text(msg, parse_mode='HTML')

@restricted
async def set_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) != 2:
        await update.message.reply_text("用法：/set_threshold <活躍人數> <絕對多數票數>")
        return
    
    try:
        active_count = int(context.args[0])
        majority_threshold = int(context.args[1])
        
        if active_count < 1 or majority_threshold < 1:
            await update.message.reply_text("❌ 數值必須大於 0。")
            return
            
        if majority_threshold > active_count:
            await update.message.reply_text("❌ 絕對多數票數不能大於活躍人數。")
            return
            
        set_setting_db('active_arbitrator_count', active_count)
        set_setting_db('majority_threshold', majority_threshold)
        
        msg = (
            f"📢 <b>仲裁委員會設置更新</b>\n\n"
            f"<b>活躍仲裁員人數：</b> {active_count}\n"
            f"<b>絕對多數門檻：</b> {majority_threshold}\n\n"
            f"此設置將用於自動判定動議結果。"
        )
        
        message = await context.bot.send_message(config['arbcom_group_id'], msg, parse_mode='HTML')
        try:
            await context.bot.pin_chat_message(config['arbcom_group_id'], message.message_id)
        except Exception:
            pass # Pinning might fail if bot lacks permission
            
        # Also notify archive channel
        try:
            await context.bot.send_message(config['archive_channel_id'], msg, parse_mode='HTML')
        except Exception as e:
            print(f"Failed to notify archive channel about threshold update: {e}")
            
    except ValueError:
        await update.message.reply_text("❌ 無效的數值。請輸入數字。")

async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tracks the chats the bot is in."""
    result = extract_status_change(update.chat_member)
    if result is None:
        return
    
    was_member, is_member = result
    
    # If the bot was added to a group, we might want to check config
    # But here we focus on user joins
    
def extract_status_change(chat_member_update: ChatMemberUpdated):
    """Takes a ChatMemberUpdated instance and extracts whether the 'old_chat_member'
    and the 'new_chat_member' are status of the member.
    """
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get("is_member", (None, None))

    if status_change is None:
        return None

    old_status = chat_member_update.old_chat_member.status
    new_status = chat_member_update.new_chat_member.status

    was_member = old_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (old_status == ChatMember.RESTRICTED and chat_member_update.old_chat_member.is_member)

    is_member = new_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (new_status == ChatMember.RESTRICTED and chat_member_update.new_chat_member.is_member)

    return was_member, is_member

async def greet_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Greets new users in chats and kicks unauthorized ones."""
    result = extract_status_change(update.chat_member)
    if result is None:
        return

    was_member, is_member = result
    
    # Only check if someone became a member
    if not was_member and is_member:
        user = update.chat_member.new_chat_member.user
        chat_id = update.chat_member.chat.id
        
        # Check if this is the authorized group
        if chat_id != config['arbcom_group_id']:
            return

        if is_owner(user.id) or is_arbitrator(user.id):
            # Authorized
            pass
        else:
            # Unauthorized
            await context.bot.ban_chat_member(chat_id, user.id)
            await context.bot.unban_chat_member(chat_id, user.id) # Unban to allow re-join if authorized later
            await context.bot.send_message(
                chat_id,
                f"🚫 未授權用戶 {user.mention_html()} 已被移除。",
                parse_mode='HTML'
            )

@restricted
async def motion_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("用法：/motion <標題> | <內容>")
        return
    
    text = ' '.join(context.args)
    if '|' in text:
        title, content = text.split('|', 1)
        title = title.strip()
        content = content.strip()
    else:
        title = text
        content = "未提供內容。"
        
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    if chat_id != config['arbcom_group_id']:
        await update.message.reply_text("⚠️ 動議只能在授權群組中建立。")
        return

    motion_id = create_motion_db(title, content, user.id, user.username, chat_id)
    
    keyboard = [
        [
            InlineKeyboardButton("支持 (0)", callback_data=f"vote:{motion_id}:support"),
            InlineKeyboardButton("反對 (0)", callback_data=f"vote:{motion_id}:oppose"),
            InlineKeyboardButton("棄權 (0)", callback_data=f"vote:{motion_id}:abstain"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg_text = (
        f"🗳 <b>動議 #{motion_id}: {html.escape(title)}</b>\n\n"
        f"{html.escape(content)}\n\n"
        f"提案人：{user.mention_html()}\n"
        f"狀態：進行中"
    )
    
    await update.message.reply_text(msg_text, reply_markup=reply_markup, parse_mode='HTML')

async def vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    
    # Verify user is arbitrator
    if not is_arbitrator(user.id):
        await query.answer("⛔ 您無權投票。", show_alert=True)
        return
        
    # Verify group
    if query.message.chat.id != config['arbcom_group_id']:
        await query.answer("⛔ 只能在授權群組中投票。", show_alert=True)
        return

    data = query.data.split(':')
    if len(data) != 3 or data[0] != 'vote':
        await query.answer("無效的投票數據。")
        return
        
    motion_id = int(data[1])
    vote_type = data[2]
    
    motion = get_motion_db(motion_id)
    if not motion or motion['status'] != 'active':
        await query.answer("⚠️ 此動議已關閉。", show_alert=True)
        return

    record_vote_db(motion_id, user.id, user.username, vote_type)
    
    # Log the vote
    logging.info(f"Vote cast: User {user.username} ({user.id}) voted {vote_type} on motion #{motion_id}")
    
    vote_map = {"support": "支持", "oppose": "反對", "abstain": "棄權"}
    await query.answer(f"投票已記錄：{vote_map.get(vote_type, vote_type)}")
    
    # Update message
    votes = get_motion_votes_db(motion_id)
    support = sum(1 for v in votes if v['vote_type'] == 'support')
    oppose = sum(1 for v in votes if v['vote_type'] == 'oppose')
    abstain = sum(1 for v in votes if v['vote_type'] == 'abstain')
    
    keyboard = [
        [
            InlineKeyboardButton(f"支持 ({support})", callback_data=f"vote:{motion_id}:support"),
            InlineKeyboardButton(f"反對 ({oppose})", callback_data=f"vote:{motion_id}:oppose"),
            InlineKeyboardButton(f"棄權 ({abstain})", callback_data=f"vote:{motion_id}:abstain"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Only edit if changed (Telegram API throws error if same)
    try:
        await query.edit_message_reply_markup(reply_markup=reply_markup)
    except Exception:
        pass

    # Check for auto-close conditions
    active_count_str = get_setting_db('active_arbitrator_count')
    majority_threshold_str = get_setting_db('majority_threshold')
    
    if active_count_str and majority_threshold_str:
        active_count = int(active_count_str)
        threshold = int(majority_threshold_str)
        
        should_close = False
        outcome = None
        reason = ""
        
        # Condition 1: Support reaches threshold -> Pass
        if support >= threshold:
            should_close = True
            outcome = "通過"
            reason = f"達到絕對多數門檻 ({threshold}票)"
            
        # Condition 2: Impossible to reach threshold -> Fail
        # Remaining votes = Active - (Support + Oppose + Abstain)
        # Max possible support = Support + Remaining
        # If Max possible support < Threshold -> Fail
        # Note: This assumes votes are final for the purpose of auto-close, 
        # or that we want to close as soon as it's mathematically impossible 
        # assuming current non-support votes stick.
        # Given user requirement: "if it is already impossible to reach absolute majority... voting should be terminated"
        total_votes_cast = support + oppose + abstain
        remaining_votes = active_count - total_votes_cast
        max_possible_support = support + remaining_votes
        
        if max_possible_support < threshold:
            should_close = True
            outcome = "未通過"
            reason = f"無法達到絕對多數門檻 (最大可能支持票: {max_possible_support}, 門檻: {threshold})"
            
        if should_close:
            await execute_close_motion(context, motion_id, outcome, reason)

@restricted
async def list_motions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    motions = get_active_motions_db()
    if not motions:
        await update.message.reply_text("目前沒有進行中的動議。")
        return
        
    msg = "<b>進行中的動議：</b>\n"
    for m in motions:
        msg += f"- #{m['id']}: {html.escape(m['title'])} (提案人：{html.escape(m['creator_username'] or 'Unknown')})\n"
        
    await update.message.reply_text(msg, parse_mode='HTML')

@restricted
async def close_motion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("用法：/close_motion <動議ID>")
        return
        
    try:
        motion_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("無效的動議ID。")
        return
        
    motion = get_motion_db(motion_id)
    if not motion:
        await update.message.reply_text("找不到該動議。")
        return
        
    if motion['status'] != 'active':
        await update.message.reply_text("該動議已經關閉。")
        return
        
    close_motion_db(motion_id)
    
    # Calculate results
    votes = get_motion_votes_db(motion_id)
    support = sum(1 for v in votes if v['vote_type'] == 'support')
    oppose = sum(1 for v in votes if v['vote_type'] == 'oppose')
    abstain = sum(1 for v in votes if v['vote_type'] == 'abstain')
    
    if support > oppose:
        outcome = "通過"
    elif oppose > support:
        outcome = "未通過"
    else:
        outcome = "平局"
        
    await execute_close_motion(context, motion_id, outcome, "手動關閉")
    await update.message.reply_text(f"動議 #{motion_id} 已關閉並存檔。")

async def execute_close_motion(context, motion_id, outcome, reason):
    motion = get_motion_db(motion_id)
    if not motion:
        return
        
    # Ensure it's closed in DB if not already (for manual close it is, for auto it might not be)
    if motion['status'] == 'active':
        close_motion_db(motion_id)
        
    votes = get_motion_votes_db(motion_id)
    support = sum(1 for v in votes if v['vote_type'] == 'support')
    oppose = sum(1 for v in votes if v['vote_type'] == 'oppose')
    abstain = sum(1 for v in votes if v['vote_type'] == 'abstain')
    
    # Format voter list
    support_voters = [v['username'] or str(v['user_id']) for v in votes if v['vote_type'] == 'support']
    oppose_voters = [v['username'] or str(v['user_id']) for v in votes if v['vote_type'] == 'oppose']
    abstain_voters = [v['username'] or str(v['user_id']) for v in votes if v['vote_type'] == 'abstain']
    
    voter_list = ""
    if support_voters:
        voter_list += f"✅ <b>支持 ({support}):</b> {', '.join(support_voters)}\n"
    if oppose_voters:
        voter_list += f"❌ <b>反對 ({oppose}):</b> {', '.join(oppose_voters)}\n"
    if abstain_voters:
        voter_list += f"⚪ <b>棄權 ({abstain}):</b> {', '.join(abstain_voters)}\n"
    
    # Archive
    archive_text = (
        f"🗳 <b>動議 #{motion_id} 已關閉</b>\n"
        f"<b>標題：</b> {html.escape(motion['title'])}\n"
        f"<b>內容：</b> {html.escape(motion['content'])}\n"
        f"<b>提案人：</b> {html.escape(motion['creator_username'] or 'Unknown')}\n\n"
        f"<b>結果：</b>\n"
        f"{voter_list}\n"
        f"<b>最終結果：</b> {outcome}\n"
        f"<b>備註：</b> {reason}"
    )
    
    try:
        await context.bot.send_message(config['archive_channel_id'], archive_text, parse_mode='HTML')
        # Also notify group if auto-closed
        if reason != "手動關閉":
             await context.bot.send_message(config['arbcom_group_id'], f"ℹ️ 動議 #{motion_id} 已自動關閉：{outcome} ({reason})", parse_mode='HTML')
    except Exception as e:
        print(f"Failed to archive motion #{motion_id}: {e}")

async def post_init(application: Application):
    """
    Post initialization hook to start background tasks.
    """
    loop = asyncio.get_running_loop()
    start_monitor(application, loop)

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    builder = ApplicationBuilder().token(config['bot_token'])
    builder.post_init(post_init)
    
    # Add proxy support if configured
    if config.get('proxy_url'):
        builder.proxy_url(config['proxy_url'])
        print(f"Using proxy: {config['proxy_url']}")
        
    application = builder.build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('add_arbitrator', add_arbitrator))
    application.add_handler(CommandHandler('remove_arbitrator', remove_arbitrator))
    application.add_handler(CommandHandler('list_arbitrators', list_arbitrators))
    application.add_handler(CommandHandler('set_threshold', set_threshold))
    
    # Handle members joining/leaving chats
    application.add_handler(ChatMemberHandler(greet_chat_members, ChatMemberHandler.CHAT_MEMBER))
    
    # Motion handlers
    application.add_handler(CommandHandler('motion', motion_command))
    application.add_handler(CommandHandler('list_motions', list_motions))
    application.add_handler(CommandHandler('close_motion', close_motion))
    application.add_handler(CallbackQueryHandler(vote_callback))
    
    print("Bot is running...")
    application.run_polling()

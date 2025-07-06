from telethon import TelegramClient, functions
from telethon.errors import RPCError

from app.errors import handle_gift_error
from app.notifications import send_notification
from app.utils.helper import get_recipient_info, get_user_balance
from app.utils.logger import success
from data.config import t


async def buy_gift(app: TelegramClient, chat_id: int, gift_id: int, quantity: int = 1) -> None:
    try:
        recipient_info, username = await get_recipient_info(app, chat_id)

        for i in range(quantity):
            current_gift = i + 1

            await app(functions.payments.SendGiftRequest(
                peer=chat_id,
                gift_id=gift_id,
                hide_sponsor=True
            ))

            success(t("console.gift_sent", current=current_gift, total=quantity,
                      gift_id=gift_id, recipient=recipient_info))

            await send_notification(app, gift_id, user_id=chat_id, username=username,
                                    current_gift=current_gift, total_gifts=quantity)

    except RPCError as ex:
        gift_price = 0
        current_balance = 0

        try:
            gifts_result = await app(functions.payments.GetAvailableGiftsRequest())
            for gift in getattr(gifts_result, "gifts", []):
                if getattr(gift, "id", None) == gift_id:
                    gift_price = getattr(gift, "price", 0)
                    break

            current_balance = await get_user_balance(app)
        except Exception:
            pass

        await handle_gift_error(app, ex, gift_id, chat_id, gift_price, current_balance)

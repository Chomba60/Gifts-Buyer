from typing import Dict, Any

from telethon import TelegramClient
from telethon.errors import RPCError

from app.notifications import send_notification
from app.utils.logger import error
from data.config import t


class ErrorHandler:
    @staticmethod
    def get_error_handlers() -> Dict[str, Dict[str, Any]]:
        return {
            'BALANCE_TOO_LOW': {
                'check': lambda e: 'BALANCE_TOO_LOW' in str(e),
                'log_message': 'low_balance',
                'notification_key': 'balance_error'
            },
            'STARGIFT_USAGE_LIMITED': {
                'check': lambda e: 'STARGIFT_USAGE_LIMITED' in str(e),
                'log_message': None,
                'notification_key': 'sold_out'
            },
            'PEER_ID_INVALID': {
                'check': lambda e: 'PEER_ID_INVALID' in str(e),
                'log_message': t("console.peer_id"),
                'notification_key': 'peer_id_error'
            }
        }


async def handle_gift_error(app: TelegramClient, ex: RPCError, gift_id: int, chat_id: int,
                            gift_price: int = 0, current_balance: int = 0) -> None:
    error_handlers = ErrorHandler.get_error_handlers()

    notification_data = {
        'balance_error': {'balance_error': True, 'gift_price': gift_price, 'current_balance': current_balance},
        'sold_out': {'sold_out': True},
        'peer_id_error': {'peer_id_error': True}
    }

    for handler in error_handlers.values():
        if handler['check'](ex):
            if handler['log_message']:
                if handler['log_message'] == 'low_balance':
                    error(t("console.low_balance", gift_id=gift_id))
                else:
                    error(handler['log_message'])

            notification_key = handler['notification_key']
            if notification_key in notification_data:
                await send_notification(app, gift_id, **notification_data[notification_key])
            return

    error(t("console.gift_send_error", gift_id=gift_id, chat_id=chat_id))
    error(str(ex))
    await send_notification(app, gift_id, error_message=f"<pre>{str(ex)}</pre>")

import asyncio
import json
import time
from typing import Any, Callable, Dict, List, Tuple

from telethon import TelegramClient
from telethon import functions

from app.notifications import send_summary_message
from app.utils.logger import log_same_line, info
from data.config import config, t


async def load_old_gifts() -> Dict[int, dict]:
    try:
        with config.DATA_FILEPATH.open("r", encoding='utf-8') as file:
            return {gift["id"]: gift for gift in json.load(file)}
    except FileNotFoundError:
        return {}


async def save_gifts(gifts: List[dict]) -> None:
    with config.DATA_FILEPATH.open("w", encoding='utf-8') as file:
        json.dump(gifts, file, indent=4, ensure_ascii=False)


async def get_current_gifts(app: TelegramClient) -> Tuple[Dict[int, dict], List[int]]:
    result = await app(functions.payments.GetAvailableGiftsRequest())
    gifts = [gift.to_dict() for gift in getattr(result, "gifts", [])]
    gifts_dict = {gift["id"]: gift for gift in gifts}
    return gifts_dict, list(gifts_dict.keys())


def categorize_gift_skips(gift_data: Dict[str, Any]) -> Dict[str, int]:
    skip_categories = {
        'sold_out_count': gift_data.get("is_sold_out", False),
        'non_limited_count': not gift_data.get("is_limited") and not config.PURCHASE_NON_LIMITED_GIFTS,
        'non_upgradable_count': config.PURCHASE_ONLY_UPGRADABLE_GIFTS and "upgrade_price" not in gift_data
    }

    return {key: 1 if condition else 0 for key, condition in skip_categories.items()}


async def detector(app: TelegramClient, callback: Callable) -> None:
    dot_count = 0

    while True:
        dot_count = (dot_count + 1) % 4
        log_same_line(f'{t("console.gift_checking")}{"." * dot_count}')
        time.sleep(0.2)

        if not app.is_connected():
            await app.connect()

        old_gifts = await load_old_gifts()
        current_gifts, gift_ids = await get_current_gifts(app)

        new_gifts = {
            gift_id: gift_data for gift_id, gift_data in current_gifts.items()
            if gift_id not in old_gifts
        }

        if new_gifts:
            info(f'{t("console.new_gifts")} {len(new_gifts)}')

            total_gifts = len(gift_ids)
            skip_counts = {'sold_out_count': 0, 'non_limited_count': 0, 'non_upgradable_count': 0}

            for gift_id, gift_data in new_gifts.items():
                gift_data["number"] = total_gifts - gift_ids.index(gift_id)

                gift_skips = categorize_gift_skips(gift_data)
                for key, value in gift_skips.items():
                    skip_counts[key] += value

            sorted_gifts = sorted(new_gifts.items(), key=lambda x: x[1]["number"])

            if config.PRIORITIZE_LOW_SUPPLY:
                sorted_gifts = sorted(sorted_gifts, key=lambda x: (
                    x[1].get("total_amount", float('inf')) if x[1].get("is_limited", False) else float('inf'),
                    x[1]["number"]
                ))

            for gift_id, gift_data in sorted_gifts:
                await callback(app, gift_data)

            await send_summary_message(app, **skip_counts)

            if any(skip_counts.values()):
                info(t("console.skip_summary",
                       sold_out=skip_counts['sold_out_count'],
                       non_limited=skip_counts['non_limited_count'],
                       non_upgradable=skip_counts['non_upgradable_count']))

        await save_gifts(list(current_gifts.values()))
        await asyncio.sleep(config.INTERVAL)

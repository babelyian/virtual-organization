from datetime import datetime, timedelta

TIME_INTERVALS = {
    "last_week": ((datetime.now() - timedelta(days=7)).isoformat(), datetime.now().isoformat()),
    "last_month": ((datetime.now() - timedelta(days=30)).isoformat(), datetime.now().isoformat()),
    "next_week": (datetime.now().isoformat(), (datetime.now() + timedelta(days=7)).isoformat()),
    "next_month": (datetime.now().isoformat(), (datetime.now() + timedelta(days=30)).isoformat()),
    "today": (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
              datetime.now().isoformat()),
    "yesterday": ((datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
                  (datetime.now() - timedelta(days=1)).replace(hour=23, minute=59, second=59).isoformat()),
}
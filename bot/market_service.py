from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


FIXED_TIMEZONES = {
    "Europe/Madrid": timezone(timedelta(hours=1), "Europe/Madrid"),
    "America/New_York": timezone(timedelta(hours=-5), "America/New_York"),
    "America/Argentina/Buenos_Aires": timezone(timedelta(hours=-3), "America/Argentina/Buenos_Aires"),
    "America/Mexico_City": timezone(timedelta(hours=-6), "America/Mexico_City"),
    "America/Bogota": timezone(timedelta(hours=-5), "America/Bogota"),
    "America/Santiago": timezone(timedelta(hours=-4), "America/Santiago"),
    "America/Caracas": timezone(timedelta(hours=-4), "America/Caracas"),
    "Asia/Tokyo": timezone(timedelta(hours=9), "Asia/Tokyo"),
}


DEFAULT_TIMEZONE = FIXED_TIMEZONES["Europe/Madrid"]


def timezone_or_default(timezone_name: str):
    try:
        return ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, Exception):
        pass
    try:
        import pytz
        return pytz.timezone(timezone_name)
    except Exception:
        return FIXED_TIMEZONES.get(timezone_name, DEFAULT_TIMEZONE)


def _localize(tz, value: datetime) -> datetime:
    if hasattr(tz, "localize"):
        return tz.localize(value)
    return value.replace(tzinfo=tz)


def obtener_estado_mercados(user_tz=DEFAULT_TIMEZONE) -> str:
    ahora_user = datetime.now(user_tz)
    texto = f"🌍 **MERCADOS (Hora Local: {ahora_user.strftime('%H:%M')})**\n\n"

    fases = [
        ("🇯🇵 Asia (Tokio)", "Asia/Tokyo", (9, 0), (18, 0)),
        ("🇪🇺 Europa (Madrid/Londres)", "Europe/Madrid", (9, 0), (17, 30)),
        ("🇺🇸 EE.UU. (Nueva York)", "America/New_York", (9, 30), (16, 0)),
    ]

    is_europe_open = False
    is_us_open = False

    for nombre, market_tz_str, (h_ap, m_ap), (h_ci, m_ci) in fases:
        market_tz = timezone_or_default(market_tz_str)
        now_market = datetime.now(market_tz)

        is_weekend = now_market.weekday() > 4
        open_time = time(h_ap, m_ap)
        close_time = time(h_ci, m_ci)
        current_time = now_market.time()
        is_open = not is_weekend and (open_time <= current_time <= close_time)
        estado = "🟢" if is_open else "🔴"

        if "Europa" in nombre and is_open:
            is_europe_open = True
        if "EE.UU." in nombre and is_open:
            is_us_open = True

        dt_open_market = _localize(market_tz, datetime.combine(now_market.date(), open_time))
        dt_close_market = _localize(market_tz, datetime.combine(now_market.date(), close_time))
        dt_open_user = dt_open_market.astimezone(user_tz)
        dt_close_user = dt_close_market.astimezone(user_tz)
        horario_texto = f"{dt_open_user.strftime('%H:%M')} - {dt_close_user.strftime('%H:%M')}"

        if is_weekend:
            texto += f"🔴 **{nombre}** (Cerrado por Fin de Semana)\n"
        else:
            texto += f"{estado} **{nombre}** ({horario_texto})\n"

    if is_europe_open and is_us_open:
        texto += "\n🔥 **SOLAPAMIENTO DETECTADO**: Máximo volumen NYSE + Europa."

    return texto

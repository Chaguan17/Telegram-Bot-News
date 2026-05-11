SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]


def format_prices(rows: list[dict]) -> str:
    prices = {item["symbol"]: float(item["price"]) for item in rows}
    msg = "💰 **ACTUALIZACIÓN DE PRECIOS**\n\n"
    msg += f"• **BTC**: `${prices.get('BTCUSDT', 0):,.2f}`\n"
    msg += f"• **ETH**: `${prices.get('ETHUSDT', 0):,.2f}`\n"
    msg += f"• **BNB**: `${prices.get('BNBUSDT', 0):,.2f}`"
    return msg


async def obtener_precios_with_async_loader(price_loader) -> str:
    try:
        return format_prices(await price_loader(SYMBOLS))
    except Exception as e:
        print(f"Error Binance: {e}")
        return "❌ Error al conectar con Binance API."

import asyncio
import json
import logging

from aiohttp import ClientSession

from pathlib import Path


async def get_cost_eth_btc_usdt():
    """
    Получение текущей стоимости BTSUSDT и ETHUSDT
    :return: None
    """
    async with ClientSession() as session:
        async with session.get(
            url="https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        ) as response:
            btc = await response.json()
        async with session.get(
            url="https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT"
        ) as response:
            eth = await response.json()

    path = Path("history.json")
    data = json.loads(path.read_text(encoding="utf-8"))

    if "btc" and "eth" in data.keys():
        data["btc"].append(btc["price"])
        data["eth"].append(eth["price"])
    else:
        data["btc"] = [btc["price"]]
        data["eth"] = [eth["price"]]

    path.write_text(json.dumps(data), encoding="utf-8")


async def calculate_correlation():
    """
    Данная функция подсчитывает значение корреляции между ETH и BTC за последний час исходя из стоимости монет
    :return Значение корреляции между ETH и BTC за последний час:
    """
    path = Path("history.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    list_btc_cost = data["btc"][-100]  # Данные по стоимости BTC за последний час
    list_eth_cost = data["eth"][-100]  # Данные по стоимости ETH за последний час

    average_btc_cost = sum(list_btc_cost) / 100
    average_eth_cost = sum(list_eth_cost) / 100

    list_deviations_from_the_average_cost_btc = list(
        map(lambda cost: cost - average_btc_cost, list_btc_cost)
    )
    list_deviations_from_the_average_cost_eth = list(
        map(lambda cost: cost - average_eth_cost, list_eth_cost)
    )

    list_deviations = list(
        map(
            lambda cost_btc, cost_eth: cost_btc * cost_eth,
            list_deviations_from_the_average_cost_btc,
            list_deviations_from_the_average_cost_eth,
        )
    )

    standard_deviation_btc = (
        sum(
            list(
                map(
                    lambda deviations: deviations**2,
                    list_deviations_from_the_average_cost_btc,
                )
            )
        )
        ** 0.5
    )
    standard_deviation_eth = (
        sum(
            list(
                map(
                    lambda deviations: deviations**2,
                    list_deviations_from_the_average_cost_eth,
                )
            )
        )
        ** 0.5
    )

    correlation = sum(list_deviations) / (
        standard_deviation_btc * standard_deviation_eth
    )

    return correlation


async def notify_excluding_dependency():
    """
    Данная функция уведомляет при изменении стоимости за последний час как BTC, так и ETH как с учетом корреляции, так и без ее учета
    :return: None
    """
    path = Path("history.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    btc_changing = (data["btc"][-100] / data["btc"][-1]) * 100 - 100
    eth_changing = (data["eth"][-100] / data["eth"][-1]) * 100 - 100
    correlation = await calculate_correlation()
    if abs(btc_changing) >= 1:
        logging.warning(
            f"Стоимость BTCUSDT изменилась на {btc_changing} за последние 60 минут"
        )
    if abs(eth_changing) >= 1:
        logging.warning(
            f"Стоимость ETHUSDT изменилась на {eth_changing} за последние 60 минут без учета стоимости BTCUSDT"
        )
    if abs(eth_changing - btc_changing * correlation) >= 1:
        logging.error(
            f"Стоимость ETHUSDT изменилась на {eth_changing} за последние 60 минут при учете стоимости BTCUSDT"
        )


async def main():
    """
    Данная функция лишь запускает все остальные функции в нужном порядке и с нужной задержкой
    :return: None
    """
    path = Path("history.json")
    path.write_text(
        json.dumps({}), encoding="utf-8"
    )  # очистка файла с данными при запуске приложения, чтобы предыдущие значения не влияли на результат программы
    while True:
        await get_cost_eth_btc_usdt()
        await asyncio.sleep(6)  # следующая функция вызовется лишь через 6 секунд
        await notify_excluding_dependency()


if __name__ == "__main__":
    asyncio.run(main())

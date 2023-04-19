#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import asyncio
import decimal
import typing

import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_trading.exchanges as exchanges
import octobot_trading.enums as trading_enums


class Phemex(exchanges.RestExchange):
    DESCRIPTION = ""

    @classmethod
    def get_name(cls):
        return 'phemex'

    def get_adapter_class(self):
        return PhemexCCXTAdapter

    async def create_order(self, order_type: trading_enums.TraderOrderType, symbol: str, quantity: decimal.Decimal,
                           price: decimal.Decimal = None, stop_price: decimal.Decimal = None,
                           side: trading_enums.TradeOrderSide = None, current_price: decimal.Decimal = None,
                           reduce_only: bool = False, params: dict = None) -> typing.Optional[dict]:
        if order_type is trading_enums.TraderOrderType.BUY_MARKET \
                or order_type is trading_enums.TraderOrderType.SELL_MARKET:
            # remove price argument on market orders or ccxt will try to convert cost into amount and
            # make rounding differences
            price = None
        return await super().create_order(order_type, symbol, quantity,
                                          price=price, stop_price=stop_price,
                                          side=side, current_price=current_price,
                                          reduce_only=reduce_only, params=params)

    def _get_ohlcv_params(self, time_frame, limit, **kwargs):
        to_time = self.connector.client.milliseconds()
        time_frame_msec = commons_enums.TimeFramesMinutes[time_frame] * commons_constants.MSECONDS_TO_MINUTE
        kwargs.update({
            "from": to_time - (time_frame_msec * (limit + 1)),
            "limit": limit,
        })
        return kwargs

    async def get_symbol_prices(self, symbol: str, time_frame: commons_enums.TimeFrames, limit: int = None,
                                **kwargs: dict) -> typing.Optional[list]:
        # without limit is not supported
        if limit is None:
            limit = 100
        return await super().get_symbol_prices(
            symbol=symbol, time_frame=time_frame, **self._get_ohlcv_params(time_frame, limit, **kwargs)
        )

    async def get_order(self, order_id: str, symbol: str = None, **kwargs: dict) -> dict:
        if order := await self.connector.get_order(symbol=symbol, order_id=order_id, **kwargs):
            return order
        # try from closed orders (get_order is not returning filled or cancelled orders)
        if order := await self.get_order_from_open_and_closed_orders(order_id, symbol):
            return order
        # try from trades (get_order is not returning filled or cancelled orders)
        return await self._get_order_from_trades(symbol, order_id, {})

    async def _get_order_from_trades(self, symbol, order_id, order_to_update):
        # usually the last trade is the right one
        for _ in range(3):
            if (order := await self.get_order_from_trades(symbol, order_id, order_to_update)) is None:
                await asyncio.sleep(3)
            else:
                return order
        raise KeyError("Order id not found in trades. Impossible to build order from trades history")

    def get_market_status(self, symbol, price_example=None, with_fixer=True):
        return self.get_fixed_market_status(symbol, price_example=price_example, with_fixer=with_fixer)


class PhemexCCXTAdapter(exchanges.CCXTAdapter):
    PHEMEX_FEE_CURRENCY = "feeCurrency"

    def fix_order(self, raw, **kwargs):
        fixed = super().fix_order(raw, **kwargs)
        try:
            if fixed[
                trading_enums.ExchangeConstantsOrderColumns.STATUS.value
            ] == trading_enums.OrderStatus.CLOSED.value \
                    and fixed[trading_enums.ExchangeConstantsOrderColumns.FEE.value][
               trading_enums.FeePropertyColumns.CURRENCY.value] is None:
                order_info = fixed[trading_enums.ExchangeConstantsOrderColumns.INFO.value]
                fixed[trading_enums.ExchangeConstantsOrderColumns.FEE.value][
                    trading_enums.FeePropertyColumns.CURRENCY.value] = order_info[self.PHEMEX_FEE_CURRENCY]
        except KeyError as err:
            self.logger.debug(f"Failed to fix order fees: {err}")
        return fixed
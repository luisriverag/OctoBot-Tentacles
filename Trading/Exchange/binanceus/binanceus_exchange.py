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
import tentacles.Trading.Exchange.binance as binance_tentacle
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants


class BinanceUS(binance_tentacle.Binance):
    @classmethod
    def get_name(cls):
        return 'binanceus'

    @classmethod
    def get_supported_exchange_types(cls) -> list:
        """
        :return: The list of supported exchange types
        """
        return [
            trading_enums.ExchangeTypes.SPOT,
        ]

    def get_additional_connector_config(self):
        config = super().get_additional_connector_config()
        # override to fix ccxt values
        config[ccxt_constants.CCXT_FEES] = {
            'trading': {
                'tierBased': True,
                'percentage': True,
                # ccxt replaced values
                # 'taker': float('0.001'),  # 0.1% trading fee, zero fees for all trading pairs before November 1.
                # 'maker': float('0.001'),  # 0.1% trading fee, zero fees for all trading pairs before November 1.
                # 03/03/2025 values https://www.binance.us/fees
                'taker': float('0.006'),  # 0.600%
                'maker': float('0.004'),  # 0.400%
            },
        }
        return config

    async def get_account_id(self, **kwargs: dict) -> str:
        # not available on binance.us
        # see https://docs.binance.us/#get-user-account-information-user_data
        # vs "uid" in regular binance https://binance-docs.github.io/apidocs/spot/en/#spot-account-endpoints
        return trading_constants.DEFAULT_ACCOUNT_ID

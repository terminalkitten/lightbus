import asyncio

import logging
from asyncio.futures import CancelledError

from random import random

import pytest
import lightbus
from lightbus.exceptions import SuddenDeathException, LightbusTimeout
from lightbus.utilities import handle_aio_exceptions


@pytest.mark.run_loop  # TODO: Have test repeat a few times
async def test_random_failures(bus: lightbus.BusNode, caplog, consume_rpcs, call_rpc, mocker, dummy_api, loop):
    caplog.set_level(logging.WARNING)
    loop.slow_callback_duration = 0.01
    results = []

    async def do_single_call(n):
        nonlocal results
        try:
            result = await bus.my.dummy.random_death.call_async(n=n, death_probability=0.5)
            results.append(result)
        except LightbusTimeout:
            results.append(None)

    async def co_call_rpc():
        asyncio.sleep(0.1)
        fut = asyncio.gather(*[
            do_single_call(n)
            for n in range(0, 100)
        ])
        await fut
        return fut.result()

    async def co_consume_rpcs():
        return await bus.bus_client.consume_rpcs(apis=[dummy_api])

    (call_task, ), (consume_task, ) = await asyncio.wait([co_call_rpc(), co_consume_rpcs()], return_when=asyncio.FIRST_COMPLETED)
    call_task.result()
    consume_task.cancel()
    try:
        await consume_task
        consume_task.result()
    except CancelledError:
        pass

    total_successful = len([r for r in results if r is not None])
    total_timeouts = len([r for r in results if r is None])
    assert len(results) == 100
    assert total_successful > 0
    assert total_timeouts > 0


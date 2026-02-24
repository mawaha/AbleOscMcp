"""Integration test fixtures — require a live Ableton + AbletonOSC instance."""

from __future__ import annotations

import os

import pytest

from ableosc.client import OscClient

# Skip all integration tests unless explicitly enabled
if not os.getenv("ABLEOSC_INTEGRATION"):
    pytest.skip(
        "Set ABLEOSC_INTEGRATION=1 to run integration tests against Ableton Live",
        allow_module_level=True,
    )


@pytest.fixture(scope="function")
async def live_client():
    """Real OscClient connected to Ableton Live with AbletonOSC."""
    client = OscClient(
        host=os.getenv("ABLEOSC_HOST", "127.0.0.1"),
        send_port=int(os.getenv("ABLEOSC_SEND_PORT", "11000")),
        receive_port=int(os.getenv("ABLEOSC_RECEIVE_PORT", "11001")),
    )
    await client.start()

    alive = await client.ping()
    if not alive:
        pytest.skip("AbletonOSC did not respond. Is Ableton Live running?")

    yield client
    await client.stop()

"""Objects intended for creating async behavior"""

import asyncio

from gi.events import GLibEventLoopPolicy  # type: ignore  # noqa: PGH003

policy = GLibEventLoopPolicy()
event_loop: asyncio.EventLoop = policy.get_event_loop()
event_loop.set_exception_handler(None)
asyncio.set_event_loop_policy(policy)

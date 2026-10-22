import sys
from time import monotonic, perf_counter

from anyio import sleep as anyio_sleep

WINDOWS = sys.platform == "win32"


if WINDOWS:
    time = perf_counter
else:
    time = monotonic


if WINDOWS:
    # sleep on windows as a resolution of 15ms
    # Python3.11 is somewhat better, but this home-grown version beats it
    # Deduced from practical experiments

    from textual._win_sleep import sleep as win_sleep

    async def sleep(secs: float) -> None:
        """Sleep for a given number of seconds.

        Args:
            secs: Number of seconds to sleep for.
        """
        await win_sleep(secs)

else:

    async def sleep(secs: float) -> None:
        """Sleep for a given number of seconds.

        Args:
            secs: Number of seconds to sleep for.
        """
        # Compensate for scheduling overhead in animation timers.
        # We will reduce the sleep to compensate, and also don't sleep at all for less than half a millisecond
        sleep_for = secs - 0.0005
        if sleep_for > 0:
            await anyio_sleep(sleep_for)


get_time = time
"""Get the current wall clock (monotonic) time.

Returns:
    The value (in fractional seconds) of a monotonic clock,
    i.e. a clock that cannot go backwards.
"""

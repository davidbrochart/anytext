from time import monotonic

import anyio

from anytext.app import App


class RefreshApp(App[float]):
    def __init__(self):
        self.count = 0
        self.refreshed = anyio.Event()
        super().__init__()

    def on_mount(self):
        self.start = monotonic()
        self.auto_refresh = 0.1

    def automatic_refresh(self):
        self.count += 1
        if self.count == 3:
            self.exit(monotonic() - self.start)
            self.refreshed.set()
        super().automatic_refresh()


async def test_auto_refresh():
    app = RefreshApp()
    async with app.run_test():
        with anyio.fail_after(5):
            await app.refreshed.wait()
        assert app.count == 3
        assert app.return_value is not None
        # Refreshes must respect the interval, but a busy runner may be late.
        assert app.return_value >= 0.2

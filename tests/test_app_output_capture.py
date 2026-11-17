"""Embedded apps leave their host's process streams untouched."""

import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

import anyio
import pytest

from anytext.app import App
from anytext.drivers.callback_driver import CallbackDriver


@pytest.mark.parametrize("capture", [False, True])
async def test_capture_option(capture):
    output, errors = StringIO(), StringIO()

    class CaptureApp(App):
        def on_mount(self):
            assert (sys.stdout is output) is not capture
            assert (sys.stderr is errors) is not capture
            print("stdout-marker")
            print("stderr-marker", file=sys.stderr)
            self.exit()

    with redirect_stdout(output), redirect_stderr(errors):
        await CaptureApp(capture_output=capture).run_async(headless=True)
        assert sys.stdout is output
        assert sys.stderr is errors
    assert ("stdout-marker" in output.getvalue()) is not capture
    assert ("stderr-marker" in errors.getvalue()) is not capture


async def test_concurrent_callback_apps_preserve_host_streams():
    output, errors = StringIO(), StringIO()
    ready = [anyio.Event(), anyio.Event()]
    stopped = [anyio.Event(), anyio.Event()]
    frames = [[], []]
    apps = []

    for index in range(2):

        class EmbeddedApp(App):
            def on_mount(self):
                ready[self.index].set()

        app = EmbeddedApp(
            capture_output=False,
            driver_class=lambda app, **options: CallbackDriver(
                app, output=frames[app.index].append, **options
            ),
        )
        app.index = index
        apps.append(app)

    async def run_app(index):
        try:
            await apps[index].run_async(size=(40, 10))
        finally:
            stopped[index].set()

    with redirect_stdout(output), redirect_stderr(errors):
        with anyio.fail_after(10):
            async with anyio.create_task_group() as task_group:
                task_group.start_soon(run_app, 0)
                task_group.start_soon(run_app, 1)
                await ready[0].wait()
                await ready[1].wait()
                assert sys.stdout is output
                assert sys.stderr is errors
                apps[0].exit()
                await stopped[0].wait()
                assert apps[1].is_running
                assert sys.stdout is output
                assert sys.stderr is errors
                print("host-stdout")
                print("host-stderr", file=sys.stderr)
                apps[1].exit()
                await stopped[1].wait()
        assert sys.stdout is output
        assert sys.stderr is errors
    assert output.getvalue() == "host-stdout\n"
    assert errors.getvalue() == "host-stderr\n"
    assert all(frames)


async def test_suspend_preserves_host_streams():
    class SuspendDriver(CallbackDriver):
        @property
        def can_suspend(self):
            return True

    output, errors = StringIO(), StringIO()
    app = App(
        capture_output=False,
        driver_class=lambda app, **options: SuspendDriver(
            app, output=lambda text: None, **options
        ),
    )

    async def suspend(pilot):
        async with app.suspend():
            assert sys.stdout is output
            assert sys.stderr is errors
            print("while-suspended")
        assert sys.stdout is output
        assert sys.stderr is errors
        app.exit()

    with redirect_stdout(output), redirect_stderr(errors):
        await app.run_async(auto_pilot=suspend, size=(40, 10))
        assert sys.stdout is output
        assert sys.stderr is errors
    assert output.getvalue() == "while-suspended\n"

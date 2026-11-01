"""Exercise the application lifecycle on both supported AnyIO backends."""

from contextvars import Context

import anyio
import pytest
import sniffio

from anytext import _async, work
from anytext._queue import Queue
from anytext.app import App, ComposeResult
from anytext.await_complete import AwaitComplete
from anytext.screen import ModalScreen
from anytext.widgets import Button, Label, Markdown
from anytext.worker import WorkerCancelled


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_app_lifecycle(backend):
    class TestApp(App):
        def compose(self) -> ComposeResult:
            yield Label("ready")
            yield Button("Exit")

        def on_button_pressed(self):
            self.exit(42)

    async def check():
        app = TestApp()
        async with app.run_test() as pilot:
            await pilot.click(Button)
        assert app.return_value == 42
        assert app._runtime is None

    anyio.run(check, backend=backend)


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_workers_and_thread_handoff(backend):
    class TestApp(App):
        @work(thread=True)
        def threaded(self):
            return self.call_from_thread(lambda: "thread result")

        @work(thread=True)
        async def async_threaded(self):
            await anyio.sleep(0)
            return sniffio.current_async_library()

        @work
        async def cancellable(self):
            await anyio.sleep_forever()

    async def check():
        app = TestApp()
        async with app.run_test() as pilot:
            assert await app.threaded().wait() == "thread result"
            assert await app.async_threaded().wait() == backend
            worker = app.cancellable()
            worker.cancel()
            with pytest.raises(WorkerCancelled):
                await worker.wait()
            # An AnyIO worker may post messages back to the UI task.
            await anyio.to_thread.run_sync(app.post_message, Button.Pressed(Button()))
            await pilot.pause()

    anyio.run(check, backend=backend)


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_results_timers_and_markdown(backend):
    async def check():
        app = App()
        async with app.run_test() as pilot:
            fired = anyio.Event()
            app.set_timer(0.001, fired.set)
            with anyio.fail_after(2):
                await fired.wait()

            async def dialog():
                return await app.push_screen_wait(ModalScreen())

            dialog_worker = app.run_worker(dialog())
            await pilot.pause()
            await app.screen.dismiss(123)
            assert await dialog_worker.wait() == 123
            # Result futures can be awaited repeatedly, including from AnyIO tasks.
            result = _async.Future()
            result.set_result(123)
            assert await result == 123
            assert await result == 123
            markdown = Markdown()
            await app.mount(markdown)
            await markdown.update("# AnyIO")
            assert markdown.query("MarkdownH1")
            operation = AwaitComplete(anyio.sleep(0))
            await operation
            assert operation.is_done
            await pilot.pause()

    anyio.run(check, backend=backend)


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_shutdown_on_cancellation_and_errors(backend):
    async def check():
        app = App()
        with anyio.move_on_after(0.05) as scope:
            await app.run_async(headless=True)
        assert scope.cancel_called
        assert app._runtime is None

        app = App()
        with pytest.raises(ValueError, match="original error"):
            async with app.run_test():
                raise ValueError("original error")
        assert app._runtime is None

    anyio.run(check, backend=backend)


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_queue_multiple_consumers(backend):
    async def check():
        queue = Queue[int]()
        received = []

        async def consume():
            received.append(await queue.get())
            queue.task_done()

        async with anyio.create_task_group() as group:
            group.start_soon(consume)
            group.start_soon(consume)
            await anyio.sleep(0)
            queue.put_nowait(1)
            await anyio.sleep(0)
            queue.put_nowait(2)
            await queue.join()
        assert sorted(received) == [1, 2]

    anyio.run(check, backend=backend)


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_run_backend(backend):
    async def exit_app(pilot):
        pilot.app.exit(17)

    assert App().run(headless=True, backend=backend, auto_pilot=exit_app) == 17


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_task_completion_and_timeouts(backend):
    async def check():
        async with _async.task_context():
            pending = _async.create_task(anyio.sleep_forever())
            done, remaining = await _async.wait([pending], timeout=0.001)
            assert not done
            assert remaining == {pending}
            pending.cancel()
            with pytest.raises(anyio.get_cancelled_exc_class()):
                await pending
            assert pending.done()

            async def fail():
                raise ValueError("task failure")

            task = _async.create_task(fail())
            with pytest.raises(ValueError, match="task failure"):
                await task

    anyio.run(check, backend=backend)


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_directory_tree_command_palette_and_streaming(backend, tmp_path):
    from anytext.widgets import DirectoryTree

    (tmp_path / "folder").mkdir()
    (tmp_path / "file.txt").write_text("test")

    async def check():
        app = App()
        async with app.run_test() as pilot:
            tree = DirectoryTree(tmp_path)
            markdown = Markdown()
            await app.mount(tree, markdown)
            await tree.reload()
            assert {child.label.plain for child in tree.root.children} == {
                "folder",
                "file.txt",
            }
            stream = Markdown.get_stream(markdown)
            await stream.write("# streamed")
            await stream.stop()
            assert markdown.query("MarkdownH1")
            app.action_command_palette()
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert len(app.screen_stack) == 1

    anyio.run(check, backend=backend)


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_runtime_loop_identity(backend):
    async def check():
        async with _async.task_context() as runtime:
            assert runtime.in_event_loop()
            assert Context().run(runtime.in_event_loop)
            assert not await anyio.to_thread.run_sync(runtime.in_event_loop)

    anyio.run(check, backend=backend)

from app.main import WorkerSettings


class TestWorkerSettings:
    def test_has_required_callbacks(self) -> None:
        assert callable(WorkerSettings.on_startup)
        assert callable(WorkerSettings.on_shutdown)

    def test_functions_list_exists(self) -> None:
        assert isinstance(WorkerSettings.functions, list)

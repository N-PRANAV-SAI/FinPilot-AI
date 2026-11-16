from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import time

import database.db as db_module


def test_init_db_runs_once_for_concurrent_calls(monkeypatch):
    monkeypatch.setattr(db_module, "_db_initialized", False)
    calls = 0
    calls_lock = Lock()

    def create_all(*, bind):
        nonlocal calls
        with calls_lock:
            calls += 1
        time.sleep(0.01)

    monkeypatch.setattr(db_module.Base.metadata, "create_all", create_all)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda _: db_module.init_db(), range(8)))

    assert calls == 1

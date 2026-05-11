"""
[SOVEREIGN STUB]: Direct Execution Task Registry

The enterprise Celery/Redis distributed queue was introduced as a future
certification target but requires external infrastructure (Redis server +
celery package) that is NOT available in the standalone desktop environment.

This stub satisfies all @celery_app.task decorators and send_task() calls
with zero external dependencies, restoring the original sovereign
direct-execution architecture via background threads.

When Redis and Celery are provisioned for a future cloud deployment, swap
this file for the full celery_app_cloud.py implementation.
"""

import functools
import threading

# [TASK REGISTRY]: Maps task name strings to their callable functions
# Populated at decoration time so send_task() can resolve by name.
_TASK_REGISTRY: dict = {}


class _MockSignature:
    """Mimics the Celery task .delay() and .apply_async() interface."""
    def __init__(self, func, name: str):
        self._func = func
        self._name = name

    def delay(self, *args, **kwargs):
        t = threading.Thread(target=self._func, args=args, kwargs=kwargs, daemon=True)
        t.start()

    def apply_async(self, args=None, kwargs=None, **options):
        t = threading.Thread(target=self._func, args=args or [], kwargs=kwargs or {}, daemon=True)
        t.start()

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)


class _SovereignTaskRegistry:
    """
    [SOVEREIGN STUB]: No-op task registry.
    Satisfies `@celery_app.task(...)` decorators and `send_task()` calls
    without Celery or Redis.
    """
    def task(self, *args, **kwargs):
        """Decorator factory that wraps the function in a direct-call shim."""
        task_name = kwargs.get('name', None)

        def decorator(func):
            name = task_name or f"{func.__module__}.{func.__qualname__}"
            sig = _MockSignature(func, name)
            functools.update_wrapper(sig, func)
            _TASK_REGISTRY[name] = sig
            return sig

        # Handle both @celery_app.task and @celery_app.task(name='...')
        if len(args) == 1 and callable(args[0]):
            return decorator(args[0])
        return decorator

    def send_task(self, name: str, args=None, kwargs=None, **options):
        """
        [SOVEREIGN DISPATCH]: Resolves task by name and runs it in a
        background daemon thread, matching Celery's async dispatch semantics.
        """
        task_fn = _TASK_REGISTRY.get(name)
        if task_fn is None:
            raise RuntimeError(
                f"[SOVEREIGN STUB]: Task '{name}' not found in registry. "
                f"Ensure the module containing the task has been imported first."
            )
        t = threading.Thread(
            target=task_fn._func,
            args=args or [],
            kwargs=kwargs or {},
            daemon=True
        )
        t.start()


app = _SovereignTaskRegistry()


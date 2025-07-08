import concurrent.futures
import queue
import threading
import time
import uuid
import logging
from cachetools import TTLCache

logger = logging.getLogger()


class AsyncTaskManager:
    def __init__(self, max_workers=10, ttl=3600):
        """
        Initialize async task manager

        Args:
            max_workers (int): Maximum number of worker threads
            ttl (int): Time-to-live for task results in seconds
        """
        self.max_workers = max_workers
        self.task_queue = queue.Queue()
        self.result_cache = TTLCache(maxsize=1000, ttl=ttl)
        self.result_cache_lock = threading.Lock()  # Protect cache from race conditions
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.workers = [
            threading.Thread(target=self.worker, daemon=True)
            for _ in range(max_workers)
        ]
        for w in self.workers:
            w.start()

    def worker(self):
        """Worker thread main loop that processes tasks"""
        while True:
            try:
                # Get next task from queue with timeout to allow shutdown detection
                task = self.task_queue.get()
                task_id, func, args, kwargs = task
                logger.info(f"Processing task {task_id}")
                # finish flag
                if task_id is None:
                    self.task_queue.task_done()
                    break

                # Update cache with running status
                with self.result_cache_lock:
                    self.result_cache[task_id] = {
                        "task_id": task_id,
                        "status": "running",
                        "result": None,
                    }

                # Execute task
                future = self.executor.submit(func, *args, **kwargs)
                result = future.result()
                status = "completed"

            except queue.Empty:
                # Handle queue empty timeout (normal operation)
                continue

            except Exception as e:
                # Handle task execution errors
                result = str(e)
                status = "failed"
                logger.error(f"Task {task_id} failed with error: {e}", exc_info=True)

            # Store final result in cache
            try:
                with self.result_cache_lock:
                    self.result_cache[task_id] = {
                        "task_id": task_id,
                        "status": status,
                        "result": result,
                    }
                logger.info(f"Task {task_id} completed with status: {status}")
            finally:
                # Always mark task as done
                self.task_queue.task_done()

    def submit_task(self, func, *args, **kwargs):
        """
        Submit a new task to the queue

        Args:
            func: Callable function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            str: Unique task ID
        """
        task_id = str(uuid.uuid4())
        self.task_queue.put((task_id, func, args, kwargs))
        return task_id

    def get_task_result(self, task_id):
        """
        Get result for a specific task

        Args:
            task_id (str): Unique task identifier

        Returns:
            dict: Task result information or expired status
        """
        with self.result_cache_lock:
            return self.result_cache.get(
                task_id,
                {
                    "task_id": task_id,
                    "status": "failed",
                    "result": "Result not found or expired",
                },
            )

    def shutdown(self):
        """Gracefully shutdown all worker threads and executors"""
        # Send shutdown signals
        for _ in range(self.max_workers):
            self.task_queue.put((None, None, (), {}))

        # Wait for queue to empty and workers to terminate
        self.task_queue.join()

        # Shutdown executors
        self.executor.shutdown(wait=True)
        for worker in self.workers:
            worker.join(timeout=5)


# Global async task manager instance
asyn_task = AsyncTaskManager()

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Create task manager instance
    task_manager = AsyncTaskManager(max_workers=5, ttl=600)

    # Example task function
    def example_task(x, y):
        time.sleep(1)  # Simulate work
        return x

    # Submit test tasks
    task_ids = [task_manager.submit_task(example_task, i, i + 1) for i in range(6)]

    # Monitor task progress
    try:
        while True:
            time.sleep(1)
            if all(
                "completed" in task_manager.get_task_result(tid)["status"]
                for tid in task_ids
            ):
                break
    except KeyboardInterrupt:
        logger.info("Shutting down due to user interrupt")

    # Print results
    for task_id in task_ids:
        print(f"Task {task_id} result: {task_manager.get_task_result(task_id)}")

    # Clean up resources
    task_manager.shutdown()

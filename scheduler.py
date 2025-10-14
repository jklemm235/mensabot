"""
Scheduler class that saves schedules of given functions and executes them at the specified times.
This class manages these scheduled function calls with persistence to a SQLite database.
For more info see the Scheduler class's docstring.
"""
import sqlite3
import os
import pickle
import inspect
from typing import List, Tuple, Callable, Optional, Dict
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.job import Job


DB_FILE = 'db/mensabot.db'


class Scheduler:
    """
    Manages scheduled tasks with database persistence.

    The scheduler stores tasks in a SQLite database with the following schema:
    - id: Unique identifier for the schedule
    - function_name: Name of the function to call
    - function_args: Pickled tuple of positional arguments
    - function_kwargs: Pickled dictionary of keyword arguments
    - cron_config: Pickled dictionary containing cron configuration (day_of_week, hour, minute)

    To use it:
        1. Init an instance: `scheduler = Scheduler(db_file='mydb.db')`
        2. Register functions that can be scheduled using `register_function()`.
        3. Start the scheduler with `start()`.
        4. Add schedules with `add_schedule()`/remove with `remove_schedule()`, ...
    """

    def __init__(self, db_file: str = DB_FILE):
        """
        Initialize the Scheduler.

        Args:
            db_file: Path to the SQLite database file
        """
        self.db_file = db_file
        self.scheduler = BackgroundScheduler()
        self.function_registry: Dict[str, Callable] = {}
        self._ensure_database()

    def __del__(self):
        """Destructor: Shutdown the scheduler when the instance is destroyed."""
        if hasattr(self, 'scheduler') and self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    @staticmethod
    def db_id2job_id(schedule_id: int) -> str:
        """
        Convert a database schedule ID to a job ID for APScheduler.

        Args:
            schedule_id: The database ID for the schedule

        Returns:
            The job ID string used by APScheduler
        """
        return f"schedule_{schedule_id}"

    def register_function(self, function: Callable, name: Optional[str] = None) -> None:
        """
        Register a function in the function registry so it can be scheduled.

        Args:
            function: The function to register
            name: Optional name for the function. If not provided, uses function.__name__

        Raises:
            ValueError: If a function with this name is already registered
        """
        func_name = name if name is not None else function.__name__
        if func_name in self.function_registry:
            raise ValueError(f"Function '{func_name}' is already registered")
        self.function_registry[func_name] = function

    def unregister_function(self, name: str) -> bool:
        """
        Unregister a function from the function registry.

        Args:
            name: The name of the function to unregister

        Returns:
            True if the function was unregistered, False if it wasn't registered
        """
        if name in self.function_registry:
            del self.function_registry[name]
            return True
        return False

    def get_registered_functions(self) -> Dict[str, Callable]:
        """
        Get a copy of the function registry.

        Returns:
            A dictionary mapping function names to callable objects
        """
        return self.function_registry.copy()

    @staticmethod
    def _validate_function_args(function: Callable, args: Tuple, kwargs: Dict) -> None:
        """
        Validate that the provided args and kwargs are compatible with the function signature.

        Args:
            function: The function to validate against
            args: Positional arguments to validate
            kwargs: Keyword arguments to validate

        Raises:
            TypeError: If the arguments don't match the function signature
        """
        try:
            # Get the function signature
            sig = inspect.signature(function)

            # Try to bind the arguments to the signature
            # This will raise TypeError if there's a mismatch
            sig.bind(*args, **kwargs)
        except TypeError as e:
            # Re-raise with more context
            raise TypeError(f"Invalid arguments for function '{function.__name__}': {e}")

    def _ensure_database(self):
        """Create the database and table if they don't exist."""
        # Create db directory if it doesn't exist
        db_dir = os.path.dirname(self.db_file)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        if not os.path.exists(self.db_file):
            with open(self.db_file, 'w'):
                pass

        conn = sqlite3.connect(self.db_file)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    function_name TEXT NOT NULL,
                    function_args BLOB NOT NULL,
                    function_kwargs BLOB NOT NULL,
                    cron_config BLOB NOT NULL,
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL
                )
            ''')
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def add_schedule(self,
                    function_name: str,
                    chat_id: int,
                    user_id: int,
                    args: Tuple = (),
                    kwargs: Optional[dict] = None,
                    day_of_week: str = 'mon-fri',
                    hour: int = 10,
                    minute: int = 0) -> int:
        """
        Add a new scheduled task to both the database and the scheduler.

        Args:
            function_name: The name of the function to schedule
            chat_id: The chat ID where the schedule was created
            user_id: The user ID who created the schedule
            args: Positional arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
            day_of_week: Cron day_of_week specification (e.g., 'mon-fri', 'mon,wed,fri', or '*')
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)

        Returns:
            The schedule ID from the database

        Raises:
            ValueError: If the hour or minute values are invalid
            Exception: If there's a database error
        """
        if kwargs is None:
            kwargs = {}

        # Validate inputs
        if not (0 <= hour < 24):
            raise ValueError(f"Hour must be between 0 and 23, got {hour}")
        if not (0 <= minute < 60):
            raise ValueError(f"Minute must be between 0 and 59, got {minute}")
        if function_name not in self.function_registry:
            raise ValueError(f"Function '{function_name}' is not registered")
        function = self.function_registry[function_name]

        # Validate that args and kwargs match the function signature
        self._validate_function_args(function, args, kwargs)

        # Prepare data for database
        function_args_blob = pickle.dumps(args)
        function_kwargs_blob = pickle.dumps(kwargs)
        cron_config = {
            'day_of_week': day_of_week,
            'hour': hour,
            'minute': minute
        }
        cron_config_blob = pickle.dumps(cron_config)

        # Add to database
        conn = sqlite3.connect(self.db_file)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO schedules (function_name, function_args, function_kwargs, cron_config, chat_id, user_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (function_name, function_args_blob, function_kwargs_blob, cron_config_blob, chat_id, user_id))
            conn.commit()
            schedule_id = cursor.lastrowid
        finally:
            cursor.close()
            conn.close()

        # Add to scheduler with the schedule_id
        if not schedule_id:
            raise Exception("Failed to retrieve schedule ID after insertion.")
        self._add_job_to_scheduler(
            schedule_id=schedule_id,
            function=function,
            args=args,
            kwargs=kwargs,
            cron_config=cron_config
        )

        return schedule_id

    def remove_schedule(self, schedule_id: int) -> bool:
        """
        Remove a scheduled task from both the database and the scheduler.

        Args:
            schedule_id: The ID of the schedule to remove

        Returns:
            True if the schedule was removed, False if it didn't exist

        Raises:
            Exception: If there's a database error
        """
        # Remove from database
        conn = sqlite3.connect(self.db_file)
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
            conn.commit()
            rows_deleted = cursor.rowcount
        finally:
            cursor.close()
            conn.close()

        if rows_deleted == 0:
            return False

        # Remove from scheduler
        job_id = self.db_id2job_id(schedule_id)
        try:
            self.scheduler.remove_job(job_id)
        except Exception as e:
            # Job might not exist in scheduler (e.g., if it was already removed)
            print(f"Warning: Could not remove job {job_id} from scheduler: {e}")

        return True

    def get_schedules(self, chat_id: Optional[int] = None, user_id: Optional[int] = None) -> List[Tuple[int, str, Tuple, dict, dict, int, int]]:
        """
        Retrieve schedules from the database.

        Args:
            chat_id: Optional chat ID to filter schedules
            user_id: Optional user ID to filter schedules

        Returns:
            A list of tuples containing:
            (schedule_id, function_name, args, kwargs, cron_config, chat_id, user_id)
        """
        conn = sqlite3.connect(self.db_file)
        try:
            cursor = conn.cursor()

            # Build query based on filters
            query = 'SELECT id, function_name, function_args, function_kwargs, cron_config, chat_id, user_id FROM schedules'
            params = []

            if chat_id is not None or user_id is not None:
                query += ' WHERE '
                conditions = []
                if chat_id is not None:
                    conditions.append('chat_id = ?')
                    params.append(chat_id)
                if user_id is not None:
                    conditions.append('user_id = ?')
                    params.append(user_id)
                query += ' AND '.join(conditions)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            schedules = []
            for row in rows:
                schedule_id = row[0]
                function_name = row[1]
                args = pickle.loads(row[2])
                kwargs = pickle.loads(row[3])
                cron_config = pickle.loads(row[4])
                row_chat_id = row[5]
                row_user_id = row[6]
                schedules.append((schedule_id, function_name, args, kwargs, cron_config, row_chat_id, row_user_id))

            return schedules
        finally:
            cursor.close()
            conn.close()

    def _add_job_to_scheduler(self,
                             schedule_id: int,
                             function: Callable,
                             args: Tuple,
                             kwargs: dict,
                             cron_config: dict):
        """
        Add a job to the APScheduler instance.

        Args:
            schedule_id: The database ID for this schedule
            function: The function to schedule
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            cron_config: Dictionary with 'day_of_week', 'hour', 'minute'

        Raises:
            TypeError: If the args/kwargs don't match the function signature
        """
        # Validate that args and kwargs match the function signature
        self._validate_function_args(function, args, kwargs)

        job_id = self.db_id2job_id(schedule_id)

        self.scheduler.add_job(
            function,
            'cron',
            id=job_id,
            day_of_week=cron_config['day_of_week'],
            hour=cron_config['hour'],
            minute=cron_config['minute'],
            args=args,
            kwargs=kwargs,
            replace_existing=True  # Replace if a job with this ID already exists
        )

    def load_schedules_from_db(self, runtime_kwargs: Optional[Dict] = None):
        """
        Load all schedules from the database and add them to the scheduler.
        This should be called at startup.

        Args:
            runtime_kwargs: Optional dictionary of kwargs to inject into all loaded schedules
                          Example: {'token': 'your_bot_token'} to add token to all schedules

        Raises:
            KeyError: If a function name in the database is not in the registry
        """
        if runtime_kwargs is None:
            runtime_kwargs = {}

        schedules = self.get_schedules()

        for schedule_id, function_name, args, kwargs, cron_config, _row_chat_id, _row_user_id in schedules:
            if function_name not in self.function_registry:
                print(f"Warning: Function '{function_name}' not found in registry. Skipping schedule {schedule_id}.")
                continue

            function = self.function_registry[function_name]

            # Merge runtime_kwargs with stored kwargs (runtime_kwargs take precedence)
            merged_kwargs = {**kwargs, **runtime_kwargs}

            print(f"Loading schedule {schedule_id}: {function_name}({args}, {merged_kwargs}) "
                  f"at {cron_config['hour']:02d}:{cron_config['minute']:02d} on {cron_config['day_of_week']}")

            self._add_job_to_scheduler(
                schedule_id=schedule_id,
                function=function,
                args=args,
                kwargs=merged_kwargs,
                cron_config=cron_config
            )

    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()

    def shutdown(self, wait: bool = True):
        """
        Shutdown the scheduler.

        Args:
            wait: If True, wait for all jobs to complete before shutting down
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)

    def get_jobs(self) -> List[Job]:
        """
        Get all currently scheduled jobs.

        Returns:
            A list of APScheduler Job objects
        """
        return self.scheduler.get_jobs()

    def sync_from_db(self, runtime_kwargs: Optional[Dict] = None):
        """
        Synchronize the scheduler with the database.
        This removes all jobs from the scheduler and reloads them from the database.

        Args:
            runtime_kwargs: Optional dictionary of kwargs to inject into all loaded schedules
        """
        # Remove all jobs from scheduler
        self.scheduler.remove_all_jobs()

        # Reload from database
        self.load_schedules_from_db(runtime_kwargs)

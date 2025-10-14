"""
Test script for the new Scheduler class.
This script tests basic scheduler functionality without requiring the full bot.
"""

import os
from scheduler import Scheduler

# Remove test database if it exists
TEST_DB = 'test_scheduler.db'
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

# Test function that will be scheduled
def test_function(arg1: int, arg2: str, kwarg1: str = 'default'):
    print(f"Test function called! arg1={arg1}, arg2={arg2}, kwarg1={kwarg1}")
    return f"Result: {arg1}, {arg2}, {kwarg1}"

def main():
    print("=== Scheduler Test ===\n")

    # Initialize scheduler with test database
    scheduler = Scheduler(db_file=TEST_DB)
    print("✓ Scheduler initialized")

    # Test 0: Register function
    print("\n0. Registering test function...")
    scheduler.register_function(test_function)
    registered = scheduler.get_registered_functions()
    print(f"✓ Registered {len(registered)} function(s): {list(registered.keys())}")

    # Test 1: Add a schedule
    print("\n1. Adding a schedule...")
    schedule_id = scheduler.add_schedule(
        function_name='test_function',
        chat_id=123456,
        user_id=789012,
        args=(42, "hello"),
        kwargs={'kwarg1': 'custom_value'},
        day_of_week='mon-fri',
        hour=10,
        minute=30
    )
    print(f"✓ Schedule added with ID: {schedule_id}")

    # Test 2: Get all schedules
    print("\n2. Retrieving all schedules...")
    schedules = scheduler.get_schedules()
    print(f"✓ Found {len(schedules)} schedule(s)")
    for sched_id, func_name, args, kwargs, cron_config, chat_id, user_id in schedules:
        print(f"  - ID: {sched_id}, Function: {func_name}, Args: {args}, "
              f"Kwargs: {kwargs}, Cron: {cron_config}, Chat: {chat_id}, User: {user_id}")

    # Test 3: Add another schedule
    print("\n3. Adding another schedule...")
    schedule_id_2 = scheduler.add_schedule(
        function_name='test_function',
        chat_id=654321,
        user_id=210987,
        args=(99, "world"),
        kwargs={'kwarg1': 'another_value'},
        day_of_week='sat,sun',
        hour=14,
        minute=0
    )
    print(f"✓ Second schedule added with ID: {schedule_id_2}")

    # Test 4: Get schedules again
    print("\n4. Retrieving all schedules again...")
    schedules = scheduler.get_schedules()
    print(f"✓ Found {len(schedules)} schedule(s)")

    # Test 5: Remove a schedule
    print(f"\n5. Removing schedule {schedule_id}...")
    removed = scheduler.remove_schedule(schedule_id)
    print(f"✓ Schedule removed: {removed}")

    # Test 6: Verify removal
    print("\n6. Verifying removal...")
    schedules = scheduler.get_schedules()
    print(f"✓ Found {len(schedules)} schedule(s) after removal")

    # Test 7: Load schedules into scheduler
    print("\n7. Loading schedules into scheduler...")
    scheduler.load_schedules_from_db()
    # Start the scheduler after functions are registered and schedules loaded
    scheduler.start()
    jobs = scheduler.get_jobs()
    print(f"✓ Loaded {len(jobs)} job(s) into scheduler")
    for job in jobs:
        print(f"  - Job ID: {job.id}")

    # Test 8: Test runtime kwargs injection
    print("\n8. Testing runtime kwargs injection...")
    scheduler.sync_from_db(runtime_kwargs={'kwarg1': 'runtime_override'})
    jobs = scheduler.get_jobs()
    print(f"✓ Reloaded {len(jobs)} job(s) with runtime kwargs")

    # Test 9: Remove remaining schedule
    print(f"\n9. Removing schedule {schedule_id_2}...")
    removed = scheduler.remove_schedule(schedule_id_2)
    print(f"✓ Schedule removed: {removed}")

    # Test 10: Verify all schedules removed
    print("\n10. Verifying all schedules removed...")
    schedules = scheduler.get_schedules()
    print(f"✓ Found {len(schedules)} schedule(s) - should be 0")

    # Cleanup (scheduler will shutdown automatically via destructor)
    print("\n11. Cleaning up test database...")
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    print("✓ Test database removed")

    print("\n=== All tests passed! ===")

if __name__ == '__main__':
    main()

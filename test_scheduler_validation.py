"""
Test script for scheduler argument validation.
This tests that invalid arguments are properly caught.
"""

import os
from scheduler import Scheduler

# Remove test database if it exists
TEST_DB = 'test_validation.db'
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

def test_function_with_args(name: str, age: int, city: str = 'Unknown'):
    """Test function with specific signature."""
    print(f"{name} is {age} years old from {city}")

def main():
    print("=== Scheduler Validation Test ===\n")

    scheduler = Scheduler(db_file=TEST_DB)
    scheduler.register_function(test_function_with_args)

    # Test 1: Valid arguments
    print("1. Testing valid arguments...")
    try:
        schedule_id = scheduler.add_schedule(
            function_name='test_function_with_args',
            chat_id=123456,
            user_id=789012,
            args=('Alice', 30),
            kwargs={'city': 'Berlin'},
            hour=10,
            minute=0
        )
        print(f"✓ Valid arguments accepted. Schedule ID: {schedule_id}")
    except TypeError as e:
        print(f"✗ Unexpected error: {e}")

    # Test 2: Valid arguments (with default)
    print("\n2. Testing valid arguments with defaults...")
    try:
        schedule_id = scheduler.add_schedule(
            function_name='test_function_with_args',
            chat_id=123456,
            user_id=789012,
            args=('Bob', 25),
            hour=11,
            minute=0
        )
        print(f"✓ Valid arguments accepted. Schedule ID: {schedule_id}")
    except TypeError as e:
        print(f"✗ Unexpected error: {e}")

    # Test 3: Too many positional arguments
    print("\n3. Testing too many positional arguments...")
    try:
        schedule_id = scheduler.add_schedule(
            function_name='test_function_with_args',
            chat_id=123456,
            user_id=789012,
            args=('Charlie', 35, 'Paris', 'Extra'),
            hour=12,
            minute=0
        )
        print(f"✗ Should have raised TypeError!")
    except TypeError as e:
        print(f"✓ Correctly caught error: {e}")

    # Test 4: Too few arguments
    print("\n4. Testing too few arguments...")
    try:
        schedule_id = scheduler.add_schedule(
            function_name='test_function_with_args',
            chat_id=123456,
            user_id=789012,
            args=('Diana',),  # Missing 'age'
            hour=13,
            minute=0
        )
        print(f"✗ Should have raised TypeError!")
    except TypeError as e:
        print(f"✓ Correctly caught error: {e}")

    # Test 5: Invalid keyword argument
    print("\n5. Testing invalid keyword argument...")
    try:
        schedule_id = scheduler.add_schedule(
            function_name='test_function_with_args',
            chat_id=123456,
            user_id=789012,
            args=('Eve', 28),
            kwargs={'country': 'France'},  # 'country' is not a parameter
            hour=14,
            minute=0
        )
        print(f"✗ Should have raised TypeError!")
    except TypeError as e:
        print(f"✓ Correctly caught error: {e}")

    # Test 6: Duplicate argument (positional + keyword)
    print("\n6. Testing duplicate argument...")
    try:
        schedule_id = scheduler.add_schedule(
            function_name='test_function_with_args',
            chat_id=123456,
            user_id=789012,
            args=('Frank', 40, 'London'),
            kwargs={'city': 'Madrid'},  # 'city' already provided positionally
            hour=15,
            minute=0
        )
        print(f"✗ Should have raised TypeError!")
    except TypeError as e:
        print(f"✓ Correctly caught error: {e}")

    # Test 7: Wrong argument type (validation won't catch this, but good to show)
    print("\n7. Testing wrong argument type (will be accepted)...")
    try:
        schedule_id = scheduler.add_schedule(
            function_name='test_function_with_args',
            chat_id=123456,
            user_id=789012,
            args=('George', 'not-a-number'),  # age should be int, but signature validation won't catch this
            hour=16,
            minute=0
        )
        print(f"✓ Arguments accepted (type hints are not enforced at runtime)")
        print("   Note: Type validation would require additional runtime checks")
    except TypeError as e:
        print(f"Error: {e}")

    # Get all schedules to verify what was added
    print("\n8. Checking stored schedules...")
    schedules = scheduler.get_schedules()
    print(f"✓ Total valid schedules stored: {len(schedules)}")
    for sched_id, func_name, args, kwargs, cron, chat_id, user_id in schedules:
        print(f"   - Schedule {sched_id}: {func_name}{args} {kwargs} (chat={chat_id}, user={user_id})")

    # Cleanup (scheduler will shutdown automatically via destructor)
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    print("\n=== Validation tests complete! ===")

if __name__ == '__main__':
    main()

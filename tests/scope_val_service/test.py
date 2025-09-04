"""
Test script for scope validation
"""

import asyncio

from app.adapters.claude_service import get_claude_client
from app.core.scope_val_service import scope_validation

from tests.scope_val_service.user_inputs import valid_home_health_examples, invalid_examples, edge_case_examples

claude_client = get_claude_client()

async def run_single_test(test_case, test_num=None):
        """Run a single test case"""
        if test_num:
            print(f"\n--- Test {test_num}: {test_case['name']} ---")
        else:
            print(f"\n--- Testing: {test_case['name']} ---")
        
        # Print the payload for reference
        print("Payload:")
        for key, value in test_case['payload'].items():
            print(f"  {key}: {value}")
        
        print("\nResult:")
        try:
            async for response in scope_validation(test_case['payload'], claude_client):
                print(f"  {response}")
        except Exception as e:
            print(f"  ERROR: {e}")
        
        print("-" * 60)

async def run_test_suite(suite_name, test_cases):
    """Run a complete test suite"""
    print(f"\n{'='*60}")
    print(f"TESTING: {suite_name}")
    print('='*60)
    
    for i, test_case in enumerate(test_cases, 1):
        await run_single_test(test_case, i)
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)

async def run_all_tests():
    """Run all test suites"""
    print("Starting Domain Validation Tests...")
    print("="*60)
    
    test_suites = [
        ("VALID HOME HEALTH EXAMPLES (Should Pass)", valid_home_health_examples),
        ("INVALID NON-HOME HEALTH EXAMPLES (Should Be Rejected)", invalid_examples),
        ("EDGE CASE EXAMPLES (Borderline Cases)", edge_case_examples),
    ]
    
    for suite_name, test_cases in test_suites:
        await run_test_suite(suite_name, test_cases)
        print(f"\nCompleted: {suite_name}")
        await asyncio.sleep(1)  # Longer delay between suites
    
    print(f"\n{'='*60}")
    print("ALL TESTS COMPLETED")
    print('='*60)

async def run_quick_test():
    """Run just a few examples for quick testing"""
    print("Running Quick Test...")

    quick_tests = [
        valid_home_health_examples[0],  # Basic home health
        invalid_examples[0],            # Emergency department
        edge_case_examples[0]           # Outpatient with home follow-up
    ]
    
    for test_case in quick_tests:
        await run_single_test(test_case)
        await asyncio.sleep(0.5)


def main():
    
    """Main function with user choice"""
    print("Domain Validation Test Script")
    print("=" * 30)
    print("Choose test option:")
    print("1. Quick test (3 examples)")
    print("2. Run all tests (comprehensive)")
    print("3. Exit")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        asyncio.run(run_quick_test())
    elif choice == "2":
        asyncio.run(run_all_tests())
    elif choice == "3":
        print("Exiting...")
        return
    else:
        print("Invalid choice. Exiting...")
        return

if __name__ == "__main__":
    main()
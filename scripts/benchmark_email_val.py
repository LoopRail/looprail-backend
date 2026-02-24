import time
import statistics
from email_validator import validate_email

def benchmark():
    # Load domains
    with open("config/disposable_email_domains.txt", "r") as f:
        domains_list = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    domains_set = set(domains_list)
    
    test_email = "test@mailinator.com"
    test_domain = "mailinator.com"
    
    print(f"Benchmarking with {len(domains_list)} domains...")
    
    # 1. Benchmark List Lookup (Old)
    start = time.perf_counter()
    for _ in range(100):
        _ = test_domain in domains_list
    list_time = (time.perf_counter() - start) / 100
    print(f"Old List Lookup (Avg): {list_time*1000:.4f} ms")
    
    # 2. Benchmark Set Lookup (New)
    start = time.perf_counter()
    for _ in range(100):
        _ = test_domain in domains_set
    set_time = (time.perf_counter() - start) / 100
    print(f"New Set Lookup (Avg): {set_time*1000:.64f} ms")
    
    print(f"Lookup Speedup: {list_time / set_time:.2f}x")
    
    # 3. Benchmark Email Validator (Deliverability check)
    print("\nBenchmarking Email Validator (Network vs No-Network)...")
    
    start = time.perf_counter()
    validate_email(test_email, check_deliverability=False)
    fast_val_time = time.perf_counter() - start
    print(f"Fast Validation (No DNS): {fast_val_time*1000:.2f} ms")
    
    try:
        start = time.perf_counter()
        validate_email(test_email, check_deliverability=True)
        slow_val_time = time.perf_counter() - start
        print(f"Slow Validation (With DNS): {slow_val_time*1000:.2f} ms")
    except Exception as e:
        print(f"Slow Validation failed (as expected if offline/timeout): {e}")

if __name__ == "__main__":
    benchmark()

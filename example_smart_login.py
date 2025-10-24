#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example: Sử dụng Smart Login với Token Caching
Demonstrates how to use the new smart login system with token caching
"""

from multix import get_automation_token_fast, initialize_multilogin_service, MultiloginService
import time

# Thông tin đăng nhập
EMAIL = "quytv@iart.asia"
PASSWORD = "12345679Qaz!"
SECRET_2FA = "UBEOVFAKXD7ZV7GNUW3F7TBSHLY5HAGP"
WORKSPACE_ID = "edfa065b-4274-4742-9783-d1284ea0262a"
WORKSPACE_EMAIL = "phuonganht93@iart.asia"

def example_fastest_way():
    """Ví dụ: Cách nhanh nhất để lấy automation token"""
    print("🚀 Example 1: Cách nhanh nhất lấy token")
    print("=" * 50)
    
    start_time = time.time()
    
    # Chỉ cần 1 dòng code!
    token = get_automation_token_fast(
        email=EMAIL,
        password=PASSWORD,
        secret_2fa=SECRET_2FA,
        workspace_id=WORKSPACE_ID,
        workspace_email=WORKSPACE_EMAIL
    )
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    if token:
        print(f"✅ Token lấy thành công trong {elapsed:.2f}s")
        print(f"🎫 Token: {token[:30]}...")
        return token
    else:
        print("❌ Không thể lấy token")
        return None

def example_smart_login():
    """Ví dụ: Smart Login với control chi tiết hơn"""
    print("\n🧠 Example 2: Smart Login với control chi tiết")
    print("=" * 50)
    
    start_time = time.time()
    
    result = initialize_multilogin_service(
        email=EMAIL,
        password=PASSWORD,
        secret_2fa=SECRET_2FA,
        workspace_id=WORKSPACE_ID,
        workspace_email=WORKSPACE_EMAIL,
        use_smart_login=True  # Sử dụng cached token nếu có
    )
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    if result['success']:
        cache_status = "từ cache" if result.get('from_cache') else "đăng nhập mới"
        print(f"✅ Thành công trong {elapsed:.2f}s ({cache_status})")
        print(f"🎫 Automation Token: {result['automation_token'][:30]}...")
        return result['automation_token']
    else:
        print(f"❌ Lỗi: {result.get('error')}")
        return None

def example_direct_class_usage():
    """Ví dụ: Sử dụng trực tiếp class cho control tối đa"""
    print("\n🔧 Example 3: Sử dụng trực tiếp class")
    print("=" * 50)
    
    # Tạo service instance
    service = MultiloginService(
        email=EMAIL,
        password=PASSWORD,
        secret_2fa=SECRET_2FA,
        workspace_id=WORKSPACE_ID,
        workspace_email=WORKSPACE_EMAIL
    )
    
    # Kiểm tra cached token trước
    print("🔍 Kiểm tra cached token...")
    cached_result = service.get_cached_automation_token()
    
    if cached_result['success']:
        print("⚡ Sử dụng cached token!")
        return cached_result['automation_token']
    else:
        print("🔐 Cached token không có/hết hạn, đăng nhập mới...")
        result = service.full_login_process()
        if result['success']:
            print("✅ Đăng nhập mới thành công!")
            return result['automation_token']
        else:
            print(f"❌ Đăng nhập thất bại: {result.get('error')}")
            return None

def example_performance_comparison():
    """Ví dụ: So sánh performance giữa lần đầu và lần sau"""
    print("\n📊 Example 4: Performance Comparison")
    print("=" * 50)
    
    print("🔄 Lần 1: Đăng nhập đầy đủ (force new login)")
    start1 = time.time()
    result1 = initialize_multilogin_service(
        email=EMAIL,
        password=PASSWORD,
        secret_2fa=SECRET_2FA,
        workspace_id=WORKSPACE_ID,
        workspace_email=WORKSPACE_EMAIL,
        use_smart_login=False  # Force full login
    )
    time1 = time.time() - start1
    
    if result1['success']:
        print(f"✅ Lần 1: {time1:.2f}s (full login)")
    
    print("\n⚡ Lần 2: Smart login (sử dụng cached token)")
    start2 = time.time()
    result2 = initialize_multilogin_service(
        email=EMAIL,
        password=PASSWORD,
        secret_2fa=SECRET_2FA,
        workspace_id=WORKSPACE_ID,
        workspace_email=WORKSPACE_EMAIL,
        use_smart_login=True  # Use cached token
    )
    time2 = time.time() - start2
    
    if result2['success']:
        cache_status = "cached" if result2.get('from_cache') else "new login"
        print(f"✅ Lần 2: {time2:.2f}s ({cache_status})")
        
        if result2.get('from_cache'):
            speedup = time1 / time2 if time2 > 0 else float('inf')
            print(f"🚀 Tăng tốc: {speedup:.1f}x nhanh hơn!")

def main():
    """Main function to run all examples"""
    print("🎯 DEMO: Smart Login System với Token Caching")
    print("=" * 60)
    
    # Example 1: Fastest way
    token1 = example_fastest_way()
    
    # Example 2: Smart login
    token2 = example_smart_login()
    
    # Example 3: Direct class usage  
    token3 = example_direct_class_usage()
    
    # Example 4: Performance comparison
    example_performance_comparison()
    
    print("\n" + "=" * 60)
    print("🎉 Demo hoàn thành!")
    print("💡 Lần đầu chạy sẽ đăng nhập đầy đủ")
    print("⚡ Các lần sau sẽ dùng cached token - Siêu nhanh!")
    print("=" * 60)

if __name__ == "__main__":
    main()

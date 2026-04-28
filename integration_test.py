#!/usr/bin/env python3
"""
IATRS System Integration Validator
Validates that all components are properly integrated and working together.
"""

import requests
import mysql.connector
import os
import sys
from dotenv import load_dotenv
import json
import time

# Load environment variables
load_dotenv()

BASE_URL = "http://localhost:5001"

def test_database_connection():
    """Test direct database connection"""
    print("🔍 Testing database connection...")
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        if conn.is_connected():
            print("✅ Database connection successful")
            conn.close()
            return True
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def test_health_endpoint():
    """Test health check endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'healthy' and data.get('database') == 'connected':
                print("✅ Health check passed")
                return True
            else:
                print(f"❌ Health check failed: {data}")
                return False
        else:
            print(f"❌ Health check returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_basic_endpoints():
    """Test basic API endpoints"""
    print("🔍 Testing basic API endpoints...")

    endpoints = [
        ('GET', '/jobs', 'Jobs listing'),
        ('GET', '/system/stats', 'System statistics'),
    ]

    success_count = 0

    for method, endpoint, description in endpoints:
        try:
            if method == 'GET':
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            elif method == 'POST':
                response = requests.post(f"{BASE_URL}{endpoint}", timeout=5)

            if response.status_code == 200:
                print(f"✅ {description} endpoint working")
                success_count += 1
            else:
                print(f"❌ {description} endpoint failed: {response.status_code}")
        except Exception as e:
            print(f"❌ {description} endpoint error: {e}")

    return success_count == len(endpoints)

def test_advanced_features():
    """Test advanced features"""
    print("🔍 Testing advanced features...")

    features = [
        ('GET', '/jobs/search?q=engineer', 'Advanced job search'),
        ('GET', '/jobs/recommend/1', 'Job recommendations'),
        ('GET', '/users/activity/1', 'User activity tracking'),
    ]

    success_count = 0

    for method, endpoint, description in features:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            if response.status_code in [200, 404]:  # 404 is acceptable for empty data
                print(f"✅ {description} working")
                success_count += 1
            else:
                print(f"❌ {description} failed: {response.status_code}")
        except Exception as e:
            print(f"❌ {description} error: {e}")

    return success_count == len(features)

def test_database_integrity():
    """Test database integrity and data consistency"""
    print("🔍 Testing database integrity...")

    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        cursor = conn.cursor(dictionary=True)

        # Check table counts
        tables_checks = [
            ('users', 10, 'User accounts'),
            ('jobs', 5, 'Job listings'),
            ('recruiters', 5, 'Recruiter profiles'),
            ('candidates', 5, 'Candidate profiles'),
        ]

        integrity_passed = True

        for table, expected_count, description in tables_checks:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            result = cursor.fetchone()
            actual_count = result['count']

            if actual_count == expected_count:
                print(f"✅ {description}: {actual_count} records")
            else:
                print(f"❌ {description}: Expected {expected_count}, got {actual_count}")
                integrity_passed = False

        # Check foreign key relationships
        cursor.execute("""
            SELECT COUNT(*) as orphaned_jobs
            FROM jobs j
            LEFT JOIN recruiters r ON j.recruiter_id = r.recruiter_id
            WHERE r.recruiter_id IS NULL
        """)
        orphaned_jobs = cursor.fetchone()['orphaned_jobs']

        if orphaned_jobs == 0:
            print("✅ Foreign key relationships intact")
        else:
            print(f"❌ Found {orphaned_jobs} orphaned job records")
            integrity_passed = False

        conn.close()
        return integrity_passed

    except Exception as e:
        print(f"❌ Database integrity check error: {e}")
        return False

def test_frontend_integration():
    """Test frontend integration"""
    print("🔍 Testing frontend integration...")

    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200 and 'text/html' in response.headers.get('content-type', ''):
            print("✅ Frontend serving HTML pages")
            return True
        else:
            print(f"❌ Frontend not serving properly: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend integration error: {e}")
        return False

def generate_integration_report(results):
    """Generate a comprehensive integration report"""
    print("\n" + "="*60)
    print("🎯 IATRS SYSTEM INTEGRATION REPORT")
    print("="*60)

    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)

    print(f"📊 Overall Status: {'✅ INTEGRATION SUCCESSFUL' if passed_tests == total_tests else '❌ INTEGRATION ISSUES DETECTED'}")
    print(f"📈 Tests Passed: {passed_tests}/{total_tests}")
    print()

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} - {test_name}")

    print("\n" + "="*60)

    if passed_tests == total_tests:
        print("🎉 SYSTEM FULLY INTEGRATED AND OPERATIONAL!")
        print("🌐 Access your application at: http://localhost:5001")
        print("📧 Default login password: Password@123")
        print("📚 Check README.md for API documentation")
    else:
        print("⚠️  SYSTEM INTEGRATION INCOMPLETE")
        print("🔧 Please check the failed tests above and resolve issues")

    print("="*60)

def main():
    """Main integration validation function"""
    print("🚀 Starting IATRS System Integration Validation...")
    print(f"🌐 Target URL: {BASE_URL}")
    print(f"🗄️  Database: {os.getenv('DB_NAME')} on {os.getenv('DB_HOST')}")
    print()

    # Wait a moment for services to be ready
    print("⏳ Waiting for services to stabilize...")
    time.sleep(2)

    # Run all integration tests
    results = {}

    results['Database Connection'] = test_database_connection()
    results['Health Endpoint'] = test_health_endpoint()
    results['Basic Endpoints'] = test_basic_endpoints()
    results['Advanced Features'] = test_advanced_features()
    results['Database Integrity'] = test_database_integrity()
    results['Frontend Integration'] = test_frontend_integration()

    # Generate final report
    generate_integration_report(results)

    # Return exit code based on results
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
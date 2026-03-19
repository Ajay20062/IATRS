import requests
import json

def test_apply_api():
    """Test the application API endpoint"""
    url = "http://127.0.0.1:5000/apply"
    
    # Test data
    payload = {
        "candidate_id": 2,  # Bob Martinez
        "job_id": 2        # Senior web developer
    }
    
    try:
        print("🧪 Testing application API...")
        print(f"📤 POST {url}")
        print(f"📋 Data: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, json=payload)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            print("✅ Application API working correctly!")
        else:
            print("❌ Application API failed")
            
    except Exception as e:
        print(f"❌ Error testing API: {e}")

if __name__ == "__main__":
    test_apply_api()

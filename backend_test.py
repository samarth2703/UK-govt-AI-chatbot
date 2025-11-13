import requests
import sys
import json
from datetime import datetime
import time

class ApniSarkarBotTester:
    def __init__(self, base_url="https://apni-seva-chat.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session_id = f"test-session-{int(time.time())}"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        
        result = {
            "test_name": name,
            "status": "PASSED" if success else "FAILED",
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"{status} - {name}: {details}")

    def test_api_root(self):
        """Test API root endpoint"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f", Response: {data.get('message', 'No message')}"
            self.log_test("API Root Endpoint", success, details)
            return success
        except Exception as e:
            self.log_test("API Root Endpoint", False, f"Error: {str(e)}")
            return False

    def test_chat_endpoint(self):
        """Test chat endpoint with English message"""
        try:
            payload = {
                "session_id": self.session_id,
                "message": "Tell me about Char Dham Yatra registration",
                "language": "english"
            }
            
            print("🔄 Sending chat request (this may take 20-30 seconds for GPT-5)...")
            response = requests.post(
                f"{self.api_url}/chat", 
                json=payload, 
                timeout=60,
                headers={'Content-Type': 'application/json'}
            )
            
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                if 'response' in data and 'detected_language' in data:
                    details += f", Response length: {len(data['response'])} chars, Language: {data['detected_language']}"
                    # Check if response contains relevant information
                    if "char dham" in data['response'].lower() or "yatra" in data['response'].lower():
                        details += ", Contains relevant content"
                    else:
                        details += ", WARNING: Response may not be relevant"
                else:
                    success = False
                    details += ", Missing required fields in response"
            else:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f", Raw response: {response.text[:200]}"
            
            self.log_test("Chat Endpoint (English)", success, details)
            return success, response.json() if success else {}
            
        except Exception as e:
            self.log_test("Chat Endpoint (English)", False, f"Error: {str(e)}")
            return False, {}

    def test_chat_hindi(self):
        """Test chat endpoint with Hindi message"""
        try:
            payload = {
                "session_id": self.session_id,
                "message": "जन्म प्रमाण पत्र के लिए कैसे आवेदन करें?",
                "language": "hindi"
            }
            
            print("🔄 Sending Hindi chat request...")
            response = requests.post(
                f"{self.api_url}/chat", 
                json=payload, 
                timeout=60,
                headers={'Content-Type': 'application/json'}
            )
            
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                if 'response' in data and 'detected_language' in data:
                    details += f", Response length: {len(data['response'])} chars, Language: {data['detected_language']}"
                else:
                    success = False
                    details += ", Missing required fields in response"
            
            self.log_test("Chat Endpoint (Hindi)", success, details)
            return success
            
        except Exception as e:
            self.log_test("Chat Endpoint (Hindi)", False, f"Error: {str(e)}")
            return False

    def test_chat_history(self):
        """Test chat history retrieval"""
        try:
            response = requests.get(f"{self.api_url}/chat/history/{self.session_id}", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                if isinstance(data, list):
                    details += f", History count: {len(data)} messages"
                    if len(data) > 0:
                        # Check if messages have required fields
                        first_msg = data[0]
                        required_fields = ['id', 'session_id', 'message', 'response', 'language', 'timestamp']
                        missing_fields = [field for field in required_fields if field not in first_msg]
                        if missing_fields:
                            details += f", Missing fields: {missing_fields}"
                        else:
                            details += ", All required fields present"
                else:
                    success = False
                    details += ", Response is not a list"
            
            self.log_test("Chat History Retrieval", success, details)
            return success
            
        except Exception as e:
            self.log_test("Chat History Retrieval", False, f"Error: {str(e)}")
            return False

    def test_clear_session(self):
        """Test session clearing"""
        try:
            response = requests.delete(f"{self.api_url}/chat/session/{self.session_id}", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                if 'deleted_count' in data:
                    details += f", Deleted count: {data['deleted_count']}"
                else:
                    success = False
                    details += ", Missing deleted_count in response"
            
            self.log_test("Clear Session", success, details)
            return success
            
        except Exception as e:
            self.log_test("Clear Session", False, f"Error: {str(e)}")
            return False

    def test_invalid_endpoint(self):
        """Test invalid endpoint handling"""
        try:
            response = requests.get(f"{self.api_url}/invalid-endpoint", timeout=10)
            success = response.status_code == 404
            details = f"Status: {response.status_code} (Expected 404)"
            self.log_test("Invalid Endpoint Handling", success, details)
            return success
        except Exception as e:
            self.log_test("Invalid Endpoint Handling", False, f"Error: {str(e)}")
            return False

    def test_malformed_chat_request(self):
        """Test malformed chat request handling"""
        try:
            # Missing required fields
            payload = {"message": "test"}  # Missing session_id
            response = requests.post(
                f"{self.api_url}/chat", 
                json=payload, 
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            success = response.status_code in [400, 422]  # Bad request or validation error
            details = f"Status: {response.status_code} (Expected 400/422)"
            self.log_test("Malformed Request Handling", success, details)
            return success
        except Exception as e:
            self.log_test("Malformed Request Handling", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Apni Sarkar Bot Backend Tests")
        print(f"📍 Testing API at: {self.api_url}")
        print(f"🆔 Session ID: {self.session_id}")
        print("=" * 60)
        
        # Test basic connectivity first
        if not self.test_api_root():
            print("❌ API root test failed - stopping further tests")
            return False
        
        # Test core functionality
        chat_success, chat_response = self.test_chat_endpoint()
        if not chat_success:
            print("❌ Chat endpoint failed - this is critical")
        
        # Test Hindi support
        self.test_chat_hindi()
        
        # Test history (only if chat worked)
        if chat_success:
            self.test_chat_history()
            self.test_clear_session()
        
        # Test error handling
        self.test_invalid_endpoint()
        self.test_malformed_chat_request()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate < 70:
            print("⚠️  WARNING: Low success rate - major issues detected")
        elif success_rate < 90:
            print("⚠️  Some issues detected - review failed tests")
        else:
            print("✅ Most tests passed - API appears healthy")
        
        return success_rate >= 70

def main():
    tester = ApniSarkarBotTester()
    success = tester.run_all_tests()
    
    # Save detailed results
    results_file = f"/app/test_reports/backend_test_results_{int(time.time())}.json"
    with open(results_file, 'w') as f:
        json.dump({
            "summary": {
                "total_tests": tester.tests_run,
                "passed_tests": tester.tests_passed,
                "success_rate": (tester.tests_passed / tester.tests_run) * 100 if tester.tests_run > 0 else 0,
                "timestamp": datetime.now().isoformat()
            },
            "test_results": tester.test_results
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
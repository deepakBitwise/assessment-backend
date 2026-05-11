"""
Example client implementation for the new authentication system.
This shows how a frontend should handle login, token refresh, and logout.
"""

import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
STORAGE_FILE = "auth_tokens.json"  # In real apps, use secure storage (localStorage, etc.)


class AuthClient:
    """Client for handling authentication with refresh token support"""

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.load_tokens()

    def load_tokens(self):
        """Load stored tokens from persistent storage"""
        try:
            with open(STORAGE_FILE, "r") as f:
                data = json.load(f)
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.token_expires_at = data.get("expires_at")
        except FileNotFoundError:
            pass

    def save_tokens(self):
        """Save tokens to persistent storage"""
        with open(STORAGE_FILE, "w") as f:
            json.dump(
                {
                    "access_token": self.access_token,
                    "refresh_token": self.refresh_token,
                    "expires_at": self.token_expires_at,
                },
                f,
            )

    def login(self, email: str, password: str) -> bool:
        """
        Login with email and password.
        Returns True on success, stores tokens for future use.
        """
        try:
            response = requests.post(
                f"{self.base_url}/login/access-token",
                data={"username": email, "password": password},
            )
            response.raise_for_status()

            data = response.json()
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]

            # Calculate expiration time
            expires_in = data.get("expires_in", 3600)
            self.token_expires_at = (
                datetime.now() + timedelta(seconds=expires_in)
            ).isoformat()

            self.save_tokens()
            print("✓ Login successful")
            return True

        except requests.exceptions.RequestException as e:
            print(f"✗ Login failed: {e}")
            return False

    def is_token_expired(self) -> bool:
        """Check if current access token is expired"""
        if not self.token_expires_at:
            return True

        expires_at = datetime.fromisoformat(self.token_expires_at)
        return datetime.now() >= expires_at

    def refresh_access_token(self) -> bool:
        """
        Refresh access token using refresh token.
        Called automatically when token is about to expire.
        """
        if not self.refresh_token:
            print("✗ No refresh token available")
            return False

        try:
            response = requests.post(
                f"{self.base_url}/login/refresh",
                json={"refresh_token": self.refresh_token},
            )
            response.raise_for_status()

            data = response.json()
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]  # May be new token

            # Update expiration time
            expires_in = data.get("expires_in", 3600)
            self.token_expires_at = (
                datetime.now() + timedelta(seconds=expires_in)
            ).isoformat()

            self.save_tokens()
            print("✓ Token refreshed successfully")
            return True

        except requests.exceptions.RequestException as e:
            print(f"✗ Token refresh failed: {e}")
            return False

    def get_headers(self) -> dict:
        """
        Get authorization headers for API requests.
        Automatically refreshes token if expired.
        """
        if self.is_token_expired():
            print("Token expired, refreshing...")
            if not self.refresh_access_token():
                raise Exception("Failed to refresh token. Please login again.")

        return {"Authorization": f"Bearer {self.access_token}"}

    def api_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make authenticated API request.
        Automatically handles token refresh.
        """
        url = f"{self.base_url}{endpoint}"
        headers = self.get_headers()

        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        response = requests.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    def get_current_user(self):
        """Get current user info"""
        response = self.api_request("POST", "/login/test-token")
        return response.json()

    def get_active_sessions(self):
        """Get list of active sessions (devices)"""
        response = self.api_request("GET", "/sessions")
        return response.json()

    def logout(self, session_id: str = None) -> bool:
        """
        Logout from one or all devices.
        If session_id provided, logout only that device.
        Otherwise, logout from all devices.
        """
        try:
            params = {}
            if session_id:
                params["session_id"] = session_id

            self.api_request("POST", "/logout", params=params)
            self.access_token = None
            self.refresh_token = None
            self.token_expires_at = None

            # Clear stored tokens
            try:
                import os

                os.remove(STORAGE_FILE)
            except FileNotFoundError:
                pass

            print("✓ Logout successful")
            return True

        except Exception as e:
            print(f"✗ Logout failed: {e}")
            return False


# Example usage
if __name__ == "__main__":
    client = AuthClient()

    # 1. Login
    print("\n1. Logging in...")
    if client.login("admin@example.com", "admin123"):
        # 2. Get current user
        print("\n2. Getting current user...")
        try:
            user = client.get_current_user()
            print(f"Current user: {user['email']}")
        except Exception as e:
            print(f"Error: {e}")

        # 3. View active sessions
        print("\n3. Viewing active sessions...")
        try:
            sessions = client.get_active_sessions()
            for session in sessions:
                print(
                    f"  - {session['device_name']} ({session['device_type']}) - IP: {session['ip_address']}"
                )
        except Exception as e:
            print(f"Error: {e}")

        # 4. Make API request (will auto-refresh if needed)
        print("\n4. Making authenticated API request...")
        try:
            response = client.api_request("GET", "/users/me")
            print(f"User profile: {response.json()}")
        except Exception as e:
            print(f"Error: {e}")

        # 5. Logout
        print("\n5. Logging out...")
        client.logout()

    else:
        print("Login failed")

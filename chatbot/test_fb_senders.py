"""
Find Facebook Messenger sender_id (PSID) from conversations.

Lists all users who have messaged your Facebook Page,
showing their PSID and name (if accessible).

Usage:
    python test_fb_senders.py              # List ALL senders
    python test_fb_senders.py 26089827937340361   # Check specific PSID
"""

import httpx
import os
import sys
from dotenv import load_dotenv

load_dotenv()

GRAPH_API_URL = "https://graph.facebook.com/v21.0"
ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")


def list_all_senders():
    """List all users who have messaged the Facebook Page."""

    if not ACCESS_TOKEN or not PAGE_ID:
        print("ERROR: FACEBOOK_PAGE_ACCESS_TOKEN or FACEBOOK_PAGE_ID not set in .env")
        return

    # Step 1: Get all conversations
    print(f"Fetching conversations for Page ID: {PAGE_ID}...\n")
    
    url = f"{GRAPH_API_URL}/{PAGE_ID}/conversations"
    params = {
        "access_token": ACCESS_TOKEN,
        "fields": "participants,updated_time",
        "limit": 100,
    }

    resp = httpx.get(url, params=params, timeout=30.0)
    if resp.status_code != 200:
        print(f"Error fetching conversations: {resp.status_code}")
        print(f"Response: {resp.text}")
        return

    data = resp.json()
    conversations = data.get("data", [])
    print(f"Found {len(conversations)} conversations\n")

    # Step 2: Extract all unique senders (exclude own page)
    all_senders = {}  # psid -> {name, updated_time}

    for convo in conversations:
        updated_time = convo.get("updated_time", "unknown")
        participants = convo.get("participants", {}).get("data", [])
        
        for p in participants:
            pid = p.get("id")
            pname = p.get("name", "Unknown")
            
            # Skip our own page
            if pid and pid != PAGE_ID:
                all_senders[pid] = {
                    "name": pname,
                    "last_active": updated_time,
                }

    # Step 3: Display results
    print("=" * 70)
    print(f"{'PSID':<25} {'Name':<25} {'Last Active'}")
    print("=" * 70)

    for psid, info in sorted(all_senders.items(), key=lambda x: x[1]["last_active"], reverse=True):
        print(f"  {psid:<25} {info['name']:<25} {info['last_active']}")

    print("=" * 70)
    print(f"\nTotal unique senders: {len(all_senders)}")
    print(f"\nNOTE: These PSIDs are page-scoped. Store the PSID in")
    print(f"      trial_users.fb_id to identify returning users.")

    # Step 4: If specific PSIDs were requested, highlight them
    if len(sys.argv) > 1:
        targets = sys.argv[1:]
        print(f"\n{'=' * 70}")
        print("LOOKUP RESULTS:")
        print("=" * 70)
        for psid in targets:
            if psid in all_senders:
                info = all_senders[psid]
                print(f"  ✅ {psid} -> {info['name']} (last active: {info['last_active']})")
            else:
                print(f"  ❌ {psid} -> NOT FOUND (user hasn't messaged this page)")


    # Step 5: Try to fetch profile for each sender (test what FB returns)
    print(f"\n{'=' * 70}")
    print("PROFILE FETCH TEST (what Graph API returns per sender):")
    print("=" * 70)

    for psid in list(all_senders.keys())[:5]:  # Test first 5 only
        profile_url = f"{GRAPH_API_URL}/{psid}"
        profile_params = {
            "access_token": ACCESS_TOKEN,
            "fields": "name,first_name,last_name",
        }
        try:
            r = httpx.get(profile_url, params=profile_params, timeout=10.0)
            if r.status_code == 200:
                profile = r.json()
                print(f"  ✅ {psid} -> Profile: {profile}")
            else:
                error = r.json().get("error", {}).get("message", r.text[:100])
                print(f"  ❌ {psid} -> Failed: {error}")
        except Exception as e:
            print(f"  ❌ {psid} -> Error: {e}")


if __name__ == "__main__":
    list_all_senders()

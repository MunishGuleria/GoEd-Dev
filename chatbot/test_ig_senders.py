"""
Find Instagram sender_id from username.

Usage:
    python test_ig_senders.py shivank_srivastav
    python test_ig_senders.py user1 user2 user3
"""

import httpx
import os
import sys
from dotenv import load_dotenv

load_dotenv()

GRAPH_API_URL = "https://graph.instagram.com/v24.0"
ACCESS_TOKEN = os.getenv("INSTAGRAM_PAGE_ACCESS_TOKEN")
ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")


def find_sender_ids(usernames: list[str]):
    """Given a list of Instagram usernames, find their sender_ids from conversations."""

    # Step 1: Get all conversations
    url = f"{GRAPH_API_URL}/{ACCOUNT_ID}/conversations"
    params = {
        "access_token": ACCESS_TOKEN,
        "fields": "participants",
        "platform": "instagram",
    }

    resp = httpx.get(url, params=params, timeout=30.0)
    if resp.status_code != 200:
        print(f"Error fetching conversations: {resp.status_code} - {resp.text}")
        return

    conversations = resp.json().get("data", [])

    # Step 2: Collect all unique sender IDs (exclude own account)
    all_sender_ids = set()
    for convo in conversations:
        for p in convo.get("participants", {}).get("data", []):
            pid = p.get("id")
            if pid and pid != ACCOUNT_ID:
                all_sender_ids.add(pid)

    print(f"Scanning {len(all_sender_ids)} senders...\n")

    # Step 3: Look up each sender's profile and match username
    targets = {u.lower() for u in usernames}
    results = {}

    for sid in all_sender_ids:
        profile_url = f"{GRAPH_API_URL}/{sid}"
        profile_params = {
            "access_token": ACCESS_TOKEN,
            "fields": "name,username",
        }
        try:
            r = httpx.get(profile_url, params=profile_params, timeout=10.0)
            if r.status_code == 200:
                data = r.json()
                uname = data.get("username", "")
                name = data.get("name", "")
                if uname and uname.lower() in targets:
                    results[uname.lower()] = sid
                    print(f"FOUND: @{uname} ({name}) -> sender_id: {sid}")
                else:
                    print(f"  checked: {sid} -> {name} (@{uname})")
        except Exception as e:
            print(f"  error checking {sid}: {e}")

    # Step 4: Report results
    print("\n" + "=" * 50)
    print("RESULTS:")
    print("=" * 50)
    for username in usernames:
        sid = results.get(username.lower())
        if sid:
            print(f"  @{username} -> {sid}")
        else:
            print(f"  @{username} -> NOT FOUND (user hasn't messaged you or username not accessible)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_ig_senders.py <username1> [username2] ...")
        sys.exit(1)

    usernames = sys.argv[1:]
    find_sender_ids(usernames)

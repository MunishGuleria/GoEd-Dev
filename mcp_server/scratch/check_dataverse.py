import asyncio
import os
import sys

# Add parent directory to path so we can import client
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from client import dataverse

async def check_dataverse():
    try:
        # Search for any college with document
        endpoint = "zx_colleges?$filter=zx_document ne null&$select=zx_collegeid,zx_collegename,zx_document"
        print(f"Querying: {endpoint}")
        data = await dataverse.get(endpoint)
        print("Data received:")
        print(data)
        
        if data.get("value"):
            college = data["value"][0]
            college_id = college["zx_collegeid"]
            print(f"Found college ID: {college_id}")
            
            # Try to download the file
            token = await dataverse._get_token()
            base_url = os.getenv("DATAVERSE_BASE_URL")
            client_http = await dataverse._get_http_client()
            
            file_endpoint = f"{base_url}/zx_colleges({college_id})/zx_document/$value"
            print(f"Downloading from: {file_endpoint}")
            
            response = await client_http.get(
                file_endpoint,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                print(f"Download successful! Size: {len(response.content)} bytes")
                # Save first 20 bytes to see if it's a PNG or PDF
                print(f"Start of file: {response.content[:10].hex()}")
            else:
                print(f"Download failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await dataverse.close()

if __name__ == "__main__":
    asyncio.run(check_dataverse())

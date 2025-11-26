import docker
import httpx
import asyncio

async def test():
    try:
        client = docker.from_env()
        print("Client created")
        
        print("Listing containers via low-level API...")
        # Use low-level API which returns dicts and shouldn't crash on inspection
        containers = client.api.containers(all=True)
        print(f"Found {len(containers)} containers")
        
        for c_dict in containers:
            c_id = c_dict.get('Id')
            names = c_dict.get('Names', [])
            name = names[0].lstrip('/') if names else "unknown"
            status = c_dict.get('State', 'unknown')
            
            print(f"Processing {name} ({c_id[:12]})... Status: {status}")
            
            # We can try to get a Container object if we want, but we must be careful
            try:
                # This might fail if container is ghost
                # container = client.containers.get(c_id)
                # print(f"  Object access ok")
                pass
            except Exception as e:
                print(f"  Error accessing container object: {e}")
                
    except Exception as e:
        print(f"CRASH: {e}")

if __name__ == "__main__":
    asyncio.run(test())

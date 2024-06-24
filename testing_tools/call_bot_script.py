import asyncio
import aiofiles
import sys

async def run_script(script_name, username, password):
    """Run the main script with the given credentials."""
    cmd = ["python3", script_name, str(username), str(password)]
    # Use asyncio.create_subprocess_exec to run the script as a subprocess
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await proc.communicate()
    if stdout:
        print(f"[{username}] Output: {stdout.decode()}")
    if stderr:
        print(f"[{username}] Errors: {stderr.decode()}")

async def main(script_name, filename):
    tasks = []
    delay = 1
    password = ***********

    
    # Read usernames and passwords from the file
    async with aiofiles.open(filename, mode='r') as f:
        async for line in f:
            if line.strip():
                #username, password = line.strip().split(',')
                username = line.strip()
                # Launch the script for each user
                task = asyncio.create_task(run_script(script_name, username, password))
                tasks.append(task)
                # Wait for 5 seconds before starting the next task
                await asyncio.sleep(delay)
    
    # Wait for all tasks to complete
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python script.py <bot_script> <filename>")
        sys.exit(1)
    script_name = sys.argv[1]
    filename = sys.argv[2]
    asyncio.run(main(script_name, filename))

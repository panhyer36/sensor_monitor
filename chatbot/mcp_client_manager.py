import asyncio
import os
import sys
from contextlib import AsyncExitStack
from typing import Optional
import signal

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Global state for the MCP client
mcp_session: Optional[ClientSession] = None
mcp_exit_stack: Optional[AsyncExitStack] = None
mcp_startup_task: Optional[asyncio.Task] = None
mcp_shutdown_event = asyncio.Event() # Event to signal shutdown

# --- Configuration ---
# Determine the server script path robustly
try:
    # Assumes manager.py is in sensor_monitor/chatbot/
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up two levels to sensor_monitor/, then down to MCP_server/
    project_root_guess = os.path.dirname(os.path.dirname(current_dir))
    SERVER_SCRIPT_PATH = os.path.join(project_root_guess, 'MCP_server', 'mcp_server.py')

    if not os.path.exists(SERVER_SCRIPT_PATH):
        # Fallback using workspace root if needed (adjust path if necessary)
        workspace_root = "/Users/p304/Documents/python/MCP_client實作" # From user info
        alt_path = os.path.join(workspace_root, 'sensor_monitor', 'MCP_server', 'mcp_server.py')
        if os.path.exists(alt_path):
            SERVER_SCRIPT_PATH = alt_path
        else:
            raise FileNotFoundError("MCP server script not found.")
except Exception as e:
    print(f"[MCP Client Manager] Error determining server script path: {e}")
    SERVER_SCRIPT_PATH = None # Indicate path finding failed

PYTHON_EXECUTABLE = sys.executable or "python"

async def startup_mcp_client():
    """Starts the MCP server process and initializes the client session."""
    global mcp_session, mcp_exit_stack
    
    if mcp_session is not None:
        print("[MCP Client Manager] Session already exists. Skipping startup.")
        return

    if not SERVER_SCRIPT_PATH or not os.path.exists(SERVER_SCRIPT_PATH):
         print(f"[MCP Client Manager] Error: Cannot start MCP client, server script not found at '{SERVER_SCRIPT_PATH}'.")
         return

    print("[MCP Client Manager] Starting MCP client...")
    try:
        mcp_exit_stack = AsyncExitStack()
        server_params = StdioServerParameters(
            command=PYTHON_EXECUTABLE,
            args=[SERVER_SCRIPT_PATH],
            env=None
        )
        print(f"[MCP Client Manager] Launching server: {PYTHON_EXECUTABLE} {SERVER_SCRIPT_PATH}")
        
        # Enter contexts within the exit stack
        stdio_transport = await mcp_exit_stack.enter_async_context(stdio_client(server_params))
        session = await mcp_exit_stack.enter_async_context(ClientSession(stdio_transport[0], stdio_transport[1]))
        
        print("[MCP Client Manager] Initializing MCP session...")
        await asyncio.wait_for(session.initialize(), timeout=20.0) # Increased timeout
        
        mcp_session = session # Assign only after successful initialization
        print("[MCP Client Manager] MCP client started and session initialized successfully.")

    except asyncio.TimeoutError:
        print("[MCP Client Manager] Error: Timeout during MCP session initialization.")
        if mcp_exit_stack:
            await mcp_exit_stack.aclose() # Clean up partially started resources
        mcp_exit_stack = None
        mcp_session = None
    except Exception as e:
        print(f"[MCP Client Manager] Error during MCP client startup: {e}")
        import traceback
        traceback.print_exc()
        if mcp_exit_stack:
            await mcp_exit_stack.aclose()
        mcp_exit_stack = None
        mcp_session = None

async def shutdown_mcp_client(*args):
    """Shuts down the MCP client session and cleans up resources."""
    global mcp_session, mcp_exit_stack, mcp_startup_task
    
    print("[MCP Client Manager] Initiating shutdown...")
    mcp_shutdown_event.set() # Signal shutdown to any waiting tasks

    if mcp_startup_task and not mcp_startup_task.done():
        print("[MCP Client Manager] Cancelling ongoing startup task...")
        mcp_startup_task.cancel()
        try:
            await mcp_startup_task
        except asyncio.CancelledError:
            print("[MCP Client Manager] Startup task cancelled.")
        except Exception as e:
            print(f"[MCP Client Manager] Error waiting for cancelled startup task: {e}")
            
    if mcp_exit_stack:
        print("[MCP Client Manager] Closing MCP session and resources...")
        try:
            # Run aclose() in a separate task to avoid blocking shutdown handler
            # and potentially mitigate the original cancel scope issue.
            shutdown_task = asyncio.create_task(mcp_exit_stack.aclose())
            await asyncio.wait_for(shutdown_task, timeout=10.0) # Timeout for closing
            print("[MCP Client Manager] MCP resources closed.")
        except asyncio.TimeoutError:
             print("[MCP Client Manager] Warning: Timeout closing MCP resources.")
        except Exception as e:
            print(f"[MCP Client Manager] Error during MCP client shutdown: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[MCP Client Manager] No active session or resources to close.")
        
    mcp_session = None
    mcp_exit_stack = None
    mcp_startup_task = None
    print("[MCP Client Manager] Shutdown complete.")


def get_current_mcp_session() -> Optional[ClientSession]:
    """Returns the current MCP session if it's initialized."""
    # Could add a check here: `if mcp_startup_task and not mcp_startup_task.done(): return None`
    # But for simplicity, we assume if startup failed, mcp_session is None.
    return mcp_session

def schedule_mcp_startup():
    """Schedules the MCP client startup task."""
    global mcp_startup_task
    if mcp_startup_task is None or mcp_startup_task.done():
         loop = asyncio.get_event_loop()
         mcp_startup_task = loop.create_task(startup_mcp_client())
         print("[MCP Client Manager] MCP client startup scheduled.")
    else:
        print("[MCP Client Manager] Startup task already running or scheduled.")

# --- Signal Handling ---
def _handle_shutdown_signal(*args):
    """Initiates the async shutdown process from a sync signal handler."""
    print(f"[MCP Client Manager] Received shutdown signal {args[0]}. Scheduling cleanup...")
    # Schedule the async shutdown function to run in the event loop
    # This avoids running complex async code directly in the signal handler
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(shutdown_mcp_client())
    else:
        # If the loop isn't running, it's harder to guarantee cleanup
        print("[MCP Client Manager] Warning: Event loop not running during shutdown signal. Cleanup may not complete.")

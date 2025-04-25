from django.apps import AppConfig
import asyncio
import signal
import sys


class ChatbotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chatbot'

    def ready(self):
        """
        Called when Django starts. Schedules MCP client startup and sets up shutdown handlers.
        """
        # Ensure this runs only once, not in reload subprocesses if possible
        # (Checking sys.argv might be necessary for more complex setups)
        print("[ChatbotConfig] ready() method called.")
        
        # Import manager here to avoid circular imports or issues during initial setup
        from . import mcp_client_manager 

        # Schedule the MCP client startup in the event loop
        mcp_client_manager.schedule_mcp_startup()

        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                # Register the synchronous wrapper to handle the signal
                loop.add_signal_handler(sig, mcp_client_manager._handle_shutdown_signal, sig)
                print(f"[ChatbotConfig] Registered signal handler for {sig.name}")
            except NotImplementedError:
                 # Windows doesn't support add_signal_handler
                 print(f"[ChatbotConfig] Warning: loop.add_signal_handler not supported on this platform for {sig.name}. Shutdown might be abrupt.")
                 # Fallback or alternative mechanism might be needed for Windows production
            except Exception as e:
                 print(f"[ChatbotConfig] Error registering signal handler for {sig.name}: {e}")

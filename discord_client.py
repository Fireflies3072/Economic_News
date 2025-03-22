import discord
import asyncio
import time
import threading as td
from concurrent.futures import ThreadPoolExecutor

class BackgroundDiscordClient(discord.Client):
    def __init__(self, token, *args, **kwargs):
        super().__init__(*args, intents=discord.Intents.default(), **kwargs)
        # Create a new event loop
        self._loop = asyncio.new_event_loop()
        td.Thread(target=self._start_loop, daemon=True).start()
        self._executor = ThreadPoolExecutor(max_workers=1)
        # Connect to Discord
        asyncio.run_coroutine_threadsafe(self.start(token), self._loop)
        time.sleep(5)

    def _start_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def stop_sync(self):
        asyncio.run_coroutine_threadsafe(self.close(), self._loop)
        self._loop.stop()

    def send_message_sync(self, channel_id, content):
        def _send_message_task(channel_id, content):
            async def _send():
                channel = self.get_channel(channel_id)
                if channel:
                    for chunk in content.split('\n'):
                        if chunk:
                            await channel.send(chunk)
                            await asyncio.sleep(2)
                else:
                    print(f"Channel with ID {channel_id} not found.")
            asyncio.run_coroutine_threadsafe(_send(), self._loop).result()

        self._executor.submit(_send_message_task, channel_id, content).result()
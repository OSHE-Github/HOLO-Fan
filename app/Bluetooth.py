import asyncio
from concurrent.futures import Future
from pathlib import Path
from queue import Empty, Queue
import re
from threading import Thread

from bleak import BleakClient, BleakScanner

import var

DEVICE_NAME = "Holo-Fan"
SERVICE_UUID = "9a6b1000-5b3f-4c21-9f31-2d4c5b7a0001"
CONTROL_UUID = "9a6b1001-5b3f-4c21-9f31-2d4c5b7a0001"
DATA_UUID = "9a6b1002-5b3f-4c21-9f31-2d4c5b7a0001"
STATUS_UUID = "9a6b1003-5b3f-4c21-9f31-2d4c5b7a0001"
MAX_DATA_CHUNK = 20
MAX_VECTORS = 360
MAX_LEDS = 25


class bluetooth:
    def __init__(self, root):
        self.root = root
        self.client: BleakClient | None = None
        self.connected = False
        self._status_updates: Queue[str] = Queue()
        self._loop = asyncio.new_event_loop()
        self._loop_thread = Thread(target=self._run_loop, daemon=True)
        self._loop_thread.start()
        self._connect_future: Future[None] | None = None
        self._upload_future: Future[None] | None = None
        self._status_messages: asyncio.Queue[str] = asyncio.Queue()

        self.update_status("Disconnected")
        self._poll_status_updates()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()
        self._loop.close()

    def _poll_status_updates(self):
        while True:
            try:
                var.bt_status = self._status_updates.get_nowait()
            except Empty:
                break

        if self.root.winfo_exists():
            self.root.after(100, self._poll_status_updates)

    def update_status(self, status):
        self._status_updates.put(status)

    def connect(self):
        if self.connected:
            self.update_status("Connected")
            return
        if self._connect_future is not None and not self._connect_future.done():
            return

        self.update_status("Scanning...")
        self._connect_future = asyncio.run_coroutine_threadsafe(
            self._connect(), self._loop
        )
        self._connect_future.add_done_callback(self._report_connection_error)

    async def _connect(self):
        device = await BleakScanner.find_device_by_name(
            DEVICE_NAME, timeout=10.0
        )
        if device is None:
            self.update_status("Device not found")
            return

        client = BleakClient(device, disconnected_callback=self._handle_disconnect)
        self.client = client
        self.update_status("Connecting...")

        try:
            await client.connect()
            await client.start_notify(STATUS_UUID, self.notification_handler)
        except Exception:
            if client.is_connected:
                await client.disconnect()
            self.client = None
            raise

        self.connected = True
        self.update_status("Connected")

    def _report_connection_error(self, future):
        if future.cancelled():
            return
        error = future.exception()
        if error is not None:
            self.connected = False
            self.client = None
            self.update_status(f"Connection failed: {error}")

    def _handle_disconnect(self, client):
        if self.client is client:
            self.client = None
        self.connected = False
        self.update_status("Disconnected")

    def disconnect(self):
        future = asyncio.run_coroutine_threadsafe(self._disconnect(), self._loop)
        future.add_done_callback(self._report_disconnect_error)
        return future

    def _report_disconnect_error(self, future):
        if future.cancelled():
            return
        error = future.exception()
        if error is not None:
            self.update_status(f"Disconnect failed: {error}")

    async def _disconnect(self):
        client = self.client
        if client is not None and client.is_connected:
            await client.disconnect()

        self.client = None
        self.connected = False
        self.update_status("Disconnected")

    def send_file(self, path):
        if self._upload_future is not None and not self._upload_future.done():
            return self._upload_future
        if not self.connected or self.client is None or not self.client.is_connected:
            raise RuntimeError("Connect to the fan before sending a file.")

        self._upload_future = asyncio.run_coroutine_threadsafe(
            self._send_file(Path(path)), self._loop
        )
        self._upload_future.add_done_callback(self._report_upload_error)
        return self._upload_future

    def _report_upload_error(self, future):
        if future.cancelled():
            return
        error = future.exception()
        if error is not None:
            self.update_status(f"Upload failed: {error}")

    async def _send_file(self, path):
        client = self.client
        if client is None or not client.is_connected:
            raise RuntimeError("Bluetooth disconnected before the upload started.")

        payload = await asyncio.to_thread(path.read_bytes)
        self._validate_image_file(payload)
        self._clear_status_messages()

        await client.write_gatt_char(CONTROL_UUID, b"BEGIN_FILE", response=True)
        await self._wait_for_status("FILE_READY")

        for offset in range(0, len(payload), MAX_DATA_CHUNK):
            chunk = payload[offset : offset + MAX_DATA_CHUNK]
            await client.write_gatt_char(DATA_UUID, chunk, response=True)

        await client.write_gatt_char(CONTROL_UUID, b"END_FILE", response=True)
        await self._wait_for_status("FILE_OK")
        await client.write_gatt_char(CONTROL_UUID, b"START", response=True)
        await self._wait_for_status("RUNNING")

    def _validate_image_file(self, payload):
        try:
            lines = [
                line
                for line in payload.decode("ascii").splitlines()
                if line.strip()
            ]
        except UnicodeDecodeError as error:
            raise ValueError("image.txt must contain ASCII text.") from error

        if not lines:
            raise ValueError("image.txt is empty.")

        try:
            vector_count = int(lines[0])
        except ValueError as error:
            raise ValueError("The first line of image.txt must be a vector count.") from error

        if not 1 <= vector_count <= MAX_VECTORS:
            raise ValueError(f"Vector count must be between 1 and {MAX_VECTORS}.")
        if len(lines) != vector_count + 1:
            raise ValueError(
                f"image.txt must contain {vector_count} vector rows; found {len(lines) - 1}."
            )

        for row_number, line in enumerate(lines[1:], start=1):
            colors = line.split(",")
            if len(colors) != MAX_LEDS or any(
                re.fullmatch(r"#?[0-9A-Fa-f]{6}", color) is None
                for color in colors
            ):
                raise ValueError(
                    f"Vector row {row_number} must contain exactly {MAX_LEDS} six-digit hex colors."
                )

    def _clear_status_messages(self):
        while True:
            try:
                self._status_messages.get_nowait()
            except asyncio.QueueEmpty:
                return

    async def _wait_for_status(self, expected, timeout=15):
        while True:
            try:
                message = await asyncio.wait_for(
                    self._status_messages.get(), timeout
                )
            except TimeoutError as error:
                raise TimeoutError(
                    f"Timed out waiting for {expected} from the fan."
                ) from error
            state = message.split(",", 1)[0]
            if state == expected:
                return message
            if state.startswith("ERR_"):
                raise RuntimeError(f"The fan rejected the upload: {message}")

    def notification_handler(self, _sender, data):
        message = bytes(data).decode("utf-8", errors="replace").strip()
        if not message:
            return

        self._status_messages.put_nowait(message)
        self.update_status(message)

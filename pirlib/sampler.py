import os
import time
import random


class PirSampler:
    """
    Reads the HC-SR501 PIR sensor from a GPIO pin.

    Mock mode (MOCK=true env var or mock=True constructor arg):
    Simulates motion events without real hardware. Useful for
    running the producer inside Docker on a non-Pi machine.
    """

    def __init__(self, pin: int, mock: bool = False):
        self.pin = pin
        self.mock = mock or os.environ.get("MOCK", "false").lower() == "true"

        if self.mock:
            print(f"[PirSampler] Running in MOCK mode (pin {pin} simulated)")
            self._mock_state = False
            self._mock_next_toggle = time.time() + random.uniform(2, 5)
        else:
            from gpiozero import DigitalInputDevice
            self.dev = DigitalInputDevice(pin)

    def read(self) -> bool:
        if self.mock:
            return self._mock_read()
        return bool(self.dev.value)

    def _mock_read(self) -> bool:
        """Simulates a PIR sensor toggling HIGH for ~1s every 3–8s."""
        now = time.time()
        if now >= self._mock_next_toggle:
            self._mock_state = not self._mock_state
            if self._mock_state:
                # Stay HIGH for 0.5 – 1.5 seconds
                self._mock_next_toggle = now + random.uniform(0.5, 1.5)
            else:
                # Stay LOW for 3 – 8 seconds between events
                self._mock_next_toggle = now + random.uniform(3, 8)
        return self._mock_state

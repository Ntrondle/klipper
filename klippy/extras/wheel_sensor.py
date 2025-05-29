# wheel_sensor.py — Klipper custom RPM sensor module
# Accepts both classic "pin"/"pulses_per_rev"/"poll_interval"/"sample_time" keys and
# new "tachometer_pin"/"tachometer_ppr"/"tachometer_poll_interval"/"tachometer_sample_time" keys for configuration compatibility.

from . import pulse_counter, output_pin

class StandaloneWheelSensor:
    def __init__(self, config):
        self.name = config.get_name().split()[-1]
        printer = config.get_printer()
        self._freq_counter = None

        # Accept both "pin" and "tachometer_pin" for compatibility
        pin = config.get('pin', config.get('tachometer_pin', None))
        if pin is not None:
            # pulses‑per‑rev: allow both styles
            self.ppr = config.getint('pulses_per_rev',
                                     config.getint('tachometer_ppr', 1),
                                     minval=1)
            poll_time = config.getfloat('poll_interval',
                        config.getfloat('tachometer_poll_interval', 0.0015),
                        above=0.)
            sample_time = config.getfloat('sample_time',
                          config.getfloat('tachometer_sample_time', 0.2),
                          above=0.01)
            self._freq_counter = pulse_counter.FrequencyCounter(
                printer, pin, sample_time, poll_time)

        printer.add_object(self.name, self)

    def get_rpm(self):
        if self._freq_counter is not None:
            return self._freq_counter.get_frequency() * 30. / self.ppr
        return None

    def get_status(self, eventtime):
        return {
            'rpm': self.get_rpm()
        }

def load_config_prefix(config):
    return StandaloneWheelSensor(config)
# wheel_sensor.py — Klipper custom RPM sensor module
# Accepts both classic "pin"/"pulses_per_rev"/"poll_interval"/"sample_time" keys and
# new "tachometer_pin"/"tachometer_ppr"/"tachometer_poll_interval"/"tachometer_sample_time" keys for configuration compatibility.

from . import pulse_counter, output_pin
import logging
LOG = logging.getLogger("wheel_sensor")

class StandaloneWheelSensor:
    def __init__(self, config):
        self.name = config.get_name().split()[-1]
        printer = config.get_printer()
        self._freq_counter = None

        # Accept both "pin" and "tachometer_pin" for compatibility
        pin = config.get('pin', config.get('tachometer_pin', None))
        if pin is None:
            LOG.warning("wheel_sensor '%s': no pin specified; tachometer disabled", self.name)
        else:
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
            LOG.info("wheel_sensor '%s': using pin %s ppr=%s poll=%s sample=%s",
                     self.name, pin, self.ppr, poll_time, sample_time)

        printer.add_object(self.name, self)

    def get_rpm(self):
        rpm = None
        if self._freq_counter is not None:
            rpm = self._freq_counter.get_frequency() * 30. / self.ppr
            LOG.debug("wheel_sensor '%s': rpm=%.2f", self.name, rpm)
        return rpm

    def get_status(self, eventtime):
        rpm = self.get_rpm()
        return {
            'rpm': rpm
        }

def load_config_prefix(config):
    return StandaloneWheelSensor(config)
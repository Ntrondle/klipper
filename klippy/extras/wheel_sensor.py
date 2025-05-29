# wheel_sensor.py — Klipper custom RPM sensor module

from . import pulse_counter

class StandaloneWheelSensor:
    def __init__(self, config):
        self.name = config.get_name().split()[-1]
        printer = config.get_printer()
        self.printer = printer
        self.gcode = printer.lookup_object('gcode')
        self._freq_counter = None

        pin = config.get('pin', None)
        if pin is not None:
            self.ppr = config.getint('pulses_per_rev', 6, minval=1)
            poll_time = config.getfloat('poll_interval', 0.0015, above=0.)
            sample_time = config.getfloat('sample_time', 0.2, above=0.01)
            self._freq_counter = pulse_counter.FrequencyCounter(
                printer, pin, sample_time, poll_time)

        printer.add_object(f"{self.name}_sensor", self)

    def get_rpm(self):
        if self._freq_counter is not None:
            return self._freq_counter.get_frequency() * 30. / self.ppr
        return True

    def get_status(self, eventtime):
        rpm = self.get_rpm()
        # Send a console message every time Klipper queries status
        self.gcode.respond_info(f'RPM: {rpm}')
        return {'rpm': rpm}

def load_config_prefix(config):
    return StandaloneWheelSensor(config)
"""
StandaloneWheelSensor
---------------------

Config keys (all optional except *pin*):
  pin: ^Turtle_1:PA2              # GPIO attached to Hall-output
  pulses_per_rev: 8               # magnets per wheel revolution
  gear_ratio: 20/12 = 1.667       # motor / wheel ratio (float, default 1.0)

Returned status:
  {'wheel_rpm': <float>, 'motor_rpm': <float>}
"""
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
            self.gear_ratio = config.getfloat('gear_ratio', 1.0, above=0.)
            poll_time = config.getfloat('poll_interval', 0.0015, above=0.)
            sample_time = config.getfloat('sample_time', 0.2, above=0.01)
            self._freq_counter = pulse_counter.FrequencyCounter(
                printer, pin, sample_time, poll_time)

        printer.add_object(f"{self.name}_sensor", self)

    def _compute_rpm(self):
        # Returns tuple (wheel_rpm, motor_rpm)
        if self._freq_counter is None:
            return None, None
        freq = self._freq_counter.get_frequency()  # Hz pulses/sec
        if freq is None:
            return None, None
        wheel_rpm = freq * 60.0 / self.ppr        # Hz → RPM
        motor_rpm = wheel_rpm * self.gear_ratio
        return wheel_rpm, motor_rpm

    def get_status(self, eventtime):
        wheel_rpm, motor_rpm = self._compute_rpm()
        # Print only when wheel rpm non‑zero
        if wheel_rpm:
            self.gcode.respond_info(f'Wheel RPM: {wheel_rpm:.1f}  |  Motor RPM: {motor_rpm:.1f}')
        return {
            'wheel_rpm': wheel_rpm,
            'motor_rpm': motor_rpm,
        }

def load_config_prefix(config):
    return StandaloneWheelSensor(config)
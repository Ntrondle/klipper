# wheel_sensor.py – simple Hall / fan‑style tachometer
#
# Usage in printer.cfg:
#
#   [wheel_sensor spool_sensor]
#   tachometer_pin: ^PA2          # DRV5023 OUT
#   tachometer_ppr: 6             # pulses per revolution
#   tachometer_poll_interval: 0.001
#   tachometer_sample_time: 0.2
#
# Query with:  QUERY_OBJECT OBJECT=spool_sensor
# Object returns:  {'rpm': <float>}
#
# Moonraker: /printer/objects/query?objects=spool_sensor

from . import pulse_counter
import logging
LOG = logging.getLogger("wheel_sensor")

class WheelSensor:
    def __init__(self, config):
        self.name = config.get_name().split()[-1]
        printer = config.get_printer()

        pin = (config.get('tachometer_pin', None)
               or config.get('pin', None))
        if pin is None:
            raise config.error("wheel_sensor: 'tachometer_pin' (or 'pin') is required")

        self.ppr = config.getint('tachometer_ppr',
                                 config.getint('pulses_per_rev', 1),
                                 minval=1)
        poll_time = config.getfloat('tachometer_poll_interval',
                    config.getfloat('poll_interval', 0.0015), above=0.)
        sample_time = config.getfloat('tachometer_sample_time',
                      config.getfloat('sample_time', 0.2), above=0.01)

        self._freq_counter = pulse_counter.FrequencyCounter(
            printer, pin, sample_time, poll_time)

        LOG.info("wheel_sensor '%s': pin=%s ppr=%d poll=%g sample=%g",
                 self.name, pin, self.ppr, poll_time, sample_time)

        # Continuous updater so RPM is available without external polling
        self.rpm = 0.0
        self.reactor = printer.get_reactor()
        self.reactor.register_timer(self._tick, poll_time)

        printer.add_object(self.name, self)

    # ------------------------------------------------------------------
    # Public Klipper API
    # ------------------------------------------------------------------
    def get_status(self, eventtime):
        LOG.debug("wheel_sensor '%s': rpm=%.2f", self.name, self.rpm)
        return {'rpm': self.rpm}

    def _tick(self, eventtime):
        """Periodic callback that keeps rpm updated."""
        freq = self._freq_counter.get_frequency()
        if freq is None:
            self.rpm = 0.0
        else:
            self.rpm = freq * 60.0 / self.ppr
        return eventtime + 0.2  # update every 0.2 s

# Klipper calls this when it sees [wheel_sensor ...]
def load_config_prefix(config):
    return WheelSensor(config)
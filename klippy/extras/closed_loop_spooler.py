# Closed-loop respooler control based on wheel-speed feedback
#
# Copyright (C) 2025 Armored Turtle
#
# This file may be distributed under the terms of the GNU GPLv3 license.

from configfile import error
from .wheel_sensor import StandaloneWheelSensor


class ClosedLoopSpooler:
    """
    PID controller that adjusts an AFCassistMotor (respooler) PWM so that the
    spool-motor RPM tracks the filament-wheel RPM * ratio.

    Requires:
      • A StandaloneWheelSensor (see `wheel_sensor.py`)
      • An AFC_stepper lane with an `afc_motor_fwd` or `afc_motor_rwd`
        declared in the printer config.
    """

    def __init__(self, config):
        # Core references
        self.printer  = config.get_printer()
        self.reactor  = self.printer.get_reactor()
        self.printer.register_event_handler("klippy:ready", self._start_loop)


        # ── Mandatory config ──────────────────────────────────────────────
        wheel_shortname = config.get('wheel_sensor')
        wheel_name = f"wheel_sensor {wheel_shortname}"
        lane_name  = config.get('lane')
        self.dir   = config.get('motor_direction', 'fwd').lower()
        if self.dir not in ('fwd', 'rwd'):
            raise error("motor_direction must be 'fwd' or 'rwd'")

        # ── Tuning parameters (defaults are safe starting points) ────────
        self.ratio      = config.getfloat('ratio',       1.0)    # motor_rpm = wheel_rpm * ratio
        self.kp         = config.getfloat('kp',          0.05)
        self.ki         = config.getfloat('ki',          0.00)
        self.kd         = config.getfloat('kd',          0.00)
        self.sample_t   = config.getfloat('sample_time', 0.20)
        self.min_pwm    = config.getfloat('min_pwm',     0.10)
        self.max_pwm    = config.getfloat('max_pwm',     1.00)

        # ── Object lookup ────────────────────────────────────────────────
        # Wheel sensor object is exported as "<name>_sensor"
        wheel_obj = self.printer.lookup_object(wheel_name)
        print(f"[DEBUG] ClosedLoopSpooler: Looking up wheel sensor object with name: '{wheel_name}'")
        if not isinstance(wheel_obj, StandaloneWheelSensor):
            raise error(f"{wheel_name} is not a StandaloneWheelSensor instance")
        self.wheel = wheel_obj

        # Lane stepper object exported as "AFC_stepper <lane>"
        lane_obj = self.printer.lookup_object(f"AFC_stepper {lane_name}")
        self.motor = getattr(lane_obj, f"afc_motor_{self.dir}", None)
        if self.motor is None:
            raise error(f"AFC_stepper {lane_name} has no afc_motor_{self.dir} configured")

        # ── PID state ────────────────────────────────────────────────────
        self._integral   = 0.0
        self._last_err   = 0.0
        self._pwm        = self.min_pwm

        # Kick off the control loop
   

    def _start_loop(self):
        self.reactor.register_timer(self._update, self.reactor.NOW)

    # ───────────────────────── helpers ───────────────────────────────────
    def _read_rpms(self):
        wheel_rpm, motor_rpm = self.wheel._compute_rpm()
        return (wheel_rpm or 0.0), (motor_rpm or 0.0)

    # ─────────────────────── control loop ───────────────────────────────
    def _update(self, eventtime):
        wheel_rpm, motor_rpm = self._read_rpms()
        target = wheel_rpm * self.ratio
        err    = target - motor_rpm

        # PID maths
        self._integral += err * self.sample_t
        deriv = (err - self._last_err) / self.sample_t
        delta = (self.kp * err) + (self.ki * self._integral) + (self.kd * deriv)
        self._last_err = err

        # Clamp & apply
        self._pwm = max(self.min_pwm, min(self.max_pwm, self._pwm + delta))
        self.motor.set_pwm(self._pwm)

        return eventtime + self.sample_t


# Loader so multiple instances can be declared, e.g.
#   [closed_loop_spooler spool1] … 
def load_config_prefix(config):
    return ClosedLoopSpooler(config)
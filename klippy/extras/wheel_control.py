# ------------------------------------------------------------------
# Klipper configuration hooks
# ------------------------------------------------------------------

def load_config_prefix(config):
    """Handle sections like  [wheel_sensor <name>]  """
    return WheelSensor(config)

# Legacy fallback in case someone uses  [wheel_sensor]  with no suffix
def load_config(config):
    return WheelSensor(config)
# wheel_control.py – Closed‑loop PWM controller for spool motor
#
#   [wheel_control <name>]
#   tach_object: spool_sensor           # object providing wheel_rpm
#   motor_pin:   Turtle_1:PB0           # PWM pin to N20 driver
#   wheel_mm_per_rev: 94.2              # circumference of spool
#   pulses_per_rev:    8                # magnets per wheel revolution
#   gear_ratio:        0.6              # wheel_rev / motor_rev
#   kp: 0.15
#   ki: 2.0
#   update_period: 0.05                 # control period (s)
#   default_target_rpm: 600
#
#   G‑codes:
#       SET_SPOOLER_RPM RPM=<rpm>
#       MOVE_SPOOL_MM   LEN=<mm> [RPM=<rpm>]
#
from . import output_pin
import logging

class WheelControl:
    def __init__(self, config):
        self.printer   = printer = config.get_printer()
        self.reactor   = printer.get_reactor()
        self.gcode     = printer.lookup_object('gcode')
        self.log       = logging.getLogger("wheel_control")

        # ----- cfg -----
        self.tach_name = config.get('tach_object')
        self.mm_rev    = config.getfloat('wheel_mm_per_rev')
        self.ppr       = config.getint('pulses_per_rev')
        self.ratio     = config.getfloat('gear_ratio', 1.0, above=0.)
        self.kp        = config.getfloat('kp', 0.1, above=0.)
        self.ki        = config.getfloat('ki', 1.0, above=0.)
        self.dt        = config.getfloat('update_period', 0.05, above=.02)
        self.target_rpm= config.getfloat('default_target_rpm', 600, above=0.)

        # ----- motor pin -----
        ppins          = printer.lookup_object('pins')
        self.motor     = ppins.setup_pin('pwm', config.get('motor_pin'))
        self.motor.setup_cycle_time(0.010, False)

        # ----- tach object -----
        self.tach      = printer.lookup_object(self.tach_name)

        # PI state
        self.integral  = 0.0
        self.pwm_out   = 0.0

        # distance tracking
        self.move_active = False
        self.pulses_goal = 0.0
        self.pulses_acc  = 0.0

        # control loop
        self.reactor.register_timer(self._loop, self.reactor.NOW + self.dt)

        # g‑codes
        self.gcode.register_command("SET_SPOOLER_RPM", self.cmd_set_rpm,
                                    desc="Set closed‑loop target RPM")
        self.gcode.register_command("MOVE_SPOOL_MM",  self.cmd_move_mm,
                                    desc="Move spool LEN mm then stop")

        self.log.info("wheel_control ready (tach=%s pin=%s)",
                      self.tach_name, config.get('motor_pin'))

    # ---------- control loop ----------
    def _loop(self, eventtime):
        rpm = self.tach.get_status(eventtime)['wheel_rpm']
        if rpm is None:
            return eventtime + self.dt

        err = self.target_rpm - rpm
        self.integral += err * self.dt
        pwm = self.kp * err + self.ki * self.integral
        pwm = 0.0 if self.target_rpm == 0 else max(0.0, min(1.0, pwm))
        self.motor.set_pwm(eventtime, pwm)
        self.pwm_out = pwm

        if self.move_active:
            pulses = rpm * self.ppr / 60.0 * self.dt
            self.pulses_acc += pulses
            if self.pulses_acc >= self.pulses_goal:
                self.target_rpm = 0
                self.move_active = False
                self.integral = 0.0
                self.gcode.respond_info("MOVE_SPOOL_MM complete")

        return eventtime + self.dt

    # ---------- g‑codes ----------
    def cmd_set_rpm(self, gcmd):
        self.target_rpm = gcmd.get_float("RPM", minval=0.)
        self.integral   = 0.0
        gcmd.respond_info(f"Target rpm set to {self.target_rpm:.1f}")

    def cmd_move_mm(self, gcmd):
        mm = gcmd.get_float("LEN", minval=0.)
        self.pulses_goal = mm / self.mm_rev * self.ppr
        self.pulses_acc  = 0.0
        self.move_active = True
        self.target_rpm  = gcmd.get_float("RPM", self.target_rpm, minval=1.)
        self.integral    = 0.0
        gcmd.respond_info(
            f"Moving {mm:.1f} mm → goal {self.pulses_goal:.0f} pulses")

    # ---------- status ----------
    def get_status(self, eventtime):
        return {
            'target_rpm':  self.target_rpm,
            'pwm':         self.pwm_out,
            'integral':    self.integral,
            'goal_pulses': self.pulses_goal if self.move_active else 0,
        }

# Klipper loader
def load_config_prefix(config):
    return WheelControl(config)
# Wheel closed-loop PWM controller
#
# Usage in printer.cfg:
#
#   [wheel_control spooler]
#   tach_object: spool_sensor_sensor     # object that reports wheel_rpm
#   motor_pin:  Turtle_1:PB0             # PWM pin driving N20
#   wheel_mm_per_rev: 94.2               # spool circumference
#   pulses_per_rev: 8
#   gear_ratio: 0.6                      # wheel / motor
#   kp: 0.15
#   ki: 2.0
#   update_period: 0.05                  # 50 ms
#   default_target_rpm: 600
#
# Provides G-codes:
#   SET_SPOOLER_RPM RPM=<r>
#   MOVE_SPOOL_MM LEN=<mm>
#
from . import pulse_counter, output_pin
import logging, math

class WheelControl:
    def __init__(self, config):
        self.printer = pr = config.get_printer()
        self.reactor = pr.get_reactor()
        self.gcode   = pr.lookup_object('gcode')
        LOG = logging.getLogger("wheel_control")

        # ----- config -----
        self.tach_name  = config.get('tach_object')
        self.mm_rev     = config.getfloat('wheel_mm_per_rev')
        self.ppr        = config.getint('pulses_per_rev')
        self.ratio      = config.getfloat('gear_ratio', 1.0)
        self.kp         = config.getfloat('kp', .1, above=0)
        self.ki         = config.getfloat('ki', 1.0, above=0)
        self.dt         = config.getfloat('update_period', 0.05, above=.02)
        self.target_rpm = config.getfloat('default_target_rpm', 600, above=1)

        # ----- motor pin -----
        ppins = pr.lookup_object('pins')
        self.motor = ppins.setup_pin('pwm', config.get('motor_pin'))
        self.motor.setup_cycle_time(0.010, False)

        # ----- tach object -----
        self.tach = pr.lookup_object(self.tach_name)

        # ----- PI state -----
        self.integral = 0.0
        self.pwm_out  = 0.0

        # ----- move tracker -----
        self.move_active = False
        self.pulses_goal = 0
        self.pulses_acc  = 0
        self.prev_count  = 0

        # start control loop
        self.reactor.register_timer(self._loop, self.reactor.NOW + self.dt)

        # g-codes
        self.gcode.register_command("SET_SPOOLER_RPM", self.cmd_set_rpm,
                                    desc="Set closed-loop target rpm")
        self.gcode.register_command("MOVE_SPOOL_MM", self.cmd_move_mm,
                                    desc="Move spool X mm then stop")

        LOG.info("wheel_control: ready (tach=%s pin=%s)", self.tach_name,
                 config.get('motor_pin'))

    # ------------------ control loop ------------------
    def _loop(self, eventtime):
        rpm = self.tach.get_status(eventtime)['wheel_rpm']
        if rpm is None:
            return eventtime + self.dt      # wait for first sample

        # PI control
        err = self.target_rpm - rpm
        self.integral += err * self.dt
        pwm = self.kp * err + self.ki * self.integral
        pwm = max(0.0, min(1.0, pwm))
        self.motor.set_pwm(eventtime, pwm)
        self.pwm_out = pwm

        # pulse counting for MOVE_SPOOL_MM
        if self.move_active:
            freq = self.tach._freq_counter.get_frequency()
            pulses = freq * self.dt
            self.pulses_acc += pulses
            if self.pulses_acc >= self.pulses_goal:
                self.target_rpm = 0
                self.move_active = False
                self.integral = 0.0
                self.gcode.respond_info("MOVE_SPOOL_MM complete")

        return eventtime + self.dt

    # ------------------ g-codes ------------------
    def cmd_set_rpm(self, gcmd):
        self.target_rpm = gcmd.get_float("RPM", minval=0.)
        self.integral = 0.0
        self.gcode.respond_info(f"Target rpm set to {self.target_rpm:.1f}")

    def cmd_move_mm(self, gcmd):
        mm = gcmd.get_float("LEN", minval=0.)
        wheel_rev = mm / self.mm_rev
        self.pulses_goal = wheel_rev * self.ppr
        self.pulses_acc  = 0
        self.move_active = True
        self.target_rpm = gcmd.get_float("RPM", self.target_rpm, minval=1.)
        self.integral = 0.0
        self.gcode.respond_info(
            f"Moving spool {mm:.1f} mm → goal pulses {self.pulses_goal:.0f}")

    # ------------------ Klipper status ------------------
    def get_status(self, eventtime):
        return {
            'target_rpm': self.target_rpm,
            'pwm':        self.pwm_out,
            'integral':   self.integral,
            'goal_pulses': self.pulses_goal if self.move_active else 0,
        }

def load_config(config):
    return WheelControl(config)
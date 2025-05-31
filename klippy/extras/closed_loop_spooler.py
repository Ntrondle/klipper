# extras/AFC_closedloop.py

class AFCClosedLoopController:
    def __init__(self, printer, afc_motor, wheel_sensor, ratio=1.0, kp=0.1, ki=0.01, kd=0.00, sample_t=0.20):
        self.printer = printer
        self.reactor = printer.get_reactor()
        self.afc_motor = afc_motor
        self.wheel_sensor = wheel_sensor
        self.enabled = False
        self.ratio = ratio          # target wheel/motor ratio
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.sample_t = sample_t
        self._integral = 0.0
        self._last_err = 0.0
        self._pwm = 0.0
        self._setpoint = 0.0        # Set externally before enabling

    def set_setpoint(self, target_rpm):
        self._setpoint = target_rpm

    def enable(self, target_rpm=None):
        if target_rpm is not None:
            self.set_setpoint(target_rpm)
        if not self.enabled:
            self.enabled = True
            self._timer = self.reactor.register_timer(self._control_loop, self.reactor.NOW)

    def disable(self):
        self.enabled = False
        # Optionally: self.afc_motor.set_pwm(0)
        self._integral = 0.0
        self._last_err = 0.0
        if hasattr(self, '_timer'):
            self.reactor.unregister_timer(self._timer)
            del self._timer

    def _control_loop(self, eventtime):
        if not self.enabled:
            return self.reactor.NEVER
        # Read wheel RPM (or motor, depending on config)
        wheel_rpm, _ = self.wheel_sensor._compute_rpm()
        setpoint = self._setpoint

        # PID control
        if wheel_rpm is None:
            return eventtime + self.sample_t
        error = setpoint - wheel_rpm
        self._integral += error * self.sample_t
        derivative = (error - self._last_err) / self.sample_t
        self._last_err = error

        pwm = self.kp * error + self.ki * self._integral + self.kd * derivative
        pwm = max(0.0, min(1.0, pwm))
        self._pwm = pwm

        # Set AFC assist motor
        self.afc_motor.set_pwm(pwm)
        # Optionally update wheel sensor with current pwm
        self.wheel_sensor.current_pwm = pwm

        # Schedule next loop
        return eventtime + self.sample_t
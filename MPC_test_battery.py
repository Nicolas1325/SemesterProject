import numpy as np
import control as control
import cvxpy
import matplotlib.pyplot as plt
import time

kelvin = 273.15


class test_EMS_MPC_temperature():
    def __init__(self):
        self.ems_dt = 5 * 60
        self.T = 60 * 60 * 6 / self.ems_dt
        self.M = 60 * 60 * 6 / self.ems_dt  # Number of simulation steps
        self.R = 0.0066
        self.cw = 1565600
        self.p_air = 1.292
        self.Vroom = 192
        self.cm_air = 1005
        self.cr = self.p_air * self.Vroom * self.cm_air

    def mpc_control(self, temp_cur, temp_wall_cur, temp_ext, elec_price, battery_energy):
        x = cvxpy.Variable(2, self.T + 1)
        u = cvxpy.Variable(1, self.T)
        uh = cvxpy.Variable(1, self.T)
        ub = cvxpy.Variable(1, self.T)
        Eb = cvxpy.Variable(1, self.T + 1)
        epsi = cvxpy.Variable(1, self.T + 1)
        q = 100

        A, B, B1 = self.get_model()

        totalcost = 0.0
        constr = []
        for t in range(self.T):
            constr += [x[:, t + 1] == A * x[:, t] + B * uh[0, t] + B1 * temp_ext[t]]
            constr += [x[0, t + 1] <= kelvin + 30+epsi[t + 1]]
            constr += [x[0, t + 1] >= kelvin + 26-epsi[t + 1]]
            constr += [uh[0, t] <= 5000]
            constr += [uh[0, t] >= 0]
            constr += [u[0, t] >= 0]
            constr += [u[0, t] == uh[0, t] + ub[0, t]]
            constr += [Eb[0, t + 1] == Eb[0, t] + ub[0, t] * self.ems_dt/3600.0]
            constr += [Eb[0, t + 1] <= 3300]
            constr += [Eb[0, t + 1] >= 0]
            constr += [ub[0, t] <= 3000]
            constr += [ub[0, t] >= -3000]

        constr += [x[:, 0] == np.array([[temp_cur], [temp_wall_cur]])]
        constr += [Eb[0, 0] == battery_energy]
        constr += [epsi[0] == 30]

        for t in range(self.T):
            totalcost += elec_price[t] * (u[t]) + cvxpy.quad_form(epsi[t + 1], q)

        prob = cvxpy.Problem(cvxpy.Minimize(totalcost), constr)

        # print cvxpy.installed_solvers()

        t0 = time.time()
        prob.solve(verbose=True, solver=cvxpy.ECOS, feastol=1e-6, reltol = 1e-6, abstol=1e-5)
        t1 = time.time()

        print("delta T = " + str(t1 - t0))
        print("Horizon bett: {0}".format(Eb.value[0, :]))
        # if prob.status == cvxpy.OPTIMAL:
        ph_opt = np.array(uh.value[0, :]).flatten()
        pb_opt = np.array(ub.value[0, :]).flatten()
        return [ph_opt[0], pb_opt[0]]
        # else:
        #    print("problem infeasible")

    def get_model(self):
        Acont = np.array([[-1 / (self.cr * self.R), 1 / (self.cr * self.R)],
                          [1 / (self.cw * self.R), -2 / (self.cw * self.R)]])
        Bcont = np.array([[1 / self.cr, 0],
                          [0, 1 / (self.cw * self.R)]])
        C = np.array([[1, 0]])
        D = np.array([[0, 0]])
        sys = control.ss(Acont, Bcont, C, D)
        sysd = control.sample_system(sys, self.ems_dt)
        Adisc, Bdisc, Cdisc, Ddisc = control.ssdata(sysd)

        return Adisc, Bdisc[:, 0], Bdisc[:, 1]

    def update(self, current_t, wall_temperature, ext_temperature, elec_price, battery_energy):
        [ph_opt, pb_opt] = self.mpc_control(current_t, wall_temperature, ext_temperature, elec_price, battery_energy)
        return [ph_opt, pb_opt]


def get_elec_price(N, M):
    elec_price = [0.02]
    for i in range(N + M - 1):
        if i <= round((N + M - 1) / 16):
            elec_price_t = 0.02
        if (i > round((N + M - 1) / 16)) and (i <= round((N + M - 1) / 8)):
            elec_price_t = 0.15
        if (i > round((N + M - 1) / 8)) and (i <= round(3 * (N + M - 1) / 16)):
            elec_price_t = 0.06
        if (i > round(3 * (N + M - 1) / 16)) and (i <= round((N + M - 1) / 4)):
            elec_price_t = 0.02
        if (i > round((N + M - 1) / 4)) and (i <= round(5 * (N + M - 1) / 16)):
            elec_price_t = 0.08
        if (i > round(5 * (N + M - 1) / 16)) and (i <= round(3 * (N + M - 1) / 8)):
            elec_price_t = 0.2
        if (i > round(3 * (N + M - 1) / 8)) and (i <= round(7 * (N + M - 1) / 16)):
            elec_price_t = 0.1
        if (i > round(7 * (N + M - 1) / 16)) and (i <= (N + M - 1) / 2):
            elec_price_t = 0.02
        if (i > round((N + M - 1) / 2)) and i <= round(9 * (N + M - 1) / 16):
            elec_price_t = 0.02
        if (i > round(9 * (N + M - 1) / 16)) and (i <= round(5 * (N + M - 1) / 8)):
            elec_price_t = 0.15
        if (i > round(5 * (N + M - 1) / 8)) and (i <= round(11 * (N + M - 1) / 16)):
            elec_price_t = 0.06
        if (i > round(11 * (N + M - 1) / 16)) and (i <= round(3 * (N + M - 1) / 4)):
            elec_price_t = 0.02
        if (i > round(3 * (N + M - 1) / 4)) and (i <= round(13 * (N + M - 1) / 16)):
            elec_price_t = 0.08
        if (i > round(13 * (N + M - 1) / 16)) and (i <= round(7 * (N + M - 1) / 8)):
            elec_price_t = 0.2
        if (i > round(7 * (N + M - 1) / 8)) and (i <= round(15 * (N + M - 1) / 16)):
            elec_price_t = 0.1
        if (i > round(15 * (N + M - 1) / 16)) and (i <= N + M - 1):
            elec_price_t = 0.02

        elec_price += [elec_price_t];
    return elec_price


def get_ext_temp(N, M):
    Tavg = kelvin + 5
    Text = [Tavg]
    Magnetude = 5
    for i in range(N + M - 1):
        Text += [Tavg + Magnetude * np.sin(2 * np.pi * i / M)]
    return Text


ems = test_EMS_MPC_temperature()
ext_temperature = get_ext_temp(ems.T, ems.M)
elec_price = get_elec_price(ems.T, ems.M)

Tins = kelvin + 0
Twall = (Tins + ext_temperature[0]) / 2
T = np.array([[Tins], [Twall]])
battery_energy = 3600 * 0

history_Tins = []
history_Ph = []
history_Pb = []
history_Tw = []
history_Eb = []

for i in range(ems.M):
    [optimal_Ph, optimal_Pb] = ems.update(Tins, Twall, ext_temperature[i:i + ems.T], elec_price[i:i + ems.T],
                                          battery_energy)
    [A, B1, B2] = ems.get_model()
    T = np.dot(A, T) + np.dot(B1, optimal_Ph) + np.dot(B2, ext_temperature[i])
    Tins = T.item(0)
    Twall = T.item(1)
    battery_energy = battery_energy + optimal_Pb * ems.ems_dt/3600.0
    print("Battery energy: " + str(battery_energy))
    history_Tins += [Tins - kelvin]
    history_Tw += [Twall - kelvin]
    history_Ph += [optimal_Ph]
    history_Pb += [optimal_Pb]
    history_Eb += [battery_energy]

plt.figure()
plt.subplot(311)
plt.plot(range(ems.M), history_Ph)
plt.title("power heater")
plt.subplot(312)
plt.plot(range(ems.M), history_Tw, label="1")
plt.plot(range(ems.M), history_Tins, label="2")
plt.title("Temperature")
plt.subplot(313)
plt.plot(range(ems.M), elec_price[0:ems.M])
plt.title("Electricity price")

plt.figure()
plt.subplot(311)
plt.plot(range(ems.M), history_Pb)
plt.title("power battery")
plt.subplot(312)
plt.plot(range(ems.M), elec_price[0:ems.M])
plt.title("Electricity price")
plt.subplot(313)
plt.plot(range(ems.M), history_Eb)
plt.title("Battery energy")
plt.show()

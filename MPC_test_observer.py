import numpy as np
import control as control
import cvxpy
import matplotlib.pyplot as plt
import time

kelvin=273.15
class test_EMS_MPC_temperature():
    def __init__(self):


        self.ems_dt=10*60
        self.T = 60*60*6/self.ems_dt
        self.M=60*60*12/self.ems_dt #Number of simulation steps
        self.R = 0.0066
        self.cw = 1565600
        self.p_air = 1.292
        self.Vroom = 192
        self.cm_air = 1005
        self.cr = self.p_air * self.Vroom * self.cm_air

    def mpc_control(self, temp_cur, temp_wall_cur, temp_ext, elec_price):

        x = cvxpy.Variable(2, self.T + 1)
        u = cvxpy.Variable(1, self.T)
        epsi = cvxpy.Variable(1, self.T + 1)
        q = 100

        A, B, B1 = self.get_model()

        totalcost = 0.0
        constr = []
        for t in range(self.T):
            totalcost += elec_price[t]*u[t] + cvxpy.quad_form(epsi[t + 1], q)
            constr += [x[:, t + 1] == A * x[:, t] + B * u[t] + B1*temp_ext[t]]

            constr += [x[0, t + 1] <= kelvin+30+epsi[t + 1]]
            constr += [x[0, t + 1] >= kelvin+26-epsi[t + 1]]
            constr += [u[t] <= 5000]
            constr += [u[t] >= 0]
        constr += [x[:, 0] == np.array([[temp_cur],[temp_wall_cur]])]
        constr += [epsi[0] == 30]

        prob = cvxpy.Problem(cvxpy.Minimize(totalcost), constr)
        t0 = time.time()
        prob.solve(verbose=False)#, solver=cvxpy.ECOS, abstol=1e-2, reltol=1e-3, feastol=1e-4, warm_start=True)
        t1 = time.time()
        print("Problem solving time =" + str(t1 - t0))
        if prob.status == cvxpy.OPTIMAL:
            p_opt = np.array(u.value[0, :]).flatten()
            return p_opt[0]
        else:
            print("problem infeasible")

    def get_model(self):
        Acont=np.array([[-1/(self.cr*self.R), 1/(self.cr*self.R)],
                        [1/(self.cw * self.R), -2/(self.cw * self.R)]])
        Bcont=np.array([[1/self.cr, 0],
                        [0, 1/(self.cw*self.R)]])
        C=np.array([[1, 0]])
        D=np.array([[0,0]])
        sys=control.ss(Acont,Bcont,C,D)
        sysd = control.sample_system(sys,self.ems_dt)
        Adisc,Bdisc,Cdisc,Ddisc=control.ssdata(sysd)

        return Adisc, Bdisc[:,0],Bdisc[:,1]

    def update(self, current_t, wall_temperature, ext_temperature,  elec_price):
        t2=time.time()
        p_opt = self.mpc_control(current_t, wall_temperature, ext_temperature, elec_price)
        t3=time.time()
        #print("t mpc" + str(t3-t2))
        return p_opt

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

def get_ext_temp(N,M):
    Tavg=kelvin+5
    Text=[Tavg]
    Magnetude=5
    for i in range(N+M-1):
        Text+=[Tavg+Magnetude*np.sin(2*np.pi*i/M)]
    return Text

def get_observer(A,C,poles):
    C_tr=np.matrix.transpose(C)
    A_tr=np.matrix.transpose(A)
    L_tr=control.acker(A_tr,C_tr,poles)
    return np.matrix.transpose(L_tr)
ems=test_EMS_MPC_temperature()
ext_temperature = get_ext_temp(ems.T, ems.M)
elec_price = get_elec_price(ems.T, ems.M)

Tins=kelvin+27
Twall=(Tins+ext_temperature[0])/2
T=np.array([[Tins], [Twall]])
Tnoise=np.array([[Tins], [Twall]])

history_Tins=[]
history_Tins_pred=[]
history_P_noise=[]
history_P=[]
history_Tw_pred=[]
history_Twall=[]
history_Tins_noise=[]
history_Twall_noise=[]
total_error_observer=0
total_error_without_observer=0

T_pred=np.array([[Tins],[Twall]]);
T_pred_without_observer=np.array([[Tins],[Twall]]);
for i in range(ems.M):
    optimal_P_noise = ems.update(Tnoise.item(0), T_pred.item(1), ext_temperature[i:i+ems.T], elec_price[i:i+ems.T])
    optimal_P = ems.update(T.item(0), T.item(1), ext_temperature[i:i+ems.T], elec_price[i:i+ems.T])
    [A,B1,B2]=ems.get_model()
    T=np.dot(A,T)+np.dot(B1,optimal_P)+np.dot(B2,ext_temperature[i])
    Tnoise=np.dot(A,Tnoise)+np.dot(B1,optimal_P_noise)+np.dot(B2,ext_temperature[i])+ 1*(np.random.random_sample((2,1)))

    C=np.array([[1,0]])
    L=get_observer(A,C,[np.complex(0.5,0.1),np.complex(0.5,-0.1)])
    #print("L="+ str(L))
    #print("A="+ str(A))

    T_pred=np.dot(A-np.dot(L,C),T_pred)+np.dot(L,Tnoise.item(0))+np.dot(B1,optimal_P_noise)+np.dot(B2,ext_temperature[i])
    T_pred_without_observer=np.dot(A,T_pred_without_observer)+np.dot(B1,optimal_P_noise)+np.dot(B2,ext_temperature[i])

    Tins_noise=Tnoise.item(0)
    Twall_noise=Tnoise.item(1)
    Tins=T.item(0)
    Twall=T.item(1)
    Tins_pred=T_pred.item(0)
    Twall_pred=T_pred.item(1)
    Twall_pred_without_observer=T_pred_without_observer.item(1)
    error=(Twall_noise-Twall_pred)**2
    error_without_observer=(Twall_noise-Twall_pred_without_observer)**2
    total_error_observer+=error
    total_error_without_observer+=error_without_observer
    history_Tins_pred+=[Tins_pred-kelvin]
    history_Tins+=[Tins-kelvin]
    history_Tins_noise+=[Tins_noise-kelvin]
    history_Twall_noise+=[Twall_noise-kelvin]
    history_Tw_pred+=[Twall_pred-kelvin]
    history_Twall+=[Twall-kelvin]
    history_P_noise+=[optimal_P_noise]
    history_P+=[optimal_P]

print("Sum of error squared observer= " + str(total_error_observer))
print("Sum of error squared without observer= " + str(total_error_without_observer))
plt.figure()
plt.subplot(411)
plt.plot(range(ems.M),history_P)
plt.plot(range(ems.M),history_P_noise)
plt.legend(["P","P_with_noise"])
plt.title("power")
plt.subplot(412)
plt.plot(range(ems.M),history_Tins, label="2")
plt.plot(range(ems.M),history_Tins_pred, label="3")
plt.plot(range(ems.M),history_Tins_noise, label="3")
plt.legend(["Tins","Tins_pred","Tins_noise"])
plt.subplot(413)
plt.plot(range(ems.M),history_Twall, label="4")
plt.plot(range(ems.M),history_Tw_pred, label="1")
plt.plot(range(ems.M),history_Twall_noise, label="3")
plt.legend(["Twall","Twall_pred","Twall_noise"])
plt.title("Temperature wall")
plt.subplot(414)
plt.plot(range(ems.M),elec_price[0:ems.M])
plt.title("Electricity price")
plt.show()

                                 

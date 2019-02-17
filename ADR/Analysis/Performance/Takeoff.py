from math import sin, cos, radians, degrees
import pandas as pd

from ADR.Methods.FundamentalEquations import lift, drag, moment

class Takeoff:
    def __init__(self, plane, takeoff_parameters):

        self.plane = plane
        self.rho_air = takeoff_parameters.get("rho_air")
        self.dist_max = takeoff_parameters.get("dist_max")
        self.offset_pilot = takeoff_parameters.get("offset_pilot")

        self.distx_wing1_tpr = abs(plane.wing1.ca.abs_x - plane.tpr.x)
        self.distz_wing1_tpr = abs(plane.wing1.ca.abs_z - plane.tpr.z)

        self.distx_wing2_tpr = abs(plane.wing2.ca.abs_x - plane.tpr.x)
        self.distz_wing2_tpr = abs(plane.wing2.ca.abs_z - plane.tpr.z)

        self.distx_hs_tpr = abs(plane.hs.ca.abs_x - plane.tpr.x)
        self.distz_hs_tpr = abs(plane.hs.ca.abs_z - plane.tpr.z)

        self.distx_cg_tpr = abs(plane.cg.x - plane.tpr.x)
        self.distz_cg_tpr = abs(plane.cg.z - plane.tpr.z)

        self.distx_motor_tpr = abs(plane.motor.x - plane.tpr.x)
        self.distz_motor_tpr = abs(plane.motor.z - plane.tpr.z)

    def get_mtow(self):

        m = 1 # Massa total inicial do aviao [kg]
        g = 9.81 # Constante gravitacional [m/s^2]
        S_w1 = self.plane.wing1.area
        S_w2 = self.plane.wing2.area

        dt = 0.01 # Incremento discreto de tempo [s]
        dm = 0.1 #Incremento de massa [kg]

        incidence_active_hs = 10 # Angulo de incidencia adicionado no profundor ao ser acionado [deg]

        takeoff_failed = False

        self.mtow = 0

        self.mass_dict = {}

        while(not takeoff_failed):
            m = m+dm

            theta_airplane_deg = 0 # Angulo do aviao com a pista [°]
            V_x = 0 # Velocidade inicial do aviao no eixo X [m/s]
            V_y = 0 # Velocidade inicial do aviao no eixo Y [m/s]
            pilot_triggered = False # O piloto acionou o profundor?

            dist_x = 0 # Distancia percorrida em X [m]
            N = 0.1 # Força normal [N]
            t = 0 # Tempo [s]

            incidence_w1 = 0 # Angulo de incidencia da asa1 [deg]
            incidence_w2 = 0 # Angulo de incidencia da asa2 [deg]
            incidence_hs = 0 # Angulo de incidencia do profundor [deg]

            on_ground = True
            takeoff_failed = False

            time_dict = {}

            while(on_ground and not takeoff_failed):

                alpha_w1 = theta_airplane_deg + incidence_w1
                if self.plane.plane_type == 'biplane':
                    alpha_w2 = theta_airplane_deg + incidence_w2
                alpha_hs = theta_airplane_deg + incidence_hs

                E = self.plane.motor.thrust(V_x)

                t = t + dt

                L_w1 = self.plane.wing1.lift(self.rho_air, V_x, alpha_w1)
                L_w2 = 0 # Value if there's no wing2
                if self.plane.plane_type == 'biplane':
                    L_w2 = self.plane.wing2.lift(self.rho_air, V_x, alpha_w2)
                L_hs = self.plane.hs.lift(self.rho_air, V_x, alpha_hs)
                L = L_w1 + L_w2 - L_hs

                E_z = E*sin(radians(theta_airplane_deg))
                W = m*g

                N = W - L - E_z

                E_x = E*cos(radians(theta_airplane_deg))

                D_w1 = self.plane.wing1.drag(self.rho_air, V_x, alpha_w1)
                D_w2 = 0 # Value if there's no wing2
                if self.plane.plane_type == 'biplane':
                    D_w2 = self.plane.wing2.drag(self.rho_air, V_x, alpha_w2)
                D_hs = self.plane.hs.drag(self.rho_air, V_x, alpha_hs)
                D_tp = drag(self.rho_air, V_x, S_w1, self.plane.CD_tp)
                D_fus = drag(self.rho_air, V_x, S_w1, self.plane.CD_fus)
                D = D_w1 + D_w2 + D_hs + D_tp + D_fus

                F_at = self.plane.u_k*N

                F_x = E_x - D - F_at
                dV_x = ((F_x)/m) * dt
                V_x = V_x + dV_x
                dist_x = dist_x + V_x * dt

                M_w1 = self.plane.wing1.moment(self.rho_air, V_x, alpha_w1)
                M_w2 = 0 # Value if there's no wing2
                if self.plane.plane_type == 'biplane':
                    M_w2 = self.plane.wing2.moment(self.rho_air, V_x, alpha_w2)
                M_hs = self.plane.hs.moment(self.rho_air, V_x, alpha_hs)

                M_x = E_z*self.distx_motor_tpr - W*self.distx_cg_tpr + L_w1*self.distx_wing1_tpr + L_w2*self.distx_wing2_tpr + L_hs*self.distx_hs_tpr
                M_z = - E_x*self.distz_motor_tpr + D_w1*self.distz_wing1_tpr + D_w2*self.distz_wing2_tpr + D_hs*self.distz_hs_tpr
                M = M_x + M_z - M_hs + M_w1 + M_w2
                dOmega = (M/self.plane.Iyy_TPR)*dt
                dTheta = dOmega*dt

                if theta_airplane_deg + degrees(dTheta) >= 0:
                    theta_airplane_deg = theta_airplane_deg + degrees(dTheta)

                if (self.dist_max-dist_x) <= self.offset_pilot and pilot_triggered == False:
                    incidence_hs += incidence_active_hs
                    pilot_triggered = True
                    alpha_hs = theta_airplane_deg + incidence_hs

                if dist_x > self.dist_max:
                    takeoff_failed = True
                else:
                    takeoff_failed = False
                    self.mtow = m

                if N>0:
                    on_ground = True
                else:
                    on_ground = False

                time_data = [theta_airplane_deg, E, L, L_w1, L_w2, L_hs, D, D_w1, D_w2, D_hs, N, F_at, V_x, dist_x, M, M_w1, M_w2, M_hs, dTheta, incidence_hs]
                time_dict[t] = time_data

            time_df = pd.DataFrame.from_dict(time_dict, orient="index", columns=["theta", "E", "L", "L_w1", "L_w2", "L_hs", "D", "D_w1", "D_w2", "D_hs", "N", "F_at", "V_x", "dist_x", "M", "M_w1", "M_w2", "M_hs", "dTheta", "incidence_hs"])
            time_df.index.name = 't'
            self.mass_dict[m] = time_df

        return self.mtow
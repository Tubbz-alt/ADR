"""
Origem: Bordo de ataque da asa raiz
"""

# Descobre o intervalo aceitavel de posicionamento do CG
import math
from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
from scipy import interpolate

from ADR.Components.References.Static_margin import SM
from ADR.Components.Points.CG import CG
from ADR.Core.data_manipulation import dict_to_dataframe


class FlightStability:
    def __init__(self, plane):
        self.plane = plane
        self.wing1 = self.plane.wing1
        self.wing2 = self.plane.wing2  # wing2 equals wing 1 for now (monoplane)
        self.hs = self.plane.hs

        if self.plane.plane_type != "monoplane" and self.plane.plane_type != "biplane":
            print("Incapable of analysing FlightStability of this plane type")

    # def vary_CG(self, cg_x_range, cg_z_range):
    #     CM_plane_changing_CG = {}
    #     SM_plane_changing_CG = {}
    #     name = 1
    #     for cg_x in cg_x_range:
    #         for cg_z in cg_z_range:
    #             cg = CG({"x": cg_x, "z": cg_z})
    #             cg.tag = "cg" + str(name)
    #             CM_plane_changing_CG[cg.tag] = self.CM_plane_CG(cg)
    #             SM_plane_changing_CG[cg.tag] = self.static_margin()
    #             name += 1
    #     return CM_plane_changing_CG, SM_plane_changing_CG

    def CM_plane_CG(self, cg):
        self.surfaces_stall_min = min(self.wing1.stall_min, self.wing2.stall_min, key=abs)
        self.surfaces_stall_max = min(self.wing1.stall_max, self.wing2.stall_max, key=abs)

        incidence_min = min(self.wing1.incidence, self.wing2.incidence)
        incidence_max = max(self.wing1.incidence, self.wing2.incidence)

        self.plane_stall_min = self.surfaces_stall_min - incidence_min
        self.plane_stall_max = self.surfaces_stall_max - incidence_max

        self.alpha_plane_range = np.arange(self.plane_stall_min, self.plane_stall_max + 1)

        CM_alpha_CG_tail = {}
        CM_alpha_CG_wing1 = {}
        CM_alpha_CG_wing2 = {}
        CM_alpha_CG_wings = {}
        CM_alpha_CG_plane = {}
        self.CM_alpha_CG_plane_each_hs_incidence = {}

        for alpha_plane in self.alpha_plane_range:

            self.wing1.update_alpha(float(alpha_plane))
            self.wing2.update_alpha(float(alpha_plane))

            # Getting CM_alpha of wing1
            CM_alpha_CG_wing1[alpha_plane] = self.wing1.moment_on_CG(self.wing1, self.plane.cg, alpha_plane)

            CM_alpha_CG_wings[alpha_plane] = CM_alpha_CG_wing1[alpha_plane]

            if self.plane.plane_type == "biplane":
                CM_alpha_CG_wing2[alpha_plane] = self.wing2.moment_on_CG(self.wing1, self.plane.cg, alpha_plane)
                CM_alpha_CG_wings[alpha_plane] += CM_alpha_CG_wing2[alpha_plane]

        for hs_incidence in self.hs.get_alpha_range():
            self.hs.incidence = hs_incidence
            for alpha_plane in self.alpha_plane_range:
                self.hs.update_alpha(float(alpha_plane))

                if self.hs.attack_angle in self.hs.get_alpha_range():
                    # Getting CM_alpha of tail
                    CM_alpha_CG_tail[alpha_plane] = self.hs.moment_on_CG(self.wing1, self.plane.cg, alpha_plane)

                    # Summing CM of tail with CM of wing per each alpha
                    # Getting CM_alpha of plane
                    CM_alpha_CG_plane[alpha_plane] = CM_alpha_CG_wings[alpha_plane] + CM_alpha_CG_tail[alpha_plane]
                else:
                    CM_alpha_CG_tail[alpha_plane] = None
                    CM_alpha_CG_plane[alpha_plane] = None

            CM_alpha_CG_plane_df = dict_to_dataframe(CM_alpha_CG_plane, 'CM', 'alpha')
            self.CM_alpha_CG_plane_each_hs_incidence[hs_incidence] = CM_alpha_CG_plane_df

        self.trimm()

        dCM_dalpha_plane_df = CM_alpha_CG_plane_df.diff()
        dCM_dalpha_plane_df.fillna(method="bfill", inplace=True)
        self.plane.dCM_dalpha = dCM_dalpha_plane_df

        self.wing1.CM_alpha_CG = dict_to_dataframe(CM_alpha_CG_wing1, 'CM', 'alpha')
        self.wing2.CM_alpha_CG = dict_to_dataframe(CM_alpha_CG_wing2, 'CM', 'alpha')
        self.hs.CM_alpha_CG = dict_to_dataframe(CM_alpha_CG_tail, 'CM', 'alpha')

        return self.CM_alpha_CG_plane_each_hs_incidence

    def static_margin(self):
        SM_alpha = {}
        self.hs.incidence = 0
        for alpha_plane in self.alpha_plane_range:
            self.wing1.update_alpha(float(alpha_plane))
            self.wing2.update_alpha(float(alpha_plane))
            self.hs.update_alpha(float(alpha_plane))

            if self.hs.attack_angle in self.hs.get_alpha_range():
                # Calculating Static Margin for each alpha
                self.sm = SM(self.plane.plane_type,
                            self.wing1, self.wing2, self.hs,
                            alpha_plane,
                            self.plane.dCM_dalpha.at[alpha_plane, 'CM']) #TODO: We should pass the entire plane into SM analysys
                SM_alpha[alpha_plane] = self.sm.SM

        self.SM_alpha_df = dict_to_dataframe(SM_alpha, 'SM', 'alpha')
        self.plane.SM_alpha = self.SM_alpha_df
        return self.SM_alpha_df

    def trimm(self):
        tail_trimm = {}
        for hs_incidence, CM_alpha_CG in self.CM_alpha_CG_plane_each_hs_incidence.items():
            cm_min = 1000
            for alpha, value in CM_alpha_CG.iterrows():
                cm = value[0]
                if abs(cm) < abs(cm_min):
                    cm_min = cm
                    alpha_cm_min = alpha
            tail_trimm[alpha_cm_min] = hs_incidence
        self.tail_trimm = tail_trimm
        self.tail_trimm_df = dict_to_dataframe(tail_trimm, 'hs_incidence', 'alpha')
        self.plane.tail_trimm = self.tail_trimm_df

        self.plane.alpha_trimm_min = min(tail_trimm, key=tail_trimm.get)
        self.plane.alpha_trimm_max = max(tail_trimm, key=tail_trimm.get)

        return self.tail_trimm_df
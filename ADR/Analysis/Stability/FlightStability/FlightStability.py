"""
Origem: Bordo de ataque da asa raiz
"""

# Descobre o intervalo aceitavel de posicionamento do CG
import math
from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
from scipy import interpolate
from scipy.optimize import root_scalar

from ADR.Components.References.Static_margin import SM


class FlightStability:
    def __init__(self, plane_type, plane):
        self.plane_type = plane_type
        self.plane = plane
        self.wing1 = self.plane.wing1
        self.wing2 = self.plane.wing2     # wing2 equals wing 1 for now (monoplane)
        self.hs = self.plane.hs
        self.cg = self.plane.cg

        self.CM_alpha_CG_plane_obj = None
        self.CM_alpha_CG_plane_root = None

    # ------ Analise ------ #
    def CM_plane_CG(self):

        alpha_wing1_range = range(self.wing1.stall_min, self.wing1.stall_max + 1)
        alpha_wing2_range = range(self.wing2.stall_min, self.wing2.stall_max + 1)
        alpha_tail_range = range(self.hs.stall_min, self.hs.stall_max + 1)

        self.plane_stall_min = max(self.hs.stall_min, self.wing1.stall_min)
        self.plane_stall_max = min(self.hs.stall_max, self.wing1.stall_max)
        self.alpha_plane_range = range(self.plane_stall_min, self.plane_stall_max + 1)

        CM_alpha_CG_tail = {}
        CM_alpha_CG_wing1 = {}
        CM_alpha_CG_wing2 = {}
        CM_alpha_CG_wings = {}
        CM_alpha_CG_plane = {}

        for alpha_plane in self.alpha_plane_range:

            self.wing1.attack_angle = self.wing2.attack_angle = float(alpha_plane)
            self.hs.attack_angle = -float(alpha_plane)

            # Getting CM_alpha of wing1
            CM_alpha_CG_wing1[alpha_plane] = self.wing1.moment_on_CG("wing", self.wing1, self.cg,
                                                                     alpha_plane)

            # For biplane, add moment of wing2
            CM_alpha_CG_wing2[alpha_plane] = 0
            if self.plane_type == "biplane":
                CM_alpha_CG_wing2[alpha_plane] = self.wing2.moment_on_CG("wing", self.wing1, self.cg,
                                                                         alpha_plane)

            CM_alpha_CG_wings[alpha_plane] = CM_alpha_CG_wing1[alpha_plane] + CM_alpha_CG_wing2[alpha_plane]

            # Getting CM_alpha of tail
            CM_alpha_CG_tail[alpha_plane] = self.hs.moment_on_CG("hs", self.wing1, self.cg, alpha_plane)

        for alpha_plane in self.alpha_plane_range:
            # Summing CM of tail with CM of wing per each alpha
            # Getting CM_alpha of plane
            CM_alpha_CG_plane[alpha_plane] = CM_alpha_CG_wings[alpha_plane] + CM_alpha_CG_tail[alpha_plane]

        CM_alpha_CG_plane_df = pd.DataFrame.from_dict(CM_alpha_CG_plane, orient="index", columns=["CM"])
        CM_alpha_CG_plane_df.index.name = 'alpha'
        dCM_dalpha_plane_df = CM_alpha_CG_plane_df.diff()
        dCM_dalpha_plane_df.fillna(method="bfill", inplace=True)
        self.plane.dCM_dalpha = dCM_dalpha_plane_df

        self.wing1.CM_alpha_CG = pd.DataFrame.from_dict(CM_alpha_CG_wings, orient="index", columns=["CM"])
        self.wing1.CM_alpha_CG.index.name = 'alpha'

        self.wing2.CM_alpha_CG = pd.DataFrame.from_dict(CM_alpha_CG_wing2, orient="index", columns=["CM"])
        self.wing2.CM_alpha_CG.index.name = 'alpha'

        self.hs.CM_alpha_CG = pd.DataFrame.from_dict(CM_alpha_CG_tail, orient="index", columns=["CM"])
        self.hs.CM_alpha_CG.index.name = 'alpha'

        self.CM_alpha_CG_plane_df = pd.DataFrame.from_dict(CM_alpha_CG_plane, orient="index", columns=["CM"])
        self.CM_alpha_CG_plane_df.index.name = 'alpha'

        return self.CM_alpha_CG_plane_df

    def static_margin(self):
        SM_alpha = {}
        for alpha_plane in self.alpha_plane_range:
            self.wing1.attack_angle = self.wing2.attack_angle = float(alpha_plane)
            self.hs.attack_angle = -float(alpha_plane)

            # Calculating Static Margin for each alpha
            self.sm = SM(self.plane_type,
                         self.wing1, self.wing2, self.hs,
                         alpha_plane,
                         self.plane.dCM_dalpha.at[alpha_plane, 'CM'])
            SM_alpha[alpha_plane] = self.sm.SM

        self.SM_alpha_df = pd.DataFrame.from_dict(SM_alpha, orient="index", columns=["SM"])
        self.SM_alpha_df.index.name = 'alpha'
        return self.SM_alpha_df

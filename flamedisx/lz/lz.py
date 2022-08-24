"""lz detector implementation

"""
import numpy as np

import configparser
import os
import pandas as pd

import flamedisx as fd

export, __all__ = fd.exporter()


##
# Useful functions
##


def interpolate_acceptance(arg, domain, acceptances):
    """ Function to interpolate signal acceptance curves
    :param arg: argument values for domain interpolation
    :param domain: domain values from interpolation map
    :param acceptances: acceptance values from interpolation map
    :return: Tensor of interpolated map values (same shape as x)
    """
    return np.interp(x=arg, xp=domain, fp=acceptances)


##
# Flamedisx sources
##

##
# Common to all LZ sources
##


class LZSource:
    path_s1_corr = '/Users/Robert/s1_map_22Apr22.json'
    path_s2_corr = '/Users/Robert/s2_map_30Mar22.json'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        assert kwargs['detector'] in ('lz',)

        assert os.path.exists(os.path.join(
            os.path.dirname(__file__), '../nest/config/', kwargs['detector'] + '.ini'))

        config = configparser.ConfigParser(inline_comment_prefixes=';')
        config.read(os.path.join(os.path.dirname(__file__), '../nest/config/',
                                 kwargs['detector'] + '.ini'))

        self.drift_velocity = self.drift_velocity * 0.96 / 0.95

        try:
            self.s1_map = fd.InterpolatingMap(fd.get_resource(self.path_s1_corr))
            self.s2_map = fd.InterpolatingMap(fd.get_resource(self.path_s2_corr))
        except Exception:
            print("Could not load maps; setting position corrections to 1")
            self.s1_map = None
            self.s2_map = None

        try:
            df_S1_acc = pd.read_pickle(os.path.join(os.path.dirname(__file__),
                                       'acceptance_curves/cS1_acceptance_curve.pkl'))
            df_S2_acc = pd.read_pickle(os.path.join(os.path.dirname(__file__),
                                       'acceptance_curves/cS2_acceptance_curve.pkl'))

            self.cs1_acc_domain = df_S1_acc['cS1_phd'].values * (1 + self.double_pe_fraction)  # phd to phe
            self.cs1_acc_curve = df_S1_acc['cS1_acceptance'].values

            self.log10_cs2_acc_domain = df_S2_acc['log10_cS2_phd'].values + \
                np.log10(1 + self.double_pe_fraction)  # log_10(phd) to log_10(phe)
            self.log10_cs2_acc_curve = df_S2_acc['cS2_acceptance'].values
        except Exception:
            print("Could not load acceptance curves; setting to 1")

            self.cs1_acc_domain = None
            self.log10_cs2_acc_domain = None

    @staticmethod
    def s1_posDependence(s1_pos_corr):
        return s1_pos_corr

    @staticmethod
    def s2_posDependence(s2_pos_corr):
        return s2_pos_corr

    def add_extra_columns(self, d):
        super().add_extra_columns(d)

        if (self.s1_map is not None) and (self.s2_map is not None):
            d['s1_pos_corr'] = self.s1_map(
                np.transpose([d['x'].values,
                              d['y'].values,
                              d['drift_time'].values * 1e-9 / 1e-6]))
            d['s2_pos_corr'] = self.s2_map(
                np.transpose([d['x'].values,
                              d['y'].values]))
        else:
            d['s1_pos_corr'] = np.ones_like(d['x'].values)
            d['s2_pos_corr'] = np.ones_like(d['x'].values)

        if 's1' in d.columns and 'cs1' not in d.columns:
            d['cs1'] = d['s1'] / d['s1_pos_corr']
        if 's2' in d.columns and 'cs2' not in d.columns:
            d['cs2'] = (
                d['s2']
                / d['s2_pos_corr']
                * np.exp(d['drift_time'] / self.elife))

        if 'cs1' in d.columns:
            if self.cs1_acc_domain is not None:
                d['cs1_acc_curve'] = interpolate_acceptance(
                    d['cs1'].values,
                    self.cs1_acc_domain,
                    self.cs1_acc_curve)
            else:
                d['cs1_acc_curve'] = np.ones_like(d['cs1'].values)
        if 'cs2' in d.columns:
            if self.log10_cs2_acc_domain is not None:
                d['cs2_acc_curve'] = interpolate_acceptance(
                    np.log10(d['cs2'].values),
                    self.log10_cs2_acc_domain,
                    self.log10_cs2_acc_curve)
            else:
                d['cs2_acc_curve'] = np.ones_like(d['cs2'].values)


##
# Different interaction types: flat spectra
##


@export
class LZERSource(LZSource, fd.nest.nestERSource):
    def __init__(self, *args, **kwargs):
        if ('detector' not in kwargs):
            kwargs['detector'] = 'lz'
        super().__init__(*args, **kwargs)


@export
class LZGammaSource(LZSource, fd.nest.nestGammaSource):
    def __init__(self, *args, **kwargs):
        if ('detector' not in kwargs):
            kwargs['detector'] = 'lz'
        super().__init__(*args, **kwargs)


@export
class LZERGammaWeightedSource(LZSource, fd.nest.nestERGammaWeightedSource):
    def __init__(self, *args, **kwargs):
        if ('detector' not in kwargs):
            kwargs['detector'] = 'lz'
        super().__init__(*args, **kwargs)


@export
class LZNRSource(LZSource, fd.nest.nestNRSource):
    def __init__(self, *args, **kwargs):
        if ('detector' not in kwargs):
            kwargs['detector'] = 'lz'
        super().__init__(*args, **kwargs)


##
# Calibration sources
##


@export
class LZCH3TSource(LZSource, fd.nest.CH3TSource):
    def __init__(self, *args, **kwargs):
        if ('detector' not in kwargs):
            kwargs['detector'] = 'lz'
        super().__init__(*args, **kwargs)


##
# Background sources
##


@export
class LZBetaSource(LZSource, fd.nest.BetaSource):
    def __init__(self, *args, **kwargs):
        if ('detector' not in kwargs):
            kwargs['detector'] = 'lz'
        super().__init__(*args, **kwargs)


@export
class LZXe136Source(LZSource, fd.nest.Xe136Source):
    def __init__(self, *args, **kwargs):
        if ('detector' not in kwargs):
            kwargs['detector'] = 'lz'
        super().__init__(*args, **kwargs)


@export
class LZvERSource(LZSource, fd.nest.vERSource):
    def __init__(self, *args, **kwargs):
        if ('detector' not in kwargs):
            kwargs['detector'] = 'lz'
        super().__init__(*args, **kwargs)


@export
class LZAr37Source(LZSource, fd.nest.Ar37Source):
    def __init__(self, *args, **kwargs):
        if ('detector' not in kwargs):
            kwargs['detector'] = 'lz'
        super().__init__(*args, **kwargs)


@export
class LZXe124Source(LZSource, fd.nest.Xe124Source):
    def __init__(self, *args, **kwargs):
        if ('detector' not in kwargs):
            kwargs['detector'] = 'lz'
        super().__init__(*args, **kwargs)


@export
class LZXe127Source(LZSource, fd.nest.Xe127Source):
    def __init__(self, *args, **kwargs):
        if ('detector' not in kwargs):
            kwargs['detector'] = 'lz'
        super().__init__(*args, **kwargs)


@export
class LZB8Source(LZSource, fd.nest.B8Source):
    def __init__(self, *args, **kwargs):
        if ('detector' not in kwargs):
            kwargs['detector'] = 'lz'
        super().__init__(*args, **kwargs)

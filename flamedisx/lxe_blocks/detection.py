import typing as ty

import numpy as np
from scipy import stats
import tensorflow as tf
import tensorflow_probability as tfp

import flamedisx as fd
export, __all__ = fd.exporter()
o = tf.newaxis


class DetectPhotonsOrElectrons(fd.Block):
    """Common code for DetectPhotons and DetectElectrons"""

    static_attributes = ('check_efficiencies',)

    # Whether to check if all events have a positive detection efficiency.
    # As with check_acceptances in MakeFinalSignals, you may have to
    # turn this off, depending on your application.
    check_efficiencies = True

    quanta_name: str

    # Prevent pycharm warnings:
    source: fd.Source
    gimme: ty.Callable
    gimme_numpy: ty.Callable

    def __compute(self, data_tensor, ptensor,
                  quanta_produced, quanta_detected):
        p = self.gimme(self.quanta_name + '_detection_eff',
                       data_tensor=data_tensor, ptensor=ptensor)[:, o, o]

        if self.quanta_name == 'photon':
            # Note *= doesn't work, p will get reshaped
            p = p * self.gimme('penning_quenching_eff',
                               bonus_arg=quanta_produced,
                               data_tensor=data_tensor, ptensor=ptensor)

        result = tfp.distributions.Binomial(
            total_count=quanta_produced,
            probs=tf.cast(p, dtype=fd.float_type())
        ).prob(quanta_detected)
        return result * self.gimme(self.quanta_name + '_acceptance',
                                   bonus_arg=quanta_detected,
                                   data_tensor=data_tensor, ptensor=ptensor)

    def _simulate(self, d):
        p = self.gimme_numpy(self.quanta_name + '_detection_eff')

        if self.quanta_name == 'photon':
            p *= self.gimme_numpy(
                'penning_quenching_eff', d['photons_produced'].values)

        d[self.quanta_name + 's_detected'] = stats.binom.rvs(
            n=d['photons_produced'],
            p=p)
        d['p_accepted'] *= self.gimme_numpy(
            self.quanta_name + '_acceptance',
            d[self.quanta_name + 's_detected'].values)

    def _annotate(self, d):
        # Get efficiency
        eff = self.gimme_numpy(self.quanta_name + '_detection_eff')
        if self.quanta_name == 'photon':
            eff *= self.gimme_numpy('penning_quenching_eff',
                                    d['photons_detected_mle'].values / eff)

        # Check for bad efficiencies
        if self.check_efficiencies and np.any(eff <= 0):
            raise ValueError(f"Found event with nonpositive {self.quanta_name} "
                             "detection efficiency: did you apply and "
                             "configure your cuts correctly?")

        # Estimate produced quanta
        n_prod_mle = d[self.quanta_name + 's_produced_mle'] = \
            d[self.quanta_name + 's_detected_mle'] / eff

        # Estimating the spread in number of produced quanta is tricky since
        # the number of detected quanta is itself uncertain.
        # TODO: where did this derivation come from again?
        q = 1 / eff
        _std = (q + (q ** 2 + 4 * n_prod_mle * q) ** 0.5) / 2

        for bound, sign, intify in (('min', -1, np.floor),
                                    ('max', +1, np.ceil)):
            d[self.quanta_name + 's_produced_' + bound] = intify(
                n_prod_mle + sign * self.source.max_sigma * _std
            ).clip(0, None).astype(np.int)


@export
class DetectPhotons(DetectPhotonsOrElectrons):
    dimensions = ('photons_produced', 'photons_detected')

    model_functions = ('photon_detection_eff',)
    special_model_functions = ('photon_acceptance', 'penning_quenching_eff')

    photon_detection_eff = 0.1
    photon_acceptance = 1.

    quanta_name = 'photon'

    @staticmethod
    def penning_quenching_eff(nph):
        return 1. + 0. * nph

    def _compute(self, data_tensor, ptensor,
                 photons_produced, photons_detected):
        return self.__compute(quanta_produced=photons_produced,
                              quanta_detected=photons_detected,
                              data_tensor=data_tensor, ptensor=ptensor)


@export
class DetectElectrons(DetectPhotonsOrElectrons):
    dimensions = ('electrons_produced', 'electrons_detected')

    model_functions = ('electron_detection_eff',)
    special_model_functions = ('electron_acceptance',)

    electron_detection_eff = 1.
    electron_acceptance = 1.

    quanta_name = 'electron'

    def _compute(self, data_tensor, ptensor,
                 electrons_produced, electrons_detected):
        return self.__compute(quanta_produced=electrons_produced,
                              quanta_detected=electrons_detected,
                              data_tensor=data_tensor, ptensor=ptensor)

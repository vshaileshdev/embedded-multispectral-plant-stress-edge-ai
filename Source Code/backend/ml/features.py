import numpy as np
from scipy.signal import savgol_filter
from sklearn.base import BaseEstimator, TransformerMixin

class SpectralFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Extracts candidate spectral indices and statistical regional band features
    from 832-channel reflectance vectors.
    Applies Savitzky-Golay smoothing automatically during transform to prevent leakage.
    """
    def __init__(self, wvl_grid, apply_smoothing=True):
        self.wvl_grid = np.asarray(wvl_grid)
        self.apply_smoothing = apply_smoothing

    def _get_band_idx(self, target_nm):
        return int(np.argmin(np.abs(self.wvl_grid - target_nm)))

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = np.asarray(X)
        
        # Apply smoothing internally to prevent leakage and ensure identical processing
        if self.apply_smoothing:
            # Handle both 1D and 2D arrays
            if X.ndim == 1:
                X = X.reshape(1, -1)
                smoothed_X = savgol_filter(X, window_length=11, polyorder=2, axis=1)
            else:
                smoothed_X = savgol_filter(X, window_length=11, polyorder=2, axis=1)
        else:
            if X.ndim == 1:
                smoothed_X = X.reshape(1, -1)
            else:
                smoothed_X = X

        N = smoothed_X.shape[0]
        features = []

        # Band indices
        idx_445 = self._get_band_idx(445)
        idx_500 = self._get_band_idx(500)
        idx_510 = self._get_band_idx(510)
        idx_550 = self._get_band_idx(550)
        idx_670 = self._get_band_idx(670)
        idx_680 = self._get_band_idx(680)
        idx_700 = self._get_band_idx(700)
        idx_720 = self._get_band_idx(720)
        idx_750 = self._get_band_idx(750)
        idx_790 = self._get_band_idx(790)
        idx_800 = self._get_band_idx(800)
        idx_900 = self._get_band_idx(900)
        idx_970 = self._get_band_idx(970)

        eps = 1e-8

        for i in range(N):
            spec = smoothed_X[i]
            r445 = spec[idx_445]
            r500 = spec[idx_500]
            r510 = spec[idx_510]
            r550 = spec[idx_550]
            r670 = spec[idx_670]
            r680 = spec[idx_680]
            r700 = spec[idx_700]
            r720 = spec[idx_720]
            r750 = spec[idx_750]
            r790 = spec[idx_790]
            r800 = spec[idx_800]
            r900 = spec[idx_900]
            r970 = spec[idx_970]

            # 1. Candidate Indices
            ndvi  = (r800 - r670) / (r800 + r670 + eps)
            gndvi = (r800 - r550) / (r800 + r550 + eps)
            ndre  = (r790 - r720) / (r790 + r720 + eps)
            mcari = ((r700 - r670) - 0.2 * (r700 - r550)) * (r700 / (r670 + eps))
            psri  = (r680 - r500) / (r750 + eps)
            sipi  = (r800 - r445) / (r800 - r680 + eps)
            cri   = (1.0 / (r510 + eps)) - (1.0 / (r550 + eps))
            ari   = (1.0 / (r550 + eps)) - (1.0 / (r700 + eps))
            wbi   = r900 / (r970 + eps)
            re_slope = (r750 - r700) / 50.0

            # 2. Regional Statistical Bands
            vis_mean = np.mean(spec[(self.wvl_grid >= 400) & (self.wvl_grid <= 700)])
            re_mean  = np.mean(spec[(self.wvl_grid > 700) & (self.wvl_grid <= 740)])
            nir_mean = np.mean(spec[(self.wvl_grid > 740) & (self.wvl_grid <= 900)])
            nir_water_mean = np.mean(spec[(self.wvl_grid > 900) & (self.wvl_grid <= 1000)])

            row_feat = [
                ndvi, gndvi, ndre, mcari, psri, sipi, cri, ari, wbi, re_slope,
                vis_mean, re_mean, nir_mean, nir_water_mean
            ]
            features.append(row_feat)

        return np.array(features)

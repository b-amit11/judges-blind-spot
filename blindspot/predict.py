import numpy as np
from .data import METRICS
from .features import features


def predict(bundle, frame):
    required = [f'{side}_{metric}' for side in 'ab' for metric in METRICS] + ['round']
    if not set(required).issubset(frame.columns):
        raise ValueError('Missing required round statistics')
    for column in required:
        values = frame[column].astype(float)
        if np.isinf(values).any() or (values.dropna() < 0).any():
            raise ValueError('Statistics must be nonnegative finite numbers or missing')
        if column != 'round' and (values.dropna() % 1 != 0).any():
            raise ValueError('Counts and control seconds must be whole numbers')
    if not frame['round'].isin([1,2,3,4,5]).all():
        raise ValueError('Round must be between one and five')
    if any((frame[f'{s}_control_seconds'] > 300).any() for s in 'ab'):
        raise ValueError('Control cannot exceed 300 seconds')
    x = features(frame)
    warnings = []
    for _, row in x.iterrows():
        missing = [c for c in x if np.isnan(row[c])]
        outside = [c for c in x if row[c] < bundle['limits'][c]['min'] or row[c] > bundle['limits'][c]['max']]
        warnings.append({'missing_features':missing,'outside_training_range':outside})
    return bundle['model'].predict_proba(x)[:,1], warnings

"""Symmetric feature allowlist: no scores, names, outcome or future rounds."""
import numpy as np
import pandas as pd
from .data import METRICS


def features(frame):
    result = pd.DataFrame(index=frame.index)
    for metric in METRICS:
        a, b = frame[f'a_{metric}'].astype(float), frame[f'b_{metric}'].astype(float)
        result[f'{metric}_gap'] = (a-b).abs()
        result[f'{metric}_total'] = a+b
    for side in 'ab':
        if (frame[f'{side}_sig_landed'] > frame[f'{side}_sig_attempted']).any():
            raise ValueError('Landed strikes cannot exceed attempts')
        if (frame[f'{side}_head_landed'] > frame[f'{side}_sig_landed']).any():
            raise ValueError('Significant head strikes cannot exceed significant strikes landed')
    a = frame.a_sig_landed / frame.a_sig_attempted.replace(0, np.nan)
    b = frame.b_sig_landed / frame.b_sig_attempted.replace(0, np.nan)
    result['accuracy_gap'] = (a-b).abs()
    result['striking_grappling_conflict'] = ((frame.a_sig_landed-frame.b_sig_landed) *
                                            (frame.a_takedowns-frame.b_takedowns) < 0).astype(float)
    result['round'] = frame['round'].astype(float)
    return result


def swap_fighters(frame):
    swapped = frame.copy()
    for metric in METRICS:
        swapped[f'a_{metric}'], swapped[f'b_{metric}'] = frame[f'b_{metric}'], frame[f'a_{metric}']
    return swapped

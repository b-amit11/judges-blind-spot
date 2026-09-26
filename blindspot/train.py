"""One predeclared temporal benchmark; select by validation Brier, then test once."""
import json
import hashlib
import platform
import time

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .data import ROOT
from .features import features


def temporal_split(frame):
    dates = sorted(frame.date.unique())
    if len(dates) < 20:
        raise ValueError('Too few event dates for temporal evaluation')
    first, second = dates[int(len(dates)*.70)], dates[int(len(dates)*.85)]
    groups = [frame[frame.date < first], frame[(frame.date >= first) & (frame.date < second)], frame[frame.date >= second]]
    for part in groups:
        if part.target.nunique() != 2:
            raise ValueError('Every split must contain both classes')
    return groups


def metrics(y, probability):
    order = np.argsort(-np.asarray(probability), kind='stable')[:min(20, len(y))]
    return {'average_precision': float(average_precision_score(y, probability)),
            'brier': float(brier_score_loss(y, probability)),
            'log_loss': float(log_loss(y, probability, labels=[0,1])),
            'roc_auc': float(roc_auc_score(y, probability)),
            'precision_at_20': float(np.asarray(y)[order].mean())}


def bootstrap(frame, probability, reference, repeats=400):
    rng = np.random.default_rng(42)
    groups = list(frame.groupby('fight_id', sort=True).indices.values())
    y = frame.target.to_numpy()
    samples = []
    for _ in range(repeats):
        idx = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        samples.append([brier_score_loss(y[idx], probability[idx]),
                        average_precision_score(y[idx], probability[idx]),
                        brier_score_loss(y[idx], reference[idx])-brier_score_loss(y[idx], probability[idx])])
    values = np.quantile(samples, [.025,.975], axis=0)
    return {name: list(values[:, i]) for i, name in enumerate(['brier', 'average_precision', 'brier_improvement_vs_closeness'])}


def linear(columns=None):
    steps = []
    if columns:
        steps.append(('select', ColumnTransformer([('keep', 'passthrough', columns)], remainder='drop')))
    steps += [('impute', SimpleImputer(strategy='median', add_indicator=True)),
              ('scale', StandardScaler()), ('model', LogisticRegression(C=1.0, max_iter=1500, random_state=42))]
    return Pipeline(steps)


def train():
    frame = pd.read_csv(ROOT / 'data/processed/rounds.csv')
    train, valid, test = temporal_split(frame)
    xtrain, xvalid, xtest = map(features, [train, valid, test])
    models = {'constant': DummyClassifier(strategy='prior'),
              'strike_gap': linear(['sig_landed_gap']),
              'logistic': linear(),
              'boosted_trees': Pipeline([('impute', SimpleImputer(strategy='median', add_indicator=True)),
                  ('model', HistGradientBoostingClassifier(max_iter=100, max_leaf_nodes=7, min_samples_leaf=30,
                           learning_rate=.05, l2_regularization=2, early_stopping=False, random_state=42))])}
    validation = {}
    for name, model in models.items():
        model.fit(xtrain, train.target)
        validation[name] = metrics(valid.target, model.predict_proba(xvalid)[:,1])
    selected = min(validation, key=lambda name: (validation[name]['brier'], name))
    # Freeze selection and model before reading final holdout performance. No refit.
    model = models[selected]
    probabilities = {name: m.predict_proba(xtest)[:,1] for name, m in models.items()}
    p = probabilities[selected]
    results = {name: metrics(test.target, pred) for name, pred in probabilities.items()}
    repeats = []
    for _ in range(50):
        start = time.perf_counter()
        model.predict_proba(features(test.head(1)))
        repeats.append((time.perf_counter()-start)*1000)
    importance = permutation_importance(model, xtest, test.target, scoring='neg_brier_score', n_repeats=10, random_state=42)
    observed, predicted = calibration_curve(test.target, p, n_bins=6, strategy='quantile')
    report = {
        'selected_model': selected, 'selection_rule': 'Minimum validation Brier score; candidates fixed before testing',
        'target': 'At least one judge differs on round winner (tie is a third outcome)',
        'validation': validation, 'test': results,
        'splits': {name: {'rounds':len(df), 'fights':int(df.fight_id.nunique()), 'start':df.date.min(),
                          'end':df.date.max(), 'prevalence':float(df.target.mean())}
                   for name, df in zip(['train','validation','test'], [train,valid,test])},
        'bootstrap_95pct': bootstrap(test.reset_index(drop=True), p, probabilities['strike_gap']),
        'bootstrap_note': '400 paired bootstrap samples by fight; conditional on this fitted model. Event clustering and selection uncertainty are not covered.',
        'calibration': {'predicted':predicted.tolist(), 'observed':observed.tolist()},
        'feature_importance': sorted([{'feature':name,'mean_brier_increase':float(mean),'std':float(std)}
             for name, mean, std in zip(xtest.columns, importance.importances_mean, importance.importances_std)], key=lambda x:-x['mean_brier_increase']),
        'local_latency_ms': {'median':float(np.median(repeats)), 'p95':float(np.quantile(repeats,.95)),
                             'note':'50 warm single-row feature+inference calls; excludes network/UI, not a production SLA'},
        'versions': {'python':platform.python_version(),'sklearn':sklearn.__version__},
    }
    limits = {c:{'min':float(xtrain[c].min()),'max':float(xtrain[c].max())} for c in xtrain}
    (ROOT/'artifacts').mkdir(exist_ok=True)
    joblib.dump({'model':model,'name':selected,'features':list(xtrain.columns),'limits':limits}, ROOT/'artifacts/model.joblib')
    report['artifact_integrity'] = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
        for name in ['data/processed/rounds.csv','artifacts/model.joblib']}
    predictions = test.copy()
    predictions['probability'] = p
    predictions['absolute_error'] = (predictions.target-p).abs()
    predictions.to_csv(ROOT/'reports/test_predictions.csv', index=False)
    predictions.sort_values('absolute_error',ascending=False).head(10).to_csv(ROOT/'reports/failures.csv',index=False)
    (ROOT/'reports/metrics.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'selected':selected,'splits':report['splits'],'test':results,'intervals':report['bootstrap_95pct']},indent=2))


if __name__ == '__main__':
    train()

import json
import joblib
import numpy as np
import pandas as pd
import pytest
from blindspot.data import ROOT, disagreement, seconds, normalize
from blindspot.features import features, swap_fighters
from blindspot.predict import predict
from blindspot.train import temporal_split


@pytest.fixture
def example():
    return pd.DataFrame([{'round':2, **{f'{s}_{m}':v for s in 'ab' for m,v in
        {'sig_attempted':40,'sig_landed':20,'knockdowns':0,'takedowns':1,
         'sub_attempts':0,'control_seconds':30,'head_landed':15}.items()}}])


@pytest.mark.parametrize('margins,expected',[([1,1,2],0),([1,-1,1],1),([0,1,1],1),([0,0,0],0),([-2,-1,-1],0)])
def test_target_is_winner_disagreement_not_margin(margins,expected):
    assert disagreement(margins)==expected


def test_invalid_judges_rejected():
    with pytest.raises(ValueError): disagreement([1,1])
    with pytest.raises(ValueError): disagreement([1,np.nan,1])
    with pytest.raises(ValueError): disagreement([1,.5,1])


def test_missing_control_not_zero():
    assert np.isnan(seconds('--'))
    assert seconds('0:00') == 0
    assert seconds('2:15') == 135
    with pytest.raises(ValueError): seconds('5:01')
    with pytest.raises(ValueError): seconds('1:70')


def test_name_normalization():
    assert normalize('José Aldo')==normalize('Jose Aldo')
    assert normalize('Jon Jones')!=normalize('Jon Jones Jr')


def test_symmetry_and_outcome_exclusion(example):
    example['a_sig_landed']=30
    example['b_takedowns']=3
    pd.testing.assert_frame_equal(features(example),features(swap_fighters(example)))
    enriched=example.assign(target=1,judge_1_margin=-1,winner='A',future_round_strikes=90)
    pd.testing.assert_frame_equal(features(example),features(enriched))


def test_zero_attempt_accuracy_is_missing(example):
    example['a_sig_attempted']=0
    example['a_sig_landed']=0
    example['a_head_landed']=0
    assert np.isnan(features(example).accuracy_gap.iloc[0])


def test_temporal_split_keeps_fights_and_dates_together():
    rows=[{'date':f'2020-01-{i:02d}','fight_id':str(i),'target':y} for i in range(1,31) for y in [0,1]]
    parts=temporal_split(pd.DataFrame(rows))
    assert parts[0].date.max()<parts[1].date.min()<parts[2].date.min()
    for i in range(3):
        for j in range(i+1,3):
            assert not set(parts[i].fight_id)&set(parts[j].fight_id)


@pytest.mark.skipif(not (ROOT/'artifacts/model.joblib').exists(),reason='Train artifacts for integration checks')
def test_saved_model_symmetry_validation_and_batch_consistency(example):
    bundle=joblib.load(ROOT/'artifacts/model.joblib')
    example['a_sig_landed']=30
    p,_=predict(bundle,example)
    q,_=predict(bundle,swap_fighters(example))
    np.testing.assert_allclose(p,q,rtol=0,atol=1e-12)
    batch,_=predict(bundle,pd.concat([example,example],ignore_index=True))
    np.testing.assert_allclose(batch,[p[0],p[0]])
    with pytest.raises(ValueError): predict(bundle,example.assign(a_sig_landed=200))
    with pytest.raises(ValueError): predict(bundle,example.assign(a_control_seconds=301))
    with pytest.raises(ValueError): predict(bundle,example.assign(round=6))
    with pytest.raises(ValueError): predict(bundle,example.assign(a_takedowns=-1))
    with pytest.raises(ValueError): predict(bundle,example.assign(a_takedowns=np.inf))


@pytest.mark.skipif(not (ROOT/'data/processed/rounds.csv').exists(),reason='Download data for integration checks')
def test_real_dataset_leakage_and_label_integrity():
    data=pd.read_csv(ROOT/'data/processed/rounds.csv')
    assert not data.duplicated(['fight_id','round']).any()
    reconstructed=data[[f'judge_{i}_margin' for i in [1,2,3]]].apply(lambda r:disagreement(r.tolist()),axis=1)
    np.testing.assert_array_equal(reconstructed,data.target)
    for part in temporal_split(data):
        assert part.target.nunique()==2
    assert features(data).select_dtypes('number').shape[1]==17

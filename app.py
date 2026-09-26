"""Run: streamlit run app.py. All displayed historical predictions are held out."""
import json
import joblib
import pandas as pd
import streamlit as st
from blindspot.data import ROOT, METRICS
from blindspot.predict import predict

st.set_page_config(page_title="Judge's Blind Spot", page_icon='🥊', layout='wide')
st.markdown('''<style>
.block-container {max-width:1200px;padding-top:2.4rem;}
h1 {letter-spacing:-.055em;font-size:3.6rem!important;}
[data-testid="stMetric"] {background:#172029;border:1px solid #2d3945;border-radius:12px;padding:18px;}
.eyebrow {color:#a8e66f;font-size:.78rem;letter-spacing:.19em;font-weight:700;}
.intro {color:#aebdca;max-width:760px;font-size:1.12rem;line-height:1.65;}
</style>''', unsafe_allow_html=True)
st.markdown('<div class="eyebrow">MMA ANALYTICS / RESEARCH PROTOTYPE</div>',unsafe_allow_html=True)
st.title("Judge’s Blind Spot")
st.markdown('<p class="intro">Three judges. One round. Not always one verdict. Prioritize rounds for review using post-round statistics and a model trained on historical judging disagreement.</p>',unsafe_allow_html=True)

if not (ROOT/'artifacts/model.joblib').exists():
    st.info('Build the real-data model first: python -m blindspot.data && python -m blindspot.train')
    st.stop()

@st.cache_resource
def load_model():
    return joblib.load(ROOT/'artifacts/model.joblib')

@st.cache_data
def load_data():
    return pd.read_csv(ROOT/'reports/test_predictions.csv'), json.loads((ROOT/'reports/metrics.json').read_text())

bundle = load_model()
data, report = load_data()
score = report['test'][report['selected_model']]
a,b,c,d = st.columns(4)
a.metric('Held-out rounds',f"{len(data):,}")
b.metric('Average precision',f"{score['average_precision']:.3f}")
c.metric('Disagreement prevalence',f"{data.target.mean():.1%}")
d.metric('Top 20 review precision',f"{score['precision_at_20']:.0%}")
st.caption(f"Historical test period: {data.date.min()}–{data.date.max()}. Model: {bundle['name'].replace('_',' ')}. Estimates are not judgments of scoring correctness.")
review, sandbox, evidence = st.tabs(['01 / Review queue','02 / Round sandbox','03 / Evidence & limitations'])

with review:
    st.subheader('Start with the rounds most likely to divide judges')
    names = sorted(set(data.fighter_a) | set(data.fighter_b))
    fighter = st.selectbox('Filter by fighter',['All fighters']+names)
    shown = data if fighter == 'All fighters' else data[(data.fighter_a==fighter)|(data.fighter_b==fighter)]
    shown = shown.sort_values(['probability','fight_id','round'],ascending=[False,True,True])
    choices = shown.index.tolist()
    idx = st.selectbox('Choose a held-out round', choices,
        format_func=lambda i:f"{data.loc[i,'fighter_a']} vs {data.loc[i,'fighter_b']} · R{data.loc[i,'round']} · {data.loc[i,'date']} · {data.loc[i,'probability']:.0%}")
    row = data.loc[idx]
    left,right = st.columns([1,2])
    with left:
        st.metric('Estimated disagreement probability',f"{row.probability:.1%}")
        st.write(f"**{row.fighter_a}** vs **{row.fighter_b}**")
        st.caption(f"Round {row['round']} · {row.event}")
        st.caption(f"Input summary: significant-strike gap {abs(row.a_sig_landed-row.b_sig_landed):.0f}; control-time gap {abs(row.a_control_seconds-row.b_control_seconds):.0f}s. Global feature importance is in Evidence; these differences are not a causal explanation.")
        _, notices = predict(bundle, data.loc[[idx]])
        if notices[0]['outside_training_range'] or notices[0]['missing_features']:
            st.warning('Some features are missing or outside training ranges; inspect the input before relying on this estimate.')
        if st.checkbox('Reveal observed judge outcomes'):
            st.write('**Judges disagreed**' if row.target else '**Judges agreed on the round winner**')
            st.table(pd.DataFrame({'Judge':['1','2','3'],'Round winner':[row.fighter_a if row[f'judge_{j}_margin']>0 else row.fighter_b if row[f'judge_{j}_margin']<0 else 'Tie' for j in [1,2,3]]}))
    with right:
        comparison = pd.DataFrame({'Statistic':[x.replace('_',' ').title() for x in METRICS],row.fighter_a:[row[f'a_{m}'] for m in METRICS],row.fighter_b:[row[f'b_{m}'] for m in METRICS]})
        st.dataframe(comparison,hide_index=True,width='stretch')
        st.caption('Statistics describe activity, not the full impact of strikes or submission threats. Control is in seconds.')
    with st.expander('View the ranked review queue'):
        st.dataframe(shown[['date','fighter_a','fighter_b','round','probability']].head(100),hide_index=True,width='stretch')

with sandbox:
    st.subheader('Change the round. Inspect the estimate.')
    st.write('Hypothetical inputs only. This is an association model; changing a statistic does not establish a causal effect.')
    inputs = {'round':st.selectbox('Round',[1,2,3,4,5],key='sandbox_round')}
    cols = st.columns(2)
    defaults = {'sig_attempted':60,'sig_landed':25,'knockdowns':0,'takedowns':1,'sub_attempts':0,'control_seconds':30,'head_landed':18}
    for side,col in zip('ab',cols):
        with col:
            st.markdown(f'**Fighter {side.upper()}**')
            for m in METRICS:
                inputs[f'{side}_{m}'] = st.number_input(m.replace('_',' ').title(),min_value=0,max_value=300 if m=='control_seconds' else 1000,value=defaults[m],key=f'{side}_{m}')
    if st.button('Estimate disagreement',type='primary'):
        try:
            probability, notices = predict(bundle,pd.DataFrame([inputs]))
            st.metric('Estimated disagreement probability',f'{probability[0]:.1%}')
            if notices[0]['outside_training_range']:
                st.warning('Outside training ranges: '+', '.join(notices[0]['outside_training_range']))
            if notices[0]['missing_features']:
                st.info('Undefined features were imputed: '+', '.join(notices[0]['missing_features']))
            st.caption('Range checks are a basic guardrail, not a validated out-of-distribution detector.')
        except ValueError as exc:
            st.error(str(exc))

with evidence:
    st.subheader('The model has to earn its complexity')
    st.dataframe(pd.DataFrame(report['test']).T.rename_axis('model').reset_index(),hide_index=True,width='stretch')
    st.caption('Average precision is the reported PR summary, not trapezoidal PR-AUC. Higher is better; Brier and log loss are better when lower. Constant-model top-20 results depend on tie order.')
    st.write('Selected exclusively by validation Brier score. Whole event dates stay together; no fight crosses splits. Model inputs exclude names, judge scores, final results, and later rounds.')
    l,r=st.columns(2)
    with l:
        st.markdown('**Calibration on held-out rounds**')
        st.scatter_chart(pd.DataFrame({'Mean predicted probability':report['calibration']['predicted'],'Observed disagreement':report['calibration']['observed']}),x='Mean predicted probability',y='Observed disagreement')
    with r:
        st.markdown('**Global feature importance**')
        importance=pd.DataFrame(report['feature_importance']).head(7)
        st.bar_chart(importance.set_index('feature')['mean_brier_increase'],horizontal=True)
        st.caption('Permutation increase in held-out Brier score; correlated features can mask importance. This does not explain an individual prediction.')
    st.write('**Critical limitations**')
    st.markdown('''- Historical decision fights only; no claim about unfinished fights or current UFC performance.
- Public source joins exclude rematches and mismatches, creating selection bias.
- Labels come from an external scraper; automated score-total checks cannot prove each individual round is correct.
- Aggregate counts miss damage, timing, positional threat, and judging context.
- Judge disagreement is not evidence that a judge was wrong.
- Fight-clustered intervals do not account for event clustering, data errors, or model-selection uncertainty.''')
    st.json({'splits':report['splits'],'95% fight-bootstrap intervals':report['bootstrap_95pct']})
    st.markdown('Sources: [DylanBaut/MMA_Data_Analysis](https://github.com/DylanBaut/MMA_Data_Analysis) (round stats and scores); [komaksym/UFC-DataLab](https://github.com/komaksym/UFC-DataLab) (dates and cross-checks). Original statistics: UFCStats; judging records: MMA Decisions.')
    st.download_button('Download evaluation report',json.dumps(report,indent=2),'evaluation.json','application/json')

st.divider()
st.caption('JUDGE’S BLIND SPOT · Built to inspect uncertainty, not declare a robbery. Research prototype; no affiliation with UFC or MMA Decisions.')

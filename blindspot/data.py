"""Strict raw-data joins. Outcome fields never enter model features."""
import ast
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'stats.csv': 'https://raw.githubusercontent.com/DylanBaut/MMA_Data_Analysis/aa04256dd35102c0d489b62ed13b58e04a5c471f/UFC.csv',
    'scores.csv': 'https://raw.githubusercontent.com/DylanBaut/MMA_Data_Analysis/aa04256dd35102c0d489b62ed13b58e04a5c471f/decisions.csv',
    'metadata.csv': 'https://raw.githubusercontent.com/komaksym/UFC-DataLab/3268146c05211de9deab8b9b4c0bb4a954815f0b/data/merged_stats_n_scorecards/merged_stats_n_scorecards.csv',
}
METRICS = {
    'sig_attempted': 'Sig_Strikes_Attempted', 'sig_landed': 'Sig_Strikes_Landed',
    'knockdowns': 'KD', 'takedowns': 'TD', 'sub_attempts': 'Sub_Attempts',
    'control_seconds': 'Ctrl_Time', 'head_landed': 'Head_Strikes',
}


def normalize(name):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(name).lower()) if c.isalnum())


def pair(a, b):
    return tuple(sorted([normalize(a), normalize(b)]))


def disagreement(differences):
    if len(differences) != 3 or any(not np.isfinite(x) or int(x) != x or abs(x) > 3 for x in differences):
        raise ValueError('Expected three integer judge margins in [-3, 3].')
    return int(len(set(np.sign(differences))) > 1)


def seconds(value):
    if pd.isna(value) or str(value).strip() in {'', '--', '---'}:
        return np.nan
    parts = str(value).split(':')
    if len(parts) != 2 or not all(p.isdigit() for p in parts) or int(parts[1]) >= 60:
        raise ValueError('Invalid control time')
    result = int(parts[0]) * 60 + int(parts[1])
    if result > 300:
        raise ValueError('Control exceeds five-minute round')
    return result


def download():
    raw = ROOT / 'data/raw'
    raw.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, url in SOURCES.items():
        path = raw / name
        if not path.exists():
            with urlopen(url, timeout=60) as response:
                content = response.read()
            if len(content) < 1000:
                raise ValueError(f'Unexpected download for {name}')
            path.write_bytes(content)
        manifest[name] = {'url': url, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    (ROOT / 'reports').mkdir(exist_ok=True)
    (ROOT / 'reports/source_manifest.json').write_text(json.dumps(manifest, indent=2))


def grouped(frame, fields):
    result = defaultdict(list)
    for row in frame.to_dict('records'):
        result[pair(*(row[f] for f in fields))].append(row)
    return result


def build():
    download()
    raw = ROOT / 'data/raw'
    stats = grouped(pd.read_csv(raw / 'stats.csv'), ['Opponent_A', 'Opponent_B'])
    scores = grouped(pd.read_csv(raw / 'scores.csv'), ['Opponent_A', 'Opponent_B'])
    metadata = grouped(pd.read_csv(raw / 'metadata.csv'), ['red_fighter_name', 'blue_fighter_name'])
    audit = Counter()
    records = []
    for key, score_rows in scores.items():
        audit['candidate_pairs'] += 1
        if len(score_rows) != 1 or len(stats.get(key, [])) != 1 or len(metadata.get(key, [])) != 1:
            audit['excluded_ambiguous_or_missing_pair'] += 1
            continue
        score, stat, meta = score_rows[0], stats[key][0], metadata[key][0]
        try:
            n = int(stat['Number_of_Rounds'])
            if n not in {3, 5} or str(meta['method']) not in {'Decision - Unanimous', 'Decision - Split', 'Decision - Majority'}:
                raise ValueError('Not a full standard decision')
            if re.search(r'deduct|penalt', str(meta.get('details', '')), re.I):
                raise ValueError('Point deduction')
            margins = [[int(score[f'Rd{r}{judge}']) for r in range(1, n+1)] for judge in 'ABC']
            full_scores = [int(x) for x in ast.literal_eval(score['Full_Scores'])]
            if len(full_scores) != 6:
                raise ValueError('Missing full scorecards')
            rebuilt = []
            for card in margins:
                if any(abs(x) > 3 for x in card):
                    raise ValueError('Invalid score')
                rebuilt.extend([sum(10 + min(x, 0) for x in card), sum(10 - max(x, 0) for x in card)])
            if rebuilt != full_scores:
                raise ValueError('Round scores do not reconstruct totals')
            # UFCStats details do not guarantee corner order. Cross-check each
            # judge's unordered total pair; use named score rows for orientation.
            orientation = normalize(score['Opponent_A']) == normalize(stat['Opponent_A'])
            stat_totals = [tuple(int(x) for x in str(stat[f'Decision{i}']).split()) for i in range(1, 4)]
            totals = [tuple(sorted(full_scores[i:i+2])) for i in (0,2,4)]
            if sorted(totals) != sorted(tuple(sorted(t)) for t in stat_totals):
                raise ValueError('Scorecards disagree across sources')
            date = pd.to_datetime(meta['event_date'], dayfirst=True).strftime('%Y-%m-%d')
            fight_id = hashlib.sha256(('|'.join(key) + date).encode()).hexdigest()[:16]
            local = []
            for r in range(1, n+1):
                signed = [card[r-1] * (1 if orientation else -1) for card in margins]
                row = {'fight_id': fight_id, 'date': date, 'event': meta['event_name'],
                       'fighter_a': stat['Opponent_A'], 'fighter_b': stat['Opponent_B'],
                       'round': r, 'weight_class': meta['bout_type'], 'target': disagreement(signed),
                       **{f'judge_{j+1}_margin': signed[j] for j in range(3)}}
                for side in 'AB':
                    for metric, source in METRICS.items():
                        val = stat[f'Round_{r}_{source}_({side})']
                        row[f'{side.lower()}_{metric}'] = seconds(val) if metric == 'control_seconds' else float(val)
                    if not 0 <= row[f'{side.lower()}_sig_landed'] <= row[f'{side.lower()}_sig_attempted']:
                        raise ValueError('Invalid strike counts')
                    if any(row[f'{side.lower()}_{m}'] < 0 for m in METRICS):
                        raise ValueError('Negative count')
                local.append(row)
            # Check date/name metadata join using independent aggregate strike counts.
            for side, fighter in [('a', stat['Opponent_A']), ('b', stat['Opponent_B'])]:
                corner = 'red' if normalize(fighter) == normalize(meta['red_fighter_name']) else 'blue'
                aggregate = int(str(meta[f'{corner}_fighter_sig_str']).split(' of ')[0])
                if sum(x[f'{side}_sig_landed'] for x in local) != aggregate:
                    raise ValueError('Aggregate strike mismatch')
            records.extend(local)
            audit['accepted_fights'] += 1
        except (ValueError, KeyError, TypeError, SyntaxError) as exc:
            audit['excluded_' + str(exc)] += 1
    if not records:
        raise ValueError(f'No accepted data: {dict(audit)}')
    frame = pd.DataFrame(records).sort_values(['date', 'fight_id', 'round']).reset_index(drop=True)
    if frame.empty or frame.duplicated(['fight_id', 'round']).any():
        raise ValueError('Empty or duplicated dataset')
    path = ROOT / 'data/processed'
    path.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path / 'rounds.csv', index=False)
    audit.update(rounds=len(frame), disagreements=int(frame.target.sum()))
    (ROOT / 'reports/data_audit.json').write_text(json.dumps(dict(audit), indent=2))
    frame.sample(min(20, len(frame)), random_state=42).to_csv(ROOT / 'reports/audit_sample.csv', index=False)
    print(json.dumps(dict(audit), indent=2))
    return frame


if __name__ == '__main__':
    build()

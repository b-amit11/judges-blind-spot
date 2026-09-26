# Targeted scorecard spot check

On September 26, 2026, the assistant compared all 20 round labels and all 60 signed judge margins for four selected five-round fights against the published MMA Decisions tables. All matched, including the reversal into the statistics table’s fighter-A orientation. These fights were selected from notable model failures, not randomly sampled. This is a check against the scraper's underlying source, not an independent audit of commission originals or video.

| Fight | Published disagreement rounds | Dataset match | Source |
|---|---|---|---|
| Jose Aldo vs Rob Font | 3 | All five rounds matched | https://mmadecisions.com/decision/12761/Jose-Aldo-vs-Rob-Font |
| Marlon Vera vs Rob Font | 2 | All five rounds matched | https://mmadecisions.com/decision/13121/Marlon-Vera-vs-Rob-Font |
| Belal Muhammad vs Gilbert Burns | 4, 5 | All five rounds matched | https://mmadecisions.com/decision/13994/Belal-Muhammad-vs-Gilbert-Burns |
| Amir Albazi vs Kai Kara-France | 1, 4 | All five rounds matched | https://mmadecisions.com/decision/14045/Amir-Albazi-vs-Kai-Kara-France |

The source check covers score labels and orientation. All accepted fights also undergo automated aggregate-stat and full-score-total checks. Individual round statistics have not been independently checked against video. `audit_sample.csv` is a separate random 20-row worksheet, not a claim that those random rows were manually verified.

| category | count | percentage_of_holdout | mean_signed_BM25_minus_Qwen_ndcg_at_10 | total_signed_BM25_minus_Qwen_ndcg_at_10 | mean_gain_or_loss_ndcg_at_10 | total_gain_or_loss_ndcg_at_10 | interpretation | diagnostic_label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| beneficial_BM25_switches | 8 | 4.000000000 | 0.365432449 | 2.923459589 | 0.365432449 | 2.923459589 | BM25-minus-Qwen gain from a beneficial switch | POST-HOC DIAGNOSTICS - NOT SELECTION CRITERIA |
| harmful_BM25_switches | 60 | 30.000000000 | -0.093928643 | -5.635718598 | 0.093928643 | 5.635718598 | Qwen-minus-BM25 loss from an incorrect BM25 switch | POST-HOC DIAGNOSTICS - NOT SELECTION CRITERIA |
| correct_Qwen_keeps | 112 | 56.000000000 | -0.171115027 | -19.164882979 | 0.171115027 | 19.164882979 | Qwen-minus-BM25 advantage retained by the Qwen fallback | POST-HOC DIAGNOSTICS - NOT SELECTION CRITERIA |
| missed_BM25_opportunities | 20 | 10.000000000 | 0.349186915 | 6.983738298 | 0.349186915 | 6.983738298 | BM25-minus-Qwen gain left unrealized by a missed opportunity | POST-HOC DIAGNOSTICS - NOT SELECTION CRITERIA |

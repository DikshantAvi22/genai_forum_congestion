# Extra Experiment Summary

## Seed and Distribution Robustness
- In the stable regime, targeted changes S_T by 10.132 and overload_time by -1.000.
- In the mid regime, targeted changes S_T by 11.957 and overload_time by -15.000.
- In the collapse regime, targeted changes S_T by 2.869 and overload_time by 0.000.
- For beta_0.5_0.5, targeted shifts S_T by 13.450 relative to uniform.
- For beta_1_1, targeted shifts S_T by 11.957 relative to uniform.
- For beta_2_5, targeted shifts S_T by 14.358 relative to uniform.
- For beta_5_2, targeted shifts S_T by 5.375 relative to uniform.

## rho Ablation
- At rho=0, the targeted-uniform delta S_T is 0.000; this should be near zero if the novelty advantage disappears.

## Matched avg_answered Check
- At matched avg_answered=0.178, uniform reaches S_T=20.585 and targeted reaches S_T=31.349.
- The matched-answered comparison keeps adoption-adjusted throughput comparable while preserving the targeted advantage.

## Tipping Regions
- The lambda-xi sweep shows the strongest overload at lambda=0.050, xi=0.101.
- The beta-w_s sweep shows the strongest overload at beta=10.571, w_s=0.507.
- In the C1-xi collapse mask, the first collapse points appear around C1=0.364, xi=0.074 for epsilon=0.05.

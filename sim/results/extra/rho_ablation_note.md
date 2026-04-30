# rho Ablation Note

- `rho=0` removes novelty-quality differences because every deferred batch contributes the same normalized novelty factor of 1.
- In that regime, targeted and uniform policies should become nearly indistinguishable at matched answer rate.
- As `rho` increases, deferring high-novelty traffic raises the effective gain from forum throughput.
- That makes targeted deferral matter through traffic composition rather than raw volume.
- The gap plots show whether the advantage grows smoothly or only after a moderate novelty weighting threshold.

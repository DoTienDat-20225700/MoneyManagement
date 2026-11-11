# Adaptive EWMA development protocol

The supplied alpha grid (0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6 plus mean) and minimum history of 30 days were prespecified. Only the walk-forward warm-up was compared on development seeds 1000–1009. No configuration was changed using final test results.

`warmup_selection.csv` compares warm-ups 7, 14, 21 and 29. Criterion: mean absolute error of the selected daily burn rate against the known stationary Gaussian mean of 150,000 VND, using one 60-day history per development seed with Gaussian noise SD 25,000 VND. The candidate with the smallest development error is 21 days. This is a targeted stationary-behavior calibration, not evidence of general superiority on other scenarios.

Reproduce the calibration from `backend/`:

```python
# Run with: python manage.py shell
import csv
import datetime
import random
from decimal import Decimal
from pathlib import Path
import hubModels.services.forecasting as f

original_warmup = f.ADAPTIVE_WARMUP_DAYS
rows = []
try:
    for warmup in (7, 14, 21, 29):
        f.ADAPTIVE_WARMUP_DAYS = warmup
        error = reference = Decimal(0)
        for seed in range(1000, 1010):
            rng = random.Random(seed)
            start = datetime.date(2026, 1, 1)
            history = [(start + datetime.timedelta(days=i), Decimal(str(round(max(0, 150000 + rng.gauss(0, 25000)), 2)))) for i in range(60)]
            today = history[-1][0]
            adaptive = f.simulate_cashflow(Decimal(0), [], history, today, 30, estimator='ewma_adaptive')
            mean, _, _ = f.calculate_daily_burn_rate(history, today, estimator='mean', winsorize=False)
            error += abs(adaptive.daily_burn_rate - 150000)
            reference += abs(mean - 150000)
        rows.append((warmup, float(error / 10), float(reference / 10), float(error / reference)))
finally:
    f.ADAPTIVE_WARMUP_DAYS = original_warmup
print(rows)
```

After freezing the policy, full development evaluation:

```bash
python manage.py forecast_backtest --split development --output-dir evaluation_results/development
```

Final held-out evaluation, with unchanged policy:

```bash
python manage.py forecast_backtest
```

The final run uses seeds 0–29; development uses 1000–1009. Every origin selects its own alpha or mean using only past spending and fold-local winsorization. The one-step selection objective differs from the 30-day balance evaluation objective. All six scenarios and all five arms are retained, including losses. The stress shortfall cohort rebases origin balance to 1,000,000 VND and must be distinguished from the original-balance cohort.

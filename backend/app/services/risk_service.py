from dataclasses import dataclass
import logging
import math

logger = logging.getLogger(__name__)

@dataclass
class RiskParams:
    lambda0: float = 0.10
    alpha: float = 1.0
    deploy_rate_ref: float = 10.0

class RiskModel:
    def __init__(self, params: RiskParams = RiskParams()):
        self.p = params
        logger.info(f"RiskModel initialized with lambda0={params.lambda0:.3f}, alpha={params.alpha:.2f}")

    def lambda_t(self, deploy_rate_t: float) -> float:
        r = self.p.deploy_rate_ref/max(deploy_rate_t, 1e-6)
        lam = self.p.lambda0 * (r ** self.p.alpha)
        clamped_lam = max(0.03, min(0.25, lam))
        logger.debug(f"lambda_t: deploy_rate={deploy_rate_t:.2f} -> lambda={clamped_lam:.4f}")
        return clamped_lam

    def effective_risk(self, base_risk: float, days_since_change: float, deploy_rate_t: float) -> float:
        lam = self.lambda_t(deploy_rate_t)
        risk = base_risk * math.exp(-lam * days_since_change)
        logger.info(f"Effective risk: base={base_risk:.3f}, days={days_since_change:.1f}, deploy_rate={deploy_rate_t:.2f} -> risk={risk:.4f}")
        return risk

class Calibrator:
    def fit(self, rows):
        logger.info(f"Starting risk model calibration with {len(rows)} data points")

        try:
            xs=[]; ys=[]
            for dr, dsc, inc in rows:
                xs.append((1.0/max(dr,1e-3), dsc)); ys.append(inc)

            s11 = sum(a*a for a,b in xs) + 1e-3
            s22 = sum(b*b for a,b in xs) + 1e-3
            y1  = sum(y*a for (a,b),y in zip(xs,ys))
            y2  = sum(y*b for (a,b),y in zip(xs,ys))
            w1 = y1/s11; w2 = y2/s22

            lambda0 = min(0.25, max(0.03, abs(w1)))
            alpha   = max(0.1, min(3.0, abs(w2)/max(w1,1e-6)))

            logger.info(f"Calibration complete: lambda0={lambda0:.4f}, alpha={alpha:.3f}")
            return RiskParams(lambda0=lambda0, alpha=alpha, deploy_rate_ref=10.0)

        except Exception as e:
            logger.error(f"Risk calibration failed: {e}")
            logger.warning("Falling back to default RiskParams")
            return RiskParams()

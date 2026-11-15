"""SANS (Spaceflight-Associated Neuro-ocular Syndrome) placeholder predictor."""

from __future__ import annotations

from astra_med.ml.interface import MLPredictor


class SANSPredictor(MLPredictor):
    module_name = "sans"
    version = "0.1.0-placeholder"

    def predict(self, input_data: dict) -> dict:
        optic_disc = input_data.get("optic_disc_diameter", 1.5)  # mm
        rnfl = input_data.get("rnfl_thickness", 100.0)           # μm
        iop = input_data.get("iop", 15.0)                       # mmHg
        choroidal_folds = input_data.get("choroidal_folds", False)

        risk_score = 0.0
        findings: list[str] = []

        # Optic disc swelling (normal ~1.5 mm, edema > 1.8)
        if optic_disc > 2.2:
            risk_score += 0.35
            findings.append("Significant optic disc edema")
        elif optic_disc > 1.8:
            risk_score += 0.2
            findings.append("Mild optic disc swelling")

        # RNFL thickening (normal ~100 μm, thickening > 120 μm)
        if rnfl > 140:
            risk_score += 0.3
            findings.append("Marked RNFL thickening – papilledema concern")
        elif rnfl > 120:
            risk_score += 0.15
            findings.append("Mild RNFL thickening")

        # Intra-ocular pressure (normal 10-21 mmHg)
        if iop > 25:
            risk_score += 0.25
            findings.append("Elevated IOP – glaucoma risk")
        elif iop > 21:
            risk_score += 0.1
            findings.append("Borderline elevated IOP")

        # Choroidal folds
        if choroidal_folds:
            risk_score += 0.2
            findings.append("Choroidal folds present – SANS indicator")

        risk_score = min(risk_score, 1.0)

        if risk_score >= 0.5:
            risk_label = "SANS_PROBABLE"
        elif risk_score >= 0.25:
            risk_label = "SANS_POSSIBLE"
        else:
            risk_label = "SANS_UNLIKELY"

        return {
            "risk_label": risk_label,
            "confidence": 0.71,
            "risk_score": round(risk_score, 3),
            "details": {
                "findings": findings if findings else ["Neuro-ocular parameters within normal limits"],
                "optic_disc_status": "edema" if optic_disc > 1.8 else "normal",
                "rnfl_status": "thickened" if rnfl > 120 else "normal",
                "iop_status": "elevated" if iop > 21 else "normal",
                "choroidal_folds": choroidal_folds,
            },
        }

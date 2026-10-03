/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * API schema for a zone risk assessment.
 */
export type RiskAssessmentSchema = {
    /**
     * The risk tier (SAFE, LOW, MEDIUM, HIGH, DANGER).
     */
    tier: string;
    /**
     * Confidence score [0, 1] of the assessment.
     */
    probability: number;
    /**
     * Human-readable explanation of the risk.
     */
    explanation: string;
    /**
     * When this assessment was generated.
     */
    computed_at: string;
    /**
     * Combined 10-day rainfall (past 7d + forecast 72h).
     */
    combined_rain_mm?: (number | null);
    /**
     * Expected 10-day baseline rainfall.
     */
    expected_rain_mm?: (number | null);
    /**
     * Ratio of actual vs expected rainfall.
     */
    rainfall_anomaly_ratio?: (number | null);
    /**
     * Top SHAP contributing features from the ML model.
     */
    top_contributing_features?: (Array<string> | null);
};


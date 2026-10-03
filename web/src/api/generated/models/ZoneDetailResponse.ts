/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { RiskAssessmentSchema } from './RiskAssessmentSchema';
import type { SensorReadingSchema } from './SensorReadingSchema';
import type { WeatherSnapshotSchema } from './WeatherSnapshotSchema';
import type { ZoneListResponse } from './ZoneListResponse';
/**
 * Zone detail response schema.
 */
export type ZoneDetailResponse = {
    zone: ZoneListResponse;
    recent_readings: Array<SensorReadingSchema>;
    risk_history: Array<RiskAssessmentSchema>;
    recent_rainfall?: (WeatherSnapshotSchema | null);
    latest_sensor_reading?: (SensorReadingSchema | null);
    is_manual_override?: boolean;
};


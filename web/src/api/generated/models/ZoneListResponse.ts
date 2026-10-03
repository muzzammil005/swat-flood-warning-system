/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CoordinatesSchema } from './CoordinatesSchema';
import type { RiskAssessmentSchema } from './RiskAssessmentSchema';
import type { ZoneThresholdsSchema } from './ZoneThresholdsSchema';
/**
 * Zone list item response schema.
 */
export type ZoneListResponse = {
    id: string;
    name: string;
    coordinates: CoordinatesSchema;
    upstream_zone_id?: (string | null);
    latest_assessment?: (RiskAssessmentSchema | null);
    thresholds?: (ZoneThresholdsSchema | null);
    sensor_health?: (string | null);
    is_manual_override?: boolean;
};


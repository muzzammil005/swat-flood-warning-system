/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WaterLevelSchema } from './WaterLevelSchema';
/**
 * Zone thresholds schema for HTTP response.
 */
export type ZoneThresholdsSchema = {
    water_warning_level: WaterLevelSchema;
    water_critical_level: WaterLevelSchema;
    heavy_rain_threshold_mm: number;
};


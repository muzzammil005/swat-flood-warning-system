/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WaterLevelSchema } from './WaterLevelSchema';
/**
 * Sensor reading schema for HTTP response.
 */
export type SensorReadingSchema = {
    id: string;
    zone_id: string;
    water_level: WaterLevelSchema;
    source: string;
    timestamp: string;
};


/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { RainfallWindowSchema } from './RainfallWindowSchema';
/**
 * Weather snapshot schema for HTTP response.
 */
export type WeatherSnapshotSchema = {
    zone_id: string;
    rainfall: RainfallWindowSchema;
    fetched_at: string;
    ttl_seconds: number;
};


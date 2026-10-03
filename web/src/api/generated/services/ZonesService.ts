/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ZoneDetailResponse } from '../models/ZoneDetailResponse';
import type { ZoneListResponse } from '../models/ZoneListResponse';
import type { ZoneSummaryResponse } from '../models/ZoneSummaryResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ZonesService {
    /**
     * Get Zone Summary
     * Get a high-level summary of all zones and their current risk tiers.
     * @returns ZoneSummaryResponse Successful Response
     * @throws ApiError
     */
    public static getZoneSummaryApiZonesSummaryGet(): CancelablePromise<ZoneSummaryResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/zones/summary',
        });
    }
    /**
     * Get Zones
     * Get all zones with their most recent risk assessment, thresholds, and sensor health.
     * Zones with active manual overrides will show the override's threat_level instead of computed tier.
     * @returns ZoneListResponse Successful Response
     * @throws ApiError
     */
    public static getZonesApiZonesGet(): CancelablePromise<Array<ZoneListResponse>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/zones/',
        });
    }
    /**
     * Get Zones
     * Get all zones with their most recent risk assessment, thresholds, and sensor health.
     * Zones with active manual overrides will show the override's threat_level instead of computed tier.
     * @returns ZoneListResponse Successful Response
     * @throws ApiError
     */
    public static getZonesApiZonesGet1(): CancelablePromise<Array<ZoneListResponse>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/zones',
        });
    }
    /**
     * Get Nearest Zone
     * Find the nearest zone to given coordinates using PostGIS.
     *
     * Used for mobile geolocation.
     *
     * TODO: Move to use-cases layer, add proper error handling.
     * @param lat
     * @param lon
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getNearestZoneApiZonesNearestGet(
        lat: number,
        lon: number,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/zones/nearest',
            query: {
                'lat': lat,
                'lon': lon,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Zone
     * Get detailed information for a specific zone.
     * @param zoneId
     * @returns ZoneDetailResponse Successful Response
     * @throws ApiError
     */
    public static getZoneApiZonesZoneIdGet(
        zoneId: string,
    ): CancelablePromise<ZoneDetailResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/zones/{zone_id}',
            path: {
                'zone_id': zoneId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Zone Risk Trend
     * Get time-ordered list of risk assessments within the requested window.
     *
     * Used for dashboard's risk-trend chart.
     *
     * TODO: Move to use-cases layer, add proper error handling.
     * @param zoneId
     * @param window
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getZoneRiskTrendApiZonesZoneIdRiskTrendGet(
        zoneId: string,
        window: string = '24h',
    ): CancelablePromise<Array<Record<string, any>>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/zones/{zone_id}/risk-trend',
            path: {
                'zone_id': zoneId,
            },
            query: {
                'window': window,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Zone Rainfall Vs Risk
     * Get paired time-ordered list of rainfall and risk data within the requested window.
     *
     * Used for dashboard's rainfall-vs-risk chart.
     *
     * TODO: Move to use-cases layer, add proper error handling.
     * @param zoneId
     * @param window
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getZoneRainfallVsRiskApiZonesZoneIdRainfallVsRiskGet(
        zoneId: string,
        window: string = '24h',
    ): CancelablePromise<Array<Record<string, any>>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/zones/{zone_id}/rainfall-vs-risk',
            path: {
                'zone_id': zoneId,
            },
            query: {
                'window': window,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}

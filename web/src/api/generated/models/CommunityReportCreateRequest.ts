/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for submitting a community report.
 */
export type CommunityReportCreateRequest = {
    /**
     * Type of report: flooding, blocked_drain, high_river_level, etc.
     */
    report_type: string;
    /**
     * Detailed description of the issue
     */
    description: string;
    /**
     * Optional reporter name
     */
    reporter_name?: (string | null);
    /**
     * Optional reporter phone number
     */
    reporter_phone?: (string | null);
    /**
     * Zone ID (if known)
     */
    zone_id?: (string | null);
    /**
     * Latitude coordinate (if zone_id not provided)
     */
    latitude?: (number | null);
    /**
     * Longitude coordinate (if zone_id not provided)
     */
    longitude?: (number | null);
};


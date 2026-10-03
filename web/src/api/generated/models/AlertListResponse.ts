/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Alert list item response schema.
 */
export type AlertListResponse = {
    id?: (string | null);
    zone_id: string;
    severity: string;
    certainty: string;
    urgency: string;
    headline: string;
    description: string;
    sent_at: string;
};


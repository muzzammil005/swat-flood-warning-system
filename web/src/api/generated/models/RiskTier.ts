/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Ordered flood-risk tiers used by every downstream consumer.
 *
 * IntEnum gives us a natural ordering (``RiskTier.HIGH > RiskTier.MEDIUM``)
 * *and* lets us serialise the value as a plain integer for storage/API
 * purposes without writing a custom codec. The ordering itself encodes the
 * single-hop escalation semantics used by :class:`EscalationEngine`:
 * incrementing by one level moves to the next tier, and ``DANGER`` is the
 * hard cap.
 */
export enum RiskTier {
    '_1' = 1,
    '_2' = 2,
    '_3' = 3,
    '_4' = 4,
}

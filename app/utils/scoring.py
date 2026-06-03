from dataclasses import dataclass

from app.schemas.common import AvailabilityStatus, CoverageType
from app.services.dtos import AvailabilitySnapshot


@dataclass(frozen=True)
class CandidateScore:
    availability_quality: float
    confirmation_probability: float
    route_mismatch_score: float
    usefulness_score: float
    reason_codes: tuple[str, ...]


def availability_quality(availability: AvailabilitySnapshot) -> float:
    if availability.status == AvailabilityStatus.AVAILABLE:
        seats = availability.available_count or 1
        return min(1.0, 0.78 + seats / 100)
    if availability.status == AvailabilityStatus.RAC:
        rac = availability.rac_count or 1
        return min(0.74, 0.48 + rac / 80)
    if availability.status == AvailabilityStatus.WAITLIST:
        waitlist = availability.waitlist_count or 200
        return max(0.05, 0.42 - waitlist / 300)
    if availability.status == AvailabilityStatus.NOT_AVAILABLE:
        return 0.02
    return 0.1


def estimate_confirmation_probability(availability: AvailabilitySnapshot) -> float:
    if availability.status == AvailabilityStatus.AVAILABLE:
        seats = availability.available_count or 1
        return min(0.99, 0.86 + seats / 150)
    if availability.status == AvailabilityStatus.RAC:
        rac = availability.rac_count or 1
        return min(0.78, 0.52 + rac / 100)
    if availability.status == AvailabilityStatus.WAITLIST:
        waitlist = availability.waitlist_count or 200
        return max(0.03, 0.36 - waitlist / 350)
    if availability.status == AvailabilityStatus.NOT_AVAILABLE:
        return 0.01
    return 0.1


def classify_coverage(
    candidate_source_index: int,
    candidate_destination_index: int,
    requested_source_index: int,
    requested_destination_index: int,
) -> CoverageType:
    starts_at_or_before = candidate_source_index <= requested_source_index
    ends_at_or_after = candidate_destination_index >= requested_destination_index
    if starts_at_or_before and ends_at_or_after:
        if (
            candidate_source_index == requested_source_index
            and candidate_destination_index == requested_destination_index
        ):
            return CoverageType.FULL_COVERAGE
        return CoverageType.EXTENDED_COVERAGE
    if candidate_source_index == requested_source_index:
        return CoverageType.SAME_BOARDING_PARTIAL
    if candidate_destination_index == requested_destination_index:
        return CoverageType.LATER_BOARDING_TO_DESTINATION
    return CoverageType.INTERMEDIATE_SEGMENT


def score_candidate(
    candidate_availability: AvailabilitySnapshot,
    direct_availability: AvailabilitySnapshot,
    overlap_ratio: float,
    candidate_source_index: int,
    candidate_destination_index: int,
    requested_source_index: int,
    requested_destination_index: int,
) -> CandidateScore:
    requested_span = max(1, requested_destination_index - requested_source_index)
    source_shift = abs(candidate_source_index - requested_source_index)
    destination_shift = abs(candidate_destination_index - requested_destination_index)
    mismatch = (source_shift + destination_shift) / (requested_span + 2)
    mismatch = min(1.0, mismatch)

    quality = availability_quality(candidate_availability)
    direct_quality = availability_quality(direct_availability)
    confirmation = estimate_confirmation_probability(candidate_availability)
    boundary_fit = 1 - mismatch
    improvement = quality - direct_quality

    score = (
        quality * 0.38
        + confirmation * 0.24
        + overlap_ratio * 0.22
        + boundary_fit * 0.16
    )

    if improvement < 0.05:
        score -= 0.12
    if candidate_source_index > requested_source_index:
        score -= min(0.12, source_shift * 0.035)
    if candidate_destination_index < requested_destination_index:
        score -= min(0.12, destination_shift * 0.035)

    reason_codes: list[str] = []
    if candidate_availability.status == AvailabilityStatus.AVAILABLE:
        reason_codes.append("CONFIRMED_SEATS")
    elif candidate_availability.status == AvailabilityStatus.RAC:
        reason_codes.append("RAC_BETTER_THAN_DIRECT")
    elif candidate_availability.status == AvailabilityStatus.WAITLIST:
        reason_codes.append("LOWER_WAITLIST")

    if improvement > 0.25:
        reason_codes.append("SIGNIFICANTLY_BETTER_THAN_DIRECT")
    if overlap_ratio >= 0.8:
        reason_codes.append("HIGH_ROUTE_OVERLAP")
    if candidate_source_index == requested_source_index:
        reason_codes.append("SAME_BOARDING_STATION")
    if candidate_destination_index == requested_destination_index:
        reason_codes.append("SAME_DESTINATION")

    return CandidateScore(
        availability_quality=round(quality, 4),
        confirmation_probability=round(confirmation, 4),
        route_mismatch_score=round(mismatch, 4),
        usefulness_score=round(max(0.0, min(1.0, score)), 4),
        reason_codes=tuple(reason_codes),
    )


export type TravelClass = "SL" | "3AC" | "2AC" | "1AC" | "CC" | "EC";

export type AvailabilityStatus = "AVAILABLE" | "RAC" | "WAITLIST" | "NOT_AVAILABLE" | "UNKNOWN";

export type CoverageType =
  | "FULL_COVERAGE"
  | "EXTENDED_COVERAGE"
  | "SAME_BOARDING_PARTIAL"
  | "LATER_BOARDING_TO_DESTINATION"
  | "INTERMEDIATE_SEGMENT";

export interface TrainSearchRequest {
  source_station: string;
  destination_station: string;
  travel_date: string;
  travel_class: TravelClass;
  max_results: number;
  include_explanations: boolean;
}

export interface RouteStop {
  code: string;
  name: string;
  sequence: number;
  distance_km: number;
  arrival?: string | null;
  departure?: string | null;
}

export interface Train {
  number: string;
  name: string;
  origin_station_code: string;
  destination_station_code: string;
}

export interface Availability {
  status: AvailabilityStatus;
  available_count?: number | null;
  rac_count?: number | null;
  waitlist_count?: number | null;
  source_station_code: string;
  destination_station_code: string;
  checked_at: string;
  provider: string;
}

export interface SegmentOpportunity {
  train_number: string;
  source: RouteStop;
  destination: RouteStop;
  availability: Availability;
  coverage_type: CoverageType;
  overlap_ratio: number;
  route_mismatch_score: number;
  confirmation_probability: number;
  usefulness_score: number;
  distance_km: number;
  reason_codes: string[];
}

export interface Recommendation {
  rank: number;
  train_number: string;
  title: string;
  score: number;
  confidence: number;
  segment: SegmentOpportunity;
  explanation: string;
}

export interface TrainSearchResult {
  train: Train;
  route: RouteStop[];
  direct_availability: Availability;
  hidden_segments: SegmentOpportunity[];
  recommendations: Recommendation[];
  pairs_considered: number;
  explanation?: string | null;
}

export interface TrainSearchResponse {
  query_id: string;
  generated_at: string;
  query: TrainSearchRequest;
  results: TrainSearchResult[];
  safety_notice: string;
}

export interface SearchTelemetry {
  latencyMs: number;
  requestUrl: string;
  requestStartedAt: string;
  requestCompletedAt: string;
}

export interface SearchState {
  response: TrainSearchResponse | null;
  telemetry: SearchTelemetry | null;
}


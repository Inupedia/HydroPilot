export type ObjectType = 'river_reach' | 'reservoir' | 'dam' | 'gauge' | 'control_point'
export interface Geometry { type: 'Point' | 'LineString' | 'Polygon'; coordinates: unknown }
export interface HydroObject { id: string; name: string; object_type: ObjectType; geometry: Geometry; properties: Record<string, unknown> }
export interface NetworkPathItem { object_id: string; hop: number; via_relation: string }
export interface HydroState { scenario_id: string; object_id: string; timestamp_minutes: number; variable: string; value: number; unit: string }

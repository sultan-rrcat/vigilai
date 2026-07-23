export type Incident = {
    id: string;
    camera_id: string;
    track_id: string;
    object_class: string;
    trigger_type: string;
    zone_id?: string;
    confidence: number;
    status: 'active' | 'acknowledged' | 'escalated' | 'resolved';
    created_at: string;
    snapshot_path?: string;
}

export type Camera = {
    id: string;
    name: string;
    location: string;
    status: 'online' | 'offline';
    last_heartbeat?: string;
}
import type { Incident } from '../types';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { config } from '../config/index';
import { AlertTriangle, Clock, Camera, CheckCircle2, ImageOff } from 'lucide-react';

const API_URL = config.apiUrl;

interface IncidentGridProps {
  incidents: Incident[];
  onAcknowledge: (id: string) => void;
}

function formatDetectedTime(createdAt: string | undefined | null): string {
  if (!createdAt) return '—';
  const date = new Date(createdAt);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleTimeString();
}

const STATUS_STYLES: Record<string, { dot: string; badge: string }> = {
  escalated: {
    dot: 'bg-orange-500',
    badge: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  },
  active: {
    dot: 'bg-red-500',
    badge: 'bg-red-500/10 text-red-400 border-red-500/20',
  },
  acknowledged: {
    dot: 'bg-zinc-500',
    badge: 'bg-zinc-800 text-zinc-400 border-zinc-700',
  },
};

export function IncidentGrid({ incidents, onAcknowledge }: IncidentGridProps) {
  if (incidents.length === 0) {
    return (
      <div className="flex flex-col h-[360px] items-center justify-center text-center px-8 rounded-lg border border-dashed border-zinc-800">
        <CheckCircle2 className="w-7 h-7 text-emerald-500/70 mb-3" strokeWidth={1.75} />
        <h3 className="text-sm font-medium text-zinc-200">All clear</h3>
        <p className="text-xs text-zinc-500 mt-1">No active incidents across any zone.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-3">
      {incidents.map((incident) => {
        const style = STATUS_STYLES[incident.status] ?? STATUS_STYLES.acknowledged;

        return (
          <Card
            key={incident.id}
            className="flex flex-col overflow-hidden bg-zinc-900/40 border border-zinc-800 hover:border-zinc-700 transition-colors shadow-none py-0 gap-0"
          >
            <CardHeader className="p-3 pb-2.5 flex flex-row items-start justify-between space-y-0 gap-2">
              <div className="flex flex-col gap-1 min-w-0">
                <CardTitle className="text-[13px] font-medium text-zinc-100 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-zinc-500 shrink-0" strokeWidth={2} />
                  <span className="truncate">Intrusion detected</span>
                </CardTitle>
                <div className="flex items-center gap-1.5 text-[11px] text-zinc-500">
                  <Camera className="w-3 h-3 shrink-0" />
                  <span className="truncate">{incident.camera_id}</span>
                  <span className="text-zinc-700">·</span>
                  <span className="font-mono truncate">{incident.track_id}</span>
                </div>
              </div>
              <Badge
                variant="outline"
                className={`shrink-0 text-[10px] font-medium capitalize px-1.5 py-0 h-5 ${style.badge}`}
              >
                <span className={`h-1.5 w-1.5 rounded-full mr-1 ${style.dot}`} />
                {incident.status}
              </Badge>
            </CardHeader>

            <CardContent className="px-3 pb-3 flex-1 flex flex-col gap-2.5">
              <div className="aspect-video bg-zinc-950 rounded-md overflow-hidden border border-zinc-800 flex items-center justify-center">
                {incident.snapshot_path ? (
                  <img
                    src={`${API_URL}/${incident.snapshot_path}`}
                    alt="Incident snapshot"
                    className="object-cover w-full h-full"
                  />
                ) : (
                  <div className="flex flex-col items-center gap-1.5 text-zinc-700">
                    <ImageOff className="w-5 h-5" strokeWidth={1.75} />
                    <span className="text-[10px] uppercase tracking-wide">No image</span>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-2 px-2.5 py-2 bg-zinc-950/60 rounded-md border border-zinc-800/80">
                <div className="flex flex-col gap-0.5">
                  <span className="text-[10px] text-zinc-600">Trigger</span>
                  <span className="text-[11px] text-zinc-300 capitalize truncate">
                    {incident.trigger_type.replace('_', ' ')}
                  </span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-[10px] text-zinc-600">Detected</span>
                  <div className="flex items-center gap-1 text-[11px] text-zinc-300 font-mono">
                    <Clock className="w-3 h-3 text-zinc-600 shrink-0" />
                    {formatDetectedTime(incident.created_at)}
                  </div>
                </div>
              </div>
            </CardContent>

            <CardFooter className="p-3 pt-0">
              <Button
                size="sm"
                variant={incident.status === 'acknowledged' ? 'secondary' : 'default'}
                className={`w-full h-7 text-xs ${
                  incident.status === 'acknowledged'
                    ? 'bg-zinc-800 text-zinc-500 hover:bg-zinc-800'
                    : 'bg-indigo-600 hover:bg-indigo-500 text-white'
                }`}
                onClick={() => onAcknowledge(incident.id)}
                disabled={incident.status === 'acknowledged'}
              >
                {incident.status === 'acknowledged' ? (
                  <>
                    <CheckCircle2 className="w-3 h-3 mr-1.5" />
                    Acknowledged
                  </>
                ) : (
                  'Acknowledge'
                )}
              </Button>
            </CardFooter>
          </Card>
        );
      })}
    </div>
  );
}
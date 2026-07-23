import { useState, useEffect } from 'react';
import { IncidentGrid } from '../components/IncidentGrid';
import type { Incident } from '../types';
import { api } from '../lib/api';
import { useWebSocket } from '../hooks/useWebSocket';
import { config } from '../config/index';
import { ShieldAlert, AlertCircle, CheckCircle2 } from 'lucide-react';

const WS_URL = config.wsUrl;

type Notification = { type: 'success' | 'error'; text: string; description?: string };

export function DashboardPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [notification, setNotification] = useState<Notification | null>(null);
  const { lastMessage } = useWebSocket(WS_URL);

  const notify = (type: 'success' | 'error', text: string, description?: string) => {
    setNotification({ type, text, description });
    setTimeout(() => setNotification(null), 4000);
  };

  // 1. Initial Load: Fetch existing active incidents via REST API
  useEffect(() => {
    api.getIncidents('active, escalated')
      .then(setIncidents)
      .catch((err) => {
        console.error('Failed to fetch incidents:', err);
        notify('error', 'Could not load incidents.');
      });
  }, []);

  // 2. Real-time Updates: Listen for WebSocket broadcasts
  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.type === 'new_incident') {
      const newIncident = lastMessage.data as Incident;

      setIncidents((current) => {
        const exists = current.some((i) => i.id === newIncident.id);
        if (exists) return current;
        return [newIncident, ...current];
      });

      notify(
        'error',
        `${newIncident.object_class} detected`,
        `New intrusion in ${newIncident.camera_id} · track ${newIncident.track_id}`
      );
    }

    if (lastMessage.type === 'incident_update') {
      // The server may send a partial payload (e.g. just the fields that
      // changed on escalation), so merge onto the existing record rather
      // than replacing it wholesale — otherwise fields the update omits
      // (like created_at) get wiped out and render as "Invalid Date".
      const updatedIncident = lastMessage.data as Partial<Incident> & Pick<Incident, 'id'>;

      setIncidents((current) => {
        const index = current.findIndex((i) => i.id === updatedIncident.id);
        if (index === -1) return [updatedIncident as Incident, ...current];
        return current.map((inc) =>
          inc.id === updatedIncident.id ? { ...inc, ...updatedIncident } : inc
        );
      });
    }
  }, [lastMessage]);

  const handleAcknowledge = async (id: string) => {
    // Optimistic update
    const previous = incidents;
    setIncidents((current) =>
      current.map((inc) => (inc.id === id ? { ...inc, status: 'acknowledged' } : inc))
    );

    try {
      await api.acknowledgeIncident(id);
    } catch (error) {
      console.error('Failed to acknowledge incident:', error);
      setIncidents(previous);
      notify('error', 'Could not acknowledge the incident.', 'Please try again.');
    }
  };

  const activeIncidents = incidents.filter((inc) => inc.status !== 'resolved');

  return (
    <div className="h-full flex flex-col gap-5 relative">
      {/* --- Toast Notification --- */}
      {notification && (
        <div
          className={`fixed bottom-16 right-6 z-50 flex items-start gap-3 px-4 py-3 rounded-xl shadow-2xl backdrop-blur-md border animate-in slide-in-from-bottom-5 fade-in duration-300 max-w-sm ${
            notification.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
              : 'bg-red-500/10 border-red-500/20 text-red-400'
          }`}
        >
          {notification.type === 'success' ? (
            <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />
          ) : (
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          )}
          <div className="flex flex-col gap-0.5">
            <span className="text-sm font-medium tracking-wide">{notification.text}</span>
            {notification.description && (
              <span className="text-xs opacity-80">{notification.description}</span>
            )}
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-zinc-500" strokeWidth={2} />
            Active incidents
          </h1>
          <p className="text-xs text-zinc-500 mt-0.5">Real-time monitoring across all zones.</p>
        </div>
        {activeIncidents.length > 0 && (
          <span className="text-xs font-medium text-zinc-500 bg-zinc-900 border border-zinc-800 rounded-full px-2.5 py-1">
            {activeIncidents.length} open
          </span>
        )}
      </div>

      <div className="flex-1 overflow-auto">
        <IncidentGrid incidents={activeIncidents} onAcknowledge={handleAcknowledge} />
      </div>
    </div>
  );
}
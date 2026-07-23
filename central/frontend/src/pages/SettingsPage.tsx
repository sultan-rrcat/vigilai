// src/pages/SettingsPage.tsx
import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { api } from '../lib/api';
import { Settings, ShieldAlert, Database, Webhook, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';

type Notification = { type: 'success' | 'error'; text: string };

export function SettingsPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [isFetching, setIsFetching] = useState(true);
  const [notification, setNotification] = useState<Notification | null>(null);

  // Form State
  const [escalationTimeout, setEscalationTimeout] = useState<number>(15);
  const [webhookUrl, setWebhookUrl] = useState<string>('');
  const [retentionDays, setRetentionDays] = useState<number>(30);

  const notify = (type: 'success' | 'error', text: string) => {
    setNotification({ type, text });
    setTimeout(() => setNotification(null), 4000);
  };

  useEffect(() => {
    api
      .getSettings()
      .then((data) => {
        setEscalationTimeout(data.escalation_timeout_sec);
        setWebhookUrl(data.webhook_url || '');
        setRetentionDays(data.retention_days);
      })
      .catch((err) => {
        console.error('Failed to fetch settings:', err);
        notify('error', 'Failed to load system settings.');
      })
      .finally(() => setIsFetching(false));
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await api.updateSettings({
        escalation_timeout_sec: escalationTimeout,
        webhook_url: webhookUrl.trim() === '' ? null : webhookUrl,
        retention_days: retentionDays,
      });

      notify('success', 'Settings saved.');
    } catch (err) {
      console.error('Failed to save settings:', err);
      notify('error', 'Could not save settings.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 relative">
      {/* --- Toast Notification --- */}
      {notification && (
        <div
          className={`fixed bottom-16 right-6 z-50 flex items-start gap-3 px-4 py-3 rounded-xl shadow-2xl backdrop-blur-md border animate-in slide-in-from-bottom-5 fade-in duration-300 ${
            notification.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
              : 'bg-red-500/10 border-red-500/20 text-red-400'
          }`}
        >
          {notification.type === 'success' ? (
            <CheckCircle2 className="h-4 w-4 mt-0.5" />
          ) : (
            <AlertCircle className="h-4 w-4 mt-0.5" />
          )}
          <span className="text-sm font-medium tracking-wide">{notification.text}</span>
        </div>
      )}

      <div>
        <h1 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
          <Settings className="w-4 h-4 text-zinc-500" strokeWidth={2} />
          System settings
        </h1>
        <p className="text-xs text-zinc-500 mt-0.5">Configure global platform behavior and integrations.</p>
      </div>

      <form onSubmit={handleSave} className="space-y-5" aria-busy={isFetching}>
        {/* Core Behavior Settings */}
        <Card className="bg-zinc-900/40 border border-zinc-800 shadow-none gap-0 py-0">
          <CardHeader className="px-5 pt-4 pb-3 gap-1">
            <CardTitle className="text-[13px] font-medium text-zinc-100 flex items-center gap-2">
              <ShieldAlert className="w-3.5 h-3.5 text-zinc-500" />
              Incident management
            </CardTitle>
            <CardDescription className="text-xs text-zinc-500">
              Control how incidents are escalated and retained.
            </CardDescription>
          </CardHeader>
          <CardContent className="px-5 pb-5 space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="escalation" className="text-xs text-zinc-400">
                Escalation timeout (seconds)
              </Label>
              <Input
                id="escalation"
                type="number"
                min="5"
                max="300"
                value={escalationTimeout}
                onChange={(e) => setEscalationTimeout(parseInt(e.target.value) || 15)}
                className="h-8 text-white bg-zinc-950 border-zinc-800 text-sm focus-visible:ring-1 focus-visible:ring-indigo-500/50 focus-visible:border-indigo-500/50"
              />
              <p className="text-[11px] text-zinc-600">
                Time before an unacknowledged incident is marked escalated and notifications fire.
              </p>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="retention" className="text-xs text-zinc-400 flex items-center gap-1.5">
                <Database className="w-3 h-3" />
                Data retention (days)
              </Label>
              <Input
                id="retention"
                type="number"
                min="1"
                max="365"
                value={retentionDays}
                onChange={(e) => setRetentionDays(parseInt(e.target.value) || 30)}
                className="h-8 text-white bg-zinc-950 border-zinc-800 text-sm focus-visible:ring-1 focus-visible:ring-indigo-500/50 focus-visible:border-indigo-500/50"
              />
              <p className="text-[11px] text-zinc-600">
                Number of days to keep resolved incidents and snapshots before deletion.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Integration Settings */}
        <Card className="bg-zinc-900/40 border border-zinc-800 shadow-none gap-0 py-0">
          <CardHeader className="px-5 pt-4 pb-3 gap-1">
            <CardTitle className="text-[13px] font-medium text-zinc-100 flex items-center gap-2">
              <Webhook className="w-3.5 h-3.5 text-zinc-500" />
              External integrations
            </CardTitle>
            <CardDescription className="text-xs text-zinc-500">
              Connect the platform to third-party services.
            </CardDescription>
          </CardHeader>
          <CardContent className="px-5 pb-5">
            <div className="space-y-1.5">
              <Label htmlFor="webhook" className="text-xs text-zinc-400">
                Emergency webhook URL
              </Label>
              <Input
                id="webhook"
                type="url"
                placeholder="https://hooks.slack.com/services/..."
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                className="h-8 text-white bg-zinc-950 border-zinc-800 text-sm placeholder:text-zinc-700 focus-visible:ring-1 focus-visible:ring-indigo-500/50 focus-visible:border-indigo-500/50"
              />
              <p className="text-[11px] text-zinc-600">
                A JSON payload with incident metadata is POSTed here when an alarm escalates.
              </p>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button
            type="submit"
            disabled={isLoading || isFetching}
            size="sm"
            className="h-8 px-4 text-xs bg-indigo-600 hover:bg-indigo-500 text-white"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                Saving…
              </>
            ) : (
              'Save changes'
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
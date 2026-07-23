// src/pages/CamerasPage.tsx
import { useState, useEffect } from 'react';
import { ZoneEditor } from '../components/ZoneEditor';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { api } from '../lib/api';
import type { Camera } from '../types';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { useWebSocket } from '../hooks/useWebSocket';
import { config } from '../config';
import { Plus, Settings2, Trash2, Video, MapPin, AlertCircle, CheckCircle2 } from 'lucide-react';


import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from '../components/ui/dialog';

type Notification = { type: 'success' | 'error'; text: string };

export function CamerasPage() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedCamera, setSelectedCamera] = useState<Camera | null>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isAddingCamera, setIsAddingCamera] = useState(false);
  const [notification, setNotification] = useState<Notification | null>(null);


  // Form State
  const [newCamName, setNewCamName] = useState('');
  const [newCamLocation, setNewCamLocation] = useState('');
  const [newCamRtsp, setNewCamRtsp] = useState('');


  // Confirmation modal state (replaces window.confirm)
  const [cameraToDelete, setCameraToDelete] = useState<Camera | null>(null);
  const [isDeletingCamera, setIsDeletingCamera] = useState(false);
  const [isClearZonesModalOpen, setIsClearZonesModalOpen] = useState(false);
  const [isClearingZones, setIsClearingZones] = useState(false);


  const { lastMessage } = useWebSocket(config.wsUrl);
  const [cameraZones, setCameraZones] = useState([]);

  const notify = (type: 'success' | 'error', text: string) => {
    setNotification({ type, text });
    setTimeout(() => setNotification(null), 4000);
  };


  const handleEditCamera = async (cam: Camera) => {
    setSelectedCamera(cam);
    try {
      const zones = await api.getZones(cam.id);
      setCameraZones(zones);
    } catch (error) {
      console.error('Failed to load existing zones', error);
      notify('error', 'Could not load saved zones.');
    }
  };


  const fetchCameras = () => {
    api.getCameras().then(setCameras).catch((err) => {
      console.error('Failed to fetch cameras:', err);
      notify('error', 'Could not load cameras.');
    });
  };


  useEffect(() => {
    fetchCameras();
  }, []);


  useEffect(() => {
    if (!lastMessage) return;


    if (lastMessage.type === 'camera_update') {
      const { id, status } = lastMessage.data;


      setCameras((current) =>
        current.map((cam) => (cam.id === id ? { ...cam, status } : cam))
      );


      if (status === 'offline') {
        notify('error', 'Camera went offline');
      }
    }
  }, [lastMessage]);


  const handleSaveZone = async (polygon: number[][]) => {
    if (!selectedCamera) return;


    try {
      await api.createZone(selectedCamera.id, 'Custom Zone', polygon, 2.0);
      notify('success', 'Zone saved.');
      setSelectedCamera(null);
    } catch (error) {
      console.error('Failed to save zone:', error);
      notify('error', 'Failed to save zone geometry.');
    }
  };


  const handleClearAllZones = () => {
    if (!selectedCamera) return;
    setIsClearZonesModalOpen(true);
  };


  const confirmClearAllZones = async () => {
    if (!selectedCamera) return;


    setIsClearingZones(true);
    try {
      await api.deleteAllZones(selectedCamera.id);
      setCameraZones([]);
      notify('success', 'All zones deleted.');
      setIsClearZonesModalOpen(false);
    } catch (error) {
      console.error('Failed to delete zones:', error);
      notify('error', 'Could not delete zones.');
    } finally {
      setIsClearingZones(false);
    }
  };


  const handleAddCamera = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsAddingCamera(true);
    try {
      await api.addCamera({
        name: newCamName,
        location: newCamLocation,
        rtsp_url: newCamRtsp,
      });


      notify('success', `${newCamName} registered.`);


      setNewCamName('');
      setNewCamLocation('');
      setNewCamRtsp('');
      setIsAddModalOpen(false);


      fetchCameras();
    } catch (error) {
      console.error('Failed to add camera:', error);
      notify('error', 'Could not add camera.');
    } finally {
      setIsAddingCamera(false);
    }
  };


  const confirmDeleteCamera = async () => {
    if (!cameraToDelete) return;


    setIsDeletingCamera(true);
    try {
      await api.deleteCamera(cameraToDelete.id);
      notify('success', `${cameraToDelete.name} removed.`);
      setCameraToDelete(null);
      fetchCameras();
    } catch (error) {
      console.error('Failed to delete camera:', error);
      notify('error', 'Could not delete camera.');
    } finally {
      setIsDeletingCamera(false);
    }
  };


  // Render the Zone Editor
  if (selectedCamera) {
    return (
      <div className="h-[760px] max-w-5xl mx-auto flex flex-col gap-4 relative">
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
        <div className="flex items-center justify-between pb-3 border-b border-zinc-900">
          <div>
            <h1 className="text-[15px] font-medium text-zinc-100 flex items-center gap-2">
              <Settings2 className="w-4 h-4 text-zinc-500" strokeWidth={2} />
              Configuring: {selectedCamera.name}
            </h1>
            <p className="text-xs text-zinc-500 mt-0.5">Draw a polygon to define the detection zone.</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSelectedCamera(null)}
            className="h-7 px-3 text-xs bg-transparent border-zinc-800 text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100"
          >
            Close
          </Button>
        </div>
        <div className="rounded-lg overflow-hidden border border-zinc-800">
          <ZoneEditor
            referenceImageUrl={`${config.apiUrl}/camera_references/${selectedCamera.id}.jpg?t=${Date.now()}`}
            existingZones={cameraZones}
            onSave={handleSaveZone}
            onCancel={() => setSelectedCamera(null)}
            onClearAll={handleClearAllZones}
          />
        </div>


        <ConfirmDialog
          open={isClearZonesModalOpen}
          onOpenChange={setIsClearZonesModalOpen}
          title="Delete all zones?"
          description={`This removes every saved zone for ${selectedCamera.name}. The edge node syncs this change immediately, and it can't be undone.`}
          confirmLabel="Delete all"
          variant="destructive"
          isLoading={isClearingZones}
          onConfirm={confirmClearAllZones}
        />
      </div>
    );
  }


  // Render the Main Cameras Grid
  return (
    <div className="space-y-6 relative">
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

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold text-zinc-100">Cameras</h1>
          <p className="text-xs text-zinc-500 mt-0.5">Manage edge devices and detection zones.</p>
        </div>


        <Dialog open={isAddModalOpen} onOpenChange={setIsAddModalOpen}>
          <DialogTrigger render={<Button size="sm" className="h-8 px-3 text-xs bg-indigo-600 hover:bg-indigo-500 text-white"></Button>
          }>
              <Plus className="w-3.5 h-3.5 mr-1.5" />
              Add camera
          </DialogTrigger>
          <DialogContent className="bg-zinc-950 border border-zinc-800 text-zinc-100 sm:max-w-[420px]">
            <DialogHeader>
              <DialogTitle className="text-sm font-medium">Register camera</DialogTitle>
              <DialogDescription className="text-xs text-zinc-500">
                Add a new camera node. It appears online once it starts sending a heartbeat.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleAddCamera} className="space-y-4 py-1">
              <div className="space-y-1.5">
                <Label htmlFor="name" className="text-xs text-zinc-400">
                  Device name
                </Label>
                <Input
                  id="name"
                  required
                  value={newCamName}
                  onChange={(e) => setNewCamName(e.target.value)}
                  className="h-8 bg-zinc-900 border-zinc-800 text-sm focus-visible:ring-1 focus-visible:ring-indigo-500/50 focus-visible:border-indigo-500/50"
                  placeholder="e.g. Loading Dock Cam"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="location" className="text-xs text-zinc-400">
                  Location
                </Label>
                <Input
                  id="location"
                  required
                  value={newCamLocation}
                  onChange={(e) => setNewCamLocation(e.target.value)}
                  className="h-8 bg-zinc-900 border-zinc-800 text-sm focus-visible:ring-1 focus-visible:ring-indigo-500/50 focus-visible:border-indigo-500/50"
                  placeholder="e.g. North Warehouse"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="rtsp" className="text-xs text-zinc-400">
                  RTSP stream URL
                </Label>
                <Input
                  id="rtsp"
                  required
                  value={newCamRtsp}
                  onChange={(e) => setNewCamRtsp(e.target.value)}
                  className="h-8 bg-zinc-900 border-zinc-800 text-sm focus-visible:ring-1 focus-visible:ring-indigo-500/50 focus-visible:border-indigo-500/50"
                  placeholder="rtsp://admin:pass@192.168.1.100/stream"
                />
              </div>
              <DialogFooter className="pt-3 bg-black">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsAddModalOpen(false)}
                  className="h-8 text-xs text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={isAddingCamera}
                  className="h-8 px-3 text-xs bg-indigo-600 hover:bg-indigo-500 text-white"
                >
                  {isAddingCamera ? 'Adding…' : 'Add camera'}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>


      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {cameras.length === 0 ? (
          <div className="col-span-full py-14 flex flex-col items-center justify-center text-center rounded-lg border border-dashed border-zinc-800">
            <Video className="w-6 h-6 text-zinc-700 mb-2.5" strokeWidth={1.75} />
            <h3 className="text-sm font-medium text-zinc-300">No cameras yet</h3>
            <p className="text-xs text-zinc-500 mt-1">Add a camera to begin monitoring.</p>
          </div>
        ) : (
          cameras.map((cam) => (
            <Card
              key={cam.id}
              className="bg-zinc-900/40 border border-zinc-800 hover:border-zinc-700 transition-colors shadow-none gap-0 py-0"
            >
              <CardHeader className="px-4 pt-4 pb-2.5 gap-1">
                <div className="flex justify-between items-start gap-2">
                  <CardTitle className="text-[13px] font-medium text-zinc-100 truncate">
                    {cam.name}
                  </CardTitle>
                  <div className="flex items-center gap-1.5 shrink-0" title={cam.status}>
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${
                        cam.status === 'online' ? 'bg-emerald-500' : 'bg-red-500'
                      }`}
                    />
                    <span className="text-[10px] uppercase tracking-wide text-zinc-500">
                      {cam.status}
                    </span>
                  </div>
                </div>
                <p className="font-mono text-[10px] text-zinc-600 truncate" title={cam.id}>
                  {cam.id}
                </p>
              </CardHeader>


              <CardContent className="px-4 pb-4">
                <div className="flex items-center gap-1.5 text-xs text-zinc-400 mb-3 bg-zinc-950/60 px-2.5 py-1.5 rounded-md border border-zinc-800/80">
                  <MapPin className="w-3 h-3 text-zinc-600 shrink-0" />
                  <span className="truncate">{cam.location || 'Unspecified location'}</span>
                </div>


                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="flex-1 h-7 text-xs bg-transparent border-zinc-800 text-zinc-300 hover:bg-zinc-900 hover:text-zinc-100"
                    onClick={() => handleEditCamera(cam)}
                  >
                    <Settings2 className="w-3.5 h-3.5 mr-1.5" />
                    Zones
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    aria-label={`Delete ${cam.name}`}
                    className="h-7 px-2.5 text-xs text-zinc-500 hover:text-red-400 hover:bg-red-500/10"
                    onClick={() => setCameraToDelete(cam)}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>


      <ConfirmDialog
        open={!!cameraToDelete}
        onOpenChange={(open) => !open && setCameraToDelete(null)}
        title={`Delete "${cameraToDelete?.name}"?`}
        description="This permanently removes the camera and its saved zones. This action can't be undone."
        confirmLabel="Delete"
        variant="destructive"
        isLoading={isDeletingCamera}
        onConfirm={confirmDeleteCamera}
      />
    </div>
  );
}
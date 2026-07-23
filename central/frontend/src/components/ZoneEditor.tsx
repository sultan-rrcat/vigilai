import React, { useRef, useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Trash2, Check, Save, Crosshair, MapPinned } from 'lucide-react';

interface Point {
  x: number;
  y: number;
}

interface ZoneEditorProps {
  referenceImageUrl: string;
  existingZones?: { name: string; polygon: number[][] }[];
  onSave: (normalizedPolygon: number[][]) => void;
  onCancel: () => void;
  onClearAll: () => void;
}

export function ZoneEditor({ referenceImageUrl, existingZones = [], onSave, onClearAll }: ZoneEditorProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [points, setPoints] = useState<Point[]>([]);
  const [isClosed, setIsClosed] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);

  // Redraw the canvas whenever points change, image loads, or existing zones update
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Match canvas internal resolution to the exact display size of the tight wrapper
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw EXISTING zones first (indigo, quiet)
    existingZones.forEach((zone) => {
      if (!zone.polygon || zone.polygon.length < 3) return;

      ctx.beginPath();
      ctx.strokeStyle = 'rgba(99, 102, 241, 0.9)'; // indigo-500
      ctx.lineWidth = 1.5;
      ctx.fillStyle = 'rgba(99, 102, 241, 0.12)';

      zone.polygon.forEach((pt, index) => {
        const pixelX = pt[0] * canvas.width;
        const pixelY = pt[1] * canvas.height;
        if (index === 0) ctx.moveTo(pixelX, pixelY);
        else ctx.lineTo(pixelX, pixelY);
      });

      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      ctx.font = '500 10px Inter, sans-serif';
      const labelX = zone.polygon[0][0] * canvas.width;
      const labelY = zone.polygon[0][1] * canvas.height - 8;

      const textWidth = ctx.measureText(zone.name).width;
      ctx.fillStyle = 'rgba(9, 9, 11, 0.85)';
      ctx.roundRect(labelX - 4, labelY - 12, textWidth + 8, 17, 4);
      ctx.fill();

      ctx.fillStyle = 'rgba(165, 180, 252, 1)'; // indigo-300
      ctx.fillText(zone.name, labelX, labelY);
    });

    // Draw ACTIVE drawing points
    if (points.length > 0) {
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(244, 244, 245, 0.9)'; // zinc-100
      ctx.lineWidth = 1.5;
      ctx.fillStyle = 'rgba(244, 244, 245, 0.12)';

      points.forEach((normPt, index) => {
        const pixelX = normPt.x * canvas.width;
        const pixelY = normPt.y * canvas.height;
        if (index === 0) ctx.moveTo(pixelX, pixelY);
        else ctx.lineTo(pixelX, pixelY);
      });

      if (isClosed) {
        ctx.closePath();
        ctx.fill();
      }
      ctx.stroke();

      points.forEach((normPt) => {
        const pixelX = normPt.x * canvas.width;
        const pixelY = normPt.y * canvas.height;

        ctx.beginPath();
        ctx.arc(pixelX, pixelY, 2.5, 0, 2 * Math.PI);
        ctx.fillStyle = '#f43f5e'; // rose-500
        ctx.fill();
      });
    }
  }, [points, isClosed, imageLoaded, existingZones]);

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isClosed) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const pixelX = e.clientX - rect.left;
    const pixelY = e.clientY - rect.top;

    const normX = pixelX / rect.width;
    const normY = pixelY / rect.height;

    setPoints((prev) => [...prev, { x: normX, y: normY }]);
  };

  const handleClosePolygon = () => {
    if (points.length >= 3) {
      setIsClosed(true);
    }
  };

  const handleClearDrawing = () => {
    setPoints([]);
    setIsClosed(false);
  };

  const handleClearAll = () => {
    handleClearDrawing();
    onClearAll();
  };

  const handleSave = () => {
    if (!isClosed) return;
    const payload = points.map((p) => [Number(p.x.toFixed(4)), Number(p.y.toFixed(4))]);
    onSave(payload);
  };

  return (
    <div className="flex flex-col h-full gap-4 p-4 bg-zinc-950">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <MapPinned className="w-4 h-4 text-zinc-500" strokeWidth={2} />
          <h2 className="text-[13px] font-medium text-zinc-100">Boundary mapping</h2>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={points.length > 0 ? handleClearDrawing : handleClearAll}
            disabled={points.length === 0 && existingZones.length === 0}
            className="h-7 px-2.5 text-xs text-zinc-400 hover:text-red-400 hover:bg-red-500/10"
          >
            <Trash2 className="w-3.5 h-3.5 mr-1.5" />
            {points.length > 0 ? 'Discard points' : 'Clear all zones'}
          </Button>
          {!isClosed && points.length >= 3 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleClosePolygon}
              className="h-7 px-2.5 text-xs bg-transparent border-zinc-800 text-zinc-300 hover:bg-zinc-900 hover:text-zinc-100"
            >
              <Check className="w-3.5 h-3.5 mr-1.5" />
              Complete polygon
            </Button>
          )}
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!isClosed}
            className="h-7 px-3 text-xs bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-40"
          >
            <Save className="w-3.5 h-3.5 mr-1.5" />
            Save zone
          </Button>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900/30 overflow-hidden p-4 relative">
        {!imageLoaded && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-zinc-600 gap-2 z-0">
            <Crosshair className="w-6 h-6 animate-pulse" strokeWidth={1.75} />
            <span className="text-[11px] tracking-wide">Loading reference frame…</span>
          </div>
        )}

        <div
          className={`relative inline-block border border-zinc-800 rounded-md overflow-hidden transition-opacity duration-300 ${
            imageLoaded ? 'opacity-100' : 'opacity-0'
          }`}
          ref={containerRef}
        >
          <img
            src={referenceImageUrl}
            alt="Camera reference frame"
            onLoad={() => setImageLoaded(true)}
            onError={(e) => {
              console.warn('Reference image not found on server, falling back to placeholder.');
              e.currentTarget.src =
                'https://images.unsplash.com/photo-1574360741690-33306db7609a?q=80&w=1920&auto=format&fit=crop';
            }}
            className="block max-w-full max-h-[58vh] object-contain opacity-70"
          />

          <canvas
            ref={canvasRef}
            onClick={handleCanvasClick}
            className={`absolute inset-0 w-full h-full ${isClosed ? 'cursor-default' : 'cursor-crosshair'}`}
          />
        </div>

        {imageLoaded && !isClosed && (
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 bg-zinc-900 border border-zinc-800 px-3 py-1.5 rounded-full flex items-center gap-1.5 pointer-events-none">
            <Crosshair className="w-3 h-3 text-zinc-500" />
            <span className="text-[11px] text-zinc-400">
              {points.length === 0
                ? 'Click to place the first vertex'
                : points.length < 3
                  ? `Place ${3 - points.length} more vertices`
                  : "Click 'Complete polygon' when finished"}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

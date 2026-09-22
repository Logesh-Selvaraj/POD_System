import React, { useEffect, useMemo, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapPin, Navigation } from 'lucide-react';

// Fix default leaflet marker icon issue in webpack/vite
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
});

interface LocationPickerMapProps {
  lat: number;
  lng: number;
  onChange: (lat: number, lng: number) => void;
  radiusMeters?: number;
}

// Inner component to handle map click events
const MapClickCapture: React.FC<{ onLocationPicked: (lat: number, lng: number) => void }> = ({ onLocationPicked }) => {
  useMapEvents({
    click(e) {
      const clickedLat = parseFloat(e.latlng.lat.toFixed(6));
      const clickedLng = parseFloat(e.latlng.lng.toFixed(6));
      onLocationPicked(clickedLat, clickedLng);
    },
  });
  return null;
};

// Inner component to smoothly pan map when coordinates change
const MapViewSync: React.FC<{ center: [number, number] }> = ({ center }) => {
  const map = useMap();
  const lastCenter = useRef<[number, number]>(center);

  useEffect(() => {
    if (
      !isNaN(center[0]) &&
      !isNaN(center[1]) &&
      (lastCenter.current[0] !== center[0] || lastCenter.current[1] !== center[1])
    ) {
      lastCenter.current = center;
      map.panTo(center, { animate: true });
    }
  }, [center, map]);

  return null;
};

export const LocationPickerMap: React.FC<LocationPickerMapProps> = ({
  lat,
  lng,
  onChange,
  radiusMeters = 150,
}) => {
  const isValidPosition = typeof lat === 'number' && typeof lng === 'number' && !isNaN(lat) && !isNaN(lng);
  const currentCenter: [number, number] = useMemo(
    () => (isValidPosition ? [lat, lng] : [12.971598, 77.594566]),
    [lat, lng, isValidPosition]
  );

  const handleMarkerDragEnd = (e: L.DragEndEvent) => {
    const marker = e.target;
    if (marker) {
      const position = marker.getLatLng();
      const draggedLat = parseFloat(position.lat.toFixed(6));
      const draggedLng = parseFloat(position.lng.toFixed(6));
      onChange(draggedLat, draggedLng);
    }
  };

  const handleGetCurrentLocation = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (typeof navigator !== 'undefined' && 'geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const userLat = parseFloat(pos.coords.latitude.toFixed(6));
          const userLng = parseFloat(pos.coords.longitude.toFixed(6));
          onChange(userLat, userLng);
        },
        (err) => {
          console.warn('Geolocation lookup warning:', err.message);
        },
        { enableHighAccuracy: true, timeout: 8000 }
      );
    }
  };

  return (
    <div className="space-y-2">
      {/* Control bar / info */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-1.5 text-slate-400 font-medium">
          <MapPin className="w-3.5 h-3.5 text-indigo-600" />
          <span>Pin Location on Map</span>
          <span className="hidden sm:inline text-slate-400 text-[11px]">— Click anywhere to set coordinates</span>
        </div>
        <div className="flex items-center gap-2">
          {isValidPosition && (
            <span className="font-mono text-[11px] bg-slate-950 border border-slate-800 text-slate-200 px-2 py-0.5 rounded-md">
              {lat.toFixed(6)}, {lng.toFixed(6)}
            </span>
          )}
          {typeof navigator !== 'undefined' && 'geolocation' in navigator && (
            <button
              type="button"
              onClick={handleGetCurrentLocation}
              className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-200 rounded-md transition cursor-pointer"
              title="Locate device GPS position"
            >
              <Navigation className="w-3 h-3 text-indigo-600" />
              <span>My GPS</span>
            </button>
          )}
        </div>
      </div>

      {/* Map Container */}
      <div
        className="w-full h-64 rounded-xl overflow-hidden border border-slate-800 shadow-sm relative"
        style={{ isolation: 'isolate' }}
      >
        <MapContainer
          center={currentCenter}
          zoom={15}
          scrollWheelZoom={false}
          className="w-full h-full cursor-crosshair"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {/* Click event capture */}
          <MapClickCapture onLocationPicked={onChange} />

          {/* Map view synchronization */}
          <MapViewSync center={currentCenter} />

          {/* Target marker with drag support */}
          {isValidPosition && (
            <>
              <Marker
                position={[lat, lng]}
                draggable={true}
                eventHandlers={{
                  dragend: handleMarkerDragEnd,
                }}
              >
                <Popup>
                  <div className="text-slate-50 font-sans text-xs">
                    <strong className="text-indigo-600">Target Delivery Location</strong>
                    <br />
                    <span>Lat: {lat.toFixed(6)}</span>
                    <br />
                    <span>Lng: {lng.toFixed(6)}</span>
                    <br />
                    <span className="text-[10px] text-slate-400">Drag marker or click map to move</span>
                  </div>
                </Popup>
              </Marker>

              {/* 150m POD validation geofence radius */}
              <Circle
                center={[lat, lng]}
                radius={radiusMeters}
                pathOptions={{
                  color: '#0f172a',
                  fillColor: '#3b82f6',
                  fillOpacity: 0.12,
                  weight: 1.5,
                  dashArray: '4, 4',
                }}
              />
            </>
          )}
        </MapContainer>

        {/* Subtle overlay helper tag */}
        <div className="absolute bottom-2 left-2 pointer-events-none z-[1000] bg-slate-900/85 backdrop-blur-xs border border-slate-800 text-[10px] text-slate-300 px-2 py-0.5 rounded shadow">
          <span>Click any location on map to auto-fill Target Lat/Lng</span>
        </div>
      </div>
    </div>
  );
};

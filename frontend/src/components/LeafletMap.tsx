import React from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

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

interface LeafletMapProps {
  targetLat: number;
  targetLng: number;
  capturedLat?: number | null;
  capturedLng?: number | null;
  distanceMeters?: number | null;
  distanceM?: number | null;
}

export const LeafletMap: React.FC<LeafletMapProps> = ({
  targetLat,
  targetLng,
  capturedLat,
  capturedLng,
  distanceMeters,
  distanceM
}) => {
  const dist = distanceMeters ?? distanceM;
  const center: [number, number] = [targetLat, targetLng];

  return (
    <div className="w-full h-64 rounded-xl overflow-hidden border border-slate-800 shadow-md" style={{ isolation: 'isolate' }}>
      <MapContainer
        center={center}
        zoom={16}
        scrollWheelZoom={false}
        className="w-full h-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Target Delivery Location Marker */}
        <Marker position={[targetLat, targetLng]}>
          <Popup>
            <div className="text-slate-50 font-sans">
              <strong>Target Address</strong>
              <br />
              [{targetLat.toFixed(5)}, {targetLng.toFixed(5)}]
            </div>
          </Popup>
        </Marker>

        {/* 150m Target Radius Circle */}
        <Circle
          center={[targetLat, targetLng]}
          radius={150}
          pathOptions={{ color: '#22c55e', fillColor: '#22c55e', fillOpacity: 0.15 }}
        />

        {/* Captured GPS Marker if available */}
        {capturedLat && capturedLng && (
          <Marker position={[capturedLat, capturedLng]}>
            <Popup>
              <div className="text-slate-50 font-sans">
                <strong>Rider Captured GPS</strong>
                <br />
                Distance: {dist ? `${dist}m` : 'Calculated'}
              </div>
            </Popup>
          </Marker>
        )}
      </MapContainer>
    </div>
  );
};

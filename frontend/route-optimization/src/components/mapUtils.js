import L from "leaflet";
import iconUrl from "leaflet/dist/images/marker-icon.png";
import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";

// Fix Leaflet's default marker asset paths when bundling with Vite.
L.Icon.Default.mergeOptions({
    iconUrl,
    iconRetinaUrl,
    shadowUrl,
});

/** Build a small circular colored div-marker (used for vehicles / stops). */
export function coloredDot(color, { size = 18, ring = "#fff" } = {}) {
    return L.divIcon({
        className: "custom-dot-icon",
        html: `<span style="
      display:inline-block;width:${size}px;height:${size}px;border-radius:50%;
      background:${color};border:2px solid ${ring};
      box-shadow:0 0 0 1px rgba(0,0,0,0.25);"></span>`,
        iconSize: [size, size],
        iconAnchor: [size / 2, size / 2],
    });
}

export function warehouseIcon() {
    return L.divIcon({
        className: "custom-warehouse-icon",
        html: `<div style="font-size:40px; text-align:center; line-height:40px; filter:drop-shadow(2px 4px 4px rgba(0,0,0,0.6));">🏭</div>`,
        iconSize: [40, 40],
        iconAnchor: [20, 20],
    });
}

export function shopIcon({ completed = false } = {}) {
    const filter = completed ? "grayscale(100%) opacity(60%)" : "drop-shadow(2px 3px 3px rgba(0,0,0,0.5))";
    return L.divIcon({
        className: "custom-shop-icon",
        html: `<div style="font-size:32px; text-align:center; line-height:32px; filter:${filter};">🏪</div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
    });
}

/** Square marker for the warehouse/depot. */
export function squareMarker(color) {
    return L.divIcon({
        className: "custom-square-icon",
        html: `<span style="
      display:inline-block;width:16px;height:16px;background:${color};
      border:2px solid #fff;box-shadow:0 0 0 1px rgba(0,0,0,0.3);"></span>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8],
    });
}

export const STATUS_COLORS = {
    on_route: "#1e8e3e",
    delayed: "#d97706",
    breakdown: "#d6001c",
    maintenance: "#d6001c",
    completed: "#6b6b6b",
};

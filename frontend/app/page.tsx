"use client";

import { useState, useRef, useEffect, useCallback } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "/api/v1";

interface Place {
  name: string;
  address: string;
  place_id: string;
  types: string[];
  rating?: number;
  original: { lat: number; lng: number };
  corrected: { lat: number; lng: number };
  naver_location: { lat: number; lng: number } | null;
  sync_score: number | null;
  correction_distance_m: number;
  confidence: number;
  method: string;
  // POI 생존 검증
  status: "verified" | "warning" | "not_found";
  status_reason: string;
  status_confidence: number;
  naver_name: string | null;
  naver_category: string | null;
  naver_phone: string | null;
  naver_link: string | null;
  name_similarity: number | null;
}

interface Prediction {
  description: string;
  place_id: string;
  main_text: string;
}

declare global { interface Window { naver: any; } }

const STATUS_CONFIG = {
  verified: { icon: "\u2705", label: "\uc601\uc5c5 \uc911 \ud655\uc778", color: "var(--verified)", bg: "rgba(13,240,122,0.12)" },
  warning: { icon: "\u26a0\ufe0f", label: "\uc774\uc804 \uac00\ub2a5\uc131", color: "var(--warning)", bg: "rgba(255,171,0,0.12)" },
  not_found: { icon: "\u274c", label: "\ud3d0\uc5c5 \ucd94\uc815", color: "var(--not-found)", bg: "rgba(255,85,85,0.12)" },
} as const;

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [selected, setSelected] = useState<Place | null>(null);
  const [loading, setLoading] = useState(false);
  const [mapsKey, setMapsKey] = useState("");
  const [naverKey, setNaverKey] = useState("");
  const [gReady, setGReady] = useState(false);
  const [nReady, setNReady] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Map refs
  const nMapRef = useRef<HTMLDivElement>(null);
  const gMapRef = useRef<HTMLDivElement>(null);
  const nMap = useRef<any>(null);
  const gMap = useRef<google.maps.Map | null>(null);
  const nMarker = useRef<any>(null);
  const gMarkers = useRef<google.maps.Marker[]>([]);

  // Fetch keys
  useEffect(() => {
    fetch(`${API_BASE}/maps-keys`).then(r => r.json()).then(d => {
      if (d.success) {
        if (d.data?.google_maps_key) setMapsKey(d.data.google_maps_key);
        if (d.data?.naver_client_id) setNaverKey(d.data.naver_client_id);
      }
    }).catch(() => { });
  }, []);

  // Load SDKs
  useEffect(() => {
    if (!mapsKey || gReady) return;
    const s = document.createElement("script");
    s.src = `https://maps.googleapis.com/maps/api/js?key=${mapsKey}&language=ko`;
    s.async = true; s.onload = () => setGReady(true);
    document.head.appendChild(s);
  }, [mapsKey, gReady]);

  useEffect(() => {
    if (!naverKey || nReady) return;
    const s = document.createElement("script");
    s.src = `https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=${naverKey}`;
    s.async = true; s.onload = () => setNReady(true);
    document.head.appendChild(s);
  }, [naverKey, nReady]);

  const handleInput = useCallback((value: string) => {
    setQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (value.length < 2) { setPredictions([]); return; }
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${API_BASE}/search/autocomplete?q=${encodeURIComponent(value)}`);
        const data = await res.json();
        setPredictions(data.predictions || []);
      } catch { setPredictions([]); }
    }, 300);
  }, []);

  const handleSearch = useCallback(async (searchQuery?: string) => {
    const q = searchQuery || query;
    if (!q.trim()) return;
    // Cancel pending debounce to prevent autocomplete firing after search
    if (debounceRef.current) { clearTimeout(debounceRef.current); debounceRef.current = null; }
    setLoading(true);
    setPredictions([]);
    try {
      const res = await fetch(`${API_BASE}/search`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q }),
      });
      const data = await res.json();
      if (data.places?.length > 0) {
        setSelected(data.places[0]);
      }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [query]);

  // Reset map instances when returning to empty state (DOM unmounts)
  useEffect(() => {
    if (!selected) {
      gMap.current = null;
      nMap.current = null;
      nMarker.current = null;
      gMarkers.current = [];
    }
  }, [selected]);

  // Update maps when selected changes
  useEffect(() => {
    if (!selected) return;
    const orig = selected.original;
    const n_loc = selected.naver_location;

    // Google Map (left) — show original Google coordinate
    if (gReady && gMapRef.current) {
      if (!gMap.current) {
        gMap.current = new google.maps.Map(gMapRef.current, {
          center: orig, zoom: 17, styles: darkStyle, disableDefaultUI: true, zoomControl: true,
        });
      } else {
        gMap.current.setCenter(orig);
        gMap.current.setZoom(17);
      }
      const map = gMap.current;
      gMarkers.current.forEach(m => m.setMap(null)); gMarkers.current = [];

      const statusColor = selected.status === "verified" ? "#0df07a" : selected.status === "warning" ? "#ffab00" : "#ff5555";
      const mO = new google.maps.Marker({
        position: orig,
        map,
        icon: { path: google.maps.SymbolPath.CIRCLE, scale: 10, fillColor: statusColor, fillOpacity: 0.9, strokeColor: "#fff", strokeWeight: 2 },
        title: `${selected.name} (Google)`,
      });
      gMarkers.current.push(mO);
    }

    // Naver Map (right) — show Naver verified coordinate (or fallback to original)
    if (nReady && nMapRef.current && window.naver && window.naver.maps) {
      const pos = n_loc
        ? new window.naver.maps.LatLng(n_loc.lat, n_loc.lng)
        : new window.naver.maps.LatLng(orig.lat, orig.lng);
      if (!nMap.current) {
        nMap.current = new window.naver.maps.Map(nMapRef.current, {
          center: pos, zoom: 17,
        });
      } else {
        nMap.current.setCenter(pos);
      }
      if (nMarker.current) { nMarker.current.setPosition(pos); }
      else {
        nMarker.current = new window.naver.maps.Marker({ position: pos, map: nMap.current });
      }
    }
  }, [selected, gReady, nReady]);

  const sc = selected ? STATUS_CONFIG[selected.status] : null;

  return (
    <div className="flex flex-col h-screen bg-[var(--bg)]">
      {/* Header */}
      <header className="flex items-center gap-3 px-5 py-3 border-b border-[var(--border)] bg-[var(--panel)] z-30 flex-shrink-0">
        <h1 className="text-lg font-bold whitespace-nowrap cursor-pointer" onClick={() => { setSelected(null); setQuery(""); setPredictions([]); }}>
          <span className="text-[var(--accent)]">Geo</span>Harness
        </h1>
        <div className="relative flex-1 max-w-xl">
          <input type="text" value={query}
            onChange={(e) => handleInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); handleSearch(); } }}
            placeholder="장소를 검색하세요 (예: 천상가옥, 블루보틀 성수)"
            className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-4 py-2.5 text-sm placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] transition-colors" />
          {predictions.length > 0 && (
            <ul className="absolute top-full left-0 right-0 mt-1 bg-[var(--panel)] border border-[var(--border)] rounded-lg overflow-hidden z-40 shadow-xl">
              {predictions.map((p) => (
                <li key={p.place_id} className="px-4 py-2.5 text-sm cursor-pointer hover:bg-[var(--accent-dim)] transition-colors"
                  onClick={() => { setQuery(p.main_text); setPredictions([]); handleSearch(p.description); }}>
                  <span className="font-medium">{p.main_text}</span>
                  <span className="text-[var(--text-muted)] text-xs ml-2">{p.description.replace(p.main_text, "").replace(/^,?\s*/, "")}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <button onClick={() => handleSearch()} disabled={loading}
          className="px-5 py-2.5 bg-[var(--accent)] text-black font-semibold rounded-lg text-sm hover:brightness-110 disabled:opacity-50 transition-all whitespace-nowrap">
          {loading ? "..." : "검색"}
        </button>
      </header>

      {/* Empty State */}
      {!selected ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-5 text-center px-6">
          <p className="text-5xl">🏪</p>
          <h2 className="text-2xl font-bold">이 가게, 아직 있을까?</h2>
          <p className="text-sm text-[var(--text-muted)] max-w-lg leading-relaxed">
            구글 지도에서 찾은 한국 장소가 실제로 존재하는지<br />
            네이버 데이터와 교차검증합니다.
          </p>
          <p className="text-xs text-[var(--text-muted)] max-w-md">
            한국 내 구글 POI의 <strong className="text-[var(--warning)]">31%</strong>는 폐업·이전되었을 수 있습니다.
          </p>
          <div className="flex gap-2 mt-4 flex-wrap justify-center">
            {["복식커피", "아무튼겨울", "뚝섬미술관", "하이라인 성수"].map((n) => (
              <button key={n} onClick={() => { setQuery(n); handleSearch(n); }}
                className="px-3 py-1.5 bg-[var(--border)] rounded-full text-xs hover:bg-[var(--accent-dim)] transition-colors">{n}</button>
            ))}
          </div>
        </div>
      ) : (
        /* Result State */
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Verdict Card */}
          {sc && (
            <div className="flex-shrink-0 px-6 py-4 border-b border-[var(--border)] animate-fade-in" style={{ background: sc.bg }}>
              <div className="flex items-start gap-4 max-w-4xl mx-auto">
                {/* Status Badge */}
                <div className="flex-shrink-0 text-center">
                  <p className="text-4xl">{sc.icon}</p>
                  <p className="text-xs font-bold mt-1" style={{ color: sc.color }}>{sc.label}</p>
                  <p className="text-[10px] text-[var(--text-muted)] mt-0.5">
                    {Math.round(selected.status_confidence * 100)}%
                  </p>
                </div>
                {/* Details */}
                <div className="flex-1 min-w-0">
                  <h2 className="text-lg font-bold truncate">{selected.name}</h2>
                  <p className="text-xs text-[var(--text-muted)] truncate mt-0.5">{selected.address}</p>
                  <p className="text-xs mt-1" style={{ color: sc.color }}>{selected.status_reason}</p>

                  {selected.naver_name && (
                    <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[var(--text-muted)]">
                      <span>
                        네이버 매칭: <strong className="text-[var(--text)]">{selected.naver_name}</strong>
                        {selected.name_similarity != null && (
                          <span className="ml-1 text-[var(--text-muted)]">(유사도 {Math.round(selected.name_similarity * 100)}%)</span>
                        )}
                      </span>
                      {selected.naver_category && <span>{selected.naver_category}</span>}
                      {selected.naver_phone && <span>📞 {selected.naver_phone}</span>}
                      {selected.naver_link && (
                        <a href={selected.naver_link} target="_blank" rel="noopener noreferrer"
                          className="text-[var(--blue)] hover:underline">🔗 네이버 플레이스</a>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Maps: Google (left) | Naver (right) */}
          <div className="flex-1 flex min-h-0">
            {/* Google Map (left) */}
            <div className="w-1/2 relative border-r border-[var(--border)]">
              <div className="absolute top-3 left-3 z-10">
                <span className="bg-[var(--panel)] border border-[var(--border)] text-xs font-bold px-3 py-1.5 rounded-full shadow-lg">
                  📍 구글 지도
                </span>
              </div>
              <div ref={gMapRef} className="w-full h-full" />
            </div>
            {/* Naver Map (right) */}
            <div className="w-1/2 relative">
              <div className="absolute top-3 left-3 z-10">
                <span className={`text-xs font-bold px-3 py-1.5 rounded-full shadow-lg ${
                  selected.naver_location
                    ? "bg-[var(--accent)] text-black"
                    : "bg-[var(--panel)] border border-[var(--border)]"
                }`}>
                  {selected.naver_location ? "✅ 네이버 확인 좌표" : "📍 네이버 (좌표 없음)"}
                </span>
              </div>
              <div ref={nMapRef} className="w-full h-full" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const darkStyle: google.maps.MapTypeStyle[] = [
  { elementType: "geometry", stylers: [{ color: "#1a1a2e" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#1a1a2e" }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#8888aa" }] },
  { featureType: "road", elementType: "geometry", stylers: [{ color: "#2a2a4a" }] },
  { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#3a3a5a" }] },
  { featureType: "water", elementType: "geometry", stylers: [{ color: "#0e1626" }] },
  { featureType: "poi", elementType: "geometry", stylers: [{ color: "#1e1e3e" }] },
];

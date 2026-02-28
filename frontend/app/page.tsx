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
}

interface Prediction {
  description: string;
  place_id: string;
  main_text: string;
}

declare global { interface Window { naver: any; } }

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [selected, setSelected] = useState<Place | null>(null);
  const [loading, setLoading] = useState(false);
  const [mapsKey, setMapsKey] = useState("");
  const [naverKey, setNaverKey] = useState("");
  const [gReady, setGReady] = useState(false);
  const [nReady, setNReady] = useState(false);
  const [showCorrection, setShowCorrection] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Map refs
  const nMapRef = useRef<HTMLDivElement>(null);
  const gMapRef = useRef<HTMLDivElement>(null);
  const nMap = useRef<any>(null);
  const gMap = useRef<google.maps.Map | null>(null);
  const nMarker = useRef<any>(null);
  const gMarkers = useRef<google.maps.Marker[]>([]);
  const gLine = useRef<google.maps.Polyline | null>(null);

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
    s.src = `https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyID=${naverKey}`;
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
    setLoading(true); setPredictions([]);
    try {
      const res = await fetch(`${API_BASE}/search`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q }),
      });
      const data = await res.json();
      if (data.places?.length > 0) {
        setSelected(data.places[0]);
        setShowCorrection(false); // Reset toggle state on new search
      }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [query]);

  // Update maps when selected changes or showCorrection toggles
  useEffect(() => {
    if (!selected) return;
    const corr = selected.corrected;
    const orig = selected.original;
    const n_loc = selected.naver_location ?? corr; // fallback to corrected if naver_location absent

    // Naver Map (검색된 네이버 좌표)
    if (nReady && nMapRef.current && window.naver && window.naver.maps) {
      const pos = new window.naver.maps.LatLng(n_loc.lat, n_loc.lng);
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

    // Google Map (오차 표시)
    if (gReady && gMapRef.current) {
      if (!gMap.current) {
        gMap.current = new google.maps.Map(gMapRef.current, {
          center: orig, zoom: 17, styles: darkStyle, disableDefaultUI: true, zoomControl: true,
        });
      }
      const map = gMap.current;
      gMarkers.current.forEach(m => m.setMap(null)); gMarkers.current = [];
      gLine.current?.setMap(null);

      // Always show Original Google Coordinate
      const mO = new google.maps.Marker({
        position: orig,
        map,
        icon: { path: google.maps.SymbolPath.CIRCLE, scale: 10, fillColor: "#ff5555", fillOpacity: 0.9, strokeColor: "#fff", strokeWeight: 2 },
        title: "❌ 구글 (틀림)",
        zIndex: 1
      });
      gMarkers.current.push(mO);

      // Show Corrected coordinate and line ONLY IF toggled on
      if (showCorrection) {
        const mC = new google.maps.Marker({
          position: corr,
          map,
          icon: { path: google.maps.SymbolPath.CIRCLE, scale: 12, fillColor: "#0df07a", fillOpacity: 0.95, strokeColor: "#fff", strokeWeight: 2 },
          title: "✅ ML 보정",
          zIndex: 2
        });
        const ln = new google.maps.Polyline({
          path: [orig, corr],
          map,
          strokeColor: "#0df07a",
          strokeOpacity: 0.85,
          strokeWeight: 3,
          icons: [{ icon: { path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW, scale: 3, fillColor: "#0df07a", fillOpacity: 1 }, offset: "100%" }]
        });
        gMarkers.current.push(mC);
        gLine.current = ln;

        const b = new google.maps.LatLngBounds(); b.extend(orig); b.extend(corr); map.fitBounds(b, 60);
        const li = google.maps.event.addListener(map, "idle", () => { if ((map.getZoom() ?? 0) > 18) map.setZoom(18); google.maps.event.removeListener(li); });
      } else {
        map.setCenter(orig);
        map.setZoom(17);
      }
    }
  }, [selected, gReady, nReady, showCorrection]);

  return (
    <div className="flex flex-col h-screen bg-[var(--bg)]">
      <header className="flex items-center gap-3 px-5 py-3 border-b border-[var(--border)] bg-[var(--panel)] z-30 flex-shrink-0">
        <h1 className="text-lg font-bold whitespace-nowrap">🌐 <span className="text-[var(--accent)]">Geo</span>Harness</h1>
        <div className="relative flex-1 max-w-xl">
          <input type="text" value={query} onChange={(e) => handleInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="장소를 검색하세요 (예: 천상가옥, 오우도)"
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
          {loading ? "⏳" : "🔍 검색"}
        </button>
        <span className="text-xs text-[var(--text-muted)] hidden md:block">Powered by Gemini + ML</span>
      </header>

      {!selected ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center px-6">
          <p className="text-5xl">🗺️</p>
          <h2 className="text-2xl font-bold">구글 지도는 한국에서 틀립니다</h2>
          <p className="text-sm text-[var(--text-muted)] max-w-lg leading-relaxed">
            🇰🇷 한국 규제로 구글 지도는 수년간 업데이트되지 못했습니다.<br />
            성수동처럼 빠르게 변화한 동네에서 관광객은 길을 잃습니다.<br /><br />
            <strong className="text-[var(--accent)]">GeoHarness</strong>는 ML로 좌표를 보정하여 <strong>실제 위치</strong>를 알려드립니다.
          </p>
          <div className="flex gap-2 mt-4 flex-wrap justify-center">
            {["천상가옥", "오우도", "서울로인 서울숲점", "모나미스토어 성수점", "하이라인 성수"].map((n) => (
              <button key={n} onClick={() => { setQuery(n); handleSearch(n); }}
                className="px-3 py-1.5 bg-[var(--border)] rounded-full text-xs hover:bg-[var(--accent-dim)] transition-colors">{n}</button>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 flex min-h-0">
            {/* 네이버 지도 (Naver Maps SDK) */}
            <div className="w-1/2 relative border-r-2 border-[var(--accent)]">
              <div className="absolute top-3 left-3 z-10 flex gap-2">
                <span className="bg-[var(--accent)] text-black text-xs font-bold px-3 py-1.5 rounded-full shadow-lg">
                  {selected.naver_location ? "✅ 네이버 지도 (실제 위치 좌표)" : "📍 네이버 지도 (보정 좌표 사용)"}
                </span>
              </div>
              <div ref={nMapRef} className="w-full h-full" />
            </div>
            {/* 구글 지도 + 오차 마커 */}
            <div className="w-1/2 relative bg-black/10">
              <div className="absolute top-3 left-3 z-10">
                <span className="bg-[var(--danger)] text-white text-xs font-bold px-3 py-1.5 rounded-full shadow-lg">❌ 구글 지도 (업데이트 안됨)</span>
              </div>

              {showCorrection && (
                <div className="absolute top-3 right-3 z-10 bg-black/70 backdrop-blur-sm border border-[var(--border)] rounded-lg p-2.5 text-xs animate-in fade-in">
                  <div className="flex items-center gap-2 mb-1"><span className="w-3 h-3 rounded-full bg-[#ff5555] inline-block" /><span>구글 좌표 (틀림)</span></div>
                  <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-[#0df07a] inline-block" /><span>ML 보정 (실제)</span></div>
                  {selected.naver_location && <div className="flex items-center gap-2 mt-1"><span className="w-3 h-3 rounded-full bg-[#4a9eff] inline-block" /><span>네이버 좌표</span></div>}
                </div>
              )}

              {/* Toggle ML Correction Overlay Button — 우측 하단 */}
              {!showCorrection && (
                <div className="absolute bottom-6 right-6 z-20">
                  <button
                    onClick={() => setShowCorrection(true)}
                    className="px-6 py-3 bg-[var(--accent)] text-black font-extrabold rounded-full shadow-[0_0_20px_rgba(13,240,122,0.6)] hover:scale-105 transition-all animate-pulse"
                  >
                    ✨ ML 로직으로 좌표 보정하기
                  </button>
                </div>
              )}

              {/* 길찾기 버튼 — 구글 지도 위 오버레이 (보정 후에만 표시) */}
              {showCorrection && selected && (
                <a href={`https://www.google.com/maps/dir/?api=1&destination=${selected.corrected.lat},${selected.corrected.lng}`}
                  target="_blank" rel="noopener noreferrer"
                  className="absolute bottom-6 right-6 z-20 px-5 py-3 bg-[var(--blue)] text-white font-bold rounded-full text-sm shadow-lg hover:bg-blue-500 hover:shadow-blue-500/50 transition-all flex items-center gap-2">
                  <span className="text-lg">📍</span> 구글맵 길찾기
                </a>
              )}

              <div ref={gMapRef} className="w-full h-full" />
            </div>
          </div>
          <div className="flex-shrink-0 bg-[var(--panel)] border-t border-[var(--border)] px-6 py-4 flex items-center justify-between gap-8">
            <div className="flex-1 min-w-0 max-w-sm">
              <h2 className="text-lg font-bold truncate leading-tight">{selected.name}</h2>
              <p className="text-xs text-[var(--text-muted)] truncate mt-1">{selected.address}</p>
            </div>

            {showCorrection ? (
              <div className="flex items-center gap-12 animate-in slide-in-from-right-8 opacity-100">
                <div className="text-center flex-shrink-0">
                  {selected.sync_score != null ? (
                    <>
                      <p className={`text-4xl font-black ${selected.sync_score > 90 ? "text-[var(--accent)]" : "text-[var(--warning)]"}`}>
                        {selected.sync_score}<span className="text-xl font-normal ml-0.5">%</span>
                      </p>
                      <p className="text-xs font-medium text-[var(--text-muted)] mt-1 tracking-wider uppercase">네이버-구글 정합도</p>
                    </>
                  ) : (
                    <>
                      <p className="text-4xl font-black text-[var(--text-muted)]">N/A</p>
                      <p className="text-xs font-medium text-[var(--text-muted)] mt-1 tracking-wider uppercase">네이버 데이터 없음</p>
                    </>
                  )}
                </div>

                <div className="text-center flex-shrink-0">
                  <p className="text-4xl font-extrabold text-[#ff5555]">
                    {selected.correction_distance_m.toFixed(1)}<span className="text-xl font-normal ml-1">m</span>
                  </p>
                  <p className="text-xs font-medium text-[var(--text-muted)] mt-1 tracking-wider uppercase">공간 오차</p>
                </div>

              </div>
            ) : (
              <div className="text-[var(--text-muted)] text-sm italic font-medium w-[400px] text-center">
                ML 보정 기능을 적용하여 실제 위치와 좌표 편차를 확인하세요.
              </div>
            )}
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

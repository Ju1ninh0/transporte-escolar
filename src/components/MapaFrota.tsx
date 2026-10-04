"use client";
import "leaflet/dist/leaflet.css";
import { useEffect, useRef, useState } from "react";
import type * as Leaflet from "leaflet";

export type PontoMapa = { lat: number; lng: number };
export type ParadaMapa = PontoMapa & { nome: string; ordem: number };
export type VanMapa = PontoMapa & { id: number; rotulo: string; destaque?: boolean };

type Props = {
  paradas?: ParadaMapa[];
  vans?: VanMapa[];
  trilha?: PontoMapa[];
  altura?: string; // classe do Tailwind, ex.: "h-72"
  onClick?: (p: PontoMapa) => void;
  ajusteKey?: string | number; // quando muda, o mapa reenquadra os pontos
};

const MACEIO: [number, number] = [-9.6658, -35.7353];

function esc(texto: string) {
  return texto.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c] ?? c);
}

export default function MapaFrota({ paradas = [], vans = [], trilha = [], altura = "h-72", onClick, ajusteKey }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const mapa = useRef<Leaflet.Map | null>(null);
  const camada = useRef<Leaflet.LayerGroup | null>(null);
  const lib = useRef<typeof Leaflet | null>(null);
  const aoClicar = useRef(onClick);
  aoClicar.current = onClick;
  const ajustado = useRef<string | number | null>(null);
  const [pronto, setPronto] = useState(false);

  // Cria o mapa uma única vez (Leaflet só funciona no navegador, por isso o import dinâmico)
  useEffect(() => {
    let cancelado = false;
    (async () => {
      const mod = await import("leaflet");
      const L = ((mod as unknown as { default?: typeof Leaflet }).default ?? mod) as typeof Leaflet;
      if (cancelado || !el.current || mapa.current) return;
      lib.current = L;
      const m = L.map(el.current).setView(MACEIO, 12);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap",
      }).addTo(m);
      camada.current = L.layerGroup().addTo(m);
      m.on("click", (e: Leaflet.LeafletMouseEvent) => aoClicar.current?.({ lat: e.latlng.lat, lng: e.latlng.lng }));
      mapa.current = m;
      setPronto(true);
    })();
    return () => {
      cancelado = true;
      mapa.current?.remove();
      mapa.current = null;
      camada.current = null;
    };
  }, []);

  // Redesenha os elementos sempre que os dados mudam
  useEffect(() => {
    const L = lib.current;
    const m = mapa.current;
    const grupo = camada.current;
    if (!pronto || !L || !m || !grupo) return;
    grupo.clearLayers();
    const pontos: [number, number][] = [];

    const ordenadas = [...paradas].sort((a, b) => a.ordem - b.ordem);
    if (ordenadas.length > 1) {
      L.polyline(
        ordenadas.map((p) => [p.lat, p.lng] as [number, number]),
        { color: "#0f172a", weight: 3, dashArray: "6 6", opacity: 0.6 },
      ).addTo(grupo);
    }
    for (const p of ordenadas) {
      pontos.push([p.lat, p.lng]);
      const icone = L.divIcon({
        className: "",
        iconSize: [26, 26],
        iconAnchor: [13, 13],
        html: `<div style="background:#0f172a;color:#fff;border-radius:9999px;width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.4)">${p.ordem}</div>`,
      });
      L.marker([p.lat, p.lng], { icon: icone }).bindTooltip(esc(p.nome)).addTo(grupo);
    }

    if (trilha.length > 1) {
      L.polyline(
        trilha.map((p) => [p.lat, p.lng] as [number, number]),
        { color: "#2563eb", weight: 4, opacity: 0.7 },
      ).addTo(grupo);
    }

    for (const v of vans) {
      pontos.push([v.lat, v.lng]);
      const anel = v.destaque ? "box-shadow:0 0 0 4px rgba(37,99,235,.35);" : "box-shadow:0 1px 3px rgba(0,0,0,.4);";
      const icone = L.divIcon({
        className: "",
        iconSize: [36, 36],
        iconAnchor: [18, 18],
        html: `<div style="background:#fff;border-radius:9999px;width:36px;height:36px;display:flex;align-items:center;justify-content:center;border:2px solid #2563eb;${anel}"><svg width=\"18\" height=\"18\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#2563eb\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"3\" y=\"5\" width=\"18\" height=\"12\" rx=\"2\"/><path d=\"M3 11h18\"/><circle cx=\"8\" cy=\"19\" r=\"1.5\"/><circle cx=\"16\" cy=\"19\" r=\"1.5\"/></svg></div>`,
      });
      L.marker([v.lat, v.lng], { icon: icone, zIndexOffset: 1000 }).bindTooltip(esc(v.rotulo)).addTo(grupo);
    }

    const chave = ajusteKey ?? "unico";
    if (ajustado.current !== chave && pontos.length > 0) {
      ajustado.current = chave;
      if (pontos.length === 1) m.setView(pontos[0], 16);
      else m.fitBounds(pontos, { padding: [30, 30], maxZoom: 17 });
    }
  }, [pronto, paradas, vans, trilha, ajusteKey]);

  return <div ref={el} className={`relative isolate z-0 w-full overflow-hidden rounded-2xl border border-slate-200 ${altura}`} />;
}
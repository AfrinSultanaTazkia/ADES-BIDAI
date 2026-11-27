import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  ShieldAlert, AlertTriangle, Sliders, CheckCircle2, FileDown,
  Users, Bed, TestTube, Activity, Layers, MapPin, RefreshCw,
  Search, ArrowUpDown, Building2, Sparkles, ExternalLink, Info,
  Send, Download, Database, ArrowRight, Copy, Check, FileText,
  Home, ChevronRight, Share2, Filter, Clock
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line
} from 'recharts';
import L from 'leaflet';
import { toBangla, translateRisk, translateCity, translateResource } from './banglaUtils';

// ── Bangla helpers ──────────────────────────────────────────────────────────
const bn = {
  home: 'হোম',
  forecast: 'ডেঙ্গু পূর্বাভাস',
  allocation: 'ওয়ার্ডভিত্তিক সম্পদ বরাদ্দ',
  map: 'ঝুঁকি ও নজরদারি মানচিত্র',
  controls: 'আঞ্চলিক সম্পদ নিয়ন্ত্রণ',
  hospital: 'হাসপাতাল শয্যা ব্যবস্থাপনা',
  redistribution: 'আন্তঃওয়ার্ড সম্পদ পুনর্বণ্টন',
  alerts: 'সম্পদ ঘাটতি ও সতর্কতা',
  mosquito: 'মশক নিধন কার্যক্রম',
  dispatch: 'জরুরি বার্তা ও প্রতিবেদন',
};

// ── Pastel card accent map ────────────────────────────────────────────────
const CARD_STYLES = {
  forecast:       { bg: 'bg-[#E8F8F5]', border: 'border-[#0d9488]', icon: '📈', iconColor: 'text-[#0d9488]', iconBg: 'bg-[#ccfbf1]' },
  allocation:     { bg: 'bg-[#F3EEFF]', border: 'border-[#7c3aed]', icon: '📦', iconColor: 'text-[#7c3aed]', iconBg: 'bg-[#ede9fe]' },
  map:            { bg: 'bg-[#EFF6FF]', border: 'border-[#2563eb]', icon: '🗺️', iconColor: 'text-[#2563eb]', iconBg: 'bg-[#dbeafe]' },
  controls:       { bg: 'bg-[#FFFBEB]', border: 'border-[#ca8a04]', icon: '⚙️', iconColor: 'text-[#ca8a04]', iconBg: 'bg-[#fef9c3]' },
  hospital:       { bg: 'bg-[#FFF0F6]', border: 'border-[#db2777]', icon: '🏥', iconColor: 'text-[#db2777]', iconBg: 'bg-[#fce7f3]' },
  redistribution: { bg: 'bg-[#EEF2FF]', border: 'border-[#4338ca]', icon: '🔄', iconColor: 'text-[#4338ca]', iconBg: 'bg-[#e0e7ff]' },
  alerts:         { bg: 'bg-[#FFF5F5]', border: 'border-[#dc2626]', icon: '🚨', iconColor: 'text-[#dc2626]', iconBg: 'bg-[#fee2e2]' },
  mosquito:       { bg: 'bg-[#F0FFF4]', border: 'border-[#15803d]', icon: '🧹', iconColor: 'text-[#15803d]', iconBg: 'bg-[#dcfce7]' },
  dispatch:       { bg: 'bg-[#FFF7ED]', border: 'border-[#ea580c]', icon: '📢', iconColor: 'text-[#ea580c]', iconBg: 'bg-[#ffedd5]' },
};

const FEATURE_CARDS = [
  { id: 'forecast',       title: 'ডেঙ্গু পূর্বাভাস',              desc: 'আগামী ২ সপ্তাহের সম্ভাব্য ডেঙ্গু রোগীর সংখ্যা ও ঝুঁকির পূর্বাভাস দেখুন।' },
  { id: 'allocation',     title: 'ওয়ার্ডভিত্তিক সম্পদ বরাদ্দ',  desc: 'নির্দিষ্ট ওয়ার্ডের সম্পদের চাহিদা, বরাদ্দ ও বর্তমান পরিস্থিতি দেখুন।' },
  { id: 'map',            title: 'ঝুঁকি ও নজরদারি মানচিত্র',      desc: 'মানচিত্রের মাধ্যমে ডেঙ্গুর ঝুঁকিপূর্ণ এলাকাগুলো চিহ্নিত করুন।' },
  { id: 'controls',       title: 'আঞ্চলিক সম্পদ নিয়ন্ত্রণ',      desc: 'উপলব্ধ সম্পদ ও মশক নিধন দলের সংখ্যা নিয়ন্ত্রণ করুন।' },
  { id: 'hospital',       title: 'হাসপাতাল শয্যা ব্যবস্থাপনা',    desc: 'হাসপাতালের শয্যা সংকট ও বিকল্প হাসপাতালে রোগী স্থানান্তরের তথ্য দেখুন।' },
  { id: 'redistribution', title: 'আন্তঃওয়ার্ড সম্পদ পুনর্বণ্টন', desc: 'এক ওয়ার্ডের অতিরিক্ত সম্পদ অন্য ওয়ার্ডের ঘাটতি পূরণে ব্যবহারের পরিকল্পনা দেখুন।' },
  { id: 'alerts',         title: 'সম্পদ ঘাটতি ও সতর্কতা',         desc: 'গুরুতর সম্পদ সংকট এবং ঝুঁকিপূর্ণ ওয়ার্ডগুলো পর্যবেক্ষণ করুন।' },
  { id: 'mosquito',       title: 'মশক নিধন কার্যক্রম',              desc: 'বরাদ্দকৃত মশক নিধন দল ও কার্যক্রমের সময়সূচি দেখুন।' },
  { id: 'dispatch',       title: 'জরুরি বার্তা ও প্রতিবেদন',      desc: 'ওয়ার্ডভিত্তিক WhatsApp বার্তা এবং কমিশনারের জন্য PDF প্রতিবেদন দেখুন।' },
];

// ── Reusable sub-components ────────────────────────────────────────────────
function Breadcrumb({ current, onHome }) {
  return (
    <nav className="flex items-center gap-1.5 text-sm mb-5 text-slate-500">
      <button onClick={onHome} className="flex items-center gap-1 text-[#006A4E] font-semibold hover:underline">
        <Home className="w-3.5 h-3.5" /> হোম
      </button>
      <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
      <span className="text-slate-700 font-medium">{current}</span>
    </nav>
  );
}

function PageHeader({ title, desc, color = '#006A4E' }) {
  return (
    <div className="rounded-2xl p-6 mb-6 text-white" style={{ background: `linear-gradient(135deg, ${color} 0%, ${color}cc 100%)` }}>
      <h2 className="text-xl font-bold mb-1">{title}</h2>
      {desc && <p className="text-sm opacity-85">{desc}</p>}
    </div>
  );
}

function StatusBadge({ pct }) {
  if (pct >= 100) return <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-green-100 text-green-700">✅ পর্যাপ্ত</span>;
  if (pct >= 70)  return <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">🟡 আংশিক ঘাটতি</span>;
  return                 <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-700">🔴 গুরুতর ঘাটতি</span>;
}

function ProgBar({ pct }) {
  const color = pct >= 100 ? '#22c55e' : pct >= 70 ? '#f59e0b' : '#ef4444';
  return (
    <div className="h-2 bg-slate-200 rounded-full overflow-hidden mt-1">
      <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(100, pct)}%`, background: color }} />
    </div>
  );
}

export default function App() {
  const [lang, setLang] = useState('bn');
  const [activeView, setActiveView] = useState('home');

  // Scarcity state
  const [stockPercentage, setStockPercentage] = useState(100);
  const [totalCrews, setTotalCrews] = useState(150);
  const [controlsExpanded, setControlsExpanded] = useState(false);

  // Ward selection
  const [selectedCityCorp, setSelectedCityCorp] = useState('Dhaka North');
  const [selectedWardId, setSelectedWardId] = useState('DNCC_Ward_01');
  const [wardSearchQuery, setWardSearchQuery] = useState('');

  // Data state
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [allocationData, setAllocationData] = useState(null);

  // 60-ward table filters
  const [searchTerm, setSearchTerm] = useState('');
  const [cityFilter, setCityFilter] = useState('ALL');
  const [riskFilter, setRiskFilter] = useState('ALL');
  const [shortageFilter, setShortageFilter] = useState('ALL');
  const [sortField, setSortField] = useState('priority_ranking');
  const [sortOrder, setSortOrder] = useState('asc');

  // Manual edits
  const [manualAllocations, setManualAllocations] = useState({});
  const [manualCrews, setManualCrews] = useState({});
  const [approvalModalOpen, setApprovalModalOpen] = useState(false);
  const [approvalStatus, setApprovalStatus] = useState(null);

  // Counterfactual
  const [simWardId, setSimWardId] = useState('DNCC_Ward_01');
  const [simCrews, setSimCrews] = useState(4);
  const [simLarvicide, setSimLarvicide] = useState(85);
  const [counterfactualResult, setCounterfactualResult] = useState(null);

  // Audit
  const [auditLogs, setAuditLogs] = useState([]);
  const [notifications, setNotifications] = useState([]);

  // Hospital routing
  const [hospitalRoutingData, setHospitalRoutingData] = useState(null);
  const [hospitalSimCity, setHospitalSimCity] = useState('Chattogram');
  const [hospitalSimWard, setHospitalSimWard] = useState('CCC_Ward_01');
  const [hospitalCustomDemand, setHospitalCustomDemand] = useState({});
  const [hospitalCustomCapacity, setHospitalCustomCapacity] = useState({});
  const [hospitalSimulatorOpen, setHospitalSimulatorOpen] = useState(false);
  const [hospitalNoticesOpen, setHospitalNoticesOpen] = useState(false);
  const [hospitalTableSearch, setHospitalTableSearch] = useState('');
  const [hospitalTableCity, setHospitalTableCity] = useState('ALL');
  const [hospitalTableStatus, setHospitalTableStatus] = useState('ALL');
  const [hospitalTableSort, setHospitalTableSort] = useState('priority_score');
  const [hospitalTableSortAsc, setHospitalTableSortAsc] = useState(false);
  const [approvedHospitalPlanMsg, setApprovedHospitalPlanMsg] = useState(null);
  const [copiedNoticeId, setCopiedNoticeId] = useState(null);

  // Map
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);

  // What-If Simulator
  const [simScenarioName, setSimScenarioName] = useState('Scenario Alpha');
  const [simForecastHorizon, setSimForecastHorizon] = useState(2);
  const [simTotalCrews, setSimTotalCrews] = useState(150);
  const [simStockPct, setSimStockPct] = useState(100);
  const [simResponseModel, setSimResponseModel] = useState('saturation');
  const [simCityFilter, setSimCityFilter] = useState('ALL');
  const [simSelectedWards, setSimSelectedWards] = useState({});
  const [simRunning, setSimRunning] = useState(false);
  const [simResult, setSimResult] = useState(null);
  const [simError, setSimError] = useState(null);
  const [simApproveMsg, setSimApproveMsg] = useState(null);
  const [simRoiTableSort, setSimRoiTableSort] = useState({ field: 'roi', asc: false });
  const [simRoiCityFilter, setSimRoiCityFilter] = useState('ALL');
  const [simDispatchCopied, setSimDispatchCopied] = useState(false);
  const [simOptimizing, setSimOptimizing] = useState(false);
  const [simSavedScenarios, setSimSavedScenarios] = useState([]);

  // ── API calls ────────────────────────────────────────────────────────────
  const fetchAllocation = async (stock = stockPercentage, crews = totalCrews, customManual = null) => {
    try {
      setSimulating(true);
      let res;
      if (customManual && (Object.keys(customManual.allocations || {}).length > 0 || Object.keys(customManual.crews || {}).length > 0)) {
        res = await fetch('/api/allocation/simulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ stock_percentage: stock, total_spraying_crews: crews, manual_allocations: customManual.allocations, manual_crews: customManual.crews }),
        });
      } else {
        res = await fetch(`/api/allocation/current?stock_percentage=${stock}&total_crews=${crews}`);
      }
      const data = await res.json();
      setAllocationData(data);
      if (data.hospital_routing) setHospitalRoutingData(data.hospital_routing);
    } catch (err) { console.error('Failed to load allocation data:', err); }
    finally { setSimulating(false); setLoading(false); }
  };

  const fetchHospitalRouting = async (stock = stockPercentage, customDemand = null, customCapacity = null) => {
    try {
      setSimulating(true);
      let res;
      if (customDemand || customCapacity) {
        res = await fetch('/api/hospital-routing/simulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ stock_percentage: stock, custom_bed_demand: customDemand || {}, custom_bed_capacity: customCapacity || {}, scenario_name: 'Interactive Hospital Surge Simulation' }),
        });
      } else {
        res = await fetch(`/api/hospital-routing/current?stock_percentage=${stock}`);
      }
      const data = await res.json();
      setHospitalRoutingData(data);
    } catch (err) { console.error('Failed to load hospital routing data:', err); }
    finally { setSimulating(false); }
  };

  const handleApproveHospitalPlan = async () => {
    try {
      setSimulating(true);
      const res = await fetch('/api/hospital-routing/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan_name: `Government Hospital Routing Plan (${stockPercentage}% Capacity)`, approved_by: 'Central Health Administrator', stock_percentage: stockPercentage, custom_bed_demand: Object.keys(hospitalCustomDemand).length > 0 ? hospitalCustomDemand : null, custom_bed_capacity: Object.keys(hospitalCustomCapacity).length > 0 ? hospitalCustomCapacity : null }),
      });
      const data = await res.json();
      setApprovedHospitalPlanMsg(data.message || 'Hospital routing plan approved.');
      fetchAuditLogs();
      setTimeout(() => setApprovedHospitalPlanMsg(null), 6000);
    } catch (err) { console.error('Failed to approve hospital plan:', err); }
    finally { setSimulating(false); }
  };

  useEffect(() => { fetchAllocation(100, 150); fetchAuditLogs(); fetchNotifications(); }, []);

  const fetchAuditLogs = async () => {
    try { const res = await fetch('/api/allocation/audit-logs?limit=50'); const data = await res.json(); setAuditLogs(data.logs || []); } catch (e) { console.error(e); }
  };
  const fetchNotifications = async () => {
    try { const res = await fetch(`/api/allocation/notifications?stock_percentage=${stockPercentage}&total_crews=${totalCrews}`); const data = await res.json(); setNotifications(data.notifications || []); } catch (e) { console.error(e); }
  };

  const runCounterfactual = async (wardId = simWardId, crews = simCrews, larv = simLarvicide) => {
    try {
      const res = await fetch('/api/allocation/counterfactual', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ward_id: wardId, crews_assigned: crews, larvicide_coverage_pct: larv }) });
      const data = await res.json(); setCounterfactualResult(data);
    } catch (e) { console.error('Counterfactual simulation failed:', e); }
  };

  useEffect(() => { if (allocationData?.wards?.length > 0) runCounterfactual(allocationData.wards[0].ward_id, 4, 85); }, [allocationData?.wards]);

  const handleApprovePlan = async () => {
    try {
      const res = await fetch('/api/allocation/approve', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ plan_name: `National Dengue Response Plan (${stockPercentage}% Stock)`, approved_by: 'Central Health Administrator', stock_percentage: stockPercentage, total_spraying_crews: totalCrews, manual_allocations: manualAllocations, manual_crews: manualCrews }) });
      const data = await res.json(); setApprovalStatus(data); fetchAuditLogs();
    } catch (e) { console.error('Plan approval failed:', e); }
  };

  const handleApproveRedistribution = async (rec) => {
    try {
      const res = await fetch('/api/allocation/redistribute', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ resource_type: rec.resource_type, source_ward_id: rec.source_ward_id, destination_ward_id: rec.destination_ward_id, quantity: rec.recommended_transfer_quantity, reason: rec.reason, user: 'Central Health Administrator' }) });
      await res.json();
      alert(`স্থানান্তর অনুমোদিত: ${rec.recommended_transfer_quantity} ইউনিট ${rec.resource_type} ${rec.source_ward_id} থেকে ${rec.destination_ward_id}-তে পাঠানো হয়েছে।`);
      fetchAllocation(); fetchAuditLogs();
    } catch (e) { console.error(e); }
  };

  const runWhatIfSimulation = async () => {
    try {
      setSimRunning(true); setSimError(null); setSimApproveMsg(null);
      const larvicide_crews = {}; const fogging_crews = {}; const selectedWardsList = [];
      Object.entries(simSelectedWards).forEach(([wid, crews]) => {
        const l = parseInt(crews.larvicide_crews || 0, 10); const f = parseInt(crews.fogging_crews || 0, 10);
        if (l > 0 || f > 0) { selectedWardsList.push(wid); if (l > 0) larvicide_crews[wid] = l; if (f > 0) fogging_crews[wid] = f; }
      });
      const res = await fetch('/api/simulator/run', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario_name: simScenarioName, forecast_horizon_weeks: simForecastHorizon, deployment_start_week: 1, total_available_crews: simTotalCrews, stock_percentage: simStockPct, selected_ward_ids: selectedWardsList.length > 0 ? selectedWardsList : null, larvicide_crews, fogging_crews, response_model: simResponseModel }) });
      if (!res.ok) { const errData = await res.json(); throw new Error(errData.detail || 'Simulation execution failed'); }
      const data = await res.json(); setSimResult(data);
    } catch (err) { console.error(err); setSimError(err.message); }
    finally { setSimRunning(false); }
  };

  const optimizeCrews = async (type = 'larvicide') => {
    try {
      setSimOptimizing(true); setSimError(null);
      const res = await fetch('/api/simulator/optimize', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ available_crews: simTotalCrews, intervention_type: type, horizon_weeks: simForecastHorizon }) });
      if (!res.ok) throw new Error('Crew optimization failed');
      const data = await res.json(); const updated = { ...simSelectedWards }; const alloc = data.ward_allocation || {};
      Object.entries(alloc).forEach(([wid, count]) => { updated[wid] = { larvicide_crews: type === 'larvicide' ? count : (updated[wid]?.larvicide_crews || 0), fogging_crews: type === 'fogging' ? count : (updated[wid]?.fogging_crews || 0) }; });
      setSimSelectedWards(updated); setSimScenarioName(`ROI-Optimized ${type.toUpperCase()} Deployment`);
      alert(`গ্রিডি অপটিমাইজেশন সম্পন্ন: ${data.total_cases_prevented} আনুমানিক কেস প্রতিরোধ ${data.available_crews} দল দিয়ে।`);
    } catch (err) { console.error(err); setSimError(err.message); }
    finally { setSimOptimizing(false); }
  };

  const approveVectorPlan = async () => {
    if (!simResult) return;
    try {
      const res = await fetch('/api/simulator/approve', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ plan_name: simScenarioName, approved_by: 'Central Health Administrator', simulation_result: simResult }) });
      const data = await res.json(); setSimApproveMsg(data.message); fetchAuditLogs();
    } catch (err) { console.error(err); setSimError('Failed to approve plan.'); }
  };

  // Map setup
  useEffect(() => {
    if (activeView === 'map' && allocationData?.wards && mapContainerRef.current) {
      if (!mapInstanceRef.current) {
        const map = L.map(mapContainerRef.current).setView([23.8103, 90.4125], 11);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { attribution: '&copy; OpenStreetMap contributors &copy; CARTO', maxZoom: 19 }).addTo(map);
        mapInstanceRef.current = map;
      }
      const map = mapInstanceRef.current;
      map.eachLayer((layer) => { if (layer instanceof L.CircleMarker) map.removeLayer(layer); });
      allocationData.wards.forEach((w) => {
        const color = w.risk_level === 'High' ? '#EF4444' : w.risk_level === 'Medium' ? '#F59E0B' : '#10B981';
        const hasShortage = w.has_critical_deficit;
        const marker = L.circleMarker([w.lat, w.lon], { radius: Math.min(18, Math.max(6, w.total_predicted_cases * 1.8)), fillColor: color, color: hasShortage ? '#DC2626' : '#FFFFFF', weight: hasShortage ? 2.5 : 1, opacity: 1, fillOpacity: 0.75 }).addTo(map);
        marker.bindPopup(`<div style="font-family:sans-serif;font-size:12px;color:#1e293b;"><div style="font-weight:700;font-size:14px;margin-bottom:4px;color:${color};">#${w.priority_ranking} — ${w.ward_id} (${w.locality})</div><div><b>সিটি:</b> ${w.city}</div><div><b>অগ্রাধিকার স্কোর:</b> ${w.priority_score.toFixed(4)}</div><div><b>২-সপ্তাহ কেস:</b> ${w.total_predicted_cases} (ঝুঁকি: ${w.risk_level})</div><hr style="border:0.5px solid #e2e8f0;margin:6px 0;"/><div><b>স্যালাইন:</b> ${w.approved_saline_allocation}/${w.saline_demand} (${w.saline_fulfillment_pct}%)</div><div><b>টেস্ট কিট:</b> ${w.approved_kits_allocation}/${w.kits_demand} (${w.kits_fulfillment_pct}%)</div><div><b>শয্যা:</b> ${w.approved_beds_allocation}/${w.beds_demand} (${w.beds_fulfillment_pct}%)</div><div><b>মশক দল:</b> ${w.approved_crew_allocation}/${w.required_crews}</div>${hasShortage ? '<div style="color:#EF4444;font-weight:700;margin-top:4px;">⚠️ সম্পদ ঘাটতি রয়েছে</div>' : '<div style="color:#10B981;font-weight:700;margin-top:4px;">✓ সকল সম্পদ পর্যাপ্ত</div>'}</div>`);
      });
    }
  }, [activeView, allocationData]);

  const filteredWards = useMemo(() => {
    if (!allocationData?.wards) return [];
    return allocationData.wards.filter((w) => {
      const matchesSearch = w.ward_id.toLowerCase().includes(searchTerm.toLowerCase()) || w.locality.toLowerCase().includes(searchTerm.toLowerCase()) || w.city.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesCity = cityFilter === 'ALL' || w.city === cityFilter;
      const matchesRisk = riskFilter === 'ALL' || w.risk_level === riskFilter;
      const matchesShortage = shortageFilter === 'ALL' || (shortageFilter === 'CRITICAL' && w.has_critical_deficit) || (shortageFilter === 'CREW_SHORTAGE' && w.has_crew_shortage);
      return matchesSearch && matchesCity && matchesRisk && matchesShortage;
    }).sort((a, b) => {
      let valA = a[sortField]; let valB = b[sortField];
      if (typeof valA === 'string') return sortOrder === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
      return sortOrder === 'asc' ? valA - valB : valB - valA;
    });
  }, [allocationData, searchTerm, cityFilter, riskFilter, shortageFilter, sortField, sortOrder]);

  const overview = allocationData?.regional_overview || {};
  const scarcity = allocationData?.scarcity_controls || {};

  const citySummaryData = useMemo(() => {
    if (!allocationData?.wards) return [];
    const grouped = {};
    allocationData.wards.forEach((w) => {
      if (!grouped[w.city]) grouped[w.city] = { city: w.city, cases: 0, salineDemand: 0, salineAlloc: 0, kitsDemand: 0, kitsAlloc: 0, crewsReq: 0, crewsAssigned: 0 };
      grouped[w.city].cases += w.total_predicted_cases; grouped[w.city].salineDemand += w.saline_demand; grouped[w.city].salineAlloc += w.approved_saline_allocation; grouped[w.city].kitsDemand += w.kits_demand; grouped[w.city].kitsAlloc += w.approved_kits_allocation; grouped[w.city].crewsReq += w.required_crews; grouped[w.city].crewsAssigned += w.approved_crew_allocation;
    });
    return Object.values(grouped);
  }, [allocationData]);

  const fmt = (val, dec = null) => (lang === 'bn' ? toBangla(val, dec) : (dec !== null ? Number(val || 0).toFixed(dec) : (val || 0)));

  // ── Loading Screen ────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#F4F7F4] text-slate-800">
        <Activity className="w-12 h-12 text-[#006A4E] animate-spin mb-4" />
        <h2 className="text-xl font-bold tracking-wider text-[#006A4E]">এডিস বিদায় — লোড হচ্ছে...</h2>
        <p className="text-sm text-slate-500 mt-1">৬০টি ওয়ার্ডের ডেঙ্গু পূর্বাভাস ও জরুরি সম্পদ বণ্টন প্রক্রিয়াধীন...</p>
      </div>
    );
  }

  // ── Shared: green status colors for ward cards ───────────────────────────
  const getStatusColor = (pct) => {
    if (pct >= 100) return { bar: 'bg-emerald-500', text: 'text-emerald-600', label: 'পর্যাপ্ত', badge: 'bg-green-100 text-green-700', borderClass: 'border-emerald-200' };
    if (pct >= 70)  return { bar: 'bg-amber-400',   text: 'text-amber-600',   label: 'আংশিক ঘাটতি', badge: 'bg-amber-100 text-amber-700', borderClass: 'border-amber-200' };
    return                 { bar: 'bg-red-500',     text: 'text-red-600',     label: 'গুরুতর ঘাটতি', badge: 'bg-red-100 text-red-700', borderClass: 'border-red-200' };
  };

  // ═══════════════════════════════════════════════════════════════════════════
  // VIEWS
  // ═══════════════════════════════════════════════════════════════════════════

  // ── HOME VIEW ─────────────────────────────────────────────────────────────
  const HomeView = () => (
    <div className="space-y-8">
      {/* Regional Summary */}
      <div>
        <h2 className="text-center text-2xl font-bold text-[#006A4E] mb-1">সামগ্রিক পরিস্থিতি</h2>
        <p className="text-center text-sm text-slate-500 mb-5">৫টি সিটি কর্পোরেশন • ৬০টি ওয়ার্ড — লাইভ পূর্বাভাস ও সম্পদ অবস্থা</p>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {/* Cases */}
          <div className="bg-white border border-slate-200 rounded-2xl p-4 text-center shadow-sm hover:shadow-md transition">
            <div className="text-2xl mb-2">🩺</div>
            <div className="text-2xl font-black text-[#006A4E]">{fmt(Math.round(overview.total_predicted_cases || 0))}</div>
            <div className="text-xs text-slate-500 mt-1">আগামী ২ সপ্তাহে সম্ভাব্য রোগী</div>
            <span className="inline-block mt-2 text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">{fmt(overview.high_risk_wards_count || 0)} উচ্চ ঝুঁকির ওয়ার্ড</span>
          </div>
          {/* Saline */}
          <div className="bg-white border border-slate-200 rounded-2xl p-4 text-center shadow-sm hover:shadow-md transition">
            <div className="text-2xl mb-2">💧</div>
            <div className="text-2xl font-black text-[#006A4E]">{fmt(overview.total_saline_allocated || 0)}</div>
            <div className="text-xs text-slate-500 mt-1">মোট স্যালাইন ব্যাগ বরাদ্দ</div>
            <span className={`inline-block mt-2 text-[10px] font-bold px-2 py-0.5 rounded-full ${overview.total_saline_deficit > 0 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>{overview.total_saline_deficit > 0 ? `ঘাটতি: ${fmt(overview.total_saline_deficit)}` : 'পর্যাপ্ত'}</span>
          </div>
          {/* Kits */}
          <div className="bg-white border border-slate-200 rounded-2xl p-4 text-center shadow-sm hover:shadow-md transition">
            <div className="text-2xl mb-2">🧪</div>
            <div className="text-2xl font-black text-[#006A4E]">{fmt(overview.total_kits_allocated || 0)}</div>
            <div className="text-xs text-slate-500 mt-1">মোট ডেঙ্গু টেস্ট কিট</div>
            <span className={`inline-block mt-2 text-[10px] font-bold px-2 py-0.5 rounded-full ${overview.total_kits_deficit > 0 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>{overview.total_kits_deficit > 0 ? `ঘাটতি: ${fmt(overview.total_kits_deficit)}` : 'পর্যাপ্ত'}</span>
          </div>
          {/* Beds */}
          <div className="bg-white border border-slate-200 rounded-2xl p-4 text-center shadow-sm hover:shadow-md transition">
            <div className="text-2xl mb-2">🛏️</div>
            <div className="text-2xl font-black text-[#006A4E]">{fmt(overview.total_beds_allocated || 0)}</div>
            <div className="text-xs text-slate-500 mt-1">মোট হাসপাতাল শয্যা</div>
            <span className={`inline-block mt-2 text-[10px] font-bold px-2 py-0.5 rounded-full ${overview.total_beds_deficit > 0 ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'}`}>{overview.total_beds_deficit > 0 ? `ঘাটতি: ${fmt(overview.total_beds_deficit)}` : 'পর্যাপ্ত শয্যা'}</span>
          </div>
          {/* Crews */}
          <div className="bg-white border border-slate-200 rounded-2xl p-4 text-center shadow-sm hover:shadow-md transition">
            <div className="text-2xl mb-2">🦟</div>
            <div className="text-2xl font-black text-[#006A4E]">{fmt(overview.total_assigned_crews || 0)}</div>
            <div className="text-xs text-slate-500 mt-1">মোট মশক নিধন দল</div>
            <span className={`inline-block mt-2 text-[10px] font-bold px-2 py-0.5 rounded-full ${overview.total_crew_shortage > 0 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>{overview.total_crew_shortage > 0 ? `ঘাটতি: ${fmt(overview.total_crew_shortage)}` : 'সবাই নিয়োজিত'}</span>
          </div>
          {/* Deficit Wards */}
          <div className={`border rounded-2xl p-4 text-center shadow-sm hover:shadow-md transition ${(overview.critical_supply_wards_count || 0) > 0 ? 'bg-red-50 border-red-200' : 'bg-white border-slate-200'}`}>
            <div className="text-2xl mb-2">⚠️</div>
            <div className={`text-2xl font-black ${(overview.critical_supply_wards_count || 0) > 0 ? 'text-red-600' : 'text-green-600'}`}>{fmt(overview.critical_supply_wards_count || 0)}</div>
            <div className="text-xs text-slate-500 mt-1">ঘাটতিতে থাকা মোট ওয়ার্ড</div>
            <span className={`inline-block mt-2 text-[10px] font-bold px-2 py-0.5 rounded-full ${(overview.critical_supply_wards_count || 0) > 0 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>{(overview.critical_supply_wards_count || 0) > 0 ? 'জরুরি মনোযোগ প্রয়োজন' : 'সব সম্পদ পর্যাপ্ত'}</span>
          </div>
        </div>
      </div>

      {/* Feature Cards */}
      <div>
        <h2 className="text-center text-2xl font-bold text-[#006A4E] mb-1">আমাদের সেবাসমূহ</h2>
        <p className="text-center text-sm text-slate-500 mb-5">একটি কার্ডে ক্লিক করুন — সেই মডিউলের বিস্তারিত দেখুন</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURE_CARDS.map((card) => {
            const s = CARD_STYLES[card.id];
            return (
              <button
                key={card.id}
                onClick={() => setActiveView(card.id)}
                className={`${s.bg} border-t-4 ${s.border} rounded-2xl p-5 text-left hover:shadow-lg transition-all duration-200 hover:-translate-y-1 relative group`}
              >
                <div className={`w-12 h-12 ${s.iconBg} rounded-xl flex items-center justify-center text-2xl mb-3 shadow-sm`}>{s.icon}</div>
                <div className="font-bold text-slate-800 text-[15px] mb-1">{card.title}</div>
                <div className="text-xs text-slate-500 leading-relaxed pr-6">{card.desc}</div>
                <span className={`absolute bottom-4 right-4 text-lg ${s.iconColor} opacity-50 group-hover:opacity-100 transition font-bold`}>→</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );

  // ── FORECAST VIEW ─────────────────────────────────────────────────────────
  const ForecastView = () => {
    const topWards = (allocationData?.wards || []).slice(0, 10);
    return (
      <div>
        <Breadcrumb current={bn.forecast} onHome={() => setActiveView('home')} />
        <PageHeader title="📈 ডেঙ্গু পূর্বাভাস" desc="আগামী ২ সপ্তাহের ওয়ার্ডভিত্তিক ডেঙ্গু পূর্বাভাস ও ঝুঁকির স্তর — বিদ্যমান ML মডেল থেকে" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {[
            { label: 'মোট পূর্বাভাস রোগী', val: fmt(Math.round(overview.total_predicted_cases || 0)), sub: 'আগামী ২ সপ্তাহ', color: 'text-rose-600' },
            { label: 'উচ্চ ঝুঁকির ওয়ার্ড', val: fmt(overview.high_risk_wards_count || 0), sub: 'High Risk', color: 'text-orange-600' },
            { label: 'মাঝারি ঝুঁকির ওয়ার্ড', val: fmt(overview.medium_risk_wards_count || 0), sub: 'Medium Risk', color: 'text-amber-600' },
            { label: 'নিম্ন ঝুঁকির ওয়ার্ড', val: fmt(60 - (overview.high_risk_wards_count || 0) - (overview.medium_risk_wards_count || 0)), sub: 'Low Risk', color: 'text-green-600' },
          ].map((k, i) => (
            <div key={i} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
              <div className="text-xs text-slate-500 mb-1">{k.label}</div>
              <div className={`text-3xl font-black ${k.color}`}>{k.val}</div>
              <div className="text-[10px] text-slate-400 mt-1">{k.sub}</div>
            </div>
          ))}
        </div>
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm mb-5">
          <h3 className="font-bold text-slate-700 mb-4 text-sm">📊 সিটি কর্পোরেশন অনুযায়ী পূর্বাভাস চার্ট</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={citySummaryData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="city" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} />
                <Tooltip contentStyle={{ backgroundColor: '#fff', borderColor: '#e2e8f0', fontSize: '12px' }} />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                <Bar dataKey="cases" fill="#006A4E" name="সম্ভাব্য রোগী" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 font-bold text-slate-700 text-sm">🏆 শীর্ষ ১০ অগ্রাধিকার ওয়ার্ড</div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500 font-bold">
                <tr><th className="px-4 py-3">ক্রম</th><th className="px-4 py-3">ওয়ার্ড</th><th className="px-4 py-3">ঝুঁকি</th><th className="px-4 py-3">সম্ভাব্য রোগী</th><th className="px-4 py-3">অগ্রাধিকার স্কোর</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {topWards.map((w) => (
                  <tr key={w.ward_id} className="hover:bg-slate-50 transition">
                    <td className="px-4 py-3"><span className="font-bold text-[#006A4E]">#{w.priority_ranking}</span></td>
                    <td className="px-4 py-3"><div className="font-semibold text-slate-800">{w.ward_id}</div><div className="text-xs text-slate-400">{w.locality} • {w.city}</div></td>
                    <td className="px-4 py-3"><span className={`text-xs font-bold px-2 py-0.5 rounded-full ${w.risk_level === 'High' ? 'bg-red-100 text-red-700' : w.risk_level === 'Medium' ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'}`}>{translateRisk(w.risk_level)}</span></td>
                    <td className="px-4 py-3 font-bold text-slate-800">{fmt(w.total_predicted_cases)}</td>
                    <td className="px-4 py-3 font-mono text-[#006A4E] font-bold">{w.priority_score?.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  // ── ALLOCATION VIEW ───────────────────────────────────────────────────────
  const AllocationView = () => {
    const allWards = allocationData?.wards || [];
    const uniqueCities = Array.from(new Set(allWards.map((w) => w.city))).sort();
    const cityWards = allWards.filter((w) => {
      const matchesCity = selectedCityCorp === 'ALL' || w.city === selectedCityCorp;
      const matchesSearch = !wardSearchQuery || w.ward_id.toLowerCase().includes(wardSearchQuery.toLowerCase()) || (w.locality || '').toLowerCase().includes(wardSearchQuery.toLowerCase());
      return matchesCity && matchesSearch;
    });
    const selectedWard = allWards.find((w) => w.ward_id === selectedWardId) || cityWards[0] || allWards[0];
    const wardRedistributions = (allocationData?.redistribution_recommendations || []).filter((r) => selectedWard && (r.source_ward_id === selectedWard.ward_id || r.destination_ward_id === selectedWard.ward_id));
    const wardHospitalTransfers = (hospitalRoutingData?.routing_assignments || []).filter((r) => selectedWard && (r.source_ward_id === selectedWard.ward_id || r.destination_ward_id === selectedWard.ward_id));
    const wardDeficits = selectedWard ? [
      selectedWard.remaining_saline_deficit > 0 && { name: 'স্যালাইন ব্যাগ', req: selectedWard.saline_demand, alloc: selectedWard.approved_saline_allocation, def: selectedWard.remaining_saline_deficit, pct: selectedWard.saline_fulfillment_pct },
      selectedWard.remaining_kits_deficit > 0 && { name: 'ডেঙ্গু টেস্ট কিট', req: selectedWard.kits_demand, alloc: selectedWard.approved_kits_allocation, def: selectedWard.remaining_kits_deficit, pct: selectedWard.kits_fulfillment_pct },
      selectedWard.remaining_beds_deficit > 0 && { name: 'হাসপাতাল শয্যা', req: selectedWard.beds_demand, alloc: selectedWard.approved_beds_allocation, def: selectedWard.remaining_beds_deficit, pct: selectedWard.beds_fulfillment_pct },
      selectedWard.crew_deficit > 0 && { name: 'মশক নিধন দল', req: selectedWard.required_crews, alloc: selectedWard.approved_crew_allocation, def: selectedWard.crew_deficit, pct: selectedWard.crew_fulfillment_pct },
    ].filter(Boolean) : [];

    return (
      <div>
        <Breadcrumb current={bn.allocation} onHome={() => setActiveView('home')} />
        <PageHeader title="📦 ওয়ার্ডভিত্তিক সম্পদ বরাদ্দ" desc="সিটি কর্পোরেশন ও ওয়ার্ড নির্বাচন করুন — সম্পদের চাহিদা, বরাদ্দ ও ঘাটতির বিস্তারিত তথ্য" color="#7c3aed" />

        {/* Ward Selector */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm mb-5">
          <h3 className="font-bold text-[#006A4E] mb-4 flex items-center gap-2"><MapPin className="w-4 h-4" /> ওয়ার্ড নির্বাচন করুন</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1.5">সিটি কর্পোরেশন নির্বাচন করুন</label>
              <select value={selectedCityCorp} onChange={(e) => { const c = e.target.value; setSelectedCityCorp(c); const f = allWards.find((w) => c === 'ALL' || w.city === c); if (f) setSelectedWardId(f.ward_id); }} className="w-full border border-slate-300 rounded-xl px-3 py-2.5 text-sm text-slate-700 focus:border-[#006A4E] focus:outline-none focus:ring-2 focus:ring-[#006A4E]/20 bg-white">
                <option value="ALL">সব সিটি কর্পোরেশন ({toBangla(60)}টি ওয়ার্ড)</option>
                {uniqueCities.map((city) => <option key={city} value={city}>{translateCity(city)}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1.5">ওয়ার্ড অনুসন্ধান করুন</label>
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input type="text" placeholder="ওয়ার্ড আইডি বা এলাকার নাম..." value={wardSearchQuery} onChange={(e) => setWardSearchQuery(e.target.value)} className="w-full border border-slate-300 rounded-xl pl-9 pr-3 py-2.5 text-sm text-slate-700 focus:border-[#006A4E] focus:outline-none focus:ring-2 focus:ring-[#006A4E]/20" />
              </div>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1.5">ওয়ার্ড নির্বাচন করুন</label>
              <select value={selectedWard?.ward_id || ''} onChange={(e) => setSelectedWardId(e.target.value)} className="w-full border border-slate-300 rounded-xl px-3 py-2.5 text-sm text-slate-700 focus:border-[#006A4E] focus:outline-none focus:ring-2 focus:ring-[#006A4E]/20 bg-white">
                {cityWards.map((w) => <option key={w.ward_id} value={w.ward_id}>{w.ward_id} — {w.locality} ({translateRisk(w.risk_level)})</option>)}
              </select>
            </div>
          </div>
        </div>

        {/* Ward Detail */}
        {selectedWard && (
          <div className="space-y-5">
            {/* Ward Banner */}
            <div className="bg-[#f0fdf4] border border-[#bbf7d0] rounded-2xl p-5 flex flex-wrap items-center justify-between gap-4">
              <div>
                <h3 className="text-lg font-bold text-[#006A4E]">🏘️ {selectedWard.locality} ({selectedWard.ward_id})</h3>
                <p className="text-sm text-slate-500 mt-1">{translateCity(selectedWard.city)} • অগ্রাধিকার স্কোর: <strong className="text-[#006A4E]">{selectedWard.priority_score?.toFixed(4)}</strong> • ক্রম: <strong className="text-[#006A4E]">{toBangla(selectedWard.priority_ranking)}</strong>-তম</p>
              </div>
              <div className="flex items-center gap-3">
                <span className={`px-4 py-1.5 rounded-full font-bold text-sm border-2 ${selectedWard.risk_level === 'High' ? 'bg-red-50 text-red-700 border-red-200' : selectedWard.risk_level === 'Medium' ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-green-50 text-green-700 border-green-200'}`}>{translateRisk(selectedWard.risk_level)}</span>
              </div>
            </div>

            {/* Resource Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Cases */}
              <div className="bg-white border-t-4 border-rose-400 border border-slate-200 rounded-xl p-4 shadow-sm">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-600"><Activity className="w-4 h-4 text-rose-500" /> সম্ভাব্য ডেঙ্গু রোগী</div>
                  <span className="text-[10px] bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">আগামী ২ সপ্তাহ</span>
                </div>
                <div className="text-3xl font-black text-slate-800">{toBangla(selectedWard.total_predicted_cases)} <span className="text-sm font-normal text-slate-400">জন</span></div>
                <div className="text-xs text-slate-400 mt-2 flex gap-4"><span>সপ্তাহ ১: <b className="text-slate-600">{toBangla(selectedWard.predicted_cases_w1)}</b></span><span>সপ্তাহ ২: <b className="text-slate-600">{toBangla(selectedWard.predicted_cases_w2)}</b></span></div>
              </div>

              {/* Saline */}
              {(() => { const st = getStatusColor(selectedWard.saline_fulfillment_pct); return (
                <div className={`bg-white border-t-4 border-blue-400 border border-slate-200 rounded-xl p-4 shadow-sm`}>
                  <div className="flex items-center justify-between mb-3"><div className="flex items-center gap-2 text-sm font-semibold text-slate-600"><TestTube className="w-4 h-4 text-blue-500" /> স্যালাইন ব্যাগ</div><StatusBadge pct={selectedWard.saline_fulfillment_pct} /></div>
                  <div className="text-2xl font-bold text-slate-800">{toBangla(selectedWard.approved_saline_allocation)} <span className="text-sm font-normal text-slate-400">/ {toBangla(selectedWard.saline_demand)} (চাহিদা)</span></div>
                  <ProgBar pct={selectedWard.saline_fulfillment_pct} />
                  <div className="text-xs text-slate-500 mt-1 flex justify-between"><span>পূরণ হার: {toBangla(Math.round(selectedWard.saline_fulfillment_pct))}%</span>{selectedWard.remaining_saline_deficit > 0 && <span className="text-red-500 font-bold">ঘাটতি: {toBangla(selectedWard.remaining_saline_deficit)}</span>}</div>
                </div>
              ); })()}

              {/* Kits */}
              {(() => { return (
                <div className="bg-white border-t-4 border-purple-400 border border-slate-200 rounded-xl p-4 shadow-sm">
                  <div className="flex items-center justify-between mb-3"><div className="flex items-center gap-2 text-sm font-semibold text-slate-600"><Sparkles className="w-4 h-4 text-purple-500" /> ডেঙ্গু টেস্ট কিট</div><StatusBadge pct={selectedWard.kits_fulfillment_pct} /></div>
                  <div className="text-2xl font-bold text-slate-800">{toBangla(selectedWard.approved_kits_allocation)} <span className="text-sm font-normal text-slate-400">/ {toBangla(selectedWard.kits_demand)} (চাহিদা)</span></div>
                  <ProgBar pct={selectedWard.kits_fulfillment_pct} />
                  <div className="text-xs text-slate-500 mt-1 flex justify-between"><span>পূরণ হার: {toBangla(Math.round(selectedWard.kits_fulfillment_pct))}%</span>{selectedWard.remaining_kits_deficit > 0 && <span className="text-red-500 font-bold">ঘাটতি: {toBangla(selectedWard.remaining_kits_deficit)}</span>}</div>
                </div>
              ); })()}

              {/* Beds */}
              {(() => { return (
                <div className="bg-white border-t-4 border-amber-400 border border-slate-200 rounded-xl p-4 shadow-sm">
                  <div className="flex items-center justify-between mb-3"><div className="flex items-center gap-2 text-sm font-semibold text-slate-600"><Bed className="w-4 h-4 text-amber-500" /> হাসপাতাল শয্যা</div><StatusBadge pct={selectedWard.beds_fulfillment_pct} /></div>
                  <div className="text-2xl font-bold text-slate-800">{toBangla(selectedWard.approved_beds_allocation)} <span className="text-sm font-normal text-slate-400">/ {toBangla(selectedWard.beds_demand)} (চাহিদা)</span></div>
                  <ProgBar pct={selectedWard.beds_fulfillment_pct} />
                  <div className="text-xs text-slate-500 mt-1 flex justify-between"><span>পূরণ হার: {toBangla(Math.round(selectedWard.beds_fulfillment_pct))}%</span>{selectedWard.remaining_beds_deficit > 0 && <span className="text-red-500 font-bold">ঘাটতি: {toBangla(selectedWard.remaining_beds_deficit)}</span>}</div>
                </div>
              ); })()}

              {/* Crews */}
              {(() => { return (
                <div className="bg-white border-t-4 border-teal-400 border border-slate-200 rounded-xl p-4 shadow-sm">
                  <div className="flex items-center justify-between mb-3"><div className="flex items-center gap-2 text-sm font-semibold text-slate-600"><Users className="w-4 h-4 text-teal-500" /> মশক নিধন দল</div><StatusBadge pct={selectedWard.crew_fulfillment_pct} /></div>
                  <div className="text-2xl font-bold text-slate-800">{toBangla(selectedWard.approved_crew_allocation)} <span className="text-sm font-normal text-slate-400">/ {toBangla(selectedWard.required_crews)} (প্রয়োজনীয়)</span></div>
                  <ProgBar pct={selectedWard.crew_fulfillment_pct} />
                  <div className="text-xs text-slate-500 mt-1 flex justify-between"><span>পূরণ হার: {toBangla(Math.round(selectedWard.crew_fulfillment_pct))}%</span>{selectedWard.crew_deficit > 0 && <span className="text-red-500 font-bold">ঘাটতি: {toBangla(selectedWard.crew_deficit)}</span>}</div>
                </div>
              ); })()}

              {/* Deficit Summary */}
              <div className={`border-t-4 border border-slate-200 rounded-xl p-4 shadow-sm ${wardDeficits.length > 0 ? 'bg-red-50 border-t-red-500' : 'bg-green-50 border-t-green-500'}`}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-600"><AlertTriangle className={`w-4 h-4 ${wardDeficits.length > 0 ? 'text-red-500' : 'text-green-500'}`} /> সম্পদ ঘাটতি অবস্থা</div>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${wardDeficits.length > 0 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>{wardDeficits.length > 0 ? 'সতর্কতা সক্রিয়' : 'স্বাভাবিক'}</span>
                </div>
                <div className={`text-2xl font-bold ${wardDeficits.length > 0 ? 'text-red-600' : 'text-green-600'}`}>{wardDeficits.length > 0 ? `${toBangla(wardDeficits.length)}টি খাতে ঘাটতি` : 'কোনো ঘাটতি নেই'}</div>
                <div className="text-xs text-slate-500 mt-2">{wardDeficits.length > 0 ? `অভাব রয়েছে: ${wardDeficits.map((d) => d.name).join(', ')}` : 'সকল মেডিকেল সরঞ্জাম পর্যাপ্ত বরাদ্দ রয়েছে।'}</div>
              </div>
            </div>

            {/* Deficit Alerts */}
            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
              <h3 className="font-bold text-slate-700 mb-4 flex items-center gap-2 text-sm"><ShieldAlert className="w-4 h-4 text-red-500" /> সম্পদ ঘাটতি ও জরুরি সতর্কতা</h3>
              {wardDeficits.length === 0 ? (
                <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-center gap-3"><CheckCircle2 className="w-5 h-5 text-green-500 shrink-0" /><span className="text-sm text-green-700 font-medium">সকল সম্পদ পর্যাপ্ত। এই ওয়ার্ডে কোনো ঘাটতি নেই।</span></div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {wardDeficits.map((item, idx) => {
                    const isSevere = item.pct < 70;
                    return (
                      <div key={idx} className={`p-4 rounded-xl border ${isSevere ? 'bg-red-50 border-red-200' : 'bg-amber-50 border-amber-200'}`}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-bold text-slate-800">{item.name}</span>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${isSevere ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>{isSevere ? '🔴 গুরুতর ঘাটতি' : '🟡 আংশিক ঘাটতি'}</span>
                        </div>
                        <div className="text-xs text-slate-600 flex items-center justify-between gap-2">
                          <span>চাহিদা: <b>{toBangla(item.req)}</b></span>
                          <span>বরাদ্দ: <b>{toBangla(item.alloc)}</b></span>
                          <span className="text-red-600 font-bold">ঘাটতি: {toBangla(item.def)}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Redistribution for this ward */}
            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-slate-700 flex items-center gap-2 text-sm"><RefreshCw className="w-4 h-4 text-[#006A4E]" /> এই ওয়ার্ডের পুনর্বণ্টন পরিকল্পনা</h3>
                <button onClick={() => setActiveView('redistribution')} className="text-xs text-[#006A4E] font-semibold hover:underline">সব দেখুন →</button>
              </div>
              {wardRedistributions.length === 0 && wardHospitalTransfers.length === 0 ? (
                <div className="text-center py-6 text-sm text-slate-400 bg-slate-50 rounded-xl">এই ওয়ার্ডের জন্য কোনো পুনর্বণ্টন নির্দেশনা নেই।</div>
              ) : (
                <div className="space-y-3">
                  {wardRedistributions.map((rec, i) => (
                    <div key={i} className="bg-green-50 border border-green-200 rounded-xl p-4 flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-3 flex-wrap">
                        <div className="bg-white rounded-lg px-3 py-2 border border-green-200"><span className="text-[10px] text-slate-400 block">প্রদানকারী</span><span className="text-sm font-bold text-green-700">{rec.source_locality} ({rec.source_ward_id})</span></div>
                        <ArrowRight className="w-5 h-5 text-[#006A4E]" />
                        <div className="bg-white rounded-lg px-3 py-2 border border-green-200"><span className="text-[10px] text-slate-400 block">গ্রহণকারী</span><span className="text-sm font-bold text-amber-700">{rec.destination_locality} ({rec.destination_ward_id})</span></div>
                      </div>
                      <div className="text-right"><span className="text-[10px] text-slate-400 block">{translateResource(rec.resource_type)}</span><span className="text-base font-bold text-[#006A4E]">{toBangla(rec.recommended_transfer_quantity)} টি স্থানান্তর</span></div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  // ── MAP VIEW ──────────────────────────────────────────────────────────────
  const MapView = () => (
    <div>
      <Breadcrumb current={bn.map} onHome={() => setActiveView('home')} />
      <PageHeader title="🗺️ ঝুঁকি ও নজরদারি মানচিত্র" desc="৬০টি ওয়ার্ডের ডেঙ্গু ঝুঁকির ইন্টার‍্যাক্টিভ মানচিত্র" color="#2563eb" />
      <div className="flex items-center justify-end gap-4 text-xs text-slate-500 mb-3 flex-wrap">
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-red-500 inline-block" /> উচ্চ ঝুঁকি</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-amber-500 inline-block" /> মাঝারি ঝুঁকি</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-emerald-500 inline-block" /> নিম্ন ঝুঁকি</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full border-2 border-red-500 bg-transparent inline-block" /> সম্পদ ঘাটতি</span>
      </div>
      <div className="w-full h-[620px] rounded-2xl border border-slate-200 overflow-hidden shadow-lg">
        <div ref={mapContainerRef} className="w-full h-full" />
      </div>
    </div>
  );

  // ── CONTROLS VIEW ─────────────────────────────────────────────────────────
  const ControlsView = () => (
    <div>
      <Breadcrumb current={bn.controls} onHome={() => setActiveView('home')} />
      <PageHeader title="⚙️ আঞ্চলিক সম্পদ নিয়ন্ত্রণ" desc="উপলব্ধ সম্পদের পরিমাণ ও মশক নিধন দলের সংখ্যা নিয়ন্ত্রণ করুন" color="#ca8a04" />
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <div className="flex justify-between items-center text-sm mb-2">
              <span className="font-semibold text-slate-700 flex items-center gap-2"><Layers className="w-4 h-4 text-[#006A4E]" /> আঞ্চলিক সম্পদের প্রাপ্যতা (৩০%–১০০%)</span>
              <span className="font-black text-[#006A4E] text-lg">{fmt(stockPercentage)}%</span>
            </div>
            <input type="range" min="30" max="100" step="5" value={stockPercentage} onChange={(e) => { const val = Number(e.target.value); setStockPercentage(val); fetchAllocation(val, totalCrews); }} className="w-full h-3 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#006A4E]" />
            <div className="flex justify-between text-xs text-slate-400 mt-1"><span>৩০% (তীব্র সংকট)</span><span>৫০%</span><span>৭৫%</span><span className="text-[#006A4E] font-bold">১০০% (পূর্ণ)</span></div>
          </div>
          <div>
            <div className="flex justify-between items-center text-sm mb-2">
              <span className="font-semibold text-slate-700 flex items-center gap-2"><Users className="w-4 h-4 text-blue-600" /> মোট উপলব্ধ মশক নিধন দল</span>
              <span className="font-black text-blue-700 text-lg">{fmt(totalCrews)} দল</span>
            </div>
            <input type="range" min="0" max="300" step="5" value={totalCrews} onChange={(e) => { const val = Number(e.target.value); setTotalCrews(val); fetchAllocation(stockPercentage, val); }} className="w-full h-3 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600" />
            <div className="flex justify-between text-xs text-slate-400 mt-1"><span>০</span><span>৫০</span><span>১৫০</span><span className="text-blue-700 font-bold">৩০০</span></div>
          </div>
        </div>
        <div className="flex justify-end">
          <button onClick={() => fetchAllocation(stockPercentage, totalCrews, { allocations: manualAllocations, crews: manualCrews })} disabled={simulating} className="flex items-center gap-2 px-5 py-2.5 bg-[#006A4E] hover:bg-emerald-800 text-white text-sm font-bold rounded-xl shadow transition">
            <RefreshCw className={`w-4 h-4 ${simulating ? 'animate-spin' : ''}`} /> সম্পদ বণ্টন পুনঃগণনা করুন
          </button>
        </div>
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-center text-sm">
          {[
            { label: 'বর্তমান মজুদ স্তর', val: `${fmt(stockPercentage)}%`, color: 'text-[#006A4E]' },
            { label: 'নিয়োজিত মশক দল', val: `${fmt(scarcity.assigned_spraying_crews || 0)}/${fmt(totalCrews)}`, color: 'text-blue-600' },
            { label: 'মোট পূর্বাভাস রোগী', val: fmt(Math.round(overview.total_predicted_cases || 0)), color: 'text-rose-600' },
            { label: 'ঘাটতির ওয়ার্ড', val: `${fmt(overview.critical_supply_wards_count || 0)}/৬০`, color: 'text-amber-600' },
          ].map((k, i) => (
            <div key={i}><div className="text-xs text-slate-500 mb-1">{k.label}</div><div className={`font-black text-xl ${k.color}`}>{k.val}</div></div>
          ))}
        </div>
      </div>
    </div>
  );

  // ── HOSPITAL VIEW ─────────────────────────────────────────────────────────
  const HospitalView = () => {
    const hData = hospitalRoutingData || allocationData?.hospital_routing || {};
    const hReg = hData?.regional_summary || {};
    const hCities = hData?.city_results || [];
    const hWards = hData?.ward_results || [];
    const hRoutes = hData?.routing_assignments || [];
    const hWarnings = hData?.critical_warnings || [];
    const hNotices = hData?.dispatch_notices || [];

    const filteredHWards = hWards.filter((w) => {
      const matchCity = hospitalTableCity === 'ALL' || w.city === hospitalTableCity;
      const matchSearch = !hospitalTableSearch || w.ward_id.toLowerCase().includes(hospitalTableSearch.toLowerCase()) || (w.locality && w.locality.toLowerCase().includes(hospitalTableSearch.toLowerCase()));
      const matchStatus = hospitalTableStatus === 'ALL' || (hospitalTableStatus === 'CRITICAL' && w.critical_hospital_warning) || w.hospital_surge_status === hospitalTableStatus;
      return matchCity && matchSearch && matchStatus;
    }).sort((a, b) => {
      let vA = a[hospitalTableSort] || 0; let vB = b[hospitalTableSort] || 0;
      if (typeof vA === 'string') return hospitalTableSortAsc ? vA.localeCompare(vB) : vB.localeCompare(vA);
      return hospitalTableSortAsc ? vA - vB : vB - vA;
    });

    const cityBarData = hCities.map((c) => ({ name: c.city, চাহিদা: c.total_bed_demand, ক্যাপাসিটি: c.total_effective_bed_capacity, ঘাটতি: c.net_bed_deficit }));

    return (
      <div>
        <Breadcrumb current={bn.hospital} onHome={() => setActiveView('home')} />
        <PageHeader title="🏥 হাসপাতাল শয্যা ব্যবস্থাপনা" desc="শয্যা সংকট ও বিকল্প হাসপাতালে রোগী স্থানান্তরের তথ্য" color="#db2777" />

        {approvedHospitalPlanMsg && (<div className="bg-green-50 border border-green-300 text-green-700 px-4 py-3 rounded-xl flex items-center justify-between mb-4"><div className="flex items-center gap-2"><CheckCircle2 className="w-5 h-5" /><span className="text-sm font-semibold">{approvedHospitalPlanMsg}</span></div><button onClick={() => setApprovedHospitalPlanMsg(null)} className="text-xs bg-green-100 hover:bg-green-200 text-green-700 px-2 py-1 rounded">বন্ধ</button></div>)}

        {hWarnings.length > 0 && (
          <div className="bg-red-50 border-2 border-red-300 rounded-2xl p-4 mb-5">
            <div className="flex items-start gap-3"><AlertTriangle className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" /><div>
              <h4 className="text-sm font-bold text-red-700 mb-2">🚨 হাসপাতাল শয্যা সংকট সতর্কতা — {hWarnings.length}টি ওয়ার্ড</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">{hWarnings.slice(0, 6).map((warn, idx) => (<div key={idx} className="bg-white border border-red-200 p-2.5 rounded-lg text-xs"><div className="flex justify-between font-bold text-slate-800"><span>{warn.entity_name}</span><span className="text-red-500">+{warn.net_deficit} শয্যা ঘাটতি</span></div><p className="text-slate-500 mt-1">{warn.recommended_action}</p></div>))}</div>
            </div></div>
          </div>
        )}

        {/* KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-5">
          {[
            { label: 'শয্যা চাহিদা', val: hReg.total_projected_bed_demand || 0, color: 'text-blue-600' },
            { label: 'কার্যকর ক্যাপাসিটি', val: hReg.total_effective_bed_capacity || 0, color: 'text-slate-700' },
            { label: 'প্রাথমিক ঘাটতি', val: hReg.total_initial_bed_deficit || 0, color: 'text-amber-600' },
            { label: 'রুটেড ওভারফ্লো', val: hReg.total_routed_overflow || 0, color: 'text-green-600' },
            { label: 'অবশিষ্ট ঘাটতি', val: hReg.total_unresolved_bed_deficit || 0, color: (hReg.total_unresolved_bed_deficit || 0) > 0 ? 'text-red-600' : 'text-green-600' },
          ].map((k, i) => (
            <div key={i} className="bg-white border border-slate-200 rounded-xl p-3 shadow-sm"><div className="text-xs text-slate-500 uppercase font-bold tracking-wider mb-1">{k.label}</div><div className={`text-2xl font-black ${k.color}`}>{fmt(k.val)}</div></div>
          ))}
        </div>

        {/* City Chart */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm mb-5">
          <h3 className="font-bold text-slate-700 mb-4 text-sm">📊 সিটি অনুযায়ী শয্যা চাহিদা বনাম ক্যাপাসিটি</h3>
          <div className="h-56"><ResponsiveContainer width="100%" height="100%"><BarChart data={cityBarData}><CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" /><XAxis dataKey="name" stroke="#94a3b8" fontSize={11} /><YAxis stroke="#94a3b8" fontSize={11} /><Tooltip contentStyle={{ backgroundColor: '#fff', borderColor: '#e2e8f0', fontSize: '12px' }} /><Legend wrapperStyle={{ fontSize: '11px' }} /><Bar dataKey="চাহিদা" fill="#06b6d4" radius={[4, 4, 0, 0]} /><Bar dataKey="ক্যাপাসিটি" fill="#10b981" radius={[4, 4, 0, 0]} /><Bar dataKey="ঘাটতি" fill="#ef4444" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></div>
        </div>

        {/* City Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mb-5">
          {hCities.map((city) => (
            <div key={city.city} className={`bg-white border rounded-xl p-3 shadow-sm ${city.net_bed_deficit > 0 ? 'border-red-200' : 'border-slate-200'}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="font-bold text-slate-800 text-sm">{city.city}</span>
                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${city.net_bed_deficit > 0 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>{city.net_bed_deficit > 0 ? 'সংকট' : 'স্বাভাবিক'}</span>
              </div>
              <div className="text-xs space-y-1 text-slate-500">
                <div className="flex justify-between"><span>চাহিদা/ক্যাপাসিটি:</span><span className="font-bold text-slate-700">{city.total_bed_demand}/{city.total_effective_bed_capacity}</span></div>
                <div className="flex justify-between"><span>রুটেড:</span><span className="font-bold text-green-600">+{city.total_routed_overflow}</span></div>
                <div className="flex justify-between"><span>নেট ঘাটতি:</span><span className={`font-bold ${city.net_bed_deficit > 0 ? 'text-red-600' : 'text-green-600'}`}>{city.net_bed_deficit}</span></div>
              </div>
            </div>
          ))}
        </div>

        {/* Routing Table */}
        {hRoutes.length > 0 && (
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm mb-5">
            <h3 className="font-bold text-slate-700 mb-4 flex items-center gap-2 text-sm"><ArrowRight className="w-4 h-4 text-[#006A4E]" /> স্বয়ংক্রিয় রোগী স্থানান্তর রুটিং ({fmt(hRoutes.length)} টি রুট)</h3>
            <div className="overflow-x-auto rounded-xl border border-slate-200">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 font-bold text-slate-500 uppercase tracking-wider">
                  <tr><th className="px-4 py-3">প্রেরণকারী ওয়ার্ড</th><th className="px-4 py-3">গ্রহণকারী হাসপাতাল</th><th className="px-4 py-3">সিটি</th><th className="px-4 py-3 text-center">ওভারফ্লো শয্যা</th><th className="px-4 py-3 text-center">নেট ঘাটতি আগে/পরে</th><th className="px-4 py-3 text-center">অবস্থা</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {hRoutes.map((r, i) => (
                    <tr key={i} className="hover:bg-slate-50">
                      <td className="px-4 py-3 font-semibold text-slate-800"><div>{r.source_ward_id}</div><div className="text-slate-400">{r.source_ward_name}</div></td>
                      <td className="px-4 py-3 font-semibold text-green-700"><div>{r.destination_ward_id}</div><div className="text-slate-400">{r.destination_ward_name}</div></td>
                      <td className="px-4 py-3 text-slate-500">{r.city}</td>
                      <td className="px-4 py-3 text-center font-bold text-amber-600">+{r.routed_overflow} শয্যা</td>
                      <td className="px-4 py-3 text-center text-slate-500 font-mono">{r.source_deficit_before} → <span className="text-slate-800 font-bold">{r.source_deficit_after}</span></td>
                      <td className="px-4 py-3 text-center"><span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-green-100 text-green-700">{r.approval_status || 'প্রস্তাবিত'}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-wrap items-center gap-3">
          <button onClick={() => setHospitalSimulatorOpen(!hospitalSimulatorOpen)} className={`flex items-center gap-1.5 px-4 py-2 text-sm font-bold rounded-xl border transition ${hospitalSimulatorOpen ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-700 border-slate-300 hover:border-blue-400'}`}><Sliders className="w-4 h-4" /> ইন্টার‍্যাক্টিভ সিমুলেটর</button>
          <button onClick={() => setHospitalNoticesOpen(true)} className="flex items-center gap-1.5 px-4 py-2 text-sm font-bold rounded-xl bg-white text-slate-700 border border-slate-300 hover:border-amber-400 transition"><FileText className="w-4 h-4 text-amber-500" /> জরুরি নোটিশ ({fmt(hNotices.length)})</button>
          <button onClick={handleApproveHospitalPlan} disabled={simulating} className="flex items-center gap-1.5 px-5 py-2 text-sm font-bold rounded-xl bg-[#006A4E] hover:bg-emerald-800 text-white shadow transition"><CheckCircle2 className="w-4 h-4" /> পরিকল্পনা অনুমোদন</button>
        </div>

        {/* Simulator Drawer */}
        {hospitalSimulatorOpen && (
          <div className="mt-5 bg-blue-50 border border-blue-200 rounded-2xl p-5">
            <h4 className="text-sm font-bold text-blue-700 mb-4 flex items-center gap-2"><Sliders className="w-4 h-4" /> ইন্টার‍্যাক্টিভ হাসপাতাল শয্যা সিমুলেটর</h4>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div><label className="text-xs font-semibold text-slate-600 mb-1 block">লক্ষ্য সিটি</label><select value={hospitalSimCity} onChange={(e) => { const c = e.target.value; setHospitalSimCity(c); const f = hWards.find((w) => w.city === c); if (f) setHospitalSimWard(f.ward_id); }} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white">{['Chattogram', 'Dhaka North', 'Dhaka South', 'Gazipur', 'Narayanganj'].map((c) => <option key={c} value={c}>{c}</option>)}</select></div>
              <div><label className="text-xs font-semibold text-slate-600 mb-1 block">লক্ষ্য ওয়ার্ড</label><select value={hospitalSimWard} onChange={(e) => setHospitalSimWard(e.target.value)} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white">{hWards.filter((w) => w.city === hospitalSimCity).map((w) => <option key={w.ward_id} value={w.ward_id}>{w.ward_id} - {w.locality}</option>)}</select></div>
              <div><label className="text-xs font-semibold text-slate-600 mb-1 block">সিমুলেটেড শয্যা চাহিদা</label><input type="number" min="0" max="500" value={hospitalCustomDemand[hospitalSimWard] ?? (hWards.find((w) => w.ward_id === hospitalSimWard)?.hospital_beds_required || 0)} onChange={(e) => setHospitalCustomDemand({ ...hospitalCustomDemand, [hospitalSimWard]: parseInt(e.target.value, 10) || 0 })} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" /></div>
              <div><label className="text-xs font-semibold text-slate-600 mb-1 block">সিমুলেটেড শয্যা ক্যাপাসিটি</label><input type="number" min="0" max="500" value={hospitalCustomCapacity[hospitalSimWard] ?? (hWards.find((w) => w.ward_id === hospitalSimWard)?.hospital_beds_effective_capacity || 0)} onChange={(e) => setHospitalCustomCapacity({ ...hospitalCustomCapacity, [hospitalSimWard]: parseInt(e.target.value, 10) || 0 })} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" /></div>
            </div>
            <div className="flex justify-end gap-3 mt-4">
              <button onClick={() => { setHospitalCustomDemand({}); setHospitalCustomCapacity({}); fetchHospitalRouting(stockPercentage, null, null); }} className="px-4 py-2 text-sm text-slate-500 bg-white border border-slate-300 rounded-xl hover:border-slate-400 transition">রিসেট করুন</button>
              <button onClick={() => fetchHospitalRouting(stockPercentage, hospitalCustomDemand, hospitalCustomCapacity)} className="px-4 py-2 text-sm font-bold bg-blue-600 hover:bg-blue-500 text-white rounded-xl shadow transition">রুটিং পুনঃগণনা</button>
            </div>
          </div>
        )}

        {/* Notices Modal */}
        {hospitalNoticesOpen && (
          <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={() => setHospitalNoticesOpen(false)}>
            <div className="bg-white rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between border-b border-slate-200 p-4"><div className="flex items-center gap-2"><FileText className="w-5 h-5 text-amber-500" /><h4 className="text-sm font-bold text-slate-800">জরুরি ডিসপ্যাচ নোটিশ</h4></div><button onClick={() => setHospitalNoticesOpen(false)} className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-500 px-3 py-1 rounded-lg">বন্ধ করুন</button></div>
              <div className="p-4 overflow-y-auto space-y-3 flex-1">
                {hNotices.length === 0 ? <p className="text-sm text-slate-400 text-center py-8">কোনো নোটিশ নেই।</p> : hNotices.map((n, i) => (
                  <div key={i} className="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">{n.notice_type}</span>
                      <button onClick={() => { navigator.clipboard.writeText(n.content); setCopiedNoticeId(n.notice_id); setTimeout(() => setCopiedNoticeId(null), 2000); }} className="flex items-center gap-1 text-xs bg-white hover:bg-slate-100 text-slate-600 px-2 py-1 rounded border border-slate-200 transition">{copiedNoticeId === n.notice_id ? <><Check className="w-3 h-3 text-green-500" /> কপি হয়েছে</> : <><Copy className="w-3 h-3" /> কপি</>}</button>
                    </div>
                    <pre className="text-xs font-mono text-slate-700 bg-white p-3 rounded-lg overflow-x-auto whitespace-pre-wrap border border-slate-100">{n.content}</pre>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  // ── REDISTRIBUTION VIEW ───────────────────────────────────────────────────
  const RedistributionView = () => {
    const recs = allocationData?.redistribution_recommendations || [];
    return (
      <div>
        <Breadcrumb current={bn.redistribution} onHome={() => setActiveView('home')} />
        <PageHeader title="🔄 আন্তঃওয়ার্ড সম্পদ পুনর্বণ্টন" desc="অতিরিক্ত সম্পদ সম্পন্ন ওয়ার্ড থেকে ঘাটতি ওয়ার্ডে সম্পদ স্থানান্তরের পরিকল্পনা" color="#4338ca" />
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm mb-5">
          <p className="text-sm text-slate-500">বিদ্যমান রিডিস্ট্রিবিউশন ইঞ্জিন কম অগ্রাধিকারের উদ্বৃত্ত ওয়ার্ড থেকে উচ্চ অগ্রাধিকারের ঘাটতি ওয়ার্ডে স্যালাইন ও টেস্ট কিট স্থানান্তরের সুপারিশ করে।</p>
          <div className="flex items-center gap-4 mt-3 text-sm"><span className="font-bold text-[#006A4E]">{fmt(recs.length)} টি সুপারিশ</span></div>
        </div>
        {recs.length === 0 ? (
          <div className="text-center py-16 text-slate-400 bg-white border border-slate-200 rounded-2xl"><div className="text-4xl mb-3">✅</div><div className="font-semibold">কোনো পুনর্বণ্টনের প্রয়োজন নেই</div><div className="text-sm mt-1">সব ওয়ার্ডে সম্পদ পর্যাপ্ত বরাদ্দ রয়েছে।</div></div>
        ) : (
          <div className="space-y-4">
            {recs.map((rec) => (
              <div key={rec.recommendation_id} className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
                <div className="bg-slate-50 px-5 py-3 border-b border-slate-200 flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-500">সুপারিশ #{rec.recommendation_id}</span>
                  <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">{translateResource(rec.resource_type)}</span>
                </div>
                <div className="p-5">
                  <div className="grid grid-cols-1 md:grid-cols-5 items-center gap-4">
                    <div className="md:col-span-2 bg-green-50 border border-green-200 rounded-xl p-3">
                      <div className="text-xs text-slate-400 mb-1">📤 প্রদানকারী ওয়ার্ড</div>
                      <div className="font-bold text-green-700">{rec.source_ward_id}</div>
                      <div className="text-xs text-slate-500">{rec.source_locality}</div>
                      <div className="text-xs mt-1">পরবর্তী পূরণ হার: <span className="font-bold text-green-700">{rec.source_fulfillment_after}%</span></div>
                    </div>
                    <div className="text-center hidden md:block">
                      <ArrowRight className="w-8 h-8 text-[#006A4E] mx-auto" />
                      <div className="text-sm font-black text-[#006A4E] mt-1">{fmt(rec.recommended_transfer_quantity)} টি</div>
                    </div>
                    <div className="md:col-span-2 bg-amber-50 border border-amber-200 rounded-xl p-3">
                      <div className="text-xs text-slate-400 mb-1">📥 গ্রহণকারী ওয়ার্ড</div>
                      <div className="font-bold text-amber-700">{rec.destination_ward_id}</div>
                      <div className="text-xs text-slate-500">{rec.destination_locality}</div>
                      <div className="text-xs mt-1">পূরণ হার: <span className="text-red-500">{rec.destination_fulfillment_before}%</span> → <span className="font-bold text-green-700">{rec.destination_fulfillment_after}%</span></div>
                    </div>
                  </div>
                  <div className="flex justify-end mt-4">
                    <button onClick={() => handleApproveRedistribution(rec)} className="px-4 py-2 bg-[#006A4E] hover:bg-emerald-800 text-white text-sm font-bold rounded-xl shadow transition">✅ স্থানান্তর অনুমোদন</button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  // ── ALERTS VIEW ───────────────────────────────────────────────────────────
  const AlertsView = () => {
    const deficitWards = (allocationData?.wards || []).filter((w) => w.has_critical_deficit);
    const partialWards = (allocationData?.wards || []).filter((w) => !w.has_critical_deficit && (w.remaining_saline_deficit > 0 || w.remaining_kits_deficit > 0 || w.remaining_beds_deficit > 0));
    return (
      <div>
        <Breadcrumb current={bn.alerts} onHome={() => setActiveView('home')} />
        <PageHeader title="🚨 সম্পদ ঘাটতি ও সতর্কতা" desc="গুরুতর সম্পদ সংকটে থাকা ওয়ার্ডের তালিকা ও প্রয়োজনীয় ব্যবস্থার নির্দেশনা" color="#dc2626" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-center"><div className="text-3xl font-black text-red-600">{fmt(deficitWards.length)}</div><div className="text-sm text-red-700 font-semibold mt-1">গুরুতর ঘাটতির ওয়ার্ড</div></div>
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-center"><div className="text-3xl font-black text-amber-600">{fmt(partialWards.length)}</div><div className="text-sm text-amber-700 font-semibold mt-1">আংশিক ঘাটতির ওয়ার্ড</div></div>
          <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center"><div className="text-3xl font-black text-green-600">{fmt(60 - deficitWards.length - partialWards.length)}</div><div className="text-sm text-green-700 font-semibold mt-1">পর্যাপ্ত সম্পদের ওয়ার্ড</div></div>
        </div>
        {deficitWards.length === 0 && partialWards.length === 0 ? (
          <div className="text-center py-16 bg-green-50 border border-green-200 rounded-2xl"><CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-3" /><div className="font-bold text-green-700 text-lg">সব ওয়ার্ডে সম্পদ পর্যাপ্ত!</div><div className="text-sm text-slate-500 mt-1">কোনো ওয়ার্ডে সম্পদ ঘাটতি নেই।</div></div>
        ) : (
          <div className="space-y-3">
            {deficitWards.map((w) => (
              <div key={w.ward_id} className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
                <span className="text-xl">🔴</span>
                <div className="flex-1">
                  <div className="font-bold text-slate-800">{w.ward_id} — {w.locality} · {w.city}</div>
                  <div className="text-xs text-slate-500 mt-1">
                    {w.remaining_saline_deficit > 0 && <span className="mr-3">স্যালাইন ঘাটতি: <b className="text-red-600">{toBangla(w.remaining_saline_deficit)}</b></span>}
                    {w.remaining_kits_deficit > 0 && <span className="mr-3">কিট ঘাটতি: <b className="text-red-600">{toBangla(w.remaining_kits_deficit)}</b></span>}
                    {w.remaining_beds_deficit > 0 && <span className="mr-3">শয্যা ঘাটতি: <b className="text-red-600">{toBangla(w.remaining_beds_deficit)}</b></span>}
                    {w.crew_deficit > 0 && <span>দল ঘাটতি: <b className="text-red-600">{toBangla(w.crew_deficit)}</b></span>}
                  </div>
                </div>
                <button onClick={() => { setSelectedWardId(w.ward_id); setSelectedCityCorp(w.city); setActiveView('allocation'); }} className="text-xs bg-red-100 hover:bg-red-200 text-red-700 font-bold px-3 py-1 rounded-lg transition whitespace-nowrap">বিস্তারিত দেখুন</button>
              </div>
            ))}
            {partialWards.map((w) => (
              <div key={w.ward_id} className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
                <span className="text-xl">🟡</span>
                <div className="flex-1">
                  <div className="font-bold text-slate-800">{w.ward_id} — {w.locality} · {w.city}</div>
                  <div className="text-xs text-slate-500 mt-1">আংশিক সম্পদ ঘাটতি রয়েছে — নজরদারি প্রয়োজন।</div>
                </div>
                <button onClick={() => { setSelectedWardId(w.ward_id); setSelectedCityCorp(w.city); setActiveView('allocation'); }} className="text-xs bg-amber-100 hover:bg-amber-200 text-amber-700 font-bold px-3 py-1 rounded-lg transition whitespace-nowrap">বিস্তারিত দেখুন</button>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  // ── MOSQUITO (WHAT-IF) VIEW ───────────────────────────────────────────────
  const MosquitoView = () => (
    <div>
      <Breadcrumb current={bn.mosquito} onHome={() => setActiveView('home')} />
      <PageHeader title="🧹 মশক নিধন কার্যক্রম (What-If Simulator)" desc="লার্ভিসাইড ও ফগিং দল মোতায়েন করুন — ২-৪ সপ্তাহের প্রভাব ও ROI দেখুন" color="#15803d" />

      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-5 mb-5">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div><label className="text-xs font-semibold text-slate-600 block mb-1.5">পরিকল্পনার নাম</label><input type="text" value={simScenarioName} onChange={(e) => setSimScenarioName(e.target.value)} className="w-full border border-slate-300 rounded-xl px-3 py-2.5 text-sm focus:border-[#006A4E] focus:outline-none" /></div>
          <div><label className="text-xs font-semibold text-slate-600 block mb-1.5">পরিকল্পনার মেয়াদ</label><select value={simForecastHorizon} onChange={(e) => setSimForecastHorizon(parseInt(e.target.value, 10))} className="w-full border border-slate-300 rounded-xl px-3 py-2.5 text-sm bg-white focus:border-[#006A4E] focus:outline-none"><option value={2}>২ সপ্তাহ (মূল ML পূর্বাভাস)</option><option value={3}>৩ সপ্তাহ</option><option value={4}>৪ সপ্তাহ (সম্পূর্ণ মহামারী পথ)</option></select></div>
          <div><label className="text-xs font-semibold text-slate-600 block mb-1.5">উপলব্ধ মশক দল</label><input type="number" min="0" max="500" value={simTotalCrews} onChange={(e) => setSimTotalCrews(parseInt(e.target.value || 0, 10))} className="w-full border border-slate-300 rounded-xl px-3 py-2.5 text-sm focus:border-[#006A4E] focus:outline-none" /></div>
          <div><label className="text-xs font-semibold text-slate-600 block mb-1.5">প্রতিক্রিয়া বক্ররেখা</label><select value={simResponseModel} onChange={(e) => setSimResponseModel(e.target.value)} className="w-full border border-slate-300 rounded-xl px-3 py-2.5 text-sm bg-white focus:border-[#006A4E] focus:outline-none"><option value="saturation">স্যাচুরেশন (ক্রমহ্রাসমান রিটার্ন)</option><option value="linear">লিনিয়ার (সমানুপাতিক)</option></select></div>
          <div><label className="text-xs font-semibold text-slate-600 block mb-1.5">মেডিকেল মজুদ ({fmt(simStockPct)}%)</label><input type="range" min="30" max="100" value={simStockPct} onChange={(e) => setSimStockPct(parseInt(e.target.value, 10))} className="w-full accent-[#006A4E] mt-2.5" /></div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button onClick={runWhatIfSimulation} disabled={simRunning} className="px-5 py-2.5 bg-[#006A4E] hover:bg-emerald-800 disabled:opacity-50 text-white font-bold text-sm rounded-xl transition flex items-center gap-2 shadow"><Sparkles className="w-4 h-4" /> {simRunning ? 'সিমুলেশন চলছে...' : 'সিমুলেশন চালান'}</button>
          <button onClick={() => optimizeCrews('larvicide')} disabled={simOptimizing} className="px-4 py-2.5 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-semibold text-sm rounded-xl transition flex items-center gap-2"><Users className="w-4 h-4" /> লার্ভিসাইড অটো-অপটিমাইজ</button>
          <button onClick={() => optimizeCrews('fogging')} disabled={simOptimizing} className="px-4 py-2.5 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white font-semibold text-sm rounded-xl transition flex items-center gap-2"><Users className="w-4 h-4" /> ফগিং অটো-অপটিমাইজ</button>
          <button onClick={() => { setSimSelectedWards({}); setSimResult(null); setSimError(null); setSimApproveMsg(null); }} className="px-4 py-2.5 bg-white text-slate-600 font-semibold text-sm rounded-xl border border-slate-300 hover:border-slate-400 transition">রিসেট</button>
          {simResult && <button onClick={approveVectorPlan} className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm rounded-xl shadow transition flex items-center gap-2"><CheckCircle2 className="w-4 h-4" /> পরিকল্পনা অনুমোদন</button>}
        </div>
        {simError && <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl flex items-center gap-2"><AlertTriangle className="w-4 h-4 shrink-0" /> {simError}</div>}
        {simApproveMsg && <div className="p-3 bg-green-50 border border-green-200 text-green-700 text-sm rounded-xl flex items-center gap-2"><CheckCircle2 className="w-4 h-4 shrink-0" /> {simApproveMsg}</div>}
      </div>

      {simResult && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {[
              { label: 'নিয়োজিত দল', val: simResult.regional_impact_summary.total_crews_deployed, color: 'text-blue-600' },
              { label: 'প্রতিরোধ করা কেস', val: simResult.regional_impact_summary.total_cases_prevented, color: 'text-green-600' },
              { label: 'বাঁচানো শয্যা', val: simResult.regional_impact_summary.total_beds_saved, color: 'text-amber-600' },
              { label: 'সংরক্ষিত স্যালাইন', val: simResult.regional_impact_summary.total_saline_bags_saved, color: 'text-blue-500' },
              { label: 'সংরক্ষিত কিট', val: simResult.regional_impact_summary.total_diagnostic_kits_saved, color: 'text-purple-600' },
              { label: 'ইন্টারভেনশন ROI', val: simResult.regional_impact_summary.overall_roi ?? '—', color: 'text-teal-600' },
            ].map((k, i) => (
              <div key={i} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                <div className="text-xs text-slate-500 uppercase font-bold tracking-wider mb-1">{k.label}</div>
                <div className={`text-2xl font-black ${k.color}`}>{fmt(k.val)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Ward Deployment Table */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm mt-5">
        <div className="flex flex-wrap justify-between items-center gap-3 mb-4">
          <h3 className="font-bold text-slate-700 text-sm">🗂️ ওয়ার্ড মোতায়েন টেবিল</h3>
          <select value={simCityFilter} onChange={(e) => setSimCityFilter(e.target.value)} className="border border-slate-300 rounded-lg px-3 py-1.5 text-xs bg-white focus:outline-none">
            <option value="ALL">সব সিটি (৬০ ওয়ার্ড)</option>
            {['Dhaka North', 'Dhaka South', 'Chattogram', 'Gazipur', 'Narayanganj'].map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div className="overflow-x-auto rounded-xl border border-slate-200 max-h-80 overflow-y-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 font-bold text-slate-500 sticky top-0">
              <tr><th className="px-3 py-2.5">ওয়ার্ড</th><th className="px-3 py-2.5">সিটি</th><th className="px-3 py-2.5">ঝুঁকি</th><th className="px-3 py-2.5">রোগী (২ সপ্তাহ)</th><th className="px-3 py-2.5">লার্ভিসাইড দল</th><th className="px-3 py-2.5">ফগিং দল</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(allocationData?.wards || []).filter((w) => simCityFilter === 'ALL' || w.city === simCityFilter).map((w) => (
                <tr key={w.ward_id} className="hover:bg-slate-50">
                  <td className="px-3 py-2.5"><div className="font-semibold text-slate-700">{w.ward_id}</div><div className="text-slate-400">{w.locality}</div></td>
                  <td className="px-3 py-2.5 text-slate-500">{w.city}</td>
                  <td className="px-3 py-2.5"><span className={`font-bold px-2 py-0.5 rounded-full ${w.risk_level === 'High' ? 'bg-red-100 text-red-700' : w.risk_level === 'Medium' ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'}`}>{translateRisk(w.risk_level)}</span></td>
                  <td className="px-3 py-2.5 font-bold text-slate-700">{w.total_predicted_cases}</td>
                  <td className="px-3 py-2.5"><input type="number" min="0" max="20" value={simSelectedWards[w.ward_id]?.larvicide_crews || 0} onChange={(e) => setSimSelectedWards((prev) => ({ ...prev, [w.ward_id]: { ...(prev[w.ward_id] || {}), larvicide_crews: parseInt(e.target.value || 0, 10) } }))} className="w-16 border border-slate-300 rounded-lg px-2 py-1 text-center text-xs focus:border-[#006A4E] focus:outline-none" /></td>
                  <td className="px-3 py-2.5"><input type="number" min="0" max="20" value={simSelectedWards[w.ward_id]?.fogging_crews || 0} onChange={(e) => setSimSelectedWards((prev) => ({ ...prev, [w.ward_id]: { ...(prev[w.ward_id] || {}), fogging_crews: parseInt(e.target.value || 0, 10) } }))} className="w-16 border border-slate-300 rounded-lg px-2 py-1 text-center text-xs focus:border-amber-500 focus:outline-none" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );

  // ── DISPATCH VIEW ─────────────────────────────────────────────────────────
  const DispatchView = () => (
    <div>
      <Breadcrumb current={bn.dispatch} onHome={() => setActiveView('home')} />
      <PageHeader title="📢 জরুরি বার্তা ও প্রতিবেদন" desc="WhatsApp বার্তা এবং কমিশনারের জন্য PDF প্রতিবেদন তৈরি ও ডাউনলোড করুন" color="#ea580c" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-6">
        {[
          { icon: '💬', title: 'WhatsApp SMS বার্তা', desc: 'ওয়ার্ডভিত্তিক সম্পদ ও সতর্কতার বার্তা তৈরি করুন', btnLabel: 'বার্তা তৈরি করুন', btnColor: 'bg-[#25D366] hover:bg-green-500', action: () => window.open(`/api/allocation/export/sms?stock_percentage=${stockPercentage}&total_crews=${totalCrews}`, '_blank') },
          { icon: '📄', title: 'PDF কমিশনার ব্রিফ', desc: 'মুদ্রণযোগ্য বিস্তারিত প্রতিবেদন ডাউনলোড করুন', btnLabel: 'PDF ডাউনলোড করুন', btnColor: 'bg-[#006A4E] hover:bg-emerald-800', action: () => window.open(`/api/allocation/export/pdf?stock_percentage=${stockPercentage}&total_crews=${totalCrews}`, '_blank') },
          { icon: '🌐', title: 'HTML ওয়েব রিপোর্ট', desc: 'ব্রাউজারে দেখার উপযোগী বিস্তারিত রিপোর্ট', btnLabel: 'রিপোর্ট দেখুন', btnColor: 'bg-blue-600 hover:bg-blue-700', action: () => window.open(`/api/allocation/export/html?stock_percentage=${stockPercentage}&total_crews=${totalCrews}`, '_blank') },
          { icon: '📋', title: 'অনুমোদন লগ ও অডিট', desc: 'অনুমোদিত পরিকল্পনা ও কার্যক্রমের রেকর্ড', btnLabel: 'অডিট লগ দেখুন', btnColor: 'bg-purple-600 hover:bg-purple-700', action: null },
        ].map((item, i) => (
          <div key={i} className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col gap-3">
            <div className="text-3xl">{item.icon}</div>
            <div className="font-bold text-slate-800">{item.title}</div>
            <div className="text-sm text-slate-500">{item.desc}</div>
            <button onClick={item.action || undefined} className={`mt-auto px-5 py-2.5 ${item.btnColor} text-white font-bold text-sm rounded-xl shadow transition`}>{item.btnLabel}</button>
          </div>
        ))}
      </div>

      {/* Audit Logs */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <h3 className="font-bold text-slate-700 mb-4 flex items-center gap-2 text-sm"><Database className="w-4 h-4 text-purple-500" /> অনুমোদন লগ ({fmt(auditLogs.length)} টি)</h3>
        {auditLogs.length === 0 ? (
          <div className="text-center py-8 text-slate-400 text-sm">কোনো লগ এখনও নেই।</div>
        ) : (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {auditLogs.map((log, i) => (
              <div key={i} className="bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 flex items-start gap-3">
                <Clock className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
                <div>
                  <div className="text-sm font-semibold text-slate-700">{log.action || log.plan_name || 'অনুমোদন লগ'}</div>
                  <div className="text-xs text-slate-400 mt-0.5">{log.timestamp || log.created_at || ''} {log.approved_by ? `· ${log.approved_by}` : ''}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════════════════
  const VIEW_MAP = {
    home: <HomeView />,
    forecast: <ForecastView />,
    allocation: <AllocationView />,
    map: <MapView />,
    controls: <ControlsView />,
    hospital: <HospitalView />,
    redistribution: <RedistributionView />,
    alerts: <AlertsView />,
    mosquito: <MosquitoView />,
    dispatch: <DispatchView />,
  };

  const NAV_ITEMS = [
    { id: 'home', label: 'হোম' },
    { id: 'forecast', label: 'পূর্বাভাস' },
    { id: 'allocation', label: 'সম্পদ বরাদ্দ' },
    { id: 'map', label: 'মানচিত্র' },
    { id: 'hospital', label: 'হাসপাতাল' },
    { id: 'redistribution', label: 'পুনর্বণ্টন' },
    { id: 'alerts', label: 'সতর্কতা', badge: (overview.critical_supply_wards_count || 0) > 0 ? overview.critical_supply_wards_count : null },
    { id: 'mosquito', label: 'মশক নিধন' },
    { id: 'dispatch', label: 'বার্তা ও প্রতিবেদন' },
  ];

  return (
    <div className="min-h-screen bg-[#F4F7F4] text-slate-800 flex flex-col">
      {/* ── HEADER ── */}
      <header className="bg-[#006A4E] text-white shadow-md sticky top-0 z-40">
        <div className="max-w-[1440px] mx-auto px-4 md:px-6">
          <div className="flex items-center justify-between py-3 gap-3">
            {/* Brand */}
            <button onClick={() => setActiveView('home')} className="flex items-center gap-3 hover:opacity-90 transition">
              <div className="w-9 h-9 rounded-full bg-white/15 border border-white/30 flex items-center justify-center text-lg">🦟</div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-lg font-extrabold tracking-tight">{lang === 'bn' ? 'এডিস বিদায়' : 'ADES BIDAI'}</span>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-900/60 text-emerald-100 border border-emerald-500/40 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-300 animate-pulse" />
                    {lang === 'bn' ? `অফলাইন সক্রিয় • ${toBangla(60)}টি ওয়ার্ড` : 'Offline Ready • 60 Wards'}
                  </span>
                </div>
                <p className="text-[11px] text-emerald-100/85">{lang === 'bn' ? 'স্বাস্থ্য অধিদপ্তর (DGHS) — জাতীয় ডেঙ্গু পূর্বাভাস প্ল্যাটফর্ম' : 'DGHS — National Dengue Surveillance & Resource Command'}</p>
              </div>
            </button>

            {/* Right: Lang Toggle + Export */}
            <div className="flex items-center gap-2 flex-wrap">
              <div className="flex items-center bg-emerald-900/70 rounded-lg p-0.5 border border-emerald-500/40">
                <button onClick={() => setLang('bn')} className={`px-2.5 py-1 text-xs font-bold rounded-md transition ${lang === 'bn' ? 'bg-amber-400 text-slate-900 shadow' : 'text-emerald-100 hover:text-white'}`}>বাংলা</button>
                <button onClick={() => setLang('en')} className={`px-2.5 py-1 text-xs font-bold rounded-md transition ${lang === 'en' ? 'bg-amber-400 text-slate-900 shadow' : 'text-emerald-100 hover:text-white'}`}>EN</button>
              </div>
              <button onClick={() => window.open(`/api/allocation/export/pdf?stock_percentage=${stockPercentage}&total_crews=${totalCrews}`, '_blank')} className="flex items-center gap-1.5 px-3 py-1.5 bg-white/10 hover:bg-white/20 text-xs font-semibold text-white border border-white/20 rounded-lg transition">
                <FileDown className="w-3.5 h-3.5 text-amber-300" /> পিডিএফ
              </button>
              <button onClick={() => { setApprovalModalOpen(true); handleApprovePlan(); }} className="flex items-center gap-1.5 px-3.5 py-1.5 bg-amber-400 hover:bg-amber-300 text-slate-900 text-xs font-extrabold rounded-lg shadow transition">
                <CheckCircle2 className="w-4 h-4" /> পরিকল্পনা অনুমোদন
              </button>
            </div>
          </div>

          {/* Nav Bar */}
          <nav className="flex items-center gap-1 pb-0.5 overflow-x-auto border-t border-white/15 pt-1">
            {NAV_ITEMS.map((item) => (
              <button key={item.id} onClick={() => setActiveView(item.id)} className={`flex items-center gap-1 px-3 py-2 text-xs font-bold rounded-md whitespace-nowrap transition border-b-2 ${activeView === item.id ? 'border-amber-400 text-white bg-white/10' : 'border-transparent text-emerald-100 hover:text-white hover:bg-white/8'}`}>
                {item.label}
                {item.badge && <span className="ml-1 text-[9px] font-bold bg-red-500 text-white rounded-full px-1.5 py-0.5">{fmt(item.badge)}</span>}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* ── MAIN CONTENT ── */}
      <main className="max-w-[1440px] w-full mx-auto px-4 md:px-6 py-6 flex-1">
        {VIEW_MAP[activeView] || <HomeView />}
      </main>

      {/* ── FOOTER ── */}
      <footer className="bg-[#006A4E] text-emerald-100 text-center py-4 text-xs mt-auto">
        <div>এডিস বিদায় (ADES BIDAI) — স্বাস্থ্য অধিদপ্তর (DGHS) • BLUEPINE • সম্পূর্ণ অফলাইন সক্রিয়</div>
        <div className="mt-1 opacity-60">৬০টি ওয়ার্ড • ৫টি সিটি কর্পোরেশন • HistGradientBoosting ML মডেল • R² = 0.838</div>
      </footer>
    </div>
  );
}

import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  Sliders,
  CheckCircle2,
  FileDown,
  Share2,
  Users,
  Bed,
  TestTube,
  Activity,
  Layers,
  MapPin,
  RefreshCw,
  Search,
  Filter,
  ArrowUpDown,
  Building2,
  Sparkles,
  ExternalLink,
  Info,
  Clock,
  Send,
  Download,
  Database,
  ArrowRight
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line
} from 'recharts';
import L from 'leaflet';

export default function App() {
  // Scarcity state
  const [stockPercentage, setStockPercentage] = useState(100);
  const [totalCrews, setTotalCrews] = useState(150);

  // Data state
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [allocationData, setAllocationData] = useState(null);
  const [activeTab, setActiveTab] = useState('allocations'); // allocations, map, hospital, redistribution, simulation, audit

  // Filter & Search state for 60-ward table
  const [searchTerm, setSearchTerm] = useState('');
  const [cityFilter, setCityFilter] = useState('ALL');
  const [riskFilter, setRiskFilter] = useState('ALL');
  const [shortageFilter, setShortageFilter] = useState('ALL'); // ALL, CRITICAL, CREW_SHORTAGE
  const [sortField, setSortField] = useState('priority_ranking');
  const [sortOrder, setSortOrder] = useState('asc'); // asc, desc

  // Manual edits state
  const [manualAllocations, setManualAllocations] = useState({});
  const [manualCrews, setManualCrews] = useState({});
  const [approvalModalOpen, setApprovalModalOpen] = useState(false);
  const [approvalStatus, setApprovalStatus] = useState(null);

  // Counterfactual simulation state
  const [simWardId, setSimWardId] = useState('DNCC_Ward_01');
  const [simCrews, setSimCrews] = useState(4);
  const [simLarvicide, setSimLarvicide] = useState(85);
  const [counterfactualResult, setCounterfactualResult] = useState(null);

  // Audit logs & dispatches
  const [auditLogs, setAuditLogs] = useState([]);
  const [notifications, setNotifications] = useState([]);

  // Map reference
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);

  // Fetch allocation data
  const fetchAllocation = async (stock = stockPercentage, crews = totalCrews, customManual = null) => {
    try {
      setSimulating(true);
      let url = `/api/allocation/current?stock_percentage=${stock}&total_crews=${crews}`;
      let res;
      if (customManual && (Object.keys(customManual.allocations || {}).length > 0 || Object.keys(customManual.crews || {}).length > 0)) {
        res = await fetch('/api/allocation/simulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            stock_percentage: stock,
            total_spraying_crews: crews,
            manual_allocations: customManual.allocations,
            manual_crews: customManual.crews,
          }),
        });
      } else {
        res = await fetch(url);
      }
      const data = await res.json();
      setAllocationData(data);
    } catch (err) {
      console.error('Failed to load allocation data:', err);
    } finally {
      setSimulating(false);
      setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    fetchAllocation(100, 150);
    fetchAuditLogs();
    fetchNotifications();
  }, []);

  const fetchAuditLogs = async () => {
    try {
      const res = await fetch('/api/allocation/audit-logs?limit=50');
      const data = await res.json();
      setAuditLogs(data.logs || []);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchNotifications = async () => {
    try {
      const res = await fetch(`/api/allocation/notifications?stock_percentage=${stockPercentage}&total_crews=${totalCrews}`);
      const data = await res.json();
      setNotifications(data.notifications || []);
    } catch (e) {
      console.error(e);
    }
  };

  // Run counterfactual simulation
  const runCounterfactual = async (wardId = simWardId, crews = simCrews, larv = simLarvicide) => {
    try {
      const res = await fetch('/api/allocation/counterfactual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ward_id: wardId,
          crews_assigned: crews,
          larvicide_coverage_pct: larv,
        }),
      });
      const data = await res.json();
      setCounterfactualResult(data);
    } catch (e) {
      console.error('Counterfactual simulation failed:', e);
    }
  };

  useEffect(() => {
    if (allocationData?.wards && allocationData.wards.length > 0) {
      runCounterfactual(allocationData.wards[0].ward_id, 4, 85);
    }
  }, [allocationData?.wards]);

  // Handle plan approval
  const handleApprovePlan = async () => {
    try {
      const res = await fetch('/api/allocation/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plan_name: `National Dengue Response Plan (${stockPercentage}% Stock)`,
          approved_by: "Central Health Administrator",
          stock_percentage: stockPercentage,
          total_spraying_crews: totalCrews,
          manual_allocations: manualAllocations,
          manual_crews: manualCrews,
        }),
      });
      const data = await res.json();
      setApprovalStatus(data);
      fetchAuditLogs();
    } catch (e) {
      console.error('Plan approval failed:', e);
    }
  };

  // Handle redistribution approval
  const handleApproveRedistribution = async (rec) => {
    try {
      const res = await fetch('/api/allocation/redistribute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resource_type: rec.resource_type,
          source_ward_id: rec.source_ward_id,
          destination_ward_id: rec.destination_ward_id,
          quantity: rec.recommended_transfer_quantity,
          reason: rec.reason,
          user: "Central Health Administrator",
        }),
      });
      await res.json();
      alert(`Transfer Authorized: ${rec.recommended_transfer_quantity} units of ${rec.resource_type} dispatched from ${rec.source_ward_id} to ${rec.destination_ward_id}.`);
      fetchAllocation();
      fetchAuditLogs();
    } catch (e) {
      console.error(e);
    }
  };

  // Leaflet map setup
  useEffect(() => {
    if (activeTab === 'map' && allocationData?.wards && mapContainerRef.current) {
      if (!mapInstanceRef.current) {
        const map = L.map(mapContainerRef.current).setView([23.8103, 90.4125], 11);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
          attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
          maxZoom: 19,
        }).addTo(map);
        mapInstanceRef.current = map;
      }

      const map = mapInstanceRef.current;
      map.eachLayer((layer) => {
        if (layer instanceof L.CircleMarker) {
          map.removeLayer(layer);
        }
      });

      allocationData.wards.forEach((w) => {
        const color =
          w.risk_level === 'High' ? '#EF4444' : w.risk_level === 'Medium' ? '#F59E0B' : '#10B981';
        const hasShortage = w.has_critical_deficit;

        const marker = L.circleMarker([w.lat, w.lon], {
          radius: Math.min(18, Math.max(6, w.total_predicted_cases * 1.8)),
          fillColor: color,
          color: hasShortage ? '#DC2626' : '#FFFFFF',
          weight: hasShortage ? 2.5 : 1,
          opacity: 1,
          fillOpacity: 0.75,
        }).addTo(map);

        marker.bindPopup(`
          <div style="font-family: sans-serif; font-size: 12px; color: #F8FAFC;">
            <div style="font-weight: 700; font-size: 14px; margin-bottom: 4px; color: ${color};">
              #${w.priority_ranking} — ${w.ward_id} (${w.locality})
            </div>
            <div><b>City:</b> ${w.city}</div>
            <div><b>Priority Score:</b> ${w.priority_score.toFixed(4)}</div>
            <div><b>2-Week Cases:</b> ${w.total_predicted_cases} (Risk: ${w.risk_level})</div>
            <hr style="border: 0.5px solid #334155; margin: 6px 0;" />
            <div><b>Saline Bags:</b> ${w.approved_saline_allocation} / ${w.saline_demand} (${w.saline_fulfillment_pct}%)</div>
            <div><b>Diagnostic Kits:</b> ${w.approved_kits_allocation} / ${w.kits_demand} (${w.kits_fulfillment_pct}%)</div>
            <div><b>Hospital Beds:</b> ${w.approved_beds_allocation} / ${w.beds_demand} (${w.beds_fulfillment_pct}%)</div>
            <div><b>Spraying Crews:</b> ${w.approved_crew_allocation} / ${w.required_crews}</div>
            ${hasShortage ? '<div style="color: #EF4444; font-weight: 700; margin-top: 4px;">⚠️ CRITICAL SUPPLY DEFICIT</div>' : '<div style="color: #10B981; font-weight: 700; margin-top: 4px;">✓ 100% DEMAND FULFILLED</div>'}
          </div>
        `);
      });
    }
  }, [activeTab, allocationData]);

  // Filtered and sorted wards
  const filteredWards = useMemo(() => {
    if (!allocationData?.wards) return [];
    return allocationData.wards
      .filter((w) => {
        const matchesSearch =
          w.ward_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
          w.locality.toLowerCase().includes(searchTerm.toLowerCase()) ||
          w.city.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesCity = cityFilter === 'ALL' || w.city === cityFilter;
        const matchesRisk = riskFilter === 'ALL' || w.risk_level === riskFilter;
        const matchesShortage =
          shortageFilter === 'ALL' ||
          (shortageFilter === 'CRITICAL' && w.has_critical_deficit) ||
          (shortageFilter === 'CREW_SHORTAGE' && w.has_crew_shortage);
        return matchesSearch && matchesCity && matchesRisk && matchesShortage;
      })
      .sort((a, b) => {
        let valA = a[sortField];
        let valB = b[sortField];
        if (typeof valA === 'string') {
          return sortOrder === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }
        return sortOrder === 'asc' ? valA - valB : valB - valA;
      });
  }, [allocationData, searchTerm, cityFilter, riskFilter, shortageFilter, sortField, sortOrder]);

  const overview = allocationData?.regional_overview || {};
  const scarcity = allocationData?.scarcity_controls || {};

  // Chart data: City summary
  const citySummaryData = useMemo(() => {
    if (!allocationData?.wards) return [];
    const grouped = {};
    allocationData.wards.forEach((w) => {
      if (!grouped[w.city]) {
        grouped[w.city] = { city: w.city, cases: 0, salineDemand: 0, salineAlloc: 0, kitsDemand: 0, kitsAlloc: 0, crewsReq: 0, crewsAssigned: 0 };
      }
      grouped[w.city].cases += w.total_predicted_cases;
      grouped[w.city].salineDemand += w.saline_demand;
      grouped[w.city].salineAlloc += w.approved_saline_allocation;
      grouped[w.city].kitsDemand += w.kits_demand;
      grouped[w.city].kitsAlloc += w.approved_kits_allocation;
      grouped[w.city].crewsReq += w.required_crews;
      grouped[w.city].crewsAssigned += w.approved_crew_allocation;
    });
    return Object.values(grouped);
  }, [allocationData]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#0B1120] text-slate-200">
        <Activity className="w-12 h-12 text-cyan-400 animate-spin mb-4" />
        <h2 className="text-xl font-bold tracking-wider">ADES BIDAI CENTRAL COMMAND</h2>
        <p className="text-sm text-slate-400 mt-1">Solving Constrained Priority-Based Allocation across 60 Wards...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0B1120] text-slate-100 p-4 md:p-6 space-y-6">
      {/* 1. Header Banner */}
      <header className="flex flex-col lg:flex-row lg:items-center lg:justify-between pb-4 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="text-3xl">🦟</span>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-extrabold text-white tracking-tight">ADES BIDAI</h1>
                <span className="text-xs font-bold px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 uppercase tracking-widest">
                  Phase 2 Engine
                </span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span> 60 Wards Synced
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Directorate General of Health Services (DGHS) — Central Dengue Resource Allocation & Vector Control Command
              </p>
            </div>
          </div>
        </div>

        {/* Global Export & Action Bar */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => window.open(`/api/allocation/export/pdf?stock_percentage=${stockPercentage}&total_crews=${totalCrews}`, '_blank')}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 rounded-lg transition"
            title="Download Official Government PDF Report"
          >
            <FileDown className="w-3.5 h-3.5 text-red-400" />
            PDF Report
          </button>
          <button
            onClick={() => window.open(`/api/allocation/export/html?stock_percentage=${stockPercentage}&total_crews=${totalCrews}`, '_blank')}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 rounded-lg transition"
            title="Open Interactive HTML Report"
          >
            <ExternalLink className="w-3.5 h-3.5 text-cyan-400" />
            HTML Report
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 rounded-lg transition"
            title="View Dispatches & SMS"
          >
            <Share2 className="w-3.5 h-3.5 text-emerald-400" />
            Dispatches
          </button>
          <button
            onClick={() => {
              setApprovalModalOpen(true);
              handleApprovePlan();
            }}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold rounded-lg shadow-lg shadow-cyan-900/40 transition"
          >
            <CheckCircle2 className="w-4 h-4" />
            Approve & Lock Plan
          </button>
        </div>
      </header>

      {/* 2. Interactive Scarcity Controls Bar */}
      <section className="bg-slate-900/90 border border-cyan-800/60 rounded-xl p-4 shadow-xl shadow-cyan-950/20 backdrop-blur">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-cyan-400" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
              Interactive Public Health Scarcity Controls
            </h2>
            <span className="text-[11px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded border border-slate-700">
              Real-Time Greedy Simulation
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => fetchAllocation(stockPercentage, totalCrews, { allocations: manualAllocations, crews: manualCrews })}
              disabled={simulating}
              className="flex items-center gap-1.5 px-3 py-1 bg-cyan-950 hover:bg-cyan-900 text-cyan-300 text-xs font-bold border border-cyan-700 rounded-md transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${simulating ? 'animate-spin' : ''}`} />
              Recalculate Allocations
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
          {/* Slider 1: Regional Stock (30% - 100%) */}
          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-cyan-400" /> Available Regional Stock:
              </span>
              <span className="font-extrabold text-cyan-400 text-sm">
                {stockPercentage}% of Total Regional Inventory
              </span>
            </div>
            <input
              type="range"
              min="30"
              max="100"
              step="5"
              value={stockPercentage}
              onChange={(e) => {
                const val = Number(e.target.value);
                setStockPercentage(val);
                fetchAllocation(val, totalCrews);
              }}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
            />
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>Severe Shortage (30%)</span>
              <span>Constrained (50%)</span>
              <span>Standard (75%)</span>
              <span className="text-cyan-400 font-bold">100% Usable Stock</span>
            </div>
          </div>

          {/* Slider 2: Total Spraying Crews */}
          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                <Users className="w-4 h-4 text-emerald-400" /> Total Available Spraying Crews:
              </span>
              <span className="font-extrabold text-emerald-400 text-sm">
                {totalCrews} Crews ({scarcity.assigned_spraying_crews || 0} Assigned / {scarcity.unassigned_spraying_crews || 0} In Reserve)
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="300"
              step="5"
              value={totalCrews}
              onChange={(e) => {
                const val = Number(e.target.value);
                setTotalCrews(val);
                fetchAllocation(stockPercentage, val);
              }}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-400"
            />
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>Zero Crews (0)</span>
              <span>50 Crews</span>
              <span>150 Standard</span>
              <span className="text-emerald-400 font-bold">300 Crews Max</span>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Regional Overview KPI Ribbon */}
      <section className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        {/* Cases */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
            <Activity className="w-3.5 h-3.5 text-cyan-400" /> 2-Week Cases
          </div>
          <div className="text-2xl font-black text-white mt-1">
            {overview.total_predicted_cases || 0}
          </div>
          <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1.5">
            <span className="text-red-400 font-bold">{overview.high_risk_wards_count || 0} High</span>
            <span>•</span>
            <span className="text-amber-400 font-bold">{overview.medium_risk_wards_count || 0} Med</span>
            <span>•</span>
            <span className="text-emerald-400 font-bold">{overview.low_risk_wards_count || 0} Low</span>
          </div>
        </div>

        {/* Saline Bags */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
            <TestTube className="w-3.5 h-3.5 text-blue-400" /> IV Saline Bags
          </div>
          <div className="text-2xl font-black text-white mt-1">
            {overview.total_saline_allocated || 0} <span className="text-xs text-slate-500 font-normal">/ {overview.total_saline_demand || 0}</span>
          </div>
          <div className="text-[11px] mt-1 flex justify-between">
            <span className={overview.total_saline_deficit > 0 ? 'text-red-400 font-bold' : 'text-emerald-400 font-bold'}>
              {overview.total_saline_deficit > 0 ? `-${overview.total_saline_deficit} Deficit` : '100% Satisfied'}
            </span>
            <span className="text-slate-400">Stock: {scarcity.effective_saline_stock}</span>
          </div>
        </div>

        {/* Diagnostic Kits */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5 text-purple-400" /> Rapid Test Kits
          </div>
          <div className="text-2xl font-black text-white mt-1">
            {overview.total_kits_allocated || 0} <span className="text-xs text-slate-500 font-normal">/ {overview.total_kits_demand || 0}</span>
          </div>
          <div className="text-[11px] mt-1 flex justify-between">
            <span className={overview.total_kits_deficit > 0 ? 'text-red-400 font-bold' : 'text-emerald-400 font-bold'}>
              {overview.total_kits_deficit > 0 ? `-${overview.total_kits_deficit} Deficit` : '100% Satisfied'}
            </span>
            <span className="text-slate-400">Stock: {scarcity.effective_kits_stock}</span>
          </div>
        </div>

        {/* Hospital Beds */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
            <Bed className="w-3.5 h-3.5 text-amber-400" /> Hospital Beds
          </div>
          <div className="text-2xl font-black text-white mt-1">
            {overview.total_beds_allocated || 0} <span className="text-xs text-slate-500 font-normal">/ {overview.total_beds_demand || 0}</span>
          </div>
          <div className="text-[11px] mt-1 flex justify-between">
            <span className={overview.total_beds_deficit > 0 ? 'text-red-400 font-bold' : 'text-emerald-400 font-bold'}>
              {overview.total_beds_deficit > 0 ? `-${overview.total_beds_deficit} Shortage` : 'Beds Available'}
            </span>
            <span className="text-slate-400">Cap: {scarcity.effective_beds_stock}</span>
          </div>
        </div>

        {/* Spraying Crews */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
            <Users className="w-3.5 h-3.5 text-emerald-400" /> Spraying Crews
          </div>
          <div className="text-2xl font-black text-white mt-1">
            {overview.total_assigned_crews || 0} <span className="text-xs text-slate-500 font-normal">/ {overview.total_required_crews || 0}</span>
          </div>
          <div className="text-[11px] mt-1 flex justify-between">
            <span className={overview.total_crew_shortage > 0 ? 'text-red-400 font-bold' : 'text-emerald-400 font-bold'}>
              {overview.total_crew_shortage > 0 ? `-${overview.total_crew_shortage} Shortage` : 'All Assigned'}
            </span>
            <span className="text-slate-400">Avail: {totalCrews}</span>
          </div>
        </div>

        {/* Critical Warnings */}
        <div className={`border rounded-xl p-3.5 ${overview.critical_supply_wards_count > 0 ? 'bg-red-950/40 border-red-800' : 'bg-slate-900 border-slate-800'}`}>
          <div className="text-[11px] font-semibold uppercase tracking-wider flex items-center gap-1 text-red-400">
            <AlertTriangle className="w-3.5 h-3.5" /> Deficit Wards
          </div>
          <div className={`text-2xl font-black mt-1 ${overview.critical_supply_wards_count > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
            {overview.critical_supply_wards_count || 0}
            <span className="text-xs font-normal text-slate-400 ml-1">/ 60 Wards</span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            {overview.critical_supply_wards_count > 0 ? 'Prioritized emergency alerts active' : 'Zero unfulfilled wards'}
          </div>
        </div>
      </section>

      {/* 4. Tab Navigation Header */}
      <nav className="flex items-center gap-2 border-b border-slate-800 pb-2 overflow-x-auto">
        {[
          { id: 'allocations', label: 'Ward Allocations & Priority Ranking', icon: Activity, count: 60 },
          { id: 'map', label: 'Surveillance Map & Geographic Centroids', icon: MapPin },
          { id: 'hospital', label: 'Hospital Bed Overflow Routing', icon: Bed, count: allocationData?.hospital_overflow_routes?.length },
          { id: 'redistribution', label: 'Inter-Ward Redistribution Engine', icon: RefreshCw, count: allocationData?.redistribution_recommendations?.length },
          { id: 'simulation', label: 'Intervention Counterfactual Simulator', icon: Sparkles },
          { id: 'audit', label: 'Audit Trail & Dispatches', icon: Database, count: auditLogs.length },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-3.5 py-2 text-xs font-bold rounded-lg transition whitespace-nowrap ${
                isActive
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-700 shadow-md shadow-cyan-950'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
              {tab.label}
              {tab.count !== undefined && (
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${isActive ? 'bg-cyan-900 text-cyan-200' : 'bg-slate-800 text-slate-400'}`}>
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* 5. TAB 1: 60-Ward Allocations Table */}
      {activeTab === 'allocations' && (
        <section className="space-y-4">
          {/* Table Filters & Search */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-900 p-3 rounded-xl border border-slate-800">
            <div className="flex items-center gap-2 flex-1 max-w-md">
              <Search className="w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search by Ward ID, Locality, or City..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-slate-800 text-xs text-slate-100 placeholder-slate-500 px-3 py-1.5 rounded-lg border border-slate-700 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="flex items-center gap-2 flex-wrap text-xs">
              {/* City filter */}
              <select
                value={cityFilter}
                onChange={(e) => setCityFilter(e.target.value)}
                className="bg-slate-800 text-slate-200 border border-slate-700 px-2.5 py-1.5 rounded-lg focus:outline-none"
              >
                <option value="ALL">All Cities (60 Wards)</option>
                <option value="Dhaka North">Dhaka North (DNCC)</option>
                <option value="Dhaka South">Dhaka South (DSCC)</option>
                <option value="Chattogram">Chattogram (CCC)</option>
                <option value="Gazipur">Gazipur (GCC)</option>
                <option value="Narayanganj">Narayanganj (NCC)</option>
              </select>

              {/* Risk filter */}
              <select
                value={riskFilter}
                onChange={(e) => setRiskFilter(e.target.value)}
                className="bg-slate-800 text-slate-200 border border-slate-700 px-2.5 py-1.5 rounded-lg focus:outline-none"
              >
                <option value="ALL">All Risk Levels</option>
                <option value="High">High Risk Only</option>
                <option value="Medium">Medium Risk Only</option>
                <option value="Low">Low Risk Only</option>
              </select>

              {/* Shortage filter */}
              <select
                value={shortageFilter}
                onChange={(e) => setShortageFilter(e.target.value)}
                className="bg-slate-800 text-slate-200 border border-slate-700 px-2.5 py-1.5 rounded-lg focus:outline-none"
              >
                <option value="ALL">All Statuses</option>
                <option value="CRITICAL">Critical Deficit Only</option>
                <option value="CREW_SHORTAGE">Crew Shortage Only</option>
              </select>

              <span className="text-slate-500 text-[11px] font-semibold">
                Showing {filteredWards.length} of 60 Wards
              </span>
            </div>
          </div>

          {/* Table Container */}
          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900 shadow-xl">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950 text-slate-400 font-bold uppercase tracking-wider text-[11px] border-b border-slate-800">
                <tr>
                  <th className="py-3 px-3 cursor-pointer" onClick={() => { setSortField('priority_ranking'); setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc'); }}>
                    Rank <ArrowUpDown className="inline w-3 h-3" />
                  </th>
                  <th className="py-3 px-3">Ward & Locality</th>
                  <th className="py-3 px-3 cursor-pointer" onClick={() => { setSortField('priority_score'); setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc'); }}>
                    Priority Score <ArrowUpDown className="inline w-3 h-3" />
                  </th>
                  <th className="py-3 px-3">Risk Level</th>
                  <th className="py-3 px-3 cursor-pointer" onClick={() => { setSortField('total_predicted_cases'); setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc'); }}>
                    Cases (2W) <ArrowUpDown className="inline w-3 h-3" />
                  </th>
                  <th className="py-3 px-3">Saline (Dem / Alloc)</th>
                  <th className="py-3 px-3">Kits (Dem / Alloc)</th>
                  <th className="py-3 px-3">Beds (Dem / Alloc)</th>
                  <th className="py-3 px-3">Crews (Req / Alloc)</th>
                  <th className="py-3 px-3 text-center">Deficit Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {filteredWards.map((w) => {
                  const isHighPriority = w.priority_ranking <= 10;
                  const hasShortage = w.has_critical_deficit;
                  return (
                    <tr
                      key={w.ward_id}
                      className={`hover:bg-slate-800/50 transition ${
                        hasShortage && w.risk_level === 'High' ? 'bg-red-950/20' : isHighPriority ? 'bg-slate-900/80' : ''
                      }`}
                    >
                      <td className="py-2.5 px-3">
                        <span className={`font-mono font-bold px-2 py-0.5 rounded text-[11px] ${
                          w.priority_ranking <= 5 ? 'bg-red-950 text-red-300 border border-red-800' :
                          w.priority_ranking <= 20 ? 'bg-cyan-950 text-cyan-300 border border-cyan-800' :
                          'bg-slate-800 text-slate-400'
                        }`}>
                          #{w.priority_ranking}
                        </span>
                      </td>

                      <td className="py-2.5 px-3">
                        <div className="font-bold text-white text-xs">{w.ward_id}</div>
                        <div className="text-[11px] text-slate-400">{w.locality} • <span className="text-slate-500">{w.city}</span></div>
                      </td>

                      <td className="py-2.5 px-3 font-mono font-bold text-cyan-400">
                        {w.priority_score.toFixed(4)}
                        <span className="block text-[10px] text-slate-500 font-normal">
                          (0.7×{w.risk_score} + 0.3×{w.normalized_density.toFixed(2)})
                        </span>
                      </td>

                      <td className="py-2.5 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase tracking-wider ${
                          w.risk_level === 'High' ? 'bg-red-900/60 text-red-300 border border-red-700' :
                          w.risk_level === 'Medium' ? 'bg-amber-900/60 text-amber-300 border border-amber-700' :
                          'bg-emerald-900/60 text-emerald-300 border border-emerald-700'
                        }`}>
                          {w.risk_level}
                        </span>
                      </td>

                      <td className="py-2.5 px-3 font-bold text-white">
                        {w.total_predicted_cases}
                        <span className="block text-[10px] text-slate-500 font-normal">
                          W1: {w.predicted_cases_w1} | W2: {w.predicted_cases_w2}
                        </span>
                      </td>

                      <td className="py-2.5 px-3">
                        <div className="flex items-center gap-1.5">
                          <span className="text-slate-400">{w.saline_demand}</span>
                          <span className="text-slate-600">/</span>
                          <span className={`font-bold ${w.remaining_saline_deficit > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                            {w.approved_saline_allocation}
                          </span>
                        </div>
                        <div className="w-16 bg-slate-800 h-1 rounded mt-1 overflow-hidden">
                          <div
                            className={`h-full ${w.remaining_saline_deficit > 0 ? 'bg-red-500' : 'bg-emerald-500'}`}
                            style={{ width: `${Math.min(100, w.saline_fulfillment_pct)}%` }}
                          />
                        </div>
                      </td>

                      <td className="py-2.5 px-3">
                        <div className="flex items-center gap-1.5">
                          <span className="text-slate-400">{w.kits_demand}</span>
                          <span className="text-slate-600">/</span>
                          <span className={`font-bold ${w.remaining_kits_deficit > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                            {w.approved_kits_allocation}
                          </span>
                        </div>
                        <div className="w-16 bg-slate-800 h-1 rounded mt-1 overflow-hidden">
                          <div
                            className={`h-full ${w.remaining_kits_deficit > 0 ? 'bg-red-500' : 'bg-emerald-500'}`}
                            style={{ width: `${Math.min(100, w.kits_fulfillment_pct)}%` }}
                          />
                        </div>
                      </td>

                      <td className="py-2.5 px-3">
                        <div className="flex items-center gap-1.5">
                          <span className="text-slate-400">{w.beds_demand}</span>
                          <span className="text-slate-600">/</span>
                          <span className={`font-bold ${w.remaining_beds_deficit > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                            {w.approved_beds_allocation}
                          </span>
                        </div>
                        <div className="w-16 bg-slate-800 h-1 rounded mt-1 overflow-hidden">
                          <div
                            className={`h-full ${w.remaining_beds_deficit > 0 ? 'bg-red-500' : 'bg-emerald-500'}`}
                            style={{ width: `${Math.min(100, w.beds_fulfillment_pct)}%` }}
                          />
                        </div>
                      </td>

                      <td className="py-2.5 px-3">
                        <div className="flex items-center gap-1.5">
                          <span className="text-slate-400">{w.required_crews}</span>
                          <span className="text-slate-600">/</span>
                          <span className={`font-bold ${w.crew_deficit > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                            {w.approved_crew_allocation}
                          </span>
                        </div>
                        <div className="w-16 bg-slate-800 h-1 rounded mt-1 overflow-hidden">
                          <div
                            className={`h-full ${w.crew_deficit > 0 ? 'bg-red-500' : 'bg-emerald-500'}`}
                            style={{ width: `${Math.min(100, w.crew_fulfillment_pct)}%` }}
                          />
                        </div>
                      </td>

                      <td className="py-2.5 px-3 text-center">
                        {hasShortage ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-red-950 text-red-400 border border-red-800">
                            <AlertTriangle className="w-3 h-3 text-red-400" />
                            DEFICIT
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">
                            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                            FULFILLED
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* 6. TAB 2: Geographical Map */}
      {activeTab === 'map' && (
        <section className="space-y-3">
          <div className="flex justify-between items-center text-xs text-slate-400">
            <span>Displaying all 60 monitored urban wards across Bangladesh with exact centroid coordinates.</span>
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-red-500"></span> High Risk</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span> Medium Risk</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> Low Risk</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full border-2 border-red-500 bg-transparent"></span> Supply Deficit</span>
            </div>
          </div>
          <div className="w-full h-[620px] rounded-xl border border-slate-800 overflow-hidden shadow-2xl relative">
            <div ref={mapContainerRef} className="w-full h-full" />
          </div>
        </section>
      )}

      {/* 7. TAB 3: Hospital Bed Overflow Routing */}
      {activeTab === 'hospital' && (
        <section className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Bed className="w-4 h-4 text-cyan-400" />
              Capacity-Constrained Greedy Routing for Inpatient Bed Overflow
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Treats hospital beds as fixed ward-level physical assets. Wards with localized inpatient shortages are dynamically routed
              to the nearest surplus medical facilities using Haversine great-circle distances.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {(allocationData?.hospital_overflow_routes || []).map((route, i) => (
              <div key={i} className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3 hover:border-cyan-800 transition">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-[10px] font-bold text-red-400 uppercase tracking-wider">Deficit Ward</span>
                    <h4 className="font-bold text-white text-sm">{route.from_ward_id}</h4>
                    <p className="text-xs text-slate-400">{route.from_locality} ({route.from_city})</p>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-mono font-bold text-cyan-400 bg-cyan-950 px-2 py-0.5 rounded border border-cyan-800">
                      {route.distance_km} km
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-center my-1 text-slate-600">
                  <ArrowRight className="w-4 h-4 text-cyan-400" />
                </div>

                <div>
                  <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">Designated Surplus Hospital</span>
                  <h4 className="font-bold text-white text-sm">{route.to_ward_id}</h4>
                  <p className="text-xs text-slate-400">{route.to_locality} ({route.to_city})</p>
                </div>

                <div className="pt-2 border-t border-slate-800 flex justify-between items-center text-xs">
                  <span className="text-slate-400">Patients Routed:</span>
                  <span className="font-extrabold text-amber-400 text-sm">{route.patients_referred} Inpatient Beds</span>
                </div>

                <p className="text-[11px] text-slate-400 italic bg-slate-950 p-2 rounded border border-slate-800/80">
                  {route.rationale}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 8. TAB 4: Inter-Ward Redistribution Engine */}
      {activeTab === 'redistribution' && (
        <section className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <RefreshCw className="w-4 h-4 text-cyan-400" />
              Intelligent Surplus-to-Deficit Supply Redistribution
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Recommends transferring transferable medical inventory (saline bags and rapid diagnostic kits) from lower-priority surplus wards
              to high-priority deficit wards without inducing new shortages.
            </p>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900 shadow-xl">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950 text-slate-400 font-bold uppercase tracking-wider text-[11px] border-b border-slate-800">
                <tr>
                  <th className="py-3 px-3">Rec ID</th>
                  <th className="py-3 px-3">Resource Type</th>
                  <th className="py-3 px-3">Source (Donor Ward)</th>
                  <th className="py-3 px-3">Destination (Deficit Ward)</th>
                  <th className="py-3 px-3 text-center">Transfer Qty</th>
                  <th className="py-3 px-3">Fulfillment Impact</th>
                  <th className="py-3 px-3 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 font-medium">
                {(allocationData?.redistribution_recommendations || []).map((rec) => (
                  <tr key={rec.recommendation_id} className="hover:bg-slate-800/40">
                    <td className="py-3 px-3 font-mono font-bold text-cyan-400">{rec.recommendation_id}</td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-200 border border-slate-700 font-semibold">
                        {rec.resource_type}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <div className="font-bold text-white">{rec.source_ward_id}</div>
                      <div className="text-[11px] text-slate-400">{rec.source_locality} (Score: {rec.source_priority})</div>
                    </td>
                    <td className="py-3 px-3">
                      <div className="font-bold text-white">{rec.destination_ward_id}</div>
                      <div className="text-[11px] text-slate-400">{rec.destination_locality} (Score: {rec.destination_priority})</div>
                    </td>
                    <td className="py-3 px-3 text-center font-bold text-cyan-400 text-sm">
                      +{rec.recommended_transfer_quantity} Units
                    </td>
                    <td className="py-3 px-3">
                      <div className="text-[11px]">
                        <span className="text-slate-400">Recipient: </span>
                        <span className="text-red-400">{rec.destination_fulfillment_before}%</span> → <span className="text-emerald-400 font-bold">{rec.destination_fulfillment_after}%</span>
                      </div>
                      <div className="text-[11px]">
                        <span className="text-slate-400">Donor retains: </span>
                        <span className="text-emerald-400 font-bold">{rec.source_fulfillment_after}%</span>
                      </div>
                    </td>
                    <td className="py-3 px-3 text-center">
                      <button
                        onClick={() => handleApproveRedistribution(rec)}
                        className="px-3 py-1 bg-emerald-950 hover:bg-emerald-900 text-emerald-300 font-bold text-xs rounded border border-emerald-800 transition"
                      >
                        Authorize Transfer
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* 9. TAB 5: ML Counterfactual Simulator */}
      {activeTab === 'simulation' && (
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              Counterfactual Intervention Simulator
            </h3>
            <p className="text-xs text-slate-400">
              Simulate the biological impact of adulticide spraying and breeding site larvicide suppression
              on forward hospital admissions and resource requirements.
            </p>

            <div className="space-y-3 pt-2">
              <div>
                <label className="text-xs text-slate-300 font-semibold block mb-1">Target Ward:</label>
                <select
                  value={simWardId}
                  onChange={(e) => {
                    setSimWardId(e.target.value);
                    runCounterfactual(e.target.value, simCrews, simLarvicide);
                  }}
                  className="w-full bg-slate-800 text-xs text-slate-200 border border-slate-700 p-2 rounded-lg"
                >
                  {(allocationData?.wards || []).map((w) => (
                    <option key={w.ward_id} value={w.ward_id}>
                      {w.ward_id} — {w.locality} ({w.city})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <div className="flex justify-between text-xs text-slate-300 mb-1">
                  <span>Spraying Crews Deployed:</span>
                  <span className="font-bold text-cyan-400">{simCrews} Crews</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="12"
                  value={simCrews}
                  onChange={(e) => {
                    const val = Number(e.target.value);
                    setSimCrews(val);
                    runCounterfactual(simWardId, val, simLarvicide);
                  }}
                  className="w-full accent-cyan-400"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs text-slate-300 mb-1">
                  <span>Larviciding Coverage:</span>
                  <span className="font-bold text-emerald-400">{simLarvicide}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={simLarvicide}
                  onChange={(e) => {
                    const val = Number(e.target.value);
                    setSimLarvicide(val);
                    runCounterfactual(simWardId, simCrews, val);
                  }}
                  className="w-full accent-emerald-400"
                />
              </div>
            </div>
          </div>

          {/* Impact Results */}
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-4">
            <h4 className="text-sm font-bold text-white">Simulated Intervention Epidemiological Outcome</h4>

            {counterfactualResult && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <div className="text-[11px] text-slate-400 uppercase">Averted Cases</div>
                    <div className="text-2xl font-black text-emerald-400 mt-1">
                      {counterfactualResult.intervention_impact.averted_cases}
                    </div>
                    <div className="text-[10px] text-emerald-500 font-bold">
                      -{counterfactualResult.intervention_impact.case_reduction_pct}% Transmission Drop
                    </div>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <div className="text-[11px] text-slate-400 uppercase">Saved Saline</div>
                    <div className="text-2xl font-black text-cyan-400 mt-1">
                      +{counterfactualResult.intervention_impact.saline_bags_saved}
                    </div>
                    <div className="text-[10px] text-slate-400">Bags Preserved</div>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <div className="text-[11px] text-slate-400 uppercase">Saved Kits</div>
                    <div className="text-2xl font-black text-purple-400 mt-1">
                      +{counterfactualResult.intervention_impact.diagnostic_kits_saved}
                    </div>
                    <div className="text-[10px] text-slate-400">Rapid Test Units</div>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <div className="text-[11px] text-slate-400 uppercase">Hospital Beds</div>
                    <div className="text-2xl font-black text-amber-400 mt-1">
                      +{counterfactualResult.intervention_impact.hospital_beds_saved}
                    </div>
                    <div className="text-[10px] text-slate-400">Surge Beds Averted</div>
                  </div>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs space-y-2">
                  <div className="font-bold text-slate-300">Baseline vs Intervened Trajectory:</div>
                  <div className="grid grid-cols-2 gap-4 text-slate-400">
                    <div>
                      <span className="block font-semibold text-slate-300">Baseline Case Count:</span>
                      W1: {counterfactualResult.original_forecast.week_1} | W2: {counterfactualResult.original_forecast.week_2} | Total: {counterfactualResult.original_forecast.total_cases}
                    </div>
                    <div>
                      <span className="block font-semibold text-emerald-400">Intervened Counterfactual:</span>
                      W1: {counterfactualResult.counterfactual_forecast.week_1} | W2: {counterfactualResult.counterfactual_forecast.week_2} | Total: {counterfactualResult.counterfactual_forecast.total_cases}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* 10. TAB 6: Audit Trail & Dispatches */}
      {activeTab === 'audit' && (
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Audit Logs */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
            <div className="flex justify-between items-center pb-2 border-b border-slate-800">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Clock className="w-4 h-4 text-cyan-400" />
                Immutable Government Audit Trail
              </h3>
              <span className="text-xs text-slate-500 font-mono">SQLite Persistent Store</span>
            </div>

            <div className="space-y-2.5 max-h-[500px] overflow-y-auto pr-1">
              {auditLogs.map((log) => (
                <div key={log.id} className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs space-y-1">
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-cyan-400 font-mono text-[11px]">{log.action}</span>
                    <span className="text-[10px] text-slate-500 font-mono">{log.timestamp}</span>
                  </div>
                  <p className="text-slate-300">{log.details}</p>
                  <div className="text-[10px] text-slate-500">Signatory: {log.user}</div>
                </div>
              ))}
            </div>
          </div>

          {/* SMS / WhatsApp Notifications */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
            <div className="flex justify-between items-center pb-2 border-b border-slate-800">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Send className="w-4 h-4 text-emerald-400" />
                Deterministic Field Dispatches & Notifications
              </h3>
              <span className="text-xs text-emerald-400 font-mono">SMS & WhatsApp</span>
            </div>

            <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
              {notifications.map((notif, i) => (
                <div key={i} className="bg-slate-950 p-3.5 rounded-lg border border-slate-800 space-y-2">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold text-emerald-400">{notif.title}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300">
                      {notif.channel}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400">Target: {notif.recipient_role}</div>
                  <pre className="text-[11px] bg-slate-900 text-slate-200 p-2.5 rounded border border-slate-800 font-mono whitespace-pre-wrap leading-relaxed">
                    {notif.message}
                  </pre>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(notif.message);
                      alert('Notification message copied to clipboard.');
                    }}
                    className="text-[11px] text-cyan-400 hover:underline flex items-center gap-1 font-semibold"
                  >
                    Copy Broadcast Template
                  </button>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Modal for Approval Confirmation */}
      {approvalModalOpen && approvalStatus && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-cyan-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-8 h-8 text-emerald-400" />
              <div>
                <h3 className="text-lg font-bold text-white">Plan Officially Approved</h3>
                <p className="text-xs text-slate-400">Registry ID: #{approvalStatus.plan_id}</p>
              </div>
            </div>

            <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 text-xs space-y-2 text-slate-300">
              <div><b>Plan Name:</b> {approvalStatus.plan_name}</div>
              <div><b>Approving Authority:</b> {approvalStatus.approved_by}</div>
              <div><b>Timestamp:</b> {approvalStatus.approved_at}</div>
              <div><b>Critical Deficits Logged:</b> {approvalStatus.critical_deficits_count} Wards</div>
            </div>

            <p className="text-xs text-slate-400">
              The plan has been committed to the persistent SQLite database and logged in the immutable audit trail.
            </p>

            <button
              onClick={() => setApprovalModalOpen(false)}
              className="w-full py-2 bg-cyan-600 hover:bg-cyan-500 font-bold text-xs text-white rounded-lg transition"
            >
              Close Confirmation
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

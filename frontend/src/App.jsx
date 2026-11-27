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
  ArrowRight,
  Copy,
  Check,
  FileText
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

  // Hospital Surge & Overflow Routing State
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
      if (data.hospital_routing) {
        setHospitalRoutingData(data.hospital_routing);
      }
    } catch (err) {
      console.error('Failed to load allocation data:', err);
    } finally {
      setSimulating(false);
      setLoading(false);
    }
  };

  const fetchHospitalRouting = async (stock = stockPercentage, customDemand = null, customCapacity = null) => {
    try {
      setSimulating(true);
      let res;
      if (customDemand || customCapacity) {
        res = await fetch('/api/hospital-routing/simulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            stock_percentage: stock,
            custom_bed_demand: customDemand || {},
            custom_bed_capacity: customCapacity || {},
            scenario_name: 'Interactive Hospital Surge Simulation',
          }),
        });
      } else {
        res = await fetch(`/api/hospital-routing/current?stock_percentage=${stock}`);
      }
      const data = await res.json();
      setHospitalRoutingData(data);
    } catch (err) {
      console.error('Failed to load hospital routing data:', err);
    } finally {
      setSimulating(false);
    }
  };

  const handleApproveHospitalPlan = async () => {
    try {
      setSimulating(true);
      const res = await fetch('/api/hospital-routing/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plan_name: `Government Hospital Routing Plan (${stockPercentage}% Capacity)`,
          approved_by: 'Central Health Administrator',
          stock_percentage: stockPercentage,
          custom_bed_demand: Object.keys(hospitalCustomDemand).length > 0 ? hospitalCustomDemand : null,
          custom_bed_capacity: Object.keys(hospitalCustomCapacity).length > 0 ? hospitalCustomCapacity : null,
        }),
      });
      const data = await res.json();
      setApprovedHospitalPlanMsg(data.message || 'Hospital routing plan approved.');
      fetchAuditLogs();
      setTimeout(() => setApprovedHospitalPlanMsg(null), 6000);
    } catch (err) {
      console.error('Failed to approve hospital plan:', err);
    } finally {
      setSimulating(false);
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

      {/* 7. TAB 3: Hospital Surge & Cross-Ward Overflow Routing */}
      {activeTab === 'hospital' && (() => {
        const hData = hospitalRoutingData || allocationData?.hospital_routing || {};
        const hReg = hData?.regional_summary || {};
        const hCities = hData?.city_results || [];
        const hWards = hData?.ward_results || [];
        const hRoutes = hData?.routing_assignments || [];
        const hWarnings = hData?.critical_warnings || [];
        const hNotices = hData?.dispatch_notices || [];

        // Filter and sort for ward-wise hospital capacity table
        const filteredHWards = hWards.filter((w) => {
          const matchCity = hospitalTableCity === 'ALL' || w.city === hospitalTableCity;
          const matchSearch =
            !hospitalTableSearch ||
            w.ward_id.toLowerCase().includes(hospitalTableSearch.toLowerCase()) ||
            (w.ward_name && w.ward_name.toLowerCase().includes(hospitalTableSearch.toLowerCase())) ||
            (w.locality && w.locality.toLowerCase().includes(hospitalTableSearch.toLowerCase()));
          const matchStatus =
            hospitalTableStatus === 'ALL' ||
            (hospitalTableStatus === 'CRITICAL' && w.critical_hospital_warning) ||
            w.hospital_surge_status === hospitalTableStatus;
          return matchCity && matchSearch && matchStatus;
        }).sort((a, b) => {
          let vA = a[hospitalTableSort];
          let vB = b[hospitalTableSort];
          if (vA === undefined || vA === null) vA = 0;
          if (vB === undefined || vB === null) vB = 0;
          if (typeof vA === 'string') {
            return hospitalTableSortAsc ? vA.localeCompare(vB) : vB.localeCompare(vA);
          }
          return hospitalTableSortAsc ? vA - vB : vB - vA;
        });

        // Chart data: City Bed Demand vs Effective Capacity
        const cityBarData = hCities.map((c) => ({
          name: c.city,
          Demand: c.total_bed_demand,
          Capacity: c.total_effective_bed_capacity,
          NetDeficit: c.net_bed_deficit,
          Routed: c.total_routed_overflow,
        }));

        // Chart data: City Utilization Before vs After
        const cityUtilData = hCities.map((c) => ({
          name: c.city,
          InitialUtil: c.initial_bed_utilization || 0,
          FinalUtil: c.final_bed_utilization || 0,
          DemandPressure: c.demand_pressure || 0,
        }));

        return (
          <section className="space-y-5">
            {/* Success notification banner */}
            {approvedHospitalPlanMsg && (
              <div className="bg-emerald-950/80 border border-emerald-600 text-emerald-200 px-4 py-3 rounded-xl flex items-center justify-between shadow-lg">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  <span className="text-sm font-semibold">{approvedHospitalPlanMsg}</span>
                </div>
                <button
                  onClick={() => setApprovedHospitalPlanMsg(null)}
                  className="text-xs bg-emerald-900 hover:bg-emerald-800 text-emerald-100 px-2 py-1 rounded"
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* Critical Hospital Surge Warning Banner */}
            {hWarnings.length > 0 && (
              <div className="bg-red-950/80 border-2 border-red-600 rounded-xl p-4 shadow-xl shadow-red-950/40">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-6 h-6 text-red-400 flex-shrink-0 mt-0.5" />
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-extrabold text-red-200 uppercase tracking-wider">
                        Critical Hospital Surge Alert — Unresolved Inpatient Bed Deficits
                      </h4>
                      <span className="text-xs bg-red-900/90 text-red-100 font-bold px-2.5 py-0.5 rounded-full border border-red-700">
                        {hWarnings.length} Active Warnings
                      </span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 mt-2">
                      {hWarnings.slice(0, 6).map((warn, idx) => (
                        <div key={idx} className="bg-slate-900/90 border border-red-800/80 p-2.5 rounded-lg text-xs">
                          <div className="flex justify-between items-center font-bold text-white">
                            <span>{warn.entity_name} ({warn.city})</span>
                            <span className="text-red-400 font-mono">+{warn.net_deficit} Beds Short</span>
                          </div>
                          <p className="text-[11px] text-slate-300 mt-1">{warn.recommended_action}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Main Header & Controls Bar */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              <div>
                <h3 className="text-base font-extrabold text-white flex items-center gap-2">
                  <Bed className="w-5 h-5 text-cyan-400" />
                  Hospital Surge Detection & City-Constrained Overflow Routing
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  Enforces strict same-city capacity-constrained greedy routing across 60 urban wards in 5 city corporations.
                  Prioritizes source wards by <code className="text-cyan-300 font-mono">(0.7×Risk + 0.3×Density)</code> and routes to lowest-utilization destination wards.
                </p>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <button
                  onClick={() => setHospitalSimulatorOpen(!hospitalSimulatorOpen)}
                  className={`flex items-center gap-1.5 px-3 py-2 text-xs font-bold rounded-lg border transition ${
                    hospitalSimulatorOpen
                      ? 'bg-cyan-900 text-cyan-200 border-cyan-500'
                      : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700'
                  }`}
                >
                  <Sliders className="w-3.5 h-3.5 text-cyan-400" />
                  {hospitalSimulatorOpen ? 'Close Simulator' : 'Interactive Simulator'}
                </button>

                <button
                  onClick={() => setHospitalNoticesOpen(true)}
                  className="flex items-center gap-1.5 px-3 py-2 text-xs font-bold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
                >
                  <FileText className="w-3.5 h-3.5 text-amber-400" />
                  Dispatch Notices ({hNotices.length})
                </button>

                <button
                  onClick={handleApproveHospitalPlan}
                  disabled={simulating}
                  className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-extrabold rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-lg shadow-emerald-950 transition"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Approve Routing Plan
                </button>
              </div>
            </div>

            {/* Regional Hospital Overview: 10 KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl">
                <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Bed Demand</div>
                <div className="text-2xl font-extrabold text-cyan-400 mt-1">{hReg.total_projected_bed_demand || 0}</div>
                <div className="text-[10px] text-slate-500 mt-0.5">Projected Concurrent Need</div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl">
                <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Effective Capacity</div>
                <div className="text-2xl font-extrabold text-white mt-1">{hReg.total_effective_bed_capacity || 0}</div>
                <div className="text-[10px] text-slate-500 mt-0.5">Avail: {hReg.total_original_bed_availability || 0} beds</div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl">
                <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Initial Bed Deficit</div>
                <div className="text-2xl font-extrabold text-amber-400 mt-1">{hReg.total_initial_bed_deficit || 0}</div>
                <div className="text-[10px] text-slate-500 mt-0.5">Across overloaded wards</div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl">
                <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Routed Overflow</div>
                <div className="text-2xl font-extrabold text-emerald-400 mt-1">{hReg.total_routed_overflow || 0}</div>
                <div className="text-[10px] text-slate-500 mt-0.5">Accommodated in same city</div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl">
                <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Net Unresolved Deficit</div>
                <div className={`text-2xl font-extrabold mt-1 ${(hReg.total_unresolved_bed_deficit || 0) > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                  {hReg.total_unresolved_bed_deficit || 0}
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">
                  Resolution: {hReg.overall_shortage_resolution_percentage !== null ? `${hReg.overall_shortage_resolution_percentage}%` : 'N/A'}
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl">
                <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Overloaded Wards</div>
                <div className="text-2xl font-extrabold text-amber-400 mt-1">{hReg.total_overloaded_wards || 0}</div>
                <div className="text-[10px] text-slate-500 mt-0.5">Demand &gt; Capacity</div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl">
                <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Lower-Burden Wards</div>
                <div className="text-2xl font-extrabold text-emerald-400 mt-1">{hReg.total_lower_burden_wards || 0}</div>
                <div className="text-[10px] text-slate-500 mt-0.5">Available destination wards</div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl">
                <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Available Spare Beds</div>
                <div className="text-2xl font-extrabold text-teal-400 mt-1">{hReg.total_available_spare_beds || 0}</div>
                <div className="text-[10px] text-slate-500 mt-0.5">Initial surplus pool</div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl">
                <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Regional Utilization</div>
                <div className="text-2xl font-extrabold text-purple-400 mt-1">
                  {hReg.final_regional_utilization ? `${hReg.final_regional_utilization}%` : '0%'}
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">Initial: {hReg.initial_regional_utilization || 0}%</div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl">
                <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Critical Warning Wards</div>
                <div className={`text-2xl font-extrabold mt-1 ${(hReg.critical_warning_wards_count || 0) > 0 ? 'text-red-400' : 'text-slate-400'}`}>
                  {hReg.critical_warning_wards_count || 0}
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">Require emergency beds</div>
              </div>
            </div>

            {/* Interactive Hospital Overflow Simulator Drawer */}
            {hospitalSimulatorOpen && (
              <div className="bg-slate-900 border border-cyan-700/60 rounded-xl p-4 space-y-4 shadow-2xl">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div>
                    <h4 className="text-sm font-bold text-cyan-300 flex items-center gap-2">
                      <Sliders className="w-4 h-4 text-cyan-400" />
                      Interactive Hospital Bed Demand & Capacity Simulator
                    </h4>
                    <p className="text-xs text-slate-400">
                      Simulate hypothetical disease surges or hospital capacity bottlenecks. Changes execute in-memory through the local backend and never overwrite original dataset values.
                    </p>
                  </div>
                  <span className="text-[10px] font-mono font-bold bg-cyan-950 text-cyan-300 px-2.5 py-1 rounded border border-cyan-800">
                    SIMULATION MODE
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div>
                    <label className="text-xs font-semibold text-slate-300 mb-1 block">Target City</label>
                    <select
                      value={hospitalSimCity}
                      onChange={(e) => {
                        const newCity = e.target.value;
                        setHospitalSimCity(newCity);
                        const firstWardInCity = hWards.find((w) => w.city === newCity);
                        if (firstWardInCity) setHospitalSimWard(firstWardInCity.ward_id);
                      }}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    >
                      {['Chattogram', 'Dhaka North', 'Dhaka South', 'Gazipur', 'Narayanganj'].map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300 mb-1 block">Target Ward</label>
                    <select
                      value={hospitalSimWard}
                      onChange={(e) => setHospitalSimWard(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    >
                      {hWards
                        .filter((w) => w.city === hospitalSimCity)
                        .map((w) => (
                          <option key={w.ward_id} value={w.ward_id}>
                            {w.ward_id} - {w.locality}
                          </option>
                        ))}
                    </select>
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300 mb-1 block">
                      Simulated Bed Demand (Required)
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="500"
                      value={
                        hospitalCustomDemand[hospitalSimWard] !== undefined
                          ? hospitalCustomDemand[hospitalSimWard]
                          : (hWards.find((w) => w.ward_id === hospitalSimWard)?.hospital_beds_required || 0)
                      }
                      onChange={(e) => {
                        const val = parseInt(e.target.value, 10) || 0;
                        setHospitalCustomDemand({ ...hospitalCustomDemand, [hospitalSimWard]: val });
                      }}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300 mb-1 block">
                      Simulated Usable Bed Capacity
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="500"
                      value={
                        hospitalCustomCapacity[hospitalSimWard] !== undefined
                          ? hospitalCustomCapacity[hospitalSimWard]
                          : (hWards.find((w) => w.ward_id === hospitalSimWard)?.hospital_beds_effective_capacity || 0)
                      }
                      onChange={(e) => {
                        const val = parseInt(e.target.value, 10) || 0;
                        setHospitalCustomCapacity({ ...hospitalCustomCapacity, [hospitalSimWard]: val });
                      }}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    onClick={() => {
                      setHospitalCustomDemand({});
                      setHospitalCustomCapacity({});
                      fetchHospitalRouting(stockPercentage, null, null);
                    }}
                    className="px-3 py-1.5 text-xs text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition"
                  >
                    Reset to Dataset Baseline
                  </button>
                  <button
                    onClick={() => {
                      fetchHospitalRouting(stockPercentage, hospitalCustomDemand, hospitalCustomCapacity);
                    }}
                    className="px-4 py-1.5 text-xs font-bold bg-cyan-600 hover:bg-cyan-500 text-slate-950 rounded-lg transition shadow-md"
                  >
                    Recalculate Routing Simulation
                  </button>
                </div>
              </div>
            )}

            {/* Visualizations Section: 2 Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Chart 1: Bed Demand vs Capacity by City */}
              <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <h4 className="text-xs font-bold text-slate-300 mb-3 flex items-center justify-between">
                  <span>Hospital Bed Demand vs Effective Capacity by City</span>
                  <span className="text-[10px] text-slate-500 font-normal">Independent City Networks</span>
                </h4>
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={cityBarData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                      <XAxis dataKey="name" stroke="#64748B" fontSize={10} />
                      <YAxis stroke="#64748B" fontSize={10} />
                      <Tooltip contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', fontSize: '11px' }} />
                      <Legend wrapperStyle={{ fontSize: '10px' }} />
                      <Bar dataKey="Demand" fill="#06B6D4" name="Projected Demand" />
                      <Bar dataKey="Capacity" fill="#10B981" name="Effective Capacity" />
                      <Bar dataKey="NetDeficit" fill="#EF4444" name="Unresolved Deficit" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Chart 2: City Bed Utilization Before vs After Routing */}
              <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <h4 className="text-xs font-bold text-slate-300 mb-3 flex items-center justify-between">
                  <span>City Bed Utilization: Before vs After Cross-Ward Routing</span>
                  <span className="text-[10px] text-slate-500 font-normal">Cap: 100% Maximum</span>
                </h4>
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={cityUtilData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                      <XAxis dataKey="name" stroke="#64748B" fontSize={10} />
                      <YAxis domain={[0, 120]} stroke="#64748B" fontSize={10} unit="%" />
                      <Tooltip contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', fontSize: '11px' }} />
                      <Legend wrapperStyle={{ fontSize: '10px' }} />
                      <Bar dataKey="InitialUtil" fill="#94A3B8" name="Initial Utilization (%)" />
                      <Bar dataKey="FinalUtil" fill="#A855F7" name="Post-Routing Utilization (%)" />
                      <Bar dataKey="DemandPressure" fill="#F59E0B" name="Demand Pressure (%)" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* City-Wise Hospital Network Summary Cards */}
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                City-Constrained Network Summaries (Strict Local Routing)
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                {hCities.map((city) => (
                  <div
                    key={city.city}
                    className={`bg-slate-900 border rounded-xl p-3 space-y-2 transition ${
                      city.net_bed_deficit > 0 ? 'border-red-900/80 hover:border-red-700' : 'border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <h5 className="font-bold text-white text-xs">{city.city}</h5>
                      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                        city.net_bed_deficit > 0 ? 'bg-red-950 text-red-300 border border-red-800' : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      }`}>
                        {city.net_bed_deficit > 0 ? 'SURGE' : 'BALANCED'}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-1 text-[11px] pt-1 border-t border-slate-800/80">
                      <span className="text-slate-400">Demand / Cap:</span>
                      <span className="text-right text-slate-200 font-mono">{city.total_bed_demand} / {city.total_effective_bed_capacity}</span>
                      <span className="text-slate-400">Routed Overflow:</span>
                      <span className="text-right text-emerald-400 font-mono">+{city.total_routed_overflow}</span>
                      <span className="text-slate-400">Net Deficit:</span>
                      <span className={`text-right font-bold font-mono ${city.net_bed_deficit > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                        {city.net_bed_deficit}
                      </span>
                      <span className="text-slate-400">Final Util:</span>
                      <span className="text-right text-purple-300 font-mono">{city.final_bed_utilization || 0}%</span>
                    </div>

                    {city.critical_warning && (
                      <div className="text-[10px] text-red-300/90 bg-red-950/50 p-1.5 rounded border border-red-900/60 leading-tight">
                        {city.critical_warning}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Automatic Cross-Ward Overflow Routing Table */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    <ArrowRight className="w-4 h-4 text-cyan-400" />
                    Automatic Cross-Ward Overflow Routing Assignments
                  </h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Deterministic assignments matching source deficit with lowest-utilization destination wards within the same city.
                  </p>
                </div>
                <span className="text-xs bg-cyan-950 text-cyan-300 px-2.5 py-1 rounded-full border border-cyan-800 font-mono">
                  {hRoutes.length} Active Routes
                </span>
              </div>

              {hRoutes.length === 0 ? (
                <div className="text-center py-6 text-xs text-slate-500 bg-slate-950 rounded-lg">
                  No cross-ward overflow routing necessary for current capacity parameters.
                </div>
              ) : (
                <div className="overflow-x-auto rounded-lg border border-slate-800">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-slate-950 text-slate-400 font-bold uppercase tracking-wider text-[10px] border-b border-slate-800">
                      <tr>
                        <th className="py-2.5 px-3">Source Ward</th>
                        <th className="py-2.5 px-3">Destination Hospital</th>
                        <th className="py-2.5 px-3">City</th>
                        <th className="py-2.5 px-3 text-center">Priority</th>
                        <th className="py-2.5 px-3 text-center">Source Deficit</th>
                        <th className="py-2.5 px-3 text-center">Assigned Overflow</th>
                        <th className="py-2.5 px-3 text-center">Dest Spare</th>
                        <th className="py-2.5 px-3 text-center">Dest Util After</th>
                        <th className="py-2.5 px-3 text-center">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/80">
                      {hRoutes.map((r, i) => (
                        <tr key={i} className="hover:bg-slate-800/50 transition">
                          <td className="py-2 px-3 font-semibold text-white">
                            <div>{r.source_ward_id}</div>
                            <div className="text-[10px] text-slate-400">{r.source_ward_name}</div>
                          </td>
                          <td className="py-2 px-3 font-semibold text-emerald-300">
                            <div>{r.destination_ward_id}</div>
                            <div className="text-[10px] text-slate-400">{r.destination_ward_name} ({r.distance_km ? `${r.distance_km} km` : 'Same City'})</div>
                          </td>
                          <td className="py-2 px-3 text-slate-300">{r.city}</td>
                          <td className="py-2 px-3 text-center font-mono text-cyan-300">{r.source_priority_score}</td>
                          <td className="py-2 px-3 text-center font-mono text-slate-400">
                            {r.source_deficit_before} &rarr; <span className="text-white font-bold">{r.source_deficit_after}</span>
                          </td>
                          <td className="py-2 px-3 text-center font-bold text-amber-400 font-mono">
                            +{r.routed_overflow} Beds
                          </td>
                          <td className="py-2 px-3 text-center font-mono text-slate-400">
                            {r.destination_spare_before} &rarr; <span className="text-white">{r.destination_spare_after}</span>
                          </td>
                          <td className="py-2 px-3 text-center font-mono text-purple-300">
                            {r.destination_utilization_after ? `${r.destination_utilization_after}%` : '100%'}
                          </td>
                          <td className="py-2 px-3 text-center">
                            <span className="bg-emerald-950 text-emerald-300 text-[10px] px-2 py-0.5 rounded font-bold border border-emerald-800">
                              {r.approval_status || 'Recommended'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Ward-Wise Hospital Capacity Table (All 60 Wards) */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div>
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-cyan-400" />
                    Ward-Wise Hospital Capacity & Routing Status (All 60 Wards)
                  </h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Comprehensive ledger tracking initial deficits, cross-ward routing flows, net deficits, and post-routing bed utilization.
                  </p>
                </div>

                {/* Filters */}
                <div className="flex items-center gap-2 flex-wrap">
                  <div className="flex items-center gap-1.5 bg-slate-950 border border-slate-800 px-2.5 py-1.5 rounded-lg text-xs">
                    <Search className="w-3.5 h-3.5 text-slate-500" />
                    <input
                      type="text"
                      placeholder="Search ward or locality..."
                      value={hospitalTableSearch}
                      onChange={(e) => setHospitalTableSearch(e.target.value)}
                      className="bg-transparent text-white focus:outline-none text-xs w-36"
                    />
                  </div>

                  <select
                    value={hospitalTableCity}
                    onChange={(e) => setHospitalTableCity(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
                  >
                    <option value="ALL">All Cities (5)</option>
                    <option value="Dhaka North">Dhaka North (20)</option>
                    <option value="Dhaka South">Dhaka South (20)</option>
                    <option value="Chattogram">Chattogram (10)</option>
                    <option value="Gazipur">Gazipur (5)</option>
                    <option value="Narayanganj">Narayanganj (5)</option>
                  </select>

                  <select
                    value={hospitalTableStatus}
                    onChange={(e) => setHospitalTableStatus(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
                  >
                    <option value="ALL">All Surge Statuses</option>
                    <option value="Overloaded">Overloaded</option>
                    <option value="Fully Utilized">Fully Utilized</option>
                    <option value="Lower-Burden">Lower-Burden</option>
                    <option value="CRITICAL">Critical Warning</option>
                  </select>
                </div>
              </div>

              <div className="overflow-x-auto rounded-lg border border-slate-800 max-h-[460px] overflow-y-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950 text-slate-400 font-bold uppercase tracking-wider text-[10px] sticky top-0 z-10 border-b border-slate-800">
                    <tr>
                      <th className="py-2.5 px-3">Ward ID & Locality</th>
                      <th className="py-2.5 px-3">City</th>
                      <th className="py-2.5 px-3 text-center">Risk / Priority</th>
                      <th className="py-2.5 px-3 text-center">Bed Demand</th>
                      <th className="py-2.5 px-3 text-center">Effective Cap</th>
                      <th className="py-2.5 px-3 text-center">Initial Deficit</th>
                      <th className="py-2.5 px-3 text-center">Outbound</th>
                      <th className="py-2.5 px-3 text-center">Inbound</th>
                      <th className="py-2.5 px-3 text-center">Net Deficit</th>
                      <th className="py-2.5 px-3 text-center">Final Occupancy</th>
                      <th className="py-2.5 px-3 text-center">Spare Beds</th>
                      <th className="py-2.5 px-3 text-center">Final Util</th>
                      <th className="py-2.5 px-3 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80">
                    {filteredHWards.map((w) => (
                      <tr
                        key={w.ward_id}
                        className={`hover:bg-slate-800/50 transition ${
                          w.critical_hospital_warning ? 'bg-red-950/20' : w.hospital_surge_status === 'Overloaded' ? 'bg-amber-950/15' : ''
                        }`}
                      >
                        <td className="py-2 px-3 font-semibold text-white">
                          <div>{w.ward_id}</div>
                          <div className="text-[10px] text-slate-400">{w.locality || w.ward_name}</div>
                        </td>
                        <td className="py-2 px-3 text-slate-300">{w.city}</td>
                        <td className="py-2 px-3 text-center">
                          <div className="font-mono text-cyan-300 font-bold">{w.priority_score}</div>
                          <div className="text-[10px] text-slate-400">{w.risk_level}</div>
                        </td>
                        <td className="py-2 px-3 text-center font-mono font-bold text-cyan-400">{w.hospital_beds_required}</td>
                        <td className="py-2 px-3 text-center font-mono text-slate-300">{w.hospital_beds_effective_capacity}</td>
                        <td className="py-2 px-3 text-center font-mono text-amber-400 font-bold">
                          {w.initial_bed_deficit > 0 ? w.initial_bed_deficit : '0'}
                        </td>
                        <td className="py-2 px-3 text-center font-mono text-emerald-400">
                          {w.outbound_overflow > 0 ? `-${w.outbound_overflow}` : '-'}
                        </td>
                        <td className="py-2 px-3 text-center font-mono text-teal-400">
                          {w.inbound_overflow > 0 ? `+${w.inbound_overflow}` : '-'}
                        </td>
                        <td className="py-2 px-3 text-center font-mono font-extrabold">
                          {w.net_bed_deficit > 0 ? (
                            <span className="text-red-400 bg-red-950 px-2 py-0.5 rounded border border-red-800">
                              {w.net_bed_deficit}
                            </span>
                          ) : (
                            <span className="text-emerald-400">0</span>
                          )}
                        </td>
                        <td className="py-2 px-3 text-center font-mono text-white">{w.final_projected_occupancy}</td>
                        <td className="py-2 px-3 text-center font-mono text-slate-300">{w.remaining_spare_beds}</td>
                        <td className="py-2 px-3 text-center font-mono text-purple-300">
                          {w.final_bed_utilization !== null ? `${w.final_bed_utilization}%` : 'N/A'}
                        </td>
                        <td className="py-2 px-3 text-center">
                          <span
                            className={`text-[9.5px] font-bold px-2 py-0.5 rounded border ${
                              w.critical_hospital_warning
                                ? 'bg-red-950 text-red-300 border-red-800'
                                : w.hospital_surge_status === 'Overloaded'
                                ? 'bg-amber-950 text-amber-300 border-amber-800'
                                : w.hospital_surge_status === 'Fully Utilized'
                                ? 'bg-blue-950 text-blue-300 border-blue-800'
                                : 'bg-emerald-950 text-emerald-300 border-emerald-800'
                            }`}
                          >
                            {w.critical_hospital_warning ? 'SURGE WARNING' : w.hospital_surge_status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Dispatch Notices Modal */}
            {hospitalNoticesOpen && (
              <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
                <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl">
                  <div className="flex items-center justify-between border-b border-slate-800 p-4">
                    <div className="flex items-center gap-2">
                      <FileText className="w-5 h-5 text-cyan-400" />
                      <h4 className="text-sm font-bold text-white">
                        Offline Template-Based Hospital Dispatch & Referral Notices
                      </h4>
                    </div>
                    <button
                      onClick={() => setHospitalNoticesOpen(false)}
                      className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1 rounded-lg"
                    >
                      Close
                    </button>
                  </div>

                  <div className="p-4 overflow-y-auto space-y-3 flex-1">
                    {hNotices.length === 0 ? (
                      <p className="text-xs text-slate-500 text-center py-8">No notices available.</p>
                    ) : (
                      hNotices.map((n, i) => (
                        <div key={i} className="bg-slate-950 border border-slate-800 rounded-xl p-3.5 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold text-cyan-400 bg-cyan-950 px-2 py-0.5 rounded border border-cyan-800">
                              {n.notice_type}
                            </span>
                            <div className="flex items-center gap-2">
                              <span className="text-[10px] text-slate-500 font-mono">{n.notice_id}</span>
                              <button
                                onClick={() => {
                                  navigator.clipboard.writeText(n.content);
                                  setCopiedNoticeId(n.notice_id);
                                  setTimeout(() => setCopiedNoticeId(null), 2000);
                                }}
                                className="flex items-center gap-1 text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-1 rounded transition"
                              >
                                {copiedNoticeId === n.notice_id ? (
                                  <>
                                    <Check className="w-3 h-3 text-emerald-400" />
                                    <span className="text-emerald-400">Copied</span>
                                  </>
                                ) : (
                                  <>
                                    <Copy className="w-3 h-3" />
                                    <span>Copy</span>
                                  </>
                                )}
                              </button>
                            </div>
                          </div>
                          <pre className="text-xs font-mono text-slate-300 bg-slate-900/80 p-3 rounded-lg overflow-x-auto whitespace-pre-wrap border border-slate-800/80">
                            {n.content}
                          </pre>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            )}
          </section>
        );
      })()}

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

import {
  kineticEnergy,
  joulesToTNT,
  totalEnergyTNT,
  terminalVelocity,
  flightTime,
  fuelConsumption,
  cep,
  fragmentVelocity,
  fragmentRange,
  thermalRadius,
  craterRadius,
  craterDepth,
  damageZones,
  overpressureCurve,
} from './physics.js';

const ATTACK_ROLES = new Set(['ATK', 'ATTACK', 'KAMIKAZE']);
const SUPPORT_ROLES = new Set(['REC', 'RECON', 'EW', 'DEC', 'COM', 'CMD', 'NAV', 'ISR']);

const n = (v, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);
const clamp01 = (v) => Math.max(0, Math.min(1, n(v)));

function scorePower(drone) {
  const payload = n(drone.payloadTNTkg);
  const speed = n(drone.maxSpeedMs || drone.cruiseMs);
  return payload + (speed / 120) * 0.35;
}

function scoreAccuracy(drone, distanceKm) {
  const expectedCep = cep(n(drone.baseCEP, 25), distanceKm, drone.guidanceType);
  const guidanceBonus = /(laser|ai|mixed)/i.test(String(drone.guidanceType || '')) ? 1.2 : 1;
  return guidanceBonus / Math.max(1, expectedCep);
}

function aggregateStats(attackDrones, supportDrones, target, distanceKm) {
  const all = [...attackDrones, ...supportDrones];
  const totalTNT = all.reduce((s, d) => s + n(d.payloadTNTkg), 0);
  const avgCEP = all.length
    ? all.reduce((s, d) => s + cep(n(d.baseCEP, 25), distanceKm, d.guidanceType), 0) / all.length
    : 999;
  const etaSec = all.length
    ? Math.max(...all.map((d) => flightTime(distanceKm, n(d.cruiseKmh, 120))))
    : 0;

  const requirementKpa = Math.max(20, n(target.requiredOverpressureKpa, 35));
  const achievedKpa = n(damageZones(totalTNT).moderate.thresholdKpa);
  const blastFactor = Math.min(1.2, achievedKpa / requirementKpa);
  const precisionFactor = Math.max(0.4, 1 - avgCEP / 120);
  const defensePenalty = 1 - clamp01(target.airDefenseLevel) * 0.35;
  const hardnessPenalty = 1 - clamp01(target.hardness) * 0.25;
  const effectiveness = Math.max(0, Math.min(100, blastFactor * precisionFactor * defensePenalty * hardnessPenalty * 100));

  const riskScore = clamp01(target.airDefenseLevel * 0.6 + target.hardness * 0.4 + all.length / 25);
  const riskLevel = riskScore < 0.45 ? 'low' : riskScore < 0.75 ? 'medium' : 'high';

  return {
    totalTNT: Number(totalTNT.toFixed(2)),
    avgCEP: Number(avgCEP.toFixed(2)),
    effectiveness: Number(effectiveness.toFixed(1)),
    ETA: Number(etaSec.toFixed(1)),
    zones: damageZones(totalTNT),
    riskLevel,
  };
}

export function mapDroneToEngine(myDbDrone = {}) {
  const roleRaw = String(myDbDrone.role || myDbDrone.category || '').toUpperCase();
  const role = roleRaw.includes('ATK') || roleRaw.includes('KAM') ? 'ATK' : roleRaw || 'REC';
  const cruiseKmh = n(myDbDrone.cruise_speed_kmh, 120);
  const maxKmh = n(myDbDrone.max_speed_kmh, cruiseKmh * 1.2);
  const massKg = n(myDbDrone.weight_kg, 20);
  const payloadKg = n(myDbDrone.warhead_weight_kg, n(myDbDrone.payload_capacity_kg, 0));

  const guidanceType = String(myDbDrone.guidance_system || 'GPS').toLowerCase();
  const baseCepMap = {
    laser: 4,
    ai: 5,
    mixed: 7,
    gps: 10,
    gnss: 12,
    ins: 25,
  };

  return {
    id: myDbDrone.id,
    name: myDbDrone.name || `Drone-${myDbDrone.id || 'X'}`,
    role,
    cruiseKmh,
    cruiseMs: cruiseKmh / 3.6,
    maxSpeedMs: maxKmh / 3.6,
    rangeKm: n(myDbDrone.max_range_km, n(myDbDrone.range_km, 120)),
    enduranceH: n(myDbDrone.endurance_hours, 1.5),
    massKg,
    payloadTNTkg: payloadKg,
    casingKg: Math.max(5, massKg - payloadKg),
    fuelRateKgH: Math.max(0.4, massKg * 0.06),
    guidanceType,
    baseCEP: baseCepMap[guidanceType] ?? 16,
    successRate: clamp01(n(myDbDrone.base_success_rate_pct, 70) / 100),
    stealth: clamp01(n(myDbDrone.stealth_rating, 0.5)),
    airframe: myDbDrone,
  };
}

export function mapTargetToEngine(myDbTarget = {}, context = {}) {
  const targetType = String(myDbTarget.target_type || myDbTarget.type || '').toLowerCase();
  const typeHardness = targetType === 'fixed' ? 0.75 : targetType === 'mobile' ? 0.45 : 0.55;

  const p = String(context.protection_level || myDbTarget.protection_level || '').toLowerCase();
  const protectionHardness = p === 'high' ? 0.9 : p === 'medium' ? 0.65 : p === 'low' ? 0.35 : typeHardness;

  const ctrCap = n(myDbTarget.ctr_cap_scale ?? context.ctr_cap_scale, 0);
  const density = String(context.ads_density || myDbTarget.ads_density || '').toLowerCase();
  const densityLevel = density === 'high' ? 0.85 : density === 'medium' ? 0.55 : density === 'low' ? 0.25 : clamp01(ctrCap / 5);
  const placementBonus = Math.min(0.15, n(context.ads_placement_count, 0) * 0.02);
  const airDefenseLevel = clamp01(densityLevel + placementBonus);

  return {
    id: myDbTarget.id,
    name: myDbTarget.name || 'UNKNOWN TARGET',
    latitude: n(myDbTarget.latitude, n(myDbTarget.lat)),
    longitude: n(myDbTarget.longitude, n(myDbTarget.lon)),
    target_type: myDbTarget.target_type,
    hardness: protectionHardness,
    airDefenseLevel,
    requiredOverpressureKpa: 35 + protectionHardness * 120,
    source: myDbTarget,
  };
}

export function suggestFormations(targetProfile, droneInventory, distanceKm) {
  const target = {
    hardness: clamp01(targetProfile?.hardness ?? 0.5),
    airDefenseLevel: clamp01(targetProfile?.airDefenseLevel ?? 0.4),
    requiredOverpressureKpa: n(targetProfile?.requiredOverpressureKpa, 60),
  };

  const inRange = (droneInventory || []).filter((d) => n(d.rangeKm, 0) >= n(distanceKm, 0));
  const attackers = inRange.filter((d) => ATTACK_ROLES.has(String(d.role || '').toUpperCase()));
  const supports = inRange.filter((d) => !ATTACK_ROLES.has(String(d.role || '').toUpperCase()));

  const precisionAttack = [...attackers].sort((a, b) => scorePower(b) - scorePower(a));
  const precisionPicked = [];
  for (const d of precisionAttack) {
    precisionPicked.push(d);
    const tnt = precisionPicked.reduce((s, x) => s + n(x.payloadTNTkg), 0);
    const op = damageZones(tnt).moderate.thresholdKpa;
    if (op >= target.requiredOverpressureKpa * 1.2) break;
  }
  const precisionSupport = [...supports]
    .sort((a, b) => scoreAccuracy(b, distanceKm) - scoreAccuracy(a, distanceKm))
    .slice(0, Math.min(2, supports.length));

  const saturationAttack = [...attackers]
    .sort((a, b) => scorePower(b) - scorePower(a))
    .slice(0, Math.min(Math.max(4, Math.ceil(attackers.length * 0.45)), attackers.length));
  const saturationSupport = [...supports]
    .sort((a, b) => (String(a.role).includes('DEC') ? -1 : 0) - (String(b.role).includes('DEC') ? -1 : 0))
    .slice(0, target.airDefenseLevel > 0.5 ? Math.min(4, supports.length) : Math.min(2, supports.length));

  const reconPool = [...inRange].sort((a, b) => scoreAccuracy(b, distanceKm) - scoreAccuracy(a, distanceKm));
  const shadowAttack = reconPool.filter((d) => ATTACK_ROLES.has(String(d.role).toUpperCase())).slice(0, 2);
  const shadowSupport = reconPool.filter((d) => !ATTACK_ROLES.has(String(d.role).toUpperCase())).slice(0, Math.min(5, reconPool.length));

  const formations = [
    {
      name: 'PRECISION STRIKE',
      icon: '🎯',
      strategy: 'Fewest drones, high payload concentration, single decisive axis.',
      tags: ['Low footprint', 'High lethality'],
      attackDrones: precisionPicked,
      supportDrones: precisionSupport,
    },
    {
      name: 'SATURATION ASSAULT',
      icon: '⚔️',
      strategy: 'Multi-vector pressure with decoy/noise support and broad strike front.',
      tags: ['Multi-vector', target.airDefenseLevel > 0.5 ? 'Decoy screen' : 'Broad wave'],
      attackDrones: saturationAttack,
      supportDrones: saturationSupport,
    },
    {
      name: 'SHADOW RECON STRIKE',
      icon: '🛰️',
      strategy: 'ISR-heavy package with best guidance-to-CEP assets and selective effects.',
      tags: ['ISR-heavy', 'High accuracy'],
      attackDrones: shadowAttack,
      supportDrones: shadowSupport,
    },
  ];

  return formations.map((f) => ({ ...f, stats: aggregateStats(f.attackDrones, f.supportDrones, target, distanceKm) }));
}

export function computeImpact(formation, distanceKm) {
  const all = [...(formation.attackDrones || []), ...(formation.supportDrones || [])];

  const perDrone = all.map((d) => {
    const tSec = flightTime(distanceKm, n(d.cruiseKmh, 120));
    const fuelBurn = fuelConsumption(n(d.fuelRateKgH, 1.2), tSec);
    const massAtImpact = Math.max(1, n(d.massKg, 20) - fuelBurn);
    const impactVelocity = terminalVelocity(n(d.cruiseMs, 35), 300);
    const ke = kineticEnergy(massAtImpact, impactVelocity);
    const keTnt = joulesToTNT(ke);
    const payloadTnt = Math.max(0, n(d.payloadTNTkg));
    const tntEq = totalEnergyTNT(massAtImpact, impactVelocity, payloadTnt);
    const droneCep = cep(n(d.baseCEP, 25), distanceKm, d.guidanceType);
    const fragVel = fragmentVelocity(payloadTnt, n(d.casingKg, 10));

    return {
      id: d.id,
      name: d.name,
      role: d.role,
      massAtImpactKg: Number(massAtImpact.toFixed(2)),
      impactVelocityMs: Number(impactVelocity.toFixed(2)),
      KE_J: Number(ke.toFixed(2)),
      KE_TNTkg: Number(keTnt.toFixed(4)),
      payloadTNTkg: Number(payloadTnt.toFixed(3)),
      TNTequivKg: Number(tntEq.toFixed(3)),
      CEP_m: Number(droneCep.toFixed(2)),
      fragmentVelocityMs: Number(fragVel.toFixed(2)),
      etaSec: Number(tSec.toFixed(2)),
    };
  });

  const totalTNT = perDrone.reduce((s, d) => s + d.TNTequivKg, 0);
  const totalKE = perDrone.reduce((s, d) => s + d.KE_J, 0);
  const avgCEP = perDrone.length ? perDrone.reduce((s, d) => s + d.CEP_m, 0) / perDrone.length : 0;

  return {
    perDrone,
    combined: {
      totalTNTkg: Number(totalTNT.toFixed(3)),
      totalKE_J: Number(totalKE.toFixed(2)),
      avgCEP_m: Number(avgCEP.toFixed(2)),
      timeToTargetSec: Number((perDrone.length ? Math.max(...perDrone.map((d) => d.etaSec)) : 0).toFixed(2)),
      damageZones: damageZones(totalTNT),
      craterRadius_m: Number(craterRadius(totalTNT).toFixed(2)),
      craterDepth_m: Number(craterDepth(totalTNT).toFixed(2)),
      fragmentRange_m: Number(fragmentRange(totalTNT).toFixed(2)),
      thermalRadius_m: Number(thermalRadius(totalTNT).toFixed(2)),
      overpressureCurve: overpressureCurve(totalTNT),
      droneCount: {
        attack: (formation.attackDrones || []).length,
        support: (formation.supportDrones || []).length,
        total: all.length,
      },
    },
  };
}

const TNT_JOULES_PER_KG = 4.184e6;
const EARTH_RADIUS_KM = 6371;
const G = 9.81;

const toRad = (deg) => (deg * Math.PI) / 180;
const safe = (n, fallback = 0) => (Number.isFinite(Number(n)) ? Number(n) : fallback);

export function haversine(lat1, lon1, lat2, lon2) {
  const p1 = toRad(safe(lat1));
  const p2 = toRad(safe(lat2));
  const dLat = toRad(safe(lat2) - safe(lat1));
  const dLon = toRad(safe(lon2) - safe(lon1));

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(p1) * Math.cos(p2) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_KM * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export function kineticEnergy(massKg, velocityMs) {
  const m = Math.max(0, safe(massKg));
  const v = Math.max(0, safe(velocityMs));
  return 0.5 * m * v * v;
}

export function joulesToTNT(joules) {
  return Math.max(0, safe(joules)) / TNT_JOULES_PER_KG;
}

export function totalEnergyTNT(massKg, velocityMs, payloadTNTkg = 0) {
  return joulesToTNT(kineticEnergy(massKg, velocityMs)) + Math.max(0, safe(payloadTNTkg));
}

export function overpressure(tntKg, distanceM) {
  const w = Math.max(1e-6, safe(tntKg));
  const d = Math.max(0.1, safe(distanceM));
  const z = d / Math.cbrt(w);
  return (0.84 / z + 2.7 / (z ** 2) + 7.94 / (z ** 3)) * 100;
}

export function craterRadius(tntKg) {
  return 0.8 * Math.cbrt(Math.max(0, safe(tntKg)));
}

export function craterDepth(tntKg) {
  return 0.5 * Math.cbrt(Math.max(0, safe(tntKg)));
}

export function fragmentVelocity(tntKg, casingKg) {
  const e = Math.max(0, safe(tntKg)) * TNT_JOULES_PER_KG;
  const m = Math.max(1e-3, safe(casingKg, 1));
  return 0.6 * Math.sqrt((2 * e) / m);
}

export function fragmentRange(tntKg) {
  return 15 * (Math.max(0, safe(tntKg)) ** 0.4);
}

export function thermalRadius(tntKg) {
  return 2.5 * Math.cbrt(Math.max(0, safe(tntKg)));
}

export function terminalVelocity(cruiseMs, diveAltM) {
  const v = Math.max(0, safe(cruiseMs));
  const h = Math.max(0, safe(diveAltM));
  return Math.sqrt(v * v + 2 * G * h);
}

export function flightTime(distKm, speedKmh) {
  const d = Math.max(0, safe(distKm));
  const s = Math.max(1e-6, safe(speedKmh));
  return (d / s) * 3600;
}

export function fuelConsumption(rateKgH, timeSec) {
  const rate = Math.max(0, safe(rateKgH));
  const t = Math.max(0, safe(timeSec));
  return (rate * t) / 3600;
}

export function cep(baseCEP, distKm, guidanceType = 'gps') {
  const base = Math.max(1, safe(baseCEP, 20));
  const d = Math.max(0, safe(distKm));
  const g = String(guidanceType || 'gps').toLowerCase();

  const factors = {
    ins: 1.35,
    visual: 1.2,
    optical: 1.1,
    gps: 1,
    gnss: 1,
    laser: 0.78,
    terrain: 0.9,
    ai: 0.75,
    mixed: 0.85,
  };

  const guidanceFactor = factors[g] ?? 1.05;
  const distanceSpread = 1 + d / 300;
  return base * guidanceFactor * distanceSpread;
}

function radiusAtThreshold(tntKg, thresholdKpa) {
  let low = 0.1;
  let high = 5000;
  for (let i = 0; i < 42; i += 1) {
    const mid = (low + high) / 2;
    if (overpressure(tntKg, mid) > thresholdKpa) {
      low = mid;
    } else {
      high = mid;
    }
  }
  return Number(low.toFixed(2));
}

export function damageZones(tntKg) {
  const w = Math.max(0, safe(tntKg));
  const zones = {
    total: { thresholdKpa: 350, radiusM: radiusAtThreshold(w, 350) },
    severe: { thresholdKpa: 100, radiusM: radiusAtThreshold(w, 100) },
    moderate: { thresholdKpa: 35, radiusM: radiusAtThreshold(w, 35) },
    light: { thresholdKpa: 7, radiusM: radiusAtThreshold(w, 7) },
    glass: { thresholdKpa: 3.5, radiusM: radiusAtThreshold(w, 3.5) },
  };
  return zones;
}

export function overpressureCurve(tntKg, steps = 60) {
  const n = Math.max(10, Math.floor(safe(steps, 60)));
  const maxDist = Math.max(80, damageZones(tntKg).glass.radiusM * 1.2);
  const points = [];
  for (let i = 1; i <= n; i += 1) {
    const dist = (maxDist * i) / n;
    points.push({ dist: Number(dist.toFixed(2)), op: Number(overpressure(tntKg, dist).toFixed(2)) });
  }
  return points;
}

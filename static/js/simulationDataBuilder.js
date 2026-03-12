export function buildSimulationData(formation, impact, base, target, distanceKm) {
  const now = Date.now();
  return {
    id: `sim_${now}`,
    createdAt: now,
    base,
    target,
    distanceKm,
    formationName: formation?.name,
    drones: [...(formation?.attackDrones || []), ...(formation?.supportDrones || [])],
    impactSummary: impact?.combined || {},
  };
}

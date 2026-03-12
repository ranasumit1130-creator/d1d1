const KEY = 'dwwiat_sim_state_v1';

function loadAll() {
  try {
    return JSON.parse(sessionStorage.getItem(KEY) || '{}');
  } catch (_) {
    return {};
  }
}

function saveAll(state) {
  sessionStorage.setItem(KEY, JSON.stringify(state));
}

export const simState = {
  save(missionId, payload) {
    const s = loadAll();
    s[String(missionId)] = payload;
    saveAll(s);
    return payload;
  },
  get(missionId) {
    return loadAll()[String(missionId)] || null;
  },
  patch(missionId, partial) {
    const s = loadAll();
    const key = String(missionId);
    s[key] = { ...(s[key] || {}), ...(partial || {}) };
    saveAll(s);
    return s[key];
  },
  clear(missionId) {
    const s = loadAll();
    delete s[String(missionId)];
    saveAll(s);
  },
};

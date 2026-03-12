(function () {
  const STYLE_ID = 'strike-ui-style-v1';

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      .su-root{font-family:'Saira Condensed',sans-serif;color:#c2b280}
      .su-title{font-family:'Black Ops One','Saira Condensed',sans-serif;letter-spacing:1.4px}
      .su-panel{background:#22261c;border:1px solid #3f4830;border-left:4px solid #8fa94e;border-radius:8px;padding:14px}
      .su-grid{display:grid;gap:12px}
      .su-cards{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
      .su-card{cursor:pointer;background:#1a1c16;border:1px solid #4f5d34;border-radius:8px;padding:12px;display:flex;flex-direction:column;gap:10px}
      .su-card:hover{border-color:#a4c639;transform:translateY(-1px)}
      .su-badge{display:inline-block;padding:2px 8px;border-radius:99px;font-size:12px;text-transform:uppercase;letter-spacing:1px}
      .su-risk-low{background:#2d3f23;color:#a4c639}.su-risk-medium{background:#5f4b1d;color:#d4a017}.su-risk-high{background:#4f1f1f;color:#e74c3c}
      .su-chip{display:inline-block;font-size:11px;padding:2px 7px;border:1px solid #5f6e40;border-radius:12px;margin:2px;text-transform:uppercase}
      .su-chip.atk{border-color:#e74c3c;color:#e74c3c}.su-chip.sup{border-color:#8fa94e;color:#8fa94e}
      .su-btn{padding:8px 10px;background:transparent;border:1px solid #d4a017;color:#d4a017;text-transform:uppercase;letter-spacing:1px;cursor:pointer}
      .su-btn:hover{background:#2a2817}
      .su-table{width:100%;border-collapse:collapse;font-size:13px}
      .su-table th,.su-table td{border:1px solid #3f4830;padding:6px;text-align:left}
      .su-table th{color:#a4c639;text-transform:uppercase;letter-spacing:1px}
      .su-flex{display:flex;gap:12px;flex-wrap:wrap}
      .su-stat{min-width:150px;background:#1a1c16;border:1px solid #3f4830;border-left:4px solid #a4c639;padding:8px}
      .su-verdict{padding:8px 12px;border:2px solid;text-transform:uppercase;font-weight:700;letter-spacing:1px;display:inline-block}
      .su-svg{background:#1a1c16;border:1px solid #3f4830;border-radius:8px;padding:8px;flex:1;min-width:280px}
      .su-info{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:12px}
    `;
    document.head.appendChild(style);
  }

  function f(num, digits = 2) {
    return Number(num || 0).toFixed(digits);
  }

  function roleClass(role) {
    return /ATK|ATTACK|KAMIKAZE/i.test(String(role || '')) ? 'atk' : 'sup';
  }

  function verdict(effectiveness) {
    if (effectiveness >= 80) return { text: 'TARGET NEUTRALIZED', color: '#6b7f3b' };
    if (effectiveness >= 50) return { text: 'PARTIAL DAMAGE', color: '#d4a017' };
    return { text: 'MISSION FAILURE', color: '#e74c3c' };
  }

  class StrikeUI {
    constructor(container, props) {
      ensureStyles();
      this.container = container;
      this.props = props;
      this.state = { mode: 'formations', selected: null, impact: null };
      this.render();
    }

    async selectFormation(formation) {
      const impact = await this.props.onComputeImpact(formation);
      this.state = { mode: 'impact', selected: formation, impact };
      this.render();
    }

    renderMissionInfo() {
      const t = this.props.target || {};
      return `
        <div class="su-panel su-info">
          <div><div>TARGET</div><div class="su-title">${t.name || 'N/A'}</div></div>
          <div><div>DISTANCE</div><div class="su-title">${f(this.props.distanceKm, 1)} KM</div></div>
          <div><div>HARDNESS</div><div class="su-title">${f((t.hardness || 0) * 100, 0)}%</div></div>
          <div><div>AIR DEFENSE</div><div class="su-title">${f((t.airDefenseLevel || 0) * 100, 0)}%</div></div>
        </div>`;
    }

    renderFormations() {
      const cards = (this.props.formations || []).map((fItem, idx) => {
        const all = [...(fItem.attackDrones || []), ...(fItem.supportDrones || [])];
        const chips = all.map((d) => `<span class="su-chip ${roleClass(d.role)}">${d.name} (${d.role})</span>`).join('');
        return `
          <div class="su-card" data-i="${idx}">
            <div style="display:flex;justify-content:space-between;align-items:center">
              <div class="su-title">${fItem.icon || '✦'} ${fItem.name}</div>
              <span class="su-badge su-risk-${fItem.stats.riskLevel}">${fItem.stats.riskLevel} risk</span>
            </div>
            <div>${fItem.strategy || ''}</div>
            <div>${(fItem.tags || []).map((t) => `<span class="su-chip">${t}</span>`).join('')}</div>
            <div>${chips}</div>
            <div class="su-flex">
              <div class="su-stat"><div>Total Drones</div><strong>${all.length}</strong></div>
              <div class="su-stat"><div>Total TNT</div><strong>${f(fItem.stats.totalTNT, 2)} kg</strong></div>
              <div class="su-stat"><div>Avg CEP</div><strong>${f(fItem.stats.avgCEP, 1)} m</strong></div>
              <div class="su-stat"><div>ETA</div><strong>${f(fItem.stats.ETA, 0)} s</strong></div>
              <div class="su-stat"><div>Effectiveness</div><strong>${f(fItem.stats.effectiveness, 0)}%</strong></div>
            </div>
            <button class="su-btn">SELECT FOR IMPACT ANALYSIS</button>
          </div>`;
      }).join('');

      this.container.innerHTML = `<div class="su-root">
        ${this.renderMissionInfo()}
        <div class="su-grid su-cards">${cards}</div>
        <div style="margin-top:12px"><button class="su-btn" id="su-back-config">BACK</button></div>
      </div>`;

      this.container.querySelectorAll('.su-card').forEach((node) => {
        node.addEventListener('click', () => this.selectFormation(this.props.formations[Number(node.dataset.i)]));
      });
      this.container.querySelector('#su-back-config').addEventListener('click', this.props.onBack);
    }

    renderBlastSvg(z) {
      const g = z.glass?.radiusM || 1;
      const scale = 120 / Math.max(1, g);
      const ring = (r, c) => `<circle cx="130" cy="130" r="${Math.max(3, r * scale)}" fill="none" stroke="${c}" stroke-width="2"/>`;
      return `<svg width="260" height="260" viewBox="0 0 260 260">
        ${ring(z.glass.radiusM, '#c2b280')}
        ${ring(z.light.radiusM, '#8fa94e')}
        ${ring(z.moderate.radiusM, '#a4c639')}
        ${ring(z.severe.radiusM, '#d4a017')}
        ${ring(z.total.radiusM, '#e74c3c')}
        <circle cx="130" cy="130" r="3" fill="#fff"/>
      </svg>`;
    }

    renderCurveSvg(points) {
      const w = 320; const h = 220;
      const maxX = Math.max(...points.map((p) => p.dist), 1);
      const maxY = Math.max(...points.map((p) => p.op), 1);
      const path = points.map((p, i) => {
        const x = 20 + (p.dist / maxX) * (w - 30);
        const y = h - 20 - (p.op / maxY) * (h - 40);
        return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
      }).join(' ');
      return `<svg width="100%" height="220" viewBox="0 0 ${w} ${h}">
        <rect x="0" y="0" width="${w}" height="${h}" fill="#1a1c16"/>
        <path d="${path}" stroke="#a4c639" fill="none" stroke-width="2"/>
      </svg>`;
    }

    renderImpact() {
      const { selected, impact } = this.state;
      const rows = impact.perDrone.map((d) => `
        <tr><td>${d.name}</td><td>${d.role}</td><td>${f(d.massAtImpactKg)}</td><td>${f(d.impactVelocityMs)}</td><td>${f(d.KE_J,0)}</td><td>${f(d.TNTequivKg,3)}</td><td>${f(d.CEP_m,1)}</td><td>${f(d.fragmentVelocityMs,1)}</td></tr>`).join('');
      const c = impact.combined;
      const v = verdict(selected.stats.effectiveness);

      this.container.innerHTML = `<div class="su-root">
        <div class="su-panel">
          <div class="su-title">${selected.name} — ${this.props.target.name} — ${f(this.props.distanceKm,1)} KM</div>
        </div>

        <div class="su-panel" style="margin-top:12px;overflow:auto">
          <table class="su-table"><thead><tr><th>Name</th><th>Role</th><th>Mass@Impact</th><th>Impact V</th><th>KE</th><th>TNT Eq</th><th>CEP</th><th>Frag V</th></tr></thead>
          <tbody>${rows}<tr><td colspan="4"><strong>COMBINED TOTAL</strong></td><td><strong>${f(c.totalKE_J,0)}</strong></td><td><strong>${f(c.totalTNTkg,3)}</strong></td><td><strong>${f(c.avgCEP_m,1)}</strong></td><td>—</td></tr></tbody></table>
        </div>

        <div class="su-flex" style="margin-top:12px">
          <div class="su-stat"><div>Total TNT yield</div><strong>${f(c.totalTNTkg,2)} kg</strong></div>
          <div class="su-stat"><div>Total KE</div><strong>${f(c.totalKE_J,0)} J</strong></div>
          <div class="su-stat"><div>Avg CEP</div><strong>${f(c.avgCEP_m,1)} m</strong></div>
          <div class="su-stat"><div>Time to target</div><strong>${f(c.timeToTargetSec,0)} s</strong></div>
        </div>

        <div class="su-flex" style="margin-top:12px">
          <div class="su-svg">${this.renderBlastSvg(c.damageZones)}</div>
          <div class="su-svg">${this.renderCurveSvg(c.overpressureCurve || [])}</div>
        </div>

        <div class="su-panel" style="margin-top:12px">
          <div class="su-flex">
            <div>Total (${c.damageZones.total.thresholdKpa}kPa): ${f(c.damageZones.total.radiusM,1)} m</div>
            <div>Severe (${c.damageZones.severe.thresholdKpa}kPa): ${f(c.damageZones.severe.radiusM,1)} m</div>
            <div>Moderate (${c.damageZones.moderate.thresholdKpa}kPa): ${f(c.damageZones.moderate.radiusM,1)} m</div>
            <div>Light (${c.damageZones.light.thresholdKpa}kPa): ${f(c.damageZones.light.radiusM,1)} m</div>
            <div>Glass (${c.damageZones.glass.thresholdKpa}kPa): ${f(c.damageZones.glass.radiusM,1)} m</div>
          </div>
        </div>

        <div style="margin-top:12px;display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap">
          <div class="su-verdict" style="color:${v.color};border-color:${v.color}">${v.text}</div>
          <div>ATTACK: ${c.droneCount.attack} | SUPPORT: ${c.droneCount.support} | TOTAL: ${c.droneCount.total}</div>
        </div>

        <div style="margin-top:12px;display:flex;gap:10px">
          <button class="su-btn" id="su-back-form">BACK TO FORMATIONS</button>
          <button class="su-btn" id="su-back-config">BACK TO CONFIG</button>
        </div>
      </div>`;

      this.container.querySelector('#su-back-form').addEventListener('click', () => {
        this.state.mode = 'formations';
        this.render();
      });
      this.container.querySelector('#su-back-config').addEventListener('click', this.props.onBack);
    }

    render() {
      if (this.state.mode === 'impact') this.renderImpact();
      else this.renderFormations();
    }
  }

  window.StrikeUI = StrikeUI;
}());

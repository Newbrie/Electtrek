  // ----------------------------
  // Table Fetching
  // ----------------------------


  // 1. Define the function in the global scope so HTML can see it
  window.toggleAccordion = function() {
      const panel = document.getElementById('territory-accordion');
      if (panel) {
          const isHidden = panel.style.display === 'none' || panel.style.display === '';
          panel.style.display = isHidden ? 'block' : 'none';
          console.log("Accordion toggled:", panel.style.display); // Debug check
      } else {
          console.error("Could not find element: territory-accordion");
      }
  };

  // 2. Define the selection logic
  /**
 * 1. Navigation Logic
 * Fetches data for a specific node path and updates the UI
 */
window.selectNode = function(path) {
    if (!path) return;

    // Immediate UI feedback for the breadcrumb/header
    const displayTitle = path.split('/').pop().replace(/_/g, ' ');
    const displayElement = document.getElementById('display-path');
    if (displayElement) displayElement.innerText = displayTitle;

    fetch(`/get_territory_data?nodepath=${encodeURIComponent(path)}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                console.error("Server Error:", data.error);
                return;
            }

            // Update the Iframe Map
            const iframe = document.getElementById('iframe1');
            if (iframe && data.map_url) {
                iframe.src = data.map_url;
            }

            // Update Parent/Back Link
            const pLink = document.getElementById('parent-link');
            if (data.parent_path) {
                const parentName = data.parent_path.split('/').pop().replace(/_/g, ' ');
                pLink.style.display = 'block';
                // Use an anonymous function to prevent immediate execution
                pLink.onclick = () => selectNode(data.parent_path);
                document.getElementById('parent-name').innerText = parentName;
            } else {
                pLink.style.display = 'none';
            }

            // Render Lists (Backend now returns objects: {path, nid, name})
            renderNodeList('children-list', data.children);
            renderNodeList('siblings-list', data.siblings);
        })
        .catch(err => console.error("Navigation Fetch Error:", err));
};



  // ----------------------------
  // String Utilities
  // ----------------------------
  function toUpperCase(str) {
    return str.replace(/\w\S*/g, txt => txt.charAt(0).toUpperCase() + txt.slice(1).toUpperCase());
  }

  function subending(filename, ending) {
    const endings = [".XLSX", ".xlsx", ".CSV", ".csv", "-PRINT.html", "-MAP.html", "-WALKS.html", "-ZONES.html", "-PDS.html", "-DIVS.html", "-WARDS.html"];
    let stem = filename;

    for (const suffix of endings) if (filename.endsWith(suffix)) { stem = filename.slice(0, -suffix.length); break; }

    const result = stem + ending;
    console.log(`____Subending test: from ${filename} to ${result}`);
    return result;
  }

  // ----------------------------
  // Chart Utilities
  // ----------------------------
  function createOrUpdateChart(labels, data, rags) {
    const ragColors = { red: 'rgba(255,99,132,0.9)', amber: 'rgba(255,159,64,0.9)', limegreen: 'rgba(50,205,50,0.9)' };
    const backgroundColors = rags.map(rag => ragColors[rag]);

    const canvas = document.getElementById('streamChart');
    if (!canvas) return console.error('streamChart canvas not found.');

    const ctx = canvas.getContext('2d');

    if (window.streamChart) {
      window.streamChart.data.labels = labels;
      window.streamChart.data.datasets[0].data = data;
      window.streamChart.data.datasets[0].backgroundColor = backgroundColors;
      window.streamChart.update();
    } else {
      Chart.register(ChartDataLabels);
      window.streamChart = new Chart(ctx, {
        type: 'doughnut',
        data: { labels, datasets: [{ label: 'Electors in Stream', data, backgroundColor: backgroundColors, borderColor: '#fff', borderWidth: 1 }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, title: { display: true, text: 'Stream Loading Status' }, datalabels: { color: '#000', font: { size: 14, weight: 'bold' }, formatter: val => val.toLocaleString() } } },
        plugins: [ChartDataLabels]
      });
    }
  }

  async function fetchAndUpdateChart() {
    try {
      const { streamrag } = await (await fetch('/streamrag_api')).json();
      const labels = Object.keys(streamrag);
      const data = labels.map(l => streamrag[l].Elect);
      const rags = labels.map(l => streamrag[l].RAG);
      createOrUpdateChart(labels, data, rags);
    } catch (err) {
      console.error('Failed to fetch streamrag data:', err);
    }
  }

  // ----------------------------
  // Constants UI
  // ----------------------------
  function attachListenersToConstantFields(constants) {
    Object.keys(constants).forEach(key => {
      const el = document.getElementById(key);
      if (!el) return;

      const listener = () => refreshConstantsUI();
      el.removeEventListener("change", listener);
      el.removeEventListener("input", listener);

      if (el.tagName === "SELECT" && el.multiple) el.addEventListener("blur", listener);
      else { el.addEventListener("change", listener); el.addEventListener("input", listener); }
    });
  }


 /* ---------------------------------------------------------
  * expose refreshTableData so iframe can call the parent
  * --------------------------------------------------------- */
 window.refreshTableData = function(id) {
     console.log("Refreshing table for", id);
     window.parent.postMessage(
         { type: "update-table", stable: "nodelist_xref" },
         "*"
     );
 };



async function fetchTableData(tableName) {
  const old = pessages.pop();
  const ul = parent.document.getElementById("logwin");
  const li = parent.document.createElement("li");

  const PARTY_COLORS = {
    O: "brown", R: "cyan", C: "blue", S: "red",
    LD: "yellow", G: "limegreen", I: "indigo",
    PC: "darkred", SD: "orange", Z: "#006064",
    W: "white", X: "darkgray"
  };
   const table = document.getElementById("content-table");
   const tabTitle = document.getElementById("selectedTitle");

   if (!table || !tabTitle) {
       console.error("❌ Required DOM elements not found: #content-table or #selectedTitle");
       return;
   }

   const tabHead = table.querySelector("thead");
   const tabBody = table.querySelector("tbody");

   if (!tabHead || !tabBody) {
       console.error("❌ Table structure invalid: missing <thead> or <tbody>");
       return;
   }

   try {
       const res = await fetch(`/get_table/${tableName}`, { credentials: "same-origin" });
       if (!res.ok) throw new Error(`Server returned ${res.status}`);
       const data = await res.json();

       if (!Array.isArray(data) || data.length < 3) {
           console.error("❌ Invalid data format received:", data);
           return;
       }

       const [columnHeaders, rows, title] = data;
//       tabTitle.textContent = title;
       tabHead.innerHTML = "";
       tabBody.innerHTML = "";

       // --- 1. Filtered Table header ---
       const headRow = document.createElement("tr");
       headRow.innerHTML = `<th>?</th>` +
           columnHeaders
               .filter(h => h.toLowerCase() !== 'nid') // 🎯 Skip NID in header
               .map(h => `<th>${h.toUpperCase()}</th>`)
               .join('');
       tabHead.appendChild(headRow);

       const selectedParty = document.getElementById("yourparty")?.value;

       // --- 2. Filtered Table body ---
       rows.forEach(record => {
           const row = document.createElement("tr");

           // Extract the NID for the checkbox (it exists in 'record' but we won't show it in a cell)
           const nid = record['nid'] || record['id'] || "";

           row.innerHTML = `<td>
               <input type="checkbox"
                      class="selectRow"
                      value="${nid}"
                      data-nid="${nid}">
             </td>` +
             columnHeaders
               .filter(h => h.toLowerCase() !== 'nid') // 🎯 Skip NID in rows
               .map(h => {
                   const value = record[h] ?? "";
                   const color = (selectedParty && h === selectedParty) ? (PARTY_COLORS[selectedParty] || 'inherit') : '';
                   return `<td style="background-color:${color}">${value}</td>`;
               }).join('');

           tabBody.appendChild(row);
       });

       console.log(`✅ TABLE "${tableName}" populated with ${rows.length} rows.`);
   } catch (err) {
       console.error("❌ Error fetching table data:", err);
   }
}


window.deleteElection = async function(electionName) {
  if (!confirm(`Delete "${electionName}"? This cannot be undone.`)) return;
  const res = await fetch("/delete-election", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ election: electionName })
  });
  const resp = await res.json();
  if (resp.success && resp.electiontabs_html) {
    document.getElementById("election-tabs").innerHTML = resp.electiontabs_html;
    await fetchTableData('nodelist_xref');
    syncStreamsSelectWithTabs();
  } else alert("Could not delete election: " + (resp.error || "Unknown error"));
};

window.addElection = async function() {
  const newName = prompt("Enter name for new election:");
  if (!newName) return;
  const res = await fetch("/add-election", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ election: newName })
  });
  const resp = await res.json();
  if (resp.success && resp.electiontabs_html) {
    document.getElementById("election-tabs").innerHTML = resp.electiontabs_html;
    syncStreamsSelectWithTabs();
    updateConstantsUI(resp.constants, resp.options);
//    iframeWin.populateAllSelects(resp.options, resp.constants);
    await fetchTableData('nodelist_xref');
  } else alert("Error adding election: " + resp.error);
};

async function ensureTabsReady() {
    while (document.querySelectorAll(".election-tab").length === 0) {
        await new Promise(r => requestAnimationFrame(r));
    }
}

async function ensureOneTabActive() {
  const tabs = document.querySelectorAll(".election-tab");
  let active = document.querySelector(".election-tab.active");

  if (!active && tabs.length > 0) {

      // Fetch last-used election (correct JSON way)
      let lastElection = null;
      try {
          const res = await fetch("/last-election", { credentials: "same-origin" });
          const json = await res.json();
          lastElection = json.last_election;   // <-- THIS WAS THE FIX
      } catch (e) {
          console.warn("Could not fetch last election");
      }

      // Try selecting that tab
      if (lastElection) {
          const lastTab = [...tabs].find(t => t.dataset.election === lastElection);
          if (lastTab) {
              lastTab.classList.add("active");
              return lastTab;
          }
      }

      // Fallback: first tab
      tabs[0].classList.add("active");
      return tabs[0];
  }

  return active;
}


function accumulateToggle(element) {
    fetch("/set_accumulate", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ accumulate: element.checked }),
        credentials: 'include' // 🚨 CRITICAL: Must be here!
    })
    .then(response => response.json())
    .then(data => {
        console.log("Accumulate set to:", data.accumulate);
    });
}


async function setActiveElectionOnStartup() {
    const activeTab = await ensureOneTabActive();
    const electionName = activeTab.dataset.election || activeTab.textContent.trim();
    console.log("📩 Setting startup active tab::", electionName);

    if (!electionName) {
        console.error("No election name found for active tab!", activeTab);
        return;
    }

    try {
        // Delegate all network fetching, DOM rendering, and context-switch logging
        // directly to your centralized orchestration function
        await window.switchElection(electionName);
        console.log("🚀 Startup initialization fully completed for election:", electionName);
    } catch (e) {
        console.error("Failed to set active election on startup:", e);
    }
}

// ----------------------------
// Election Management
// ----------------------------
function syncStreamsSelectWithTabs() {
  const streamsSelect = document.getElementById('streams');
  streamsSelect.innerHTML = '';
  document.querySelectorAll('.election-tab').forEach(tab => {
    const opt = document.createElement('option');
    opt.value = tab.dataset.election;
    opt.textContent = `Election ${tab.dataset.election}`;
    streamsSelect.appendChild(opt);
  });
  streamsSelect.value = document.querySelector('.election-tab.active')?.dataset.election || '';
}





 /* ---------------------------------------------------------
  * FETCH CONSTANTS + UPDATE UI
  * --------------------------------------------------------- */


  // ----------------------------
  // Iframe & Toggle
  // ----------------------------
  window.changeIframeSrc = function(url) {
    const logWindow = document.getElementById("logwin");
    const li = document.createElement("li");
    li.textContent = `Retrieving area ${url}`;
    logWindow.appendChild(li);
    logWindow.scrollTop = logWindow.scrollHeight;

    iframe.src = url;
  };

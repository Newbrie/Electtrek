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

 window.switchElection = async function (electionName) {
    if (!electionName || electionName === "undefined") {
        console.warn("⚠️ switchElection called without a valid electionName:", electionName);
        return;
    }

    // 1. UI: Highlight active tab
    document.querySelectorAll(".election-tab").forEach(tab =>
        tab.classList.remove("active")
    );
    const clickedTab = [...document.querySelectorAll(".election-tab")]
        .find(tab => tab.dataset.election === electionName);
    if (clickedTab) clickedTab.classList.add("active");

    try {
        // 2. Backend: Set the election session
        const res = await fetch("/set-election", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({ election: electionName })
        });

        if (!res.ok) throw new Error(`Server returned HTTP ${res.status}`);

        const data = await res.json();
        const iframeEl = document.getElementById("iframe1");

        if (data.success) {
            // Capture backend-driven state
            if (data.mapfile) window.mapfile = data.mapfile;
            if (data.currentNodePath) window.currentNodePath = data.currentNodePath;

            // Update local tree reference
            const newTree = data.options?.areas;
            if (newTree && Object.keys(newTree).length) {
                window.areaTree = newTree;
            } else {
                console.warn("set-election returned no areas for", electionName, Object.keys(data.options || {}));
            }

            // Refresh the sidebar accordion now that mapfile and areaTree are both current
            if (window.areaTree && typeof window.initAccordionFromOptions === "function") {
                window.initAccordionFromOptions(window.areaTree);
            }

            // Load the correct map into the iframe
            if (iframeEl && data.mapfile) {
                const targetUrl = `/thru/${data.mapfile}`;

                // Only reload if the URL has actually changed to prevent unnecessary reloads
                if (!iframeEl.src.endsWith(targetUrl)) {
                    iframeEl.src = targetUrl;
                } else {
                    // If src didn't change, notify the existing iframe context via postMessage
                    const iframeWin = iframeEl.contentWindow;
                    if (iframeWin) {
                        iframeWin.postMessage({
                            type: "iframeSwitchElection",
                            electionName: electionName,
                            data: data
                        }, "*");
                    }
                }
            }

            // Refresh table data if configured
            if (typeof fetchTableData === "function") {
                await fetchTableData("nodelist_xref");
            }
        } else {
            console.error("❌ Failed to switch election on backend:", data.message || "Unknown error");
        }
    } catch (error) {
        console.error("❌ Error during switchElection fetch:", error);
    }
};

  const logList = document.querySelector("#logwin .flashes");

 function addMessageToLog(text) {
     if (!logList) return;

     const li = document.createElement("li");
     const now = new Date();
     const hh = String(now.getHours()).padStart(2, "0");
     const mm = String(now.getMinutes()).padStart(2, "0");
     const ss = String(now.getSeconds()).padStart(2, "0");
     const timestamp = `[${hh}:${mm}:${ss}]`;

     li.textContent = `${timestamp} ${text}`;
     logList.appendChild(li);
     logList.scrollTop = logList.scrollHeight;
 }

async function fetchTableData(tableName) {
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
  }

  function bindIframeButtons() {
    // Grab the iframe buttons map from window.options (passed down by Jinja or fetched)
    const iframeButtons = window.options?.iframeButtons;
    if (!iframeButtons || typeof iframeButtons !== 'object') return;

    Object.entries(iframeButtons).forEach(([btnId, targetUrl]) => {
        const btn = document.getElementById(btnId);
        if (btn) {
            btn.onclick = (e) => {
                e.preventDefault();
                const iframeEl = document.getElementById("iframe1");
                if (iframeEl && targetUrl) {
                    console.log(`🚀 Navigating iframe via button ${btnId} to: ${targetUrl}`);
                    iframeEl.src = targetUrl;
                } else {
                    console.warn(`⚠️ Target URL missing for ${btnId} or iframe1 not found.`);
                }
            };
        }
    });
    console.log("✅ Iframe navigation buttons bound successfully.");
}


// Helper fallback if areaTree is structured as a nested object rather than a flat path map
function findDictByPath(tree, targetPath) {
    // If your tree structure requires recursive traversal, adapt this lookup logic,
    // otherwise fallback to letting selectNode handle the fetch route if areaTree lookup is unavailable.
    return tree[targetPath] || null;
}

window.addEventListener('message', (e) => {
    if (e.origin !== window.location.origin) return;
    if (e.data && e.data.type === 'no-elector-data') {
        showDataNotLoaded(e.data.area);
    }
});

function showDataNotLoaded(areaName) {
    alert(
        `No map is available for ${areaName}.\n\n` +
        `The elector data for this area hasn't been loaded yet. ` +
        `Please import the elector data for ${areaName} and try again.`
    );
}

// Listen for failure pages loaded inside the map iframe
window.addEventListener('message', (e) => {
    if (e.origin !== window.location.origin) return;
    if (e.data && e.data.type === 'no-elector-data') {
        showDataNotLoaded(e.data.area);
        const f = document.getElementById('iframe1') || document.querySelector('iframe');
        try { f?.contentWindow.history.back(); } catch (_) {}
    }
});

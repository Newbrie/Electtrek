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



 window.switchElection = async function (electionName) {
    if (!electionName || electionName === "undefined") {
        console.warn("⚠️ switchElection called without a valid electionName:", electionName);
        return;
    }

    // 1. UI: Highlight the active tab on the parent
    document.querySelectorAll(".election-tab").forEach(tab =>
        tab.classList.remove("active")
    );
    const clickedTab = [...document.querySelectorAll(".election-tab")]
        .find(tab => tab.dataset.election === electionName);
    if (clickedTab) clickedTab.classList.add("active");

    // 2. Backend: Set the election session
    const res = await fetch("/set-election", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ election: electionName })
    });

    const data = await res.json();

    // 3. Tell the iframe to handle its internal UI, calendar, and map updates
    if (iframeWin && typeof iframeWin.iframeSwitchElection === "function") {
        iframeWin.iframeSwitchElection(electionName, data);
    } else {
        // Fallback message passing if direct access is blocked by cross-origin policies
        document.iframeWin.postMessage({
            type: "iframeSwitchElection",
            electionName: electionName,
            data: data
        }, "*");
    }

    // 4. Refresh Parent Data Tables if needed
    await iframeWin.fetchTableData("nodelist_xref");
};



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
    await iframeWin.fetchTableData('nodelist_xref');
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
    iframeWin.populateAllSelects(resp.options, resp.constants);
    await iframeWin.fetchTableData('nodelist_xref');
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

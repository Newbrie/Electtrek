  // ----------------------------
  // Table Fetching
  // ----------------------------
  const PARTY_COLORS = {
    O: "brown", R: "cyan", C: "blue", S: "red",
    LD: "yellow", G: "limegreen", I: "indigo",
    PC: "darkred", SD: "orange", Z: "lightgray",
    W: "white", X: "darkgray"
  };

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
  window.selectNode = function(path) {
      if (!path) return;

      // Update label immediately for responsiveness
      document.getElementById('display-path').innerText = path.split('/').pop().replace(/_/g, ' ');

      fetch(`/get_territory_data?nodepath=${encodeURIComponent(path)}`)
          .then(res => res.json())
          .then(data => {
              // Update the Iframe Map
              const iframe = document.getElementById('map-iframe');
              if(iframe) iframe.src = data.map_url;

              // Update Parent Link
              const pLink = document.getElementById('parent-link');
              if (data.parent_path) {
                  pLink.style.display = 'block';
                  pLink.setAttribute('onclick', `selectNode('${data.parent_path}')`);
                  document.getElementById('parent-name').innerText = data.parent_path.split('/').pop();
              } else {
                  pLink.style.display = 'none';
              }

              // Render Children & Siblings
              renderNodeList('children-list', data.children);
              renderNodeList('siblings-list', data.siblings);
          })
          .catch(err => console.error("Fetch error:", err));
  };

  // 3. Helper for rendering lists
  function renderNodeList(elementId, paths) {
      const container = document.getElementById(elementId);
      if (!container) return;

      if (!paths || paths.length === 0) {
          container.innerHTML = '<div class="none-found">No further divisions</div>';
          return;
      }

      container.innerHTML = paths.map(p => {
          const name = p.split('/').pop().replace(/_/g, ' ');
          return `<div class="nav-item" onclick="selectNode('${p}')">${name}</div>`;
      }).join('');
  }

  // 4. Initial Load
  document.addEventListener('DOMContentLoaded', () => {
      selectNode('UNITED_KINGDOM');
  });
/**
 * Populate the area accordion based on your areas dict.
 * @param {Object} areasDict - Structure: { childId: { node, children: [...] } }
 */
 function populateAreaAccordion(areasDict) {
    console.group("📍 populateAreaAccordion");
    const container = document.getElementById("areaAccordionContainer");

    if (!container) {
        console.warn("❌ areaAccordionContainer not found");
        console.groupEnd();
        return;
    }

    container.innerHTML = "";

    // Create the unique ID for the parent accordion
    const accordionId = "mainAreaAccordion";
    const accordionWrapper = document.createElement("div");
    accordionWrapper.className = "accordion";
    accordionWrapper.id = accordionId;

    const children = Object.values(areasDict || {});

    children.forEach((child, idx) => {
        if (!child?.node) return;

        const nid = child.node.nid;
        const val = child.node.value;
        const collapseId = `collapse-${idx}`;
        const headerId = `heading-${idx}`;

        // Create Accordion Item
        const item = document.createElement("div");
        item.className = "accordion-item border-0 mb-2";

        item.innerHTML = `
            <h2 class="accordion-header" id="${headerId}">
                <button class="accordion-button collapsed py-2 shadow-none" type="button"
                        data-bs-toggle="collapse" data-bs-target="#${collapseId}"
                        style="background: #f8f9fa; font-weight: 600;">
                    ${val}
                </button>
            </h2>
            <div id="${collapseId}" class="accordion-collapse collapse"
                 data-bs-parent="#${accordionId}">
                <div class="accordion-body p-0">
                    <div class="list-group list-group-flush" id="list-${idx}">
                        </div>
                </div>
            </div>
        `;

        accordionWrapper.appendChild(item);
        const listGroup = item.querySelector(`#list-${idx}`);

        // Add Grandchildren (the sub-areas)
        if (child.children && child.children.length) {
            child.children.forEach(grand => {
                const btn = document.createElement("button");
                btn.className = "list-group-item list-group-item-action border-0 ps-4 small";
                btn.dataset.fid = grand.nid;
                btn.dataset.name = grand.value;
                btn.textContent = grand.value;

                // Add click event for the sub-area
                btn.onclick = () => handleAreaSelect(grand.value);

                listGroup.appendChild(btn);
            });
        } else {
            listGroup.innerHTML = `<div class="list-group-item disabled small italic">No sub-areas</div>`;
        }
    });

    container.appendChild(accordionWrapper);
    console.log("✅ Bootstrap Accordion rendered");
    console.groupEnd();
}

 async function fetchTableData(tableName) {
   const table = document.getElementById("captains-table");
   const tabTitle = document.getElementById("selectedTitle");

   if (!table || !tabTitle) {
     console.error("❌ Required DOM elements not found: #captains-table or #selectedTitle");
     return;
   }

   const tabHead = table.querySelector("thead");
   const tabBody = table.querySelector("tbody");

   if (!tabHead || !tabBody) {
     console.error("❌ Table structure invalid: missing <thead> or <tbody>");
     return;
   }

   console.log(`📥 Fetching data for table: ${tableName}`);

   try {
     const res = await fetch(`/get_table/${tableName}`, { credentials: "same-origin" });
     if (!res.ok) throw new Error(`Server returned ${res.status}`);
     const data = await res.json();

     if (!Array.isArray(data) || data.length < 3) {
       console.error("❌ Invalid data format received:", data);
       return;
     }

     const [columnHeaders, rows, title] = data;
     tabTitle.textContent = title;
     tabHead.innerHTML = "";
     tabBody.innerHTML = "";

     // Table header
     const headRow = document.createElement("tr");
     headRow.innerHTML = `<th>?</th>` + columnHeaders.map(h => `<th>${h.toUpperCase()}</th>`).join('');
     tabHead.appendChild(headRow);

     const selectedParty = document.getElementById("yourparty")?.value;

     // Table body
     rows.forEach(record => {
       const row = document.createElement("tr");
       row.innerHTML = `<td><input type="checkbox" class="selectRow" name="selectRow[]"></td>` +
         columnHeaders.map(h => {
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


  function getTagsJson(electionTags) {
    const task_tags = {};
    const outcome_tags = {};

    Object.entries(electionTags || {}).forEach(([tag, description]) => {
        if (tag.startsWith("L")) {
            task_tags[tag] = description;
        } else if (tag.startsWith("M")) {
            outcome_tags[tag] = description;
        }
    });

    console.log("___Dash Task Tags", task_tags);
    console.log( "Outcome Tags:", outcome_tags);
    return { task_tags, outcome_tags };
}



  function handleToggle(el) {
    console.log(`Switch is ${el.checked ? 'ON' : 'OFF'}`);
  }

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


  function attachModalListener() {
      const modal = document.getElementById("modalPopup");
      if (!modal) {
          // Try again in 50ms until it exists
          setTimeout(attachModalListener, 50);
          return;
      }

      // Only attach once
      if (!modal.dataset.listenerAttached) {
          modal.addEventListener("hide.bs.modal", function (e) {
              if (preventModalClose) {
                  console.warn("⛔ Prevented modal from closing — add-place mode active");
                  e.preventDefault();
              }
          });
          modal.dataset.listenerAttached = "true";
      }
  }

  // Call this once after map or modal generation
  attachModalListener();


  /* ---------------------------------------------------------
   * CALENDAR <-> MAP TOGGLE
   * --------------------------------------------------------- */
   window.toggleView = function () {

    if (loginScreen.style.visibility === "visible") return;

    const mapVisible = iframeContainer.style.visibility === "visible";

    // Map → Calendar
    if (mapVisible) {

        // Hide map
        iframeContainer.style.visibility = "hidden";
        iframeContainer.style.pointerEvents = "none";
        iframeContainer.style.zIndex = "1";

        iframe.style.visibility = "hidden";
        iframe.style.pointerEvents = "none";

        // Show calendar
        calendar.style.visibility = "visible";
        calendar.style.opacity = "1";
        calendar.style.pointerEvents = "auto";
        calendar.style.zIndex = "200";

        toggleBtn.textContent = "🧭 View Map";
    }

    // Calendar → Map
    else {

        // Hide calendar
        calendar.style.visibility = "hidden";
        calendar.style.opacity = "0";
        calendar.style.pointerEvents = "none";

        // Show map
        iframeContainer.style.visibility = "visible";
        iframeContainer.style.pointerEvents = "auto";
        iframeContainer.style.zIndex = "200";

        iframe.style.visibility = "visible";
        iframe.style.pointerEvents = "auto";

        toggleBtn.textContent = "📅 View Calendar";
    }
};


   // -----------------------------------------------------
   // NEW PLACE CREATED
   // -----------------------------------------------------
   function fillAddPlaceForm(data) {
       const mapping = {
           prefix: "newPlacePrefix",
           house_number: "newPlaceAddress1",
           road: "newPlaceAddress1",
           suburb: "newPlaceAddress2",
           city: "newPlaceAddress2",
           postcode: "newPlacePostcode",
           url: "newPlaceURL"
       };

       // First, clear form fields
       Object.values(mapping).forEach(id => {
           const el = document.getElementById(id);
           if (el) el.value = "";
       });

       // Fill fields
       for (const key in data) {
           if (!data.hasOwnProperty(key)) continue;
           const fieldId = mapping[key];
           if (!fieldId) continue;

           const el = document.getElementById(fieldId);
           if (!el) continue;

           if (fieldId === "newPlaceAddress1") {
               // Combine house_number + road
               el.value = ((data.house_number || "") + " " + (data.road || "")).trim();
           } else if (fieldId === "newPlaceAddress2") {
               // Combine suburb + city
               el.value = ((data.suburb || "") + " " + (data.city || "")).trim();
           } else {
               el.value = data[key] || "";
           }
       }

       // Save lat/lng in dataset
       const form = document.getElementById("addPlaceForm");
       form.dataset.lat = data.lat;
       form.dataset.lng = data.lng;

       form.classList.remove("d-none");
   }

   function activateMapForAddPlace() {
       const iframe = document.getElementById("iframe1");
       const modal = document.getElementById("slot-modal");
       const calendarScroll = document.getElementById("calendar-scroll");

       addPlaceActive = true;         // your existing state variable
       preventModalClose = true;      // stops accidental closing

       iframe.classList.add("map-active");

       // Dim everything else but keep modal visually visible
       if (modal) {
           modal.classList.add("dimmed");
       }

       if (calendarScroll) {
           calendarScroll.classList.add("dimmed");
       }

       console.log("🗺️ Map activated for Add Place.");
   }



   function deactivateMapAfterPlaceSelected() {
     const modal = document.getElementById("slot-modal");
       const calendarScroll = document.getElementById("calendar-scroll");

       iframe.classList.remove("map-active");

       if (modal) {
           modal.classList.remove("dimmed");
       }

       if (calendarScroll) {
           calendarScroll.classList.remove("dimmed");
       }

       addPlaceActive = false;
       preventModalClose = false;

       console.log("📅 Map overlay deactivated; modal restored.");
   }

   function openAddResourceForm() {
   const id = prompt("Enter new resource code (unique ID like R101):");
   if (!id) return;

   const Firstname = prompt("Enter first name:");
   const Surname = prompt("Enter surname:");
   const campaignMgremail = prompt("Enter campaign manager email (optional):") || "";
   const addResourceForm = document.getElementById("addResourceForm");

   if (!Firstname || !Surname) return alert("Firstname and Surname are required");

   // Create resource object
   window.resources[id] = {
       Firstname,
       Surname,
       campaignMgremail
   };

   addResourceForm.classList.add("d-none");

 console.log("Added new resource:", window.resources[id]);
}

   function openAddTaskTagForm() {
       const tag = prompt("Enter new task tag code (e.g., L5):");
       if (!tag) return;

       if (window.task_tags[tag]) {
           return alert("This task tag already exists!");
       }

       const description = prompt("Enter task tag description:");
       if (!description) return;

       window.task_tags[tag] = description;

       console.log("Added new task tag:", tag, description);

       updateConstantsUI(window.latestConstants, window.latestOptions);
       populateAllSelects(window.latestOptions, window.latestConstants);
       alert("Task tag added!");
   }





 const getActiveElectionTab = () =>
     document.querySelector("button.election-tab.active");


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
    // 1. UI: Highlight the active tab
    document.querySelectorAll(".election-tab").forEach(tab =>
        tab.classList.remove("active")
    );
    const clickedTab = [...document.querySelectorAll(".election-tab")]
        .find(tab => tab.dataset.election === electionName);
    if (clickedTab) clickedTab.classList.add("active");

    // 2. UI: Update title
    const title = document.getElementById("calendar-title");
    if (title) title.textContent = `${electionName} Campaigns Calendar`;

    // 3. Backend: Set the election session
    const res = await fetch("/set-election", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ election: electionName })
    });

    const data = await res.json();

    // 4. Update Global State
    window.latestConstants = data.constants;
    window.latestOptions = data.options;
    updateConstantsUI(data.constants, data.options);
    populateAllSelects(data.options, data.constants);
    window.plan = data.constants?.calendar_plan;
    const mapfiles = data.constants?.mapfiles || [];
    const lastMapFile = mapfiles.slice(-1)[0];

    // 5. Load Calendar
    if (window.plan && window.plan.slots) {
        buildCalendarGrid("calendar-grid", 45);
        populateDropdowns();
        loadCalendarPlan(window.plan);
    }

    // 6. Load Map (with extension safety check)
    if (lastMapFile) {
        const correctedPath = lastMapFile.includes('.')
            ? lastMapFile
            : `${lastMapFile}.html`;

        changeIframeSrc(`/thru/${correctedPath}`);
    }

    // 7. Refresh Data Tables
    await fetchTableData("nodelist_xref");
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
    populateAllSelects(resp.options, resp.constants);
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
  console.log("📩 setting startup active tab::", electionName);
  if (!electionName) {
      console.error("No election name found for active tab!", activeTab);
      return;
  }

  try {
      const res = await fetch("/set-election", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({ election: electionName })
      });

      const data = await res.json();
//      window.latestConstants = data.constants;
//      window.latestOptions = data.options;

//      updateConstantsUI(data.constants, data.options);

//      console.log("📩  startup (set-election returned data for:", data.current_election);
//      console.log("🔀 startup places on DOM reload :", window.places);
//      console.log("🔀 startup resources on DOM reload :", window.resources);
//      console.log("🔀 startup areas on DOM reload :", window.areas);
//      console.log("🔀 startup task_tags on DOM reload :", window.task_tags);
//      console.log("🔀 startup outcome_tags on DOM reload :", window.outcome_tags);
//     window.plan = data.constants?.calendar_plan;
//     console.log("📩 calendar_plan::", plan);
  } catch (e) {
      console.error("Failed to set active election:", e);
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

async function fetchBackendURL() {
    try {
        const response = await fetch('/get-backend-url');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        const backendUrl = data.backend_url;

        window.latestConstants  = data.constants;
        window.latestOptions    = data.options;
        window.current_election = data.current_election;

        console.log("Backend URL:", backendUrl);

        window.API = backendUrl.replace(/\/$/, "");

        // Safe + correct
        window.isDev =
            backendUrl.includes("127.0.0.1") ||
            backendUrl.includes("localhost");

        console.log("__isDevelopment?", window.isDev);

    } catch (error) {
        console.error("Error fetching backend URL:", error);
    }
}



 async function getCalendarUpdate(API) {
     const currentTab = getActiveElectionTab();
     if (!currentTab) return;

     try {
         const election = currentTab.dataset.election;
         console.log("📦 Fetching election:", election);

         const response = await fetch(`${API}/current-election?election=${encodeURIComponent(election)}`);
         if (!response.ok) throw new Error(`HTTP ${response.status}`);

         const data = await response.json();
         console.log("📦 Backend response:", data);

          window.plan = data.calendar_plan;

          updateConstantsUI(data.constants, data.options);
          populateAllSelects(data.options, data.constants);
          console.log("📩 update calendar_plan::", plan);
//               console.log("🔀 update places on DOM relaod :", places);
//               console.log("🔀 update resources on DOM relaod :", resources);
//               console.log("🔀 update areas on DOM relaod :", areas);
//               console.log("🔀 update task_tags on DOM relaod :", task_tags);

        window.plan = data.constants?.calendar_plan;
         if (!window.plan || !window.plan.slots) {
             console.warn("⚠️ No slots found in calendar_plan");
             return;
         }

         loadCalendarPlan(window.plan);
         console.log("✅ Calendar plan loaded into UI");

     } catch (err) {
         console.error("🚨 Error fetching calendar plan:", err);
     }
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

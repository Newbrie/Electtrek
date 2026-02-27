  // ----------------------------
  // Table Fetching
  // ----------------------------
  const PARTY_COLORS = {
    O: "brown", R: "cyan", C: "blue", S: "red",
    LD: "yellow", G: "limegreen", I: "indigo",
    PC: "darkred", SD: "orange", Z: "lightgray",
    W: "white", X: "darkgray"
  };


/**
 * Populate the area accordion based on your areas dict.
 * @param {Object} areasDict - Structure: { childId: { node, children: [...] } }
 */
 function populateAreaAccordion(areasDict) {
     console.group("📍 populateAreaAccordion");

     console.log("Input areasDict:", areasDict);

     const container = document.getElementById("areaAccordionContainer");
     if (!container) {
         console.warn("❌ areaAccordionContainer not found in DOM");
         console.groupEnd();
         return;
     }

     // Clear existing content
     container.innerHTML = "";
     console.log("🧹 Cleared existing accordion content");

     const children = Object.values(areasDict || {});
     console.log(`🔢 Found ${children.length} top-level area(s)`);

     children.forEach((child, idx) => {
         if (!child?.node) {
             console.warn(`⚠️ Skipping invalid child at index ${idx}:`, child);
             return;
         }

         console.log(`➡️ Adding child area [${idx}]`, {
             fid: child.node.nid,
             name: child.node.value,
             grandchildren: child.children?.length || 0
         });

         const childDiv = document.createElement("div");
         childDiv.classList.add("mb-2", "area-option");
         childDiv.dataset.fid = child.node.nid;
         childDiv.dataset.name = child.node.value;
         childDiv.textContent = child.node.value;

         container.appendChild(childDiv);

         // -----------------------------
         // Grandchildren
         // -----------------------------
         if (child.children && child.children.length) {
             const subContainer = document.createElement("div");
             subContainer.style.paddingLeft = "15px";

             console.log(`   ↳ Adding ${child.children.length} sub-area(s)`);

             child.children.forEach((grand, gidx) => {
                 if (!grand) {
                     console.warn(`   ⚠️ Skipping invalid grandchild at index ${gidx}`);
                     return;
                 }

                 console.log(`   ➕ Sub-area [${gidx}]`, {
                     fid: grand.nid,
                     name: grand.value
                 });

                 const grandDiv = document.createElement("div");
                 grandDiv.classList.add("mb-1", "area-option");
                 grandDiv.dataset.fid = grand.nid;
                 grandDiv.dataset.name = grand.value;
                 grandDiv.textContent = grand.value;

                 subContainer.appendChild(grandDiv);
             });

             container.appendChild(subContainer);
         } else {
             console.log("   ↳ No sub-areas");
         }
     });

     console.log("✅ Area accordion populated successfully");
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

       alert("Task tag added!");
   }



   window.updateConstantsUI = function (constants, options) {
     window.isUpdatingConstants = true;

    if (!constants || !options) {
        console.warn("updateConstantsUI called without constants or options", { constants, options });
        return;
    }

    console.log("Updating constants UI", { constants, options });

    // =====================================================
    // ⭐ GLOBALS
    // =====================================================
    Object.entries(options).forEach(([key, value]) => {
        window[key] = value;
    });

    window.areas       = options?.areas || {};
    window.places      = constants?.places || {};
    window.resources   = options?.resources || {};
    window.tags        = constants?.tags || {};
    window.territory   = options?.territory || [];

    const result = getTagsJson(window.tags);
    window.task_tags    = result.task_tags;
    window.outcome_tags = result.outcome_tags;

    // =====================================================
    // ⭐ POPULATE ALL SELECTS FIRST
    // =====================================================
    populateAllSelects(options, constants);


    // =====================================================
    // ⭐ SPECIAL CASES FOR SELECTS
    // =====================================================

    // Resources (multi-select)
    const resourcesEl = document.getElementById("resources");
    if (resourcesEl && options.resources) {
        resourcesEl.innerHTML = "";
        Object.entries(options.resources).forEach(([code, person]) => {
            const o = document.createElement("option");
            o.value = code;
            o.textContent = `${person.Firstname} ${person.Surname}`;
            resourcesEl.appendChild(o);
        });
    }

    // candidate & campaignMgr (filtered from selected resources)
    ["candidate", "campaignMgr"].forEach(role => {
        const el = document.getElementById(role);
        if (!el) return;

        el.innerHTML = "";

        const selectedResources = Array.isArray(constants.resources)
            ? constants.resources
            : [];

        selectedResources.forEach(code => {
            const person = options.resources?.[code];
            if (!person) return;

            const o = document.createElement("option");
            o.value = code;
            o.textContent = `${person.Firstname} ${person.Surname}`;
            el.appendChild(o);
        });
    });

    // mapfiles
    const mapfilesEl = document.getElementById("mapfiles");
    if (mapfilesEl && Array.isArray(constants.mapfiles)) {
        mapfilesEl.innerHTML = "";
        constants.mapfiles.forEach((path, idx) => {
            const o = document.createElement("option");
            o.value = path;
            o.textContent = path.split("/").pop();
            if (idx === constants.mapfiles.length - 1) o.selected = true;
            mapfilesEl.appendChild(o);
        });
        mapfilesEl.onchange = () => {
            changeIframeSrc(`/thru/${mapfilesEl.value}`);
        };
    }

    // =====================================================
    // ⭐ APPLY SELECTED VALUES (single + multi + checkbox)
    // =====================================================
    Object.entries(constants).forEach(([key, value]) => {
        const el = document.getElementById(key);
        if (!el) return;

        if (el.tagName === "SELECT") {
            if (el.multiple && Array.isArray(value)) {
                Array.from(el.options).forEach(opt => {
                    opt.selected = value.includes(opt.value);
                });
            } else if (value != null) {
                el.value = value;
            }
        } else if (el.type === "checkbox") {
            el.checked = Boolean(value);
        } else {
            el.value = value ?? "";
        }

        // =====================================================
        // ⭐ AUTO BACKEND UPDATE
        // =====================================================
        el.oninput = () => {

            if (window.isUpdatingConstants) return;   // 🔥 prevents loop

            let newVal;

            if (el.type === "number") newVal = parseFloat(el.value);
            else if (el.type === "checkbox") newVal = el.checked;
            else if (el.multiple) newVal = Array.from(el.selectedOptions).map(o => o.value);
            else newVal = el.value;

            fetch("/set-constant", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    election: document.querySelector(".election-tab.active")?.dataset.election || "",
                    name: key,
                    value: newVal
                })
            })
            .then(res => res.text())
            .then(text => {
                console.log("RAW RESPONSE:", text);
                return JSON.parse(text);
            })
            .then(resp => {
                if (!resp.success) {
                    alert("Failed to update: " + resp.error);
                }
            });
            .catch(err => {
                  console.error("FETCH FAILED:", err);
              });
        };

    });

    if (typeof attachListenersToConstantFields === "function") {
        attachListenersToConstantFields(constants);
    }

    // Optional: any additional dropdown setup
    if (typeof populateDropdowns === "function") {
        populateDropdowns();
    }
    window.isUpdatingConstants = false;

};



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
   console.log("🔀 Switching election to:", electionName);

   // Highlight the active tab
   document.querySelectorAll(".election-tab").forEach(tab =>
       tab.classList.remove("active")
   );

   const clickedTab = [...document.querySelectorAll(".election-tab")]
       .find(tab => tab.dataset.election === electionName);

   if (clickedTab) clickedTab.classList.add("active");

   // Update title immediately
   const title = document.getElementById("calendar-title");
   if (title) title.textContent = `${electionName} Campaigns Calendar`;

   // Tell backend
   const res = await fetch("/set-election", {
       method: "POST",
       headers: { "Content-Type": "application/json" },
       credentials: "same-origin",
       body: JSON.stringify({ election: electionName })
   });

   const data = await res.json();
   console.log("set-election call outcome",data.success);
   window.latestConstants = data.constants;
   window.latestOptions = data.options;
   updateConstantsUI(data.constants, data.options);

  window.plan = data.constants?.calendar_plan;
  const lastMapFile = data.constants?.mapfiles?.slice(-1)[0];

  console.log("🔀 set places on DOM reload :", window.places);
  console.log("🔀 set resources on DOM reload :", window.resources);
  console.log("🔀 set areas on DOM reload :", window.areas);
  console.log("🔀 set task_tags on DOM reload :", window.task_tags);
  console.log("📩 set calendar_plan::", window.plan);


  if (!window.plan || !window.plan.slots) {
      console.warn("⚠️ No slots found in calendar_plan");
      return;
  }
  buildCalendarGrid("calendar-grid", 45);
  populateDropdowns();
  loadCalendarPlan(window.plan);
  console.log("✅ Calendar plan loaded into UI");



   if (lastMapFile) {
     console.log("📩 setting mapfile::", lastMapFile);
      changeIframeSrc(`/thru/${lastMapFile}`);
      console.log("📩 displayed mapfile::", lastMapFile);
   }


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
        body: JSON.stringify({ accumulate: element.checked })
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
  function refreshConstantsUI(callback) {
     console.log("📩 refreshing constants");
      return fetch("/get-constants", { credentials: "same-origin" })
          .then(res => res.json())
          .then(data => {
            console.log("DATA RECEIVED:", data);
              window.latestConstants = data.constants;
              window.latestOptions = data.options;
              window.updateConstantsUI(data.constants, data.options);
              if (callback) callback(data);
              return data.constants;
          });
  }

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

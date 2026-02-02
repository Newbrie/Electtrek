// -----------------------------------------------------
// DOM Content Loaded Event XXXXXXXXXXXXXXXXXXXXXXXXXXXX
// -----------------------------------------------------
console.log("🔥 dashdomcontent.js loaded, readyState =", document.readyState);

  document.addEventListener("DOMContentLoaded", async () => {

    // Call the function to fetch the backend URL used as window.API
  fetchBackendURL();


  let selectedPlaceData = null; // Store data from the map
  let preventModalClose = false;
  let addPlaceActive = false;

  /* ---------------------------------------------------------
   * CALENDAR LOGIN AND CALENDAR BUILD
   * --------------------------------------------------------- */

  // elements
  window.iframeContainer = document.getElementById("iframe-container");
  window.iframe = document.getElementById("iframe1"); // the actual iframe element
  window.calendar = document.getElementById("calendar");
  window.loginScreen = document.getElementById("loginScreen");
  window.loginBtn = document.getElementById("loginBtn");
  window.passwordInput = document.getElementById("password");
  window.loginMessage = document.getElementById("loginMessage");
  window.toggleBtn = document.getElementById("b9");



  /* ---------------------------------------------------------
   * ENSURE TABLE REFRESH ON PAGE LOAD
   * --------------------------------------------------------- */

  const params = new URLSearchParams(window.location.search);
  const table = params.get("loadTable");
  console.log("___ Table being reloaded ", table);
  console.log("___ Is Function ? ", typeof fetchTableData);
  if (table && typeof fetchTableData === "function") {
      console.log("📊 Auto-loading table:", table);
      fetchTableData(table);
  }
  /* ---------------------------------------------------------
   * FETCH AREA ACCORDION FOR MODALS
   * --------------------------------------------------------- */

  try {
      // Fetch areas from backend API
      const res = await fetch("/fetch_areas");
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);

      const data = await res.json();
      // Expected data: { areas: {...} } or your accordion dict

      // Save globally if needed
      window.areas = data.areas || {};

      // Populate the accordion container
      populateAreaAccordion(window.areas);

  } catch (err) {
      console.error("Failed to fetch areas:", err);
      const container = document.getElementById("areaAccordionContainer");
      if (container) {
          container.innerHTML = '<div class="alert alert-danger">Failed to load areas</div>';
      }
  }

  /* ---------------------------------------------------------
   * CALENDAR LOGIN AND CALENDAR BUILD
   * --------------------------------------------------------- */

  console.log("Initial view set: calendar visible, map hidden");


  document.addEventListener("click", function (e) {
      const btn = e.target.closest(".area-option");
      if (!btn) return;

      const fid = btn.dataset.fid;
      const name = btn.dataset.name;
      const select = document.getElementById("areaSelect");

      // toggle selection
      let existing = [...select.options].find(o => o.value === fid);

      if (existing) {
          existing.remove();
          btn.classList.remove("active");
      } else {
          const opt = document.createElement("option");
          opt.value = fid;
          opt.textContent = name;
          opt.selected = true;
          select.appendChild(opt);
          btn.classList.add("active");
      }
  });


  /* ---------------------------------------------------------
   * AWAIT TOGGLEVIEW OR UPDATE TABLE MESSAGES FROM USER
   * --------------------------------------------------------- */

 window.addEventListener("message", async (event) => {
   const data = event.data;


   console.log("📩 Parent received message:", data, "from", event.origin);
   // -----------------------------------------------------
   // toggleView
   // -----------------------------------------------------
   if (data?.type === "toggleView" || data === "toggleView") {
       console.log("📩 Received toggleView from iframe");
       await window.toggleView();
       return;
   }

   // -----------------------------------------------------
   // TABLE UPDATE
   // -----------------------------------------------------
   if (data?.type === "update-table" || data === "update-table") {
       fetchTableData(data.stable);
       return;
   }

     if (data?.type === "newPlaceCreated") {
         document.getElementById("map-overlay").style.display = "none";
         deactivateMapAfterPlaceSelected();

         selectedPlaceData = data;
         console.log("📦 Stored selectedPlaceData:", selectedPlaceData);

         fillAddPlaceForm(selectedPlaceData); // your existing function to fill the modal

         // --- Append new place to window.places ---
         if (!window.places) window.places = {};

         // Use prefix as key, can be adjusted
         const key = selectedPlaceData.prefix || `place_${Date.now()}`;

         // Store object with whatever structure fillSelect expects
         window.places[key] = {
             name: `${selectedPlaceData.house_number || ""} ${selectedPlaceData.road || ""}, ${selectedPlaceData.suburb || ""} ${selectedPlaceData.city || ""}`.trim(),
             lat: selectedPlaceData.lat,
             lng: selectedPlaceData.lng,
             postcode: selectedPlaceData.postcode
         };

         // --- Refresh the select dropdown ---
         fillSelect("placeSelect", window.places);

         window.latestConstants.places[key] = window.places[key];

         updateConstantsUI(window.latestConstants, window.latestOptions);

//         window.iframe.classList.add("dimmed");
         preventModalClose = false;
         addPlaceActive = false;
     }
});

// ------------------------------
// IN CALENDAR MODAL Add Place button handler
// ------------------------------
document.getElementById("addPlaceBtn").addEventListener("click", () => {

    const overlay = document.getElementById("map-overlay");
    const overlayIframe = document.getElementById("overlay-iframe");

    overlayIframe.src = document.getElementById("iframe1").src;
    overlay.style.display = "block";

    overlayIframe.onload = () => {
        console.log("📌 Iframe loaded — sending enableAddPlace");
        overlayIframe.contentWindow.postMessage(
            { type: "enableAddPlace" },
            "*"
        );
    };
});

// ------------------------------
// IN CALENDAR MODAL Save button handler
// ------------------------------
document.getElementById("saveNewPlace").addEventListener("click", () => {
    const form = document.getElementById("addPlaceForm");

    // Use the currently selected place data
    const newPlace = selectedPlaceData;
    if (!newPlace) {
        console.error("No place data to save!");
        return;
    }

    // Ensure places dict exists
    if (!window.places) window.places = {};
    window.places[newPlace.prefix] = newPlace;

    // Update dropdown (only prefix)
    fillSelect("placeSelect", window.places);

    // Add marker permanently to FeatureGroup if available
    const markerGroup = window.Featurelayers?.['marker'];
    if (markerGroup && window.pinMarker) {
        markerGroup.addLayer(window.pinMarker);

        // Optionally track by prefix for later reference
        if (!window.permanentMarkers) window.permanentMarkers = {};
        window.permanentMarkers[newPlace.prefix] = window.pinMarker;

        // Clear temporary pointer
        window.pinMarker = null;
    }

    console.log("📌 New place saved:", newPlace);
    console.log("📌 Updated places dict:", window.places);

    // Hide mini-place form and restore overlay/iframe
    form.classList.add("d-none");
    const overlayIframe = document.getElementById("overlay-iframe");
    if (overlayIframe) {
        overlayIframe.classList.remove("dimmed");
        overlayIframe.style.visibility = "hidden";
    }

    // Reset awaitingNewPlace flag
    window.awaitingNewPlace = false;
});

// ------------------------------
// IN CALENDAR MODAL Show add-resource form
// ------------------------------
//
document.getElementById("addResourceBtn").addEventListener("click", () => {
    document.getElementById("addResourceForm").classList.remove("d-none");
});

// ------------------------------
// IN CALENDAR MODAL Show save-resource form
// ------------------------------
//
document.getElementById("saveNewResource").addEventListener("click", () => {
    const first = newResFirst.value.trim();
    const last  = newResLast.value.trim();
    const email = newResEmail.value.trim();

    if (!first || !last) {
        alert("Firstname and surname required");
        return;
    }

    const code = (first[0] + last).toUpperCase();

    const resourceObj = {
        Firstname: first,
        Surname: last,
        campaignMgremail: email
    };

    // Update global state
    window.resources[code] = resourceObj;

    // ALSO update latestOptions (otherwise UI resets)
    window.latestOptions.resources[code] = resourceObj;

    populateDropdowns();
    updateConstantsUI(window.latestConstants, window.latestOptions);


});

// ------------------------------
// IN CALENDAR MODAL Show add-tasktag form
// ------------------------------
//
document.getElementById("addTaskTagBtn").addEventListener("click", () => {
    document.getElementById("addTaskTagForm").classList.remove("d-none");
});

// ------------------------------
// IN CALENDAR MODAL Show save-tasktag form
// ------------------------------
//
document.getElementById("saveNewTag").addEventListener("click", () => {
    const code  = newTagCode.value.trim();
    const label = newTagLabel.value.trim();

    if (!code || !label) {
        alert("Both code and label required");
        return;
    }

    // Update global
    window.task_tags[code] = label;

    // ALSO update options so updateConstantsUI does not overwrite
    window.latestOptions.task_tags[code] = label;

    // Refresh UI
    populateDropdowns();
    updateConstantsUI(window.latestConstants, window.latestOptions);

    addTaskTagForm.classList.add("d-none");
});

console.log("🔀 places on DOM relaod :", window.places);
console.log("🔀 resources on DOM relaod :", window.resources);
console.log("🔀 areas on DOM relaod :", window.areas);
console.log("🔀 task_tags on DOM relaod :", window.task_tags);

    // Call this function on startup to tell backend which election is active


// ------------------------------
// IN CALENDAR MODAL Wait for the tabs to be ready
// ------------------------------
//
await ensureTabsReady();
// 2️⃣ Tell backend which election is active
await setActiveElectionOnStartup();

// 4. Build calendar UI BEFORE loading calendar data
console.log("📅 Building calendar UI…");
buildCalendarGrid("calendar-grid", 45);
populateDropdowns();
console.log("📅 Calendar UI ready.");

// 5. NOW load plan into fully created calendar
await getCalendarUpdate(window.API);
console.log("📅 Calendar data loaded.");


/* ---------------------------------------------------------
 * Initial state — hide map + calendar, show login unless in dev
 * --------------------------------------------------------- */

if (window.isDev) {
    console.warn("⚠ DEV MODE: Skipping login screen");

    loginScreen.style.visibility = "hidden";
    console.log("Setting initial view: MAP visible");

   // --- Map visible ---
   iframeContainer.style.visibility = "visible";
   iframeContainer.style.opacity = "1";
   iframeContainer.style.pointerEvents = "auto";
   iframeContainer.style.zIndex = "200";

   iframe.style.visibility = "visible";
   iframe.style.pointerEvents = "auto";

   // --- Calendar hidden ---
   calendar.style.visibility = "hidden";
   calendar.style.opacity = "0";
   calendar.style.pointerEvents = "none";
   calendar.style.zIndex = "1";

   // --- Toggle button should switch TO the calendar ---
   toggleBtn.textContent = "📅 View Calendar";

    window.loggedIn = true;

} else {
    // Normal login behaviour
    loginScreen.style.visibility = "visible";
    console.log("Setting initial view: MAP visible");

   // --- Map visible ---
   iframeContainer.style.visibility = "visible";
   iframeContainer.style.opacity = "1";
   iframeContainer.style.pointerEvents = "auto";
   iframeContainer.style.zIndex = "200";

   iframe.style.visibility = "visible";
   iframe.style.pointerEvents = "auto";

   // --- Calendar hidden ---
   calendar.style.visibility = "hidden";
   calendar.style.opacity = "0";
   calendar.style.pointerEvents = "none";
   calendar.style.zIndex = "1";

   // --- Toggle button should switch TO the calendar ---
   toggleBtn.textContent = "📅 View Calendar";
    window.loggedIn = false;
}


/* ---------------------------------------------------------
 * LOGIN state — show hidden map and calendar
 * --------------------------------------------------------- */

passwordInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        loginBtn.click();
    }
});


 toggleBtn.addEventListener("click", async () => {
       await window.toggleView();
   });


/* ---------------------------------------------------------
 * GENERAL ELEMENTS
 * --------------------------------------------------------- */
const tableSelector = document.getElementById("tableSelector");
const resourcesToggle = document.getElementById("resources-toggle");
const resourcesContainer = document.getElementById("resources-container");

const electionTabs = document.querySelectorAll(".election-tab");


const changeIframe = (url) => changeIframeSrc(url);



/* ---------------------------------------------------------
* TRIGGER TABLE DATA REFRESH USING TABLE SELECTOR
* --------------------------------------------------------- */
if (tableSelector) {
    tableSelector.addEventListener("change", (e) => {
        fetchTableData(e.target.value);
    });
}



for (const [id, url] of Object.entries(iframeButtons)) {
    const btn = document.getElementById(id);
    if (btn) btn.addEventListener("click", () => changeIframe(url));
}


/* ---------------------------------------------------------
* LOGOUT BUTTON
* --------------------------------------------------------- */
document.getElementById("logout-button")?.addEventListener("click", () => {
    window.location.href = "/logout";
});


/* ---------------------------------------------------------
* RESET-ELECTION TERRITORY BUTTON
* --------------------------------------------------------- */

const territorySelect = document.getElementById("territory");
const mapIframe = document.getElementById("iframe1");

territorySelect.addEventListener("change", async () => {
    const mapfile = territorySelect.value;
    if (!mapfile) return;

    try {
        // 1️⃣ persist selection
        const res = await fetch("/update-territory", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ mapfile })
        });

        if (!res.ok) {
            throw new Error("Failed to update territory");
        }

        // 2️⃣ update map iframe
        mapIframe.src = `/thru/${encodeURIComponent(mapfile)}`;

    } catch (err) {
        console.error(err);
        alert("Could not save territory selection");
    }
});



document.getElementById("b0")?.addEventListener("click", () => {
  const tab = getActiveElectionTab();
  if (!tab) return;

  fetch("/update-territory", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({
          election: tab.dataset.election
      })
  })
      .then(res => res.json())
      .then(resp => {
          if (resp.success) refreshConstantsUI();
      });

});


/* ---------------------------------------------------------
 * ELECTION RESOURCES DROPDOWN BUTTON
 * --------------------------------------------------------- */
resourcesToggle?.addEventListener("click", () => {
    const visible = resourcesContainer.style.display === "block";
    resourcesContainer.style.display = visible ? "none" : "block";
    resourcesToggle.textContent = visible ? "Resources ⬇" : "Resources ⬆";
});

/* ---------------------------------------------------------
 * SET ELECTION TAB CLICK HANDLER
 * --------------------------------------------------------- */
 document.addEventListener("click", async (e) => {
     if (!e.target.classList.contains("election-tab")) return;

     const electionName = e.target.dataset.election;
     console.log("📩 Switching to:", electionName);
     await switchElection(electionName);

     // Optional: keep any extra tab sync logic
     syncStreamsSelectWithTabs();
 });




/* ---------------------------------------------------------
 * ELECTION DATA RESOURCE SELECTION REFRESH
 * --------------------------------------------------------- */
const resourcesSelect = document.getElementById("resources");

resourcesSelect?.addEventListener("blur", () => {
    const selected = Array.from(resourcesSelect.selectedOptions).map(o => o.value);
    const tab = getActiveElectionTab();
    if (!tab) return;

    fetch("/set-constant", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
            election: tab.dataset.election,
            name: "resources",
            value: selected
        })
    })
        .then(res => res.json())
        .then(resp => {
            if (resp.success) refreshConstantsUI();
        });
});


/* ---------------------------------------------------------
 *  PARENT-NODE REASSIGNMENT SELECTION
 * --------------------------------------------------------- */
document.addEventListener("change", (e) => {
    if (!e.target.classList.contains("parent-dropdown")) return;

    const select = e.target;
    const subject = select.dataset.subject;

    fetch("/reassign_parent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            subject,
            old_parent: select.dataset.oldValue,
            new_parent: select.value
        })
    })
        .then(r => r.json())
        .then(data => {
            if (data.status === "success") {
              select.dataset.oldValue = select.value;
                console.log(`${data.message}`);
                changeIframeSrc(`${data.mapfile}`);
            }
        });
});


  console.log("📅 Calendar dropdowns populated…");

  // Buttons (use correct IDs)
  const switchToMapBtn = document.getElementById("switch-tomap-btn");
  const saveCalendarBtn = document.getElementById("save-calendar-btn"); // ✅ matches HTML ID
  const generateSummaryBtn = document.getElementById("generate-summary-btn");
  const saveSlotBtn = document.getElementById("saveSlotBtn");
  const clearSlotBtn = document.getElementById("clearSlotBtn");

  // Attach button event handlers
  switchToMapBtn.addEventListener("click", window.toggleView);
  saveCalendarBtn.addEventListener("click", saveCalendarPlan);
  generateSummaryBtn.addEventListener("click", generateSummaryReport);
  saveSlotBtn.addEventListener("click", handleSaveSlot);
  clearSlotBtn.addEventListener("click", handleClearSlot);
  // Attach listers to constants
  attachListenersToConstantFields(constants);
});

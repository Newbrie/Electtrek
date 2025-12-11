// -----------------------------------------------------
// DOM Content Loaded Event XXXXXXXXXXXXXXXXXXXXXXXXXXXX
// -----------------------------------------------------

  document.addEventListener("DOMContentLoaded", async () => {

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
// Add Place button handler
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
// Save button handler
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


// Show add-resource form
document.getElementById("addResourceBtn").addEventListener("click", () => {
    document.getElementById("addResourceForm").classList.remove("d-none");
});

// Save new resource
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


// Show add-task-tag form
document.getElementById("addTaskTagBtn").addEventListener("click", () => {
    document.getElementById("addTaskTagForm").classList.remove("d-none");
});

// Save new tag
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


// 1. Wait for tabs
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
 * expose refreshTableData so iframe can call the parent
 * --------------------------------------------------------- */





// Initial state — hide map + calendar, show login unless in dev mode

if (window.isDev) {
    console.warn("⚠ DEV MODE: Skipping login screen");

    loginScreen.style.visibility = "visible";
    calendar.style.visibility = "hidden"; // show calendar initially
    iframe.style.visibility = "visible";  // hide map initially
    toggleBtn.textContent = "📅 View Map"; // button shows calendar option
    calendar.dataset.loaded = "true";    // avoid duplicate fetches

    window.loggedIn = true;

} else {
    // Normal login behaviour
    loginScreen.style.visibility = "visible";
    calendar.style.visibility = "hidden";  // hide calendar
    iframe.style.visibility = "visible";   // show map by default
    toggleBtn.textContent = "📅 View Map"; // button shows calendar option
    window.loggedIn = false;
}


// ENTER triggers login
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
     * TABLE SELECTOR
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
     * LOGOUT
     * --------------------------------------------------------- */
    document.getElementById("logout-button")?.addEventListener("click", () => {
        window.location.href = "/logout";
    });


    /* ---------------------------------------------------------
     * RESET-ELECTION TERRITORY
     * --------------------------------------------------------- */

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
     * RESOURCES TOGGLE
     * --------------------------------------------------------- */
    resourcesToggle?.addEventListener("click", () => {
        const visible = resourcesContainer.style.display === "block";
        resourcesContainer.style.display = visible ? "none" : "block";
        resourcesToggle.textContent = visible ? "Resources ⬇" : "Resources ⬆";
    });

    /* ---------------------------------------------------------
     * TAB CLICK HANDLER
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
     * RESOURCES UPDATE
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
     * PARENT-DROPDOWN REASSIGNMENT
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

});

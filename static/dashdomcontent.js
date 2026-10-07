// -----------------------------------------------------
// DOM Content Loaded Event XXXXXXXXXXXXXXXXXXXXXXXXXXXX
// -----------------------------------------------------
console.log("🔥 dashdomcontent.js loaded, readyState =", document.readyState);
document.addEventListener("DOMContentLoaded", async () => {

  const iframeWin = document.getElementById("iframe1")?.contentWindow;

  const startHour = 9, endHour = 21, slotDuration = 2;

  // ----------------------------
  // mapfile to parent Flash Message Handling (Now safe because the DOM is loaded)
  // ----------------------------
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

  window.messages?.forEach(msg => addMessageToLog(msg));

  // ----------------------------
  // iframe postMessage handling
  // ----------------------------
  if (typeof bindEvent === "function") {
      bindEvent(window, "message", (e) => {
          addMessageToLog(e.data?.type || String(e.data));
      });
  }

  /* ---------------------------------------------------------
   * ENSURE TABLE REFRESH ON PAGE LOAD
   * --------------------------------------------------------- */



  const params = new URLSearchParams(window.location.search);
  const table = params.get("loadTable");
  console.log("___ Table being reloaded ", table);
  console.log("___ Is Function ? ", typeof iframeWin.fetchTableData);
  if (table && typeof iframeWin.fetchTableData === "function") {
      console.log("📊 Auto-loading table:", table);
      await iframeWin.fetchTableData(table);
  }




// ------------------------------
// IN CALENDAR MODAL Wait for the tabs to be ready
// ------------------------------
//
await ensureTabsReady();
// 2️⃣ Tell backend which election is active
await setActiveElectionOnStartup();
await refreshConstantsUI();

/* ---------------------------------------------------------
 * Initial state — hide map + calendar, show login unless in dev
 * --------------------------------------------------------- */


  // Normal login behaviour

  console.log("Setting initial view: MAP visible");


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
    tableSelector.addEventListener("click", async (e) => {
        await iframeWin.fetchTableData(e.target.value);
    });

    tableSelector.addEventListener("change", async (e) => {
        await iframeWin.fetchTableData(e.target.value);
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

     e.preventDefault();   // 👈 ADD THIS LINE — stops default browser navigation
                            // (e.g. an <a href> or form submit) from firing a
                            // second, bodyless GET to /set-election alongside
                            // our real POST below.

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

 // 1. Define the reusable helper function
 window.getActiveElectionName = function() {
     const activeTab = document.querySelector('#election-tabs .election-tab.active');
     return activeTab ? activeTab.getAttribute('data-election') : null;
 };

resourcesSelect?.addEventListener("blur", () => {
    const selected = Array.from(resourcesSelect.selectedOptions).map(o => o.value);
    const tab = getActiveElectionName();
    if (!tab) return;

    fetch("/set-constant", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            election: tab.dataset.election,
            name: "resources",
            value: selected
        }),
        credentials: "include"
    })
    .then(res => res.json()) // ✅ convert response to JSON
    .then(resp => {
        console.log(`✅ Response for "resources":`, resp);

        if (resp.constants) {
            updateConstantsUI(resp.constants, resourcesSelect.options); // ✅ pass defined options
            iframeWin.populateAllSelects(resourcesSelect.options, resp.constants);
        }

        if (!resp.success) {
            console.warn(`⚠️ Failed to update "resources":`, resp.error); // ✅ use fixed key
        }
    })
    .catch(err => {
        console.error("Failed to update resources constant:", err);
    });
});


/* ---------------------------------------------------------
 *  PARENT-NODE REASSIGNMENT / DELETE SELECTION
 * --------------------------------------------------------- */
 document.addEventListener("change", async (e) => {

    if (!e.target.classList.contains("parent-dropdown")) return;

    const select = e.target;
    const nid = select.dataset.nid;
    const oldParentNid = select.dataset.oldParentNid;
    const newParentNid = select.value;

    if (!nid) {
        console.error("Missing node ID");
        return;
    }

    select.disabled = true;

    try {

        // DELETE
        if (newParentNid === "__DELETE__") {

            if (!confirm("Delete this node?")) {
                select.disabled = false;
                return;
            }

            const res = await fetch("/delete_node", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ nid })
            });

            const data = await res.json();

            if (!res.ok || data.status !== "success") {
                throw new Error(data.message || "Delete failed");
            }

            if (data.mapfile) changeIframeSrc(data.mapfile);
            await iframeWin.fetchTableData("nodelist_xref");
        }

        // REASSIGN
        else {

            const res = await fetch("/reassign_parent", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    nid,
                    new_parent_nid: newParentNid
                })
            });

            const data = await res.json();

            if (!res.ok || data.status !== "success") {
                throw new Error(data.message || "Reassignment failed");
            }

            select.dataset.oldParentNid = newParentNid;

            if (data.mapfile) changeIframeSrc(data.mapfile);
            await iframeWin.fetchTableData("nodelist_xref");
        }

    } catch (err) {
        console.error("Node operation failed:", err);
    } finally {
        select.disabled = false;
    }
});





    // Attach listers to constants
  attachListenersToConstantFields(window.latestConstants);



// Listtener for the bulkaction select
// Use a named function to prevent accidental double-binding
function handleBulkAction() {
    const dropdown = document.getElementById("groupActionSelect");
    const targetRoute = dropdown.value;

    // 1. Clear previous logs
    console.clear();
    console.log("🚀 Bulk Action Started");

    // 🎯 Get the active election context
    const selectedElection = window.getActiveElectionName ? window.getActiveElectionName() : null;

    if (!selectedElection) {
        alert("Error: Could not determine the active election context.");
        console.error("Bulk action halted: window.getActiveElectionName() returned empty or is not defined.");
        return;
    }

    console.log(`Election Context: [${selectedElection}]`);

    // Inside your btnRunGroupAction click listener:
    const selectedNids = Array.from(document.querySelectorAll(".selectRow:checked"))
        .map(cb => {
            // Try every possible way to find that ID
            const id = cb.getAttribute('data-nid') || cb.dataset.nid || cb.value;
            console.log("Checkbox element:", cb, "Extracted ID:", id);
            return id;
        })
        .filter(id => id && id !== "on" && id !== "undefined");

    // STOP if we have Nones
    if (selectedNids.length === 0 || selectedNids.includes(undefined)) {
        console.error("Selected NIDs contains invalid data:", selectedNids);
        alert("Error: Checkboxes found, but IDs are missing from the elements.");
        return;
    }

    // 3. Disable the button to prevent "Quick Succession" double-clicks
    const btn = document.getElementById("btnRunGroupAction");
    btn.disabled = true;

    // 📦 Send both election context and NIDs to the server
    fetch(targetRoute, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            election: selectedElection,
            nids: selectedNids
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert(`Success! Processed ${data.count} nodes.`);
            if (data.map_url) {
                document.getElementById("iframe1").src = data.map_url;
            }
        } else {
            alert("Server Error: " + data.error);
        }
    })
    .catch(err => console.error("Fetch error:", err))
    .finally(() => {
        btn.disabled = false; // Re-enable button
    });
}



// Ensure we only attach the listener ONCE
const bulkBtn = document.getElementById("btnRunGroupAction");
bulkBtn.replaceWith(bulkBtn.cloneNode(true)); // This trick clears all existing listeners
document.getElementById("btnRunGroupAction").addEventListener("click", handleBulkAction);
// 4. Initial Load

const dataPath = document.getElementById('territory');
selectNode(dataPath);


});

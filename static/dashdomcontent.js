// -----------------------------------------------------
// DOM Content Loaded Event XXXXXXXXXXXXXXXXXXXXXXXXXXXX
// -----------------------------------------------------
console.log("🔥 dashdomcontent.js loaded, readyState =", document.readyState);
document.addEventListener("DOMContentLoaded", async () => {


  const startHour = 9, endHour = 21, slotDuration = 2;

  // ----------------------------
  // mapfile to parent Flash Message Handling (Now safe because the DOM is loaded)
  // ----------------------------
  const logList = document.querySelector("#logwin .flashes");



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
  console.log("___ Is Function ? ", typeof fetchTableData);
  if (table && typeof fetchTableData === "function") {
      console.log("📊 Auto-loading table:", table);
      await fetchTableData(table);
  }




// ------------------------------
// IN CALENDAR MODAL Wait for the tabs to be ready
// ------------------------------
//
await ensureTabsReady();
// 2️⃣ Tell backend which election is active
await setActiveElectionOnStartup();
await refreshConstantsUI();



// Helper fallback if areaTree is structured as a nested object rather than a flat path map
function findDictByPath(tree, targetPath) {
    // If your tree structure requires recursive traversal, adapt this lookup logic,
    // otherwise fallback to letting selectNode handle the fetch route if areaTree lookup is unavailable.
    return tree[targetPath] || null;
}


});

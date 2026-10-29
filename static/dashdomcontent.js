// -----------------------------------------------------
// DOM Content Loaded Event XXXXXXXXXXXXXXXXXXXXXXXXXXXX
// -----------------------------------------------------
console.log("🔥 dashdomcontent.js loaded, readyState =", document.readyState);
document.addEventListener("DOMContentLoaded", async () => {

  console.log("[IFR] context", {
      isIframe: window.self !== window.top,
      own: { places: typeof window.places, task_tags: typeof window.task_tags },
      parent: (() => {
          try {
              return {
                  places: typeof window.parent.places,
                  task_tags: typeof window.parent.task_tags,
                  taskTagKeys: Object.keys(window.parent.task_tags || {}).length
              };
          } catch (e) { return "parent not accessible: " + e.message; }
      })()
  });

  const startHour = 9, endHour = 21, slotDuration = 2;

  // ----------------------------
  // mapfile to parent Flash Message Handling (Now safe because the DOM is loaded)
  // ----------------------------


  const territoryDisplay = document.getElementById("territory-display");
  const territoryAccordion = document.getElementById("territory-accordion");

  if (territoryDisplay && territoryAccordion) {
      territoryDisplay.addEventListener("click", (e) => {
          e.stopPropagation();
          // Toggle visibility of the custom accordion panel
          const isVisible = territoryAccordion.style.display === "block";
          territoryAccordion.style.display = isVisible ? "none" : "block";
      });

      // Close accordion if clicking outside
      document.addEventListener("click", (e) => {
          if (!territoryDisplay.contains(e.target) && !territoryAccordion.contains(e.target)) {
              territoryAccordion.style.display = "none";
          }
      });
  }


  window.messages?.forEach(msg => addMessageToLog(msg));

// ----------------------------
// iframe postMessage handling
// ----------------------------
let areaTreeRequest = 0;   // guards against out-of-order responses



const handleIframeMessage = async (e) => {
    if (e.origin !== window.location.origin) return;   // ignore foreign frames
    const data = e.data;
    if (!data || typeof data !== 'object') {
        if (data) addMessageToLog(String(data));
        return;
    }

    addMessageToLog(data.type || JSON.stringify(data).slice(0, 80));

    const pathChanged =
        data.type === 'iframeHydrationPayload' ||
        data.type === 'iframeSwitchElection' ||
        data.type === 'node-changed' ||
        data.mapfile || data.currentNodePath;

    if (!pathChanged) return;

    // 🎯 1. Update active path and mapfile globals
    if (data.currentNodePath) window.currentNodePath = data.currentNodePath;
    if (data.mapfile)         window.mapfile = data.mapfile;

    // 🎯 2. If payload was pushed from iframe, hydrate parent globals directly (NO double fetch!)
    // 🎯 2. If payload was pushed from iframe, hydrate parent globals directly (NO double fetch!)
      if (data.type === 'iframeHydrationPayload') {
          window.current_election = data.current_election || window.current_election;
          // Ensure currentElectionName is set from active tab if missing
          if (!window.currentElectionName) {
              window.currentElectionName = window.current_election || "DEMO"; // or read active tab element
          }
          window.options           = data.options || window.options || {};
          window.latestConstants   = data.constants || window.constants;

          window.task_tags        = window.options.task_tags || [];
          window.resources        = window.options.resources || [];
          window.places           = window.options.places || [];
          window.areas            = window.options.areas || {};

          // 🎯 Set areaTree directly from options.areas payload before refreshing DOM
          if (window.options.areas) {
              window.areaTree = window.options.areas;
          }

          if (window.task_tags.length > 0) {
              window.taskTree = window.task_tags;
          }
      }

};

if (typeof bindEvent === 'function') {
    bindEvent(window, 'message', handleIframeMessage);
} else {
    window.addEventListener('message', handleIframeMessage);
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

bindIframeButtons();




});

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

async function refreshAreaTree() {
    const myRequest = ++areaTreeRequest;
    try {
        const r = await fetch('/get-constants', {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        if (!r.ok) throw new Error(`get-constants ${r.status}`);
        const payload = await r.json();

        // A newer navigation has started since this request: drop this result
        if (myRequest !== areaTreeRequest) return;

        const tree = payload.options?.areas;      // set_election logs options.get('areas')
        if (!tree) {
            console.warn('refreshAreaTree: no options.areas in response', Object.keys(payload.options || {}));
            return;
        }

        window.areaTree = tree;
        if (typeof window.initAccordionFromOptions === 'function') {
            window.initAccordionFromOptions(tree);
            console.log('🌳 [Parent] Accordion refreshed for path:', window.currentNodePath);
        }
    } catch (err) {
        console.error('refreshAreaTree failed:', err);
    }
}
window.refreshAreaTree = refreshAreaTree;

const handleIframeMessage = (e) => {
    if (e.origin !== window.location.origin) return;   // ignore foreign frames
    const data = e.data;
    if (!data || typeof data !== 'object') {
        if (data) addMessageToLog(String(data));
        return;
    }

    addMessageToLog(data.type || JSON.stringify(data).slice(0, 80));

    const pathChanged =
        data.type === 'updateNodePath' ||
        data.type === 'iframeSwitchElection' ||
        data.type === 'node-changed' ||
        data.mapfile || data.currentNodePath;

    if (!pathChanged) return;

    if (data.currentNodePath) window.currentNodePath = data.currentNodePath;
    if (data.mapfile)         window.mapfile = data.mapfile;

    // The tree is depth-limited and election/area specific, so fetch it again
    // rather than reusing the one injected at page load.
    refreshAreaTree();
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

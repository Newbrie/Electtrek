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
    // If you use a custom bindEvent wrapper or standard window.addEventListener:
    const handleIframeMessage = (e) => {
        const data = e.data;
        if (!data) return;

        addMessageToLog(data.type || String(data));

        // 🎯 Catch node/map changes from the iframe and update parent state instantly
        if (data.type === "updateNodePath" || data.type === "iframeSwitchElection" || data.mapfile || data.currentNodePath) {
            if (data.currentNodePath) {
                window.currentNodePath = data.currentNodePath;
            }
            if (data.mapfile) {
                window.mapfile = data.mapfile;
            }

            // Force parent accordion to re-render for the newly selected area hierarchy
            if (typeof initAccordionFromOptions === "function" && window.areaTree) {
                initAccordionFromOptions(window.areaTree);
                console.log("🌳 [Parent] Accordion refreshed for path:", window.currentNodePath);
            }
        }
    };

    if (typeof bindEvent === "function") {
        bindEvent(window, "message", handleIframeMessage);
    } else {
        window.addEventListener("message", handleIframeMessage);
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

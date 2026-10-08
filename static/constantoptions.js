
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

initAccordionFromOptions = (optionsData) => {
    console.log("🔍 [Accordion Init] Starting with optionsData:", optionsData);

    const areas = optionsData?.areas || window.currentOptions?.areas;
    console.log("🔍 [Accordion Init] Resolved areas object:", areas);

    if (areas && typeof areas === 'object') {
        const districtKey = Object.keys(areas).find(k => k.toUpperCase() === "SURREY_HEATH") || Object.keys(areas)[0];
        console.log("🔍 [Accordion Init] Found districtKey:", districtKey);

        const targetBranch = districtKey ? { [districtKey]: areas[districtKey] } : areas;
        console.log("🔍 [Accordion Init] Target branch payload:", targetBranch);

        if (targetBranch) {
            // A. Update display path title
            const displayTitle = (window.initialPath ? window.initialPath.split('/').pop() : "Selection").replace(/_/g, ' ');
            const displayElement = document.getElementById('display-path');
            if (displayElement) {
                displayElement.innerText = displayTitle;
                console.log("✅ [Accordion Init] Updated display-path element to:", displayTitle);
            } else {
                console.warn("⚠️ [Accordion Init] #display-path element not found in DOM.");
            }

            // Check container existence
            const containerEl = document.getElementById('children-list');
            console.log("🔍 [Accordion Init] Checking target container #children-list:", containerEl);

            // B. Render using tree selector
            if (typeof window.renderTreeSelector === "function") {
                console.log("🚀 [Accordion Init] window.renderTreeSelector found. Invoking...");

                window.renderTreeSelector(targetBranch, {
                    containerId: 'children-list',
                    accordionId: 'election-accordion',
                    emptyMessage: 'No sub-divisions available',
                    allLabel: (name) => `${name.replace(/_/g, ' ')}`,
                    createButton: (parentElement, nodeName, labelText, className) => {
                        console.log("🛠️ [renderTreeSelector] createButton callback triggered for:", nodeName, "with label:", labelText);

                        const btn = document.createElement('button');
                        btn.type = 'button';
                        btn.className = `btn btn-sm w-100 text-start py-1 px-3 ${className || ''}`;
                        btn.textContent = labelText.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase());

                        btn.onclick = (e) => {
                            e.stopPropagation();
                            console.log("📍 [Accordion Click] Clicked node:", nodeName);
                            if (typeof selectNode === "function") {
                                selectNode(nodeName);
                            }
                        };
                        parentElement.appendChild(btn);
                    }
                });
                console.log("✅ Successfully executed renderTreeSelector.");
            } else {
                console.error("❌ [Accordion Init] window.renderTreeSelector is NOT a function!");
            }
        } else {
            console.warn("⚠️ [Accordion Init] targetBranch is empty or null.");
        }
    } else {
        console.log("⏳ [Accordion Init] Areas data not ready yet. Retrying in 150ms...");
        setTimeout(() => initAccordionFromOptions(optionsData), 150);
        return;
    }

    if (typeof selectNode === "function" && window.initialPath) {
        console.log("🚀 [Accordion Init] Calling initial selectNode with:", window.initialPath);
        selectNode(window.initialPath);
    }
};

window.updateConstantsUI = function (constants, options) {
    if (window.isUpdatingConstants) {
        console.warn("[UCUI:0] Skipped: already running (re-entrant call?)", new Error().stack);
        return;
    }
    window.isUpdatingConstants = true;
    console.log("[UCUI:0] START");

    try {
        // ...existing code, with these between sections:
        console.log("[UCUI:0] globals done");
        console.log("[UCUI:0] resources done");
        console.log("[UCUI:0] candidate/manager done");
        console.log("[UCUI:0] mapfiles done");
        console.log("[UCUI:0] apply loop done");
        console.log("[UCUI:0] END (reached bottom)");
    } catch (err) {
        console.error("[UCUI:0] CRASH", err);
        throw err;
    } finally {
        window.isUpdatingConstants = false;
    }
};

window.updateConstantsUI = function (constants, options) {

  if (window.isUpdatingConstants) {
      console.warn("[UCUI:0] Skipped: already running (re-entrant call?)", new Error().stack);
      return;
  }
  window.isUpdatingConstants = true;
  console.log("[UCUI:0] START");

    try {
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

        window.areas     = options?.areas || {};
        window.places    = constants?.places || {};
        window.resources = options?.resources || {};
        window.tags      = constants?.tags || {};
        window.task_tags    = options.task_tags || {};
        window.outcome_tags = options.outcome_tags || {};

        console.log("[UCUI:0] globals done");

        // =====================================================
        // Resources
        // =====================================================
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
        console.log("[UCUI:0] resources done");

        // =====================================================
        // Candidate / Manager
        // =====================================================
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
        console.log("[UCUI:0] candidate/manager done");

        // =====================================================
        // Mapfiles
        // =====================================================
        // =====================================================
        const mapfilesEl = document.getElementById("mapfiles");


    if (mapfilesEl && Array.isArray(constants.mapfiles) && constants.mapfiles.length > 0) {
        mapfilesEl.innerHTML = "";

        constants.mapfiles.forEach(path => {
            const o = document.createElement("option");
            o.value = path;
            o.textContent = path.split("/").pop();
            mapfilesEl.appendChild(o);
        });



        // Default to the most recent map in the array
        const latestMap = constants.mapfiles[constants.mapfiles.length - 1];
        mapfilesEl.value = latestMap;

        mapfilesEl.onchange = () => {
            if (window.isUpdatingConstants) return;

            const selectedValue = mapfilesEl.value;

            // Ensure the path has an extension before sending to the /thru/ route
            const finalPath = selectedValue.includes('.')
                ? selectedValue
                : `${selectedValue}.html`;

            changeIframeSrc(`/thru/${finalPath}`);
        };
        console.log("[UCUI:0] mapfiles done");
    }
      else {
          // 🔴 DEBUG: Why did the block fail?
          if (!mapfilesEl) console.error("🔴 Element #mapfiles not found in DOM");
          if (!Array.isArray(constants.mapfiles)) console.error("🔴 constants.mapfiles is not an array:", constants.mapfiles);
          if (constants.mapfiles?.length === 0) console.warn("🔴 constants.mapfiles is empty");
      }
      console.log("[UCUI:0] mapfiles section finished");   // runs on either path
        // =====================================================
        // Apply values + bind inputs
        // =====================================================
        Object.entries(constants).forEach(([key, value]) => {

            if (key === "mapfiles") return;

            const el = document.getElementById(key);
            if (!el) return;

            // 🛑 prevent triggering input while updating
            el.dataset.updating = "true";

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

            el.dataset.updating = "false";

            // =====================================================
            // AUTO BACKEND UPDATE
            // =====================================================
            if (!el.dataset.bound) {

                el.oninput = () => {

                    if (window.isUpdatingConstants) return;
                    if (el.dataset.updating === "true") return;

                    let newVal;

                    if (el.type === "number") newVal = parseFloat(el.value);
                    else if (el.type === "checkbox") newVal = el.checked;
                    else if (el.multiple) newVal = Array.from(el.selectedOptions).map(o => o.value);
                    else newVal = el.value;

                    fetch("/set-constant", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            election: document.querySelector(".election-tab.active")?.dataset.election || "",
                            name: key,
                            value: newVal
                        }),
                        credentials: "include"
                    })
                    .then(res => res.json())
                    .then(resp => {
                        console.log(`✅ [UCUI:0] Response for "${key}":`, resp);
                    })
                    .catch(err => {
                        console.error(`💥 [UCUI:0] Error updating "${key}":`, err);
                    });
                };

                el.dataset.bound = "true";
            }
        });
        console.log("[UCUI:0] apply loop done");

        if (typeof attachListenersToConstantFields === "function") {
            attachListenersToConstantFields(constants);
        }

        if (typeof populateDropdowns === "function") {
            populateDropdowns();
        }
          console.log("[UCUI:0] END (reached bottom)");

      } catch (err) {
          console.error("[UCUI:0] CRASH", err);
          throw err;
      } finally {
          window.isUpdatingConstants = false;
      }

};

window.refreshConstantsUI = function(callback) {
    console.log("📩 refreshing constants");
    const iframeWin = document.getElementById("iframe1")?.contentWindow;


    return fetch("/get-constants", { credentials: "same-origin" })
        .then(res => {
            if (!res.ok) {
                throw new Error(`Server error: ${res.status}`);
            }
            return res.json();
        })
        .then(data => {
            console.log("DATA RECEIVED:", data);

            window.latestConstants = data.constants;
            window.latestOptions = data.options;

            window.updateConstantsUI(data.constants, data.options);
//            iframeWin.populateAllSelects(data.options, data.constants);
            console.log("📩 calling initAccordion");
            initAccordionFromOptions(data.options);


            if (callback) callback(data);
            return data.constants;
        }).catch(err => {
          console.error("Failed to refresh constants:", err);
          alert(`Failed to load constants: ${err.message}`); // <--- Change this to see the true error
    });
}

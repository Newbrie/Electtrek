
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

window.updateConstantsUI = function (constants, options) {

    if (window.isUpdatingConstants) return;

    window.isUpdatingConstants = true;

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

        const result = getTagsJson(window.tags);
        window.task_tags    = result.task_tags;
        window.outcome_tags = result.outcome_tags;


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
    }
      else {
          // 🔴 DEBUG: Why did the block fail?
          if (!mapfilesEl) console.error("🔴 Element #mapfiles not found in DOM");
          if (!Array.isArray(constants.mapfiles)) console.error("🔴 constants.mapfiles is not an array:", constants.mapfiles);
          if (constants.mapfiles?.length === 0) console.warn("🔴 constants.mapfiles is empty");
      }

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
                        console.log(`✅ Response for "${key}":`, resp);
                    })
                    .catch(err => {
                        console.error(`💥 Error updating "${key}":`, err);
                    });
                };

                el.dataset.bound = "true";
            }
        });

        if (typeof attachListenersToConstantFields === "function") {
            attachListenersToConstantFields(constants);
        }

        if (typeof populateDropdowns === "function") {
            populateDropdowns();
        }

    } finally {
        window.isUpdatingConstants = false;
    }
};

window.refreshConstantsUI = function(callback) {
    console.log("📩 refreshing constants");

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
            populateAllSelects(data.options, data.constants);

            if (callback) callback(data);
            return data.constants;
        })
        .catch(err => {
            console.error("Failed to refresh constants:", err);
            alert("Failed to load constants. Check server logs.");
        });
}

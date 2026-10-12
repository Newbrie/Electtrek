// Configuration constants matching backend behavior
const IGNORABLE_SEGMENTS = new Set(['', '.', 'undefined', 'null']);
const FILE_SUFFIXES = ['-MAP.html', '-PRINT.html', '.html', '.htm'];

/**
 * Clean file suffixes, or return null if ignorable/empty.
 */
 function cleanPathPart(part) {
     if (!part) return null;
     const trimmed = part.trim();

     if (IGNORABLE_SEGMENTS.has(trimmed)) {
         return null;
     }

     for (const suffix of FILE_SUFFIXES) {
         if (trimmed.endsWith(suffix)) {
             return null;
         }
     }

     return trimmed;
 }

 /**
  * Split path string, clean each segment, and remove sequential duplicates.
  */
 function stepify(pathStr) {
     if (!pathStr || typeof pathStr !== 'string') return [];

     const parts = pathStr.trim().split('/');
     const cleaned = [];

     for (const part of parts) {
         const cleanedPart = cleanPathPart(part);
         if (cleanedPart) {
             // Only append if it's the first element OR not a duplicate of the previous element
             if (cleaned.length === 0 || cleaned[cleaned.length - 1] !== cleanedPart) {
                 cleaned.push(cleanedPart);
             }
         }
     }

     return cleaned;
 }

 /**
  * Takes a clean list of geographic parts and builds a node path string.
  */
 function pathify(parts) {
     if (!Array.isArray(parts) || parts.length === 0) {
         return "";
     }

     return parts.join('/');
 }

 window.renderTreeSelector = function (tree, options = {}) {
     const {
         containerId,
         emptyMessage = 'No items available',
         accordionId,
         allLabel = name => `All of ${name}`,
         createButton
     } = options;

     const container = document.getElementById(containerId);
     if (!container) return;

     container.innerHTML = '';

     if (
         !tree ||
         typeof tree !== 'object' ||
         Object.keys(tree).length === 0
     ) {
         container.innerHTML =
             `<div class="small text-muted p-2">${emptyMessage}</div>`;
         return;
     }

     const acc = document.createElement('div');
     acc.className = 'accordion';
     acc.id = accordionId;

     let idCounter = 0;

     function renderLevel(node, parentElement, path = [], depth = 0) {
         if (!node || typeof node !== 'object') return;

         Object.entries(node).forEach(([name, children]) => {
             const currentPath = [...path, name];

             const hasChildren =
                 children &&
                 typeof children === 'object' &&
                 Object.keys(children).length > 0;

             const uniqueId = `${accordionId}-${idCounter++}`;

             // -------------------------------------------------
             // TOP LEVEL
             // -------------------------------------------------
             if (depth === 0) {
                 const item = document.createElement('div');
                 item.className = 'accordion-item border-0 mb-1';

                 item.innerHTML = `
                     <h2 class="accordion-header">
                         <button
                             class="accordion-button collapsed py-2 shadow-none"
                             type="button"
                             data-bs-toggle="collapse"
                             data-bs-target="#${uniqueId}"
                             aria-expanded="false">
                             ${name}
                         </button>
                     </h2>

                     <div
                         id="${uniqueId}"
                         class="accordion-collapse collapse">

                         <div class="accordion-body p-0"></div>
                     </div>
                 `;

                 const body = item.querySelector('.accordion-body');

                 // Pass currentPath as 5th argument so createButton knows the full path
                 createButton(
                     body,
                     name,
                     allLabel(name),
                     'fw-semibold',
                     currentPath
                 );

                 if (hasChildren) {
                     renderLevel(
                         children,
                         body,
                         currentPath,
                         depth + 1
                     );
                 }

                 parentElement.appendChild(item);
                 return;
             }

             // -------------------------------------------------
             // NESTED LEVEL
             // -------------------------------------------------
             const wrapper = document.createElement('div');
             wrapper.className = 'border-0';

             if (hasChildren) {
                 const header = document.createElement('button');

                 header.type = 'button';
                 header.className =
                     'btn btn-sm w-100 text-start py-2 shadow-none';

                 header.style.paddingLeft =
                     `${1 + depth * 1.25}rem`;

                 header.setAttribute(
                     'data-bs-toggle',
                     'collapse'
                 );

                 header.setAttribute(
                     'data-bs-target',
                     `#${uniqueId}`
                 );

                 header.setAttribute(
                     'aria-expanded',
                     'false'
                 );

                 header.textContent = `▸ ${name}`;

                 const collapse = document.createElement('div');
                 collapse.id = uniqueId;
                 collapse.className = 'collapse';

                 const list = document.createElement('div');
                 list.className =
                     'list-group list-group-flush';

                 // Pass currentPath as 5th argument
                 createButton(
                     list,
                     name,
                     allLabel(name),
                     '',
                     currentPath
                 );

                 // Recursively render children
                 renderLevel(
                     children,
                     list,
                     currentPath,
                     depth + 1
                 );

                 collapse.appendChild(list);

                 wrapper.appendChild(header);
                 wrapper.appendChild(collapse);

             } else {
                 // -------------------------------------------------
                 // LEAF
                 // -------------------------------------------------
                 // Pass currentPath as 5th argument
                 createButton(
                     wrapper,
                     name,
                     name,
                     '',
                     currentPath
                 );
             }

             parentElement.appendChild(wrapper);
         });
     }

     // Initialize root path steps from window.mapfile if available, or empty array
     const rootSteps = typeof stepify === 'function' ? stepify(window.mapfile || "") : [];
     rootSteps.pop(); // remove current filename leaf if present

     renderLevel(tree, acc, rootSteps);

     container.appendChild(acc);
 };

 function createMapButton(parentElement, nodeName, labelText, className, nodePathArray) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `btn btn-sm w-100 text-start py-1 px-3 ${className || ''}`;
    btn.textContent = labelText.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase());

    btn.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();

        // 🛡️ Resolve targetPath FRESH at the moment of click
        let targetPath = nodeName;
        if (typeof pathify === 'function' && typeof stepify === 'function') {
            if (Array.isArray(nodePathArray) && nodePathArray.length > 0) {
                if (nodePathArray[0] === 'UNITED_KINGDOM') {
                    targetPath = pathify(nodePathArray);
                } else {
                    const parentSteps = stepify(window.mapfile || window.currentNodePath || "");
                    console.log(`🚀 ParentSteps: ${parentSteps}`);

                    parentSteps.pop(); // remove current territory level/filename
                    targetPath = pathify([...parentSteps, ...nodePathArray]);
                }
            } else if (window.mapfile || window.currentNodePath) {
                const cleanSteps = stepify(window.mapfile || window.currentNodePath);
                console.log(`🚀 cleanSteps: ${cleanSteps}`);

                cleanSteps.pop(); // remove current territory level/filename
                targetPath = pathify([...cleanSteps, nodeName]);
            }
        }

        const mapFilename = `${nodeName}-MAP.html`;
        const fetchPath = `${targetPath}/${mapFilename}`;

        console.log(`🚀 Sending path to backend: ${fetchPath}`);

        // 2. Tell the backend to switch to this path (corrected route to /downbut/ or /transfer/)
        fetch(`/transfer/${fetchPath}`, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) throw new Error('Backend transfer failed');
            return response.text();
        })
        .then(() => {
            const iframeSrc = `/thru/${targetPath}/${mapFilename}`;

            const mapIframe = document.querySelector('iframe') || document.getElementById('map-iframe');
            if (mapIframe) {
                mapIframe.src = iframeSrc;
                console.log(`🗺️ Iframe successfully updated to: ${iframeSrc}`);
            }

            // 3. Synchronize global window state
            window.currentNodePath = targetPath;
            window.mapfile = `${targetPath}/${mapFilename}`;

            // 4. Update header display text
            const displayElement = document.getElementById('display-path');
            if (displayElement) {
                displayElement.innerText = nodeName.replace(/_/g, ' ');
            }

            // 5. Close the accordion dropdown
            const accordion = document.getElementById('territory-accordion');
            if (accordion) {
                accordion.style.display = 'none';
            }
        })
        .catch(error => {
            console.error("❌ Error setting node path on backend:", error);
            window.location.href = `/downbut/${fetchPath}`;
        });
    };

    parentElement.appendChild(btn);
}

function createTaskButton(
list,
taskCode,
displayName,
indentClass = '',
selectedKey = 'selectedTask'
) {
const button = document.createElement('button');

button.type = 'button';
button.className =
    `list-group-item list-group-item-action small ${indentClass}`;

button.textContent = displayName;
button.dataset.code = taskCode;

if (window[selectedKey] === taskCode) {
    button.classList.add('active');
}

button.addEventListener('click', function () {
    const accordion = list.closest('.accordion');

    if (accordion) {
        accordion
            .querySelectorAll('.list-group-item')
            .forEach(btn => btn.classList.remove('active'));
    }

    window[selectedKey] = taskCode;

    button.classList.add('active');

    console.log('Task selected:', taskCode);

    syncTaskSelect();
});

list.appendChild(button);
}

function createAreaButton(
list,
taskCode,
displayName,
indentClass = '',
selectedKey = 'selectedTask'
) {
const button = document.createElement('button');

button.type = 'button';
button.className =
    `list-group-item list-group-item-action small ${indentClass}`;

button.textContent = displayName;
button.dataset.code = taskCode;

if (window[selectedKey] === taskCode) {
    button.classList.add('active');
}

button.addEventListener('click', function () {
    const accordion = list.closest('.accordion');

    if (accordion) {
        accordion
            .querySelectorAll('.list-group-item')
            .forEach(btn => btn.classList.remove('active'));
    }

    window[selectedKey] = taskCode;

    button.classList.add('active');

    console.log('Task selected:', taskCode);

    syncTaskSelect();
});

list.appendChild(button);
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

initAccordionFromOptions = (optionsData) => {
    const areas = optionsData?.areas || window.currentOptions?.areas || window.areaTree;
    if (!areas) return;

    const mapfile = window.mapfile || "UNITED_KINGDOM/ENGLAND/SURREY/SURREY_HEATH-MAP.html";
    const currentSteps = stepify(mapfile);

    const activeNodeName = currentSteps.length > 0 ? currentSteps[currentSteps.length - 1] : "SURREY_HEATH";

    const displayElement = document.getElementById('display-path');
    if (displayElement) {
        displayElement.innerText = activeNodeName.replace(/_/g, ' ');
    }

    if (typeof window.renderTreeSelector === "function") {
        window.renderTreeSelector(areas, {
            containerId: 'children-list',
            accordionId: 'election-accordion',
            emptyMessage: 'No sub-divisions available',
            allLabel: (name) => `${name.replace(/_/g, ' ')}`,
            createButton: createMapButton // 👈 Maps your interactive map button builder here!
        });
        console.log("✅ Successfully initialized territory accordion with createMapButton!");
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

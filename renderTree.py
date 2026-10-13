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
            let combinedSteps = [];

            if (Array.isArray(nodePathArray) && nodePathArray.length > 0) {
                // If we have an explicit nodePathArray, use it as the primary source of truth
                combinedSteps = stepify(nodePathArray.join('/'));
            } else {
                // Otherwise, grab active path and append the new node name
                const activePath = window.currentNodePath || window.mapfile || "UNITED_KINGDOM";
                const cleanParentSteps = stepify(activePath);
                combinedSteps = [...cleanParentSteps, nodeName];
            }

            // 🛡️ THE FIX: Pass the fully combined steps back through stepify(pathify(...))
            // This guarantees that any duplicate at the boundary seam (e.g. SURREY / SURREY)
            // is completely eradicated globally across the whole path!
            const finalCleanSteps = stepify(pathify(combinedSteps));
            targetPath = pathify(finalCleanSteps);
        }

        const mapFilename = `${nodeName}-MAP.html`;
        const fetchPath = `${targetPath}/${mapFilename}`;

        console.log(`🚀 Sending path to backend: ${fetchPath}`);

        fetch(`/transfer/${fetchPath}`, {
            method: 'GET',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(response => {
            if (!response.ok) throw new Error('Backend transfer failed');
            return response.json(); // 👈 Expecting JSON now instead of raw text
        })
        .then(data => {
            if (data.success && data.map_url) {
                const mapIframe = document.querySelector('iframe') || document.getElementById('map-iframe');
                if (mapIframe) {
                    mapIframe.src = data.map_url; // 👈 Assign the filepath/URL returned from Python
                    console.log(`🗺️ Iframe successfully updated to: ${data.map_url}`);
                }

                // Synchronize global window state
                window.currentNodePath = targetPath;
                window.mapfile = `${targetPath}/${mapFilename}`;
            }
        })
        .catch(error => {
            console.error("❌ Error setting node path on backend:", error);
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

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

// Make stepify & pathify available globally
window.stepify = stepify;
window.pathify = pathify;


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

    if (!tree || typeof tree !== 'object' ||
        Object.keys(tree).length === 0) {
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
                !Array.isArray(children) &&
                Object.keys(children).length > 0 &&
                Object.values(children).some(
                    val => typeof val === 'object' && val !== null
                );

            const uniqueId = `${accordionId}-${idCounter++}`;

            if (depth === 0) {
                const item = document.createElement('div');
                item.className = 'accordion-item border-0 mb-1';

                item.innerHTML = `
                    <h2 class="accordion-header">
                        <button class="accordion-button collapsed py-2 shadow-none"
                                type="button"
                                data-bs-toggle="collapse"
                                data-bs-target="#${uniqueId}"
                                aria-expanded="false">
                            ${name.replace(/_/g, ' ')}
                        </button>
                    </h2>
                    <div id="${uniqueId}" class="accordion-collapse collapse">
                        <div class="accordion-body p-0"></div>
                    </div>
                `;

                const body = item.querySelector('.accordion-body');

                createButton(
                    body, name, allLabel(name),
                    'fw-semibold', currentPath
                );

                if (hasChildren) {
                    renderLevel(children, body, currentPath, depth + 1);
                }

                parentElement.appendChild(item);
                return;
            }

            const wrapper = document.createElement('div');
            wrapper.className = 'border-0';

            if (hasChildren) {
                const header = document.createElement('button');
                header.type = 'button';
                header.className =
                    'btn btn-sm w-100 text-start py-2 shadow-none';
                header.style.paddingLeft =
                    `${1 + depth * 1.25}rem`;
                header.setAttribute('data-bs-toggle', 'collapse');
                header.setAttribute('data-bs-target', `#${uniqueId}`);
                header.setAttribute('aria-expanded', 'false');
                header.textContent =
                    `▸ ${name.replace(/_/g, ' ')}`;

                const collapse = document.createElement('div');
                collapse.id = uniqueId;
                collapse.className = 'collapse';

                const list = document.createElement('div');
                list.className = 'list-group list-group-flush';

                createButton(
                    list, name, allLabel(name), '', currentPath
                );

                renderLevel(children, list, currentPath, depth + 1);

                collapse.appendChild(list);
                wrapper.appendChild(header);
                wrapper.appendChild(collapse);
              } else {
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

    const rootSteps =
        typeof stepify === 'function'
            ? stepify(window.mapfile || '')
            : [];

    rootSteps.pop();

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

        let targetPath = nodeName;

        if (typeof pathify === 'function' && typeof stepify === 'function') {
            // 🎯 Use window.mapfile or window.currentNodePath as the authoritative baseline
            const activePath = window.mapfile || window.currentNodePath || "UNITED_KINGDOM";
            const parentSteps = stepify(activePath);

            // Pop off the old leaf mapfile name from the active path to get the clean parent directory sequence
            if (parentSteps.length > 0 && parentSteps[parentSteps.length - 1].includes('-MAP')) {
                parentSteps.pop();
            }

            // Combine base directory steps with the clicked nodeName
            const combinedSteps = [...parentSteps, nodeName];
            const finalCleanSteps = stepify(pathify(combinedSteps));
            targetPath = pathify(finalCleanSteps);
        }

        // Extract the leaf node name cleanly for the map file suffix
        const pathSteps = targetPath.split('/');
        const leafNodeName = pathSteps[pathSteps.length - 1];
        const mapFilename = `${leafNodeName}-MAP.html`;
        const fetchPath = `${targetPath}/${mapFilename}`;

        console.log(`🚀 Sending path to backend: ${fetchPath}`);

        fetch(`/transfer/${fetchPath}`, {
            method: 'GET',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(response => {
            if (!response.ok) throw new Error('Backend transfer failed');
            return response.json();
        })
        .then(data => {
            if (data.success && data.map_url) {
                const mapIframe = document.getElementById('iframe1') || document.querySelector('iframe');
                if (mapIframe) {
                    mapIframe.src = data.map_url;
                    console.log(`🗺️ Iframe successfully updated to: ${data.map_url}`);
                }

                // Update global state tracking
                window.currentNodePath = targetPath;
                window.mapfile = `${targetPath}/${mapFilename}`;

                // Update display path header
                const displayElement = document.getElementById('display-path');
                if (displayElement) {
                    displayElement.innerText = leafNodeName.replace(/_/g, ' ');
                }
            }
        })
        .catch(error => {
            console.error("❌ Error setting node path on backend:", error);
        });
    };

    parentElement.appendChild(btn);
}

window.initAccordionFromOptions = (tree, config = {}) => {
    if (!tree || typeof tree !== 'object') {
        console.warn("⚠️ initAccordionFromOptions: No valid tree provided.");
        return;
    }

    let currentTree = tree;
    const activePath = window.currentNodePath || window.mapfile || "";

    if (typeof stepify === 'function' && activePath) {
        let steps = stepify(activePath);

        // 🎯 TARGET CHANGE: Stop traversal at "SURREY" (or slice off the last leaf level so parent context remains visible)
        // If you want to view from Surrey downwards, find where Surrey is and stop there,
        // or exclude the last 1 or 2 steps (like the specific Woking ward/constituency leaf).
        const surreyIndex = steps.findIndex(s => s.toUpperCase() === "SURREY");
        if (surreyIndex !== -1) {
            // Keep up to Surrey, or keep Surrey + its immediate children container
            steps = steps.slice(0, surreyIndex + 2); // Includes SURREY and its direct children (constituencies)
        } else if (steps.length > 1) {
            // Fallback: Drop just the final leaf node so you see the parent container
            steps = steps.slice(0, steps.length - 1);
        }

        // Traverse down the restricted steps
        for (const step of steps) {
            // Case-insensitive key matching
            const matchedKey = Object.keys(currentTree).find(k => k.toUpperCase() === step.toUpperCase());
            if (matchedKey && currentTree[matchedKey] && typeof currentTree[matchedKey] === 'object') {
                currentTree = currentTree[matchedKey];
            }
        }
    }

    const containerId = config.containerId || 'children-list';
    const accordionId = config.accordionId || 'election-accordion';
    const createButton =  window.createMapButton;
    const emptyMessage = config.emptyMessage || 'No sub-divisions available';

    const currentSteps = typeof stepify === 'function' && activePath ? stepify(activePath) : [];
    const activeNodeName = currentSteps.length > 0 ? currentSteps[currentSteps.length - 1] : "SURREY";

    const displayElement = document.getElementById('display-path');
    if (displayElement) {
        displayElement.innerText = activeNodeName.replace(/_/g, ' ');
    }

    if (typeof window.renderTreeSelector === "function") {
        window.renderTreeSelector(currentTree, {
            containerId: containerId,
            accordionId: accordionId,
            emptyMessage: emptyMessage,
            allLabel: (name) => `${name.replace(/_/g, ' ')}`,
            createButton: createButton
        });
        console.log(`✅ Successfully initialized accordion for #${containerId} rooted at Surrey hierarchy!`);
    }
};



function createAreaButton(list, AreaCode, displayName, indentClass = '') {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = `list-group-item list-group-item-action small ${indentClass}`;
  button.textContent = displayName;
  button.dataset.code = AreaCode;

  if (window.selectedArea === AreaCode) button.classList.add('active');

  button.addEventListener('click', () => {
    list.closest('.accordion')
        ?.querySelectorAll('.list-group-item')
        .forEach(b => b.classList.remove('active'));
    window.selectedArea = AreaCode;
    button.classList.add('active');
    syncAreaSelect();
  });

  list.appendChild(button);
}


function createTaskButton(list, taskCode, displayName, indentClass = '') {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = `list-group-item list-group-item-action small ${indentClass}`;
  button.textContent = displayName;
  button.dataset.code = taskCode;

  if (window.selectedTask === taskCode) button.classList.add('active');

  button.addEventListener('click', () => {
    list.closest('.accordion')
        ?.querySelectorAll('.list-group-item')
        .forEach(b => b.classList.remove('active'));
    window.selectedTask = taskCode;
    button.classList.add('active');
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


/* ---------- Sync Helpers for Single Select ---------- */
window.selectedArea = null;
window.selectedTask = null;

function syncTaskSelect() {
  const sel = document.getElementById('activitySelect');
  if (!sel) return;

  const code = window.selectedTask;
  if (!code) {
    sel.replaceChildren();
    return;
}

  const label = code; // Replace with the task's descriptive label
  sel.replaceChildren(new Option(label, code, true, true));
  sel.value = code;
}

function syncAreaSelect() {

  const sel = document.getElementById('areaSelect');
  if (!sel) return;

  const code = window.selectedArea;
  if (!code) {
    sel.replaceChildren();
    return;
}

  const label = code; // Replace with the area's descriptive label
  sel.replaceChildren(new Option(label, code, true, true));
  sel.value = code;
}

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


 const TYPE_SEGMENT = { ward: 'WARDS', division: 'DIVS' };
 const TYPED_CHILD_INDEX = 4;

 /**
  * parts:     level-aligned steps, e.g. ['UNITED_KINGDOM','ENGLAND','SURREY','EAST_SURREY','GODSTONE']
  * typedNode: type ('ward' | 'division') of the node at index 4 in this path.
  */
 function pathify(parts, typedNode = 'ward') {
     if (!Array.isArray(parts) || parts.length === 0) {
         return "";
     }

     // Already typed? Don't insert a second segment.
     if (parts.some(p => Object.values(TYPE_SEGMENT).includes(p))) {
         return parts.join('/');
     }

     // Too shallow to have a typed child
     if (parts.length <= TYPED_CHILD_INDEX) {
         return parts.join('/');
     }

     const seg = TYPE_SEGMENT[typedNode];
     return [
         ...parts.slice(0, TYPED_CHILD_INDEX),
         ...(seg ? [seg] : []),
         ...parts.slice(TYPED_CHILD_INDEX),
     ].join('/');
 }

// Make stepify & pathify available globally
window.stepify = stepify;
window.pathify = pathify;


// WARDS / DIVS are grouping segments in the typed area tree: they are shown as
// headers but have no map of their own, so they never get an "All" map button.
const TYPE_GROUPS = new Set(['WARDS', 'DIVS']);

window.renderTreeSelector = function (tree, options = {}) {
    const {
        containerId,
        emptyMessage = 'No items available',
        accordionId,
        allLabel = name => `All of ${name}`,
        createButton,
        rootPath            // NEW: real keys descended through to reach `tree`
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
            const isGroup = TYPE_GROUPS.has(name.toUpperCase());

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

                if (!isGroup) {
                    createButton(
                        body, name, allLabel(name),
                        'fw-semibold', currentPath
                    );
                }

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

                if (!isGroup) {
                    createButton(
                        list, name, allLabel(name), '', currentPath
                    );
                }

                renderLevel(children, list, currentPath, depth + 1);

                collapse.appendChild(list);
                wrapper.appendChild(header);
                wrapper.appendChild(collapse);
            } else if (!isGroup) {
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

    // Start path: use the keys the caller actually descended through, so the
    // path and the tree can never drift apart. Fall back to the old
    // mapfile-based guess only if no rootPath was supplied.
    let startPath;
    if (Array.isArray(rootPath)) {
        startPath = [...rootPath];
    } else {
        startPath = typeof stepify === 'function'
            ? stepify(window.mapfile || '')
            : [];
        startPath.pop();
    }

    renderLevel(tree, acc, startPath);
    container.appendChild(acc);
};

function createMapButton(parentElement, nodeName, labelText, className, nodePath) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `btn btn-sm w-100 text-start py-1 px-3 ${className || ''}`;
    btn.textContent = labelText.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase());

    btn.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();

        // nodePath is the node's full Geo_index key, e.g.
        // UNITED_KINGDOM/ENGLAND/SURREY/EAST_SURREY/WARDS/GODSTONE
        const targetPath = nodePath;

        const leafNodeName = targetPath.split('/').pop();
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





function createAreaButton(list, AreaCode, displayName, indentClass = '', nodePath) {
  // Typed Geo_index path is the unique id; fall back to the bare name if none is supplied
  const code = Array.isArray(nodePath) ? nodePath.join('/') : (nodePath || AreaCode);

  const button = document.createElement('button');
  button.type = 'button';
  button.className = `list-group-item list-group-item-action small ${indentClass}`;
  button.textContent = displayName;
  button.dataset.code = code;

  if (window.selectedArea === code) button.classList.add('active');

  button.addEventListener('click', () => {
    list.closest('.accordion')
        ?.querySelectorAll('.list-group-item')
        .forEach(b => b.classList.remove('active'));
    window.selectedArea = code;
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

window.initAccordionFromOptions = (tree, config = {}) => {
    if (!tree || typeof tree !== 'object') {
        console.warn("⚠️ initAccordionFromOptions: No valid tree provided.");
        return;
    }

    const hasPath = typeof stepify === 'function' && !!window.mapfile;
    const fullSteps = hasPath ? stepify(window.mapfile) : [];

    let currentTree = tree;
    const rootPath = [];   // hoisted so it's always defined for renderTreeSelector

    if (fullSteps.length) {
        let steps = fullSteps;

        // Stop at SURREY plus its direct children, otherwise drop the final leaf
        // so the parent container stays visible.
        const surreyIndex = steps.findIndex(s => s.toUpperCase() === "SURREY");
        if (surreyIndex !== -1) {
            steps = steps.slice(0, surreyIndex + 2);
        } else if (steps.length > 1) {
            steps = steps.slice(0, -1);
        }

        // Walk down the tree, recording the real keys as we go
        for (const step of steps) {
            const matchedKey = Object.keys(currentTree)
                .find(k => k.toUpperCase() === step.toUpperCase());

            if (matchedKey && currentTree[matchedKey] && typeof currentTree[matchedKey] === 'object') {
                currentTree = currentTree[matchedKey];
                rootPath.push(matchedKey);
            } else {
                console.warn(`⚠️ initAccordionFromOptions: "${step}" not found in tree, stopping at "${rootPath.join('/') || 'root'}".`);
                break;   // don't skip ahead into the wrong subtree
            }
        }
    }

    const containerId  = config.containerId  || 'children-list';
    const accordionId  = config.accordionId  || 'election-accordion';
    const emptyMessage = config.emptyMessage || 'No sub-divisions available';
    const createButton = config.createButton || window.createMapButton;

    const activeNodeName = fullSteps.length ? fullSteps[fullSteps.length - 1] : "SURREY";

    const displayElement = document.getElementById('display-path');
    if (displayElement) {
        displayElement.innerText = activeNodeName.replace(/_/g, ' ');
    }

    if (typeof window.renderTreeSelector !== "function") {
        console.warn("⚠️ initAccordionFromOptions: window.renderTreeSelector is not available.");
        return;
    }

    window.renderTreeSelector(currentTree, {
        containerId,
        accordionId,
        emptyMessage,
        allLabel: (name) => name.replace(/_/g, ' '),
        createButton,
        rootPath
    });

    console.log(`✅ Initialized accordion for #${containerId} rooted at /${rootPath.join('/')}`);
};
